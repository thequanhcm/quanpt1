"""Data models and contract envelopes for Brain Foundation Contract V1.

Core Principles:
1. Agent claimed identity does NOT grant authority.
2. In inert mode, real execution is prohibited (attempted_actions remains empty).
3. Proposed memory remains quarantined as CANDIDATE.
4. Outcome requires verified evidence; no unverified claims of success.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
import uuid

from quan_ai_brain.core.redaction import redact_text, redact_value
from quan_ai_brain.execution.resource_budget import ResourceBudget
from quan_ai_brain.governance.policy import RiskLevel


class AgentType(str, Enum):
    ASSISTANT = "assistant"
    WORKER = "worker"
    MONITOR = "monitor"
    SPECIALIST = "specialist"
    EXTERNAL_AGENT = "external_agent"
    MOCK = "mock"


class AgentTrustLevel(str, Enum):
    UNTRUSTED = "untrusted"
    PROBATIONARY = "probationary"
    TRUSTED = "trusted"
    SYSTEM = "system"


class TaskState(str, Enum):
    RECEIVED = "received"
    PLANNED = "planned"
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    BLOCKED = "blocked"
    AUTHORIZED = "authorized"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    OUTCOME_UNKNOWN = "outcome_unknown"


@dataclass(frozen=True)
class AgentIdentity:
    """Agent identity specification.

    Invariant: An agent's claimed identity never establishes its authority.
    Only Brain's independent policy evaluation and owner grants confer authority.
    """
    agent_id: str
    agent_type: AgentType | str = AgentType.MOCK
    contract_version: str = "1.0"
    declared_domain: str = "general"
    declared_capabilities: tuple[str, ...] = field(default_factory=tuple)
    trust_level: AgentTrustLevel | str = AgentTrustLevel.UNTRUSTED
    is_verified_by_brain: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": redact_text(self.agent_id),
            "agent_type": self.agent_type.value if isinstance(self.agent_type, AgentType) else str(self.agent_type),
            "contract_version": self.contract_version,
            "declared_domain": redact_text(self.declared_domain),
            "declared_capabilities": list(self.declared_capabilities),
            "trust_level": self.trust_level.value if isinstance(self.trust_level, AgentTrustLevel) else str(self.trust_level),
            "is_verified_by_brain": self.is_verified_by_brain,
        }


@dataclass(frozen=True)
class CapabilityRequest:
    """Explicit request for a specific tool or action capability."""
    capability_name: str
    parameters_schema: dict[str, Any] = field(default_factory=dict)
    intended_scope: str = "workspace"
    risk_level_claimed: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "capability_name": redact_text(self.capability_name),
            "parameters_schema": redact_value(self.parameters_schema),
            "intended_scope": self.intended_scope,
            "risk_level_claimed": self.risk_level_claimed,
        }


@dataclass(frozen=True)
class EvidenceRecord:
    """Auditable evidence supporting a task result or decision."""
    evidence_id: str
    source_type: str
    description: str
    evidence_payload: dict[str, Any]
    collected_at_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    provenance_ref: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "source_type": self.source_type,
            "description": redact_text(self.description),
            "evidence_payload": redact_value(self.evidence_payload),
            "collected_at_utc": self.collected_at_utc,
            "provenance_ref": self.provenance_ref,
        }


@dataclass(frozen=True)
class MemoryProposal:
    """Proposed lesson, procedure, or fact for memory storage.

    Invariant: Stays quarantined as CANDIDATE; never confers authority.
    """
    proposal_id: str
    memory_type: str
    content: str
    source_task_id: str
    evidence_refs: tuple[str, ...] = field(default_factory=tuple)
    confidence_score: float = 0.5
    verification_status: str = "CANDIDATE"
    suggested_project_scope: str = "general"

    def to_dict(self) -> dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "memory_type": self.memory_type,
            "content": redact_text(self.content),
            "source_task_id": self.source_task_id,
            "evidence_refs": list(self.evidence_refs),
            "confidence_score": self.confidence_score,
            "verification_status": self.verification_status,
            "suggested_project_scope": self.suggested_project_scope,
        }


@dataclass
class TaskRequest:
    """Canonical task request envelope for the Brain Control Plane."""
    objective: str
    agent_identity: AgentIdentity
    request_id: str = field(default_factory=lambda: f"req_{uuid.uuid4().hex[:10]}")
    correlation_id: str = field(default_factory=lambda: f"corr_{uuid.uuid4().hex[:10]}")
    success_criteria: str = ""
    task_input: dict[str, Any] = field(default_factory=dict)
    workspace_scope: str = "workspace"
    memory_refs: list[str] = field(default_factory=list)
    requested_capabilities: list[CapabilityRequest] = field(default_factory=list)
    budget_request: ResourceBudget | None = None
    approval_id: str | None = None
    idempotency_key: str = ""
    deadline_utc: str | None = None
    created_at_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "correlation_id": self.correlation_id,
            "objective": redact_text(self.objective),
            "success_criteria": redact_text(self.success_criteria),
            "agent_identity": self.agent_identity.to_dict(),
            "task_input": redact_value(self.task_input),
            "workspace_scope": self.workspace_scope,
            "memory_refs": list(self.memory_refs),
            "requested_capabilities": [c.to_dict() for c in self.requested_capabilities],
            "budget_request": self.budget_request.to_dict() if self.budget_request else None,
            "approval_id": self.approval_id,
            "idempotency_key": self.idempotency_key,
            "deadline_utc": self.deadline_utc,
            "created_at_utc": self.created_at_utc,
        }


@dataclass
class TaskOutcome:
    """Traceable, evidence-backed task outcome."""
    task_id: str
    request_id: str
    correlation_id: str
    state: TaskState
    planned_actions: list[dict[str, Any]] = field(default_factory=list)
    authorized_actions: list[dict[str, Any]] = field(default_factory=list)
    attempted_actions: list[dict[str, Any]] = field(default_factory=list)
    observed_outcomes: list[dict[str, Any]] = field(default_factory=list)
    evidence: list[EvidenceRecord] = field(default_factory=list)
    memory_proposals: list[MemoryProposal] = field(default_factory=list)
    governance_decision: str = ""
    approval_id: str | None = None
    is_outcome_certain: bool = True
    error_message: str | None = None
    is_inert: bool = True
    notice: str = "[INERT FOUNDATION - ZERO PRODUCTION EXECUTION]"
    completed_at_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "request_id": self.request_id,
            "correlation_id": self.correlation_id,
            "state": self.state.value,
            "planned_actions": [redact_value(a) for a in self.planned_actions],
            "authorized_actions": [redact_value(a) for a in self.authorized_actions],
            "attempted_actions": [redact_value(a) for a in self.attempted_actions],
            "observed_outcomes": [redact_value(o) for o in self.observed_outcomes],
            "evidence": [e.to_dict() for e in self.evidence],
            "memory_proposals": [m.to_dict() for m in self.memory_proposals],
            "governance_decision": self.governance_decision,
            "approval_id": self.approval_id,
            "is_outcome_certain": self.is_outcome_certain,
            "error_message": redact_text(self.error_message) if self.error_message else None,
            "is_inert": self.is_inert,
            "notice": self.notice,
            "completed_at_utc": self.completed_at_utc,
        }
