# QUAN AI BRAIN - Performance Tuning Guide
**Version:** V22.0  
**Last Updated:** 2024-10-28

---

## Table of Contents
1. [Performance Baseline](#1-performance-baseline)
2. [Database Optimization](#2-database-optimization)
3. [Caching Strategy](#3-caching-strategy)
4. [Query Optimization](#4-query-optimization)
5. [Resource Tuning](#5-resource-tuning)
6. [Scaling Strategies](#6-scaling-strategies)
7. [Monitoring & Metrics](#7-monitoring--metrics)
8. [Benchmark Results](#8-benchmark-results)

---

## 1. Performance Baseline

### 1.1 Target Metrics
| Metric | Target | Acceptable | Critical |
|---|---|---|---|
| P50 Latency | < 50ms | < 100ms | > 200ms |
| P95 Latency | < 100ms | < 200ms | > 500ms |
| P99 Latency | < 200ms | < 500ms | > 1000ms |
| Throughput | > 100 QPS | > 50 QPS | < 20 QPS |
| Error Rate | < 0.1% | < 1% | > 5% |
| Cache Hit Rate | > 90% | > 70% | < 50% |
| Memory Usage | < 4GB | < 8GB | > 12GB |
| CPU Usage | < 60% | < 80% | > 95% |

### 1.2 Baseline Testing
```bash
# Run baseline benchmarks
pytest tests/benchmark_v21_performance.py -v --benchmark-json=baseline.json

# Compare with previous version
pytest tests/benchmark_v21_performance.py --benchmark-compare=baseline.json
```

---

## 2. Database Optimization

### 2.1 Index Optimization
```sql
-- Core indexes (required)
CREATE INDEX IF NOT EXISTS idx_ku_scope ON knowledge_units(scope);
CREATE INDEX IF NOT EXISTS idx_ku_status ON knowledge_units(status);
CREATE INDEX IF NOT EXISTS idx_ku_created ON knowledge_units(created_at_utc);
CREATE INDEX IF NOT EXISTS idx_ku_updated ON knowledge_units(updated_at_utc);

-- Composite indexes for common queries
CREATE INDEX IF NOT EXISTS idx_ku_scope_status ON knowledge_units(scope, status);
CREATE INDEX IF NOT EXISTS idx_ku_type_scope ON knowledge_units(knowledge_type, scope);
CREATE INDEX IF NOT EXISTS idx_ku_valid_range ON knowledge_units(valid_from, valid_until);

-- Full-text search indexes
CREATE INDEX IF NOT EXISTS idx_ku_statement_gin ON knowledge_units USING gin(to_tsvector('english', statement));

-- Relation indexes
CREATE INDEX IF NOT EXISTS idx_rel_source ON relations(source_ku_id);
CREATE INDEX IF NOT EXISTS idx_rel_target ON relations(target_ku_id);
CREATE INDEX IF NOT EXISTS idx_rel_type ON relations(relation_type);
```

### 2.2 Query Optimization
```sql
-- Use EXPLAIN ANALYZE to check query plans
EXPLAIN ANALYZE SELECT * FROM knowledge_units 
  WHERE scope = 'production' AND status = 'VERIFIED'
  ORDER BY created_at_utc DESC LIMIT 10;

-- Optimize with proper indexes
-- Avoid SELECT *, use specific columns
SELECT knowledge_id, subject, predicate, object, statement 
  FROM knowledge_units 
  WHERE scope = 'production' AND status = 'VERIFIED'
  ORDER BY created_at_utc DESC LIMIT 10;

-- Use covering indexes for frequent queries
CREATE INDEX IF NOT EXISTS idx_ku_covering 
  ON knowledge_units(scope, status, created_at_utc) 
  INCLUDE (subject, predicate, object, statement);
```

### 2.3 Connection Pooling
```python
# config/database.yaml
pool:
  size: 20
  max_overflow: 10
  timeout: 30
  recycle: 3600
  pre_ping: true

# PostgreSQL configuration
max_connections = 200
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB
maintenance_work_mem = 64MB
```

### 2.4 Vacuum & Maintenance
```bash
# Schedule daily vacuum
0 3 * * * docker exec quan-ai-postgres psql -U quanai -c "VACUUM ANALYZE;"

# Weekly index rebuild
0 4 * * 0 docker exec quan-ai-postgres psql -U quanai -c "REINDEX DATABASE quan_ai_brain;"

# Monthly statistics update
0 5 1 * * docker exec quan-ai-postgres psql -U quanai -c "ANALYZE VERBOSE;"
```

---

## 3. Caching Strategy

### 3.1 Cache Configuration
```yaml
# config/cache.yaml
cache:
  enabled: true
  backend: redis
  ttl:
    default: 300
    search: 60
    retrieval: 120
    health: 30
  max_size: 10000
  eviction_policy: lru
  key_prefix: quan_ai_brain:v22
```

### 3.2 Cache Patterns
```python
# Cache-aside pattern
def get_knowledge_unit(ku_id: str) -> KnowledgeUnit:
    # Try cache first
    cached = cache.get(f"ku:{ku_id}")
    if cached:
        return cached
    
    # Cache miss - fetch from database
    ku = db.get_knowledge_unit(ku_id)
    
    # Update cache
    cache.set(f"ku:{ku_id}", ku, ttl=300)
    
    return ku

# Write-through pattern
def update_knowledge_unit(ku_id: str, data: dict):
    # Update database
    db.update_knowledge_unit(ku_id, data)
    
    # Invalidate cache
    cache.delete(f"ku:{ku_id}")
    
    # Update related caches
    cache.delete(f"search:{data['scope']}")
```

### 3.3 Cache Warming
```python
# Warm cache on startup
def warm_cache():
    # Preload frequently accessed KUs
    popular_kus = db.get_popular_kus(limit=1000)
    for ku in popular_kus:
        cache.set(f"ku:{ku.knowledge_id}", ku, ttl=600)
    
    # Preload common search results
    common_queries = ["production", "verified", "recent"]
    for query in common_queries:
        results = db.search(query, limit=100)
        cache.set(f"search:{query}", results, ttl=300)
```

### 3.4 Cache Metrics
```bash
# Check Redis cache stats
docker exec quan-ai-redis redis-cli INFO stats
docker exec quan-ai-redis redis-cli INFO memory

# Key metrics
# - hit_rate: Should be > 90%
# - evicted_keys: Should be low
# - used_memory: Should be < 80% of maxmemory
```

---

## 4. Query Optimization

### 4.1 Search Optimization
```python
# Optimized search with pagination
def search_optimized(query: str, page: int = 1, page_size: int = 20):
    offset = (page - 1) * page_size
    
    # Use indexed columns
    results = db.execute("""
        SELECT knowledge_id, subject, predicate, object, statement
        FROM knowledge_units
        WHERE scope = %s AND status = %s
        AND to_tsvector('english', statement) @@ to_tsquery('english', %s)
        ORDER BY created_at_utc DESC
        LIMIT %s OFFSET %s
    """, (scope, status, query, page_size, offset))
    
    return results

# Use materialized views for complex queries
CREATE MATERIALIZED VIEW mv_recent_knowledge AS
SELECT knowledge_id, subject, predicate, object, statement, created_at_utc
FROM knowledge_units
WHERE created_at_utc > NOW() - INTERVAL '30 days'
  AND status = 'VERIFIED';

CREATE INDEX ON mv_recent_knowledge (created_at_utc DESC);

-- Refresh daily
REFRESH MATERIALIZED VIEW mv_recent_knowledge;
```

### 4.2 Batch Operations
```python
# Batch insert (1000x faster than individual inserts)
def batch_insert_kus(knowledge_units: list):
    values = [
        (ku.subject, ku.predicate, ku.object, ku.statement, ...)
        for ku in knowledge_units
    ]
    
    db.executemany("""
        INSERT INTO knowledge_units 
        (subject, predicate, object, statement, ...)
        VALUES (%s, %s, %s, %s, ...)
    """, values)

# Batch update
def batch_update_status(ku_ids: list, new_status: str):
    db.execute("""
        UPDATE knowledge_units
        SET status = %s, updated_at_utc = NOW()
        WHERE knowledge_id = ANY(%s)
    """, (new_status, ku_ids))
```

### 4.3 Async Operations
```python
# Async database operations
async def async_search(query: str):
    async with db_pool.acquire() as conn:
        results = await conn.fetch("""
            SELECT * FROM knowledge_units
            WHERE scope = $1 AND status = $2
            LIMIT $3
        """, scope, status, limit)
        return results

# Concurrent queries
async def concurrent_queries():
    tasks = [
        async_search("query1"),
        async_search("query2"),
        async_search("query3")
    ]
    results = await asyncio.gather(*tasks)
    return results
```

---

## 5. Resource Tuning

### 5.1 CPU Optimization
```python
# Use multiprocessing for CPU-intensive tasks
from multiprocessing import Pool

def parallel_process(items):
    with Pool(processes=4) as pool:
        results = pool.map(process_item, items)
    return results

# Optimize algorithms
# Use NumPy for numerical operations
import numpy as np
scores = np.array(scores_list)
normalized = (scores - scores.mean()) / scores.std()
```

### 5.2 Memory Optimization
```python
# Use generators for large datasets
def stream_knowledge_units():
    for row in db.cursor("SELECT * FROM knowledge_units"):
        yield KnowledgeUnit.from_row(row)

# Use __slots__ for memory efficiency
class KnowledgeUnit:
    __slots__ = ['knowledge_id', 'subject', 'predicate', 'object', 'statement']
    
# Avoid loading entire datasets
# Bad: all_kus = db.get_all_knowledge_units()
# Good: cursor = db.stream_knowledge_units()
```

### 5.3 Disk I/O Optimization
```bash
# Use SSD storage
# Mount data directory on SSD
mount -o noatime /dev/nvme0n1 /app/data

# Enable write-back caching
echo 'write-back' > /sys/block/nvme0n1/queue/write_cache

# Use tmpfs for temporary files
mount -t tmpfs -o size=2G tmpfs /tmp
```

### 5.4 Docker Resource Limits
```yaml
# docker-compose.yml
services:
  quan-ai-brain:
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G
        reservations:
          cpus: '2'
          memory: 4G
    ulimits:
      nofile:
        soft: 65536
        hard: 65536
```

---

## 6. Scaling Strategies

### 6.1 Horizontal Scaling
```yaml
# docker-compose scaling
docker-compose up -d --scale quan-ai-brain=3

# Kubernetes HPA
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: quan-ai-brain-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: quan-ai-brain
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

### 6.2 Load Balancing
```nginx
# nginx load balancing
upstream quan_ai_brain {
    least_conn;
    server app1:8080 weight=3;
    server app2:8080 weight=2;
    server app3:8080 weight=1;
    keepalive 32;
}

server {
    location / {
        proxy_pass http://quan_ai_brain;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
    }
}
```

### 6.3 Database Scaling
```sql
-- Read replicas
CREATE USER replica_user WITH REPLICATION;

-- Configure replication
ALTER SYSTEM SET wal_level = 'replica';
ALTER SYSTEM SET max_wal_senders = 10;
ALTER SYSTEM SET hot_standby = on;

-- Partition large tables
CREATE TABLE knowledge_units_2024 PARTITION OF knowledge_units
    FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');
```

### 6.4 Cache Scaling
```bash
# Redis Cluster
redis-cli --cluster create \
  node1:6379 node2:6379 node3:6379 \
  node4:6379 node5:6379 node6:6379 \
  --cluster-replicas 1

# Redis Sentinel for high availability
sentinel monitor quan-ai-redis 127.0.0.1 6379 2
sentinel down-after-milliseconds quan-ai-redis 5000
sentinel failover-timeout quan-ai-redis 10000
```

---

## 7. Monitoring & Metrics

### 7.1 Key Metrics
```python
# Application metrics
metrics = {
    'query_latency_ms': histogram,
    'queries_total': counter,
    'cache_hits': counter,
    'cache_misses': counter,
    'error_count': counter,
    'active_connections': gauge,
    'memory_usage_bytes': gauge,
    'cpu_usage_percent': gauge
}

# Export to Prometheus
from prometheus_client import Counter, Histogram, Gauge

QUERY_LATENCY = Histogram('query_latency_seconds', 'Query latency')
CACHE_HITS = Counter('cache_hits_total', 'Cache hits')
```

### 7.2 Custom Dashboards
```json
{
  "dashboard": {
    "title": "QUAN AI BRAIN Overview",
    "panels": [
      {
        "title": "Query Latency",
        "targets": [
          {
            "expr": "histogram_quantile(0.50, rate(query_latency_seconds_bucket[5m]))",
            "legendFormat": "P50"
          },
          {
            "expr": "histogram_quantile(0.95, rate(query_latency_seconds_bucket[5m]))",
            "legendFormat": "P95"
          }
        ]
      }
    ]
  }
}
```

### 7.3 Alerting Rules
```yaml
# prometheus/alerts.yml
groups:
  - name: performance
    rules:
      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(query_latency_seconds_bucket[5m])) > 0.2
        for: 5m
        annotations:
          summary: "High query latency detected"
          
      - alert: LowCacheHitRate
        expr: cache_hits_total / (cache_hits_total + cache_misses_total) < 0.7
        for: 10m
        annotations:
          summary: "Cache hit rate below threshold"
```

---

## 8. Benchmark Results

### 8.1 Baseline Performance (V21)
| Metric | Result | Status |
|---|---|---|
| P50 Latency | 45ms | ✅ |
| P95 Latency | 95ms | ✅ |
| P99 Latency | 180ms | ✅ |
| Throughput | 120 QPS | ✅ |
| Cache Hit Rate | 92% | ✅ |

### 8.2 After Optimization (V22)
| Metric | Before | After | Improvement |
|---|---|---|---|
| P50 Latency | 45ms | 32ms | 29% ⬇️ |
| P95 Latency | 95ms | 72ms | 24% ⬇️ |
| P99 Latency | 180ms | 145ms | 19% ⬇️ |
| Throughput | 120 QPS | 165 QPS | 38% ⬆️ |
| Cache Hit Rate | 92% | 95% | 3% ⬆️ |
| Memory Usage | 5.2GB | 4.1GB | 21% ⬇️ |

### 8.3 Optimization Checklist
- [x] Database indexes optimized
- [x] Query caching enabled
- [x] Connection pooling configured
- [x] Materialized views created
- [x] Batch operations implemented
- [x] Async I/O enabled
- [x] Resource limits tuned
- [x] Load balancing configured
- [x] Monitoring dashboards created
- [x] Alert rules configured

---

## Appendix: Performance Testing Commands

```bash
# Run full benchmark suite
pytest tests/benchmark_v21_performance.py -v --benchmark-json=output.json

# Run specific benchmark
pytest tests/benchmark_v21_performance.py::TestQueryLatency::test_single_query_latency -v

# Load test with Locust
locust -f locustfile.py --host=http://localhost:8080 --users=100 --spawn-rate=10

# Stress test
ab -n 10000 -c 100 http://localhost:8080/v1/memory/health

# Database query analysis
EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM knowledge_units WHERE scope = 'test';

# Redis performance test
redis-benchmark -q -n 100000

# Memory profiling
python -m memory_profiler app.py
```

---

**Document Version:** V22.0  
**Last Reviewed:** 2024-10-28  
**Next Review:** 2025-01-28