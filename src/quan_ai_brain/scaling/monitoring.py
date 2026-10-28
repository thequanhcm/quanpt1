"""
Observability Module (V30.4) — in-process tracing, SLO, alerting, logs.

Provides:
- Observability: trace spans with parent/child relationships
- SLO calculator: success ratio over a sliding window
- Error budget: remaining budget and burn rate
- Alert rules: threshold + "for" duration before firing
- Log aggregation: ring buffer + level/text filter

SIMULATION SCOPE (per V30 plan constraints):
- No OpenTelemetry exporter, no Jaeger/Zipkin, no external APM.
- All state in-process; suitable for unit-level simulation only.

Version: V30.4
"""

import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Deque, Dict, List, Optional

logger = logging.getLogger(__name__)


class SpanStatus(Enum):
    """Span completion status."""
    OK = "ok"
    ERROR = "error"
    UNSET = "unset"


@dataclass
class Span:
    """One trace span."""
    span_id: str
    trace_id: str
    name: str
    parent_id: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    status: SpanStatus = SpanStatus.UNSET
    attributes: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration_ms(self) -> Optional[float]:
        if self.start_time is not None and self.end_time is not None:
            return (self.end_time - self.start_time) * 1000.0
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "span_id": self.span_id,
            "trace_id": self.trace_id,
            "name": self.name,
            "parent_id": self.parent_id,
            "duration_ms": self.duration_ms,
            "status": self.status.value,
            "attributes": dict(self.attributes),
        }


class AlertSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class AlertRule:
    """Threshold + for-duration alert rule."""
    rule_id: str
    metric_name: str
    threshold: float
    comparison: str  # 'gt' | 'lt' | 'gte' | 'lte' | 'eq'
    for_seconds: float
    severity: AlertSeverity = AlertSeverity.WARNING
    description: str = ""

    def evaluate(self, value: float) -> bool:
        ops = {
            "gt": lambda v, t: v > t,
            "gte": lambda v, t: v >= t,
            "lt": lambda v, t: v < t,
            "lte": lambda v, t: v <= t,
            "eq": lambda v, t: v == t,
        }
        if self.comparison not in ops:
            raise ValueError(f"unsupported comparison: {self.comparison}")
        return ops[self.comparison](value, self.threshold)


@dataclass
class Alert:
    """A fired alert."""
    rule_id: str
    metric_name: str
    value: float
    threshold: float
    fired_at: datetime
    severity: AlertSeverity
    message: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "metric_name": self.metric_name,
            "value": self.value,
            "threshold": self.threshold,
            "fired_at": self.fired_at.isoformat(),
            "severity": self.severity.value,
            "message": self.message,
        }


@dataclass
class LogRecord:
    """One aggregated log entry."""
    timestamp: float
    level: str
    message: str
    source: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "level": self.level,
            "message": self.message,
            "source": self.source,
        }


class RingBuffer:
    """Fixed-capacity ring buffer."""

    def __init__(self, capacity: int) -> None:
        if capacity < 1:
            raise ValueError("capacity must be >= 1")
        self.capacity = capacity
        self._items: Deque[Any] = deque(maxlen=capacity)

    def append(self, item: Any) -> None:
        self._items.append(item)

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self):
        return iter(self._items)

    def snapshot(self) -> List[Any]:
        return list(self._items)


class Observability:
    """In-process observability facade: tracing, SLO, alerts, log aggregation."""

    def __init__(
        self,
        slo_target: float = 0.999,
        window_seconds: float = 300.0,
        log_capacity: int = 1000,
    ) -> None:
        self.slo_target = slo_target
        self.window_seconds = window_seconds
        self._spans: Dict[str, Span] = {}
        self._trace_spans: Dict[str, List[str]] = {}
        self._span_counter = 0
        self._lock = threading.RLock()

        # SLO event stream: (timestamp, success: bool)
        self._slo_events: Deque[tuple] = deque()
        self._alert_rules: Dict[str, AlertRule] = {}
        self._alert_state: Dict[str, Dict[str, Any]] = {}
        self._fired_alerts: List[Alert] = []
        self._logs = RingBuffer(log_capacity)

    # ---------------- tracing ----------------

    def start_span(
        self,
        name: str,
        trace_id: Optional[str] = None,
        parent_span_id: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> Span:
        with self._lock:
            self._span_counter += 1
            sid = f"span-{self._span_counter:06d}"
            tid = trace_id or f"trace-{self._span_counter:06d}"
            if parent_span_id is not None and parent_span_id in self._spans:
                tid = self._spans[parent_span_id].trace_id
            span = Span(
                span_id=sid,
                trace_id=tid,
                name=name,
                parent_id=parent_span_id,
                start_time=time.time(),
                attributes=dict(attributes or {}),
            )
            self._spans[sid] = span
            self._trace_spans.setdefault(tid, []).append(sid)
            return span

    def end_span(self, span: Span, status: SpanStatus = SpanStatus.OK) -> Span:
        with self._lock:
            if span.span_id not in self._spans:
                raise KeyError(f"unknown span: {span.span_id}")
            span.end_time = time.time()
            span.status = status
            return span

    def get_span(self, span_id: str) -> Optional[Span]:
        return self._spans.get(span_id)

    def trace_tree(self, trace_id: str) -> List[Span]:
        """All spans of a trace, parents before children."""
        ids = self._trace_spans.get(trace_id, [])
        spans = [self._spans[i] for i in ids]
        spans.sort(key=lambda s: (s.parent_id is not None, s.start_time or 0))
        return spans

    def record_outcome(self, success: bool, at: Optional[float] = None) -> None:
        """Record one request outcome for SLO accounting."""
        with self._lock:
            self._slo_events.append((at if at is not None else time.time(), bool(success)))

    # ---------------- SLO ----------------

    def slo_success_ratio(self, window: Optional[float] = None,
                          now: Optional[float] = None) -> Optional[float]:
        """
        Success ratio of outcomes within the sliding window.
        Returns None when there is no data in the window.
        """
        window = window if window is not None else self.window_seconds
        now = now if now is not None else time.time()
        with self._lock:
            relevant = [(t, ok) for (t, ok) in self._slo_events if now - t <= window]
        if not relevant:
            return None
        return sum(1 for _, ok in relevant if ok) / len(relevant)

    def slo_status(self, window: Optional[float] = None,
                   now: Optional[float] = None) -> Dict[str, Any]:
        ratio = self.slo_success_ratio(window, now)
        return {
            "target": self.slo_target,
            "observed": ratio,
            "compliant": ratio is not None and ratio >= self.slo_target,
            "window_seconds": window if window is not None else self.window_seconds,
        }

    def error_budget_remaining(self, window: Optional[float] = None,
                               now: Optional[float] = None) -> Optional[float]:
        """
        Fraction of error budget remaining (0..1).
        Budget = 1 - target; consumed = (1 - observed_ratio) / (1 - target).
        Returns None when no data.
        """
        ratio = self.slo_success_ratio(window, now)
        if ratio is None:
            return None
        budget = 1.0 - self.slo_target
        if budget <= 0:
            return 1.0 if ratio >= 1.0 else 0.0
        consumed = max(0.0, (1.0 - ratio) / budget)
        return max(0.0, 1.0 - consumed)

    def error_budget_burn_rate(self, window: Optional[float] = None,
                               now: Optional[float] = None) -> Optional[float]:
        """
        Burn rate = actual error ratio / allowed error ratio.
        1.0 means consuming budget exactly at plan; >1 faster than plan.
        Returns None when no data.
        """
        ratio = self.slo_success_ratio(window, now)
        if ratio is None:
            return None
        budget = 1.0 - self.slo_target
        if budget <= 0:
            return 0.0 if ratio >= 1.0 else float("inf")
        return max(0.0, (1.0 - ratio) / budget)

    # ---------------- alerting ----------------

    def add_alert_rule(self, rule: AlertRule) -> None:
        if rule.rule_id in self._alert_rules:
            raise ValueError(f"duplicate rule_id: {rule.rule_id}")
        self._alert_rules[rule.rule_id] = rule
        self._alert_state[rule.rule_id] = {"breach_since": None, "fired": False}

    def remove_alert_rule(self, rule_id: str) -> bool:
        self._alert_rules.pop(rule_id, None)
        return self._alert_state.pop(rule_id, None) is not None

    def _check_alerts(self, metric_name: str, value: float, now: float) -> None:
        for rule in self._alert_rules.values():
            if rule.metric_name != metric_name:
                continue
            state = self._alert_state[rule.rule_id]
            breach = rule.evaluate(value)
            if breach:
                if state["breach_since"] is None:
                    state["breach_since"] = now
                if (not state["fired"]) and (now - state["breach_since"]) >= rule.for_seconds:
                    alert = Alert(
                        rule_id=rule.rule_id,
                        metric_name=metric_name,
                        value=value,
                        threshold=rule.threshold,
                        fired_at=datetime.now(timezone.utc),
                        severity=rule.severity,
                        message=(f"{metric_name}={value} breached {rule.comparison} "
                                 f"{rule.threshold} for >= {rule.for_seconds}s"),
                    )
                    self._fired_alerts.append(alert)
                    state["fired"] = True
            else:
                state["breach_since"] = None
                state["fired"] = False

    def record_metric(self, name: str, value: float,
                      at: Optional[float] = None) -> List[Alert]:
        """Record a metric sample; evaluates alert rules with 'for' duration."""
        now = at if at is not None else time.time()
        with self._lock:
            self._check_alerts(name, value, now)
            return [a for a in self._fired_alerts if a.metric_name == name]

    def fired_alerts(self) -> List[Alert]:
        return list(self._fired_alerts)

    def reset_alerts(self) -> None:
        self._fired_alerts.clear()
        for st in self._alert_state.values():
            st["breach_since"] = None
            st["fired"] = False

    # ---------------- log aggregation ----------------

    def log(self, level: str, message: str, source: str = "",
            timestamp: Optional[float] = None) -> LogRecord:
        rec = LogRecord(
            timestamp=timestamp if timestamp is not None else time.time(),
            level=level.upper(),
            message=message,
            source=source,
        )
        self._logs.append(rec)
        return rec

    def query_logs(
        self,
        min_level: Optional[str] = None,
        contains: Optional[str] = None,
        since: Optional[float] = None,
        until: Optional[float] = None,
        source: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[LogRecord]:
        """Filter the ring buffer. min_level uses the INFO<WARNING<ERROR<CRITICAL order."""
        order = {"DEBUG": 0, "INFO": 1, "WARNING": 2, "ERROR": 3, "CRITICAL": 4}
        min_rank = order.get((min_level or "").upper())
        out: List[LogRecord] = []
        for rec in self._logs:
            if min_rank is not None and order.get(rec.level, 0) < min_rank:
                continue
            if contains is not None and contains.lower() not in rec.message.lower():
                continue
            if since is not None and rec.timestamp < since:
                continue
            if until is not None and rec.timestamp > until:
                continue
            if source is not None and rec.source != source:
                continue
            out.append(rec)
        if limit is not None:
            out = out[-limit:]
        return out

    def log_count(self) -> int:
        return len(self._logs)

    # ---------------- integration helpers ----------------

    def traced(self, name: str, trace_id: Optional[str] = None,
               parent_span_id: Optional[str] = None):
        """Context manager for a span that records outcome automatically."""
        obs = self

        class _Ctx:
            def __enter__(self_inner):
                self_inner.span = obs.start_span(name, trace_id, parent_span_id)
                return self_inner.span

            def __exit__(self_inner, exc_type, exc, tb):
                status = SpanStatus.OK if exc is None else SpanStatus.ERROR
                obs.end_span(self_inner.span, status)
                obs.record_outcome(success=(exc is None))
                return False

        return _Ctx()
