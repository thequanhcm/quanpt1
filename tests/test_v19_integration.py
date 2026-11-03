"""V19 tests — System Integration & Production Readiness (15 tests)."""
from __future__ import annotations

import time
import pytest
from pathlib import Path
import tempfile

from quan_ai_brain.core.integration import (
    CachingLayer, MetricsCollector, AuditLogger, HealthMonitor,
    UnifiedMemoryAPI, MemoryOrchestrator, IntegrationConfig
)


@pytest.fixture
def audit_db():
    """Create temporary audit database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "test_v19_audit.db"


class TestCachingLayer:
    """Tests for caching layer."""
    
    def test_cache_set_get(self):
        """Test cache set and get."""
        cache = CachingLayer(ttl=300)
        cache.set("key1", {"data": "value"})
        
        result = cache.get("key1")
        assert result == {"data": "value"}
    
    def test_cache_miss(self):
        """Test cache miss."""
        cache = CachingLayer(ttl=300)
        result = cache.get("nonexistent")
        assert result is None
    
    def test_cache_invalidate(self):
        """Test cache invalidation."""
        cache = CachingLayer(ttl=300)
        cache.set("key1", {"data": "value"})
        cache.invalidate("key1")
        
        result = cache.get("key1")
        assert result is None
    
    def test_cache_stats(self):
        """Test cache statistics."""
        cache = CachingLayer(ttl=300)
        cache.set("key1", "value1")
        cache.get("key1")  # Hit
        cache.get("key2")  # Miss
        
        stats = cache.get_stats()
        assert stats['hits'] == 1
        assert stats['misses'] == 1
        assert stats['hit_rate'] == 0.5


class TestMetricsCollector:
    """Tests for metrics collector."""
    
    def test_record_query(self):
        """Test recording query latency."""
        metrics = MetricsCollector()
        metrics.record_query(10.5)
        metrics.record_query(15.2)
        
        result = metrics.get_metrics()
        assert result.query_latency_ms > 0
    
    def test_record_error(self):
        """Test recording error."""
        metrics = MetricsCollector()
        metrics.record_request()
        metrics.record_error()
        
        result = metrics.get_metrics()
        assert result.error_rate > 0
    
    def test_metrics_reset(self):
        """Test metrics reset."""
        metrics = MetricsCollector()
        metrics.record_query(10.0)
        metrics.reset()
        
        result = metrics.get_metrics()
        assert result.query_latency_ms == 0.0


class TestAuditLogger:
    """Tests for audit logger."""
    
    def test_log_event(self, audit_db):
        """Test logging audit event."""
        audit = AuditLogger(str(audit_db))
        audit.log('test_action', 'test_module', {'key': 'value'})
        
        logs = audit.get_logs(limit=10)
        assert len(logs) == 1
        assert logs[0]['action'] == 'test_action'
        audit.close()
    
    def test_log_with_user(self, audit_db):
        """Test logging with user ID."""
        audit = AuditLogger(str(audit_db))
        audit.log('test_action', 'test_module', user_id='user123')
        
        logs = audit.get_logs(limit=10)
        assert logs[0]['user_id'] == 'user123'
        audit.close()
    
    def test_log_error(self, audit_db):
        """Test logging error."""
        audit = AuditLogger(str(audit_db))
        audit.log('failed_action', 'test_module', success=False, error_message='Test error')
        
        logs = audit.get_logs(limit=10)
        assert logs[0]['success'] is False
        assert logs[0]['error_message'] == 'Test error'
        audit.close()


class TestHealthMonitor:
    """Tests for health monitor."""
    
    def test_register_module(self):
        """Test registering module."""
        monitor = HealthMonitor()
        monitor.register_module('test_module')
        
        health = monitor.get_health()
        assert 'test_module' in health
        assert health['test_module'].status == 'healthy'
    
    def test_update_status(self):
        """Test updating module status."""
        monitor = HealthMonitor()
        monitor.register_module('test_module')
        monitor.update_status('test_module', 'degraded', {'reason': 'high_load'})
        
        health = monitor.get_health()
        assert health['test_module'].status == 'degraded'
    
    def test_health_report(self):
        """Test generating health report."""
        monitor = HealthMonitor()
        monitor.register_module('module1')
        monitor.register_module('module2')
        
        report = monitor.generate_health_report()
        assert report['overall_status'] == 'healthy'
        assert report['total_count'] == 2


class TestUnifiedMemoryAPI:
    """Tests for unified memory API."""
    
    def test_unified_search(self, audit_db):
        """Test unified search."""
        config = IntegrationConfig()
        api = UnifiedMemoryAPI(config)
        
        result = api.unified_search("test query", filters={'type': 'fact'})
        
        assert 'results' in result
        assert 'cached' in result
        assert 'latency_ms' in result
        api.close()
    
    def test_unified_retrieval(self, audit_db):
        """Test unified retrieval."""
        config = IntegrationConfig()
        api = UnifiedMemoryAPI(config)
        
        result = api.unified_retrieval("test query", top_k=5, privacy_level='strict')
        
        assert 'results' in result
        assert 'latency_ms' in result
        api.close()
    
    def test_health_check(self, audit_db):
        """Test health check."""
        config = IntegrationConfig()
        api = UnifiedMemoryAPI(config)
        
        report = api.memory_health_check()
        
        assert 'overall_status' in report
        assert 'modules' in report
        assert 'performance' in report
        assert 'cache' in report
        api.close()
    
    def test_system_report(self, audit_db):
        """Test system report."""
        config = IntegrationConfig()
        api = UnifiedMemoryAPI(config)
        
        report = api.generate_system_report()
        
        assert 'generated_at' in report
        assert 'health' in report
        assert 'performance' in report
        assert 'modules' in report
        api.close()


class TestMemoryOrchestrator:
    """Tests for memory orchestrator."""
    
    def test_execute_workflow(self, audit_db):
        """Test executing workflow."""
        config = IntegrationConfig()
        orchestrator = MemoryOrchestrator(config)
        
        workflow = {
            'id': 'wf1',
            'steps': [
                {'type': 'search', 'name': 'step1', 'query': 'test'},
                {'type': 'retrieval', 'name': 'step2', 'query': 'test', 'top_k': 5}
            ]
        }
        
        result = orchestrator.execute_workflow(workflow)
        
        assert result['workflow_id'] == 'wf1'
        assert len(result['results']) == 2
        assert all(r['success'] for r in result['results'])
        orchestrator.close()
    
    def test_workflow_with_error(self, audit_db):
        """Test workflow with error."""
        config = IntegrationConfig()
        orchestrator = MemoryOrchestrator(config)
        
        workflow = {
            'id': 'wf2',
            'steps': [
                {'type': 'search', 'name': 'step1', 'query': 'test'},
                {'type': 'invalid_type', 'name': 'step2'}
            ]
        }
        
        result = orchestrator.execute_workflow(workflow)
        
        assert result['completed'] is False
        assert result['results'][1]['success'] is False
        orchestrator.close()


class TestIntegrationConfig:
    """Tests for integration configuration."""
    
    def test_default_config(self):
        """Test default configuration."""
        config = IntegrationConfig()
        
        assert config.cache_enabled is True
        assert config.cache_ttl == 300
        assert config.async_mode is False
        assert config.privacy_level == 'standard'
    
    def test_custom_config(self):
        """Test custom configuration."""
        config = IntegrationConfig(
            cache_enabled=False,
            cache_ttl=600,
            async_mode=True,
            privacy_level='strict'
        )
        
        assert config.cache_enabled is False
        assert config.cache_ttl == 600
        assert config.async_mode is True
        assert config.privacy_level == 'strict'