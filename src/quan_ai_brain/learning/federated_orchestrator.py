"""
Federated Learning Orchestrator Module (V23.2)

Coordinates federated training rounds across simulated in-memory nodes:
- Federated round lifecycle (dispatch -> collect -> aggregate)
- Weighted aggregation of model weights and knowledge updates
- Node participation control: voting, unresponsive tracking, drop-out
- Optional differential-privacy noise (Laplace / Gaussian) with budget

SIMULATED COMPONENTS (no network, no subprocess, stdlib only):
- Nodes are in-memory dataclasses; "training" is delegated to a caller-supplied
  synchronous callback (``train_fn``). A real deployment would replace this with
  authenticated network calls; nothing here performs network I/O.
- DP noise is applied to aggregated weights mathematically only.

Version: V23.2
Author: QUAN AI BRAIN Team
"""

from __future__ import annotations

import logging
import math
import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Sequence

logger = logging.getLogger(__name__)

NODE_STATUS_ACTIVE = "active"
NODE_STATUS_VOTING = "voting"
NODE_STATUS_UNRESPONSIVE = "unresponsive"
NODE_STATUS_DROPPED = "dropped"

_ELIGIBLE_STATUSES = (NODE_STATUS_ACTIVE, NODE_STATUS_VOTING, NODE_STATUS_UNRESPONSIVE)


class InsufficientNodesError(RuntimeError):
    """Raised when a federated round cannot start (too few eligible nodes)."""


class PrivacyBudgetExhausted(RuntimeError):
    """Raised when a DP query would exceed the configured privacy budget."""


class NodeUnresponsiveError(RuntimeError):
    """Simulated fault: a node failed to answer within the (logical) timeout."""


@dataclass
class FederatedNode:
    """A simulated participant node in the federated network."""

    node_id: str
    capabilities: List[str] = field(default_factory=list)
    samples: int = 0
    status: str = NODE_STATUS_ACTIVE
    missed_rounds: int = 0
    last_active_round: int = -1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "capabilities": list(self.capabilities),
            "samples": self.samples,
            "status": self.status,
            "missed_rounds": self.missed_rounds,
            "last_active_round": self.last_active_round,
        }


@dataclass
class DifferentialPrivacy:
    """Optional DP noise mechanism (simulated, math-only).

    Applies Laplace or Gaussian noise to scalar values and tracks the epsilon
    budget. Deterministic when a seed is provided (used by tests).
    """

    epsilon: float = 1.0
    sensitivity: float = 1.0
    mechanism: str = "laplace"  # 'laplace' | 'gaussian'
    delta: float = 1e-5
    max_budget: float = 10.0
    seed: Optional[int] = None
    epsilon_spent: float = 0.0
    _rng: random.Random = field(init=False, repr=False, default_factory=random.Random)

    def __post_init__(self) -> None:
        if self.mechanism not in ("laplace", "gaussian"):
            raise ValueError(f"unknown DP mechanism: {self.mechanism!r}")
        if self.epsilon <= 0:
            raise ValueError("epsilon must be positive")
        self._rng = random.Random(self.seed)

    @property
    def budget_remaining(self) -> float:
        return max(0.0, self.max_budget - self.epsilon_spent)

    def spend(self, epsilon: float) -> None:
        if epsilon <= 0:
            raise ValueError("epsilon spend must be positive")
        if self.epsilon_spent + epsilon > self.max_budget:
            raise PrivacyBudgetExhausted(
                f"budget exceeded: spent={self.epsilon_spent:.4f} "
                f"requested={epsilon:.4f} max={self.max_budget:.4f}"
            )
        self.epsilon_spent += epsilon

    def _laplace_noise(self, scale: float) -> float:
        u = self._rng.random() - 0.5  # uniform(-0.5, 0.5)
        if u == 0.0:
            return 0.0
        return -scale * math.copysign(1.0, u) * math.log(1.0 - 2.0 * abs(u))

    def _gaussian_noise(self, sigma: float) -> float:
        return self._rng.gauss(0.0, sigma)

    def add_noise(self, value: float, epsilon: Optional[float] = None) -> float:
        """Return ``value`` perturbed with DP noise; spends budget."""
        eps = self.epsilon if epsilon is None else epsilon
        self.spend(eps)
        if self.mechanism == "laplace":
            return value + self._laplace_noise(self.sensitivity / eps)
        sigma = self.sensitivity * math.sqrt(2.0 * math.log(1.25 / self.delta)) / eps
        return value + self._gaussian_noise(sigma)


@dataclass
class NodeUpdate:
    """A single node's contribution for one round (simulated local training)."""

    node_id: str
    round_id: int
    weights: Dict[str, float]
    knowledge_updates: List[str] = field(default_factory=list)
    loss: Optional[float] = None
    samples: int = 1
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "round_id": self.round_id,
            "weights": dict(self.weights),
            "knowledge_updates": list(self.knowledge_updates),
            "loss": self.loss,
            "samples": self.samples,
            "timestamp": self.timestamp,
        }


@dataclass
class RoundResult:
    """Outcome of one federated round."""

    round_id: int
    participants: List[str]
    updates_received: int
    unresponsive_nodes: List[str]
    excluded_nodes: List[str]
    aggregated_weights: Dict[str, float]
    aggregated_loss: Optional[float]
    knowledge_updates: List[str]
    global_model_version: int
    converged: bool = False
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "round_id": self.round_id,
            "participants": list(self.participants),
            "updates_received": self.updates_received,
            "unresponsive_nodes": list(self.unresponsive_nodes),
            "excluded_nodes": list(self.excluded_nodes),
            "aggregated_weights": dict(self.aggregated_weights),
            "aggregated_loss": self.aggregated_loss,
            "knowledge_updates": list(self.knowledge_updates),
            "global_model_version": self.global_model_version,
            "converged": self.converged,
            "notes": list(self.notes),
        }


# A train_fn receives (node_id, global_weights) and returns a NodeUpdate or
# None / raises NodeUnresponsiveError to simulate a non-responsive node.
TrainFn = Callable[[str, Dict[str, float]], Optional[NodeUpdate]]


class FederatedOrchestrator:
    """Orchestrates simulated federated training rounds.

    Responsibilities:
    - register / unregister nodes
    - run a federated round: dispatch, collect, aggregate
    - weighted-average aggregation (by sample counts)
    - knowledge-update merging (dedupe, drop excluded nodes' items)
    - node control: missed-round tracking, auto-drop, majority-vote exclusion
    - optional DP noise on aggregated weights
    - convergence monitoring on the loss history
    """

    def __init__(
        self,
        nodes: Optional[Sequence[FederatedNode]] = None,
        dp: Optional[DifferentialPrivacy] = None,
        min_nodes: int = 1,
        max_missed_rounds: int = 2,
        convergence_threshold: float = 1e-3,
        convergence_window: int = 2,
    ) -> None:
        self.nodes: Dict[str, FederatedNode] = {}
        self.dp = dp
        self.min_nodes = min_nodes
        self.max_missed_rounds = max_missed_rounds
        self.convergence_threshold = convergence_threshold
        self.convergence_window = convergence_window
        self.global_weights: Dict[str, float] = {}
        self.global_model_version: int = 0
        self.round_results: List[RoundResult] = []
        self._votes: Dict[str, Dict[str, bool]] = {}  # target -> voter -> accept
        for node in nodes or []:
            self.register_node(node)

    # ------------------------------------------------------------------ nodes
    def register_node(self, node: FederatedNode) -> bool:
        """Register a node; returns False if the node_id already exists."""
        if node.node_id in self.nodes:
            return False
        self.nodes[node.node_id] = node
        return True

    def unregister_node(self, node_id: str) -> bool:
        """Remove a node; returns False if it was not registered."""
        if node_id not in self.nodes:
            return False
        del self.nodes[node_id]
        self._votes.pop(node_id, None)
        for target_votes in self._votes.values():
            target_votes.pop(node_id, None)
        return True

    def get_node(self, node_id: str) -> Optional[FederatedNode]:
        return self.nodes.get(node_id)

    def node_status_summary(self) -> Dict[str, int]:
        summary: Dict[str, int] = {}
        for node in self.nodes.values():
            summary[node.status] = summary.get(node.status, 0) + 1
        return summary

    def eligible_node_ids(self) -> List[str]:
        return sorted(
            nid for nid, n in self.nodes.items() if n.status in _ELIGIBLE_STATUSES
        )

    # ------------------------------------------------------------------ votes
    def cast_vote(self, voter_id: str, target_node_id: str, accept: bool) -> bool:
        """Record a vote about a target node. Only eligible non-target nodes vote."""
        if voter_id not in self.nodes or self.nodes[voter_id].status not in _ELIGIBLE_STATUSES:
            return False
        if target_node_id not in self.nodes or target_node_id == voter_id:
            return False
        self._votes.setdefault(target_node_id, {})[voter_id] = bool(accept)
        return True

    def _resolve_exclusions(self) -> List[str]:
        """Nodes excluded by majority reject votes (strict majority against)."""
        excluded: List[str] = []
        for target, votes in self._votes.items():
            if target not in self.nodes:
                continue
            accept = sum(1 for v in votes.values() if v)
            reject = sum(1 for v in votes.values() if not v)
            if reject > accept:
                excluded.append(target)
        return sorted(excluded)

    def _reset_votes(self) -> None:
        self._votes.clear()

    # ------------------------------------------------------------------ round
    def _aggregate(
        self, updates: List[NodeUpdate]
    ) -> tuple[Dict[str, float], Optional[float]]:
        """Weighted average of weights (by samples); mean of losses."""
        if not updates:
            return {}, None
        keys: set[str] = set()
        for u in updates:
            keys.update(u.weights)
        total_samples = sum(max(u.samples, 0) for u in updates)
        aggregated: Dict[str, float] = {}
        for key in sorted(keys):
            if total_samples > 0:
                weighted = sum(
                    u.weights.get(key, 0.0) * max(u.samples, 0) for u in updates
                )
                aggregated[key] = weighted / total_samples
            else:
                aggregated[key] = sum(u.weights.get(key, 0.0) for u in updates) / len(
                    updates
                )
        losses = [u.loss for u in updates if u.loss is not None]
        mean_loss = sum(losses) / len(losses) if losses else None
        return aggregated, mean_loss

    def _merge_knowledge(self, updates: List[NodeUpdate]) -> List[str]:
        """Dedupe knowledge items across accepted updates, preserving order."""
        seen: set[str] = set()
        merged: List[str] = []
        for u in updates:
            for item in u.knowledge_updates:
                if item not in seen:
                    seen.add(item)
                    merged.append(item)
        return merged

    def _apply_dp(self, weights: Dict[str, float]) -> Dict[str, float]:
        if self.dp is None or not weights:
            return weights
        # Spend budget once per aggregation, not per key.
        self.dp.spend(self.dp.epsilon)
        noisy: Dict[str, float] = {}
        for key in sorted(weights):
            if self.dp.mechanism == "laplace":
                noisy[key] = float(weights[key]) + self.dp._laplace_noise(
                    self.dp.sensitivity / self.dp.epsilon
                )
            else:
                sigma = (
                    self.dp.sensitivity
                    * math.sqrt(2.0 * math.log(1.25 / self.dp.delta))
                    / self.dp.epsilon
                )
                noisy[key] = float(weights[key]) + self.dp._gaussian_noise(sigma)
        return noisy

    def _is_converged(self) -> bool:
        losses = [r.aggregated_loss for r in self.round_results]
        losses = [l for l in losses if l is not None]
        if len(losses) <= self.convergence_window:
            return False
        window = self.convergence_window
        recent = losses[-(window + 1):]
        deltas = [abs(recent[i + 1] - recent[i]) for i in range(len(recent) - 1)]
        return all(d < self.convergence_threshold for d in deltas)

    def run_round(self, train_fn: TrainFn) -> RoundResult:
        """Run one federated round against the registered (simulated) nodes."""
        eligible = self.eligible_node_ids()
        if len(eligible) < self.min_nodes:
            raise InsufficientNodesError(
                f"need >= {self.min_nodes} eligible nodes, have {len(eligible)}"
            )

        excluded = self._resolve_exclusions()
        participants = [nid for nid in eligible if nid not in excluded]
        unresponsive: List[str] = []
        updates: List[NodeUpdate] = []

        for node_id in participants:
            node = self.nodes[node_id]
            if node.status == NODE_STATUS_DROPPED:
                continue  # dropped nodes stay out of rounds
            update: Optional[NodeUpdate] = None
            try:
                update = train_fn(node_id, dict(self.global_weights))
            except NodeUnresponsiveError:
                update = None
            except Exception as exc:  # simulated node fault -> unresponsive
                logger.debug("node %s raised %s", node_id, exc)
                update = None
            if update is None or not isinstance(update, NodeUpdate):
                unresponsive.append(node_id)
                node.missed_rounds += 1
                node.status = NODE_STATUS_UNRESPONSIVE
                if node.missed_rounds >= self.max_missed_rounds:
                    node.status = NODE_STATUS_DROPPED
                    self.round_results  # (no-op; kept for readability)
            else:
                node.missed_rounds = 0
                node.status = NODE_STATUS_ACTIVE
                node.last_active_round = self.global_model_version + 1
                node.samples = max(update.samples, node.samples) or update.samples
                updates.append(update)

        accepted = [u for u in updates if u.node_id not in excluded]
        aggregated, mean_loss = self._aggregate(accepted)
        knowledge = self._merge_knowledge(accepted)
        final_weights = self._apply_dp(aggregated)

        self.global_weights = dict(final_weights)
        self.global_model_version += 1

        result = RoundResult(
            round_id=self.global_model_version,
            participants=participants,
            updates_received=len(accepted),
            unresponsive_nodes=sorted(unresponsive),
            excluded_nodes=excluded,
            aggregated_weights=dict(final_weights),
            aggregated_loss=mean_loss,
            knowledge_updates=knowledge,
            global_model_version=self.global_model_version,
            converged=False,
        )
        # Append first so convergence sees the current round's loss too.
        self.round_results.append(result)
        result.converged = self._is_converged()
        self._reset_votes()
        return result

    def run_training(
        self,
        train_fn: TrainFn,
        max_rounds: int = 10,
        stop_on_convergence: bool = True,
    ) -> List[RoundResult]:
        """Run up to ``max_rounds`` rounds; stop early when converged."""
        results: List[RoundResult] = []
        for _ in range(max_rounds):
            try:
                result = self.run_round(train_fn)
            except InsufficientNodesError:
                break
            results.append(result)
            if stop_on_convergence and result.converged:
                break
        return results

    # ------------------------------------------------------------ convergence
    def monitor_convergence(
        self,
        threshold: Optional[float] = None,
        window: Optional[int] = None,
    ) -> bool:
        """Re-evaluate convergence using the current loss history."""
        if threshold is not None:
            self.convergence_threshold = threshold
        if window is not None:
            self.convergence_window = window
        return self._is_converged()
