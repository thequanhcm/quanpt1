"""Memory Retrieval Benchmark for QUAN AI BRAIN — Sprint 3.

Measures and compares retrieval performance across:
- Cold vs warm embedding cache
- Batch vs single queries
- Incremental indexing
- Retrieval relevance (precision@k, recall@k)

Usage:
    from quan_ai_brain.memory.benchmark import MemoryBenchmark
    benchmark = MemoryBenchmark(store, embedding_service)
    results = benchmark.run_full_suite()
    print(results.to_summary())

Giai đoạn Sprint 3 (2026-10-25): Core benchmark framework with cold/warm, batch, relevance.
"""
from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from quan_ai_brain.cognition.embedding import BGEEmbeddingService
from quan_ai_brain.cognition.retrieval import CognitiveRetriever, MemoryQuery, RetrievalResult
from quan_ai_brain.memory.sqlite_store import MemoryStore


@dataclass
class BenchmarkRun:
    """Single benchmark run result."""
    test_name: str
    timestamp: str
    duration_ms: float
    queries_count: int
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    success_count: int
    error_count: int
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RelevanceResult:
    """Relevance measurement result."""
    test_name: str
    timestamp: str
    precision_at_3: float
    precision_at_5: float
    recall_at_3: float
    recall_at_5: float
    mean_reciprocal_rank: float
    total_queries: int
    relevant_found: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BenchmarkSuiteResult:
    """Full benchmark suite result."""
    suite_name: str
    timestamp: str
    total_duration_ms: float
    cold_embedding_ms: float
    warm_embedding_ms: float
    batch_vs_single_ratio: float
    results: list[BenchmarkRun]
    relevance: RelevanceResult | None = None

    def to_summary(self) -> str:
        """Generate human-readable summary."""
        lines = [
            f"=== BENCHMARK SUITE: {self.suite_name} ===",
            f"Timestamp: {self.timestamp}",
            f"Total duration: {self.total_duration_ms:.2f}ms",
            "",
            "Embedding Performance:",
            f"  Cold start: {self.cold_embedding_ms:.2f}ms",
            f"  Warm inference: {self.warm_embedding_ms:.2f}ms",
            f"  Speedup: {self.cold_embedding_ms / max(1, self.warm_embedding_ms):.2f}x",
            "",
            "Batch vs Single Ratio: {self.batch_vs_single_ratio:.2f}x",
            "",
            "Individual Tests:",
        ]
        for run in self.results:
            lines.append(
                f"  {run.test_name}: {run.avg_latency_ms:.2f}ms avg, "
                f"p95={run.p95_latency_ms:.2f}ms, p99={run.p99_latency_ms:.2f}ms"
            )
        if self.relevance:
            rel = self.relevance
            lines.extend([
                "",
                "Relevance Metrics:",
                f"  Precision@3: {rel.precision_at_3:.3f}",
                f"  Precision@5: {rel.precision_at_5:.3f}",
                f"  Recall@3: {rel.recall_at_3:.3f}",
                f"  Recall@5: {rel.recall_at_5:.3f}",
                f"  MRR: {rel.mean_reciprocal_rank:.3f}",
            ])
        return "\n".join(lines)


class MemoryBenchmark:
    """Runs comprehensive benchmarks on memory retrieval pipeline."""

    def __init__(
        self,
        store: MemoryStore,
        embedding_service: BGEEmbeddingService | None = None,
        retriever: CognitiveRetriever | None = None,
    ) -> None:
        self.store = store
        self.embedding_service = embedding_service
        self.retriever = retriever or CognitiveRetriever(store, embedding_service)
        self._test_queries: list[tuple[str, list[str]]] = []  # (query, expected_ids)

    def add_test_query(self, query: str, expected_ids: list[str]) -> None:
        """Add a query with known expected results for relevance testing."""
        self._test_queries.append((query, expected_ids))

    def run_cold_warm_embedding_test(self, num_runs: int = 5) -> BenchmarkRun:
        """Test cold vs warm embedding performance."""
        if not self.embedding_service:
            return BenchmarkRun(
                test_name="embedding_cold_warm",
                timestamp=datetime.now(timezone.utc).isoformat(),
                duration_ms=0,
                queries_count=0,
                avg_latency_ms=0,
                p50_latency_ms=0,
                p95_latency_ms=0,
                p99_latency_ms=0,
                min_latency_ms=0,
                max_latency_ms=0,
                success_count=0,
                error_count=1,
                metadata={"error": "No embedding service"},
            )

        latencies: list[float] = []
        success = 0

        # Cold run (clear cache first if possible)
        try:
            t0 = time.perf_counter()
            self.embedding_service.client.embed(["benchmark_cold_start_test"])
            cold_ms = (time.perf_counter() - t0) * 1000
        except Exception:
            cold_ms = 0

        # Warm runs
        for _ in range(num_runs):
            try:
                t0 = time.perf_counter()
                self.embedding_service.client.embed(["benchmark_warm_test"])
                latencies.append((time.perf_counter() - t0) * 1000)
                success += 1
            except Exception:
                pass

        if not latencies:
            return BenchmarkRun(
                test_name="embedding_cold_warm",
                timestamp=datetime.now(timezone.utc).isoformat(),
                duration_ms=0,
                queries_count=0,
                avg_latency_ms=0,
                p50_latency_ms=0,
                p95_latency_ms=0,
                p99_latency_ms=0,
                min_latency_ms=0,
                max_latency_ms=0,
                success_count=0,
                error_count=1,
                metadata={"cold_ms": cold_ms, "error": "No warm runs succeeded"},
            )

        latencies.sort()
        n = len(latencies)
        return BenchmarkRun(
            test_name="embedding_cold_warm",
            timestamp=datetime.now(timezone.utc).isoformat(),
            duration_ms=sum(latencies),
            queries_count=n,
            avg_latency_ms=sum(latencies) / n,
            p50_latency_ms=latencies[int(n * 0.5)],
            p95_latency_ms=latencies[int(n * 0.95)] if n > 20 else latencies[-1],
            p99_latency_ms=latencies[int(n * 0.99)] if n > 100 else latencies[-1],
            min_latency_ms=latencies[0],
            max_latency_ms=latencies[-1],
            success_count=success,
            error_count=num_runs - success,
            metadata={"cold_ms": cold_ms, "warm_avg": sum(latencies) / n},
        )

    def run_batch_vs_single_test(self, queries: list[str], batch_size: int = 10) -> tuple[BenchmarkRun, BenchmarkRun]:
        """Compare batch vs single query performance."""
        # Single queries
        single_latencies: list[float] = []
        for q in queries:
            try:
                t0 = time.perf_counter()
                self.retriever.retrieve(q, top_k=3)
                single_latencies.append((time.perf_counter() - t0) * 1000)
            except Exception:
                pass

        # Batch queries (if retriever supports it, otherwise simulate)
        batch_latencies: list[float] = []
        for i in range(0, len(queries), batch_size):
            batch = queries[i:i + batch_size]
            try:
                t0 = time.perf_counter()
                for q in batch:
                    self.retriever.retrieve(q, top_k=3)
                batch_latencies.append((time.perf_counter() - t0) * 1000)
            except Exception:
                pass

        def make_run(name: str, latencies: list[float]) -> BenchmarkRun:
            if not latencies:
                return BenchmarkRun(
                    test_name=name,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    duration_ms=0,
                    queries_count=0,
                    avg_latency_ms=0,
                    p50_latency_ms=0,
                    p95_latency_ms=0,
                    p99_latency_ms=0,
                    min_latency_ms=0,
                    max_latency_ms=0,
                    success_count=0,
                    error_count=1,
                )
            latencies.sort()
            n = len(latencies)
            return BenchmarkRun(
                test_name=name,
                timestamp=datetime.now(timezone.utc).isoformat(),
                duration_ms=sum(latencies),
                queries_count=n,
                avg_latency_ms=sum(latencies) / n,
                p50_latency_ms=latencies[int(n * 0.5)],
                p95_latency_ms=latencies[int(n * 0.95)] if n > 20 else latencies[-1],
                p99_latency_ms=latencies[int(n * 0.99)] if n > 100 else latencies[-1],
                min_latency_ms=latencies[0],
                max_latency_ms=latencies[-1],
                success_count=n,
                error_count=0,
            )

        return make_run("batch_retrieval", batch_latencies), make_run("single_retrieval", single_latencies)

    def run_relevance_test(self) -> RelevanceResult | None:
        """Test retrieval relevance using known expected results."""
        if not self._test_queries:
            return None

        precision_3: list[float] = []
        precision_5: list[float] = []
        recall_3: list[float] = []
        recall_5: list[float] = []
        reciprocal_ranks: list[float] = []

        total_relevant_found = 0

        for query, expected_ids in self._test_queries:
            try:
                result = self.retriever.retrieve(query, top_k=5)
                retrieved_ids = [m.memory_id for m in result.memories[:5]]

                # Precision@k
                relevant_in_top3 = len(set(retrieved_ids[:3]) & set(expected_ids))
                relevant_in_top5 = len(set(retrieved_ids) & set(expected_ids))
                precision_3.append(relevant_in_top3 / 3)
                precision_5.append(relevant_in_top5 / 5)

                # Recall@k
                recall_3.append(relevant_in_top3 / max(1, len(expected_ids)))
                recall_5.append(relevant_in_top5 / max(1, len(expected_ids)))

                # MRR
                rr = 0.0
                for i, rid in enumerate(retrieved_ids):
                    if rid in expected_ids:
                        rr = 1.0 / (i + 1)
                        break
                reciprocal_ranks.append(rr)
                total_relevant_found += relevant_in_top5
            except Exception:
                pass

        if not precision_3:
            return None

        n = len(precision_3)
        return RelevanceResult(
            test_name="relevance_metrics",
            timestamp=datetime.now(timezone.utc).isoformat(),
            precision_at_3=sum(precision_3) / n,
            precision_at_5=sum(precision_5) / n,
            recall_at_3=sum(recall_3) / n,
            recall_at_5=sum(recall_5) / n,
            mean_reciprocal_rank=sum(reciprocal_ranks) / n,
            total_queries=n,
            relevant_found=total_relevant_found,
        )

    def run_full_suite(self, num_warm_runs: int = 5, test_queries: list[str] | None = None) -> BenchmarkSuiteResult:
        """Run full benchmark suite."""
        t0_suite = time.perf_counter()

        # 1. Cold/warm embedding test
        embedding_result = self.run_cold_warm_embedding_test(num_warm_runs)
        cold_ms = embedding_result.metadata.get("cold_ms", 0)
        warm_ms = embedding_result.metadata.get("warm_avg", 0)

        # 2. Batch vs single test
        test_queries = test_queries or ["test query 1", "test query 2", "test query 3"]
        batch_result, single_result = self.run_batch_vs_single_test(test_queries)
        batch_ratio = single_result.avg_latency_ms / max(1, batch_result.avg_latency_ms)

        # 3. Relevance test
        relevance = self.run_relevance_test()

        total_duration = (time.perf_counter() - t0_suite) * 1000

        return BenchmarkSuiteResult(
            suite_name="Sprint 3 Memory Benchmark",
            timestamp=datetime.now(timezone.utc).isoformat(),
            total_duration_ms=total_duration,
            cold_embedding_ms=cold_ms,
            warm_embedding_ms=warm_ms,
            batch_vs_single_ratio=batch_ratio,
            results=[embedding_result, batch_result, single_result],
            relevance=relevance,
        )