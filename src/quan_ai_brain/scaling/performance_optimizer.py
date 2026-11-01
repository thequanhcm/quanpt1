"""
Performance Optimizer Module (V30.2) — SIMULATED, in-process only.

Provides:
- QueryOptimizer: analyze pseudo query plans (list of ops with costs)
- Index recommender (frequently filtered fields)
- Cache advisor (hit-rate -> L1/L2 recommendation)
- Sharding key suggester (hash / cardinality based)
- N+1 query detector (repeated query patterns inside loops)

SIMULATION SCOPE (per V30 plan constraints):
- No real database, no EXPLAIN, no Redis/CDN.
- Plans are plain lists of ops; all analysis is in-process heuristics.

Version: V30.2
"""

import hashlib
import logging
from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence

logger = logging.getLogger(__name__)


class OpType(Enum):
    """Pseudo query-plan operators."""
    SEQ_SCAN = "seq_scan"
    INDEX_SCAN = "index_scan"
    HASH_JOIN = "hash_join"
    NESTED_LOOP = "nested_loop"
    SORT = "sort"
    FILTER = "filter"
    AGGREGATE = "aggregate"
    LIMIT = "limit"


class CacheLevel(Enum):
    """Cache levels recommended by the cache advisor."""
    NONE = "none"
    L1 = "l1"   # in-process, tiny, fastest
    L2 = "l2"   # shared cache layer
    L1_L2 = "l1_l2"  # both layers


@dataclass
class PlanOp:
    """One operator in a pseudo query plan."""
    op_type: OpType
    table: str
    cost: float
    rows: int = 0
    filter_fields: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "op_type": self.op_type.value,
            "table": self.table,
            "cost": self.cost,
            "rows": self.rows,
            "filter_fields": list(self.filter_fields),
        }


@dataclass
class QueryPlan:
    """A pseudo query plan: ordered list of ops."""
    query_id: str
    ops: List[PlanOp]

    @property
    def total_cost(self) -> float:
        return sum(op.cost for op in self.ops)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query_id": self.query_id,
            "ops": [op.to_dict() for op in self.ops],
            "total_cost": self.total_cost,
        }


@dataclass
class IndexSuggestion:
    """Recommended index."""
    table: str
    fields: List[str]
    reason: str
    estimated_benefit: float  # 0..1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "table": self.table,
            "fields": list(self.fields),
            "reason": self.reason,
            "estimated_benefit": self.estimated_benefit,
        }


@dataclass
class CacheRecommendation:
    """Cache advisor output."""
    key: str
    level: CacheLevel
    hit_rate: float
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "level": self.level.value,
            "hit_rate": self.hit_rate,
            "reason": self.reason,
        }


@dataclass
class ShardingSuggestion:
    """Sharding key suggestion."""
    table: str
    key_field: str
    method: str  # 'hash' or 'range'
    cardinality: int
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "table": self.table,
            "key_field": self.key_field,
            "method": self.method,
            "cardinality": self.cardinality,
            "reason": self.reason,
        }


@dataclass
class NPlus1Finding:
    """A detected N+1 pattern."""
    query_pattern: str
    repetitions: int
    table: str
    severity: str  # 'low' | 'medium' | 'high'
    suggestion: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query_pattern": self.query_pattern,
            "repetitions": self.repetitions,
            "table": self.table,
            "severity": self.severity,
            "suggestion": self.suggestion,
        }


@dataclass
class OptimizationReport:
    """Full optimizer output for one plan."""
    query_id: str
    total_cost: float
    expensive_ops: List[PlanOp]
    index_suggestions: List[IndexSuggestion]
    cache_recommendation: CacheRecommendation
    sharding_suggestion: Optional[ShardingSuggestion]
    n_plus_1_findings: List[NPlus1Finding]
    verdict: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query_id": self.query_id,
            "total_cost": self.total_cost,
            "expensive_ops": [op.to_dict() for op in self.expensive_ops],
            "index_suggestions": [s.to_dict() for s in self.index_suggestions],
            "cache_recommendation": self.cache_recommendation.to_dict(),
            "sharding_suggestion": (self.sharding_suggestion.to_dict()
                                    if self.sharding_suggestion else None),
            "n_plus_1_findings": [f.to_dict() for f in self.n_plus_1_findings],
            "verdict": self.verdict,
        }


def sharding_reason(table: str, key_field: str, method: str, cardinality: int) -> str:
    """Human-readable justification for a sharding key choice."""
    if method == "hash":
        return (f"field '{key_field}' on '{table}' has high cardinality "
                f"({cardinality}); hash distributes rows evenly")
    return (f"field '{key_field}' on '{table}' has ordered, moderate cardinality "
            f"({cardinality}); range sharding keeps locality")


class QueryOptimizer:
    """Heuristic optimizer over pseudo query plans (stdlib-only simulation)."""

    EXPENSIVE_OPS = {OpType.SEQ_SCAN, OpType.NESTED_LOOP, OpType.SORT}
    # ops whose filter_fields benefit from an index
    INDEXABLE_OPS = {OpType.SEQ_SCAN, OpType.FILTER}
    MIN_FILTER_COUNT_FOR_INDEX = 2

    def __init__(
        self,
        cost_threshold: float = 100.0,
        filter_field_threshold: int = 3,
        cache_hit_l1: float = 0.8,
        cache_hit_l2: float = 0.5,
        n_plus_1_threshold: int = 3,
        sharding_cardinality_threshold: int = 100,
    ) -> None:
        self.cost_threshold = cost_threshold
        self.filter_field_threshold = filter_field_threshold
        self.cache_hit_l1 = cache_hit_l1
        self.cache_hit_l2 = cache_hit_l2
        self.n_plus_1_threshold = n_plus_1_threshold
        self.sharding_cardinality_threshold = sharding_cardinality_threshold

    # ---------------- plan analysis ----------------

    def analyze_plan(self, plan: QueryPlan) -> OptimizationReport:
        total = plan.total_cost
        expensive = [op for op in plan.ops
                     if op.cost >= self.cost_threshold and op.op_type in self.EXPENSIVE_OPS]
        index_sugg = self.suggest_indexes(plan)
        cache_rec = self.cache_advisor(plan.query_id, plan.total_cost)
        n_plus_1 = self.detect_n_plus_1([plan])
        sharding = None
        if plan.ops:
            # suggest on the biggest table touched
            table = max((op.table for op in plan.ops), key=lambda t: sum(
                o.rows for o in plan.ops if o.table == t))
            rows = sum(o.rows for o in plan.ops if o.table == table)
            if rows > 0:
                sharding = self.suggest_sharding_key(
                    table=table,
                    field_stats={
                        "id": rows * 10,
                        f"{table.split('.')[-1]}_id": max(1, rows // 2),
                    },
                )
        if total >= 10 * self.cost_threshold:
            verdict = "critical"
        elif total >= self.cost_threshold:
            verdict = "needs_optimization"
        else:
            verdict = "healthy"
        return OptimizationReport(
            query_id=plan.query_id,
            total_cost=total,
            expensive_ops=expensive,
            index_suggestions=index_sugg,
            cache_recommendation=cache_rec,
            sharding_suggestion=sharding,
            n_plus_1_findings=n_plus_1,
            verdict=verdict,
        )

    # ---------------- index recommender ----------------

    def suggest_indexes(self, plan: QueryPlan) -> List[IndexSuggestion]:
        """Suggest indexes on frequently filtered fields."""
        field_counts: Counter = Counter()
        for op in plan.ops:
            if op.op_type in self.INDEXABLE_OPS:
                for f in op.filter_fields:
                    field_counts[(op.table, f)] += 1
        suggestions = []
        for (table, f), count in sorted(field_counts.items(), key=lambda kv: -kv[1]):
            if count >= self.MIN_FILTER_COUNT_FOR_INDEX:
                benefit = min(1.0, count / 10.0)
                suggestions.append(IndexSuggestion(
                    table=table,
                    fields=[f],
                    reason=f"field '{f}' on '{table}' filtered in {count} scan/filter ops",
                    estimated_benefit=benefit,
                ))
        return suggestions

    def suggest_indexes_from_plans(self, plans: Sequence[QueryPlan]) -> List[IndexSuggestion]:
        """Aggregate filter-field frequency across multiple plans."""
        merged = QueryPlan(query_id="__merged__", ops=[op for p in plans for op in p.ops])
        return self.suggest_indexes(merged)

    # ---------------- cache advisor ----------------

    def cache_advisor(self, key: str, cost: float, hit_rate: Optional[float] = None) -> CacheRecommendation:
        """
        Recommend cache level from hit rate (and cost as tie-breaker).
        - hit_rate >= l1_threshold  -> L1
        - l2_threshold <= hit < l1  -> L2
        - below l2                  -> L2 if query is expensive, else NONE
        """
        hr = hit_rate if hit_rate is not None else 0.0
        if hr >= self.cache_hit_l1:
            level = CacheLevel.L1
            reason = f"hit rate {hr:.2f} >= {self.cache_hit_l1} → serve from in-process L1"
        elif hr >= self.cache_hit_l2:
            level = CacheLevel.L2
            reason = f"hit rate {hr:.2f} >= {self.cache_hit_l2} → shared L2 cache"
        else:
            if cost >= self.cost_threshold:
                level = CacheLevel.L2
                reason = f"low hit rate {hr:.2f} but expensive query (cost {cost}) → L2"
            else:
                level = CacheLevel.NONE
                reason = f"low hit rate {hr:.2f} and cheap query (cost {cost}) → skip cache"
        return CacheRecommendation(key=key, level=level, hit_rate=hr, reason=reason)

    # ---------------- sharding suggester ----------------

    def suggest_sharding_key(
        self,
        table: str,
        field_stats: Dict[str, int],
    ) -> Optional[ShardingSuggestion]:
        """
        field_stats: field -> observed distinct values (cardinality).
        - highest-cardinality field wins, method='hash'
        - if no field has enough cardinality, no suggestion (None)
        """
        if not field_stats:
            return None
        best = max(field_stats.items(), key=lambda kv: kv[1])
        field_name, card = best
        if card < self.sharding_cardinality_threshold:
            return None
        method = "hash" if card >= self.sharding_cardinality_threshold * 2 else "range"
        return ShardingSuggestion(
            table=table,
            key_field=field_name,
            method=method,
            cardinality=card,
            reason=sharding_reason(table, field_name, method, card),
        )

    # ---------------- N+1 detector ----------------

    def detect_n_plus_1(self, plans: Sequence[QueryPlan]) -> List[NPlus1Finding]:
        """
        Detect repeated identical query patterns (N+1 anti-pattern).
        Normalizes each plan to a pattern signature (ops + tables).
        """
        sig_counts: Counter = Counter()
        sig_tables: Dict[str, str] = {}
        for plan in plans:
            sig = self._signature(plan)
            sig_counts[sig] += 1
            if sig not in sig_tables and plan.ops:
                sig_tables[sig] = plan.ops[0].table
        findings = []
        for sig, count in sig_counts.items():
            if count >= self.n_plus_1_threshold:
                findings.append(NPlus1Finding(
                    query_pattern=sig,
                    repetitions=count,
                    table=sig_tables.get(sig, "?"),
                    severity="high" if count >= 10 else "medium",
                    suggestion="batch the loop into a single IN-query or prefetch",
                ))
        return sorted(findings, key=lambda f: -f.repetitions)

    @staticmethod
    def _signature(plan: QueryPlan) -> str:
        parts = [f"{op.op_type.value}:{op.table}" for op in plan.ops]
        raw = "|".join(parts)
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]

    def optimize(self, plan: QueryPlan) -> OptimizationReport:
        return self.analyze_plan(plan)
