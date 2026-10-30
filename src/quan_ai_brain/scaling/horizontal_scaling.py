"""
Horizontal Scaling Module (V30.1) — SIMULATED, in-process only.

Provides:
- LoadBalancer: round-robin / least-connections / weighted strategies
- Health-check registry (mark unhealthy after N consecutive failures)
- Service registry (register / deregister / discover)
- Sticky sessions via client-id hash
- Per-node circuit breaker (closed -> open -> half_open)

SIMULATION SCOPE (per V30 plan constraints):
- No sockets, no ports, no real network calls, no K8s/Docker/Redis.
- All state is in-process; this models control-plane logic only.

Version: V30.1
"""

import hashlib
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class ScalingStrategy(Enum):
    """Load balancing strategy."""
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED = "weighted"
    STICKY = "sticky"


class NodeState(Enum):
    """Lifecycle state of a backend node."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DRAINING = "draining"


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"          # normal operation
    OPEN = "open"              # tripped, rejecting requests
    HALF_OPEN = "half_open"    # allowing a probe request


@dataclass
class BackendNode:
    """A single backend node in the pool."""
    node_id: str
    address: str
    port: int
    weight: int = 1
    state: NodeState = NodeState.HEALTHY
    active_connections: int = 0
    total_requests: int = 0
    total_failures: int = 0
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    last_health_check: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "address": self.address,
            "port": self.port,
            "weight": self.weight,
            "state": self.state.value,
            "active_connections": self.active_connections,
            "total_requests": self.total_requests,
            "total_failures": self.total_failures,
        }


@dataclass
class StickySession:
    """Sticky session binding a client to a node."""
    client_id: str
    node_id: str
    created_at: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    request_count: int = 0


@dataclass
class CircuitBreaker:
    """Per-node circuit breaker."""
    failure_threshold: int = 5
    recovery_timeout: float = 30.0
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count_in_half_open: int = 0
    opened_at: Optional[float] = None
    total_trips: int = 0

    def can_pass(self, now: Optional[float] = None) -> bool:
        now = now if now is not None else time.time()
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            if self.opened_at is not None and (now - self.opened_at) >= self.recovery_timeout:
                # Move to half-open: allow probe
                self.state = CircuitState.HALF_OPEN
                self.success_count_in_half_open = 0
                return True
            return False
        # HALF_OPEN: allow a limited number of probes
        return self.success_count_in_half_open < 1  # single probe at a time

    def record_success(self) -> None:
        if self.state == CircuitState.OPEN:
            # implicit probe: only closes if recovery timeout has elapsed
            now = time.time()
            if self.opened_at is not None and (now - self.opened_at) >= self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                self.success_count_in_half_open = 0
            else:
                return  # still within open period; stays OPEN
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            self.failure_count = 0
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0

    def record_failure(self, now: Optional[float] = None) -> None:
        now = now if now is not None else time.time()
        if self.state == CircuitState.HALF_OPEN:
            self._trip(now)
            return
        self.failure_count += 1
        if self.failure_count >= self.failure_threshold:
            self._trip(now)

    def _trip(self, now: float) -> None:
        self.state = CircuitState.OPEN
        self.opened_at = now
        self.total_trips += 1
        self.failure_count = self.failure_threshold


class ServiceRegistry:
    """In-process service registry: register / deregister / discover."""

    def __init__(self) -> None:
        # service_name -> {node_id: BackendNode}
        self._services: Dict[str, Dict[str, BackendNode]] = {}

    def register(self, service_name: str, node: BackendNode) -> None:
        nodes = self._services.setdefault(service_name, {})
        nodes[node.node_id] = node

    def deregister(self, service_name: str, node_id: str) -> bool:
        nodes = self._services.get(service_name)
        if not nodes:
            return False
        return nodes.pop(node_id, None) is not None

    def get_service(self, service_name: str) -> List[BackendNode]:
        return list(self._services.get(service_name, {}).values())

    def has_service(self, service_name: str) -> bool:
        return bool(self._services.get(service_name))

    def service_names(self) -> List[str]:
        return sorted(self._services.keys())

    def node_count(self, service_name: str) -> int:
        return len(self._services.get(service_name, {}))

    def clear(self) -> None:
        self._services.clear()


class HealthCheckRegistry:
    """
    Tracks health-check outcomes per node.
    Marks a node unhealthy after `failure_threshold` consecutive failures.
    """

    def __init__(self, failure_threshold: int = 3, checker: Optional[Callable[[str], bool]] = None):
        if failure_threshold < 1:
            raise ValueError("failure_threshold must be >= 1")
        self.failure_threshold = failure_threshold
        # node_id -> consecutive failure count
        self._fail_counts: Dict[str, int] = {}
        self._checker = checker

    def record_success(self, node_id: str) -> NodeState:
        self._fail_counts[node_id] = 0
        return NodeState.HEALTHY

    def record_failure(self, node_id: str) -> NodeState:
        count = self._fail_counts.get(node_id, 0) + 1
        self._fail_counts[node_id] = count
        if count >= self.failure_threshold:
            return NodeState.UNHEALTHY
        return NodeState.HEALTHY

    def is_healthy(self, node_id: str) -> bool:
        return self._fail_counts.get(node_id, 0) < self.failure_threshold

    def failure_count(self, node_id: str) -> int:
        return self._fail_counts.get(node_id, 0)

    def run_check(self, node: BackendNode) -> NodeState:
        """Run the registered checker (or default probe) for one node."""
        if self._checker is not None:
            ok = self._checker(node)
        else:
            ok = node.state != NodeState.UNHEALTHY
        if ok:
            return self.record_success(node.node_id)
        return self.record_failure(node.node_id)

    def run_checks(self, nodes: List[BackendNode]) -> Dict[str, NodeState]:
        return {n.node_id: self.run_check(n) for n in nodes}


class LoadBalancer:
    """
    In-process load balancer.

    - strategies: round_robin | least_connections | weighted | sticky
    - sticky: consistent hash of client_id -> node (also available directly
      via sticky_route for pure hash-based routing without session tracking)
    - integrates health-check registry + per-node circuit breaker
    """

    def __init__(
        self,
        strategy: ScalingStrategy = ScalingStrategy.ROUND_ROBIN,
        health_failure_threshold: int = 3,
        cb_failure_threshold: int = 5,
        cb_recovery_timeout: float = 30.0,
    ) -> None:
        self.strategy = strategy
        self.registry = ServiceRegistry()
        self.health = HealthCheckRegistry(failure_threshold=health_failure_threshold)
        self._circuits: Dict[str, CircuitBreaker] = {}
        self._cb_failure_threshold = cb_failure_threshold
        self._cb_recovery_timeout = cb_recovery_timeout
        self._round_robin_idx = 0
        self._sticky_sessions: Dict[str, StickySession] = {}
        self._sticky_ttl: float = 300.0
        self.stats: Dict[str, int] = {
            "requests_routed": 0,
            "requests_rejected": 0,
        }

    # ---------------- node management ----------------

    def add_node(self, node: BackendNode) -> None:
        if node.node_id in {n.node_id for n in self.registry.get_service("default")}:
            raise ValueError(f"Duplicate node_id: {node.node_id}")
        self.registry.register("default", node)
        self._circuits[node.node_id] = CircuitBreaker(
            failure_threshold=self._cb_failure_threshold,
            recovery_timeout=self._cb_recovery_timeout,
        )

    def remove_node(self, node_id: str) -> bool:
        existed = self.registry.deregister("default", node_id)
        self._circuits.pop(node_id, None)
        return existed

    def nodes(self) -> List[BackendNode]:
        return self.registry.get_service("default")

    def node(self, node_id: str) -> Optional[BackendNode]:
        for n in self.registry.get_service("default"):
            if n.node_id == node_id:
                return n
        return None

    # ---------------- health ----------------

    def mark_failure(self, node_id: str) -> NodeState:
        """Record one health-check failure; mark unhealthy after threshold."""
        node = self.node(node_id)
        state = self.health.record_failure(node_id)
        if node is not None:
            node.state = state
            node.consecutive_failures += 1
        return state

    def mark_success(self, node_id: str) -> NodeState:
        node = self.node(node_id)
        state = self.health.record_success(node_id)
        if node is not None:
            node.state = state
            node.consecutive_failures = 0
            node.consecutive_successes += 1
        return state

    def mark_unhealthy(self, node_id: str) -> None:
        node = self.node(node_id)
        if node is not None:
            node.state = NodeState.UNHEALTHY

    def healthy_nodes(self) -> List[BackendNode]:
        return [n for n in self.nodes() if n.state == NodeState.HEALTHY]

    def is_node_healthy(self, node_id: str) -> bool:
        node = self.node(node_id)
        return node is not None and node.state == NodeState.HEALTHY

    # ---------------- circuit breaker ----------------

    def circuit(self, node_id: str) -> CircuitBreaker:
        if node_id not in self._circuits:
            self._circuits[node_id] = CircuitBreaker(
                failure_threshold=self._cb_failure_threshold,
                recovery_timeout=self._cb_recovery_timeout,
            )
        return self._circuits[node_id]

    def circuit_state(self, node_id: str) -> CircuitState:
        return self.circuit(node_id).state

    def trip_circuit(self, node_id: str, now: Optional[float] = None) -> CircuitState:
        cb = self.circuit(node_id)
        cb._trip(now if now is not None else time.time())
        return cb.state

    def record_request_result(self, node_id: str, success: bool) -> None:
        cb = self.circuit(node_id)
        if success:
            cb.record_success()
            self.mark_success(node_id)
        else:
            cb.record_failure()
            self.mark_failure(node_id)

    # ---------------- routing ----------------

    def _route_round_robin(self, candidates: List[BackendNode]) -> BackendNode:
        if self._round_robin_idx >= len(candidates):
            self._round_robin_idx = 0
        node = candidates[self._round_robin_idx]
        self._round_robin_idx = (self._round_robin_idx + 1) % max(len(candidates), 1)
        return node

    @staticmethod
    def _hash(client_id: str) -> int:
        return int(hashlib.sha256(client_id.encode("utf-8")).hexdigest(), 16)

    def sticky_route(self, client_id: str, candidates: List[BackendNode]) -> BackendNode:
        """Pure hash-based sticky routing (deterministic, no session table)."""
        h = self._hash(client_id)
        return candidates[h % len(candidates)]

    def _get_or_create_session(self, client_id: str) -> Optional[StickySession]:
        sess = self._sticky_sessions.get(client_id)
        now = time.time()
        if sess is not None and (now - sess.last_seen) > self._sticky_ttl:
            sess = None  # expired
        return sess

    def route(
        self,
        client_id: Optional[str] = None,
        strategy: Optional[ScalingStrategy] = None,
        service: str = "default",
    ) -> BackendNode:
        """
        Route a logical request to a backend node.
        Raises RuntimeError when no healthy candidate is available or the
        chosen node's circuit is open.
        """
        strat = strategy if strategy is not None else self.strategy
        candidates = self.healthy_nodes()
        if not candidates:
            self.stats["requests_rejected"] += 1
            raise RuntimeError("no healthy backend node available")

        if strat == ScalingStrategy.STICKY:
            if client_id is None:
                raise ValueError("client_id required for sticky routing")
            sess = self._get_or_create_session(client_id)
            if sess is not None:
                target = self.node(sess.node_id)
                if target is not None and target.state == NodeState.HEALTHY and \
                        self.circuit(sess.node_id).can_pass():
                    sess.last_seen = time.time()
                    sess.request_count += 1
                    target.total_requests += 1
                    target.active_connections += 1
                    self.stats["requests_routed"] += 1
                    return target
                # fall through to re-hash
            target = self.sticky_route(client_id, candidates)
            self._sticky_sessions[client_id] = StickySession(
                client_id=client_id, node_id=target.node_id
            )
            target.total_requests += 1
            target.active_connections += 1
            self.stats["requests_routed"] += 1
            return target

        # Non-sticky strategies: pick, then check circuit
        if strat == ScalingStrategy.ROUND_ROBIN:
            target = self._route_round_robin(candidates)
        elif strat == ScalingStrategy.LEAST_CONNECTIONS:
            target = min(candidates, key=lambda n: (n.active_connections, n.node_id))
        elif strat == ScalingStrategy.WEIGHTED:
            total = sum(n.weight for n in candidates)
            pos = self._round_robin_idx % total
            acc = 0
            target = candidates[-1]
            for n in candidates:
                acc += n.weight
                if pos < acc:
                    target = n
                    break
            self._round_robin_idx += 1
        else:
            raise ValueError(f"unsupported strategy: {strat}")

        if not self.circuit(target.node_id).can_pass():
            self.stats["requests_rejected"] += 1
            raise RuntimeError(f"circuit open for node {target.node_id}")
        target.total_requests += 1
        target.active_connections += 1
        self.stats["requests_routed"] += 1
        return target

    def release(self, node_id: str) -> None:
        """Release a connection slot after request completion."""
        node = self.node(node_id)
        if node is not None and node.active_connections > 0:
            node.active_connections -= 1

    # ---------------- sticky session helpers ----------------

    def sticky_session(self, client_id: str) -> Optional[StickySession]:
        return self._sticky_sessions.get(client_id)

    def expire_sticky_sessions(self, max_age: Optional[float] = None) -> int:
        """Drop sticky sessions older than max_age (default: ttl). Returns dropped count."""
        now = time.time()
        ttl = max_age if max_age is not None else self._sticky_ttl
        dropped = 0
        for cid in list(self._sticky_sessions.keys()):
            sess = self._sticky_sessions[cid]
            if (now - sess.last_seen) > ttl:
                del self._sticky_sessions[cid]
                dropped += 1
        return dropped

    # ---------------- stats ----------------

    def load_distribution(self) -> Dict[str, int]:
        return {n.node_id: n.total_requests for n in self.nodes()}

    def reset(self) -> None:
        self.registry.clear()
        self._circuits.clear()
        self._sticky_sessions.clear()
        self._round_robin_idx = 0
        self.stats = {"requests_routed": 0, "requests_rejected": 0}
