"""V39 Learning Engine tests — repaired 30/10/2026.

LỊCH SỬ: commit e6135a5 (memory expansion) ghi đè feedback_processor.py /
self_optimizer.py của Sprint 5 gốc (0bd5daa) → test này ERROR collection từ
30/10 (import class không tồn tại). Repair:
- Monitoring API (PerformanceMetric, ErrorAnalysis, ImprovementSuggestion,
  Priority, collect_user_feedback, track_performance, analyze_system_errors,
  suggest_improvements) được KHÔI PHỤC trong performance_monitor.py.
- SelfOptimizer hiện hành là DB-backed (25/25 test Sprint 5 PASS) — phần test
  ở đây dùng đúng API hiện hành (register/optimize_parameter/history).
- KnowledgeRefiner (prune/update/prioritize) nằm ở knowledge_refiner.py.
"""
import sys
from datetime import datetime
from pathlib import Path

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# (30/10/2026) RESTORE: monitoring API Sprint 5 khôi phục trong performance_monitor.
from quan_ai_brain.learning.performance_monitor import (
    ErrorAnalysis,
    ImprovementSuggestion,
    PerformanceMetric,
    PerformanceMonitor,
    Priority,
    analyze_system_errors,
    collect_user_feedback,
    suggest_improvements,
    track_performance,
)

from quan_ai_brain.learning.self_optimizer import SelfOptimizer
from quan_ai_brain.learning.knowledge_refiner import KnowledgeRefiner


# ==================== PERFORMANCE MONITOR TESTS (Sprint 5 API) ====================

class TestPerformanceMonitor:
    """Test performance monitoring (API Sprint 5 khôi phục)."""

    @pytest.fixture
    def monitor(self):
        """Create PerformanceMonitor instance."""
        return PerformanceMonitor()

    def test_track_metric(self, monitor):
        """Test performance metric tracking."""
        metric = monitor.track_metric(
            metric_name="response_time",
            value=150.5,
            unit="ms",
            baseline=200.0,
            target=100.0
        )

        assert isinstance(metric, PerformanceMetric)
        assert metric.name == "response_time"
        assert metric.value == 150.5
        assert metric.unit == "ms"

    def test_analyze_errors(self, monitor):
        """Test error analysis."""
        error_logs = [
            {"type": "timeout", "component": "api", "timestamp": datetime.now()},
            {"type": "timeout", "component": "api", "timestamp": datetime.now()},
            {"type": "timeout", "component": "database", "timestamp": datetime.now()},
            {"type": "null_pointer", "component": "service", "timestamp": datetime.now()}
        ]

        analyses = monitor.analyze_errors(error_logs)

        assert len(analyses) > 0
        assert any(a.error_type == "timeout" for a in analyses)
        assert all(isinstance(a, ErrorAnalysis) for a in analyses)

    def test_analyze_errors_empty(self, monitor):
        """Error analysis with no errors."""
        assert monitor.analyze_errors([]) == []

    def test_get_performance_summary(self, monitor):
        """Test performance summary."""
        monitor.track_metric("accuracy", 0.95)
        monitor.track_metric("accuracy", 0.97)
        monitor.track_metric("latency", 150)

        summary = monitor.get_performance_summary()

        assert "metrics" in summary
        assert "accuracy" in summary["metrics"]
        assert "trends" in summary

    def test_get_performance_summary_empty(self, monitor):
        """Summary on empty store must not crash."""
        monitor_fresh = PerformanceMonitor()
        # shared store may already have data from other tests; only shape-check
        summary = monitor_fresh.get_performance_summary()
        assert isinstance(summary, dict)

    def test_suggest_improvements(self, monitor):
        """Test improvement suggestion generation."""
        monitor.track_metric("latency_p95", 4800, unit="ms", baseline=2000, target=1000)
        monitor.analyze_errors([
            {"type": "timeout", "component": "api", "timestamp": datetime.now()},
            {"type": "timeout", "component": "api", "timestamp": datetime.now()},
        ])
        suggestions = monitor.suggest_improvements()

        assert isinstance(suggestions, list)
        assert len(suggestions) > 0
        assert all(isinstance(s, ImprovementSuggestion) for s in suggestions)
        assert all(s.priority in list(Priority) for s in suggestions)

    def test_suggestion_priority_values(self):
        """Priority enum has Sprint 5 members."""
        assert Priority.CRITICAL.value == "critical"
        assert Priority.HIGH.value == "high"
        assert Priority.MEDIUM.value == "medium"
        assert Priority.LOW.value == "low"


# ==================== FEEDBACK PROCESSOR TESTS (API hiện hành) ====================

class TestFeedbackProcessor:
    """Test feedback collection (DB-backed, hiện hành)."""

    @pytest.fixture
    def processor(self):
        from quan_ai_brain.learning.feedback_processor import FeedbackProcessor
        return FeedbackProcessor()

    def test_collect_feedback(self, processor):
        from quan_ai_brain.learning.feedback_processor import FeedbackCategory, FeedbackType
        feedback = processor.submit_feedback(
            feedback_type=FeedbackType.RATING,
            category=FeedbackCategory.OTHER,
            rating=5.0,
            text="Great service!"
        )
        assert feedback is not None
        assert feedback.rating == 5.0
        assert feedback.sentiment is not None

    def test_collect_feedback_negative(self, processor):
        from quan_ai_brain.learning.feedback_processor import (
            FeedbackCategory, FeedbackType, Sentiment)
        feedback = processor.submit_feedback(
            feedback_type=FeedbackType.TEXT,
            category=FeedbackCategory.OTHER,
            text="Terrible experience, very slow"
        )
        assert feedback.sentiment == Sentiment.NEGATIVE

    def test_get_feedback_statistics(self, processor):
        from quan_ai_brain.learning.feedback_processor import FeedbackCategory, FeedbackType
        processor.submit_feedback(FeedbackType.RATING, FeedbackCategory.OTHER, rating=4.0, text="Good")
        processor.submit_feedback(FeedbackType.RATING, FeedbackCategory.OTHER, rating=2.0, text="Bad")
        processor.submit_feedback(FeedbackType.TEXT, FeedbackCategory.OTHER, text="Great!")

        stats = processor.get_statistics()
        assert "total_feedbacks" in stats
        assert stats["total_feedbacks"] >= 3
        assert "avg_rating" in stats


# ==================== SELF OPTIMIZER TESTS (API hiện hành DB-backed) ====================

class TestSelfOptimizer:
    """Test SelfOptimizer (DB-backed hiện hành)."""

    @pytest.fixture
    def optimizer(self, tmp_path):
        """Isolated SelfOptimizer per test (không đụng brain.db production)."""
        return SelfOptimizer(db_path=str(tmp_path / "test_optimizer.db"))

    def test_register_and_get_parameter(self, optimizer):
        optimizer.register_parameter("threshold", 0.5, min_value=0.0,
                                     max_value=1.0, step=0.1)
        assert optimizer.get_parameter("threshold") == 0.5

    def test_optimize_parameter(self, optimizer):
        optimizer.register_parameter("gain", 0.5, min_value=0.0,
                                     max_value=1.0, step=0.05)

        def fake_metric(params):
            return abs(0.75 - params.get("gain", 0))

        result = optimizer.optimize_parameter("gain", fake_metric,
                                              iterations=5, direction="minimize")
        assert "best_value" in result
        assert result["iterations"] == 5
        assert 0.0 <= result["best_value"] <= 1.0

    def test_optimization_history(self, optimizer):
        optimizer.register_parameter("p1", 0.5, min_value=0, max_value=1)
        optimizer.optimize_parameter("p1", lambda p: 1.0, iterations=3)
        history = optimizer.get_optimization_history(limit=10)
        assert isinstance(history, list)
        assert len(history) >= 1

    def test_get_statistics(self, optimizer):
        stats = optimizer.get_statistics()
        assert "total_runs" in stats
        assert "total_parameters" in stats


# ==================== KNOWLEDGE REFINER TESTS ====================

class TestKnowledgeRefiner:
    """Test knowledge quality/refinement (API hiện hành knowledge_refiner)."""

    @pytest.fixture
    def refiner(self, tmp_path):
        return KnowledgeRefiner(db_path=str(tmp_path / "test_refiner.db"))

    def test_record_refinement(self, refiner):
        ref_id = refiner.record_refinement(
            knowledge_id="K1",
            refinement_type="update",
            old_value="stale",
            new_value="fresh",
            reason="stale content",
            confidence_before=0.4,
            confidence_after=0.8,
        )
        assert ref_id is not None

    def test_assess_quality(self, refiner):
        q = refiner.assess_quality("K2", accuracy=0.9, completeness=0.8,
                                   recency=0.9, feedback=0.8)
        assert q is not None
        assert 0.0 <= q.overall_score <= 1.0

    def test_get_refinements_empty(self, refiner):
        assert refiner.get_refinements(knowledge_id="NONE") == []


# ==================== CONVENIENCE FUNCTIONS (Sprint 5 module API) ====================

class TestConvenienceFunctions:
    def test_collect_user_feedback(self):
        fb = collect_user_feedback("Test feedback", rating=4.0)
        assert fb is not None

    def test_track_performance(self):
        metric = track_performance("test_metric", 100.0, "ms")
        assert metric is not None
        assert isinstance(metric, PerformanceMetric)

    def test_analyze_system_errors(self):
        errors = analyze_system_errors([{"type": "test", "component": "test"}])
        assert isinstance(errors, list)

    def test_suggest_improvements(self):
        suggestions = suggest_improvements()
        assert isinstance(suggestions, list)


# ==================== INTEGRATION ====================

class TestLearningIntegration:
    def test_feedback_to_suggestion_pipeline(self):
        """Full loop: metric + errors -> suggestions (Sprint 5 pipeline)."""
        monitor = PerformanceMonitor()
        monitor.track_metric("error_rate", 0.08, baseline=0.02, target=0.03)
        monitor.analyze_errors([
            {"type": "timeout", "component": "responder", "timestamp": datetime.now()},
            {"type": "timeout", "component": "responder", "timestamp": datetime.now()},
            {"type": "timeout", "component": "responder", "timestamp": datetime.now()},
        ])
        suggestions = monitor.suggest_improvements()
        assert isinstance(suggestions, list)
        # Có lỗi dominant severity cao → phải có ít nhất 1 đề xuất fix
        assert any("timeout" in s.title.lower() or "error_rate" in s.title.lower()
                   for s in suggestions)
