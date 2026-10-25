"""Unit tests for ContinuousEvaluationHarness and measurable intelligence in QUAN AI BRAIN."""
from __future__ import annotations

from pathlib import Path
import pytest

from quan_ai_brain.contract.models import TaskOutcome, TaskState
from quan_ai_brain.governance.consultation_inbox import ConsultationStore
from quan_ai_brain.learning.evaluation import BenchmarkTaskResult, ContinuousEvaluationHarness, EvaluationMetric
from quan_ai_brain.learning.periodic_reporter import PeriodicLearningReporter
from quan_ai_brain.memory.sqlite_store import MemoryStore
from quan_ai_brain.orchestration.models import TaskStatus
from quan_ai_brain.orchestration.task_registry import DurableTaskRegistry


def test_run_benchmark_suite(tmp_path: Path) -> None:
    harness = ContinuousEvaluationHarness(tmp_path)
    results = harness.run_benchmark_suite()

    assert len(results) == 5
    task_names = [r.task_name for r in results]
    assert "governance_r5_hard_block" in task_names
    assert "vietnamese_memory_retrieval" in task_names
    assert "dag_cycle_rejection" in task_names
    assert "quarantine_candidate_isolation" in task_names
    assert "credential_redaction_filter" in task_names

    # All 5 standard benchmarks must pass on baseline
    assert all(r.passed for r in results)
    assert all(r.score == 1.0 for r in results)
    assert all(r.latency_ms >= 0 for r in results)


def test_measure_upgrade_progress_computes_improvement(tmp_path: Path) -> None:
    harness = ContinuousEvaluationHarness(tmp_path)
    metric = harness.measure_upgrade_progress(simulated_latency_reduction_ms=2.0)

    assert isinstance(metric, EvaluationMetric)
    assert metric.metric_id.startswith("eval_")
    assert metric.overall_score_before == 1.0
    assert metric.regression_detected is False
    assert metric.recommendation == "PROCEED"
    assert len(metric.benchmark_results) == 5


def test_learning_cycle_drains_real_failed_task_from_registry(tmp_path: Path) -> None:
    mem_store = MemoryStore(":memory:", workspace=tmp_path)
    cst_store = ConsultationStore(":memory:")
    registry = DurableTaskRegistry(":memory:", workspace=tmp_path)

    # Register a task and mark it FAILED
    real_task = registry.register_task(
        goal="Truy xuất dữ liệu hiệu năng bộ nhớ đệm",
        risk_level="R1",
    )
    registry.update_task_status(
        real_task.task_id,
        TaskStatus.FAILED,
        error_message="Quá tải thời gian truy xuất bộ nhớ (>150ms)",
    )

    reporter = PeriodicLearningReporter(
        workspace=tmp_path,
        db_path=":memory:",
        memory_store=mem_store,
        consultation_store=cst_store,
        task_registry=registry,
    )

    report = reporter.trigger_learning_cycle(trigger_reason="real_task_error_drain")
    assert report.cycle_number == 2
    assert real_task.task_id in report.summary
    assert len(report.gaps_detected) >= 1
    # Check that gap description references the real error
    assert "Quá tải" in report.gaps_detected[0]["description"]
    # Check that recommendations include measurable evaluation
    assert any("Đo lường tiến bộ" in rec for rec in report.recommendations)


def test_learning_cycle_with_explicit_task_outcome(tmp_path: Path) -> None:
    mem_store = MemoryStore(":memory:", workspace=tmp_path)
    cst_store = ConsultationStore(":memory:")

    reporter = PeriodicLearningReporter(
        workspace=tmp_path,
        db_path=":memory:",
        memory_store=mem_store,
        consultation_store=cst_store,
    )

    explicit_outcome = TaskOutcome(
        task_id="task_explicit_error_999",
        request_id="req_999",
        correlation_id="corr_999",
        state=TaskState.FAILED,
        error_message="Lỗi kết nối timeout khi gọi local endpoint",
        is_outcome_certain=True,
    )

    report = reporter.trigger_learning_cycle(
        trigger_reason="explicit_outcome_test",
        task_outcome=explicit_outcome,
    )
    assert "task_explicit_error_999" in report.summary
    assert "Lỗi kết nối timeout" in report.gaps_detected[0]["description"]
