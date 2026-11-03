"""DEOM V4 G-C — Task State Machine (state transitions chặt chẽ).

Nhận xét về các transitions:
- Terminal states (COMPLETED*, FAILED, CANCELLED, REJECTED, EXPIRED, OUTCOME_UNKNOWN)
  là trạng thái cuối — chỉ cho phép transition an toàn nhất định:
    * COMPLETED* → VERIFYING (đi qua verifier để phong VERIFIED/UNVERIFIED)
    * COMPLETED → COMPLETED_PARTIALLY (điều chỉnh mức hoàn thành — review)
    * terminal → PAUSED (owner yêu cầu xem lại — audit đầy đủ)
  KHÔNG cho quay về RUNNING/PENDING (chống re-execute sau khi đã kết luận).
- Cấm zombie revive: BLOCKED/EXPIRED/REJECTED → RUNNING.

Thiết kế tập trung 1 nơi: VALID_TRANSITIONS + enforce trong update_task_status
(điểm duy nhất mọi flow đổi trạng thái). Transition exception được phép qua
cờ force=False mặc định — không flow nào dùng force trong code hiện tại.
"""
from __future__ import annotations

from quan_ai_brain.orchestration.models import TaskStatus

# Nhóm trạng thái
TERMINAL_TASK_STATES: frozenset[TaskStatus] = frozenset(
    {
        TaskStatus.COMPLETED,
        TaskStatus.COMPLETED_VERIFIED,
        TaskStatus.COMPLETED_PARTIALLY,
        TaskStatus.COMPLETED_UNVERIFIED,
        TaskStatus.FAILED,
        TaskStatus.CANCELLED,
        TaskStatus.REJECTED,
        TaskStatus.EXPIRED,
        TaskStatus.OUTCOME_UNKNOWN,
    }
)

# Transitions hợp lệ: từ trạng thái → tập trạng thái được phép đi tới.
# Lưu ý giá trị legacy: task mới mặc định PENDING; NL intake tạo RECEIVED.
# - PENDING/RECEIVED: pipeline hiểu nhiệm vụ (UNDERSTANDING→ANALYZING→PLANNING→READY)
#   hoặc điều hành trực tiếp (APPROVED/IN_PROGRESS/WAITING_APPROVAL/BLOCKED/CANCELLED/EXPIRED/FAILED).
# - OUTCOME_UNKNOWN (sau restart recovery): chỉ owner/verifier quyết — không tự chạy lại.
VALID_TASK_TRANSITIONS: dict[TaskStatus, frozenset[TaskStatus]] = {
    # --- intake pipeline + legacy PENDING ---
    TaskStatus.PENDING: frozenset(
        {
            TaskStatus.UNDERSTANDING, TaskStatus.ANALYZING, TaskStatus.PLANNING,
            TaskStatus.READY, TaskStatus.APPROVED, TaskStatus.IN_PROGRESS,
            TaskStatus.WAITING_APPROVAL, TaskStatus.BLOCKED,
            TaskStatus.CANCELLED, TaskStatus.EXPIRED, TaskStatus.FAILED,
            TaskStatus.PAUSED, TaskStatus.VERIFYING,
            TaskStatus.COMPLETED, TaskStatus.COMPLETED_VERIFIED,
            TaskStatus.COMPLETED_PARTIALLY, TaskStatus.COMPLETED_UNVERIFIED,
        }
    ),
    TaskStatus.RECEIVED: frozenset(
        {
            TaskStatus.UNDERSTANDING, TaskStatus.ANALYZING, TaskStatus.PLANNING,
            TaskStatus.READY, TaskStatus.APPROVED, TaskStatus.IN_PROGRESS,
            TaskStatus.WAITING_APPROVAL, TaskStatus.BLOCKED,
            TaskStatus.CANCELLED, TaskStatus.EXPIRED, TaskStatus.FAILED,
            TaskStatus.PAUSED, TaskStatus.VERIFYING,
            TaskStatus.COMPLETED, TaskStatus.COMPLETED_VERIFIED,
            TaskStatus.COMPLETED_PARTIALLY, TaskStatus.COMPLETED_UNVERIFIED,
        }
    ),
    TaskStatus.UNDERSTANDING: frozenset({TaskStatus.ANALYZING, TaskStatus.PLANNING, TaskStatus.READY, TaskStatus.CANCELLED, TaskStatus.FAILED, TaskStatus.BLOCKED}),
    TaskStatus.ANALYZING: frozenset({TaskStatus.PLANNING, TaskStatus.READY, TaskStatus.NEEDS_INFORMATION, TaskStatus.CANCELLED, TaskStatus.FAILED, TaskStatus.BLOCKED}),
    TaskStatus.PLANNING: frozenset({TaskStatus.READY, TaskStatus.NEEDS_INFORMATION, TaskStatus.WAITING_APPROVAL, TaskStatus.CANCELLED, TaskStatus.FAILED, TaskStatus.BLOCKED}),
    TaskStatus.READY: frozenset({TaskStatus.IN_PROGRESS, TaskStatus.APPROVED, TaskStatus.WAITING_APPROVAL, TaskStatus.BLOCKED, TaskStatus.PAUSED, TaskStatus.CANCELLED, TaskStatus.EXPIRED, TaskStatus.FAILED}),
    # --- điều hành ---
    TaskStatus.APPROVED: frozenset({TaskStatus.IN_PROGRESS, TaskStatus.WAITING_APPROVAL, TaskStatus.BLOCKED, TaskStatus.CANCELLED, TaskStatus.PAUSED, TaskStatus.EXPIRED}),
    TaskStatus.IN_PROGRESS: frozenset(
        {
            TaskStatus.VERIFYING, TaskStatus.COMPLETED, TaskStatus.COMPLETED_PARTIALLY,
            TaskStatus.COMPLETED_UNVERIFIED, TaskStatus.FAILED, TaskStatus.BLOCKED,
            TaskStatus.WAITING_APPROVAL, TaskStatus.PAUSED, TaskStatus.CANCELLED,
            TaskStatus.OUTCOME_UNKNOWN, TaskStatus.EXPIRED,
        }
    ),
    TaskStatus.VERIFYING: frozenset({TaskStatus.COMPLETED_VERIFIED, TaskStatus.COMPLETED_UNVERIFIED, TaskStatus.FAILED, TaskStatus.BLOCKED, TaskStatus.OUTCOME_UNKNOWN, TaskStatus.COMPLETED}),
    TaskStatus.WAITING_APPROVAL: frozenset({TaskStatus.APPROVED, TaskStatus.REJECTED, TaskStatus.BLOCKED, TaskStatus.CANCELLED, TaskStatus.EXPIRED, TaskStatus.IN_PROGRESS, TaskStatus.PAUSED}),
    TaskStatus.NEEDS_INFORMATION: frozenset({TaskStatus.ANALYZING, TaskStatus.PLANNING, TaskStatus.READY, TaskStatus.CANCELLED, TaskStatus.EXPIRED}),
    TaskStatus.BLOCKED: frozenset({TaskStatus.READY, TaskStatus.IN_PROGRESS, TaskStatus.WAITING_APPROVAL, TaskStatus.CANCELLED, TaskStatus.EXPIRED, TaskStatus.FAILED, TaskStatus.PAUSED, TaskStatus.PENDING}),
    TaskStatus.PAUSED: frozenset({TaskStatus.READY, TaskStatus.IN_PROGRESS, TaskStatus.WAITING_APPROVAL, TaskStatus.BLOCKED, TaskStatus.CANCELLED, TaskStatus.EXPIRED}),
    # --- terminal (hạn chế tối đa) ---
    TaskStatus.COMPLETED: frozenset({TaskStatus.VERIFYING, TaskStatus.COMPLETED_PARTIALLY, TaskStatus.PAUSED}),
    TaskStatus.COMPLETED_VERIFIED: frozenset({TaskStatus.PAUSED}),  # kết luận cuối — không đụng
    TaskStatus.COMPLETED_PARTIALLY: frozenset({TaskStatus.VERIFYING, TaskStatus.PAUSED}),
    TaskStatus.COMPLETED_UNVERIFIED: frozenset({TaskStatus.VERIFYING, TaskStatus.PAUSED}),
    TaskStatus.FAILED: frozenset({TaskStatus.READY, TaskStatus.PAUSED}),  # retry: về READY có chủ đích
    TaskStatus.CANCELLED: frozenset({TaskStatus.PAUSED}),
    TaskStatus.REJECTED: frozenset({TaskStatus.PAUSED}),
    TaskStatus.EXPIRED: frozenset({TaskStatus.PAUSED}),
    TaskStatus.OUTCOME_UNKNOWN: frozenset({TaskStatus.READY, TaskStatus.PAUSED, TaskStatus.CANCELLED}),
}


class InvalidTaskTransitionError(Exception):
    """Transition trái phép trong state machine (fail-closed, có vết audit)."""


def is_valid_transition(current: TaskStatus, target: TaskStatus) -> bool:
    if current == target:
        return True  # no-op (ghi lại checkpoint/progress) luôn hợp lệ
    return target in VALID_TASK_TRANSITIONS.get(current, frozenset())
