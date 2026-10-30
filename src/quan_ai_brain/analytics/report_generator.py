"""
Automated Report Generator Module (V25.3)

Renders analytics data into templated reports:
- Markdown template with fixed sections: Executive Summary / Metrics Detail /
  Anomalies / Recommendations
- Renders from the existing M1 ``MetricsCalculator`` (or a plain metric list)
- Exports: Markdown string, HTML string, CSV string

Standard library only. Reuses dataclasses from
``quan_ai_brain.analytics.analytics_engine`` (M1 - reused, not modified).

Version: V25.3
Author: QUAN AI BRAIN Team
"""

import csv
import html
import io
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Union

from quan_ai_brain.analytics.analytics_engine import (
    Anomaly,
    Insight,
    Metric,
    MetricsCalculator,
)

logger = logging.getLogger(__name__)

SECTION_TITLES = {
    'executive_summary': 'Executive Summary',
    'metrics_detail': 'Metrics Detail',
    'anomalies': 'Anomalies',
    'recommendations': 'Recommendations',
}


@dataclass
class ReportSection:
    """One section of a generated report."""
    title: str
    content: str
    metrics: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'title': self.title,
            'content': self.content,
            'metrics': dict(self.metrics),
        }


@dataclass
class Report:
    """A fully generated report plus its source data."""
    report_id: str
    title: str
    generated_at: datetime
    period_start: Optional[datetime]
    period_end: Optional[datetime]
    sections: List[ReportSection]
    metrics: List[Metric]
    anomalies: List[Anomaly]
    insights: List[Insight]
    recommendations: List[str]

    def health_status(self) -> str:
        """Derived health: 'critical' | 'warning' | 'healthy'."""
        if any(a.severity == 'critical' for a in self.anomalies):
            return 'critical'
        for m in self.metrics:
            if m.threshold_critical is not None and m.value < m.threshold_critical:
                return 'critical'
        if self.anomalies:
            return 'warning'
        for m in self.metrics:
            if m.threshold_warning is not None and m.value < m.threshold_warning:
                return 'warning'
        return 'healthy'

    def get_section(self, title: str) -> Optional[ReportSection]:
        return next((s for s in self.sections if s.title == title), None)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'report_id': self.report_id,
            'title': self.title,
            'generated_at': self.generated_at.isoformat(),
            'period_start': self.period_start.isoformat() if self.period_start else None,
            'period_end': self.period_end.isoformat() if self.period_end else None,
            'health_status': self.health_status(),
            'sections': [s.to_dict() for s in self.sections],
            'metrics': [m.to_dict() for m in self.metrics],
            'anomalies': [a.to_dict() for a in self.anomalies],
            'insights': [i.to_dict() for i in self.insights],
            'recommendations': list(self.recommendations),
        }


class ReportGenerator:
    """
    Generates templated reports from metrics, anomalies and insights.

    ``metrics_provider`` may be:
    - a M1 ``MetricsCalculator`` instance (``calculate_all_metrics`` is called
      on every ``generate_report``), or
    - a plain sequence of ``Metric`` objects, or
    - None (empty report).
    """

    def __init__(
        self,
        metrics_provider: Optional[Union[MetricsCalculator, Sequence[Metric]]] = None,
    ):
        self._provider = metrics_provider

    # ------------------------------------------------------------------
    # Metric collection
    # ------------------------------------------------------------------
    def _collect_metrics(self) -> List[Metric]:
        provider = self._provider
        if provider is None:
            return []
        if hasattr(provider, 'calculate_all_metrics'):
            return list(provider.calculate_all_metrics())
        return list(provider)

    # ------------------------------------------------------------------
    # Report generation
    # ------------------------------------------------------------------
    def generate_report(
        self,
        title: str = "QUAN AI BRAIN Analytics Report",
        anomalies: Optional[Sequence[Anomaly]] = None,
        insights: Optional[Sequence[Insight]] = None,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None,
        report_id: Optional[str] = None,
        generated_at: Optional[datetime] = None,
        extra_recommendations: Optional[Sequence[str]] = None,
    ) -> Report:
        metrics = self._collect_metrics()
        anomalies = list(anomalies or [])
        insights = list(insights or [])

        recommendations = self._extract_recommendations(insights, metrics)
        for extra in extra_recommendations or []:
            text = str(extra).strip()
            if text and text.lower() not in {r.lower() for r in recommendations}:
                recommendations.append(text)

        sections = [
            ReportSection(
                title=SECTION_TITLES['executive_summary'],
                content=self._exec_summary_content(metrics, anomalies, insights),
                metrics=self._key_figures(metrics),
            ),
            ReportSection(
                title=SECTION_TITLES['metrics_detail'],
                content=self._metrics_detail_content(metrics),
                metrics={m.metric_id: float(m.value) for m in metrics},
            ),
            ReportSection(
                title=SECTION_TITLES['anomalies'],
                content=self._anomalies_content(anomalies),
            ),
            ReportSection(
                title=SECTION_TITLES['recommendations'],
                content=(
                    "\n".join(f"- {r}" for r in recommendations)
                    if recommendations
                    else "- No recommendations available."
                ),
            ),
        ]

        return Report(
            report_id=report_id or f"report_{uuid.uuid4().hex[:12]}",
            title=title,
            generated_at=generated_at or datetime.utcnow(),
            period_start=period_start,
            period_end=period_end,
            sections=sections,
            metrics=metrics,
            anomalies=anomalies,
            insights=insights,
            recommendations=recommendations,
        )

    # ------------------------------------------------------------------
    # Section builders
    # ------------------------------------------------------------------
    @staticmethod
    def _key_figures(metrics: List[Metric]) -> Dict[str, float]:
        figures: Dict[str, float] = {}
        by_id = {m.metric_id: m for m in metrics}
        for key in ('total_ku', 'avg_confidence', 'verified_rate'):
            if key in by_id:
                figures[key] = float(by_id[key].value)
        return figures

    def _exec_summary_content(
        self,
        metrics: List[Metric],
        anomalies: List[Anomaly],
        insights: List[Insight],
    ) -> str:
        by_id = {m.metric_id: m for m in metrics}
        lines = [f"- Health status: {self._health_status(metrics, anomalies)}"]
        lines.append(f"- Total metrics collected: {len(metrics)}")
        if 'total_ku' in by_id:
            lines.append(
                f"- Knowledge units tracked: {by_id['total_ku'].value:.0f}"
            )
        else:
            lines.append("- Knowledge units tracked: n/a")
        if 'avg_confidence' in by_id:
            lines.append(
                f"- Average confidence: {by_id['avg_confidence'].value:.2f}"
            )
        else:
            lines.append("- Average confidence: n/a")
        lines.append(f"- Anomalies detected: {len(anomalies)}")
        lines.append(f"- Insights generated: {len(insights)}")
        return "\n".join(lines)

    @staticmethod
    def _health_status(
        metrics: List[Metric], anomalies: List[Anomaly]
    ) -> str:
        if any(a.severity == 'critical' for a in anomalies):
            return 'critical'
        for m in metrics:
            if m.threshold_critical is not None and m.value < m.threshold_critical:
                return 'critical'
        if anomalies:
            return 'warning'
        for m in metrics:
            if m.threshold_warning is not None and m.value < m.threshold_warning:
                return 'warning'
        return 'healthy'

    @staticmethod
    def _metrics_detail_content(metrics: List[Metric]) -> str:
        if not metrics:
            return "_No metrics available._"
        lines = [
            "| Metric | Value | Unit | Type | Change | Trend |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
        for m in metrics:
            change = f"{m.change:+.2f}%" if m.change is not None else "-"
            trend = m.trend or "-"
            lines.append(
                f"| {m.name} | {m.value:.2f} | {m.unit} | "
                f"{m.metric_type.value} | {change} | {trend} |"
            )
        return "\n".join(lines)

    @staticmethod
    def _anomalies_content(anomalies: List[Anomaly]) -> str:
        if not anomalies:
            return "- No anomalies detected."
        lines = []
        for a in anomalies:
            lines.append(
                f"- **[{a.severity}] {a.metric_name}** - {a.description} "
                f"(observed={a.observed_value:.2f}, "
                f"expected={a.expected_value:.2f}, "
                f"deviation={a.deviation:.2f} sigma)"
            )
        return "\n".join(lines)

    @staticmethod
    def _extract_recommendations(
        insights: List[Insight], metrics: List[Metric]
    ) -> List[str]:
        """
        Recommendations from insights (highest score first, deduped) plus a
        fallback line for metrics below their warning threshold.
        """
        out: List[str] = []
        seen = set()

        def _add(text: str) -> None:
            key = text.strip().lower()
            if key and key not in seen:
                seen.add(key)
                out.append(text.strip())

        ordered = sorted(
            insights, key=lambda i: (-(i.confidence * i.impact), i.title)
        )
        for ins in ordered:
            for rec in ins.recommendations:
                _add(rec)
        for m in metrics:
            if m.threshold_warning is not None and m.value < m.threshold_warning:
                _add(
                    f"Review metric '{m.name}' - below warning threshold "
                    f"({m.value:.2f} < {m.threshold_warning})"
                )
        return out

    # ------------------------------------------------------------------
    # Export: Markdown
    # ------------------------------------------------------------------
    def to_markdown(self, report: Report) -> str:
        lines: List[str] = [f"# {report.title}", ""]
        lines.append(f"**Report ID:** {report.report_id}  ")
        lines.append(f"**Generated at:** {report.generated_at.isoformat()}  ")
        if report.period_start or report.period_end:
            start = report.period_start.isoformat() if report.period_start else "n/a"
            end = report.period_end.isoformat() if report.period_end else "n/a"
            lines.append(f"**Period:** {start} -> {end}  ")
        lines.append(f"**Health status:** {report.health_status()}  ")
        lines.append("")
        for section in report.sections:
            lines.append(f"## {section.title}")
            lines.append("")
            lines.append(section.content)
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"

    # ------------------------------------------------------------------
    # Export: HTML
    # ------------------------------------------------------------------
    @staticmethod
    def _content_to_html(content: str) -> str:
        esc = html.escape
        parts: List[str] = []
        in_list = False
        for raw in content.splitlines():
            line = raw.strip()
            if not line:
                continue
            if line.startswith('- '):
                if not in_list:
                    parts.append('<ul>')
                    in_list = True
                parts.append(f'<li>{esc(line[2:])}</li>')
            else:
                if in_list:
                    parts.append('</ul>')
                    in_list = False
                parts.append(f'<p>{esc(line)}</p>')
        if in_list:
            parts.append('</ul>')
        return "\n".join(parts)

    def to_html(self, report: Report) -> str:
        esc = html.escape
        parts: List[str] = [
            '<!DOCTYPE html>',
            '<html>',
            '<head>',
            f'<title>{esc(report.title)}</title>',
            '<meta charset="utf-8">',
            '</head>',
            '<body>',
            f'<h1>{esc(report.title)}</h1>',
            (
                f'<p>Report ID: {esc(report.report_id)} | '
                f'Generated at: {esc(report.generated_at.isoformat())} | '
                f'Health status: {esc(report.health_status())}</p>'
            ),
        ]
        for section in report.sections:
            parts.append(f'<h2>{esc(section.title)}</h2>')
            if (
                section.title == SECTION_TITLES['metrics_detail']
                and report.metrics
            ):
                parts.append('<table border="1">')
                parts.append(
                    '<tr><th>Metric</th><th>Value</th><th>Unit</th>'
                    '<th>Type</th></tr>'
                )
                for m in report.metrics:
                    parts.append(
                        f'<tr><td>{esc(m.name)}</td><td>{m.value:.2f}</td>'
                        f'<td>{esc(m.unit)}</td><td>{esc(m.metric_type.value)}</td></tr>'
                    )
                parts.append('</table>')
            else:
                parts.append(self._content_to_html(section.content))
        parts.append('</body>')
        parts.append('</html>')
        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Export: CSV
    # ------------------------------------------------------------------
    def to_csv(self, report: Report) -> str:
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(
            ['metric_id', 'name', 'value', 'unit', 'metric_type',
             'change', 'trend', 'timestamp']
        )
        for m in report.metrics:
            writer.writerow([
                m.metric_id,
                m.name,
                m.value,
                m.unit,
                m.metric_type.value,
                '' if m.change is None else m.change,
                m.trend or '',
                m.timestamp.isoformat(),
            ])
        return buf.getvalue()

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------
    def render(self, report: Report, fmt: str = 'markdown') -> str:
        fmt = (fmt or '').lower()
        if fmt in ('markdown', 'md'):
            return self.to_markdown(report)
        if fmt == 'html':
            return self.to_html(report)
        if fmt == 'csv':
            return self.to_csv(report)
        raise ValueError(f"Unsupported report format: {fmt}")
