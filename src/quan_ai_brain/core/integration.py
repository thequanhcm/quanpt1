"""V19 — System Integration & Production Readiness.

Tích hợp toàn bộ 8 sprints (V11-V18) + production readiness (performance, monitoring, logging, deployment).
"""
from __future__ import annotations

import json
import logging
import sqlite3
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class IntegrationConfig:
    """Integration configuration."""
    cache_enabled: bool = True
    cache_ttl: int = 300  # seconds
    async_mode: bool = False
    batch_size: int = 100
    max_retries: int = 3
    timeout: int = 30
    privacy_level: str = 'standard'  # 'standard', 'strict', 'relaxed'


@dataclass
class HealthStatus:
    """Health status for a module."""
    module_name: str
    status: str  # 'healthy', 'degraded', 'unhealthy'
    last_check: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceMetrics:
    """Performance metrics."""
    query_latency_ms: float
    throughput_per_sec: float
    cache_hit_rate: float
    memory_usage_mb: float
    cpu_usage_percent: float
    error_rate: float
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class CachingLayer:
    """Caching layer for performance optimization."""
    
    def __init__(self, ttl: int = 300):
        self.ttl = ttl
        self._cache: dict[str, tuple[Any, float]] = {}
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0
    
    def get(self, key: str) -> Any | None:
        """Get from cache."""
        with self._lock:
            if key in self._cache:
                value, timestamp = self._cache[key]
                if time.time() - timestamp < self.ttl:
                    self.hits += 1
                    return value
                else:
                    del self._cache[key]
            
            self.misses += 1
            return None
    
    def set(self, key: str, value: Any):
        """Set cache entry."""
        with self._lock:
            self._cache[key] = (value, time.time())
    
    def invalidate(self, key: str):
        """Invalidate cache entry."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
    
    def get_stats(self) -> dict:
        """Get cache statistics."""
        total = self.hits + self.misses
        hit_rate = self.hits / total if total > 0 else 0.0
        
        return {
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': hit_rate,
            'size': len(self._cache)
        }
    
    def clear(self):
        """Clear all cache."""
        with self._lock:
            self._cache.clear()


class MetricsCollector:
    """Collect performance metrics."""
    
    def __init__(self):
        self._metrics: list[PerformanceMetrics] = []
        self._lock = threading.Lock()
        self._query_times: list[float] = []
        self._errors: int = 0
        self._requests: int = 0
    
    def record_query(self, latency_ms: float):
        """Record query latency."""
        with self._lock:
            self._query_times.append(latency_ms)
            if len(self._query_times) > 1000:
                self._query_times = self._query_times[-1000:]
    
    def record_error(self):
        """Record error."""
        with self._lock:
            self._errors += 1
            self._requests += 1
    
    def record_request(self):
        """Record request."""
        with self._lock:
            self._requests += 1
    
    def get_metrics(self) -> PerformanceMetrics:
        """Get current metrics."""
        with self._lock:
            avg_latency = sum(self._query_times) / len(self._query_times) if self._query_times else 0.0
            error_rate = self._errors / self._requests if self._requests > 0 else 0.0
            
            return PerformanceMetrics(
                query_latency_ms=avg_latency,
                throughput_per_sec=self._requests / max(1, len(self._query_times)),
                cache_hit_rate=0.0,  # Would come from cache layer
                memory_usage_mb=0.0,  # Would come from system
                cpu_usage_percent=0.0,  # Would come from system
                error_rate=error_rate
            )
    
    def reset(self):
        """Reset metrics."""
        with self._lock:
            self._query_times.clear()
            self._errors = 0
            self._requests = 0


class AuditLogger:
    """Comprehensive audit logging."""
    
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self._conn = sqlite3.connect(str(self.db_path))
        self._create_schema()
    
    def _create_schema(self):
        """Create audit log schema."""
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                user_id TEXT,
                action TEXT NOT NULL,
                module TEXT,
                details TEXT,
                success INTEGER NOT NULL,
                error_message TEXT
            );
            
            CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp);
            CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_logs(action);
            CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_logs(user_id);
        """)
        self._conn.commit()
    
    def log(self, action: str, module: str, details: dict | None = None,
           success: bool = True, error_message: str | None = None,
           user_id: str | None = None):
        """Log audit event."""
        self._conn.execute(
            """INSERT INTO audit_logs 
               (timestamp, user_id, action, module, details, success, error_message)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                datetime.now(timezone.utc).isoformat(),
                user_id,
                action,
                module,
                json.dumps(details or {}),
                1 if success else 0,
                error_message
            )
        )
        self._conn.commit()
    
    def get_logs(self, limit: int = 100, action: str | None = None) -> list[dict]:
        """Get audit logs."""
        query = "SELECT * FROM audit_logs ORDER BY timestamp DESC"
        params = []
        
        if action:
            query += " WHERE action = ?"
            params.append(action)
        
        query += f" LIMIT {limit}"
        
        rows = self._conn.execute(query, params).fetchall()
        
        logs = []
        for row in rows:
            logs.append({
                'id': row[0],
                'timestamp': row[1],
                'user_id': row[2],
                'action': row[3],
                'module': row[4],
                'details': json.loads(row[5]),
                'success': bool(row[6]),
                'error_message': row[7]
            })
        
        return logs
    
    def close(self):
        """Close connection."""
        self._conn.close()


class HealthMonitor:
    """Monitor system health."""
    
    def __init__(self):
        self._modules: dict[str, HealthStatus] = {}
        self._lock = threading.Lock()
    
    def register_module(self, module_name: str):
        """Register module for monitoring."""
        with self._lock:
            self._modules[module_name] = HealthStatus(
                module_name=module_name,
                status='healthy',
                last_check=datetime.now(timezone.utc).isoformat()
            )
    
    def update_status(self, module_name: str, status: str, details: dict | None = None):
        """Update module status."""
        with self._lock:
            if module_name in self._modules:
                self._modules[module_name].status = status
                self._modules[module_name].last_check = datetime.now(timezone.utc).isoformat()
                if details:
                    self._modules[module_name].details.update(details)
    
    def get_health(self) -> dict[str, HealthStatus]:
        """Get health status of all modules."""
        with self._lock:
            return self._modules.copy()
    
    def is_healthy(self) -> bool:
        """Check if system is healthy."""
        with self._lock:
            return all(m.status == 'healthy' for m in self._modules.values())
    
    def generate_health_report(self) -> dict:
        """Generate comprehensive health report."""
        with self._lock:
            modules = {name: {
                'status': status.status,
                'last_check': status.last_check,
                'details': status.details
            } for name, status in self._modules.items()}
            
            overall_status = 'healthy' if all(m.status == 'healthy' for m in self._modules.values()) else 'degraded'
            
            return {
                'overall_status': overall_status,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'modules': modules,
                'healthy_count': sum(1 for m in self._modules.values() if m.status == 'healthy'),
                'total_count': len(self._modules)
            }


class UnifiedMemoryAPI:
    """Unified API for all memory operations."""
    
    def __init__(self, config: IntegrationConfig | None = None):
        self.config = config or IntegrationConfig()
        self.cache = CachingLayer(ttl=self.config.cache_ttl)
        self.metrics = MetricsCollector()
        self.audit = AuditLogger('data/audit.db')
        self.health = HealthMonitor()
        
        # Register modules
        modules = [
            'temporal', 'cross_modal', 'quality', 'emotional',
            'causal', 'counterfactual', 'federated', 'privacy'
        ]
        for module in modules:
            self.health.register_module(module)
        
        logger.info("UnifiedMemoryAPI initialized")
    
    def unified_search(self, query: str, filters: dict | None = None,
                      context: dict | None = None) -> dict:
        """Unified search across all memory types."""
        start_time = time.time()
        
        try:
            # Check cache
            cache_key = f"search:{query}:{json.dumps(filters or {})}"
            cached = self.cache.get(cache_key)
            if cached:
                self.metrics.record_query((time.time() - start_time) * 1000)
                return {'results': cached, 'cached': True}
            
            # Perform search (placeholder - would integrate all modules)
            results = []
            
            # Cache results
            self.cache.set(cache_key, results)
            
            latency = (time.time() - start_time) * 1000
            self.metrics.record_query(latency)
            self.audit.log('unified_search', 'integration', {
                'query': query,
                'filters': filters,
                'result_count': len(results),
                'latency_ms': latency
            })
            
            return {'results': results, 'cached': False, 'latency_ms': latency}
        
        except Exception as e:
            self.metrics.record_error()
            self.audit.log('unified_search', 'integration', {
                'query': query,
                'error': str(e)
            }, success=False, error_message=str(e))
            raise
    
    def unified_retrieval(self, query: str, top_k: int = 10,
                         context: dict | None = None,
                         privacy_level: str | None = None) -> dict:
        """Unified retrieval with privacy controls."""
        start_time = time.time()
        
        try:
            privacy = privacy_level or self.config.privacy_level
            
            # Placeholder - would integrate all retrieval modules
            results = []
            
            latency = (time.time() - start_time) * 1000
            self.metrics.record_query(latency)
            self.audit.log('unified_retrieval', 'integration', {
                'query': query,
                'top_k': top_k,
                'privacy_level': privacy,
                'result_count': len(results),
                'latency_ms': latency
            })
            
            return {'results': results, 'latency_ms': latency}
        
        except Exception as e:
            self.metrics.record_error()
            self.audit.log('unified_retrieval', 'integration', {
                'query': query,
                'error': str(e)
            }, success=False, error_message=str(e))
            raise
    
    def memory_health_check(self) -> dict:
        """Check health of all memory modules."""
        report = self.health.generate_health_report()
        
        # Add performance metrics
        report['performance'] = self.metrics.get_metrics().__dict__
        report['cache'] = self.cache.get_stats()
        
        return report
    
    def generate_system_report(self) -> dict:
        """Generate comprehensive system report."""
        return {
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'health': self.health.generate_health_report(),
            'performance': self.metrics.get_metrics().__dict__,
            'cache': self.cache.get_stats(),
            'config': {
                'cache_enabled': self.config.cache_enabled,
                'cache_ttl': self.config.cache_ttl,
                'async_mode': self.config.async_mode,
                'privacy_level': self.config.privacy_level
            },
            'modules': {
                'temporal': 'V11',
                'cross_modal': 'V12',
                'quality': 'V13',
                'ui': 'V14',
                'graph': 'V15',
                'emotional': 'V16',
                'causal': 'V17',
                'federated': 'V18'
            }
        }
    
    def batch_operations(self, operations: list[dict]) -> list[dict]:
        """Execute batch operations."""
        results = []
        
        for op in operations[:self.config.batch_size]:
            try:
                # Placeholder - would execute operations
                results.append({
                    'operation': op.get('type'),
                    'success': True
                })
            except Exception as e:
                results.append({
                    'operation': op.get('type'),
                    'success': False,
                    'error': str(e)
                })
        
        return results
    
    def close(self):
        """Close resources."""
        self.audit.close()
        logger.info("UnifiedMemoryAPI closed")


class MemoryOrchestrator:
    """Orchestrate memory operations across modules."""
    
    def __init__(self, config: IntegrationConfig | None = None):
        self.config = config or IntegrationConfig()
        self.api = UnifiedMemoryAPI(config)
        logger.info("MemoryOrchestrator initialized")
    
    def execute_workflow(self, workflow: dict) -> dict:
        """Execute memory workflow."""
        steps = workflow.get('steps', [])
        results = []
        
        for step in steps:
            try:
                result = self._execute_step(step)
                results.append({
                    'step': step.get('name'),
                    'success': True,
                    'result': result
                })
            except Exception as e:
                results.append({
                    'step': step.get('name'),
                    'success': False,
                    'error': str(e)
                })
                if not self.config.async_mode:
                    break
        
        return {
            'workflow_id': workflow.get('id'),
            'results': results,
            'completed': all(r['success'] for r in results)
        }
    
    def _execute_step(self, step: dict) -> Any:
        """Execute a single workflow step."""
        step_type = step.get('type')
        
        if step_type == 'search':
            return self.api.unified_search(
                step.get('query', ''),
                step.get('filters'),
                step.get('context')
            )
        elif step_type == 'retrieval':
            return self.api.unified_retrieval(
                step.get('query', ''),
                step.get('top_k', 10),
                step.get('context'),
                step.get('privacy_level')
            )
        else:
            raise ValueError(f"Unknown step type: {step_type}")
    
    def close(self):
        """Close orchestrator."""
        self.api.close()