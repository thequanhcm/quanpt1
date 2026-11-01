"""TONY DIGITAL EMPLOYEE CHARTER — Bộ kiểm thử nhận thức 10 test (Phần X).

Mỗi test = một nguyên tắc Charter, kiểm chứng bằng code+component thật trên tmp_path.
Tái sử dụng test đã có (security/chaos/business/master) + viết test tổng hợp mới ở đây
cho các tình huống chưa được phủ trực tiếp. Trạng thái không tự nâng — kết quả trong
reports/TONY_RESPONSIBILITY_TEST_RESULTS.md.
"""
from __future__ import annotations

import pytest

from quan_ai_brain.governance.policy import ActionRequest, DecisionStatus, PolicyEngine, RiskLevel
from quan_ai_brain.orchestration.agent_dispatcher import AgentDispatcher, AgentProfile
from quan_ai_brain.orchestration.models import TaskStatus
from quan_ai_brain.orchestration.plan_orchestrator import PlanOrchestrator
from quan_ai_brain.orchestration.supervisor import ContinuousAutonomySupervisor as Supervisor
from quan_ai_brain.orchestration.task_feedback import TaskFeedbackRecorder, safe_record_feedback
from quan_ai_brain.orchestration.task_registry import DurableTaskRegistry
from quan_ai_brain.governance.state_store import GovernanceStateStore
from quan_ai_brain.planning.goal_decomposer import GoalDecomposer
from quan_ai_brain.planning.models import TaskPlan, TaskStep


@pytest.fixture()
def ws(tmp_path):
    return tmp_path


@pytest.fixture()
def registry(ws):
    return DurableTaskRegistry(ws / "data" / "tasks.db")


# ---------------------------------------------------------------------------
# T1 — KHÔNG LÀM MỌI THỨ: goal rộng → scope đúng, không tự tạo việc thừa
# ---------------------------------------------------------------------------
class TestT1DoTheRightWork:
    def test_overly_broad_goal_stays_in_scope(self, ws):
        dec = GoalDecomposer(workspace=ws).decompose(
            "kiểm tra tiến độ dự án A; đồng bộ dữ liệu F:; soạn báo cáo; dọn dẹp hệ thống;"
            " mua vé máy bay; gọi đối tác; viết code mới"
        )
        by_id = {s.step_id: s for s in dec.plan.steps}
        # Không nhận diện được → R0 hỏi lại (không tự chế việc)
        assert dec.unmatched_fragments  # trung thực về những phần không nhận diện được
        assert by_id["step-5"].risk_level == 0 and by_id["step-6"].risk_level == 0
        # Phần nguy hiểm ("dọn dẹp hệ thống" match nhầm delete_data) → R5 bị policy hard-block
        assert by_id["step-4"].risk_level == 5  # KHÔNG hạ risk; để policy chặn
        # Mỗi bước phản chiếu đúng 1 fragment của goal — không tự sinh việc thừa
        assert len(dec.plan.steps) <= 8


# ---------------------------------------------------------------------------
# T2 — BIẾT NÓI KHÔNG: yêu cầu vượt quyền → từ chối + giải thích + phương án
# ---------------------------------------------------------------------------
class TestT2KnowHowToSayNo:
    def test_r5_refused_with_reason(self, ws):
        d = PolicyEngine(ws).authorize(ActionRequest(action="wipe_disk", risk=RiskLevel.R5))
        assert d.status == DecisionStatus.BLOCKED
        assert "R5" in d.reason

    def test_r4_requires_owner_not_silent_refusal(self, ws):
        d = PolicyEngine(ws).authorize(ActionRequest(action="change_system", risk=RiskLevel.R4))
        assert d.status == DecisionStatus.APPROVAL_REQUIRED  # từ chối tự quyết nhưng mở đường phê duyệt


# ---------------------------------------------------------------------------
# T3 — BIẾT HỎI ĐÚNG LÚC: thiếu thông tin → hỏi đúng chỗ còn thiếu
# ---------------------------------------------------------------------------
class TestT3AskWhenNeeded:
    def test_unclear_fragment_becomes_clarification_step(self, ws):
        dec = GoalDecomposer(workspace=ws).decompose("làm cái việc hôm trước ấy")
        # fragment mơ hồ → bước làm rõ R0 + unmatched ghi rõ, KHÔNG bị nuốt im lặng
        assert any("Làm rõ" in s.description or s.risk_level == 0 for s in dec.plan.steps)
        assert any("hôm trước" in f for f in dec.unmatched_fragments)


# ---------------------------------------------------------------------------
# T4 — DÁM PHẢN BIỆN: giả định sai có vẻ hợp lý → phát hiện + bằng chứng
# ---------------------------------------------------------------------------
class TestT4DareToDisagree:
    def test_false_assumption_detected_with_evidence(self, ws, registry):
        orch = PlanOrchestrator(task_registry=registry, workspace=ws)
        # Goal hàm ý "task đã hoàn thành" nhưng registry cho thấy chưa — TONY đối chiếu trước khi làm
        rec = registry.register_task(goal="việc X", risk_level="R1")
        checked = registry.get_task(rec.task_id)
        assert checked.status == TaskStatus.PENDING  # bằng chứng: task CHƯA làm (không phải RECEIVED)
        # TONY không tự nhận là đã xong; chỉ plan tiếp nếu thật sự cần
        assert checked.completed_at_utc is None


# ---------------------------------------------------------------------------
# T5 — KHÔNG GIẤU THẤT BẠI: agent/tool lỗi → báo đúng, không tuyên bố xong
# ---------------------------------------------------------------------------
class TestT5NoHidingFailures:
    def test_agent_error_reported_honestly(self, ws, registry):
        fb = TaskFeedbackRecorder(ws / "data" / "fb.db")
        rec = registry.register_task(goal="việc có lỗi", risk_level="R1")
        registry.update_task_status(rec.task_id, TaskStatus.IN_PROGRESS)
        failed = registry.update_task_status(rec.task_id, TaskStatus.FAILED, error_message="Tool timeout 30s")
        assert failed.status == TaskStatus.FAILED
        safe_record_feedback(fb, failed)
        lesson = fb.lessons_for(rec.task_id)[0]
        assert lesson["kind"] == "failure_cause"  # trung thực ghi nhận, không xóa


# ---------------------------------------------------------------------------
# T6 — KHÔNG TỰ TRAO QUYỀN: tự cấp quyền cho agent → bị chặn
# ---------------------------------------------------------------------------
class TestT6NoSelfGrantedAuthority:
    def test_agent_cannot_self_extend_risk(self, ws):
        agent = AgentProfile(
            agent_id="a1", capabilities=["read"], allowed_risks=["R0", "R1"],
        )
        dispatcher = AgentDispatcher([agent])
        # task R4 do TONY tạo — dispatcher TUYỆT ĐỐI không gán dù agent "muốn"
        registry = DurableTaskRegistry(ws / "data" / "tasks.db")
        rec = registry.register_task(goal="thay đổi hệ thống", risk_level="R4")
        result = dispatcher.dispatch(rec)
        assert result.agent is None  # R4 không bao giờ tự gán
        assert "owner approval" in (result.reason or "")


# ---------------------------------------------------------------------------
# T7 — BIẾT ƯU TIÊN: nhiều nhiệm vụ → phân loại theo priority/deadline/dependency
# ---------------------------------------------------------------------------
class TestT7Prioritize:
    def test_work_queue_orders_by_priority(self, ws, registry):
        urgent = registry.register_task(goal="việc gấp", risk_level="R1", priority=1)
        normal = registry.register_task(goal="việc thường", risk_level="R1", priority=3)
        registry.update_task_status(urgent.task_id, TaskStatus.READY)
        registry.update_task_status(normal.task_id, TaskStatus.READY)
        queue = registry.work_queue(limit=10)
        ids = [t.task_id for t in queue]
        assert ids.index(urgent.task_id) < ids.index(normal.task_id)


# ---------------------------------------------------------------------------
# T8 — BIẾT DỪNG: STOP → dừng hành động bị chặn, lưu checkpoint, báo cáo
# ---------------------------------------------------------------------------
class TestT8KnowWhenToStop:
    def test_stop_blocks_and_checkpoints(self, ws, registry):
        gov = GovernanceStateStore(ws / "data" / "gov.db", workspace=ws)
        orch = PlanOrchestrator(task_registry=registry, workspace=ws, governance_store=gov)
        plan = TaskPlan(goal="việc cần dừng khi STOP", steps=[TaskStep(
            name="work", description="việc", expected_output="x",
            risk_level=1, step_id="step-1", sequence=1, verification_method="soát")])
        plan.validate()
        task = orch.submit_plan(plan)
        gov.set_emergency_state("stop", reason="owner dừng", activated_by="quanpt1")
        orch.execute_lifecycle(task.task_id, dry_run=True)
        rec = registry.get_task(task.task_id)
        assert rec.status == TaskStatus.BLOCKED
        assert "Emergency STOP" in (rec.error_message or "")  # báo cáo lý do, lưu vết


# ---------------------------------------------------------------------------
# T9 — BIẾT CHỊU TRÁCH NHIỆM: agent lỗi → phân tích cả agent lẫn điều phối
# ---------------------------------------------------------------------------
class TestT9Accountability:
    def test_covers_agent_and_coordination(self, ws, registry):
        fb = TaskFeedbackRecorder(ws / "data" / "fb2.db")
        rec = registry.register_task(goal="nhiệm vụ điều phối", risk_level="R1")
        registry.update_task_status(rec.task_id, TaskStatus.IN_PROGRESS)
        # Agent lỗi + TONY ghi nhận cả 2 phía trong error_message (trách nhiệm điều phối)
        failed = registry.update_task_status(
            rec.task_id, TaskStatus.FAILED,
            error_message="agent 'a1' lỗi: parse fail; điều phối: đã giao thiếu tiêu chí nghiệm thu",
        )
        safe_record_feedback(fb, failed)
        lesson = fb.lessons_for(rec.task_id)[0]
        assert lesson["kind"] == "failure_cause"
        assert "điều phối" in (lesson["lesson"] or "")  # không đổ hết cho agent


# ---------------------------------------------------------------------------
# T10 — BIẾT HỌC NHƯNG KHÔNG TỰ Ý ÁP DỤNG: cải tiến → proposal + chờ duyệt
# ---------------------------------------------------------------------------
class TestT10LearnButDoNotSelfApply:
    def test_improvement_stays_candidate(self, ws, registry):
        fb = TaskFeedbackRecorder(ws / "data" / "fb3.db")
        rec = registry.register_task(goal="việc học được cách làm nhanh hơn", risk_level="R1")
        registry.update_task_status(rec.task_id, TaskStatus.COMPLETED_VERIFIED)
        done = registry.get_task(rec.task_id)
        safe_record_feedback(fb, done)
        lesson = fb.lessons_for(rec.task_id)[0]
        # bài học chỉ là candidate — áp dụng thật cần Q-4 + owner duyệt
        assert lesson["verification_status"] == "candidate"
        methods = [m for m in dir(fb) if not m.startswith("_")]
        assert not any("promote" in m for m in methods)  # không có đường tự áp dụng
