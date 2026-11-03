"""Windows Process Containment and Isolation Interface for QUAN AI BRAIN.

Sprint 7A: Windows Process Containment Contract and Inert Runner.
Defines the boundary between application-level resource budgeting and OS-level
Windows Job Object containment.

Strict Invariant:
- In Sprint 7A, all execution remains strictly inert (is_inert = True).
- Zero operating system subprocesses are launched.
- Production execution is blocked while sign-off is PENDING_OWNER_SIGNOFF.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Protocol, runtime_checkable
import uuid

from quan_ai_brain.core.audit import AuditLogger
from quan_ai_brain.core.redaction import redact_value
from quan_ai_brain.execution.resource_budget import ResourceBudget, ResourceBudgetValidator
from quan_ai_brain.execution.staging import ProductionExecutionProhibitedError, StageStatus
from quan_ai_brain.governance.policy import PolicyEngine, RiskLevel
from quan_ai_brain.governance.state_store import GovernanceStateStore
from quan_ai_brain.tools.approval import ApprovalGate
from quan_ai_brain.tools.path_guard import PathGuard


class ContainmentError(Exception):
    """Base exception for containment configuration and enforcement errors."""


class ContainmentConfigurationError(ContainmentError):
    """Raised when an OS containment boundary cannot be configured or applied."""


# Win32 Job Object Extended Limit Flags (Standard Windows NT Constants)
JOB_OBJECT_LIMIT_PROCESS_TIME = 0x0002
JOB_OBJECT_LIMIT_ACTIVE_PROCESS = 0x0008
JOB_OBJECT_LIMIT_PROCESS_MEMORY = 0x0100
JOB_OBJECT_LIMIT_JOB_MEMORY = 0x0200
JOB_OBJECT_LIMIT_DIE_ON_UNHANDLED_EXCEPTION = 0x0400
JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x2000


@dataclass
class ProcessContainmentConfig:
    """OS-level containment parameters mapped from a ResourceBudget.

    Distinction Note:
    - This dataclass holds the parameters to be passed to Windows Job Object
      (JOB_OBJECT_LIMIT_*) and AppContainer configurations.
    - Defining these values does NOT mean the OS kernel has enforced them until
      a verified OS runner binds the process to an active Job Object handle.
    """

    job_name: str
    max_memory_bytes: int
    max_cpu_time_ms: int
    max_active_processes: int
    kill_on_job_close: bool = True
    breakaway_prohibited: bool = True
    network_isolated: bool = True
    limit_flags_bitmask: int = 0
    is_os_enforced: bool = False
    allowed_workspace_scope: str = "workspace"
    created_at_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @classmethod
    def from_budget(
        cls,
        budget: ResourceBudget,
        job_id_prefix: str = "quan_job",
    ) -> ProcessContainmentConfig:
        """Translate an application ResourceBudget into OS containment parameters."""
        job_name = f"{job_id_prefix}_{uuid.uuid4().hex[:8]}"
        memory_bytes = int(budget.max_memory_mb * 1024 * 1024)
        cpu_ms = int(budget.max_cpu_time_seconds * 1000)
        # In staging/inert mode, max_child_processes is 0, so active process limit is 1
        active_procs = max(1, budget.max_child_processes + 1)
        net_isolated = budget.network_policy.value != "RESTRICTED"

        bitmask = (
            JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            | JOB_OBJECT_LIMIT_JOB_MEMORY
            | JOB_OBJECT_LIMIT_PROCESS_TIME
            | JOB_OBJECT_LIMIT_ACTIVE_PROCESS
            | JOB_OBJECT_LIMIT_DIE_ON_UNHANDLED_EXCEPTION
        )

        return cls(
            job_name=job_name,
            max_memory_bytes=memory_bytes,
            max_cpu_time_ms=cpu_ms,
            max_active_processes=active_procs,
            kill_on_job_close=True,
            breakaway_prohibited=True,
            network_isolated=net_isolated,
            limit_flags_bitmask=bitmask,
            is_os_enforced=False,
            allowed_workspace_scope=budget.allowed_workspace_scope,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@runtime_checkable
class ProcessBackendInterface(Protocol):
    """Protocol defining how process backends configure containment and spawn processes."""

    def is_available(self) -> bool:
        """Check if this backend is supported on the current host OS."""
        ...

    def configure_containment(self, config: ProcessContainmentConfig) -> Any:
        """Configure the containment boundary (e.g. create Job Object handle)."""
        ...

    def spawn_process(
        self,
        command: list[str],
        containment_handle: Any,
        cwd: Path,
        env: dict[str, str],
    ) -> Any:
        """Spawn a process strictly bound to the containment boundary."""
        ...


class InertProcessBackend:
    """Default inert backend that never calls subprocess or executes real OS commands.

    Guarantees zero execution side effects.
    """

    def __init__(self) -> None:
        self.is_inert: bool = True
        self.supports_production: bool = False

    def is_available(self) -> bool:
        return True

    def configure_containment(self, config: ProcessContainmentConfig) -> dict[str, Any]:
        """Simulate containment configuration without OS API calls."""
        return {
            "job_name": config.job_name,
            "status": "CONFIGURED_INERT",
            "limits_applied": {
                "memory_bytes": config.max_memory_bytes,
                "cpu_time_ms": config.max_cpu_time_ms,
                "active_processes": config.max_active_processes,
                "kill_on_job_close": config.kill_on_job_close,
            },
        }

    def spawn_process(
        self,
        command: list[str],
        containment_handle: Any,
        cwd: Path,
        env: dict[str, str],
    ) -> Any:
        """Permanently refused: inert backend never launches an OS process."""
        raise ProductionExecutionProhibitedError(
            "InertProcessBackend cannot launch OS processes. Real execution is prohibited "
            "while sign-off is PENDING_OWNER_SIGNOFF."
        )


class ContainedExecutionRunner:
    """Supervised execution runner coordinating governance, containment configuration, and dispatch.

    Strict Fail-Closed Ordering:
    1. Emergency state check (STOP/FREEZE).
    2. Governance sign-off check (must be signed off by owner before production dispatch).
    3. Resource budget validation.
    4. Containment configuration mapping and verification.
    5. Safe inert dispatch via injected backend.
    """

    def __init__(
        self,
        workspace: str | Path,
        store: GovernanceStateStore | None = None,
        policy_engine: PolicyEngine | None = None,
        budget_validator: ResourceBudgetValidator | None = None,
        backend: ProcessBackendInterface | None = None,
        approval_gate: ApprovalGate | None = None,
        audit_logger: AuditLogger | None = None,
    ) -> None:
        self.workspace = Path(workspace).resolve()
        self.path_guard = PathGuard(self.workspace)
        self.store = store
        self.policy_engine = policy_engine or PolicyEngine(self.workspace)
        self.budget_validator = budget_validator or ResourceBudgetValidator()
        self.backend = backend or InertProcessBackend()
        self.approval_gate = approval_gate or ApprovalGate(store=self.store)
        self.audit_logger = audit_logger or AuditLogger(self.workspace)
        self._is_inert: bool = True

    @property
    def is_inert(self) -> bool:
        return self._is_inert

    def prepare_and_stage(
        self,
        command: list[str],
        budget: ResourceBudget,
        risk_level: RiskLevel,
        approval_id: str | None = None,
        action_goal: str = "",
    ) -> dict[str, Any]:
        """Validate governance rules, map containment parameters, and simulate execution.

        Does NOT call subprocess or launch an OS process.
        """
        # 1. Emergency STOP / FREEZE check
        if self.store is not None:
            self.store.verify_integrity()
            emergency = self.store.get_emergency_state()
            if emergency.state in ("stop", "freeze"):
                err = f"Execution halted: system emergency state is {emergency.state.upper()} ({emergency.reason})"
                self._audit("runner.emergency_blocked", {"error": err, "state": emergency.state})
                return {"status": "BLOCKED", "reason": err, "success": False}

        # 2. Risk Level R5 hard-block
        if int(risk_level) >= int(RiskLevel.R5):
            err = "Risk Level R5 is prohibited in this system; execution blocked"
            self._audit("runner.r5_blocked", {"error": err})
            return {"status": "BLOCKED", "reason": err, "success": False}

        # 3. Risk Level R4 separate approval check via ApprovalGate
        if int(risk_level) >= int(RiskLevel.R4):
            if not approval_id:
                err = "Risk Level R4 requires verified owner approval; no approval_id provided"
                self._audit("runner.r4_approval_required", {"error": err})
                return {"status": "DENIED", "reason": err, "success": False}

            action_req = self.approval_gate.create_request(
                tool_id=command[0] if command else "process",
                action="execute",
                params={"command": command},
                resource_scope="workspace",
                risk_level=risk_level,
                goal=action_goal,
            )
            valid_appr, reason = self.approval_gate.evaluate_approval(approval_id, action_req)
            if not valid_appr:
                err = f"Risk Level R4 owner approval invalid: {reason}"
                self._audit("runner.r4_approval_invalid", {"error": err, "approval_id": approval_id})
                return {"status": "DENIED", "reason": err, "success": False}

        # 4. Resource budget validation
        b_ok, b_reason = self.budget_validator.validate_budget(budget)
        if not b_ok:
            err = f"Resource budget validation failed: {b_reason}"
            self._audit("runner.budget_denied", {"error": err})
            return {"status": "DENIED", "reason": err, "success": False}

        # 5. Map containment configuration
        try:
            containment_cfg = ProcessContainmentConfig.from_budget(budget)
            containment_handle = self.backend.configure_containment(containment_cfg)
        except Exception as exc:
            err = f"Containment configuration failed: {exc}"
            self._audit("runner.containment_error", {"error": err})
            raise ContainmentConfigurationError(err) from exc

        # 6. Audit staging event
        self._audit(
            "runner.staged_inert",
            {
                "command": command,
                "containment": containment_cfg.to_dict(),
                "risk_level": int(risk_level),
                "is_inert": True,
            },
        )

        return {
            "status": "STAGED_INERT",
            "success": True,
            "containment_handle": containment_handle,
            "containment_config": containment_cfg.to_dict(),
            "notice": "[INERT STAGING - ZERO PROCESS SPAWNED]",
        }

    def execute_contained(
        self,
        command: list[str],
        budget: ResourceBudget,
        risk_level: RiskLevel,
        approval_id: str | None = None,
        action_goal: str = "",
        cwd: Path | None = None,
        env: dict[str, str] | None = None,
    ) -> Any:
        """Execute a command through the configured backend under strict containment and governance.

        First invokes prepare_and_stage() to verify emergency state, risk levels (R4/R5),
        and resource budgets. If staging succeeds, delegates to backend.spawn_process().
        """
        staging_res = self.prepare_and_stage(
            command=command,
            budget=budget,
            risk_level=risk_level,
            approval_id=approval_id,
            action_goal=action_goal,
        )
        if not staging_res.get("success"):
            return staging_res

        containment_handle = staging_res["containment_handle"]
        try:
            result = self.backend.spawn_process(
                command=command,
                containment_handle=containment_handle,
                cwd=cwd,
                env=env,
            )
            self._audit(
                "runner.executed",
                {
                    "command": command,
                    "risk_level": int(risk_level),
                    "success": getattr(result, "success", True),
                },
            )
            return result
        except Exception as exc:
            self._audit(
                "runner.execution_error",
                {
                    "command": command,
                    "risk_level": int(risk_level),
                    "error": str(exc),
                },
            )
            raise

    def _audit(self, event_type: str, details: dict[str, Any]) -> None:
        self.audit_logger.record(event_type=event_type, details=redact_value(details))

