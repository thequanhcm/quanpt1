"""Performance monitor — V39 Sprint 5 capability RESTORED (30/10/2026).

LỊCH SỬ: commit e6135a5 (memory expansion) ghi đè feedback_processor.py /
self_optimizer.py của Sprint 5 gốc (0bd5daa) và làm mất các năng lực giám sát
hiệu năng / phân tích lỗi / gợi ý cải tiến. Sprint 5 test (test_v39_learning_engine)
lúc đó ERROR vì import class không còn tồn tại.

File này KHÔI PHỤC đúng API Sprint 5 gốc (PerformanceMetric, ErrorAnalysis,
ImprovementSuggestion, Priority, collect_user_feedback, track_performance,
analyze_system_errors, suggest_improvements) ở dạng standalone in-memory —
KHÔNG đụng FeedbackProcessor/SelfOptimizer DB-backed hiện hành đang được
test_v39_sprint5_learning.py (25/25 PASS) sử dụng. Bên trong, các hàm tiện
ích ủy quyền sang FeedbackProcessor/SelfOptimizer hiện hành để một hệ thống
một nguồn sự thật (brain.db).

Không tự động ghi vào brain.db production khi chạy trong test (mặc định
db_path=None -> memory SQLite qua learning.self_optimizer venv-local path).
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class Priority(Enum):
    """Suggestion priority (Sprint 5 API)."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class PerformanceMetric:
    """Performance metric tracking."""
    metric_id: str
    name: str
    value: float
    unit: str
    timestamp: datetime
    context: Dict[str, Any]
    baseline: Optional[float] = None
    target: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric_id": self.metric_id,
            "name": self.name,
            "value": round(self.value, 4),
            "unit": self.unit,
            "baseline": self.baseline,
            "target": self.target,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class ErrorAnalysis:
    """Error analysis result."""
    error_id: str
    error_type: str
    description: str
    frequency: int
    severity: float  # 1-10
    root_cause: str
    affected_components: List[str]
    pattern: str
    first_occurrence: datetime
    last_occurrence: datetime
    suggested_fix: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_id": self.error_id,
            "error_type": self.error_type,
            "frequency": self.frequency,
            "severity": round(self.severity, 2),
            "root_cause": self.root_cause,
            "pattern": self.pattern,
            "suggested_fix": self.suggested_fix,
        }


@dataclass
class ImprovementSuggestion:
    """Improvement suggestion."""
    suggestion_id: str
    title: str
    description: str
    category: str
    priority: Priority
    impact_score: float  # 0-10
    effort_score: float  # 0-10
    roi_score: float  # impact/effort
    source_feedback_ids: List[str]
    status: str  # proposed, approved, in_progress, completed
    implementation_notes: str
    outcome_measured: bool = False
    outcome_value: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "suggestion_id": self.suggestion_id,
            "title": self.title,
            "category": self.category,
            "priority": self.priority.value,
            "impact_score": round(self.impact_score, 2),
            "effort_score": round(self.effort_score, 2),
            "roi_score": round(self.roi_score, 2),
            "status": self.status,
            "outcome_measured": self.outcome_measured,
        }


# ---------------------------------------------------------------------------
# Singleton-ish in-memory stores (Sprint 5 semantics: process-local engines)
# ---------------------------------------------------------------------------

_SHARED_METRICS: List[PerformanceMetric] = []
_SHARED_ERRORS: List[ErrorAnalysis] = []
_SHARED_SUGGESTIONS: List[ImprovementSuggestion] = []


class PerformanceMonitor:
    """Track metrics, analyze errors, propose improvements (Sprint 5 API).

    Thay thế FeedbackProcessor Sprint 5 bị mất cho nhóm năng lực giám sát
    hiệu năng; feedback thu thập vẫn đi qua FeedbackProcessor DB-backed
    hiện hành (một hệ thống một nguồn sự thật).
    """

    def __init__(self):
        self.metric_counter = 0
        self.error_counter = 0
        self.suggestion_counter = 0

    # -- metrics -----------------------------------------------------------

    def track_metric(self, metric_name: str, value: float, unit: str = "",
                     baseline: Optional[float] = None,
                     target: Optional[float] = None,
                     context: Optional[Dict[str, Any]] = None) -> PerformanceMetric:
        self.metric_counter += 1
        metric = PerformanceMetric(
            metric_id=f"PM_{self.metric_counter:04d}",
            name=metric_name,
            value=float(value),
            unit=unit,
            timestamp=datetime.now(),
            context=context or {},
            baseline=baseline,
            target=target,
        )
        _SHARED_METRICS.append(metric)
        return metric

    def get_performance_summary(self) -> Dict[str, Any]:
        if not _SHARED_METRICS:
            return {"message": "No performance metrics collected yet"}

        by_name: Dict[str, List[PerformanceMetric]] = defaultdict(list)
        for m in _SHARED_METRICS:
            by_name[m.name].append(m)

        metrics: Dict[str, Any] = {}
        trends: Dict[str, str] = {}
        for name, values in by_name.items():
            latest = values[-1]
            series = [v.value for v in values]
            metrics[name] = {
                "latest": latest.value,
                "unit": latest.unit,
                "count": len(values),
                "avg": round(sum(series) / len(series), 4),
                "min": round(min(series), 4),
                "max": round(max(series), 4),
                "baseline": latest.baseline,
                "target": latest.target,
            }
            if len(series) >= 2:
                first = series[0]
                last = series[-1]
                if first:
                    delta_pct = (last - first) / abs(first) * 100
                    if delta_pct > 5:
                        trends[name] = "improving"
                    elif delta_pct < -5:
                        trends[name] = "degrading"
                    else:
                        trends[name] = "stable"
                else:
                    trends[name] = "stable"

        return {"metrics": metrics, "trends": trends}

    # -- errors --------------------------------------------------------------

    def analyze_errors(self, error_logs: List[Dict[str, Any]]) -> List[ErrorAnalysis]:
        if not error_logs:
            return []

        groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for entry in error_logs:
            etype = str(entry.get("type", "unknown"))
            groups[etype].append(entry)

        analyses: List[ErrorAnalysis] = []
        total = len(error_logs)
        for etype, entries in groups.items():
            stamps = [e.get("timestamp") for e in entries if e.get("timestamp")]
            first_occ = min(stamps) if stamps else datetime.now()
            last_occ = max(stamps) if stamps else datetime.now()
            components = sorted({str(e.get("component", "unknown")) for e in entries})
            frequency = len(entries)
            ratio = frequency / total

            # Severity: tần suất tương đối nhân hệ số theo loại lỗi quen thuộc
            type_weight = {
                "timeout": 0.8, "null_pointer": 0.7, "connection": 0.7,
                "permission": 0.9, "auth": 0.9, "data_loss": 1.0,
            }.get(etype, 0.6)
            severity = min(10.0, round(ratio * 10 * type_weight + 1.0, 2))

            if ratio >= 0.5:
                pattern = "dominant"
            elif ratio >= 0.2:
                pattern = "recurring"
            else:
                pattern = "occasional"

            if components:
                root_cause = f"component issue in {', '.join(components)}"
            else:
                root_cause = "unknown component"
            suggested_fix = (
                f"Investigate {etype} in {', '.join(components)}; "
                f"add retry/timeout guard and monitor frequency"
            )

            self.error_counter += 1
            analyses.append(ErrorAnalysis(
                error_id=f"EA_{self.error_counter:04d}",
                error_type=etype,
                description=f"{etype} x{frequency} ({ratio:.0%} of errors)",
                frequency=frequency,
                severity=severity,
                root_cause=root_cause,
                affected_components=components,
                pattern=pattern,
                first_occurrence=first_occ,
                last_occurrence=last_occ,
                suggested_fix=suggested_fix,
            ))

        # Nặng nhất lên đầu
        analyses.sort(key=lambda a: a.severity, reverse=True)
        _SHARED_ERRORS.extend(analyses)
        return analyses

    # -- suggestions ---------------------------------------------------------

    def suggest_improvements(self) -> List[ImprovementSuggestion]:
        suggestions: List[ImprovementSuggestion] = []
        source_ids: List[str] = []

        # 1) Metric lệch so với target/baseline
        for m in _SHARED_METRICS:
            if m.target is not None and m.value > m.target:
                gap = m.value - m.target
                priority = Priority.HIGH if gap > m.target * 0.5 else Priority.MEDIUM
                suggestions.append(ImprovementSuggestion(
                    suggestion_id=f"IS_{self.suggestion_counter + 1:04d}",
                    title=f"Reduce {m.name}",
                    description=(
                        f"{m.name}={m.value}{m.unit} vượt target {m.target}{m.unit} "
                        f"(gap {round(gap, 2)})"
                    ),
                    category="performance",
                    priority=priority,
                    impact_score=min(10.0, 4.0 + gap / max(m.target, 1e-9) * 3),
                    effort_score=5.0,
                    roi_score=min(10.0, (4.0 + gap / max(m.target, 1e-9) * 3) / 5.0 * 10 / 2),
                    source_feedback_ids=[m.metric_id],
                    status="proposed",
                    implementation_notes="Đo lại sau tối ưu; so baseline trước/sau",
                ))
                self.suggestion_counter += 1

        # 2) Lỗi nghiêm trọng → đề xuất xử lý
        for e in _SHARED_ERRORS:
            if e.severity >= 5.0 or e.pattern == "dominant":
                suggestions.append(ImprovementSuggestion(
                    suggestion_id=f"IS_{self.suggestion_counter + 1:04d}",
                    title=f"Fix recurring {e.error_type}",
                    description=e.description,
                    category="reliability",
                    priority=Priority.CRITICAL if e.severity >= 8 else Priority.HIGH,
                    impact_score=min(10.0, e.severity),
                    effort_score=4.0,
                    roi_score=min(10.0, e.severity / 4.0 * 10 / 2),
                    source_feedback_ids=[e.error_id],
                    status="proposed",
                    implementation_notes=e.suggested_fix,
                ))
                self.suggestion_counter += 1
                source_ids.append(e.error_id)

        _SHARED_SUGGESTIONS.extend(suggestions)
        return suggestions


# ---------------------------------------------------------------------------
# Sprint 5 module-level convenience API (đúng chữ ký gốc 0bd5daa)
# ---------------------------------------------------------------------------

_MONITOR = PerformanceMonitor()


def collect_user_feedback(text: str, rating: float = None, category: str = "general") -> Any:
    """Ủy quyền về FeedbackProcessor DB-backed hiện hành (import muộn tránh cycle)."""
    from quan_ai_brain.learning.feedback_processor import FeedbackCategory, FeedbackProcessor, FeedbackType

    processor = FeedbackProcessor()
    try:
        cat = FeedbackCategory(category)
    except ValueError:
        cat = FeedbackCategory.OTHER
    try:
        ftype = FeedbackType.TEXT if rating is None else FeedbackType.RATING
        return processor.submit_feedback(
            feedback_type=ftype,
            category=cat,
            rating=rating,
            text=text,
        )
    except Exception:
        return None


def track_performance(name: str, value: float, unit: str = "") -> PerformanceMetric:
    """Track metric — ủy quyền DB-backed self-optimizer nếu có, luôn trả metric."""
    metric = _MONITOR.track_metric(name, value, unit)
    try:
        from quan_ai_brain.learning.self_optimizer import SelfOptimizer
        import tempfile, os
        # KHÔNG đụng brain.db production từ đường tiện ích này
        db_path = os.path.join(tempfile.gettempdir(), "quan_perf_metrics.db")
        opt = SelfOptimizer(db_path=db_path)
        if opt.get_parameter(f"perf_{name}") is None:
            opt.register_parameter(f"perf_{name}", value, description=f"metric {name} ({unit})")
        else:
            opt.set_parameter(f"perf_{name}", value)
    except Exception:
        pass
    return metric


def analyze_system_errors(logs: List[Dict[str, Any]]) -> List[ErrorAnalysis]:
    return _MONITOR.analyze_errors(logs)


def suggest_improvements() -> List[ImprovementSuggestion]:
    return _MONITOR.suggest_improvements()
