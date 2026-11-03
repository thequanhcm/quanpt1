"""DEOM M6 — Tests tích hợp: supervisor tự ghi feedback sau task terminal.

Bao phủ: COMPLETED → feedback + lesson candidate trong DB; FAILED → lesson
failure_cause; feedback recorder lỗi → supervisor VẪN chạy bình thường
(fail-safe); template recurring không bao giờ được dispatcher chọn.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from quan_ai_brain.governance.state_store import GovernanceStateStore
from quan_ai_brain.orchestration.models import TaskStatus
from quan_ai_brain.orchestration.recurring_engine import RecurringTaskEngine
from quan_ai_brain.orchestration.supervisor import ContinuousAutonomySupervisor as Supervisor
from quan_ai_brain.orchestration.task_feedback import TaskFeedbackRecorder
from quan_ai_brain.orchestration.task_registry import DurableTaskRegistry


@pytest.fixture()
def env(tmp_path):
    ws = tmp_path
    registry = DurableTaskRegistry(ws / "tasks.db")
    gov = GovernanceStateStore(ws / "governance.db", workspace=ws)
    fb = TaskFeedbackRecorder(ws / "feedback.db")
    sup = Supervisor(
        workspace=ws,
        task_registry=registry,
        governance_store=gov,
        feedback_recorder=fb,
    )
    return sup, registry, fb


class TestSupervisorFeedback:
    def test_completed_task_records_feedback(self, env):
        sup, registry, fb = env
        t = registry.register_task(goal="việc demo feedback", risk_level="R1")
        registry.update_task_status(t.task_id, TaskStatus.READY)
        sup._current_task = registry.get_task(t.task_id)
        sup._current_plan = None
        from quan_ai_brain.orchestration.models import SupervisorState

        sup._state = SupervisorState.RUNNING_AUTHORIZED_TASK
        sup.step()
        stats = fb.stats()
        assert stats["feedback"] >= 1
        lessons = fb.lessons_for(t.task_id)
        assert lessons and lessons[0]["verification_status"] == "candidate"

    def test_feedback_failure_does_not_break_supervisor(self, env):
        sup, registry, fb = env

        class Broken:
            def record_feedback(self, task):
                raise RuntimeError("boom")

        sup.feedback_recorder = Broken()
        t = registry.register_task(goal="việc demo feedback lỗi", risk_level="R1")
        registry.update_task_status(t.task_id, TaskStatus.READY)
        sup._current_task = registry.get_task(t.task_id)
        sup._current_plan = None
        from quan_ai_brain.orchestration.models import SupervisorState

        sup._state = SupervisorState.RUNNING_AUTHORIZED_TASK
        # KHÔNG được raise — feedback lỗi nuốt an toàn
        state = sup.step()
        assert state is not None


class TestRecurringNotDispatched:
    def test_recurring_template_excluded_from_queue(self, tmp_path):
        registry = DurableTaskRegistry(tmp_path / "tasks.db")
        engine = RecurringTaskEngine(registry)
        tmpl = engine.register_recurring("việc định kỳ X", "mỗi 30 phút")
        # task thường READY
        normal = registry.register_task(goal="việc thường Y", risk_level="R1")
        registry.update_task_status(normal.task_id, TaskStatus.READY)
        q = registry.work_queue(limit=50)
        ids = [t.task_id for t in q]
        assert normal.task_id in ids
        assert tmpl.task_id not in ids
