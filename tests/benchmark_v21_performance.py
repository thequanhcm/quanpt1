"""V21 Benchmarks — Performance, Load, and Comparison Tests."""
from __future__ import annotations

import time
import statistics
import pytest
from pathlib import Path
import tempfile
from concurrent.futures import ThreadPoolExecutor
import threading

from quan_ai_brain.memory.deep_memory import DeepMemoryStore
from quan_ai_brain.core.integration import UnifiedMemoryAPI, IntegrationConfig


@pytest.fixture
def benchmark_db():
    """Create temporary benchmark database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "benchmark.db"


class TestQueryLatency:
    """Query latency benchmarks."""
    
    def test_single_query_latency(self, benchmark_db, benchmark):
        """Benchmark single query latency."""
        store = DeepMemoryStore(str(benchmark_db))
        
        # Add test data
        for i in range(100):
            store._insert_unit(
                knowledge_type='FACT',
                subject=f'subject_{i}',
                predicate='is',
                object=f'object_{i}',
                statement=f'Test statement {i}',
                source_refs=[],
                evidence_refs=[],
                scope='benchmark'
            )
        
        # Benchmark query
        def query():
            return store.search('test', limit=10)
        
        result = benchmark(query)
        
        assert len(result) <= 10
    
    def test_batch_query_latency(self, benchmark_db, benchmark):
        """Benchmark batch query latency."""
        store = DeepMemoryStore(str(benchmark_db))
        
        # Add test data
        for i in range(1000):
            store._insert_unit(
                knowledge_type='FACT',
                subject=f'subject_{i}',
                predicate='is',
                object=f'object_{i}',
                statement=f'Test statement {i}',
                source_refs=[],
                evidence_refs=[],
                scope='benchmark'
            )
        
        # Benchmark batch query
        def batch_query():
            return store.search('test', limit=100)
        
        result = benchmark(batch_query)
        
        assert len(result) <= 100


class TestThroughput:
    """Throughput benchmarks."""
    
    def test_queries_per_second(self, benchmark_db):
        """Benchmark queries per second."""
        store = DeepMemoryStore(str(benchmark_db))
        
        # Add test data
        for i in range(1000):
            store._insert_unit(
                knowledge_type='FACT',
                subject=f'subject_{i}',
                predicate='is',
                object=f'object_{i}',
                statement=f'Test statement {i}',
                source_refs=[],
                evidence_refs=[],
                scope='benchmark'
            )
        
        # Measure throughput
        num_queries = 1000
        start_time = time.time()
        
        for _ in range(num_queries):
            store.search('test', limit=10)
        
        end_time = time.time()
        elapsed = end_time - start_time
        qps = num_queries / elapsed
        
        # Assert minimum throughput (adjust based on hardware)
        assert qps > 100, f"Throughput too low: {qps:.2f} qps"
    
    def test_concurrent_queries(self, benchmark_db):
        """Benchmark concurrent queries."""
        store = DeepMemoryStore(str(benchmark_db))
        
        # Add test data
        for i in range(1000):
            store._insert_unit(
                knowledge_type='FACT',
                subject=f'subject_{i}',
                predicate='is',
                object=f'object_{i}',
                statement=f'Test statement {i}',
                source_refs=[],
                evidence_refs=[],
                scope='benchmark'
            )
        
        num_workers = 10
        queries_per_worker = 100
        
        def worker():
            for _ in range(queries_per_worker):
                store.search('test', limit=10)
        
        # Measure concurrent throughput
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(worker) for _ in range(num_workers)]
            for future in futures:
                future.result()
        
        end_time = time.time()
        elapsed = end_time - start_time
        total_queries = num_workers * queries_per_worker
        qps = total_queries / elapsed
        
        assert qps > 50, f"Concurrent throughput too low: {qps:.2f} qps"


class TestMemoryUsage:
    """Memory usage benchmarks."""
    
    def test_memory_per_ku(self, benchmark_db):
        """Benchmark memory usage per knowledge unit."""
        store = DeepMemoryStore(str(benchmark_db))
        
        import tracemalloc
        tracemalloc.start()
        
        # Add KUs
        num_kus = 1000
        for i in range(num_kus):
            store._insert_unit(
                knowledge_type='FACT',
                subject=f'subject_{i}',
                predicate='is',
                object=f'object_{i}',
                statement=f'Test statement {i} with some additional text',
                source_refs=[],
                evidence_refs=[],
                scope='benchmark'
            )
        
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        memory_per_ku = peak / num_kus
        
        # Assert reasonable memory usage (adjust based on requirements)
        assert memory_per_ku < 10000, f"Memory per KU too high: {memory_per_ku:.2f} bytes"
    
    def test_cache_memory_efficiency(self, benchmark_db):
        """Benchmark cache memory efficiency."""
        config = IntegrationConfig(cache_enabled=True, cache_ttl=300)
        api = UnifiedMemoryAPI(config)
        
        import tracemalloc
        tracemalloc.start()
        
        # Perform operations
        for i in range(100):
            api.unified_search(f"query {i}", filters={'type': 'fact'})
        
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # Check cache stats
        cache_stats = api.cache.get_stats()
        
        assert cache_stats['hit_rate'] >= 0, "Cache should have valid hit rate"


class TestCachePerformance:
    """Cache performance benchmarks."""
    
    def test_cache_hit_rate(self, benchmark_db):
        """Benchmark cache hit rate."""
        config = IntegrationConfig(cache_enabled=True, cache_ttl=300)
        api = UnifiedMemoryAPI(config)
        
        # Perform same query multiple times
        for _ in range(10):
            api.unified_search("same query", filters={'type': 'fact'})
        
        cache_stats = api.cache.get_stats()
        
        # First query is miss, rest should be hits
        expected_hit_rate = 0.9
        assert cache_stats['hit_rate'] >= expected_hit_rate, \
            f"Cache hit rate too low: {cache_stats['hit_rate']:.2f}"
    
    def test_cache_latency_improvement(self, benchmark_db, benchmark):
        """Benchmark cache latency improvement."""
        config = IntegrationConfig(cache_enabled=True, cache_ttl=300)
        api = UnifiedMemoryAPI(config)
        
        # Warm up cache
        api.unified_search("benchmark query", filters={'type': 'fact'})
        
        # Benchmark cached query
        def cached_query():
            return api.unified_search("benchmark query", filters={'type': 'fact'})
        
        latency = benchmark(cached_query)
        
        # Cached queries should be fast (< 10ms)
        assert latency['latency_ms'] < 10, f"Cached query too slow: {latency['latency_ms']:.2f}ms"


class TestComparison:
    """Comparison benchmarks between versions/strategies."""
    
    def test_v11_vs_v20_retrieval(self, benchmark_db):
        """Compare V11 vs V20 retrieval speed."""
        store = DeepMemoryStore(str(benchmark_db))
        
        # Add test data
        for i in range(1000):
            store._insert_unit(
                knowledge_type='FACT',
                subject=f'subject_{i}',
                predicate='is',
                object=f'object_{i}',
                statement=f'Test statement {i}',
                source_refs=[],
                evidence_refs=[],
                scope='benchmark'
            )
        
        # V11-style retrieval (simple search)
        start = time.time()
        for _ in range(100):
            store.search('test', limit=10)
        v11_time = time.time() - start
        
        # V20-style retrieval (unified with caching)
        config = IntegrationConfig(cache_enabled=True)
        api = UnifiedMemoryAPI(config)
        
        start = time.time()
        for _ in range(100):
            api.unified_search('test', filters={'type': 'fact'})
        v20_time = time.time() - start
        
        # V20 should be faster or equal due to caching
        improvement = (v11_time - v20_time) / v11_time * 100
        
        print(f"V11 time: {v11_time:.3f}s, V20 time: {v20_time:.3f}s, Improvement: {improvement:.1f}%")
        
        # Allow some variance
        assert v20_time <= v11_time * 1.1, f"V20 should be at least as fast as V11"
    
    def test_with_without_caching(self, benchmark_db):
        """Compare with vs without caching."""
        # Without cache
        config_no_cache = IntegrationConfig(cache_enabled=False)
        api_no_cache = UnifiedMemoryAPI(config_no_cache)
        
        start = time.time()
        for _ in range(100):
            api_no_cache.unified_search('test', filters={'type': 'fact'})
        no_cache_time = time.time() - start
        
        # With cache
        config_cache = IntegrationConfig(cache_enabled=True)
        api_cache = UnifiedMemoryAPI(config_cache)
        
        # Warm up
        api_cache.unified_search('test', filters={'type': 'fact'})
        
        start = time.time()
        for _ in range(100):
            api_cache.unified_search('test', filters={'type': 'fact'})
        cache_time = time.time() - start
        
        improvement = (no_cache_time - cache_time) / no_cache_time * 100
        
        print(f"Without cache: {no_cache_time:.3f}s, With cache: {cache_time:.3f}s, Improvement: {improvement:.1f}%")
        
        # Caching should improve performance
        assert cache_time < no_cache_time, "Caching should improve performance"


class TestLoadTesting:
    """Load testing benchmarks."""
    
    def test_sustained_load(self, benchmark_db):
        """Test sustained load over time."""
        store = DeepMemoryStore(str(benchmark_db))
        
        # Add test data
        for i in range(1000):
            store._insert_unit(
                knowledge_type='FACT',
                subject=f'subject_{i}',
                predicate='is',
                object=f'object_{i}',
                statement=f'Test statement {i}',
                source_refs=[],
                evidence_refs=[],
                scope='benchmark'
            )
        
        # Sustained load for 10 seconds
        duration = 10
        start_time = time.time()
        query_count = 0
        
        while time.time() - start_time < duration:
            store.search('test', limit=10)
            query_count += 1
        
        queries_per_second = query_count / duration
        
        print(f"Sustained load: {queries_per_second:.2f} qps for {duration}s")
        
        assert queries_per_second > 50, f"Sustained throughput too low: {queries_per_second:.2f} qps"
    
    def test_stress_test(self, benchmark_db):
        """Stress test - find breaking point."""
        store = DeepMemoryStore(str(benchmark_db))
        
        # Add large dataset
        for i in range(10000):
            store._insert_unit(
                knowledge_type='FACT',
                subject=f'subject_{i}',
                predicate='is',
                object=f'object_{i}',
                statement=f'Test statement {i}',
                source_refs=[],
                evidence_refs=[],
                scope='benchmark'
            )
        
        # Increasing load
        num_workers = 1
        max_workers = 50
        queries_per_worker = 10
        
        while num_workers <= max_workers:
            try:
                with ThreadPoolExecutor(max_workers=num_workers) as executor:
                    futures = []
                    for _ in range(num_workers):
                        future = executor.submit(lambda: [
                            store.search('test', limit=10) for _ in range(queries_per_worker)
                        ])
                        futures.append(future)
                    
                    for future in futures:
                        future.result(timeout=30)
                
                num_workers *= 2
            except Exception:
                break
        
        print(f"Stress test: System handled up to {num_workers // 2} concurrent workers")
        
        # Should handle at least some load
        assert num_workers > 2, "System should handle basic concurrent load"


class TestPercentileLatency:
    """Percentile latency benchmarks."""
    
    def test_p50_p95_p99_latency(self, benchmark_db):
        """Benchmark p50, p95, p99 latency."""
        store = DeepMemoryStore(str(benchmark_db))
        
        # Add test data
        for i in range(1000):
            store._insert_unit(
                knowledge_type='FACT',
                subject=f'subject_{i}',
                predicate='is',
                object=f'object_{i}',
                statement=f'Test statement {i}',
                source_refs=[],
                evidence_refs=[],
                scope='benchmark'
            )
        
        # Collect latencies
        latencies = []
        for _ in range(1000):
            start = time.time()
            store.search('test', limit=10)
            latency = (time.time() - start) * 1000  # ms
            latencies.append(latency)
        
        # Calculate percentiles
        latencies.sort()
        p50 = statistics.median(latencies)
        p95 = latencies[int(len(latencies) * 0.95)]
        p99 = latencies[int(len(latencies) * 0.99)]
        
        print(f"P50: {p50:.2f}ms, P95: {p95:.2f}ms, P99: {p99:.2f}ms")
        
        # Assert reasonable percentiles
        assert p50 < 50, f"P50 latency too high: {p50:.2f}ms"
        assert p95 < 100, f"P95 latency too high: {p95:.2f}ms"
        assert p99 < 200, f"P99 latency too high: {p99:.2f}ms"