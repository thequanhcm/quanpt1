"""Integration tests for PlanOrchestrator and end-to-end task lifecycle.

Validates:
1. DAG Validation -> Risk Assessment -> Durable Registration
2. Anti-replay Idempotency
3. R0-R2 Inert Sandbox Execution with Result Verification
4. R5 Hard-Block Safety Boundary (Immediate Fail-Closed Halt)
5. R4 Approval Gate Wait & Out-of-band Resume
6. Dependency Chain & Blocking
7. Task Cancellation & Interrupted Task Recovery
"""
from __future__ import annotations

from pathlib import Path
import pytest

from quan_ai_brain.contract.models import TaskState
from quan_ai_brain.orchestration.models import AutonomyLevel, TaskStatus
from quan_ai_brain.orchestration.plan_orchestrator import PlanOrchestrator
from quan_ai_brain.orchestration.task_registry import DurableTaskRegistry
from quan_ai_brain.planning.models import TaskPlan, TaskStep
from quan_ai_brain.tools.approval import ApprovalGate, compute_action_fingerprint


@pytest.fixture
def orchestrator(tmp_path: Path) -> PlanOrchestrator:
    db_file = tmp_path / "tasks.db"
    registry = DurableTaskRegistry(db_file, workspace=tmp_path)
    return PlanOrchestrator(task_registry=registry, workspace=tmp_path)


def test_submit_plan_registers_task_and_steps(orchestrator: PlanOrchestrator) -> None:
    plan = TaskPlan(
        goal="Thu thập và phân tích dữ liệu hiệu năng pin",
        steps=[
            TaskStep(
                name="Kiểm tra trạng thái hệ thống",
                description="Đọc thông số RAM và CPU máy chủ",
                expected_output="Thông số sức khỏe hệ thống",
                risk_level=0,
                step_id="step_sys_health",
                sequence=1,
            ),
            TaskStep(
                name="Truy vấn dữ liệu nhật ký",
                description="Đọc tệp nhật ký hiệu năng",
                expected_output="Dữ liệu nhật ký hợp lệ",
                risk_level=1,
                step_id="step_read_logs",
                sequence=2,
                dependencies=("step_sys_health",),
            ),
        ],
    )

    task_rec = orchestrator.submit_plan(plan)

    assert task_rec.task_id.startswith("task_")
    assert task_rec.goal == "Thu thập và phân tích dữ liệu hiệu năng pin"
    assert task_rec.risk_level == "R1"
    assert task_rec.status == TaskStatus.PENDING

    # Verify steps in registry
    steps = orchestrator.task_registry.list_steps_for_task(task_rec.task_id)
    assert len(steps) == 2
    assert steps[0].step_id == "step_sys_health"
    assert steps[0].sequence == 1
    assert steps[0].status == TaskStatus.PENDING
    assert steps[1].step_id == "step_read_logs"
    assert steps[1].dependencies == ["step_sys_health"]


def test_idempotency_prevents_duplicate_plan_submission(orchestrator: PlanOrchestrator) -> None:
    plan = TaskPlan(
        goal="Tác vụ kiểm tra trùng lặp",
        steps=[
            TaskStep(
                name="Bước duy nhất",
                description="Mô tả bước",
                expected_output="Kết quả",
                risk_level=0,
                step_id="step_single",
            )
        ],
    )

    first = orchestrator.submit_plan(plan, idempotency_key="idem_unique_test_key")
    second = orchestrator.submit_plan(plan, idempotency_key="idem_unique_test_key")

    assert first.task_id == second.task_id
    all_tasks = orchestrator.task_registry.list_tasks()
    assert len(all_tasks) == 1


def test_execute_lifecycle_r0_r2_happy_path(orchestrator: PlanOrchestrator) -> None:
    plan = TaskPlan(
        goal="Đọc thông tin cấu hình và tạo báo cáo tóm tắt",
        steps=[
            TaskStep(
                name="Đọc cấu hình hệ thống",
                description="Đọc file cấu hình workspace",
                expected_output="Cấu hình hợp lệ",
                risk_level=0,
                step_id="step_1",
                sequence=1,
            ),
            TaskStep(
                name="Tạo tóm tắt báo cáo",
                description="Tổng hợp dữ liệu đã đọc",
                expected_output="Tóm tắt hoàn chỉnh",
                risk_level=1,
                step_id="step_2",
                sequence=2,
                dependencies=("step_1",),
            ),
        ],
    )

    task_rec = orchestrator.submit_plan(plan)
    outcome = orchestrator.execute_lifecycle(task_rec.task_id, dry_run=True)

    assert outcome.state == TaskState.SUCCEEDED
    assert outcome.is_outcome_certain is True
    assert outcome.is_inert is True
    assert len(outcome.observed_outcomes) == 2

    # Verify database state
    refreshed_task = orchestrator.task_registry.get_task(task_rec.task_id)
    assert refreshed_task is not None
    assert refreshed_task.status == TaskStatus.COMPLETED
    assert refreshed_task.completed_at_utc is not None

    steps = orchestrator.task_registry.list_steps_for_task(task_rec.task_id)
    assert all(s.status == TaskStatus.COMPLETED for s in steps)


def test_execute_lifecycle_r5_hard_block(orchestrator: PlanOrchestrator) -> None:
    plan = TaskPlan(
        goal="Tác vụ nguy hiểm chứa bước xóa hệ thống R5",
        steps=[
            TaskStep(
                name="Kiểm tra môi trường",
                description="Bước R0 an toàn",
                expected_output="OK",
                risk_level=0,
                step_id="step_safe",
                sequence=1,
            ),
            TaskStep(
                name="Xóa ổ đĩa sản xuất hoặc sửa firmware",
                description="Hành động R5 nghiêm cấm",
                expected_output="Bị chặn",
                risk_level=5,
                policy_status="blocked",
                step_id="step_forbidden_r5",
                sequence=2,
                dependencies=("step_safe",),
            ),
        ],
    )

    task_rec = orchestrator.submit_plan(plan)
    outcome = orchestrator.execute_lifecycle(task_rec.task_id)

    # Invariant: Must be immediately BLOCKED
    assert outcome.state == TaskState.BLOCKED
    assert "R5 PROHIBITED" in (outcome.error_message or "")

    refreshed_task = orchestrator.task_registry.get_task(task_rec.task_id)
    assert refreshed_task is not None
    assert refreshed_task.status == TaskStatus.BLOCKED

    steps = orchestrator.task_registry.list_steps_for_task(task_rec.task_id)
    # Step 1 may complete, but Step 2 is BLOCKED
    r5_step = [s for s in steps if s.step_id == "step_forbidden_r5"][0]
    assert r5_step.status == TaskStatus.BLOCKED


def test_execute_lifecycle_r4_approval_gate_wait_and_resume(orchestrator: PlanOrchestrator) -> None:
    from quan_ai_brain.tools.approval import ApprovalStatus
    plan = TaskPlan(
        goal="Tác vụ nâng cấp mã nguồn yêu cầu phê duyệt R4",
        steps=[
            TaskStep(
                name="Soạn thảo diff nâng cấp",
                description="Chuẩn bị bản vá",
                expected_output="Diff hoàn chỉnh",
                risk_level=1,
                step_id="step_diff",
                sequence=1,
            ),
            TaskStep(
                name="Triển khai bản vá mã nguồn",
                description="Thực thi thay đổi mã nguồn R4",
                expected_output="Đã áp dụng",
                risk_level=4,
                requires_approval=True,
                step_id="step_apply_patch",
                sequence=2,
                dependencies=("step_diff",),
            ),
        ],
    )

    task_rec = orchestrator.submit_plan(plan)

    # 1. First execution: should pause at R4 step
    outcome1 = orchestrator.execute_lifecycle(task_rec.task_id)
    assert outcome1.state == TaskState.WAITING_FOR_APPROVAL

    refreshed_task = orchestrator.task_registry.get_task(task_rec.task_id)
    assert refreshed_task is not None
    assert refreshed_task.status == TaskStatus.WAITING_APPROVAL

    # 2. Simulate owner granting approval in ApprovalGate
    pending_requests = [
        r for r in orchestrator.approval_gate._requests.values()
        if r.status == ApprovalStatus.PENDING_OWNER_APPROVAL
    ]
    assert len(pending_requests) >= 1
    target_req = pending_requests[0]
    orchestrator.approval_gate.grant_approval(
        target_req,
        approver="owner:quanpt1",
        notes="Owner verified diff and granted approval",
    )

    # 3. Resume lifecycle execution: should now complete!
    outcome2 = orchestrator.execute_lifecycle(task_rec.task_id)
    assert outcome2.state == TaskState.SUCCEEDED

    final_task = orchestrator.task_registry.get_task(task_rec.task_id)
    assert final_task is not None
    assert final_task.status == TaskStatus.COMPLETED


def test_execute_lifecycle_dependency_failure_blocks_dependent_step(orchestrator: PlanOrchestrator) -> None:
    plan = TaskPlan(
        goal="Tác vụ chuỗi phụ thuộc",
        steps=[
            TaskStep(
                name="Bước lỗi",
                description="Bước sẽ gặp sự cố R5",
                expected_output="Lỗi",
                risk_level=5,
                policy_status="blocked",
                step_id="step_a",
                sequence=1,
            ),
            TaskStep(
                name="Bước phụ thuộc",
                description="Không được phép chạy khi bước trước bị chặn",
                expected_output="Không chạy",
                risk_level=0,
                step_id="step_b",
                sequence=2,
                dependencies=("step_a",),
            ),
        ],
    )

    task_rec = orchestrator.submit_plan(plan)
    outcome = orchestrator.execute_lifecycle(task_rec.task_id)

    assert outcome.state == TaskState.BLOCKED
    steps = orchestrator.task_registry.list_steps_for_task(task_rec.task_id)
    assert steps[0].status == TaskStatus.BLOCKED


def test_cancel_task_aborts_pending_steps(orchestrator: PlanOrchestrator) -> None:
    plan = TaskPlan(
        goal="Tác vụ bị người dùng hủy giữa chừng",
        steps=[
            TaskStep(
                name="Bước 1",
                description="Mô tả 1",
                expected_output="OK",
                risk_level=0,
                step_id="s1",
                sequence=1,
            ),
            TaskStep(
                name="Bước 2",
                description="Mô tả 2",
                expected_output="OK",
                risk_level=0,
                step_id="s2",
                sequence=2,
                dependencies=("s1",),
            ),
        ],
    )

    task_rec = orchestrator.submit_plan(plan)
    cancelled_task = orchestrator.cancel_task(task_rec.task_id, reason="Chủ sở hữu Quanpt1 yêu cầu dừng")

    assert cancelled_task.status == TaskStatus.CANCELLED
    steps = orchestrator.task_registry.list_steps_for_task(task_rec.task_id)
    assert all(s.status == TaskStatus.CANCELLED for s in steps)


def test_persistence_and_recovery_across_restart(tmp_path: Path) -> None:
    db_file = tmp_path / "tasks.db"
    reg1 = DurableTaskRegistry(db_file, workspace=tmp_path)
    orch1 = PlanOrchestrator(reg1, workspace=tmp_path)

    plan = TaskPlan(
        goal="Tác vụ kiểm tra tính bền vững qua khởi động lại",
        steps=[
            TaskStep(
                name="Bước duy nhất",
                description="Mô tả bước",
                expected_output="Kết quả",
                risk_level=0,
                step_id="step_p1",
            )
        ],
    )
    t = orch1.submit_plan(plan)

    # Set task to IN_PROGRESS directly to simulate mid-execution crash
    reg1.update_task_status(t.task_id, TaskStatus.IN_PROGRESS)

    # Simulate process termination & new registry instantiation
    reg2 = DurableTaskRegistry(db_file, workspace=tmp_path)
    orch2 = PlanOrchestrator(reg2, workspace=tmp_path)

    recovered = orch2.recover_tasks()
    assert len(recovered) == 1
    assert recovered[0].task_id == t.task_id
    assert recovered[0].status == TaskStatus.OUTCOME_UNKNOWN

    # Steps are also intact
    steps = reg2.list_steps_for_task(t.task_id)
    assert len(steps) == 1
    assert steps[0].step_id == "step_p1"


def test_plan_orchestrator_honors_emergency_stop_in_governance_db(tmp_path: Path) -> None:
    """Verifies that PlanOrchestrator honors emergency STOP and FREEZE from unified data/governance.db."""
    from quan_ai_brain.governance.state_store import GovernanceStateStore

    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    db_file = data_dir / "tasks.db"
    reg = DurableTaskRegistry(db_file, workspace=tmp_path)
    orch = PlanOrchestrator(reg, workspace=tmp_path)

    assert orch.governance_store.db_path == data_dir / "governance.db"

    plan = TaskPlan(
        goal="Tác vụ kiểm tra cờ dừng khẩn cấp STOP/FREEZE",
        steps=[
            TaskStep(
                name="Bước an toàn",
                description="Mô tả",
                expected_output="OK",
                risk_level=0,
                step_id="step_safe_1",
            )
        ],
    )
    t = orch.submit_plan(plan)

    # 1. Set STOP in governance.db
    orch.governance_store.set_emergency_state("stop", reason="Chủ sở hữu kích hoạt STOP khẩn cấp từ Cockpit")

    outcome = orch.execute_lifecycle(t.task_id)
    assert outcome.state == TaskState.BLOCKED
    assert "STOP" in (outcome.error_message or "")
    assert orch.task_registry.get_task(t.task_id).status == TaskStatus.BLOCKED

    # 2. Reset to normal
    orch.governance_store.set_emergency_state("normal", reason="Chủ sở hữu khôi phục NORMAL")
    orch.task_registry.update_task_status(t.task_id, TaskStatus.PENDING)

    outcome_normal = orch.execute_lifecycle(t.task_id)
    assert outcome_normal.state == TaskState.SUCCEEDED


def test_execute_lifecycle_r4_auto_creates_consultation_ticket_and_resumes_on_ticket_approval(
    orchestrator: PlanOrchestrator,
) -> None:
    """Verifies that an R4 step waiting for approval automatically registers a ConsultationTicket

    and resumes execution once the owner approves the ticket via the Executive Desk.
    """
    from quan_ai_brain.governance.consultation_inbox import ConsultationCategory, TicketStatus

    plan = TaskPlan(
        goal="Tác vụ nâng cấp hệ thống có bước R4 yêu cầu phê duyệt qua Consultation Inbox",
        steps=[
            TaskStep(
                name="Soạn thảo mã nguồn nâng cấp",
                description="Tạo bản vá",
                expected_output="Bản vá sẵn sàng",
                risk_level=1,
                step_id="step_prep",
                sequence=1,
            ),
            TaskStep(
                name="Thực thi bản vá nâng cấp mã nguồn",
                description="Áp dụng thay đổi R4",
                expected_output="Bản vá áp dụng an toàn",
                risk_level=4,
                requires_approval=True,
                step_id="step_r4_patch",
                sequence=2,
                dependencies=("step_prep",),
            ),
        ],
    )

    task_rec = orchestrator.submit_plan(plan)

    # 1. First execution: should pause at R4 and auto-create consultation ticket
    outcome1 = orchestrator.execute_lifecycle(task_rec.task_id)
    assert outcome1.state == TaskState.WAITING_FOR_APPROVAL

    refreshed_task = orchestrator.task_registry.get_task(task_rec.task_id)
    assert refreshed_task is not None
    assert refreshed_task.status == TaskStatus.WAITING_APPROVAL

    # 2. Verify ConsultationTicket was automatically registered
    ticket_id = f"cst_{task_rec.task_id}_step_r4_patch"
    ticket = orchestrator.consultation_store.get_ticket(ticket_id)
    assert ticket is not None
    assert ticket.ticket_id == ticket_id
    assert ticket.category == ConsultationCategory.CODE_PATCH_R4
    assert ticket.status == TicketStatus.PENDING_REVIEW
    assert "step_r4_patch" in ticket.evidence_notes

    # 3. Simulate owner reviewing and approving ticket via Executive Desk
    updated_ticket = orchestrator.consultation_store.respond_ticket(
        ticket_id,
        decision="APPROVE",
        guidance="Phê duyệt bởi Anh Quân (Quanpt1) qua Executive Desk :8766",
    )
    assert updated_ticket.status == TicketStatus.APPROVED

    # 4. Resume execution: orchestrator recognizes the approved consultation ticket and completes!
    outcome2 = orchestrator.execute_lifecycle(task_rec.task_id)
    assert outcome2.state == TaskState.SUCCEEDED

    final_task = orchestrator.task_registry.get_task(task_rec.task_id)
    assert final_task is not None
    assert final_task.status == TaskStatus.COMPLETED

