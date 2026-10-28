"""
Performance Optimizer Module (V23.4)

Analyzes a simple call-graph profile (stdlib dict input) and proposes
optimizations: batching, caching, parallelization — with estimated speedups.

SIMULATED COMPONENTS:
- Analysis is entirely heuristic/mathematical (Amdahl-style speedup model) on
  caller-supplied profile dicts. Nothing is executed, timed, or profiled for
  real; "estimated speedup" is a model number, not a benchmark.

Version: V23.4
Author: QUAN AI BRAIN Team
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

OPT_BATCH = "batch"
OPT_CACHE = "cache"
OPT_PARALLEL = "parallel"
OPT_ALGORITHM = "algorithm"


class ProfileError(ValueError):
    """Raised when a profile dict is malformed."""


@dataclass
class CallNode:
    """One function in the profile: self/total time and call counts."""

    name: str
    total_time_ms: float
    self_time_ms: float
    call_count: int
    callers: List[str] = field(default_factory=list)
    callees: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "total_time_ms": self.total_time_ms,
            "self_time_ms": self.self_time_ms,
            "call_count": self.call_count,
            "callers": list(self.callers),
            "callees": list(self.callees),
            "metadata": dict(self.metadata),
        }


@dataclass
class Recommendation:
    """A single optimization recommendation with estimated speedup."""

    rec_id: str
    kind: str  # batch | cache | parallel | algorithm
    target: str
    description: str
    estimated_speedup: float  # e.g. 3.2 => ~3.2x faster for the target
    estimated_time_saved_ms: float
    confidence: float  # 0..1 heuristic confidence
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rec_id": self.rec_id,
            "kind": self.kind,
            "target": self.target,
            "description": self.description,
            "estimated_speedup": self.estimated_speedup,
            "estimated_time_saved_ms": self.estimated_time_saved_ms,
            "confidence": self.confidence,
            "details": dict(self.details),
        }


@dataclass
class OptimizationReport:
    """Full result of one profile analysis."""

    total_time_ms: float
    hotspots: List[str]
    recommendations: List[Recommendation]
    estimated_total_speedup: float
    estimated_total_time_saved_ms: float
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_time_ms": self.total_time_ms,
            "hotspots": list(self.hotspots),
            "recommendations": [r.to_dict() for r in self.recommendations],
            "estimated_total_speedup": self.estimated_total_speedup,
            "estimated_total_time_saved_ms": self.estimated_total_time_saved_ms,
            "notes": list(self.notes),
        }


def _amdahl_speedup(fraction: float, factor: float) -> float:
    """Amdahl's law: overall speedup when ``fraction`` of time gets ``factor``-x faster."""
    if factor <= 1.0 or fraction <= 0.0:
        return 1.0
    fraction = min(fraction, 1.0)
    return 1.0 / ((1.0 - fraction) + fraction / factor)


class PerformanceOptimizer:
    """Heuristic optimizer over a simple call-graph profile.

    Expected profile shape::

        {
          "functions": {
              "fetch_user": {"total_ms": 500.0, "self_ms": 120.0,
                             "calls": 100, "callers": ["main"],
                             "callees": ["db_query"], "io_bound": True,
                             "distinct_keys_per_call": 100},
              ...
          }
        }

    Heuristics:
    - high call count + repeated same-key reads -> cache
    - many small calls to the same callee (N distinct keys) -> batch
    - io_bound callees called independently from one parent -> parallel
    - deep pure-compute recursion / repeated math -> algorithm
    """

    def __init__(
        self,
        cache_hit_rate: float = 0.9,
        batch_speedup_per_fanin: float = 0.10,
        max_batch_speedup: float = 8.0,
        default_workers: int = 4,
        hotspot_fraction: float = 0.8,
    ) -> None:
        if not 0.0 < cache_hit_rate < 1.0:
            raise ValueError("cache_hit_rate must be in (0, 1)")
        self.cache_hit_rate = cache_hit_rate
        self.batch_speedup_per_fanin = batch_speedup_per_fanin
        self.max_batch_speedup = max_batch_speedup
        self.default_workers = default_workers
        self.hotspot_fraction = hotspot_fraction

    # ----------------------------------------------------------------- parse
    def _parse(self, profile: Dict[str, Any]) -> Dict[str, CallNode]:
        functions = profile.get("functions")
        if not isinstance(functions, dict) or not functions:
            raise ProfileError("profile must contain a non-empty 'functions' dict")
        nodes: Dict[str, CallNode] = {}
        for name, spec in functions.items():
            if not isinstance(spec, dict):
                raise ProfileError(f"function spec for {name!r} must be a dict")
            try:
                total = float(spec.get("total_ms", spec.get("total_time_ms", 0.0)))
                self_ms = float(spec.get("self_ms", spec.get("self_time_ms", 0.0)))
                calls = int(spec.get("calls", spec.get("call_count", 0)))
            except (TypeError, ValueError) as exc:
                raise ProfileError(f"bad numeric fields for {name!r}: {exc}") from exc
            if total < 0 or self_ms < 0 or calls < 0:
                raise ProfileError(f"negative timings for {name!r}")
            nodes[name] = CallNode(
                name=name,
                total_time_ms=total,
                self_time_ms=self_ms,
                call_count=calls,
                callers=list(spec.get("callers", []) or []),
                callees=list(spec.get("callees", []) or []),
                metadata={
                    k: v
                    for k, v in spec.items()
                    if k
                    not in (
                        "total_ms",
                        "self_ms",
                        "calls",
                        "total_time_ms",
                        "self_time_ms",
                        "call_count",
                        "callers",
                        "callees",
                    )
                },
            )
        return nodes

    # -------------------------------------------------------------- hotspots
    def find_hotspots(
        self, profile: Dict[str, Any], top_n: int = 5
    ) -> List[str]:
        """Functions sorted by total time, covering ~hotspot_fraction of runtime."""
        nodes = self._parse(profile)
        ordered = sorted(
            nodes.values(), key=lambda n: n.total_time_ms, reverse=True
        )
        total = sum(n.total_time_ms for n in nodes.values())
        if total <= 0:
            return []
        hotspots: List[str] = []
        acc = 0.0
        for node in ordered:
            hotspots.append(node.name)
            acc += node.total_time_ms
            if total > 0 and acc / total >= self.hotspot_fraction:
                break
        return hotspots[: max(top_n, len(hotspots))] if hotspots else []

    # -------------------------------------------------------- recommendations
    def _rec_cache(self, node: CallNode, total_time: float) -> Optional[Recommendation]:
        """Repeated reads of the same key(s) -> cache."""
        repeated = node.call_count > 10 and node.metadata.get("io_bound")
        if not repeated:
            return None
        factor = 1.0 / (1.0 - self.cache_hit_rate)  # effective read amplification
        speedup = _amdahl_speedup(
            node.total_time_ms / total_time if total_time > 0 else 0.0, factor
        )
        saved = node.total_time_ms * (1.0 - self.cache_hit_rate)
        return Recommendation(
            rec_id=f"cache:{node.name}",
            kind=OPT_CACHE,
            target=node.name,
            description=(
                f"Cache repeated I/O reads in '{node.name}' "
                f"({node.call_count} calls, hit-rate ~{self.cache_hit_rate:.0%})"
            ),
            estimated_speedup=round(speedup, 3),
            estimated_time_saved_ms=round(saved, 3),
            confidence=0.7,
            details={
                "call_count": node.call_count,
                "cache_hit_rate": self.cache_hit_rate,
            },
        )

    def _rec_batch(self, node: CallNode, total_time: float) -> Optional[Recommendation]:
        """Many small same-callee calls with distinct keys -> batch them."""
        distinct = node.metadata.get("distinct_keys_per_call")
        small_calls = node.call_count >= 10 and node.total_time_ms / max(
            node.call_count, 1
        ) < 5.0  # per-call cost under 5ms -> batching wins
        if not (small_calls and distinct and distinct >= 10):
            return None
        factor = 1.0 + min(
            self.batch_speedup_per_fanin * math.log2(distinct),
            self.max_batch_speedup - 1.0,
        )
        speedup = _amdahl_speedup(
            node.total_time_ms / total_time if total_time > 0 else 0.0, factor
        )
        saved = node.total_time_ms * (1.0 - 1.0 / factor)
        return Recommendation(
            rec_id=f"batch:{node.name}",
            kind=OPT_BATCH,
            target=node.name,
            description=(
                f"Batch '{node.name}' calls: {node.call_count} calls x "
                f"{distinct} distinct keys; round-trips dominate per-call cost"
            ),
            estimated_speedup=round(speedup, 3),
            estimated_time_saved_ms=round(saved, 3),
            confidence=0.65,
            details={
                "call_count": node.call_count,
                "distinct_keys_per_call": distinct,
                "batch_factor": round(factor, 3),
            },
        )

    def _rec_parallel(
        self, profile: Dict[str, Any], node: CallNode, total_time: float
    ) -> Optional[Recommendation]:
        """Parent with several io_bound callees -> run them in parallel."""
        io_callees = [
            callee
            for callee in node.callees
            if callee in profile.get("functions", {})
            and profile["functions"][callee].get("io_bound")
        ]
        if len(io_callees) < 2:
            return None
        # Sum of io_bound callees' self time is parallelizable
        io_self = sum(
            float(profile["functions"][c].get("self_ms", 0.0)) for c in io_callees
        )
        workers = min(len(io_callees), self.default_workers)
        factor = float(workers)
        fraction = io_self / total_time if total_time > 0 else 0.0
        speedup = _amdahl_speedup(fraction, factor)
        saved = io_self * (1.0 - 1.0 / factor)
        return Recommendation(
            rec_id=f"parallel:{node.name}",
            kind=OPT_PARALLEL,
            target=node.name,
            description=(
                f"Parallelize '{node.name}': {len(io_callees)} independent I/O "
                f"callees ({', '.join(io_callees)}) with {workers} workers"
            ),
            estimated_speedup=round(speedup, 3),
            estimated_time_saved_ms=round(saved, 3),
            confidence=0.6,
            details={
                "io_callees": io_callees,
                "workers": workers,
                "parallel_fraction": round(fraction, 4),
            },
        )

    def analyze(self, profile: Dict[str, Any]) -> OptimizationReport:
        """Analyze a profile and produce recommendations + estimated speedup."""
        nodes = self._parse(profile)
        total_time = sum(n.total_time_ms for n in nodes.values())
        if total_time <= 0:
            return OptimizationReport(
                total_time_ms=0.0,
                hotspots=[],
                recommendations=[],
                estimated_total_speedup=1.0,
                estimated_total_time_saved_ms=0.0,
                notes=["profile has zero total time; nothing to optimize"],
            )

        recs: List[Recommendation] = []
        for node in nodes.values():
            for candidate in (
                self._rec_cache(node, total_time),
                self._rec_batch(node, total_time),
                self._rec_parallel(profile, node, total_time),
            ):
                if candidate is not None:
                    recs.append(candidate)

        # Dedupe by rec_id, keep highest time-saved
        best: Dict[str, Recommendation] = {}
        for rec in recs:
            existing = best.get(rec.rec_id)
            if existing is None or rec.estimated_time_saved_ms > existing.estimated_time_saved_ms:
                best[rec.rec_id] = rec
        recs = sorted(
            best.values(),
            key=lambda r: r.estimated_time_saved_ms,
            reverse=True,
        )

        # Combined Amdahl speedup over disjoint saved-time fractions
        saved = sum(r.estimated_time_saved_ms for r in recs)
        fraction = min(saved / total_time, 1.0)
        if recs:
            # Use the best single-rec factor as the applied factor
            factor = max(r.estimated_speedup for r in recs)
        else:
            factor = 1.0
        total_speedup = _amdahl_speedup(fraction, factor) if factor > 1.0 else 1.0
        total_saved = min(saved, total_time)

        return OptimizationReport(
            total_time_ms=round(total_time, 3),
            hotspots=self.find_hotspots(profile),
            recommendations=recs,
            estimated_total_speedup=round(total_speedup, 3),
            estimated_total_time_saved_ms=round(total_saved, 3),
            notes=[
                "Speedups are heuristic Amdahl-style estimates on simulated "
                "profile data, not measured benchmarks."
            ],
        )

    def recommend(self, profile: Dict[str, Any], top_n: int = 5) -> List[Recommendation]:
        """Return the top-N recommendations only."""
        return self.analyze(profile).recommendations[:top_n]

    # --------------------------------------------------- what-if speedup calc
    def estimate_speedup(
        self, baseline_ms: float, optimized_fraction: float, factor: float
    ) -> float:
        """Public Amdahl helper: overall speedup for a what-if scenario."""
        return round(_amdahl_speedup(optimized_fraction, factor), 3)
