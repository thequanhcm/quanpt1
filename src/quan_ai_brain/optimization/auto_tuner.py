"""
Auto-Tuning System Module (V26.1)

This module provides automatic performance optimization including:
- Real-time performance monitoring
- Automatic tuning algorithms
- Threshold-based optimization
- A/B testing framework
- Safety mechanisms

Version: V26.1
Author: QUAN AI BRAIN Team
"""

import asyncio
import logging
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import json
import random

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of performance metrics"""
    LATENCY_P50 = "latency_p50"
    LATENCY_P95 = "latency_p95"
    LATENCY_P99 = "latency_p99"
    THROUGHPUT = "throughput"
    ERROR_RATE = "error_rate"
    CPU_USAGE = "cpu_usage"
    MEMORY_USAGE = "memory_usage"
    CACHE_HIT_RATE = "cache_hit_rate"
    DB_CONNECTIONS = "db_connections"
    QUEUE_SIZE = "queue_size"


class OptimizationType(Enum):
    """Types of optimizations"""
    CACHE_SIZE = "cache_size"
    BATCH_SIZE = "batch_size"
    CONNECTION_POOL = "connection_pool"
    TIMEOUT = "timeout"
    RETRY_COUNT = "retry_count"
    PARALLELISM = "parallelism"
    INDEX_ENABLE = "index_enable"
    QUERY_OPTIMIZE = "query_optimize"


class TuningAction(Enum):
    """Actions for tuning"""
    INCREASE = "increase"
    DECREASE = "decrease"
    ENABLE = "enable"
    DISABLE = "disable"
    SET = "set"


@dataclass
class Metric:
    """Represents a performance metric"""
    metric_id: str
    metric_type: MetricType
    value: float
    timestamp: datetime
    unit: str = ""
    tags: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'metric_id': self.metric_id,
            'metric_type': self.metric_type.value,
            'value': self.value,
            'timestamp': self.timestamp.isoformat(),
            'unit': self.unit,
            'tags': self.tags
        }


@dataclass
class OptimizationSuggestion:
    """Represents an optimization suggestion"""
    suggestion_id: str
    optimization_type: OptimizationType
    action: TuningAction
    current_value: Any
    suggested_value: Any
    expected_improvement: float
    confidence: float
    risk_level: str  # 'low', 'medium', 'high'
    reason: str
    metrics_affected: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            'suggestion_id': self.suggestion_id,
            'optimization_type': self.optimization_type.value,
            'action': self.action.value,
            'current_value': self.current_value,
            'suggested_value': self.suggested_value,
            'expected_improvement': self.expected_improvement,
            'confidence': self.confidence,
            'risk_level': self.risk_level,
            'reason': self.reason,
            'metrics_affected': self.metrics_affected
        }


@dataclass
class TuningConfig:
    """Configuration for auto-tuning"""
    config_id: str
    name: str
    enabled: bool
    thresholds: Dict[str, float]
    optimization_rules: Dict[str, Any]
    safety_limits: Dict[str, Any]
    last_updated: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'config_id': self.config_id,
            'name': self.name,
            'enabled': self.enabled,
            'thresholds': self.thresholds,
            'optimization_rules': self.optimization_rules,
            'safety_limits': self.safety_limits,
            'last_updated': self.last_updated.isoformat()
        }


@dataclass
class ABTest:
    """Represents an A/B test"""
    test_id: str
    name: str
    variant_a: Dict[str, Any]
    variant_b: Dict[str, Any]
    traffic_split: float  # Percentage for variant B
    status: str  # 'running', 'completed', 'rolled_back'
    metrics: Dict[str, Any]
    started_at: datetime
    completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'test_id': self.test_id,
            'name': self.name,
            'variant_a': self.variant_a,
            'variant_b': self.variant_b,
            'traffic_split': self.traffic_split,
            'status': self.status,
            'metrics': self.metrics,
            'started_at': self.started_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }


class MetricsCollector:
    """Collects performance metrics from the system"""

    def __init__(self, db=None):
        self.db = db
        self.metrics_history: Dict[str, List[Metric]] = {}
        self.collection_interval = 60  # seconds

    def collect_all_metrics(self) -> List[Metric]:
        """Collect all available metrics"""
        metrics = []

        # Latency metrics
        metrics.extend(self._collect_latency_metrics())

        # Throughput metrics
        metrics.extend(self._collect_throughput_metrics())

        # Error rate metrics
        metrics.extend(self._collect_error_metrics())

        # Resource metrics
        metrics.extend(self._collect_resource_metrics())

        # Cache metrics
        metrics.extend(self._collect_cache_metrics())

        # Store in history
        for metric in metrics:
            if metric.metric_type.value not in self.metrics_history:
                self.metrics_history[metric.metric_type.value] = []
            self.metrics_history[metric.metric_type.value].append(metric)

            # Keep only last 24 hours
            cutoff = datetime.utcnow() - timedelta(hours=24)
            self.metrics_history[metric.metric_type.value] = [
                m for m in self.metrics_history[metric.metric_type.value]
                if m.timestamp > cutoff
            ]

        return metrics

    def _collect_latency_metrics(self) -> List[Metric]:
        """Collect latency metrics"""
        metrics = []
        now = datetime.utcnow()

        # Simulate latency data (in real implementation, query actual data)
        p50 = random.uniform(30, 80)
        p95 = random.uniform(80, 150)
        p99 = random.uniform(150, 300)

        metrics.append(Metric(
            metric_id='latency_p50',
            metric_type=MetricType.LATENCY_P50,
            value=p50,
            timestamp=now,
            unit='ms'
        ))

        metrics.append(Metric(
            metric_id='latency_p95',
            metric_type=MetricType.LATENCY_P95,
            value=p95,
            timestamp=now,
            unit='ms'
        ))

        metrics.append(Metric(
            metric_id='latency_p99',
            metric_type=MetricType.LATENCY_P99,
            value=p99,
            timestamp=now,
            unit='ms'
        ))

        return metrics

    def _collect_throughput_metrics(self) -> List[Metric]:
        """Collect throughput metrics"""
        now = datetime.utcnow()
        throughput = random.uniform(100, 500)  # requests per second

        return [Metric(
            metric_id='throughput',
            metric_type=MetricType.THROUGHPUT,
            value=throughput,
            timestamp=now,
            unit='req/s'
        )]

    def _collect_error_metrics(self) -> List[Metric]:
        """Collect error rate metrics"""
        now = datetime.utcnow()
        error_rate = random.uniform(0.0, 2.0)  # percentage

        return [Metric(
            metric_id='error_rate',
            metric_type=MetricType.ERROR_RATE,
            value=error_rate,
            timestamp=now,
            unit='%'
        )]

    def _collect_resource_metrics(self) -> List[Metric]:
        """Collect resource utilization metrics"""
        metrics = []
        now = datetime.utcnow()

        cpu_usage = random.uniform(30, 80)
        memory_usage = random.uniform(40, 75)

        metrics.append(Metric(
            metric_id='cpu_usage',
            metric_type=MetricType.CPU_USAGE,
            value=cpu_usage,
            timestamp=now,
            unit='%'
        ))

        metrics.append(Metric(
            metric_id='memory_usage',
            metric_type=MetricType.MEMORY_USAGE,
            value=memory_usage,
            timestamp=now,
            unit='%'
        ))

        return metrics

    def _collect_cache_metrics(self) -> List[Metric]:
        """Collect cache metrics"""
        now = datetime.utcnow()
        hit_rate = random.uniform(85, 98)  # percentage

        return [Metric(
            metric_id='cache_hit_rate',
            metric_type=MetricType.CACHE_HIT_RATE,
            value=hit_rate,
            timestamp=now,
            unit='%'
        )]

    def get_metric_history(self, metric_type: MetricType, hours: int = 24) -> List[Metric]:
        """Get historical data for a metric"""
        key = metric_type.value
        if key not in self.metrics_history:
            return []

        cutoff = datetime.utcnow() - timedelta(hours=hours)
        return [m for m in self.metrics_history[key] if m.timestamp > cutoff]

    def get_current_value(self, metric_type: MetricType) -> Optional[float]:
        """Get current value of a metric"""
        key = metric_type.value
        if key not in self.metrics_history or not self.metrics_history[key]:
            return None

        return self.metrics_history[key][-1].value


class AutoTuner:
    """Automatic performance tuner"""

    def __init__(self, config: TuningConfig, metrics_collector: MetricsCollector):
        self.config = config
        self.metrics_collector = metrics_collector
        self.optimization_history: List[Dict[str, Any]] = []
        self.current_config: Dict[str, Any] = {
            'cache_size': 1000,
            'batch_size': 100,
            'connection_pool': 20,
            'timeout': 30,
            'retry_count': 3,
            'parallelism': 4,
            'index_enabled': True,
            'query_optimized': True
        }

    def analyze_and_tune(self) -> List[OptimizationSuggestion]:
        """Analyze metrics and generate optimization suggestions"""
        if not self.config.enabled:
            return []

        # Collect current metrics
        metrics = self.metrics_collector.collect_all_metrics()

        # Analyze bottlenecks
        bottlenecks = self._identify_bottlenecks(metrics)

        # Generate suggestions
        suggestions = []
        for bottleneck in bottlenecks:
            suggestion = self._generate_suggestion(bottleneck, metrics)
            if suggestion:
                suggestions.append(suggestion)

        # Sort by expected improvement
        suggestions.sort(key=lambda s: s.expected_improvement, reverse=True)

        # Log analysis
        logger.info(f"Generated {len(suggestions)} optimization suggestions")

        return suggestions

    def _identify_bottlenecks(self, metrics: List[Metric]) -> List[Dict[str, Any]]:
        """Identify performance bottlenecks"""
        bottlenecks = []

        # Check latency
        p95_latency = next((m.value for m in metrics if m.metric_type == MetricType.LATENCY_P95), None)
        if p95_latency and p95_latency > self.config.thresholds.get('latency_p95_threshold', 200):
            bottlenecks.append({
                'type': 'high_latency',
                'metric': 'latency_p95',
                'value': p95_latency,
                'threshold': self.config.thresholds.get('latency_p95_threshold', 200)
            })

        # Check error rate
        error_rate = next((m.value for m in metrics if m.metric_type == MetricType.ERROR_RATE), None)
        if error_rate and error_rate > self.config.thresholds.get('error_rate_threshold', 1.0):
            bottlenecks.append({
                'type': 'high_error_rate',
                'metric': 'error_rate',
                'value': error_rate,
                'threshold': self.config.thresholds.get('error_rate_threshold', 1.0)
            })

        # Check CPU usage
        cpu_usage = next((m.value for m in metrics if m.metric_type == MetricType.CPU_USAGE), None)
        if cpu_usage and cpu_usage > self.config.thresholds.get('cpu_threshold', 70):
            bottlenecks.append({
                'type': 'high_cpu',
                'metric': 'cpu_usage',
                'value': cpu_usage,
                'threshold': self.config.thresholds.get('cpu_threshold', 70)
            })

        # Check cache hit rate
        cache_hit_rate = next((m.value for m in metrics if m.metric_type == MetricType.CACHE_HIT_RATE), None)
        if cache_hit_rate and cache_hit_rate < self.config.thresholds.get('cache_hit_rate_threshold', 90):
            bottlenecks.append({
                'type': 'low_cache_hit_rate',
                'metric': 'cache_hit_rate',
                'value': cache_hit_rate,
                'threshold': self.config.thresholds.get('cache_hit_rate_threshold', 90)
            })

        return bottlenecks

    def _generate_suggestion(self, bottleneck: Dict[str, Any], metrics: List[Metric]) -> Optional[OptimizationSuggestion]:
        """Generate optimization suggestion for a bottleneck"""
        suggestion_id = f"suggestion_{bottleneck['type']}_{datetime.utcnow().timestamp()}"

        if bottleneck['type'] == 'high_latency':
            return OptimizationSuggestion(
                suggestion_id=suggestion_id,
                optimization_type=OptimizationType.CACHE_SIZE,
                action=TuningAction.INCREASE,
                current_value=self.current_config['cache_size'],
                suggested_value=min(self.current_config['cache_size'] * 2, 10000),
                expected_improvement=0.25,
                confidence=0.8,
                risk_level='low',
                reason=f"P95 latency ({bottleneck['value']:.1f}ms) exceeds threshold ({bottleneck['threshold']}ms). Increasing cache size may reduce database queries.",
                metrics_affected=['latency_p95', 'latency_p99', 'throughput']
            )

        elif bottleneck['type'] == 'high_error_rate':
            return OptimizationSuggestion(
                suggestion_id=suggestion_id,
                optimization_type=OptimizationType.BATCH_SIZE,
                action=TuningAction.DECREASE,
                current_value=self.current_config['batch_size'],
                suggested_value=max(self.current_config['batch_size'] // 2, 10),
                expected_improvement=0.30,
                confidence=0.75,
                risk_level='medium',
                reason=f"Error rate ({bottleneck['value']:.2f}%) exceeds threshold ({bottleneck['threshold']}%). Reducing batch size may improve reliability.",
                metrics_affected=['error_rate', 'throughput']
            )

        elif bottleneck['type'] == 'high_cpu':
            return OptimizationSuggestion(
                suggestion_id=suggestion_id,
                optimization_type=OptimizationType.PARALLELISM,
                action=TuningAction.DECREASE,
                current_value=self.current_config['parallelism'],
                suggested_value=max(self.current_config['parallelism'] - 1, 1),
                expected_improvement=0.20,
                confidence=0.7,
                risk_level='low',
                reason=f"CPU usage ({bottleneck['value']:.1f}%) exceeds threshold ({bottleneck['threshold']}%). Reducing parallelism may lower CPU load.",
                metrics_affected=['cpu_usage', 'latency_p95']
            )

        elif bottleneck['type'] == 'low_cache_hit_rate':
            return OptimizationSuggestion(
                suggestion_id=suggestion_id,
                optimization_type=OptimizationType.CACHE_SIZE,
                action=TuningAction.INCREASE,
                current_value=self.current_config['cache_size'],
                suggested_value=min(self.current_config['cache_size'] * 1.5, 10000),
                expected_improvement=0.35,
                confidence=0.85,
                risk_level='low',
                reason=f"Cache hit rate ({bottleneck['value']:.1f}%) below threshold ({bottleneck['threshold']}%). Increasing cache size may improve hit rate.",
                metrics_affected=['cache_hit_rate', 'latency_p95', 'throughput']
            )

        return None

    def apply_optimization(self, suggestion: OptimizationSuggestion) -> bool:
        """Apply an optimization suggestion"""
        try:
            # Check safety limits
            if not self._is_safe_to_apply(suggestion):
                logger.warning(f"Optimization {suggestion.suggestion_id} not safe to apply")
                return False

            # Apply the optimization
            opt_type = suggestion.optimization_type.value
            new_value = suggestion.suggested_value

            if suggestion.action == TuningAction.INCREASE:
                self.current_config[opt_type] = new_value
            elif suggestion.action == TuningAction.DECREASE:
                self.current_config[opt_type] = new_value
            elif suggestion.action == TuningAction.SET:
                self.current_config[opt_type] = new_value
            elif suggestion.action == TuningAction.ENABLE:
                self.current_config[opt_type] = True
            elif suggestion.action == TuningAction.DISABLE:
                self.current_config[opt_type] = False

            # Log the change
            self.optimization_history.append({
                'suggestion_id': suggestion.suggestion_id,
                'optimization_type': opt_type,
                'old_value': suggestion.current_value,
                'new_value': new_value,
                'applied_at': datetime.utcnow().isoformat(),
                'status': 'applied'
            })

            logger.info(f"Applied optimization: {opt_type} {suggestion.action.value} to {new_value}")

            return True

        except Exception as e:
            logger.error(f"Failed to apply optimization {suggestion.suggestion_id}: {e}")
            return False

    def _is_safe_to_apply(self, suggestion: OptimizationSuggestion) -> bool:
        """Check if it's safe to apply an optimization"""
        opt_type = suggestion.optimization_type.value
        new_value = suggestion.suggested_value

        # Check safety limits
        if opt_type in self.config.safety_limits:
            limits = self.config.safety_limits[opt_type]
            if 'min' in limits and new_value < limits['min']:
                return False
            if 'max' in limits and new_value > limits['max']:
                return False

        # High risk optimizations require manual approval
        if suggestion.risk_level == 'high':
            return False

        return True

    def get_current_config(self) -> Dict[str, Any]:
        """Get current configuration"""
        return self.current_config.copy()

    def get_optimization_history(self) -> List[Dict[str, Any]]:
        """Get optimization history"""
        return self.optimization_history.copy()


class ABTestingFramework:
    """A/B testing framework for safe optimization rollout"""

    def __init__(self):
        self.active_tests: Dict[str, ABTest] = {}
        self.metrics_history: Dict[str, List[Dict[str, Any]]] = {}

    def create_test(self, name: str, variant_a: Dict[str, Any], variant_b: Dict[str, Any], traffic_split: float = 50) -> ABTest:
        """Create a new A/B test"""
        test_id = f"abtest_{name}_{datetime.utcnow().timestamp()}"

        test = ABTest(
            test_id=test_id,
            name=name,
            variant_a=variant_a,
            variant_b=variant_b,
            traffic_split=traffic_split,
            status='running',
            metrics={},
            started_at=datetime.utcnow()
        )

        self.active_tests[test_id] = test
        logger.info(f"Created A/B test: {test_id}")

        return test

    def assign_variant(self, test_id: str, user_id: str) -> str:
        """Assign user to a variant"""
        if test_id not in self.active_tests:
            raise ValueError(f"Test {test_id} not found")

        test = self.active_tests[test_id]
        if test.status != 'running':
            raise ValueError(f"Test {test_id} is not running")

        # Deterministic assignment based on user_id
        hash_value = hash(user_id) % 100
        if hash_value < (100 - test.traffic_split):
            return 'A'
        else:
            return 'B'

    def record_metric(self, test_id: str, variant: str, metric_name: str, value: float):
        """Record a metric for a test"""
        if test_id not in self.active_tests:
            return

        if test_id not in self.metrics_history:
            self.metrics_history[test_id] = []

        self.metrics_history[test_id].append({
            'variant': variant,
            'metric_name': metric_name,
            'value': value,
            'timestamp': datetime.utcnow().isoformat()
        })

    def analyze_test(self, test_id: str) -> Optional[Dict[str, Any]]:
        """Analyze test results"""
        if test_id not in self.active_tests:
            return None

        test = self.active_tests[test_id]
        if test.status != 'running':
            return {'status': 'completed', 'winner': test.metrics.get('winner', 'unknown')}

        # Collect metrics for both variants
        metrics = self.metrics_history.get(test_id, [])

        if not metrics:
            return None

        # Calculate averages
        variant_a_metrics = [m for m in metrics if m['variant'] == 'A']
        variant_b_metrics = [m for m in metrics if m['variant'] == 'B']

        if not variant_a_metrics or not variant_b_metrics:
            return None

        # Compare performance
        result = {
            'test_id': test_id,
            'status': 'running',
            'variant_a_count': len(variant_a_metrics),
            'variant_b_count': len(variant_b_metrics),
            'variant_a_avg': statistics.mean([m['value'] for m in variant_a_metrics]),
            'variant_b_avg': statistics.mean([m['value'] for m in variant_b_metrics])
        }

        return result

    def complete_test(self, test_id: str, winner: str) -> bool:
        """Complete a test and declare a winner"""
        if test_id not in self.active_tests:
            return False

        test = self.active_tests[test_id]
        test.status = 'completed'
        test.completed_at = datetime.utcnow()
        test.metrics['winner'] = winner

        logger.info(f"Completed A/B test {test_id}, winner: {winner}")

        return True

    def rollback_test(self, test_id: str) -> bool:
        """Rollback a test"""
        if test_id not in self.active_tests:
            return False

        test = self.active_tests[test_id]
        test.status = 'rolled_back'
        test.completed_at = datetime.utcnow()

        logger.warning(f"Rolled back A/B test {test_id}")

        return True


# API Handler Functions
async def get_metrics() -> List[Dict[str, Any]]:
    """Get current performance metrics"""
    pass

async def get_suggestions() -> List[Dict[str, Any]]:
    """Get optimization suggestions"""
    pass

async def apply_optimization(suggestion_id: str) -> Dict[str, Any]:
    """Apply an optimization"""
    pass

async def create_ab_test(name: str, variant_a: dict, variant_b: dict, traffic_split: float) -> Dict[str, Any]:
    """Create an A/B test"""
    pass

async def get_test_results(test_id: str) -> Dict[str, Any]:
    """Get A/B test results"""
    pass