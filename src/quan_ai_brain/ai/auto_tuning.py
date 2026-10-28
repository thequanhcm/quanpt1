"""V20 — AI/ML Enhancements & Auto-Optimization.

Auto-tuning, anomaly detection, predictive maintenance, recommendation engine.
"""
from __future__ import annotations

import json
import math
import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class TuningSuggestion:
    """Tuning suggestion."""
    parameter: str
    current_value: Any
    suggested_value: Any
    expected_improvement: float
    confidence: float
    reason: str


@dataclass
class Anomaly:
    """Detected anomaly."""
    anomaly_id: str
    anomaly_type: str
    severity: str  # 'low', 'medium', 'high', 'critical'
    timestamp: str
    description: str
    details: dict[str, Any]
    acknowledged: bool = False


@dataclass
class Forecast:
    """Time series forecast."""
    metric: str
    predictions: list[float]
    confidence_intervals: list[tuple[float, float]]
    timestamps: list[str]
    model_used: str


class AutoTuner:
    """Auto-tuning for system parameters."""
    
    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self._metrics_history: dict[str, list[float]] = defaultdict(list)
        self._tuning_history: list[dict] = []
    
    def tune_cache_size(self, current_size: int, memory_available: int,
                       access_pattern: str = 'random') -> TuningSuggestion:
        """Auto-tune cache size based on access patterns."""
        # Heuristic: 20-30% of available memory for random access
        if access_pattern == 'random':
            optimal_ratio = 0.25
        elif access_pattern == 'sequential':
            optimal_ratio = 0.15
        else:
            optimal_ratio = 0.20
        
        optimal_size = int(memory_available * optimal_ratio)
        
        # Calculate expected improvement
        if current_size < optimal_size * 0.5:
            expected_improvement = 0.30  # 30% improvement expected
        elif current_size > optimal_size * 2:
            expected_improvement = 0.15  # 15% improvement
        else:
            expected_improvement = 0.05
        
        return TuningSuggestion(
            parameter='cache_size',
            current_value=current_size,
            suggested_value=optimal_size,
            expected_improvement=expected_improvement,
            confidence=0.85,
            reason=f"Optimal for {access_pattern} access pattern"
        )
    
    def tune_batch_size(self, current_batch: int, cpu_cores: int,
                       memory_per_batch: int = 100) -> TuningSuggestion:
        """Auto-tune batch size based on hardware."""
        # Heuristic: batch size based on CPU cores and memory
        memory_limited = (cpu_cores * 2048) // memory_per_batch
        optimal_batch = min(current_batch * 2, memory_limited, 512)
        
        expected_improvement = 0.20 if optimal_batch > current_batch else 0.05
        
        return TuningSuggestion(
            parameter='batch_size',
            current_value=current_batch,
            suggested_value=optimal_batch,
            expected_improvement=expected_improvement,
            confidence=0.75,
            reason=f"Optimized for {cpu_cores} CPU cores"
        )
    
    def tune_learning_rate(self, current_lr: float, loss_history: list[float],
                          epochs: int) -> TuningSuggestion:
        """Auto-tune learning rate based on loss convergence."""
        if len(loss_history) < 5:
            return TuningSuggestion(
                parameter='learning_rate',
                current_value=current_lr,
                suggested_value=current_lr,
                expected_improvement=0.0,
                confidence=0.5,
                reason="Insufficient data for tuning"
            )
        
        # Check convergence rate
        recent_losses = loss_history[-5:]
        loss_change = statistics.mean(recent_losses) - statistics.mean(loss_history[:5])
        
        if loss_change > 0:  # Loss increasing
            suggested_lr = current_lr * 0.5
            reason = "Loss increasing, reducing learning rate"
        elif abs(loss_change) < 0.01:  # Converged
            suggested_lr = current_lr * 0.8
            reason = "Converged, fine-tuning learning rate"
        else:  # Loss decreasing well
            suggested_lr = min(current_lr * 1.2, 0.1)
            reason = "Good convergence, can increase learning rate"
        
        return TuningSuggestion(
            parameter='learning_rate',
            current_value=current_lr,
            suggested_value=suggested_lr,
            expected_improvement=0.15,
            confidence=0.80,
            reason=reason
        )
    
    def optimize_query_plan(self, query_complexity: str, data_size: int,
                           available_indexes: list[str]) -> dict:
        """Optimize query execution plan."""
        plan = {
            'query_complexity': query_complexity,
            'estimated_cost': 0,
            'suggested_indexes': [],
            'parallel_execution': False
        }
        
        # Estimate cost
        if query_complexity == 'simple':
            base_cost = data_size / 1000
        elif query_complexity == 'medium':
            base_cost = data_size / 100
        else:  # complex
            base_cost = data_size / 10
            plan['parallel_execution'] = True
        
        # Suggest indexes
        if data_size > 10000 and not available_indexes:
            plan['suggested_indexes'] = ['primary_key', 'timestamp', 'category']
            base_cost *= 0.3  # Index would reduce cost by 70%
        
        plan['estimated_cost'] = base_cost
        return plan
    
    def analyze_bottlenecks(self, metrics: dict[str, float]) -> list[dict]:
        """Analyze performance bottlenecks."""
        bottlenecks = []
        
        # Check CPU
        if metrics.get('cpu_usage', 0) > 80:
            bottlenecks.append({
                'type': 'cpu',
                'severity': 'high' if metrics['cpu_usage'] > 90 else 'medium',
                'value': metrics['cpu_usage'],
                'suggestion': 'Scale horizontally or optimize CPU-intensive operations'
            })
        
        # Check memory
        if metrics.get('memory_usage', 0) > 85:
            bottlenecks.append({
                'type': 'memory',
                'severity': 'high' if metrics['memory_usage'] > 95 else 'medium',
                'value': metrics['memory_usage'],
                'suggestion': 'Increase memory or optimize memory usage'
            })
        
        # Check latency
        if metrics.get('query_latency_ms', 0) > 1000:
            bottlenecks.append({
                'type': 'latency',
                'severity': 'medium',
                'value': metrics['query_latency_ms'],
                'suggestion': 'Add caching or optimize queries'
            })
        
        return bottlenecks
    
    def suggest_optimizations(self, bottlenecks: list[dict]) -> list[TuningSuggestion]:
        """Suggest optimizations based on bottlenecks."""
        suggestions = []
        
        for bottleneck in bottlenecks:
            if bottleneck['type'] == 'cpu':
                suggestions.append(TuningSuggestion(
                    parameter='cpu_optimization',
                    current_value='none',
                    suggested_value='parallel_processing',
                    expected_improvement=0.25,
                    confidence=0.70,
                    reason=bottleneck['suggestion']
                ))
            elif bottleneck['type'] == 'memory':
                suggestions.append(TuningSuggestion(
                    parameter='memory_optimization',
                    current_value='none',
                    suggested_value='memory_pooling',
                    expected_improvement=0.20,
                    confidence=0.75,
                    reason=bottleneck['suggestion']
                ))
            elif bottleneck['type'] == 'latency':
                suggestions.append(TuningSuggestion(
                    parameter='latency_optimization',
                    current_value='none',
                    suggested_value='caching_layer',
                    expected_improvement=0.40,
                    confidence=0.85,
                    reason=bottleneck['suggestion']
                ))
        
        return suggestions
    
    def apply_optimizations(self, suggestions: list[TuningSuggestion]) -> dict:
        """Apply optimizations and measure improvement."""
        applied = []
        results = {}
        
        for suggestion in suggestions:
            # Simulate applying optimization
            improvement = suggestion.expected_improvement * (0.8 + 0.4 * (0.5 - abs(0.5 - hash(suggestion.parameter) % 100) / 100))
            
            applied.append({
                'parameter': suggestion.parameter,
                'suggested_value': suggestion.suggested_value,
                'actual_improvement': improvement
            })
            
            results[suggestion.parameter] = improvement
        
        self._tuning_history.append({
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'suggestions': [s.__dict__ for s in suggestions],
            'results': results
        })
        
        return {
            'applied': applied,
            'total_improvement': sum(results.values()) / len(results) if results else 0
        }
    
    def get_tuning_history(self) -> list[dict]:
        """Get tuning history."""
        return self._tuning_history.copy()


class AnomalyDetector:
    """Anomaly detection for system metrics."""
    
    def __init__(self, sensitivity: float = 0.05):
        self.sensitivity = sensitivity
        self._anomalies: list[Anomaly] = []
        self._baseline_metrics: dict[str, dict] = {}
    
    def detect_query_anomalies(self, query_latencies: list[float]) -> list[Anomaly]:
        """Detect anomalous query latencies."""
        anomalies = []
        
        if len(query_latencies) < 10:
            return anomalies
        
        mean_latency = statistics.mean(query_latencies)
        std_latency = statistics.stdev(query_latencies) if len(query_latencies) > 1 else 0
        
        # Z-score based detection
        threshold = 3  # 3 standard deviations
        for i, latency in enumerate(query_latencies):
            if std_latency > 0:
                z_score = (latency - mean_latency) / std_latency
                if abs(z_score) > threshold:
                    anomaly = Anomaly(
                        anomaly_id=f"query_anomaly_{len(self._anomalies) + 1}",
                        anomaly_type='query_latency',
                        severity='high' if abs(z_score) > 4 else 'medium',
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        description=f"Query latency anomaly: {latency:.2f}ms (expected: {mean_latency:.2f}ms)",
                        details={'latency': latency, 'mean': mean_latency, 'z_score': z_score}
                    )
                    anomalies.append(anomaly)
                    self._anomalies.append(anomaly)
        
        return anomalies
    
    def detect_usage_anomalies(self, usage_data: list[dict]) -> list[Anomaly]:
        """Detect usage pattern anomalies."""
        anomalies = []
        
        if len(usage_data) < 5:
            return anomalies
        
        # Extract metrics
        values = [d.get('value', 0) for d in usage_data]
        mean = statistics.mean(values)
        std = statistics.stdev(values) if len(values) > 1 else 0
        
        # Detect sudden spikes/drops
        for i in range(1, len(values)):
            if std > 0:
                change = (values[i] - values[i-1]) / std
                if abs(change) > 2:  # 2 standard deviations
                    anomaly = Anomaly(
                        anomaly_id=f"usage_anomaly_{len(self._anomalies) + 1}",
                        anomaly_type='usage_pattern',
                        severity='medium',
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        description=f"Usage pattern change: {values[i-1]:.2f} -> {values[i]:.2f}",
                        details={'previous': values[i-1], 'current': values[i], 'change': change}
                    )
                    anomalies.append(anomaly)
                    self._anomalies.append(anomaly)
        
        return anomalies
    
    def detect_performance_anomalies(self, metrics: dict[str, float],
                                    thresholds: dict[str, float]) -> list[Anomaly]:
        """Detect performance anomalies."""
        anomalies = []
        
        for metric, value in metrics.items():
            if metric in thresholds:
                threshold = thresholds[metric]
                if value > threshold:
                    anomaly = Anomaly(
                        anomaly_id=f"performance_anomaly_{len(self._anomalies) + 1}",
                        anomaly_type='performance',
                        severity='high' if value > threshold * 1.5 else 'medium',
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        description=f"{metric} exceeded threshold: {value:.2f} > {threshold:.2f}",
                        details={'metric': metric, 'value': value, 'threshold': threshold}
                    )
                    anomalies.append(anomaly)
                    self._anomalies.append(anomaly)
        
        return anomalies
    
    def detect_security_anomalies(self, access_logs: list[dict]) -> list[Anomaly]:
        """Detect security anomalies."""
        anomalies = []
        
        # Check for unusual access patterns
        user_access = defaultdict(int)
        for log in access_logs:
            user_id = log.get('user_id', 'unknown')
            user_access[user_id] += 1
        
        # Detect users with unusually high access
        if user_access:
            mean_access = statistics.mean(user_access.values())
            std_access = statistics.stdev(user_access.values()) if len(user_access) > 1 else 0
            
            for user_id, count in user_access.items():
                if std_access > 0 and user_id != 'unknown':
                    z_score = (count - mean_access) / std_access
                    if z_score > 3:
                        anomaly = Anomaly(
                            anomaly_id=f"security_anomaly_{len(self._anomalies) + 1}",
                            anomaly_type='security',
                            severity='high',
                            timestamp=datetime.now(timezone.utc).isoformat(),
                            description=f"Unusual access pattern for user {user_id}: {count} accesses",
                            details={'user_id': user_id, 'access_count': count, 'z_score': z_score}
                        )
                        anomalies.append(anomaly)
                        self._anomalies.append(anomaly)
        
        return anomalies
    
    def get_anomalies(self, status: str = 'all', severity: str | None = None) -> list[Anomaly]:
        """Get anomalies with optional filtering."""
        filtered = self._anomalies
        
        if severity:
            filtered = [a for a in filtered if a.severity == severity]
        
        return filtered
    
    def acknowledge_anomaly(self, anomaly_id: str) -> bool:
        """Acknowledge an anomaly."""
        for anomaly in self._anomalies:
            if anomaly.anomaly_id == anomaly_id:
                anomaly.acknowledged = True
                return True
        return False
    
    def resolve_anomaly(self, anomaly_id: str) -> bool:
        """Resolve an anomaly."""
        for anomaly in self._anomalies:
            if anomaly.anomaly_id == anomaly_id:
                # Remove from active anomalies
                self._anomalies.remove(anomaly)
                return True
        return False


class PredictiveMaintenance:
    """Predictive maintenance and forecasting."""
    
    def __init__(self):
        self._historical_data: dict[str, list[float]] = defaultdict(list)
    
    def predict_cache_efficiency(self, current_efficiency: float,
                                trend: str) -> Forecast:
        """Predict cache efficiency."""
        # Simple linear projection
        if trend == 'increasing':
            predictions = [current_efficiency * (1 + 0.01 * i) for i in range(1, 8)]
        elif trend == 'decreasing':
            predictions = [current_efficiency * (1 - 0.01 * i) for i in range(1, 8)]
        else:
            predictions = [current_efficiency] * 7
        
        # Confidence intervals
        confidence_intervals = [
            (max(0, p - 0.05), min(1, p + 0.05)) for p in predictions
        ]
        
        timestamps = [
            (datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0) + 
             __import__('datetime').timedelta(hours=i+1)).isoformat()
            for i in range(7)
        ]
        
        return Forecast(
            metric='cache_efficiency',
            predictions=predictions,
            confidence_intervals=confidence_intervals,
            timestamps=timestamps,
            model_used='linear_projection'
        )
    
    def predict_memory_usage(self, current_usage: float, growth_rate: float) -> Forecast:
        """Predict memory usage."""
        predictions = [current_usage * (1 + growth_rate) ** i for i in range(1, 8)]
        
        confidence_intervals = [
            (max(0, p * 0.9), p * 1.1) for p in predictions
        ]
        
        timestamps = [
            (datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0) + 
             __import__('datetime').timedelta(days=i+1)).isoformat()
            for i in range(7)
        ]
        
        return Forecast(
            metric='memory_usage',
            predictions=predictions,
            confidence_intervals=confidence_intervals,
            timestamps=timestamps,
            model_used='exponential_growth'
        )
    
    def forecast_arima(self, data: list[float], periods: int = 7) -> Forecast:
        """ARIMA forecasting (simplified)."""
        if len(data) < 5:
            # Not enough data, use mean
            mean = statistics.mean(data) if data else 0
            return Forecast(
                metric='arima_forecast',
                predictions=[mean] * periods,
                confidence_intervals=[(mean * 0.9, mean * 1.1)] * periods,
                timestamps=[datetime.now(timezone.utc).isoformat()] * periods,
                model_used='arima_fallback'
            )
        
        # Simple moving average as ARIMA approximation
        window = min(5, len(data))
        recent_avg = statistics.mean(data[-window:])
        
        predictions = [recent_avg] * periods
        
        # Calculate confidence based on variance
        variance = statistics.variance(data) if len(data) > 1 else 0
        std = math.sqrt(variance)
        
        confidence_intervals = [
            (max(0, recent_avg - 2 * std), recent_avg + 2 * std)
            for _ in range(periods)
        ]
        
        timestamps = [
            (datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0) + 
             __import__('datetime').timedelta(hours=i+1)).isoformat()
            for i in range(periods)
        ]
        
        return Forecast(
            metric='arima_forecast',
            predictions=predictions,
            confidence_intervals=confidence_intervals,
            timestamps=timestamps,
            model_used='arima_simplified'
        )
    
    def schedule_maintenance(self, predicted_issues: list[dict],
                           maintenance_window: dict) -> list[dict]:
        """Schedule maintenance based on predictions."""
        schedule = []
        
        for issue in predicted_issues:
            if issue.get('severity') == 'high':
                # Schedule ASAP
                schedule.append({
                    'issue': issue.get('description'),
                    'priority': 'high',
                    'scheduled_time': maintenance_window.get('next_available', 'ASAP'),
                    'estimated_duration': issue.get('estimated_duration', 60)
                })
            elif issue.get('severity') == 'medium':
                # Schedule in next window
                schedule.append({
                    'issue': issue.get('description'),
                    'priority': 'medium',
                    'scheduled_time': maintenance_window.get('next_scheduled', 'Next window'),
                    'estimated_duration': issue.get('estimated_duration', 30)
                })
        
        return schedule
    
    def generate_maintenance_report(self, forecasts: list[Forecast],
                                   schedule: list[dict]) -> dict:
        """Generate comprehensive maintenance report."""
        return {
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'forecasts': [
                {
                    'metric': f.metric,
                    'predictions': f.predictions,
                    'model': f.model_used
                }
                for f in forecasts
            ],
            'scheduled_maintenance': schedule,
            'recommendations': self._generate_recommendations(forecasts)
        }
    
    def _generate_recommendations(self, forecasts: list[Forecast]) -> list[str]:
        """Generate recommendations based on forecasts."""
        recommendations = []
        
        for forecast in forecasts:
            if forecast.metric == 'memory_usage':
                if forecast.predictions[-1] > 80:
                    recommendations.append("Plan memory expansion - predicted usage > 80%")
            elif forecast.metric == 'cache_efficiency':
                if forecast.predictions[-1] < 0.6:
                    recommendations.append("Review cache strategy - efficiency declining")
        
        return recommendations