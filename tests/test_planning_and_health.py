import pytest

from quan_ai_brain.daemon.health import get_health_snapshot
from quan_ai_brain.planning.models import TaskPlan, TaskStep


def test_validates_task_plan():
    plan = TaskPlan(goal="Create a report", steps=[TaskStep("inventory", "List safe files", "Markdown inventory", 0)])
    plan.validate()


def test_high_risk_step_must_mark_approval_or_blocking():
    plan = TaskPlan(goal="Change policy", steps=[TaskStep("change", "Modify production policy", "Updated policy", 4)])
    with pytest.raises(ValueError):
        plan.validate()


def test_health_snapshot_is_explicitly_only_skeleton():
    snapshot = get_health_snapshot()
    assert snapshot.status == "ok"
    assert "not implemented" in snapshot.note
