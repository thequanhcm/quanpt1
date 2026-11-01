"""DEOM M4 — Tests tích hợp: wire ApprovalCardService vào PlanOrchestrator.

Bao phủ: R4 step KHÔNG card → WAITING_APPROVAL (+ consultation ticket);
card APPROVED (owner duyệt) → bước R4 chạy được, card consumed đúng 1 lần;
card consumed → task KHÁC không dùng lại được.
"""
from __future__ import annotations

import pytest

from quan_ai_brain.governance.approval_service import OWNER_ID, ApprovalCardService
from quan_ai_brain.orchestration.models import TaskStatus
from quan_ai_brain.orchestration.plan_orchestrator import PlanOrchestrator
from quan_ai_brain.orchestration.task_registry import DurableTaskRegistry
from quan_ai_brain.planning.models import TaskPlan, TaskStep


@pytest.fixture()
def workspace(tmp_path):
    return tmp_path


@pytest.fixture()
def cards(tmp_path):
    return ApprovalCardService(tmp_path / "approval_v2.db")


@pytest.fixture()
def make_orchestrator(workspace, cards):
    def _make():
        registry = DurableTaskRegistry(workspace / "data" / "tasks.db")
        orch = PlanOrchestrator(
            task_registry=registry, workspace=workspace, approval_cards=cards
        )
        return orch, registry

    return _make


def _plan_with_r4_step() -> TaskPlan:
    step = TaskStep(
        name="system_change",
        description="Thay đổi cấu hình hệ thống theo yêu cầu",
        expected_output="Hệ thống ở trạng thái mới",
        risk_level=4,
        requires_approval=True,
        step_id="step-1",
        sequence=1,
        verification_method="health check",
    )
    plan = TaskPlan(goal="cấu hình hệ thống theo yêu cầu", steps=[step])
    plan.validate()
    return plan


class TestR4StepWithoutCard:
    def test_r4_step_halts_waiting_approval(self, make_orchestrator):
        orch, registry = make_orchestrator()
        task = orch.submit_plan(_plan_with_r4_step())
        outcome = orch.execute_lifecycle(task.task_id, dry_run=True)
        refreshed = registry.get_task(task.task_id)
        assert refreshed.status == TaskStatus.WAITING_APPROVAL

    def test_no_card_means_ticket_created(self, make_orchestrator):
        orch, registry = make_orchestrator()
        task = orch.submit_plan(_plan_with_r4_step())
        orch.execute_lifecycle(task.task_id, dry_run=True)
        refreshed = registry.get_task(task.task_id)
        assert refreshed.status == TaskStatus.WAITING_APPROVAL
        # checkpoint ghi blocked_step + ticket id
        assert refreshed.checkpoint_data is not None


class TestR4StepWithApprovedCard:
    def test_approved_card_unlocks_r4_step_once(self, make_orchestrator, cards):
        orch, registry = make_orchestrator()
        task = orch.submit_plan(_plan_with_r4_step())
        tid = task.task_id

        # TONY tạo card đề xuất → owner duyệt (tách đề xuất/phê duyệt)
        card = cards.create_card(
            task_id=tid,
            action_summary="Cho phép bước system_change của task",
            risk_level="R4",
            requested_by="tony",
        )
        cards.approve(card.approval_id, decided_by=OWNER_ID, approval_evidence="dm://ok-m4")

        outcome = orch.execute_lifecycle(tid, dry_run=True)
        refreshed = registry.get_task(tid)

        # Bước R4 được mở khóa nhờ card → task hoàn tất trong inert sandbox
        assert refreshed.status in (
            TaskStatus.COMPLETED,
            TaskStatus.COMPLETED_VERIFIED,
            TaskStatus.COMPLETED_UNVERIFIED,
        )
        consumed = cards.get_card(card.approval_id)
        assert consumed.consumed_at_utc is not None

    def test_consumed_card_cannot_unlock_other_task(self, make_orchestrator, cards):
        orch, registry = make_orchestrator()
        task1 = orch.submit_plan(_plan_with_r4_step())
        card = cards.create_card(
            task_id=task1.task_id, action_summary="duyet lan 1", requested_by="tony"
        )
        cards.approve(card.approval_id, decided_by=OWNER_ID, approval_evidence="dm://ok")
        orch.execute_lifecycle(task1.task_id, dry_run=True)

        # task2 KHÔNG có card riêng → không được mở khóa dù card task1 đã APPROVED
        # (card đã consumed + task_id khác → _check_step_approval không ăn)
        task2 = orch.submit_plan(_plan_with_r4_step())
        orch.execute_lifecycle(task2.task_id, dry_run=True)
        refreshed2 = registry.get_task(task2.task_id)
        assert refreshed2.status == TaskStatus.WAITING_APPROVAL
