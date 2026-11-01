"""
Advanced Analytics & AI Insights Module (V25)

This module provides:
- Real-time analytics dashboard
- AI-powered insights engine
- Automated report generation
- Knowledge graph visualization
- Recommendation system

Version: V25.0
Author: QUAN AI BRAIN Team
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import json
import statistics
from collections import Counter, defaultdict

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of analytics metrics"""
    COUNT = "count"
    RATE = "rate"
    AVERAGE = "average"
    TREND = "trend"
    DISTRIBUTION = "distribution"
    CORRELATION = "correlation"


class ChartType(Enum):
    """Types of charts"""
    LINE = "line"
    BAR = "bar"
    PIE = "pie"
    AREA = "area"
    SCATTER = "scatter"
    HEATMAP = "heatmap"
    GAUGE = "gauge"


class InsightType(Enum):
    """Types of AI insights"""
    PATTERN = "pattern"
    ANOMALY = "anomaly"
    TREND = "trend"
    CORRELATION = "correlation"
    PREDICTION = "prediction"
    RECOMMENDATION = "recommendation"


class Priority(Enum):
    """Insight priority levels"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class Metric:
    """Represents a single metric"""
    metric_id: str
    name: str
    value: float
    unit: str
    metric_type: MetricType
    timestamp: datetime
    change: Optional[float] = None  # Percentage change
    trend: Optional[str] = None  # 'up', 'down', 'stable'
    threshold_warning: Optional[float] = None
    threshold_critical: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'metric_id': self.metric_id,
            'name': self.name,
            'value': self.value,
            'unit': self.unit,
            'metric_type': self.metric_type.value,
            'timestamp': self.timestamp.isoformat(),
            'change': self.change,
            'trend': self.trend,
            'threshold_warning': self.threshold_warning,
            'threshold_critical': self.threshold_critical
        }


@dataclass
class ChartData:
    """Represents chart data"""
    chart_id: str
    chart_type: ChartType
    title: str
    data: List[Dict[str, Any]]
    x_axis: Optional[str] = None
    y_axis: Optional[str] = None
    color_scheme: str = "default"

    def to_dict(self) -> Dict[str, Any]:
        return {
            'chart_id': self.chart_id,
            'chart_type': self.chart_type.value,
            'title': self.title,
            'data': self.data,
            'x_axis': self.x_axis,
            'y_axis': self.y_axis,
            'color_scheme': self.color_scheme
        }


@dataclass
class Insight:
    """Represents an AI-generated insight"""
    insight_id: str
    insight_type: InsightType
    title: str
    description: str
    confidence: float
    impact: float  # 0-1
    priority: Priority
    evidence: List[str]
    recommendations: List[str]
    related_metrics: List[str]
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'insight_id': self.insight_id,
            'insight_type': self.insight_type.value,
            'title': self.title,
            'description': self.description,
            'confidence': self.confidence,
            'impact': self.impact,
            'priority': self.priority.value,
            'evidence': self.evidence,
            'recommendations': self.recommendations,
            'related_metrics': self.related_metrics,
            'created_at': self.created_at.isoformat()
        }


@dataclass
class Anomaly:
    """Represents a detected anomaly"""
    anomaly_id: str
    metric_name: str
    observed_value: float
    expected_value: float
    deviation: float
    timestamp: datetime
    severity: str  # 'low', 'medium', 'high', 'critical'
    description: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            'anomaly_id': self.anomaly_id,
            'metric_name': self.metric_name,
            'observed_value': self.observed_value,
            'expected_value': self.expected_value,
            'deviation': self.deviation,
            'timestamp': self.timestamp.isoformat(),
            'severity': self.severity,
            'description': self.description
        }


@dataclass
class Forecast:
    """Represents a forecast/prediction"""
    forecast_id: str
    metric_name: str
    predicted_values: List[Tuple[datetime, float]]
    confidence_intervals: List[Tuple[float, float]]
    model_used: str
    accuracy: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            'forecast_id': self.forecast_id,
            'metric_name': self.metric_name,
            'predicted_values': [(t.isoformat(), v) for t, v in self.predicted_values],
            'confidence_intervals': self.confidence_intervals,
            'model_used': self.model_used,
            'accuracy': self.accuracy
        }


class MetricsCalculator:
    """Calculates real-time metrics from knowledge base"""

    def __init__(self, db):
        self.db = db
        self._metrics_cache: Dict[str, Metric] = {}
        self._cache_ttl = 300  # 5 minutes

    def calculate_all_metrics(self) -> List[Metric]:
        """Calculate all available metrics"""
        metrics = []

        # Count metrics
        metrics.extend(self._calculate_count_metrics())

        # Quality metrics
        metrics.extend(self._calculate_quality_metrics())

        # Activity metrics
        metrics.extend(self._calculate_activity_metrics())

        # Freshness metrics
        metrics.extend(self._calculate_freshness_metrics())

        # Search metrics
        metrics.extend(self._calculate_search_metrics())

        return metrics

    def _calculate_count_metrics(self) -> List[Metric]:
        """Calculate count-based metrics"""
        metrics = []
        now = datetime.utcnow()

        # Total knowledge units
        total = self.db.count_knowledge_units()
        metrics.append(Metric(
            metric_id='total_ku',
            name='Total Knowledge Units',
            value=total,
            unit='units',
            metric_type=MetricType.COUNT,
            timestamp=now
        ))

        # By type
        by_type = self.db.count_by_type()
        for ku_type, count in by_type.items():
            metrics.append(Metric(
                metric_id=f'count_{ku_type}',
                name=f'{ku_type} Count',
                value=count,
                unit='units',
                metric_type=MetricType.COUNT,
                timestamp=now
            ))

        # By status
        by_status = self.db.count_by_status()
        for status, count in by_status.items():
            metrics.append(Metric(
                metric_id=f'count_{status}',
                name=f'{status} Count',
                value=count,
                unit='units',
                metric_type=MetricType.COUNT,
                timestamp=now
            ))

        return metrics

    def _calculate_quality_metrics(self) -> List[Metric]:
        """Calculate quality metrics"""
        metrics = []
        now = datetime.utcnow()

        # Average confidence
        avg_confidence = self.db.get_average_confidence()
        metrics.append(Metric(
            metric_id='avg_confidence',
            name='Average Confidence',
            value=avg_confidence,
            unit='score',
            metric_type=MetricType.AVERAGE,
            timestamp=now,
            threshold_warning=0.6,
            threshold_critical=0.4
        ))

        # Verified rate
        total = self.db.count_knowledge_units()
        verified = self.db.count_by_status('VERIFIED')
        verified_rate = verified / total if total > 0 else 0
        metrics.append(Metric(
            metric_id='verified_rate',
            name='Verified Rate',
            value=verified_rate,
            unit='ratio',
            metric_type=MetricType.RATE,
            timestamp=now,
            threshold_warning=0.5,
            threshold_critical=0.3
        ))

        return metrics

    def _calculate_activity_metrics(self) -> List[Metric]:
        """Calculate activity metrics"""
        metrics = []
        now = datetime.utcnow()

        # Recent creates (24h)
        creates_24h = self.db.count_recent('created_at_utc', hours=24)
        metrics.append(Metric(
            metric_id='creates_24h',
            name='Creates (24h)',
            value=creates_24h,
            unit='count',
            metric_type=MetricType.COUNT,
            timestamp=now
        ))

        # Recent updates (24h)
        updates_24h = self.db.count_recent('updated_at_utc', hours=24)
        metrics.append(Metric(
            metric_id='updates_24h',
            name='Updates (24h)',
            value=updates_24h,
            unit='count',
            metric_type=MetricType.COUNT,
            timestamp=now
        ))

        return metrics

    def _calculate_freshness_metrics(self) -> List[Metric]:
        """Calculate freshness metrics"""
        metrics = []
        now = datetime.utcnow()

        # Average age
        avg_age = self.db.get_average_age()
        metrics.append(Metric(
            metric_id='avg_age',
            name='Average Age',
            value=avg_age.total_days,
            unit='days',
            metric_type=MetricType.AVERAGE,
            timestamp=now,
            threshold_warning=30,
            threshold_critical=90
        ))

        # Stale count (>90 days)
        stale = self.db.count_stale(days=90)
        metrics.append(Metric(
            metric_id='stale_count',
            name='Stale Knowledge Units',
            value=stale,
            unit='units',
            metric_type=MetricType.COUNT,
            timestamp=now,
            threshold_warning=10,
            threshold_critical=50
        ))

        return metrics

    def _calculate_search_metrics(self) -> List[Metric]:
        """Calculate search-related metrics"""
        metrics = []
        now = datetime.utcnow()

        # Total searches (24h)
        searches_24h = self.db.count_searches(hours=24)
        metrics.append(Metric(
            metric_id='searches_24h',
            name='Searches (24h)',
            value=searches_24h,
            unit='queries',
            metric_type=MetricType.COUNT,
            timestamp=now
        ))

        # Average results per search
        avg_results = self.db.get_average_search_results()
        metrics.append(Metric(
            metric_id='avg_search_results',
            name='Avg Search Results',
            value=avg_results,
            unit='results',
            metric_type=MetricType.AVERAGE,
            timestamp=now
        ))

        return metrics

    def get_metric(self, metric_id: str) -> Optional[Metric]:
        """Get a specific metric"""
        if metric_id in self._metrics_cache:
            return self._metrics_cache[metric_id]
        return None


class TrendAnalyzer:
    """Analyzes trends in metrics over time"""

    def __init__(self, db):
        self.db = db

    def analyze_trend(self, metric_name: str, period: str = '7d') -> Dict[str, Any]:
        """Analyze trend for a metric"""
        # Get historical data
        data_points = self._get_historical_data(metric_name, period)

        if len(data_points) < 2:
            return {'trend': 'insufficient_data', 'data': []}

        # Calculate trend direction
        values = [dp['value'] for dp in data_points]
        slope = self._calculate_slope(values)

        if slope > 0.05:
            trend = 'up'
        elif slope < -0.05:
            trend = 'down'
        else:
            trend = 'stable'

        # Calculate statistics
        stats = {
            'trend': trend,
            'slope': slope,
            'mean': statistics.mean(values),
            'std': statistics.stdev(values) if len(values) > 1 else 0,
            'min': min(values),
            'max': max(values),
            'data': data_points
        }

        return stats

    def _get_historical_data(self, metric_name: str, period: str) -> List[Dict[str, Any]]:
        """Get historical data points"""
        # Parse period
        if period == '24h':
            hours = 24
            granularity = 'hour'
        elif period == '7d':
            hours = 168
            granularity = 'hour'
        elif period == '30d':
            hours = 720
            granularity = 'day'
        else:
            hours = 168
            granularity = 'hour'

        # Query database for historical data
        data = self.db.get_metric_history(metric_name, hours, granularity)

        return data

    def _calculate_slope(self, values: List[float]) -> float:
        """Calculate linear regression slope"""
        if len(values) < 2:
            return 0.0

        n = len(values)
        x = list(range(n))
        x_mean = sum(x) / n
        y_mean = sum(values) / n

        numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return 0.0

        return numerator / denominator


class AnomalyDetector:
    """Detects anomalies in metrics using statistical methods"""

    def __init__(self, db):
        self.db = db
        self.baseline_window = 7  # days
        self.threshold_std = 2.0  # standard deviations

    def detect_anomalies(self) -> List[Anomaly]:
        """Detect anomalies across all metrics"""
        anomalies = []

        # Key metrics to monitor
        metrics_to_monitor = [
            'creates_24h',
            'updates_24h',
            'searches_24h',
            'avg_confidence',
            'verified_rate'
        ]

        for metric_name in metrics_to_monitor:
            anomaly = self._check_metric_anomaly(metric_name)
            if anomaly:
                anomalies.append(anomaly)

        return anomalies

    def _check_metric_anomaly(self, metric_name: str) -> Optional[Anomaly]:
        """Check if a metric has an anomaly"""
        # Get current value
        current = self.db.get_current_metric_value(metric_name)
        if current is None:
            return None

        # Get baseline (historical average)
        baseline = self._get_baseline(metric_name)
        if baseline is None:
            return None

        # Calculate deviation
        if baseline['std'] == 0:
            deviation = 0
        else:
            deviation = (current - baseline['mean']) / baseline['std']

        # Check if anomaly
        if abs(deviation) > self.threshold_std:
            severity = 'critical' if abs(deviation) > 3 else 'high' if abs(deviation) > 2.5 else 'medium'

            return Anomaly(
                anomaly_id=f'anomaly_{metric_name}_{datetime.utcnow().timestamp()}',
                metric_name=metric_name,
                observed_value=current,
                expected_value=baseline['mean'],
                deviation=deviation,
                timestamp=datetime.utcnow(),
                severity=severity,
                description=f'{metric_name} is {deviation:.1f} standard deviations from baseline'
            )

        return None

    def _get_baseline(self, metric_name: str) -> Optional[Dict[str, float]]:
        """Get baseline statistics for a metric"""
        history = self.db.get_metric_history(metric_name, hours=168 * self.baseline_window, granularity='hour')

        if not history:
            return None

        values = [dp['value'] for dp in history]

        return {
            'mean': statistics.mean(values),
            'std': statistics.stdev(values) if len(values) > 1 else 0
        }


class InsightsGenerator:
    """Generates AI-powered insights from analytics data"""

    def __init__(self, db):
        self.db = db
        self.calculator = MetricsCalculator(db)
        self.trend_analyzer = TrendAnalyzer(db)
        self.anomaly_detector = AnomalyDetector(db)

    def generate_insights(self) -> List[Insight]:
        """Generate all insights"""
        insights = []

        # Pattern insights
        insights.extend(self._generate_pattern_insights())

        # Trend insights
        insights.extend(self._generate_trend_insights())

        # Anomaly insights
        insights.extend(self._generate_anomaly_insights())

        # Correlation insights
        insights.extend(self._generate_correlation_insights())

        # Recommendation insights
        insights.extend(self._generate_recommendation_insights())

        # Sort by priority
        insights.sort(key=lambda i: i.priority.value)

        return insights

    def _generate_pattern_insights(self) -> List[Insight]:
        """Generate pattern-based insights"""
        insights = []

        # Check for common patterns
        patterns = self._detect_patterns()

        for pattern in patterns:
            insight = Insight(
                insight_id=f'insight_pattern_{pattern["type"]}',
                insight_type=InsightType.PATTERN,
                title=pattern['title'],
                description=pattern['description'],
                confidence=pattern['confidence'],
                impact=pattern['impact'],
                priority=Priority.MEDIUM,
                evidence=pattern['evidence'],
                recommendations=pattern['recommendations'],
                related_metrics=pattern['metrics']
            )
            insights.append(insight)

        return insights

    def _detect_patterns(self) -> List[Dict[str, Any]]:
        """Detect common patterns in data"""
        patterns = []

        # Example: Check for temporal patterns
        creates_by_hour = self.db.get_creates_by_hour()
        if creates_by_hour:
            peak_hour = max(creates_by_hour, key=creates_by_hour.get)
            patterns.append({
                'type': 'temporal',
                'title': f'Peak Activity at Hour {peak_hour}',
                'description': f'Most knowledge creation happens at hour {peak_hour}:00',
                'confidence': 0.8,
                'impact': 0.6,
                'evidence': [f'Peak hour: {peak_hour}', f'Average: {sum(creates_by_hour.values()) / len(creates_by_hour):.1f}'],
                'recommendations': ['Schedule maintenance during low-activity hours', 'Plan capacity for peak hours'],
                'metrics': ['creates_24h']
            })

        return patterns

    def _generate_trend_insights(self) -> List[Insight]:
        """Generate trend-based insights"""
        insights = []

        # Analyze key metrics
        metrics = ['creates_24h', 'avg_confidence', 'verified_rate']

        for metric in metrics:
            trend_data = self.trend_analyzer.analyze_trend(metric, '7d')

            if trend_data['trend'] != 'insufficient_data':
                if trend_data['trend'] == 'up':
                    title = f'Increasing {metric}'
                    impact = 0.7
                elif trend_data['trend'] == 'down':
                    title = f'Declining {metric}'
                    impact = 0.8
                else:
                    title = f'Stable {metric}'
                    impact = 0.3

                insight = Insight(
                    insight_id=f'insight_trend_{metric}',
                    insight_type=InsightType.TREND,
                    title=title,
                    description=f'{metric} shows {trend_data["trend"]} trend over the past 7 days',
                    confidence=0.85,
                    impact=impact,
                    priority=Priority.HIGH if trend_data['trend'] == 'down' else Priority.LOW,
                    evidence=[f'Slope: {trend_data["slope"]:.3f}', f'Mean: {trend_data["mean"]:.2f}'],
                    recommendations=[f'Monitor {metric} closely', 'Investigate causes of trend'],
                    related_metrics=[metric]
                )
                insights.append(insight)

        return insights

    def _generate_anomaly_insights(self) -> List[Insight]:
        """Generate anomaly-based insights"""
        insights = []

        anomalies = self.anomaly_detector.detect_anomalies()

        for anomaly in anomalies:
            insight = Insight(
                insight_id=f'insight_anomaly_{anomaly.anomaly_id}',
                insight_type=InsightType.ANOMALY,
                title=f'Anomaly Detected: {anomaly.metric_name}',
                description=anomaly.description,
                confidence=0.9,
                impact=0.9 if anomaly.severity == 'critical' else 0.7,
                priority=Priority.CRITICAL if anomaly.severity == 'critical' else Priority.HIGH,
                evidence=[f'Observed: {anomaly.observed_value}', f'Expected: {anomaly.expected_value:.2f}', f'Deviation: {anomaly.deviation:.2f}σ'],
                recommendations=['Investigate root cause', 'Check for system issues', 'Review recent changes'],
                related_metrics=[anomaly.metric_name]
            )
            insights.append(insight)

        return insights

    def _generate_correlation_insights(self) -> List[Insight]:
        """Generate correlation-based insights"""
        insights = []

        # Example: Check correlation between searches and creates
        correlation = self._calculate_correlation('searches_24h', 'creates_24h')

        if abs(correlation) > 0.7:
            direction = 'positive' if correlation > 0 else 'negative'
            insight = Insight(
                insight_id='insight_correlation_search_create',
                insight_type=InsightType.CORRELATION,
                title=f'Strong {direction.title()} Correlation: Searches ↔ Creates',
                description=f'Searches and creates are {direction}ly correlated (r={correlation:.2f})',
                confidence=0.8,
                impact=0.6,
                priority=Priority.MEDIUM,
                evidence=[f'Correlation coefficient: {correlation:.2f}', 'High searches may lead to more creates'],
                recommendations=['Optimize search to improve discovery', 'Encourage creation after searches'],
                related_metrics=['searches_24h', 'creates_24h']
            )
            insights.append(insight)

        return insights

    def _generate_recommendation_insights(self) -> List[Insight]:
        """Generate recommendation insights"""
        insights = []

        # Check for actionable recommendations
        metrics = self.calculator.calculate_all_metrics()

        for metric in metrics:
            if metric.threshold_warning and metric.value < metric.threshold_warning:
                insight = Insight(
                    insight_id=f'insight_recommendation_{metric.metric_id}',
                    insight_type=InsightType.RECOMMENDATION,
                    title=f'Action Required: {metric.name}',
                    description=f'{metric.name} is below warning threshold ({metric.value:.2f} < {metric.threshold_warning})',
                    confidence=0.95,
                    impact=0.8,
                    priority=Priority.HIGH,
                    evidence=[f'Current: {metric.value:.2f}', f'Threshold: {metric.threshold_warning}'],
                    recommendations=[f'Investigate low {metric.name}', 'Take corrective action'],
                    related_metrics=[metric.metric_id]
                )
                insights.append(insight)

        return insights

    def _calculate_correlation(self, metric1: str, metric2: str) -> float:
        """Calculate correlation between two metrics"""
        history1 = self.db.get_metric_history(metric1, hours=168, granularity='hour')
        history2 = self.db.get_metric_history(metric2, hours=168, granularity='hour')

        if not history1 or not history2 or len(history1) != len(history2):
            return 0.0

        values1 = [dp['value'] for dp in history1]
        values2 = [dp['value'] for dp in history2]

        # Pearson correlation
        n = len(values1)
        mean1 = sum(values1) / n
        mean2 = sum(values2) / n

        numerator = sum((values1[i] - mean1) * (values2[i] - mean2) for i in range(n))
        denom1 = sum((values1[i] - mean1) ** 2 for i in range(n)) ** 0.5
        denom2 = sum((values2[i] - mean2) ** 2 for i in range(n)) ** 0.5

        if denom1 == 0 or denom2 == 0:
            return 0.0

        return numerator / (denom1 * denom2)


# API Handler Functions
async def get_all_metrics() -> Dict[str, Any]:
    """Get all metrics"""
    # Implementation depends on db connection
    pass


async def get_trend(metric_name: str, period: str) -> Dict[str, Any]:
    """Get trend analysis for a metric"""
    pass


async def get_anomalies() -> List[Dict[str, Any]]:
    """Get detected anomalies"""
    pass


async def get_insights() -> List[Dict[str, Any]]:
    """Get all insights"""
    pass


async def get_forecast(metric_name: str, days: int) -> Dict[str, Any]:
    """Get forecast for a metric"""
    pass