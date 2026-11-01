"""ADVANCED ASSURANCE — G-C Task State Machine (ADV-003, owner duyệt 02/11).

Bất biến kiểm chứng:
- Terminal → RUNNING bị chặn (COMPLETED*/FAILED/CANCELLED/EXPIRED/REJECTED/OUTCOME_UNKNOWN
  không quay về IN_PROGRESS/PENDING).
- Zombie revive bị chặn: EXPIRED → RUNNING; CANCELLED → IN_PROGRESS.
- Terminal được phép đi tiếp theo nghĩa an toàn:
    COMPLETED* → VERIFYING (chạy verifier), COMPLETED* → PAUSED,
    COMPLETED_UNVERIFIED → VERIFYING (verify lại khi có bằng chứng).
- Mọi transition trái phép → InvalidTaskTransitionError + KHÔNG đổi trạng thái.
- Transition trái phép KHÔNG xóa transition log cũ (audit nguyên vẹn).
- OUTCOME_UNKNOWN (sau restart) chỉ về READY/IN_PROGRESS có chủ đích (owner retry),
  không bao giờ tự động re-run bởi code.
"""
from __future__ import annotations

import pytest

from quan_ai_brain.orchestration.models import TaskStatus
from quan_ai_brain.orchestration.task_registry import DurableTaskRegistry
from quan_ai_brain.orchestration.task_state_machine import (
    TERMINAL_TASK_STATES,
    InvalidTaskTransitionError,
    is_valid_transition,
)


@pytest.fixture()
def registry(tmp_path):
    return DurableTaskRegistry(tmp_path / "tasks_sm.db")


def _to(registry, task_id, status, **kw):
    return registry.update_task_status(task_id, status, **kw)


class TestTerminalCannotRunAgain:
    @pytest.mark.parametrize(
        "terminal",
        [TaskStatus.COMPLETED_VERIFIED, TaskStatus.FAILED, TaskStatus.CANCELLED, TaskStatus.EXPIRED, TaskStatus.OUTCOME_UNKNOWN],
    )
    def test_terminal_to_in_progress_blocked(self, registry, terminal):
        t = registry.register_task("việc kết thúc", risk_level="R1")
        _to(registry, t.task_id, TaskStatus.IN_PROGRESS)
        if terminal == TaskStatus.COMPLETED_VERIFIED:
            _to(registry, t.task_id, TaskStatus.VERIFYING)
            registry.verify_task(t.task_id, evidence_ok=True, note="bằng chứng đầy đủ")
        elif terminal == TaskStatus.OUTCOME_UNKNOWN:
            registry.recover_in_flight_tasks()
        else:
            _to(registry, t.task_id, terminal)
        with pytest.raises(InvalidTaskTransitionError):
            _to(registry, t.task_id, TaskStatus.IN_PROGRESS)
        assert registry.get_task(t.task_id).status == terminal  # không bị đổi

    def test_completed_verified_to_running_zombie_blocked(self, registry):
        t = registry.register_task("xong rồi", risk_level="R1")
        _to(registry, t.task_id, TaskStatus.IN_PROGRESS)
        _to(registry, t.task_id, TaskStatus.VERIFYING)
        _to(registry, t.task_id, TaskStatus.COMPLETED_VERIFIED, evidence_ref="ev:1")
        with pytest.raises(InvalidTaskTransitionError):
            _to(registry, t.task_id, TaskStatus.IN_PROGRESS)
        with pytest.raises(InvalidTaskTransitionError):
            _to(registry, t.task_id, TaskStatus.PENDING)

    def test_blocked_transition_log_preserved_after_rejection(self, registry):
        """Transition trái phép phải để lại hệ thống nguyên vẹn: log cũ đủ, status giữ."""
        t = registry.register_task("audit giữ vết", risk_level="R1")
        _to(registry, t.task_id, TaskStatus.IN_PROGRESS, actor="a1")
        _to(registry, t.task_id, TaskStatus.FAILED, actor="a2", reason="lỗi")
        before = registry.list_transitions(t.task_id)
        with pytest.raises(InvalidTaskTransitionError):
            _to(registry, t.task_id, TaskStatus.IN_PROGRESS, actor="a3")
        after = registry.list_transitions(t.task_id)
        assert len(after) == len(before)  # không có dòng lạ
        assert registry.get_task(t.task_id).status == TaskStatus.FAILED


class TestAllowedSafeContinuations:
    def test_completed_can_still_be_verified(self, registry):
        t = registry.register_task("verify muộn", risk_level="R1")
        _to(registry, t.task_id, TaskStatus.IN_PROGRESS)
        _to(registry, t.task_id, TaskStatus.COMPLETED)
        v = registry.verify_task(t.task_id, evidence_ok=True, note="bằng chứng tới muộn")
        assert v.status == TaskStatus.COMPLETED_VERIFIED

    def test_unverified_can_reverify(self, registry):
        t = registry.register_task("verify lại", risk_level="R1")
        _to(registry, t.task_id, TaskStatus.IN_PROGRESS)
        _to(registry, t.task_id, TaskStatus.VERIFYING)
        _to(registry, t.task_id, TaskStatus.COMPLETED_UNVERIFIED)
        v = registry.verify_task(t.task_id, evidence_ok=True, note="đủ bằng chứng lần 2")
        assert v.status == TaskStatus.COMPLETED_VERIFIED

    def test_failed_can_retry_to_ready(self, registry):
        t = registry.register_task("retry có chủ đích", risk_level="R1")
        _to(registry, t.task_id, TaskStatus.IN_PROGRESS)
        _to(registry, t.task_id, TaskStatus.FAILED, error_message="tạm lỗi")
        _to(registry, t.task_id, TaskStatus.READY, actor="owner", reason="owner yêu cầu thử lại")
        assert registry.get_task(t.task_id).status == TaskStatus.READY

    def test_no_op_same_status_allowed(self, registry):
        """Cùng trạng thái = ghi checkpoint/progress, luôn hợp lệ."""
        t = registry.register_task("no-op", risk_level="R1")
        _to(registry, t.task_id, TaskStatus.IN_PROGRESS)
        rec = _to(registry, t.task_id, TaskStatus.IN_PROGRESS, checkpoint_data={"step": 2})
        assert rec.checkpoint_data.get("step") == 2


class TestStateMachineProperties:
    def test_all_terminal_states_have_entry(self):
        # Mọi trạng thái terminal phải nằm trong bảng transitions (để định nghĩa exit an toàn)
        for s in TERMINAL_TASK_STATES:
            assert s in is_valid_transition.__globals__["VALID_TASK_TRANSITIONS"]

    def test_terminal_never_allows_running(self):
        from quan_ai_brain.orchestration.task_state_machine import VALID_TASK_TRANSITIONS

        for terminal, exits in VALID_TASK_TRANSITIONS.items():
            if terminal in TERMINAL_TASK_STATES:
                assert TaskStatus.IN_PROGRESS not in exits, f"{terminal} → IN_PROGRESS phải bị cấm"
                assert TaskStatus.PENDING not in exits, f"{terminal} → PENDING phải bị cấm"

    def test_supervisor_recovery_path_still_works(self, registry):
        """recover_in_flight_tasks (restart) vẫn hoạt động với state machine."""
        t = registry.register_task("việc dang dở", risk_level="R1")
        _to(registry, t.task_id, TaskStatus.IN_PROGRESS)
        recovered = registry.recover_in_flight_tasks()
        assert t.task_id in [r.task_id for r in recovered]
        assert registry.get_task(t.task_id).status == TaskStatus.OUTCOME_UNKNOWN
        # owner retry hợp lệ từ OUTCOME_UNKNOWN
        _to(registry, t.task_id, TaskStatus.READY, actor="owner", reason="owner duyệt chạy lại")
        assert registry.get_task(t.task_id).status == TaskStatus.READY
