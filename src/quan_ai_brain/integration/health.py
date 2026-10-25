"""Connector Health Monitor and Circuit Breaker."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import time
from typing import Any

from quan_ai_brain.integration.adapter import BaseConnectorAdapter


class CircuitState(str, Enum):
    CLOSED = "CLOSED"        # Normal operating condition
    HALF_OPEN = "HALF_OPEN"  # Testing recovery
    TRIPPED = "TRIPPED"      # Halted due to consecutive failures


@dataclass
class HealthStatus:
    system_id: str
    healthy: bool
    status_text: str
    latency_ms: float
    circuit_state: CircuitState = CircuitState.CLOSED
    consecutive_failures: int = 0
    total_calls: int = 0
    total_errors: int = 0
    last_check_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        res = asdict(self)
        res["circuit_state"] = self.circuit_state.value
        return res


class ConnectorHealthMonitor:
    """Monitors live health, latency, and circuit breaker trip states for external connectors."""

    def __init__(self, failure_threshold: int = 4, recovery_timeout_sec: float = 30.0) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout_sec = recovery_timeout_sec
        self._stats: dict[str, HealthStatus] = {}

    def get_status(self, system_id: str) -> HealthStatus | None:
        return self._stats.get(system_id)

    def check_health(self, adapter: BaseConnectorAdapter) -> HealthStatus:
        """Execute non-destructive health probe on an adapter."""
        system_id = adapter.manifest.system_id
        stat = self._stats.setdefault(
            system_id,
            HealthStatus(
                system_id=system_id,
                healthy=True,
                status_text="INITIALIZING",
                latency_ms=0.0,
            ),
        )
        stat.total_calls += 1

        # Check if circuit is tripped
        now = time.time()
        if stat.circuit_state == CircuitState.TRIPPED:
            # Check if recovery timeout elapsed
            last_dt = datetime.fromisoformat(stat.last_check_utc).timestamp()
            if now - last_dt >= self.recovery_timeout_sec:
                stat.circuit_state = CircuitState.HALF_OPEN
            else:
                stat.healthy = False
                stat.status_text = "CIRCUIT_TRIPPED"
                return stat

        t0 = time.perf_counter()
        try:
            res = adapter.health_check()
            latency = (time.perf_counter() - t0) * 1000.0
            is_ok = bool(res.get("healthy", False))

            if is_ok:
                stat.healthy = True
                stat.status_text = res.get("status", "HEALTHY")
                stat.latency_ms = round(latency, 2)
                stat.consecutive_failures = 0
                stat.circuit_state = CircuitState.CLOSED
                stat.details = res
            else:
                self._record_failure(stat, res.get("error", "Health check returned false"))
        except Exception as exc:
            self._record_failure(stat, str(exc))

        stat.last_check_utc = datetime.now(timezone.utc).isoformat()
        return stat

    def _record_failure(self, stat: HealthStatus, error_msg: str) -> None:
        stat.healthy = False
        stat.total_errors += 1
        stat.consecutive_failures += 1
        stat.status_text = f"UNHEALTHY: {error_msg}"
        if stat.consecutive_failures >= self.failure_threshold:
            stat.circuit_state = CircuitState.TRIPPED
