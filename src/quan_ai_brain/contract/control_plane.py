"""Brain Foundation Control Plane implementation.

Executes the vertical slice:
Agent -> TaskRequest -> Policy Assessment -> Planning -> Governance Gate -> Evidence Envelope -> Audit Record
Strictly inert: zero real production execution.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
import uuid

from quan_ai_brain.contract.models import (
    AgentIdentity,
    EvidenceRecord,
    MemoryProposal,
    TaskOutcome,
    TaskRequest,
    TaskState,
)
from quan_ai_brain.core.audit import AuditLogger
from quan_ai_brain.core.redaction import redact_value
from quan_ai_brain.execution.resource_budget import ResourceBudget, ResourceBudgetValidator
from quan_ai_brain.governance.policy import ActionRequest, DecisionStatus, PolicyEngine, RiskLevel
from quan_ai_brain.governance.state_store import GovernanceStateStore
from quan_ai_brain.llm import FallbackMode, LLMProvider
from quan_ai_brain.planning.coordinator import ExecutiveCoordinator
from quan_ai_brain.planning.models import TaskPlan, TaskStatus
from quan_ai_brain.tools.approval import ApprovalGate
from quan_ai_brain.tools.path_guard import PathGuard
from quan_ai_brain.tools.sandbox import SystemState


class BrainControlPlane:
    """Canonical cognitive and governance control plane for QUAN AI BRAIN."""

    def __init__(
        self,
        workspace: str | Path,
        coordinator: ExecutiveCoordinator | None = None,
        policy_engine: PolicyEngine | None = None,
        store: GovernanceStateStore | None = None,
        approval_gate: ApprovalGate | None = None,
        budget_validator: ResourceBudgetValidator | None = None,
        audit_logger: AuditLogger | None = None,
    ) -> None:
        self.workspace = Path(workspace).resolve()
        self.path_guard = PathGuard(self.workspace)
        self.store = store
        self.policy_engine = policy_engine or PolicyEngine(self.workspace)
        self.llm_provider = LLMProvider(fallback_mode=FallbackMode.ALWAYS_MOCK)
        self.coordinator = coordinator or ExecutiveCoordinator(
            self.workspace,
            llm_provider=self.llm_provider,
            policy_engine=self.policy_engine,
        )
        self.approval_gate = approval_gate or ApprovalGate(store=self.store)
        self.budget_validator = budget_validator or ResourceBudgetValidator()
        self.audit_logger = audit_logger or AuditLogger(self.workspace)

    def dispatch_task(self, request: TaskRequest) -> TaskOutcome:
        """Process a task request through the verified governance and planning pipeline.

        Zero-Execution Invariant:
        In this milestone, no subprocesses or external write operations are executed.
        All actions remain planned or inertly authorized.
        """
        task_id = f"task_{uuid.uuid4().hex[:10]}"
        evidence_list: list[EvidenceRecord] = []

        # 1. Emergency state check
        if self.store is not None:
            em_rec = self.store.get_emergency_state()
            if em_rec.state in ("stop", "freeze"):
                outcome = TaskOutcome(
                    task_id=task_id,
                    request_id=request.request_id,
                    correlation_id=request.correlation_id,
                    state=TaskState.BLOCKED,
                    governance_decision=f"blocked_emergency_{em_rec.state}",
                    error_message=f"Brain is in emergency {em_rec.state.upper()} state. Execution halted.",
                    is_outcome_certain=True,
                )
                self._record_audit(request, outcome)
                return outcome

        # 2. Agent identity recording & initial evidence
        evidence_list.append(
            EvidenceRecord(
                evidence_id=f"ev_id_{uuid.uuid4().hex[:8]}",
                source_type="identity_verification",
                description="Agent identity ingested into Control Plane",
                evidence_payload={
                    "agent_id": request.agent_identity.agent_id,
                    "claimed_trust": request.agent_identity.trust_level,
                    "is_verified_by_brain": request.agent_identity.is_verified_by_brain,
                },
                provenance_ref=request.request_id,
            )
        )

        # 3. Budget validation if requested
        if request.budget_request is not None:
            budget_ok, budget_err = self.budget_validator.validate_budget(request.budget_request)
            if not budget_ok:
                outcome = TaskOutcome(
                    task_id=task_id,
                    request_id=request.request_id,
                    correlation_id=request.correlation_id,
                    state=TaskState.BLOCKED,
                    governance_decision="blocked_budget_violation",
                    error_message=f"Requested resource budget rejected: {budget_err}",
                    evidence=evidence_list,
                )
                self._record_audit(request, outcome)
                return outcome

        # 4. Generate structured task plan via ExecutiveCoordinator
        plan: TaskPlan = self.coordinator.plan(
            goal=request.objective,
            project_scope=request.workspace_scope,
            fallback=True,
        )

        planned_actions = [s.to_dict() for s in plan.steps]
        evidence_list.append(
            EvidenceRecord(
                evidence_id=f"ev_plan_{uuid.uuid4().hex[:8]}",
                source_type="plan_generation",
                description="Structured TaskPlan generated by ExecutiveCoordinator",
                evidence_payload={
                    "plan_id": plan.plan_id,
                    "step_count": len(plan.steps),
                    "requires_approval": plan.requires_approval,
                    "blocked": plan.blocked,
                },
                provenance_ref=plan.plan_id,
            )
        )

        # 5. Policy evaluation on plan steps
        highest_risk = 0
        has_blocked_r5 = False
        requires_r4_approval = False

        for step in plan.steps:
            if step.risk_level > highest_risk:
                highest_risk = step.risk_level
            if step.risk_level == 5 or step.policy_status in ("blocked", "deny"):
                has_blocked_r5 = True
            if step.risk_level == 4 or step.requires_approval:
                requires_r4_approval = True

        # Check requested capabilities as well
        for cap in request.requested_capabilities:
            act_req = ActionRequest(
                action=cap.capability_name,
                risk=RiskLevel(cap.risk_level_claimed) if cap.risk_level_claimed in range(6) else RiskLevel.R3,
                target_path=cap.intended_scope,
            )
            dec = self.policy_engine.authorize(act_req)
            if dec.status == DecisionStatus.BLOCKED:
                has_blocked_r5 = True
            elif dec.status == DecisionStatus.APPROVAL_REQUIRED:
                requires_r4_approval = True


        # 6. Resolve final governance state
        if has_blocked_r5 or plan.blocked:
            outcome = TaskOutcome(
                task_id=task_id,
                request_id=request.request_id,
                correlation_id=request.correlation_id,
                state=TaskState.BLOCKED,
                planned_actions=planned_actions,
                governance_decision="blocked_r5_prohibited",
                error_message="Task contains R5 prohibited actions. Hard blocked.",
                evidence=evidence_list,
                is_outcome_certain=True,
            )
            self._record_audit(request, outcome)
            return outcome

        if requires_r4_approval:
            # Check if valid approval is attached
            if not request.approval_id:
                outcome = TaskOutcome(
                    task_id=task_id,
                    request_id=request.request_id,
                    correlation_id=request.correlation_id,
                    state=TaskState.WAITING_FOR_APPROVAL,
                    planned_actions=planned_actions,
                    governance_decision="waiting_owner_approval_r4",
                    error_message="Task requires explicit authenticated owner approval (R4). Approval ID missing.",
                    evidence=evidence_list,
                    is_outcome_certain=True,
                )
                self._record_audit(request, outcome)
                return outcome

            # Verify approval token via ApprovalGate
            app_record = self.approval_gate.get_approval(request.approval_id)
            if not app_record or app_record.consumed or app_record.revoked:
                outcome = TaskOutcome(
                    task_id=task_id,
                    request_id=request.request_id,
                    correlation_id=request.correlation_id,
                    state=TaskState.BLOCKED,
                    planned_actions=planned_actions,
                    governance_decision="blocked_invalid_approval",
                    error_message="Attached approval token is missing, consumed, or revoked.",
                    evidence=evidence_list,
                    is_outcome_certain=True,
                )
                self._record_audit(request, outcome)
                return outcome

            # Approval is valid: authorized
            outcome = TaskOutcome(
                task_id=task_id,
                request_id=request.request_id,
                correlation_id=request.correlation_id,
                state=TaskState.AUTHORIZED,
                planned_actions=planned_actions,
                authorized_actions=planned_actions,
                attempted_actions=[],  # ZERO execution in inert mode
                governance_decision="authorized_by_owner_approval",
                approval_id=request.approval_id,
                evidence=evidence_list,
                is_outcome_certain=True,
            )
            self._record_audit(request, outcome)
            return outcome

        # Default R0-R2: Safe planned state
        outcome = TaskOutcome(
            task_id=task_id,
            request_id=request.request_id,
            correlation_id=request.correlation_id,
            state=TaskState.PLANNED,
            planned_actions=planned_actions,
            authorized_actions=planned_actions if highest_risk <= 2 else [],
            attempted_actions=[],  # ZERO execution in inert mode
            governance_decision="planned_inert_simulation",
            evidence=evidence_list,
            is_outcome_certain=True,
        )
        self._record_audit(request, outcome)
        return outcome

    def _record_audit(self, request: TaskRequest, outcome: TaskOutcome) -> None:
        """Record append-only redacted audit log."""
        self.audit_logger.record(
            event_type="brain_control_plane_dispatch",
            details={
                "request_id": request.request_id,
                "correlation_id": request.correlation_id,
                "agent_id": request.agent_identity.agent_id,
                "task_state": outcome.state.value,
                "governance_decision": outcome.governance_decision,
                "is_inert": outcome.is_inert,
                "evidence_count": len(outcome.evidence),
            },
        )
