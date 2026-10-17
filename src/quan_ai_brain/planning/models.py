"""Typed plan objects; no autonomous executor in Sprint 1."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TaskStatus(str, Enum):
    DRAFT = "draft"
    READY = "ready"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class TaskStep:
    name: str
    description: str
    expected_output: str
    risk_level: int = 0
    requires_approval: bool = False


@dataclass
class TaskPlan:
    goal: str
    steps: list[TaskStep] = field(default_factory=list)
    status: TaskStatus = TaskStatus.DRAFT
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.goal.strip():
            raise ValueError("Task plan goal must not be empty")
        if not self.steps:
            raise ValueError("Task plan must contain at least one step")
        for index, step in enumerate(self.steps, start=1):
            if not step.name.strip() or not step.expected_output.strip():
                raise ValueError(f"Step {index} must have a name and expected output")
            if step.risk_level not in range(0, 6):
                raise ValueError(f"Step {index} has an invalid risk level")
            if step.risk_level >= 4 and not step.requires_approval:
                raise ValueError(f"Step {index} at risk R4/R5 must indicate approval/blocking")
