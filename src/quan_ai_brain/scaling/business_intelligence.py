"""
Business Intelligence Module (V30.5) — in-process analytics & reporting.

Provides:
- Time-series aggregation (hourly / daily rollup)
- KPI calculator (target vs actual, trend direction & slope)
- Dashboard model: widgets (metric / chart / table) with data serializer
- Scheduled report config + next-run calculator

SIMULATION SCOPE (per V30 plan constraints):
- Pure stdlib in-process computation; no warehouse, no Spark/Presto,
  no external BI service.

Version: V30.5
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

logger = logging.getLogger(__name__)


class RollupGranularity(Enum):
    HOURLY = "hourly"
    DAILY = "daily"


class WidgetType(Enum):
    METRIC = "metric"
    CHART = "chart"
    TABLE = "table"


class TrendDirection(Enum):
    UP = "up"
    DOWN = "down"
    STABLE = "stable"
    INSUFFICIENT = "insufficient"


@dataclass
class TimePoint:
    """One observation in a time series."""
    timestamp: datetime
    value: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "value": self.value,
        }


@dataclass
class KPI:
    """Key performance indicator result."""
    kpi_id: str
    name: str
    actual: float
    target: float
    direction: Optional[TrendDirection] = None
    slope: float = 0.0
    unit: str = ""
    higher_is_better: bool = True

    @property
    def attainment(self) -> float:
        """Target attainment ratio."""
        if self.target == 0:
            return 1.0 if self.actual == 0 else float("inf")
        if self.higher_is_better:
            return self.actual / self.target
        return self.target / self.actual if self.actual != 0 else float("inf")

    @property
    def met(self) -> bool:
        if self.higher_is_better:
            return self.actual >= self.target
        return self.actual <= self.target

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kpi_id": self.kpi_id,
            "name": self.name,
            "actual": self.actual,
            "target": self.target,
            "attainment": self.attainment,
            "met": self.met,
            "direction": self.direction.value if self.direction else None,
            "slope": self.slope,
            "unit": self.unit,
        }


@dataclass
class MetricWidget:
    widget_id: str
    title: str
    value: float
    unit: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"widget_id": self.widget_id, "type": "metric", "title": self.title,
                "value": self.value, "unit": self.unit}


@dataclass
class ChartWidget:
    widget_id: str
    title: str
    points: List[TimePoint]
    chart_type: str = "line"

    def to_dict(self) -> Dict[str, Any]:
        return {"widget_id": self.widget_id, "type": "chart", "title": self.title,
                "chart_type": self.chart_type,
                "points": [p.to_dict() for p in self.points]}


@dataclass
class TableWidget:
    widget_id: str
    title: str
    columns: List[str]
    rows: List[List[Any]]

    def to_dict(self) -> Dict[str, Any]:
        return {"widget_id": self.widget_id, "type": "table", "title": self.title,
                "columns": list(self.columns),
                "rows": [list(r) for r in self.rows]}


DashboardWidget = Union[MetricWidget, ChartWidget, TableWidget]


@dataclass
class Dashboard:
    """Dashboard model holding typed widgets."""
    dashboard_id: str
    title: str
    widgets: List[DashboardWidget] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def add_widget(self, widget: DashboardWidget) -> None:
        self.widgets.append(widget)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dashboard_id": self.dashboard_id,
            "title": self.title,
            "created_at": self.created_at.isoformat(),
            "widgets": [w.to_dict() for w in self.widgets],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


@dataclass
class ScheduleConfig:
    """Scheduled report configuration."""
    report_id: str
    name: str
    interval: str  # 'hourly' | 'daily' | 'weekly'
    anchor: datetime            # first run anchor
    recipients: List[str] = field(default_factory=list)
    enabled: bool = True

    def validate(self) -> List[str]:
        errors = []
        if self.interval not in ("hourly", "daily", "weekly"):
            errors.append(f"invalid interval: {self.interval}")
        if not self.recipients:
            errors.append("at least one recipient is required")
        return errors

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "name": self.name,
            "interval": self.interval,
            "anchor": self.anchor.isoformat(),
            "recipients": list(self.recipients),
            "enabled": self.enabled,
        }


def _bucket_key(ts: datetime, granularity: RollupGranularity) -> Tuple[int, ...]:
    if granularity == RollupGranularity.HOURLY:
        return (ts.year, ts.month, ts.day, ts.hour)
    return (ts.year, ts.month, ts.day)


def _bucket_start(ts: datetime, granularity: RollupGranularity) -> datetime:
    if granularity == RollupGranularity.HOURLY:
        return ts.replace(minute=0, second=0, microsecond=0)
    return ts.replace(hour=0, minute=0, second=0, microsecond=0)


class BusinessIntelligence:
    """In-process BI: aggregation, KPI, dashboard, schedule math."""

    def __init__(self) -> None:
        self._dashboards: Dict[str, Dashboard] = {}
        self._schedules: Dict[str, ScheduleConfig] = {}

    # ---------------- time-series aggregation ----------------

    def aggregate_time_series(
        self,
        points: Sequence[TimePoint],
        granularity: RollupGranularity,
    ) -> List[TimePoint]:
        """Roll up into hourly/daily buckets; bucket value = SUM (counters)."""
        sums: Dict[Tuple[int, ...], float] = {}
        starts: Dict[Tuple[int, ...], datetime] = {}
        for p in points:
            key = _bucket_key(p.timestamp, granularity)
            sums[key] = sums.get(key, 0.0) + p.value
            starts[key] = _bucket_start(p.timestamp, granularity)
        return [TimePoint(timestamp=starts[k], value=sums[k]) for k in sorted(sums.keys())]

    def average_time_series(
        self,
        points: Sequence[TimePoint],
        granularity: RollupGranularity,
    ) -> List[TimePoint]:
        """Same bucketing but bucket value = MEAN (gauges like latency)."""
        sums: Dict[Tuple[int, ...], float] = {}
        counts: Dict[Tuple[int, ...], int] = {}
        starts: Dict[Tuple[int, ...], datetime] = {}
        for p in points:
            key = _bucket_key(p.timestamp, granularity)
            sums[key] = sums.get(key, 0.0) + p.value
            counts[key] = counts.get(key, 0) + 1
            starts[key] = _bucket_start(p.timestamp, granularity)
        return [TimePoint(timestamp=starts[k], value=sums[k] / counts[k])
                for k in sorted(sums.keys())]

    # ---------------- KPI calculator ----------------

    def calculate_kpi(
        self,
        kpi_id: str,
        name: str,
        actual: float,
        target: float,
        history: Optional[Sequence[float]] = None,
        unit: str = "",
        higher_is_better: bool = True,
    ) -> KPI:
        history = list(history or [])
        if len(history) >= 2:
            slope = self._slope(history)
            if slope > 1e-9:
                direction = TrendDirection.UP
            elif slope < -1e-9:
                direction = TrendDirection.DOWN
            else:
                direction = TrendDirection.STABLE
        else:
            slope = 0.0
            direction = TrendDirection.INSUFFICIENT
        return KPI(
            kpi_id=kpi_id,
            name=name,
            actual=actual,
            target=target,
            direction=direction,
            slope=slope,
            unit=unit,
            higher_is_better=higher_is_better,
        )

    @staticmethod
    def _slope(values: Sequence[float]) -> float:
        n = len(values)
        if n < 2:
            return 0.0
        x_mean = (n - 1) / 2
        y_mean = sum(values) / n
        num = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
        den = sum((i - x_mean) ** 2 for i in range(n))
        if den == 0:
            return 0.0
        return num / den

    # ---------------- dashboard ----------------

    def create_dashboard(self, dashboard_id: str, title: str) -> Dashboard:
        if dashboard_id in self._dashboards:
            raise ValueError(f"duplicate dashboard_id: {dashboard_id}")
        d = Dashboard(dashboard_id=dashboard_id, title=title)
        self._dashboards[dashboard_id] = d
        return d

    def get_dashboard(self, dashboard_id: str) -> Optional[Dashboard]:
        return self._dashboards.get(dashboard_id)

    def dashboards(self) -> List[Dashboard]:
        return list(self._dashboards.values())

    # ---------------- scheduled reports ----------------

    def add_schedule(self, config: ScheduleConfig) -> ScheduleConfig:
        errors = config.validate()
        if errors:
            raise ValueError("; ".join(errors))
        self._schedules[config.report_id] = config
        return config

    def get_schedule(self, report_id: str) -> Optional[ScheduleConfig]:
        return self._schedules.get(report_id)

    @staticmethod
    def next_run(schedule: ScheduleConfig, after: datetime) -> datetime:
        """
        Next run strictly after `after`, based on interval steps from anchor.
        Supports hourly/daily/weekly; result carries `after`'s tzinfo.
        """
        if schedule.interval == "hourly":
            step = timedelta(hours=1)
        elif schedule.interval == "daily":
            step = timedelta(days=1)
        elif schedule.interval == "weekly":
            step = timedelta(weeks=1)
        else:
            raise ValueError(f"unsupported interval: {schedule.interval}")
        cursor = schedule.anchor
        if cursor.tzinfo is None and after.tzinfo is not None:
            cursor = cursor.replace(tzinfo=after.tzinfo)
        guard = 0
        while cursor <= after and guard < 1_000_000:
            cursor += step
            guard += 1
        if cursor <= after:
            raise RuntimeError("next_run: step loop exceeded guard")
        return cursor

    # ---------------- serialization ----------------

    def serialize_report_data(self, data: Dict[str, Any]) -> str:
        return json.dumps(data, ensure_ascii=False, default=str)
