"""Isolated Executor Staging and Inert Simulation Framework for QUAN AI BRAIN.

Sprint 5: Isolated Executor Staging.
Strict Zero-Execution Guarantee:
- All staged operations are inert simulations only.
- Real production execution, external write APIs, and daemons are hard-disabled.
- Cannot be enabled by a runtime flag.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any
import uuid

from quan_ai_brain.core.audit import AuditLogger
from quan_ai_brain.core.redaction import redact_value
from quan_ai_brain.execution.resource_budget import ResourceBudget, ResourceBudgetValidator
from quan_ai_brain.governance.policy import ActionRequest, DecisionStatus, PolicyEngine, RiskLevel
from quan_ai_brain.governance.state_store import GovernanceStateStore
from quan_ai_brain.tools.approval import ApprovalGate, compute_action_fingerprint
from quan_ai_brain.tools.delegation import DelegationRegistry
from quan_ai_brain.tools.path_guard import PathGuard, PathOutsideWorkspaceError
from quan_ai_brain.tools.sandbox import SystemState


class ProductionExecutionProhibitedError(PermissionError):
    """Raised when any caller attempts to invoke real production execution without approved sign-off."""


class StageStatus(str, Enum):
    STAGED = "staged"
    SIMULATED = "simulated"
    BLOCKED = "blocked"
    DENIED = "denied"


@dataclass
class ExecutionStageRequest:
    """Formal request to stage an action for isolated validation."""

    tool_id: str
    action: str
    params: dict[str, Any]
    risk_level: RiskLevel
    resource_scope: str = "workspace"
    approval_id: str | None = None
    grant_id: str | None = None
    task_id: str = ""
    budget: ResourceBudget | None = None
    stage_id: str = field(default_factory=lambda: f"stage_{uuid.uuid4().hex[:10]}")
    staged_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["params"] = redact_value(self.params)
        data["risk_level"] = int(self.risk_level)
        if self.budget is not None:
            data["budget"] = self.budget.to_dict()
        return data


@dataclass
class ExecutionStageResult:
    """Outcome of an inert staging validation and dry-run simulation."""

    stage_id: str
    success: bool
    status: StageStatus
    simulated_output: Any
    error: str | None = None
    governance_decision: str = ""
    is_inert: bool = True
    notice: str = "[INERT STAGING - ZERO PRODUCTION EXECUTION]"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class IsolatedStagingExecutor:
    """Inert staging executor enforcing governance checks without executing real actions.

    Invariant constraints:
    1. Zero real command execution, zero hardware manipulation.
    2. Strict fail-closed when governance database is unreadable or emergency STOP/FREEZE is active.
    3. Production execution is permanently disabled in this release.
    """

    def __init__(
        self,
        workspace: str | Path,
        policy_engine: PolicyEngine | None = None,
        approval_gate: ApprovalGate | None = None,
        delegation_registry: DelegationRegistry | None = None,
        store: GovernanceStateStore | None = None,
        budget_validator: ResourceBudgetValidator | None = None,
        audit_logger: AuditLogger | None = None,
    ) -> None:
        self.workspace = Path(workspace).resolve()
        self.path_guard = PathGuard(self.workspace)
        self.store = store
        self.policy_engine = policy_engine or PolicyEngine(self.workspace)
        self.approval_gate = approval_gate or ApprovalGate(store=self.store)
        self.delegation_registry = delegation_registry or DelegationRegistry(store=self.store)
        self.budget_validator = budget_validator or ResourceBudgetValidator()
        self.audit_logger = audit_logger or AuditLogger(self.workspace)

        # Invariant security flags: permanent and immutable
        self._is_inert: bool = True
        self._supports_production: bool = False

    @property
    def is_inert(self) -> bool:
        """Confirms that this staging executor only performs inert dry-run simulation."""
        return self._is_inert

    @property
    def supports_production(self) -> bool:
        """Confirms that production execution is strictly unsupported."""
        return self._supports_production

    def stage_and_simulate(self, req: ExecutionStageRequest) -> ExecutionStageResult:
        """Perform end-to-end governance validation and dry-run simulation.

        Does NOT call any real tools, write any files, or execute any OS commands.
        """
        # Step 1: Pre-Execution Emergency State Check
        if self.store is not None:
            # Enforce store integrity
            self.store.verify_integrity()
            emergency = self.store.get_emergency_state()
            if emergency.state in ("stop", "freeze"):
                msg = f"Staging halted: persistent emergency state is {emergency.state.upper()} ({emergency.reason})"
                self._record_audit(req, status=StageStatus.BLOCKED, decision="blocked_emergency", error=msg)
                return ExecutionStageResult(
                    stage_id=req.stage_id,
                    success=False,
                    status=StageStatus.BLOCKED,
                    simulated_output=None,
                    error=msg,
                    governance_decision="blocked_emergency",
                )

        # Step 1.5: Resource Budget Validation Gate
        if req.budget is not None:
            b_ok, b_reason = self.budget_validator.validate_budget(req.budget)
            if not b_ok:
                err = f"Resource budget validation failed: {b_reason}"
                self._record_audit(req, status=StageStatus.DENIED, decision="denied_budget", error=err)
                return ExecutionStageResult(
                    stage_id=req.stage_id,
                    success=False,
                    status=StageStatus.DENIED,
                    simulated_output=None,
                    error=err,
                    governance_decision="denied_budget",
                )

        # Step 2: PolicyEngine Risk Gate
        target_path: str | None = None
        if "file_path" in req.params:
            target_path = str(req.params["file_path"])
        elif "dir_path" in req.params:
            target_path = str(req.params["dir_path"])

        if target_path:
            try:
                self.path_guard.resolve(target_path)
            except (PathOutsideWorkspaceError, ValueError) as exc:
                err = f"PathGuard validation failed: {exc}"
                self._record_audit(req, status=StageStatus.DENIED, decision="denied_path_guard", error=err)
                return ExecutionStageResult(
                    stage_id=req.stage_id,
                    success=False,
                    status=StageStatus.DENIED,
                    simulated_output=None,
                    error=err,
                    governance_decision="denied_path_guard",
                )

        action_req = ActionRequest(action=req.action, risk=req.risk_level, target_path=target_path)
        policy_decision = self.policy_engine.authorize(action_req)

        if policy_decision.status == DecisionStatus.BLOCKED:
            msg = f"PolicyEngine hard-blocked action: {policy_decision.reason}"
            self._record_audit(req, status=StageStatus.BLOCKED, decision="blocked_policy", error=msg)
            return ExecutionStageResult(
                stage_id=req.stage_id,
                success=False,
                status=StageStatus.BLOCKED,
                simulated_output=None,
                error=msg,
                governance_decision="blocked_policy",
            )

        # Step 3: Consent / Approval Evaluation
        governance_decision = "pending_owner_approval"
        if req.approval_id:
            # Verify approval
            fingerprint = compute_action_fingerprint(
                tool_id=req.tool_id,
                action=req.action,
                params=req.params,
                resource_scope=req.resource_scope,
                risk_level=int(req.risk_level),
            )
            dummy_req = self.approval_gate.create_request(
                tool_id=req.tool_id,
                action=req.action,
                params=req.params,
                resource_scope=req.resource_scope,
                risk_level=req.risk_level,
            )
            dummy_req.fingerprint = fingerprint

            valid, reason = self.approval_gate.evaluate_approval(req.approval_id, dummy_req)
            if not valid:
                err = f"Owner approval invalid for staging: {reason}"
                self._record_audit(req, status=StageStatus.DENIED, decision="denied_approval", error=err)
                return ExecutionStageResult(
                    stage_id=req.stage_id,
                    success=False,
                    status=StageStatus.DENIED,
                    simulated_output=None,
                    error=err,
                    governance_decision="denied_approval",
                )
            governance_decision = "allowed_by_approval"
        elif req.grant_id:
            # Check delegation grant
            grant = self.delegation_registry.get_grant(req.grant_id)
            if not grant or grant.status.value != "active":
                err = f"Delegation grant '{req.grant_id}' is not active or unverified"
                self._record_audit(req, status=StageStatus.DENIED, decision="denied_delegation", error=err)
                return ExecutionStageResult(
                    stage_id=req.stage_id,
                    success=False,
                    status=StageStatus.DENIED,
                    simulated_output=None,
                    error=err,
                    governance_decision="denied_delegation",
                )
            if req.budget is not None:
                g_ok, g_reason = self.budget_validator.validate_against_grant(req.budget, grant)
                if not g_ok:
                    err = f"Delegation grant budget exceeded: {g_reason}"
                    self._record_audit(req, status=StageStatus.DENIED, decision="denied_delegation", error=err)
                    return ExecutionStageResult(
                        stage_id=req.stage_id,
                        success=False,
                        status=StageStatus.DENIED,
                        simulated_output=None,
                        error=err,
                        governance_decision="denied_delegation",
                    )
            governance_decision = "allowed_by_delegation"
        else:
            # Check if any delegation grant covers it
            del_ok, del_reason, grant = self.delegation_registry.check_delegation(
                tool_id=req.tool_id,
                action_type=req.action,
                risk_level=req.risk_level,
                resource_path=target_path,
                project_scope="QUAN_AI_BRAIN",
            )
            if del_ok and grant:
                if req.budget is not None:
                    g_ok, g_reason = self.budget_validator.validate_against_grant(req.budget, grant)
                    if not g_ok:
                        err = f"Delegation grant budget exceeded: {g_reason}"
                        self._record_audit(req, status=StageStatus.DENIED, decision="denied_delegation", error=err)
                        return ExecutionStageResult(
                            stage_id=req.stage_id,
                            success=False,
                            status=StageStatus.DENIED,
                            simulated_output=None,
                            error=err,
                            governance_decision="denied_delegation",
                        )
                governance_decision = "allowed_by_delegation"
            else:
                err = f"Action requires explicit owner approval; no valid approval or active delegation ({del_reason})"
                self._record_audit(req, status=StageStatus.DENIED, decision="approval_required", error=err)
                return ExecutionStageResult(
                    stage_id=req.stage_id,
                    success=False,
                    status=StageStatus.DENIED,
                    simulated_output=None,
                    error=err,
                    governance_decision="approval_required",
                )

        # Step 4: Construct Simulated Dry-Run Outcome
        simulated_result = {
            "staged_tool": req.tool_id,
            "staged_action": req.action,
            "sanitized_params": redact_value(req.params),
            "authorized_by": governance_decision,
            "risk_level": req.risk_level.name if hasattr(req.risk_level, "name") else str(req.risk_level),
            "resource_budget": req.budget.to_dict() if req.budget else "DEFAULT_SAFE_BOUNDS",
            "simulated_side_effects": "NONE (Inert Staging)",
            "verification_status": "VALIDATED_FOR_STAGING",
        }

        self._record_audit(req, status=StageStatus.SIMULATED, decision=governance_decision, error=None)

        return ExecutionStageResult(
            stage_id=req.stage_id,
            success=True,
            status=StageStatus.SIMULATED,
            simulated_output=simulated_result,
            error=None,
            governance_decision=governance_decision,
            is_inert=True,
        )

    def execute_production(self, request: Any) -> None:
        """Permanently disabled production entrypoint."""
        raise ProductionExecutionProhibitedError(
            "Production execution is strictly disabled in Sprint 6 (STATUS: PENDING_OWNER_SIGNOFF). "
            "Requires explicit owner sign-off on docs/SPRINT6_DESIGN_SIGNOFF.md."
        )

    def _record_audit(
        self,
        req: ExecutionStageRequest,
        status: StageStatus,
        decision: str,
        error: str | None,
    ) -> None:
        """Audit logging for staging actions."""
        self.audit_logger.record(
            event_type="executor.staging_simulation",
            details={
                "stage_id": req.stage_id,
                "tool_id": req.tool_id,
                "action": req.action,
                "status": status.value,
                "decision": decision,
                "error": error,
                "is_inert": True,
            },
        )
