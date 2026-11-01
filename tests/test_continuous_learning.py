"""Tests for Sprint 5 — Continuous Learning Engine.

Tests for 5-type learning:
- Type A: Learn new knowledge
- Type B: Learn from experience
- Type C: Learn usage
- Type D: Sandbox experiments
- Type E: System changes (approval)
- Evaluation
"""
import sys

sys.path.insert(0, "src")

from quan_ai_brain.cognition.continuous_learning_engine import (
    ContinuousLearningEngine,
    LearningType,
    LearningStatus,
)
from quan_ai_brain.memory.knowledge_ingestion import KnowledgeSource
from quan_ai_brain.memory.sqlite_store import MemoryStore


def test_type_a_knowledge():
    """Type A: Learn new knowledge from authorized sources."""
    store = MemoryStore(":memory:")
    engine = ContinuousLearningEngine(store)

    report = engine.learn_type_a_knowledge(
        content="GLM-5.3-Flash là model chủ lực cho hội thoại.",
        source_type=KnowledgeSource.PROJECT_DOCS,
        source_ref="docs/LLM_CONFIG.md",
        tags=["llm", "configuration"],
    )

    assert report.learning_type == LearningType.TYPE_A_KNOWLEDGE
    assert report.status == LearningStatus.COMPLETED
    assert report.success is True
    assert report.knowledge_id is not None
    assert report.source == "docs/LLM_CONFIG.md"

    print("✓ Type A: Learn knowledge: PASS")


def test_type_b_experience_success():
    """Type B: Learn from successful task."""
    store = MemoryStore(":memory:")
    engine = ContinuousLearningEngine(store)

    report = engine.learn_type_b_experience(
        task_goal="Deploy Sprint 2 to Pi 5",
        task_result="SUCCESS: All files uploaded, kiosk running",
        success=True,
    )

    assert report.learning_type == LearningType.TYPE_B_EXPERIENCE
    assert report.status == LearningStatus.COMPLETED
    assert report.success is True
    assert report.knowledge_id is not None

    print("✓ Type B: Learn experience (success): PASS")


def test_type_b_experience_failure():
    """Type B: Learn from failed task with root cause."""
    store = MemoryStore(":memory:")
    engine = ContinuousLearningEngine(store)

    report = engine.learn_type_b_experience(
        task_goal="Test barge-in on Pi 5",
        task_result="FAILED: Audio did not stop when speaking",
        success=False,
        root_cause="Barge-in JS not loaded in kiosk root",
        lesson_learned="Verify file checksum after upload",
    )

    assert report.learning_type == LearningType.TYPE_B_EXPERIENCE
    assert report.status == LearningStatus.COMPLETED
    assert report.success is True  # Learning succeeded even though task failed
    assert report.proposal is not None
    assert report.proposal["type"] == "improvement"

    print("✓ Type B: Learn experience (failure): PASS")


def test_type_c_usage_success():
    """Type C: Learn from successful retrieval."""
    store = MemoryStore(":memory:")
    engine = ContinuousLearningEngine(store)

    report = engine.learn_type_c_usage(
        query="What is the default LLM model?",
        retrieved_knowledge=["know_abc123", "know_def456"],
        success=True,
    )

    assert report.learning_type == LearningType.TYPE_C_USAGE
    assert report.status == LearningStatus.COMPLETED
    assert report.success is True
    assert report.knowledge_id is not None

    print("✓ Type C: Learn usage (success): PASS")


def test_type_c_usage_failure():
    """Type C: Learn from failed retrieval."""
    store = MemoryStore(":memory:")
    engine = ContinuousLearningEngine(store)

    report = engine.learn_type_c_usage(
        query="How to configure barge-in?",
        retrieved_knowledge=[],
        success=False,
        feedback="No relevant knowledge found",
    )

    assert report.learning_type == LearningType.TYPE_C_USAGE
    assert report.status == LearningStatus.COMPLETED
    assert report.success is True  # Learning succeeded
    assert report.proposal is not None
    assert report.proposal["type"] == "retrieval_improvement"

    print("✓ Type C: Learn usage (failure): PASS")


def test_type_d_sandbox_success():
    """Type D: Successful sandbox experiment."""
    store = MemoryStore(":memory:")
    engine = ContinuousLearningEngine(store)

    baseline = {"precision@5": 0.65, "recall@5": 0.60, "mrr": 0.70}
    results = {"precision@5": 0.75, "recall@5": 0.72, "mrr": 0.78}

    report = engine.learn_type_d_sandbox(
        hypothesis="Adding conflict detection improves retrieval precision",
        experiment_design="Compare retrieval with/without conflict detection",
        baseline_metrics=baseline,
        experiment_results=results,
        conclusion="Conflict detection reduces false positives by 15%",
    )

    assert report.learning_type == LearningType.TYPE_D_SANDBOX
    assert report.status == LearningStatus.COMPLETED
    assert report.success is True
    assert report.proposal is not None
    assert report.proposal["type"] == "deployment_request"
    assert report.test_results["overall_improvement"] > 0

    print("✓ Type D: Sandbox experiment (success): PASS")


def test_type_d_sandbox_failure():
    """Type D: Failed sandbox experiment."""
    store = MemoryStore(":memory:")
    engine = ContinuousLearningEngine(store)

    baseline = {"precision@5": 0.65, "recall@5": 0.60}
    results = {"precision@5": 0.62, "recall@5": 0.58}

    report = engine.learn_type_d_sandbox(
        hypothesis="Changing embedding model improves recall",
        experiment_design="Test new model on benchmark dataset",
        baseline_metrics=baseline,
        experiment_results=results,
        conclusion="New model performs worse on Vietnamese queries",
    )

    assert report.learning_type == LearningType.TYPE_D_SANDBOX
    assert report.status == LearningStatus.COMPLETED
    assert report.success is False  # Experiment failed
    assert report.proposal is None  # No deployment proposal

    print("✓ Type D: Sandbox experiment (failure): PASS")


def test_type_e_system_change():
    """Type E: System change requiring approval."""
    store = MemoryStore(":memory:")
    engine = ContinuousLearningEngine(store)

    report = engine.learn_type_e_system(
        change_description="Upgrade BGE-M3 to latest version",
        diff="Updated embedding model version from 1.0 to 2.0",
        test_results={"regression": "PASS", "benchmark": "PASS"},
        risk_level=2,
        rollback_plan="Revert to BGE-M3 v1.0 if issues occur",
    )

    assert report.learning_type == LearningType.TYPE_E_SYSTEM
    assert report.status == LearningStatus.PROPOSING  # Waiting for approval
    assert report.proposal is not None
    assert report.proposal["requires_owner_approval"] is True
    assert report.proposal["risk_level"] == 2

    print("✓ Type E: System change (pending approval): PASS")


def test_evaluation():
    """Test learning evaluation."""
    store = MemoryStore(":memory:")
    engine = ContinuousLearningEngine(store)

    eval_result = engine.evaluate_learning(
        baseline_precision=0.60,
        baseline_recall=0.55,
        baseline_mrr=0.65,
        post_precision=0.72,
        post_recall=0.68,
        post_mrr=0.75,
    )

    assert eval_result.precision_improvement > 0
    assert eval_result.recall_improvement > 0
    assert eval_result.mrr_improvement > 0
    assert eval_result.overall_improvement > 0
    assert eval_result.passed is True

    print("✓ Evaluation: PASS")


def test_get_reports():
    """Test retrieving reports by type."""
    store = MemoryStore(":memory:")
    engine = ContinuousLearningEngine(store)

    # Create multiple reports
    engine.learn_type_a_knowledge("Test A1", KnowledgeSource.PROJECT_DOCS, "test1.md")
    engine.learn_type_a_knowledge("Test A2", KnowledgeSource.PROJECT_DOCS, "test2.md")
    engine.learn_type_b_experience("Task 1", "Result", True)

    # Get Type A reports
    type_a_reports = engine.get_reports(learning_type=LearningType.TYPE_A_KNOWLEDGE)
    assert len(type_a_reports) == 2

    # Get all reports
    all_reports = engine.get_reports()
    assert len(all_reports) == 3

    print("✓ Get reports: PASS")


def test_pending_approvals():
    """Test getting pending approvals."""
    store = MemoryStore(":memory:")
    engine = ContinuousLearningEngine(store)

    # Create a Type E change
    engine.learn_type_e_system(
        "Change 1", "Diff 1", {"test": "PASS"}, 2, "Rollback 1"
    )
    engine.learn_type_e_system(
        "Change 2", "Diff 2", {"test": "PASS"}, 3, "Rollback 2"
    )

    pending = engine.get_pending_approvals()
    assert len(pending) == 2

    print("✓ Pending approvals: PASS")


def main() -> int:
    """Run all tests."""
    print("=" * 60)
    print("Sprint 5 — Continuous Learning Engine Tests")
    print("=" * 60)

    tests = [
        test_type_a_knowledge,
        test_type_b_experience_success,
        test_type_b_experience_failure,
        test_type_c_usage_success,
        test_type_c_usage_failure,
        test_type_d_sandbox_success,
        test_type_d_sandbox_failure,
        test_type_e_system_change,
        test_evaluation,
        test_get_reports,
        test_pending_approvals,
    ]

    failed = 0
    for test in tests:
        try:
            test()
        except AssertionError as e:
            print(f"✗ {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test.__name__}: {type(e).__name__}: {e}")
            failed += 1

    print("=" * 60)
    if failed == 0:
        print(f"✓ All {len(tests)} tests passed — Sprint 5 continuous learning ready")
        return 0
    else:
        print(f"✗ {failed}/{len(tests)} tests failed")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())