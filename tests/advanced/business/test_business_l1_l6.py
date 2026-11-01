"""ADVANCED ASSURANCE — P7: 6 kịch bản nghiệp vụ L1–L6 (Phần 11).

Chạy component THẬT (decomposer → orchestrator → registry → state machine → feedback)
trên tmp_path: L1 đọc R0 · L2 soạn R1 DAG · L3 R2 chờ duyệt · L4 DAG chặn khi bước trước
FAILED · L5 R4 fingerprint G-A đúng/sai · L6 học từ trải nghiệm + đo bằng LearningMetrics.
Không LLM, không network, không đụng production. Mức xác minh cao nhất: INTEGRATION_TESTED.
"""
from __future__ import annotations

import pytest

from quan_ai_brain.governance.approval_service import OWNER_ID, ApprovalCardService
from quan_ai_brain.learning.learning_metrics import LearningMetrics
from quan_ai_brain.orchestration.models import TaskStatus
from quan_ai_brain.orchestration.plan_orchestrator import PlanOrchestrator
from quan_ai_brain.orchestration.supervisor import ContinuousAutonomySupervisor as Supervisor
from quan_ai_brain.orchestration.task_feedback import TaskFeedbackRecorder
from quan_ai_brain.orchestration.task_registry import DurableTaskRegistry
from quan_ai_brain.planning.goal_decomposer import GoalDecomposer
from quan_ai_brain.planning.models import TaskPlan, TaskStep
from quan_ai_brain.governance.state_store import GovernanceStateStore


@pytest.fixture()
def ws(tmp_path):
    return tmp_path


@pytest.fixture()
def registry(ws):
    return DurableTaskRegistry(ws / "data" / "tasks.db")


@pytest.fixture()
def orch_ws(ws, registry):
    cards = ApprovalCardService(ws / "data" / "approval_v2.db")
    orch = PlanOrchestrator(task_registry=registry, workspace=ws, approval_cards=cards)
    return orch, cards


def _r0_plan(goal: str) -> TaskPlan:
    step = TaskStep(
        name="read_info", description=f"Đọc và tóm tắt: {goal}", expected_output="Bản tóm tắt",
        risk_level=0, step_id="step-1", sequence=1, verification_method="Owner soát nội dung",
    )
    plan = TaskPlan(goal=goal, steps=[step])
    plan.validate()
    return plan


def _r1_dag_plan(goal: str) -> TaskPlan:
    s1 = TaskStep(name="collect_data", description="Thu thập số liệu", expected_output="Bảng số liệu",
                  risk_level=1, step_id="step-1", sequence=1, verification_method="Đối chiếu nguồn")
    s2 = TaskStep(name="draft_report", description="Soạn báo cáo", expected_output="File báo cáo nháp",
                  risk_level=1, step_id="step-2", sequence=2, dependencies=["step-1"],
                  verification_method="Owner đọc nháp")
    plan = TaskPlan(goal=goal, steps=[s1, s2])
    plan.validate()
    return plan


def _r4_plan(goal: str) -> TaskPlan:
    step = TaskStep(name="system_change", description="Thay đổi cấu hình theo yêu cầu",
                    expected_output="Hệ thống trạng thái mới", risk_level=4, requires_approval=True,
                    step_id="step-1", sequence=1, verification_method="health check")
    plan = TaskPlan(goal=goal, steps=[step])
    plan.validate()
    return plan


# ---------------------------------------------------------------------------
# L1 — Đọc thông tin R0: đọc xong là xong, có evidence, không cần duyệt
# ---------------------------------------------------------------------------
class TestL1ReadOnlyScenario:
    def test_r0_read_completes_with_evidence(self, ws, registry, orch_ws):
        orch, _ = orch_ws
        task = orch.submit_plan(_r0_plan("xem tiến độ báo cáo quý 4 của phòng kinh doanh"))
        outcome = orch.execute_lifecycle(task.task_id, dry_run=True)
        refreshed = registry.get_task(task.task_id)
        # Task Verifier (M2): tất cả step COMPLETED + evidence → COMPLETED_VERIFIED
        assert refreshed.status in (TaskStatus.COMPLETED, TaskStatus.COMPLETED_VERIFIED)
        assert outcome.task_id == task.task_id

    def test_l1_no_waiting_approval_for_r0(self, ws, registry, orch_ws):
        orch, _ = orch_ws
        task = orch.submit_plan(_r0_plan("đọc hộ anh file ghi chú cuộc họp"))
        orch.execute_lifecycle(task.task_id, dry_run=True)
        assert registry.get_task(task.task_id).status != TaskStatus.WAITING_APPROVAL


# ---------------------------------------------------------------------------
# L2 — Viết tổng hợp R1 với DAG 2 bước
# ---------------------------------------------------------------------------
class TestL2DraftWithDag:
    def test_r1_dag_completes_in_order(self, ws, registry, orch_ws):
        orch, _ = orch_ws
        task = orch.submit_plan(_r1_dag_plan("soạn báo cáo tuần gửi anh Quân"))
        orch.execute_lifecycle(task.task_id, dry_run=True)
        steps = registry.list_steps_for_task(task.task_id)
        by_id = {s.step_id: s for s in steps}
        assert by_id["step-1"].status == TaskStatus.COMPLETED
        assert by_id["step-2"].status == TaskStatus.COMPLETED


# ---------------------------------------------------------------------------
# L3 — Việc R2 cần tool ngoài → KHÔNG tự chạy, chờ duyệt
# ---------------------------------------------------------------------------
def _r2_plan(goal: str) -> TaskPlan:
    step = TaskStep(name="send_external", description="Gửi email cho đối tác về lịch họp",
                    expected_output="Email đã gửi", risk_level=2, requires_approval=True,
                    step_id="step-1", sequence=1, verification_method="Xác nhận từ owner")
    plan = TaskPlan(goal=goal, steps=[step])
    plan.validate()
    return plan


class TestL3ExternalActionNeedsApproval:
    def test_r2_without_card_stays_waiting(self, ws, registry, orch_ws):
        orch, _ = orch_ws
        task = orch.submit_plan(_r2_plan("gửi email xác nhận lịch họp cho đối tác"))
        orch.execute_lifecycle(task.task_id, dry_run=True)
        assert registry.get_task(task.task_id).status == TaskStatus.WAITING_APPROVAL


# ---------------------------------------------------------------------------
# L4 — Chuỗi phụ thuộc: bước trước FAILED → bước sau KHÔNG chạy
# ---------------------------------------------------------------------------
def _dag_with_failing_first() -> TaskPlan:
    s1 = TaskStep(name="collect_data", description="Thu thập dữ liệu nguồn", expected_output="Dữ liệu",
                  risk_level=1, step_id="step-1", sequence=1, verification_method="Đối chiếu")
    s2 = TaskStep(name="aggregate", description="Tổng hợp kết quả kiểm kê", expected_output="Báo cáo",
                  risk_level=1, step_id="step-2", sequence=2, dependencies=["step-1"],
                  verification_method="Owner soát")
    plan = TaskPlan(goal="kiểm kê xong mới tổng hợp báo cáo", steps=[s1, s2])
    plan.validate()
    return plan


class TestL4DagBlocksOnFailure:
    def test_failed_dependency_halts_downstream(self, ws, registry, orch_ws):
        orch, _ = orch_ws
        task = orch.submit_plan(_dag_with_failing_first())
        tid = task.task_id
        # buộc bước 1 FAILED đúng thật (mô phỏng nguồn lỗi) rồi chạy lifecycle
        registry.update_task_status(tid, TaskStatus.IN_PROGRESS)
        steps = registry.list_steps_for_task(tid)
        first = [s for s in steps if s.step_id == "step-1"][0]
        registry.update_step_status(first.step_id, TaskStatus.FAILED, error_message="nguồn lỗi")
        orch.execute_lifecycle(tid, dry_run=True)
        steps2 = registry.list_steps_for_task(tid)
        by_id = {s.step_id: s for s in steps2}
        # Bước 1 KHÔNG được lifecycle "chữa lành" — vẫn FAILED sau khi chạy lại
        assert by_id["step-1"].status == TaskStatus.FAILED
        assert by_id["step-2"].status in (TaskStatus.BLOCKED, TaskStatus.PENDING)  # KHÔNG chạy trôi qua lỗi


# ---------------------------------------------------------------------------
# L5 — R4 approval binding (G-A): fingerprint đúng → 1 lần; sai → BLOCKED
# ---------------------------------------------------------------------------
class TestL5ApprovalBindingFingerprint:
    def _approved_card(self, orch, cards, ws, task_id, summary):
        registry2 = DurableTaskRegistry(ws / "data" / "tasks.db")
        steps = registry2.list_steps_for_task(task_id)
        fp = orch.step_action_fingerprint(steps[0], task_id)
        card = cards.create_card(
            task_id=task_id,
            action_summary=summary,
            requested_by="tony",
            scope=[f"task:{task_id}"],
            action_fingerprint=fp,
        )
        cards.approve(card.approval_id, decided_by=OWNER_ID, approval_evidence="a duyệt")
        return card, fp

    def test_correct_fingerprint_consumes_once(self, ws, registry, orch_ws):
        orch, cards = orch_ws
        task = orch.submit_plan(_r4_plan("cấu hình hệ thống theo yêu cầu"))
        card, fp = self._approved_card(orch, cards, ws, task.task_id, "Thay đổi cấu hình hệ thống theo yêu cầu")
        out = cards.consume(card.approval_id, actor="system", action_fingerprint=fp)
        assert out.state == "APPROVED" and out.consumed_at_utc  # atomic consume: consumed_at được set
        with pytest.raises(Exception):
            cards.consume(card.approval_id, actor="system", action_fingerprint=fp)

    def test_wrong_fingerprint_blocked_and_card_intact(self, ws, registry, orch_ws):
        orch, cards = orch_ws
        task = orch.submit_plan(_r4_plan("cấu hình hệ thống khác theo yêu cầu"))
        card, _fp = self._approved_card(orch, cards, ws, task.task_id, "Thay đổi cấu hình hệ thống khác theo yêu cầu")
        wrong_fp = "0" * 64
        with pytest.raises(Exception):
            cards.consume(card.approval_id, actor="system", action_fingerprint=wrong_fp)
        refreshed = cards.get_card(card.approval_id)
        assert refreshed.state == "APPROVED"  # card còn nguyên — fail-closed


# ---------------------------------------------------------------------------
# L6 — Học từ trải nghiệm: terminal → lesson candidate; LearningMetrics đếm đúng
# ---------------------------------------------------------------------------
class TestL6LearnFromExperience:
    def test_terminal_task_creates_candidate_lesson_and_metrics(self, ws, registry):
        fb = TaskFeedbackRecorder(ws / "data" / "feedback.db")
        sup = Supervisor(
            workspace=ws, task_registry=registry,
            governance_store=GovernanceStateStore(ws / "data" / "governance.db", workspace=ws),
            feedback_recorder=fb,
        )
        t = registry.register_task(goal="tổng hợp số liệu báo cáo tháng 10", risk_level="R1")
        registry.update_task_status(t.task_id, TaskStatus.READY)
        sup._current_task = registry.get_task(t.task_id)
        sup._current_plan = None
        from quan_ai_brain.orchestration.models import SupervisorState

        sup._state = SupervisorState.RUNNING_AUTHORIZED_TASK
        sup.step()
        lessons = fb.lessons_for(t.task_id)
        assert lessons and lessons[0]["verification_status"] == "candidate"
        lm = LearningMetrics(ws / "data" / "tasks.db", feedback_db=ws / "data" / "feedback.db")
        rep = lm.learning_report()
        assert rep["lessons"]["candidate"] >= 1
        assert rep["feedback"] >= 1
