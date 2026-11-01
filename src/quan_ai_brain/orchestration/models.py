"""Data models for Continuous Autonomy OS in QUAN AI BRAIN."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class AutonomyLevel(str, Enum):
    """Bounded autonomy levels governed by Policy Engine and Owner Consent."""
    LEVEL_A = "LEVEL_A"  # Read-only health, analysis, candidate creation, safe tests
    LEVEL_B = "LEVEL_B"  # Isolated staging tests (requires test authorization)
    LEVEL_C = "LEVEL_C"  # Working code modifications (requires owner diff approval)
    LEVEL_D = "LEVEL_D"  # Production deployment or external integrations (R4/R5)


class TaskStatus(str, Enum):
    """Durable lifecycle states of tasks in QUAN AI BRAIN.

    DEOM M2 (01/11/2026): mở rộng theo Master Prompt V3.0 §4.3-4.4.
    - Nhóm intake mới: RECEIVED → UNDERSTANDING → ANALYZING → PLANNING → READY
    - Hoàn tất tách 3 mức: COMPLETED_VERIFIED / COMPLETED_PARTIALLY / COMPLETED_UNVERIFIED
      (chỉ TaskVerifier được gán COMPLETED_VERIFIED — có bằng chứng acceptance criteria)
    - Điều hành: VERIFYING, NEEDS_INFORMATION, PAUSED, EXPIRED, REJECTED
    - Nhóm legacy (giữ nguyên cho tương thích): PENDING, IN_PROGRESS, WAITING_APPROVAL,
      APPROVED, COMPLETED, FAILED, CANCELLED, OUTCOME_UNKNOWN, BLOCKED
    """

    # --- legacy (giữ nguyên) ---
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    APPROVED = "APPROVED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    OUTCOME_UNKNOWN = "OUTCOME_UNKNOWN"
    BLOCKED = "BLOCKED"
    # --- DEOM M2: intake pipeline ---
    RECEIVED = "RECEIVED"
    UNDERSTANDING = "UNDERSTANDING"
    ANALYZING = "ANALYZING"
    PLANNING = "PLANNING"
    READY = "READY"
    # --- DEOM M2: điều hành + kết quả có kiểm chứng ---
    VERIFYING = "VERIFYING"
    NEEDS_INFORMATION = "NEEDS_INFORMATION"
    PAUSED = "PAUSED"
    EXPIRED = "EXPIRED"
    REJECTED = "REJECTED"
    COMPLETED_VERIFIED = "COMPLETED_VERIFIED"
    COMPLETED_PARTIALLY = "COMPLETED_PARTIALLY"
    COMPLETED_UNVERIFIED = "COMPLETED_UNVERIFIED"


# Trạng thái coi là "đã kết thúc có kết quả" (dùng cho thống kê + completed_at)
TERMINAL_OK_STATES = (
    TaskStatus.COMPLETED,
    TaskStatus.COMPLETED_VERIFIED,
    TaskStatus.COMPLETED_PARTIALLY,
    TaskStatus.COMPLETED_UNVERIFIED,
)

TERMINAL_STATES = (
    TaskStatus.COMPLETED,
    TaskStatus.COMPLETED_VERIFIED,
    TaskStatus.COMPLETED_PARTIALLY,
    TaskStatus.COMPLETED_UNVERIFIED,
    TaskStatus.CANCELLED,
    TaskStatus.REJECTED,
    TaskStatus.EXPIRED,
)

# Nhóm priority DEOM §7.2 (1=Critical chạy trước, 5=Background)
PRIORITY_CRITICAL = 1
PRIORITY_HIGH = 2
PRIORITY_NORMAL = 3
PRIORITY_LOW = 4
PRIORITY_BACKGROUND = 5

# Nguồn task (source) hợp lệ
VALID_SOURCES = ("owner", "proactive", "learning", "system")


class SupervisorState(str, Enum):
    """Deterministic states for ContinuousAutonomySupervisor."""
    STARTING = "STARTING"
    HEALTH_CHECK = "HEALTH_CHECK"
    READY = "READY"
    IDLE = "IDLE"
    SELECTING_TASK = "SELECTING_TASK"
    PLANNING = "PLANNING"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    RUNNING_AUTHORIZED_TASK = "RUNNING_AUTHORIZED_TASK"
    VERIFYING_RESULT = "VERIFYING_RESULT"
    LEARNING = "LEARNING"
    PREPARING_UPGRADE_PROPOSAL = "PREPARING_UPGRADE_PROPOSAL"
    WAITING_FOR_OWNER = "WAITING_FOR_OWNER"
    RECOVERING = "RECOVERING"
    SAFE_MODE = "SAFE_MODE"
    STOPPED = "STOPPED"
    FAILED = "FAILED"


@dataclass
class TaskRecord:
    """Durable task representation persisted across process restarts.

    DEOM M2: bổ sung priority/deadline/parent/dependencies/required_tools/
    assigned_agents/permission_scope/progress_weight/source theo §4.3.
    """
    task_id: str
    correlation_id: str
    idempotency_key: str
    goal: str
    risk_level: str  # R0 - R5
    autonomy_level: AutonomyLevel
    status: TaskStatus
    created_at_utc: str
    updated_at_utc: str
    acceptance_criteria: list[str] = field(default_factory=list)
    approved_scope: list[str] = field(default_factory=list)
    completed_at_utc: str | None = None
    resource_budget: dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    max_retries: int = 3
    error_message: str | None = None
    evidence_refs: list[str] = field(default_factory=list)
    result_payload: dict[str, Any] = field(default_factory=dict)
    checkpoint_data: dict[str, Any] = field(default_factory=dict)
    # --- DEOM M2 fields (mặc định an toàn, nullable — không phá 578 records cũ) ---
    priority: int = PRIORITY_NORMAL
    deadline_utc: str | None = None
    parent_task_id: str | None = None
    dependencies: list[str] = field(default_factory=list)
    required_tools: list[str] = field(default_factory=list)
    assigned_agents: list[str] = field(default_factory=list)
    permission_scope: list[str] = field(default_factory=list)
    progress_weight: dict[str, Any] = field(default_factory=dict)
    source: str = "owner"

    def to_dict(self) -> dict[str, Any]:
        res = asdict(self)
        res["autonomy_level"] = self.autonomy_level.value
        res["status"] = self.status.value
        return res


@dataclass
class TaskTransition:
    """DEOM §4.4 — transition log bắt buộc: ai đổi trạng thái, khi nào, vì sao, bằng chứng gì."""
    task_id: str
    from_status: str | None
    to_status: str
    actor: str  # 'tony' | 'owner' | 'system' | agent id
    reason: str = ""
    evidence_ref: str = ""
    at_utc: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TaskStepRecord:
    """Durable individual step representation persisted across process restarts."""
    step_id: str
    task_id: str
    sequence: int
    name: str
    description: str
    risk_level: int
    status: TaskStatus
    requires_approval: bool = False
    dependencies: list[str] = field(default_factory=list)
    expected_output: str = ""
    verification_method: str = ""
    result_payload: dict[str, Any] = field(default_factory=dict)
    error_message: str | None = None
    completed_at_utc: str | None = None

    def to_dict(self) -> dict[str, Any]:
        res = asdict(self)
        res["status"] = self.status.value
        return res

