"""
AI Insights Engine Module (V25.2)

Rule-based insight generation built on top of the V25.1 analytics engine:
- anomaly -> insight bridging (severity mapped to confidence/impact/priority)
- trend -> insight with an explicit forecast note (slope projection)
- correlation heuristic (Pearson) across numeric series -> correlation insights
- metric threshold breaches -> recommendation insights
- scoring as impact x confidence with priority derivation
- dedupe of similar insights (token Jaccard within the same insight type)

Standard library only. Reuses dataclasses and enums from
``quan_ai_brain.analytics.analytics_engine`` (M1 - reused, not modified).

Version: V25.2
Author: QUAN AI BRAIN Team
"""

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple

from quan_ai_brain.analytics.analytics_engine import (
    Anomaly,
    Insight,
    InsightType,
    Metric,
    Priority,
)

logger = logging.getLogger(__name__)

# Common filler words ignored when comparing insight texts for similarity.
_STOPWORDS = frozenset({
    'a', 'an', 'the', 'is', 'are', 'was', 'were', 'of', 'to', 'in', 'on',
    'for', 'and', 'or', 'with', 'at', 'by', 'from', 'over', 'than', 'this',
    'that', 'it', 'its', 'be', 'been', 'shows', 'show', 'detected',
})


def _tokens(text: str) -> set:
    """Lowercase alphanumeric token set with stopwords removed."""
    words = re.findall(r"[a-z0-9]+", (text or "").lower())
    return {w for w in words if w not in _STOPWORDS}


def pearson_correlation(xs: Sequence[float], ys: Sequence[float]) -> float:
    """
    Heuristic Pearson correlation coefficient between two numeric series.

    Returns 0.0 for degenerate inputs (length mismatch, fewer than 2 points,
    or a constant series) instead of raising.
    """
    if xs is None or ys is None:
        return 0.0
    if len(xs) != len(ys) or len(xs) < 2:
        return 0.0
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    numerator = sum((xs[i] - mx) * (ys[i] - my) for i in range(n))
    dx = sum((v - mx) ** 2 for v in xs) ** 0.5
    dy = sum((v - my) ** 2 for v in ys) ** 0.5
    if dx == 0.0 or dy == 0.0:
        return 0.0
    r = numerator / (dx * dy)
    # Guard against floating point noise outside [-1, 1].
    return max(-1.0, min(1.0, r))


class CorrelationAnalyzer:
    """Finds strongly correlated pairs among a collection of numeric series."""

    def __init__(self, threshold: float = 0.7, min_points: int = 3):
        self.threshold = threshold
        self.min_points = min_points

    def correlation(self, xs: Sequence[float], ys: Sequence[float]) -> float:
        """Pearson correlation for a single pair of series."""
        return pearson_correlation(xs, ys)

    def find_strong_pairs(
        self, series: Dict[str, Sequence[float]]
    ) -> List[Tuple[str, str, float]]:
        """
        Return all pairs (name_a, name_b, r) with |r| > threshold.

        Series shorter than ``min_points`` or with mismatched lengths are
        skipped. Names are iterated in sorted order so results are
        deterministic.
        """
        names = sorted(series.keys())
        pairs: List[Tuple[str, str, float]] = []
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                name_a, name_b = names[i], names[j]
                values_a, values_b = series[name_a], series[name_b]
                if len(values_a) < self.min_points or len(values_a) != len(values_b):
                    continue
                r = pearson_correlation(values_a, values_b)
                if abs(r) > self.threshold:
                    pairs.append((name_a, name_b, r))
        return pairs


class AIInsightsEngine:
    """
    Rule-based insight engine bridging M1 analytics outputs to insights.

    Inputs are plain data (metrics, anomalies, trend results, numeric series)
    so the engine can run against mocked or real analytics data without a
    database dependency.
    """

    # severity -> (confidence, impact)
    _SEVERITY_PROFILE = {
        'critical': (0.9, 0.9),
        'high': (0.9, 0.7),
        'medium': (0.85, 0.5),
        'low': (0.8, 0.3),
    }

    def __init__(
        self,
        series: Optional[Dict[str, Sequence[float]]] = None,
        metrics: Optional[Sequence[Metric]] = None,
        anomalies: Optional[Sequence[Anomaly]] = None,
        trend_results: Optional[Dict[str, Dict[str, Any]]] = None,
        correlation_threshold: float = 0.7,
    ):
        self.series: Dict[str, List[float]] = {
            str(k): list(v) for k, v in (series or {}).items()
        }
        self.metrics: List[Metric] = list(metrics or [])
        self.anomalies: List[Anomaly] = list(anomalies or [])
        self.trend_results: Dict[str, Dict[str, Any]] = dict(trend_results or {})
        self.correlation_threshold = correlation_threshold
        self.correlation_analyzer = CorrelationAnalyzer(threshold=correlation_threshold)
        self._counter = 0

    # ------------------------------------------------------------------
    # Input registration
    # ------------------------------------------------------------------
    def add_series(self, name: str, values: Sequence[float]) -> None:
        self.series[str(name)] = list(values)

    def add_metric(self, metric: Metric) -> None:
        self.metrics.append(metric)

    def add_anomaly(self, anomaly: Anomaly) -> None:
        self.anomalies.append(anomaly)

    def add_trend_result(self, metric_name: str, result: Dict[str, Any]) -> None:
        """Register the output shape of M1 ``TrendAnalyzer.analyze_trend``."""
        self.trend_results[str(metric_name)] = result

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------
    @staticmethod
    def score(insight: Insight) -> float:
        """Insight score = impact x confidence, clamped to [0, 1]."""
        return round(insight.confidence * insight.impact, 6)

    @staticmethod
    def derive_priority(score: float) -> Priority:
        """Map a 0-1 score to a Priority level."""
        if score >= 0.8:
            return Priority.CRITICAL
        if score >= 0.6:
            return Priority.HIGH
        if score >= 0.4:
            return Priority.MEDIUM
        return Priority.LOW

    def _build(
        self,
        insight_type: InsightType,
        title: str,
        description: str,
        confidence: float,
        impact: float,
        evidence: Sequence[str],
        recommendations: Sequence[str],
        related_metrics: Sequence[str],
    ) -> Insight:
        self._counter += 1
        slug = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")[:48] or "insight"
        return Insight(
            insight_id=f"ins_{insight_type.value}_{self._counter:04d}_{slug}",
            insight_type=insight_type,
            title=title,
            description=description,
            confidence=float(confidence),
            impact=float(impact),
            priority=self.derive_priority(float(confidence) * float(impact)),
            evidence=list(evidence),
            recommendations=list(recommendations),
            related_metrics=list(related_metrics),
        )

    # ------------------------------------------------------------------
    # Rules: anomaly -> insight
    # ------------------------------------------------------------------
    def insight_from_anomaly(self, anomaly: Anomaly) -> Insight:
        """Bridge an M1 ``Anomaly`` into an ``Insight``."""
        confidence, impact = self._SEVERITY_PROFILE.get(
            anomaly.severity, (0.8, 0.5)
        )
        return self._build(
            InsightType.ANOMALY,
            title=f"Anomaly Detected: {anomaly.metric_name}",
            description=anomaly.description
            or f"{anomaly.metric_name} deviates from its baseline.",
            confidence=confidence,
            impact=impact,
            evidence=[
                f"Observed: {anomaly.observed_value}",
                f"Expected: {anomaly.expected_value:.2f}",
                f"Deviation: {anomaly.deviation:.2f} sigma",
            ],
            recommendations=[
                "Investigate root cause",
                "Check for system issues",
                "Review recent changes",
            ],
            related_metrics=[anomaly.metric_name],
        )

    # ------------------------------------------------------------------
    # Rules: trend -> insight (with forecast note)
    # ------------------------------------------------------------------
    def insight_from_trend(
        self, metric_name: str, trend_result: Dict[str, Any]
    ) -> Optional[Insight]:
        """
        Bridge an M1 ``TrendAnalyzer.analyze_trend`` result into an Insight.

        The description carries a forecast note projecting the next period
        from the trend slope. Returns None for insufficient data.
        """
        trend = trend_result.get('trend')
        if trend in (None, 'insufficient_data'):
            return None

        slope = float(trend_result.get('slope', 0.0) or 0.0)
        data = trend_result.get('data') or []
        values = [
            float(dp.get('value', 0.0)) for dp in data if isinstance(dp, dict)
        ]

        forecast_note = ""
        if values:
            projected = values[-1] + slope
            forecast_note = (
                f" Forecast note: if the current slope ({slope:.3f}/period) "
                f"persists, next period is projected at ~{projected:.2f}."
            )

        if trend == 'down':
            title = f"Declining {metric_name}"
            impact = 0.8
            recommendations = [
                "Investigate causes of the decline",
                "Set an alert for further drops",
            ]
        elif trend == 'up':
            title = f"Increasing {metric_name}"
            impact = 0.7
            recommendations = [
                "Monitor growth",
                "Plan capacity for continued growth",
            ]
        else:
            title = f"Stable {metric_name}"
            impact = 0.3
            recommendations = ["Continue monitoring"]

        description = (
            f"{metric_name} shows {trend} trend over the observed period."
            f"{forecast_note}"
        )
        evidence = [f"Slope: {slope:.3f}"]
        if 'mean' in trend_result:
            evidence.append(f"Mean: {float(trend_result['mean']):.2f}")

        return self._build(
            InsightType.TREND,
            title=title,
            description=description,
            confidence=0.85,
            impact=impact,
            evidence=evidence,
            recommendations=recommendations,
            related_metrics=[metric_name],
        )

    # ------------------------------------------------------------------
    # Rules: correlation -> insight
    # ------------------------------------------------------------------
    def insight_from_correlation(
        self, name_a: str, name_b: str, r: float
    ) -> Insight:
        direction = 'positive' if r > 0 else 'negative'
        return self._build(
            InsightType.CORRELATION,
            title=f"Strong {direction.title()} Correlation: {name_a} <-> {name_b}",
            description=(
                f"{name_a} and {name_b} are strongly {direction}ly correlated "
                f"(Pearson r={r:.2f})."
            ),
            confidence=0.8,
            impact=0.6,
            evidence=[
                f"Pearson r: {r:.3f}",
                f"Series length: {len(self.series.get(name_a, []))}",
            ],
            recommendations=[
                "Investigate the shared driver behind both series",
                "Use the leading series as an early signal for the other",
            ],
            related_metrics=[name_a, name_b],
        )

    # ------------------------------------------------------------------
    # Rules: metric threshold -> recommendation insight
    # ------------------------------------------------------------------
    def insights_from_metric(self, metric: Metric) -> List[Insight]:
        """
        Recommend action when a metric falls below its thresholds.

        Mirrors the M1 rule (value < threshold_warning) and adds a stronger
        critical-tier rule (value < threshold_critical).
        """
        out: List[Insight] = []
        if (
            metric.threshold_critical is not None
            and metric.value < metric.threshold_critical
        ):
            out.append(
                self._build(
                    InsightType.RECOMMENDATION,
                    title=f"Action Required: {metric.name}",
                    description=(
                        f"{metric.name} ({metric.value:.2f}) is below the "
                        f"critical threshold ({metric.threshold_critical})."
                    ),
                    confidence=0.95,
                    impact=0.9,
                    evidence=[
                        f"Current: {metric.value:.2f}",
                        f"Critical threshold: {metric.threshold_critical}",
                    ],
                    recommendations=[
                        f"Investigate low {metric.name}",
                        "Take corrective action immediately",
                    ],
                    related_metrics=[metric.metric_id],
                )
            )
        elif (
            metric.threshold_warning is not None
            and metric.value < metric.threshold_warning
        ):
            out.append(
                self._build(
                    InsightType.RECOMMENDATION,
                    title=f"Action Required: {metric.name}",
                    description=(
                        f"{metric.name} ({metric.value:.2f}) is below the "
                        f"warning threshold ({metric.threshold_warning})."
                    ),
                    confidence=0.95,
                    impact=0.8,
                    evidence=[
                        f"Current: {metric.value:.2f}",
                        f"Warning threshold: {metric.threshold_warning}",
                    ],
                    recommendations=[
                        f"Investigate low {metric.name}",
                        "Take corrective action",
                    ],
                    related_metrics=[metric.metric_id],
                )
            )
        return out

    # ------------------------------------------------------------------
    # Dedupe
    # ------------------------------------------------------------------
    def dedupe(
        self, insights: List[Insight], threshold: float = 0.75
    ) -> List[Insight]:
        """
        Remove similar insights (same type, token Jaccard >= threshold).

        Within each type, higher-scored (impact x confidence) insights are
        kept. Different insight types are never merged even when texts match.
        """
        kept: List[Insight] = []
        kept_tokens: List[set] = []
        ordered = sorted(
            insights,
            key=lambda i: (
                i.insight_type.value,
                -(i.confidence * i.impact),
                i.insight_id,
            ),
        )
        for ins in ordered:
            toks = _tokens(f"{ins.title} {ins.description}")
            duplicate = False
            for idx, prev in enumerate(kept):
                if prev.insight_type != ins.insight_type:
                    continue
                union = kept_tokens[idx] | toks
                inter = kept_tokens[idx] & toks
                jaccard = (len(inter) / len(union)) if union else 1.0
                if jaccard >= threshold:
                    duplicate = True
                    break
            if not duplicate:
                kept.append(ins)
                kept_tokens.append(toks)
        return kept

    # ------------------------------------------------------------------
    # Full generation
    # ------------------------------------------------------------------
    def generate_all(self) -> List[Insight]:
        """Run all rules, dedupe, and sort by score (desc) then title."""
        insights: List[Insight] = []

        for anomaly in self.anomalies:
            insights.append(self.insight_from_anomaly(anomaly))

        for name in sorted(self.trend_results):
            insight = self.insight_from_trend(name, self.trend_results[name])
            if insight is not None:
                insights.append(insight)

        for name_a, name_b, r in self.correlation_analyzer.find_strong_pairs(
            self.series
        ):
            insights.append(self.insight_from_correlation(name_a, name_b, r))

        for metric in self.metrics:
            insights.extend(self.insights_from_metric(metric))

        insights = self.dedupe(insights)
        insights.sort(key=lambda i: (-(i.confidence * i.impact), i.title))
        return insights
