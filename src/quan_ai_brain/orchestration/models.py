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
    """Durable lifecycle states of tasks in QUAN AI BRAIN."""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    APPROVED = "APPROVED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    OUTCOME_UNKNOWN = "OUTCOME_UNKNOWN"
    BLOCKED = "BLOCKED"


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
    """Durable task representation persisted across process restarts."""
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

    def to_dict(self) -> dict[str, Any]:
        res = asdict(self)
        res["autonomy_level"] = self.autonomy_level.value
        res["status"] = self.status.value
        return res


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

