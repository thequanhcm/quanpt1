"""Operational Playbook Specification for Repeatable Verified Procedures."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from quan_ai_brain.governance.policy import RiskLevel
from quan_ai_brain.integration.profile import KnowledgeLevel


@dataclass
class PlaybookStep:
    """Discrete step within an Operational Playbook."""
    step_num: int
    name: str
    target_system: str
    operation_id: str
    params: dict[str, Any]
    checkpoint: str
    expected_result: str
    verification_query: dict[str, Any] = field(default_factory=dict)
    rollback_step: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class OperationalPlaybook:
    """13-attribute Standard Operational Playbook defined in Master Prompt V6 Section V."""
    playbook_id: str
    goal: str
    prerequisites: list[str]
    required_permissions: list[str]
    input_schema: dict[str, Any]
    steps: list[PlaybookStep]
    checkpoints: list[str]
    expected_output: str
    failure_conditions: list[str]
    recovery_procedure: str
    verification_method: str
    risk_level: RiskLevel
    required_approval_level: str  # "NONE", "DELEGATED", "OWNER_APPROVAL"
    version: str
    source_documentation: str
    knowledge_level: KnowledgeLevel = KnowledgeLevel.OBSERVED
    created_at_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self) -> None:
        if not self.playbook_id or not self.playbook_id.strip():
            raise ValueError("playbook_id must not be empty")
        if not self.goal or not self.goal.strip():
            raise ValueError("goal must not be empty")
        if not isinstance(self.risk_level, RiskLevel):
            raise TypeError("risk_level must be an instance of RiskLevel IntEnum")
        if not isinstance(self.knowledge_level, KnowledgeLevel):
            raise TypeError("knowledge_level must be an instance of KnowledgeLevel")

    def is_executable_autonomously(self) -> bool:
        """Only VERIFIED playbooks with risk <= R2 can be executed under delegated autonomy."""
        return (
            self.knowledge_level == KnowledgeLevel.VERIFIED
            and int(self.risk_level) <= int(RiskLevel.R2)
            and self.required_approval_level != "OWNER_APPROVAL"
        )

    def to_dict(self) -> dict[str, Any]:
        res = asdict(self)
        res["risk_level"] = int(self.risk_level)
        res["risk_name"] = self.risk_level.name
        res["knowledge_level"] = self.knowledge_level.value
        return res
