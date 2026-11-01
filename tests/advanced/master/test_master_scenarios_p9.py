"""ADVANCED ASSURANCE — P9: 3 Master Scenarios tổng hợp (Phần 13).

MS1: ngày làm việc chuẩn (goal → plan → execute → verify → feedback → lesson candidate).
MS2: sự cố giữa chừng (step FAILED → DAG chặn → task FAILED → lesson failure_cause;
     lifecycle chạy lại KHÔNG "chữa lành" ngầm).
MS3: khủng hoảng + phục hồi (supervisor sập giữa chừng → OUTCOME_UNKNOWN → emergency
     STOP chặn task mới → hủy STOP → vận hành lại).
Toàn bộ component thật + tmp_path, không LLM/network, không đụng production.
"""
from __future__ import annotations

import pytest

from quan_ai_brain.governance.state_store import GovernanceStateStore
from quan_ai_brain.learning.learning_metrics import LearningMetrics
from quan_ai_brain.orchestration.models import SupervisorState, TaskStatus
from quan_ai_brain.orchestration.plan_orchestrator import PlanOrchestrator
from quan_ai_brain.orchestration.supervisor import ContinuousAutonomySupervisor as Supervisor
from quan_ai_brain.orchestration.task_feedback import TaskFeedbackRecorder
from quan_ai_brain.orchestration.task_registry import DurableTaskRegistry
from quan_ai_brain.planning.models import TaskPlan, TaskStep


@pytest.fixture()
def ws(tmp_path):
    return tmp_path


@pytest.fixture()
def stack(ws):
    registry = DurableTaskRegistry(ws / "data" / "tasks.db")
    gov = GovernanceStateStore(ws / "data" / "governance.db", workspace=ws)
    fb = TaskFeedbackRecorder(ws / "data" / "feedback.db")
    orch = PlanOrchestrator(task_registry=registry, workspace=ws)
    sup = Supervisor(workspace=ws, task_registry=registry, governance_store=gov, feedback_recorder=fb)
    return registry, gov, fb, orch, sup


def _plan(goal: str, *, n_steps: int = 2) -> TaskPlan:
    steps = [
        TaskStep(
            name=f"work_{i}", description=f"Phần việc {i}: {goal}", expected_output="Kết quả phần việc",
            risk_level=1, step_id=f"step-{i}", sequence=i,
            dependencies=[f"step-{i-1}"] if i > 1 else [], verification_method="Owner soát",
        )
        for i in range(1, n_steps + 1)
    ]
    plan = TaskPlan(goal=goal, steps=steps)
    plan.validate()
    return plan


# ---------------------------------------------------------------------------
# MS1 — Ngày làm việc chuẩn
# ---------------------------------------------------------------------------
class TestMS1FullDay:
    def test_goal_to_lesson_candidate(self, ws, stack):
        registry, gov, fb, orch, sup = stack
        task = orch.submit_plan(_plan("tổng hợp báo cáo tuần và gửi anh Quân"))
        orch.execute_lifecycle(task.task_id, dry_run=True)
        done = registry.get_task(task.task_id)
        assert done.status in (TaskStatus.COMPLETED, TaskStatus.COMPLETED_VERIFIED)
        # supervisor ghi feedback cho task đã terminal (không cần step() — G-C
        # chặn terminal → COMPLETED lại; gọi recorder trực tiếp như M6 wire)
        from quan_ai_brain.orchestration.task_feedback import safe_record_feedback

        safe_record_feedback(fb, done)
        lessons = fb.lessons_for(task.task_id)
        assert lessons and lessons[0]["verification_status"] == "candidate"
        lm = LearningMetrics(ws / "data" / "tasks.db", feedback_db=ws / "data" / "feedback.db")
        rep = lm.learning_report()
        assert rep["lessons"]["candidate"] >= 1
        assert rep["feedback"] >= 1


# ---------------------------------------------------------------------------
# MS2 — Sự cố giữa chừng, fail-honest
# ---------------------------------------------------------------------------
class TestMS2MidwayFailure:
    def test_failure_blocks_dag_and_learns(self, ws, stack):
        registry, gov, fb, orch, sup = stack
        task = orch.submit_plan(_plan("kiểm kê kho rồi tổng hợp báo cáo", n_steps=3))
        tid = task.task_id
        registry.update_task_status(tid, TaskStatus.IN_PROGRESS)
        # bước 2 lỗi giữa chừng
        steps = registry.list_steps_for_task(tid)
        second = [s for s in steps if s.step_id == "step-2"][0]
        registry.update_step_status(second.step_id, TaskStatus.FAILED, error_message="nguồn dữ liệu lỗi")
        orch.execute_lifecycle(tid, dry_run=True)
        by_id = {s.step_id: s for s in registry.list_steps_for_task(tid)}
        assert by_id["step-2"].status == TaskStatus.FAILED
        assert by_id["step-3"].status in (TaskStatus.BLOCKED, TaskStatus.PENDING)
        # lifecycle chạy lại: KHÔNG tự chữa lành — bước FAILED vẫn FAILED
        orch.execute_lifecycle(tid, dry_run=True)
        by_id = {s.step_id: s for s in registry.list_steps_for_task(tid)}
        assert by_id["step-2"].status == TaskStatus.FAILED
        assert by_id["step-3"].status in (TaskStatus.BLOCKED, TaskStatus.PENDING)
        # học từ thất bại
        rec = registry.get_task(tid)
        from quan_ai_brain.orchestration.task_feedback import safe_record_feedback

        safe_record_feedback(fb, rec)
        lessons = fb.lessons_for(tid)
        assert lessons and lessons[0]["kind"] == "failure_cause"


# ---------------------------------------------------------------------------
# MS3 — Khủng hoảng + phục hồi
# ---------------------------------------------------------------------------
class TestMS3CrisisRecovery:
    def test_crash_to_outcome_unknown_then_emergency_then_resume(self, ws, stack):
        registry, gov, fb, orch, sup = stack
        task = orch.submit_plan(_plan("việc dài hạn cần chạy qua nhiều bước"))
        tid = task.task_id
        registry.update_task_status(tid, TaskStatus.IN_PROGRESS)

        # 1. Supervisor "sập" → recovery: IN_PROGRESS → OUTCOME_UNKNOWN (không tự re-run)
        recovered = registry.recover_in_flight_tasks()
        assert tid in [t.task_id for t in recovered]
        assert registry.get_task(tid).status == TaskStatus.OUTCOME_UNKNOWN

        # 2. OUTCOME_UNKNOWN KHÔNG tự chạy lại được (G-C: state machine chặn)
        from quan_ai_brain.orchestration.task_state_machine import InvalidTaskTransitionError

        with pytest.raises(InvalidTaskTransitionError):
            registry.update_task_status(tid, TaskStatus.IN_PROGRESS)

        # 3. Emergency STOP chặn lifecycle task mới
        gov.set_emergency_state("stop", reason="sự cố nghiêm trọng — dừng toàn bộ", activated_by="quanpt1")
        t2 = orch.submit_plan(_plan("việc mới trong lúc STOP"))
        orch.execute_lifecycle(t2.task_id, dry_run=True)
        assert registry.get_task(t2.task_id).status == TaskStatus.BLOCKED

        # 4. Hủy STOP → hệ thống vận hành bình thường trở lại
        gov.set_emergency_state("normal", reason="đã xử lý xong sự cố", activated_by="quanpt1")
        t3 = orch.submit_plan(_plan("việc mới sau khi hết STOP"))
        orch.execute_lifecycle(t3.task_id, dry_run=True)
        assert registry.get_task(t3.task_id).status in (TaskStatus.COMPLETED, TaskStatus.COMPLETED_VERIFIED)

        # 5. Task OUTCOME_UNKNOWN vẫn chờ owner — hệ thống không tự quyết
        assert registry.get_task(tid).status == TaskStatus.OUTCOME_UNKNOWN
