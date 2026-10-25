"""Safe Tool Sandbox for QUAN AI BRAIN.

Executes strictly bounded, audited tools (R0-R2) with:
1. Owner Consent First principle (default requires explicit approval or active delegation grant).
2. Delegated Autonomy verification (R0-R2 bounded grants).
3. Independent PolicyEngine authorization (R5 hard-blocked, R4 approval required).
4. PathGuard workspace confinement and sensitive file protection.
5. Emergency STOP/FREEZE controls.
6. Append-only redacted audit logging.
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from quan_ai_brain.core.audit import AuditLogger
from quan_ai_brain.core.redaction import redact_value
from quan_ai_brain.governance.policy import ActionRequest, DecisionStatus, PolicyEngine, RiskLevel
from quan_ai_brain.tools.approval import (
    ApprovalGate,
    ApprovalRequest,
    ApprovalStatus,
    compute_action_fingerprint,
)
from quan_ai_brain.tools.delegation import DelegationRegistry
from quan_ai_brain.tools.path_guard import PathGuard, PathOutsideWorkspaceError
from quan_ai_brain.tools.registry import ToolDefinition, ToolRegistry


class SystemState(str, Enum):
    NORMAL = "normal"
    STOP = "stop"
    FREEZE = "freeze"


_SENSITIVE_PATTERNS = (
    ".env",
    "id_rsa",
    ".pem",
    ".key",
    ".pfx",
    "credentials.json",
    "token.json",
    ".git",
    ".sqlite",
    ".db",
)


def _is_sensitive_path(path_str: str) -> bool:
    """Check if a path targets sensitive credential, repo internals, or raw database files."""
    normalized = path_str.replace("\\", "/").lower()
    parts = normalized.split("/")
    for part in parts:
        if part.startswith(".env") or part == ".git":
            return True
        for sens in (".pem", ".key", ".pfx", "id_rsa", "credentials.json", "token.json", ".sqlite", ".db"):
            if part.endswith(sens) or sens in part:
                return True
    return False


@dataclass
class ExecutionResult:
    """Standardized outcome of a sandboxed tool invocation."""

    success: bool
    output: Any
    error: str | None
    risk_level: RiskLevel
    tool_id: str
    action: str
    governance_decision: str
    approval_id: str | None = None
    grant_id: str | None = None
    audit_recorded: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class SafeToolSandbox:
    """Coordinates tool execution with strict multi-layer governance gates."""

    def __init__(
        self,
        workspace: str | Path,
        registry: ToolRegistry | None = None,
        policy_engine: PolicyEngine | None = None,
        approval_gate: ApprovalGate | None = None,
        delegation_registry: DelegationRegistry | None = None,
        audit_logger: AuditLogger | None = None,
        store: Any | None = None,
    ) -> None:
        self.workspace = Path(workspace).resolve()
        self.path_guard = PathGuard(self.workspace)
        self.store = store

        if self.store is not None:
            # Verify database integrity on startup - fail closed if corrupted
            self.store.verify_integrity()

        self.registry = registry or ToolRegistry()
        self.policy_engine = policy_engine or PolicyEngine(self.workspace)
        self.approval_gate = approval_gate or ApprovalGate(store=self.store)
        self.delegation_registry = delegation_registry or DelegationRegistry(store=self.store)
        self.audit_logger = audit_logger or AuditLogger(self.workspace)
        self._system_state: SystemState = SystemState.NORMAL

        # Sync initial emergency state from persistent store if available
        if self.store is not None:
            rec = self.store.get_emergency_state()
            if rec.state == "stop":
                self._system_state = SystemState.STOP
            elif rec.state == "freeze":
                self._system_state = SystemState.FREEZE
            else:
                self._system_state = SystemState.NORMAL

        # Register standard default safe tools
        self.register_default_tools()

    def set_system_state(
        self,
        state: SystemState,
        reason: str = "",
        activated_by: str = "OWNER",
    ) -> None:
        self._system_state = state
        if self.store is not None:
            self.store.set_emergency_state(
                state=state.value,
                reason=reason,
                activated_by=activated_by,
            )

    def get_system_state(self) -> SystemState:
        if self.store is not None:
            rec = self.store.get_emergency_state()
            if rec.state == "stop":
                return SystemState.STOP
            elif rec.state == "freeze":
                return SystemState.FREEZE
            return SystemState.NORMAL
        return self._system_state

    # -------------------------------------------------------------------------
    # Built-in Tool Handlers
    # -------------------------------------------------------------------------

    def _handler_file_read(self, params: dict[str, Any]) -> dict[str, Any]:
        file_path = params["file_path"]
        resolved = self.path_guard.resolve(file_path)
        if not resolved.exists():
            raise FileNotFoundError(f"File '{file_path}' does not exist")
        if not resolved.is_file():
            raise ValueError(f"Path '{file_path}' is not a regular file")

        # Cap max read size to 100KB for safety
        max_bytes = 100 * 1024
        size = resolved.stat().st_size
        if size > max_bytes:
            raise ValueError(f"File size ({size} bytes) exceeds sandbox safe read limit of {max_bytes} bytes")

        content = resolved.read_text(encoding="utf-8", errors="replace")
        rel_path = str(resolved.relative_to(self.workspace)).replace("\\", "/")
        return {"file_path": rel_path, "size_bytes": size, "content": content}

    def _handler_dir_list(self, params: dict[str, Any]) -> dict[str, Any]:
        dir_path = params.get("dir_path", ".")
        resolved = self.path_guard.resolve(dir_path)
        if not resolved.exists():
            raise FileNotFoundError(f"Directory '{dir_path}' does not exist")
        if not resolved.is_dir():
            raise ValueError(f"Path '{dir_path}' is not a directory")

        entries = []
        for item in sorted(resolved.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
            if item.name == ".git":
                continue
            entries.append({
                "name": item.name,
                "is_dir": item.is_dir(),
                "size_bytes": item.stat().st_size if item.is_file() else None,
            })

        rel_path = str(resolved.relative_to(self.workspace)).replace("\\", "/")
        return {"dir_path": rel_path or ".", "entries": entries, "count": len(entries)}

    def _handler_git_status(self, params: dict[str, Any]) -> dict[str, Any]:
        short = params.get("short", True)
        cmd = ["git", "status"]
        if short:
            cmd.append("--short")
        try:
            res = subprocess.run(
                cmd,
                cwd=str(self.workspace),
                capture_output=True,
                text=True,
                timeout=10,
                check=True,
            )
            stdout = res.stdout.strip()
            return {"clean": len(stdout) == 0, "status_text": stdout}
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as exc:
            raise RuntimeError(f"Git status query failed: {exc}")

    def _handler_memory_read(self, params: dict[str, Any]) -> dict[str, Any]:
        query = params.get("query")
        m_type = params.get("memory_type")
        limit = min(int(params.get("limit", 10)), 50)
        db_path = self.workspace / "data" / "brain.db"
        if not db_path.exists():
            return {"count": 0, "memories": [], "notice": "Memory database file does not exist yet"}

        from quan_ai_brain.memory.sqlite_store import MemoryStore

        store = MemoryStore(db_path=db_path, workspace=self.workspace)
        records = store.search_memories(query=query, memory_type=m_type, limit=limit)
        return {
            "count": len(records),
            "memories": [r.to_dict() for r in records],
        }

    def _handler_system_health(self, params: dict[str, Any]) -> dict[str, Any]:
        db_exists = (self.workspace / "data" / "brain.db").exists()
        audit_exists = (self.workspace / "logs" / "audit.jsonl").exists()
        git_exists = (self.workspace / ".git").is_dir()
        return {
            "workspace": str(self.workspace).replace("\\", "/"),
            "healthy": True,
            "components": {
                "memory_database": "ready" if db_exists else "not_created",
                "audit_logger": "ready" if audit_exists else "initialized",
                "git_repository": "present" if git_exists else "absent",
                "system_state": self._system_state.value,
            },
        }

    def _handler_plan_validate(self, params: dict[str, Any]) -> dict[str, Any]:
        from quan_ai_brain.planning.models import StepStatus, TaskPlan, TaskStatus, TaskStep

        plan_data = params.get("plan")
        if isinstance(plan_data, TaskPlan):
            plan = plan_data
        elif isinstance(plan_data, dict):
            # Reconstruct and validate

            steps = []
            for s in plan_data.get("steps", []):
                steps.append(
                    TaskStep(
                        name=s.get("name", s.get("step_id", "unnamed_step")),
                        step_id=s.get("step_id", ""),
                        description=s.get("description", ""),
                        risk_level=RiskLevel(s.get("risk_level", 0)),
                        preconditions=s.get("preconditions", []),
                        expected_output=s.get("expected_output", ""),
                        verification_method=s.get("verification_method", ""),
                        dependencies=s.get("dependencies", []),
                        requires_approval=s.get("requires_approval", False),
                        status=StepStatus(s.get("status", "proposed")),
                    )
                )
            plan = TaskPlan(
                plan_id=plan_data.get("plan_id", "test-plan"),
                goal=plan_data.get("goal", ""),
                summary=plan_data.get("summary", ""),
                steps=steps,
                status=TaskStatus.DRAFT if plan_data.get("status") in (None, "draft", "proposed") else TaskStatus(plan_data["status"]),
            )
        else:
            raise ValueError("Parameter 'plan' must be a TaskPlan or dictionary representation")

        plan.validate()
        return {
            "valid": True,
            "plan_id": plan.plan_id,
            "steps_count": len(plan.steps),
            "requires_approval": plan.requires_approval,
            "blocked": plan.blocked,
        }

    def _handler_file_write_new(self, params: dict[str, Any]) -> dict[str, Any]:
        file_path = params["file_path"]
        content = params["content"]

        resolved = self.path_guard.resolve(file_path)

        # Non-negotiable constraint: Overwriting is forbidden by default in Sprint 3B
        if resolved.exists():
            raise FileExistsError(
                f"Target file '{file_path}' already exists; overwriting is strictly prohibited in Sprint 3B"
            )

        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(content, encoding="utf-8")
        rel_path = str(resolved.relative_to(self.workspace)).replace("\\", "/")
        return {
            "file_path": rel_path,
            "bytes_written": len(content.encode("utf-8")),
            "created": True,
        }

    def register_default_tools(self) -> None:
        """Register the safe baseline toolset (R0-R2)."""
        tools = [
            ToolDefinition(
                tool_id="file_read",
                description="Read UTF-8 text from an allowed workspace file",
                action_type="read",
                risk_level=RiskLevel.R0,
                handler=self._handler_file_read,
                input_schema={"required": ["file_path"], "types": {"file_path": str}},
                allowed_resource_scope="workspace",
                side_effects=False,
                supports_dry_run=True,
            ),
            ToolDefinition(
                tool_id="dir_list",
                description="List contents of a directory in the workspace",
                action_type="read",
                risk_level=RiskLevel.R0,
                handler=self._handler_dir_list,
                input_schema={"types": {"dir_path": str}},
                allowed_resource_scope="workspace",
                side_effects=False,
                supports_dry_run=True,
            ),
            ToolDefinition(
                tool_id="git_status",
                description="Check read-only git status of workspace",
                action_type="read",
                risk_level=RiskLevel.R0,
                handler=self._handler_git_status,
                allowed_resource_scope="workspace",
                side_effects=False,
                supports_dry_run=True,
            ),
            ToolDefinition(
                tool_id="memory_read",
                description="Search and inspect long-term memory records (read-only)",
                action_type="read",
                risk_level=RiskLevel.R0,
                handler=self._handler_memory_read,
                allowed_resource_scope="workspace",
                side_effects=False,
                supports_dry_run=True,
            ),
            ToolDefinition(
                tool_id="system_health",
                description="Inspect health status of workspace components",
                action_type="read",
                risk_level=RiskLevel.R0,
                handler=self._handler_system_health,
                allowed_resource_scope="workspace",
                side_effects=False,
                supports_dry_run=True,
            ),
            ToolDefinition(
                tool_id="plan_validate",
                description="Validate TaskPlan structure, DAG dependencies, and governance requirements in memory",
                action_type="analysis",
                risk_level=RiskLevel.R1,
                handler=self._handler_plan_validate,
                input_schema={"required": ["plan"]},
                allowed_resource_scope="workspace",
                side_effects=False,
                supports_dry_run=True,
            ),
            ToolDefinition(
                tool_id="file_write_new",
                description="Write text to a new file in workspace (overwriting existing files is prohibited)",
                action_type="write",
                risk_level=RiskLevel.R2,
                handler=self._handler_file_write_new,
                input_schema={"required": ["file_path", "content"], "types": {"file_path": str, "content": str}},
                allowed_resource_scope="workspace",
                side_effects=True,
                supports_dry_run=True,
            ),
        ]

        for t in tools:
            if not self.registry.has_tool(t.tool_id):
                self.registry.register(t)

    # -------------------------------------------------------------------------
    # Execution Pipeline
    # -------------------------------------------------------------------------

    def execute(
        self,
        tool_id: str,
        params: dict[str, Any],
        approval_id: str | None = None,
        goal: str = "",
        dry_run: bool = False,
    ) -> ExecutionResult:
        """Run tool action through multi-layer verification and governance."""
        # Step 1: Check if tool is registered
        tool = self.registry.get(tool_id)
        if not tool:
            self._audit(
                event_type="sandbox.tool_rejected",
                tool_id=tool_id,
                risk=RiskLevel.R5,
                decision="blocked",
                success=False,
                error=f"Tool '{tool_id}' is not registered",
            )
            return ExecutionResult(
                success=False,
                output=None,
                error=f"Tool '{tool_id}' is not registered in ToolRegistry",
                risk_level=RiskLevel.R5,
                tool_id=tool_id,
                action="unknown",
                governance_decision="blocked",
            )

        # Step 2: Validate input parameters against schema
        valid, err_msg = self.registry.validate_params(tool_id, params)
        if not valid:
            self._audit(
                event_type="sandbox.invalid_params",
                tool_id=tool_id,
                risk=tool.risk_level,
                decision="deny",
                success=False,
                error=err_msg,
            )
            return ExecutionResult(
                success=False,
                output=None,
                error=f"Invalid parameters for tool '{tool_id}': {err_msg}",
                risk_level=tool.risk_level,
                tool_id=tool_id,
                action=tool.action_type,
                governance_decision="deny",
            )

        # Step 3: Check target path for path traversal or sensitive file access
        target_path: str | None = None
        if "file_path" in params:
            target_path = str(params["file_path"])
        elif "dir_path" in params:
            target_path = str(params["dir_path"])

        if target_path:
            # Check for path traversal or outside workspace escape
            try:
                self.path_guard.resolve(target_path)
            except (PathOutsideWorkspaceError, ValueError) as exc:
                self._audit(
                    event_type="sandbox.path_guard_violation",
                    tool_id=tool_id,
                    risk=tool.risk_level,
                    decision="deny",
                    success=False,
                    error=str(exc),
                )
                return ExecutionResult(
                    success=False,
                    output=None,
                    error=f"PathGuard check failed: {exc}",
                    risk_level=tool.risk_level,
                    tool_id=tool_id,
                    action=tool.action_type,
                    governance_decision="deny",
                )

            # Check for sensitive files (.env, credentials, secrets, database)
            if _is_sensitive_path(target_path):
                msg = f"Access to sensitive file or pattern is prohibited: '{target_path}'"
                self._audit(
                    event_type="sandbox.sensitive_file_blocked",
                    tool_id=tool_id,
                    risk=tool.risk_level,
                    decision="deny",
                    success=False,
                    error=msg,
                )
                return ExecutionResult(
                    success=False,
                    output=None,
                    error=msg,
                    risk_level=tool.risk_level,
                    tool_id=tool_id,
                    action=tool.action_type,
                    governance_decision="deny",
                )

        # Step 4: PolicyEngine evaluation
        action_req = ActionRequest(action=tool.action_type, risk=tool.risk_level, target_path=target_path)
        policy_decision = self.policy_engine.authorize(action_req)

        if policy_decision.status == DecisionStatus.BLOCKED:
            self._audit(
                event_type="sandbox.policy_blocked",
                tool_id=tool_id,
                risk=tool.risk_level,
                decision="blocked",
                success=False,
                error=policy_decision.reason,
            )
            return ExecutionResult(
                success=False,
                output=None,
                error=f"PolicyEngine blocked action: {policy_decision.reason}",
                risk_level=tool.risk_level,
                tool_id=tool_id,
                action=tool.action_type,
                governance_decision="blocked",
            )

        if policy_decision.status == DecisionStatus.DENY:
            self._audit(
                event_type="sandbox.policy_denied",
                tool_id=tool_id,
                risk=tool.risk_level,
                decision="deny",
                success=False,
                error=policy_decision.reason,
            )
            return ExecutionResult(
                success=False,
                output=None,
                error=f"PolicyEngine denied action: {policy_decision.reason}",
                risk_level=tool.risk_level,
                tool_id=tool_id,
                action=tool.action_type,
                governance_decision="deny",
            )

        # Step 5: Check System Emergency State (STOP / FREEZE)
        current_state = self.get_system_state()
        if current_state in (SystemState.STOP, SystemState.FREEZE):
            state_msg = f"Execution blocked: system is in {current_state.value.upper()} state"
            self._audit(
                event_type="sandbox.system_state_blocked",
                tool_id=tool_id,
                risk=tool.risk_level,
                decision="blocked",
                success=False,
                error=state_msg,
            )
            return ExecutionResult(
                success=False,
                output=None,
                error=state_msg,
                risk_level=tool.risk_level,
                tool_id=tool_id,
                action=tool.action_type,
                governance_decision="blocked",
            )

        # Step 6: Consent Gate — Owner Approval vs Delegated Autonomy
        matched_approval_id: str | None = None
        matched_grant_id: str | None = None
        governance_decision = "pending_owner_approval"

        # Create standardized request for checking
        current_req = self.approval_gate.create_request(
            tool_id=tool.tool_id,
            action=tool.action_type,
            params=params,
            resource_scope="workspace",
            risk_level=tool.risk_level,
            goal=goal,
        )

        if approval_id:
            # Case A: Explicit approval provided
            valid_approval, reason = self.approval_gate.evaluate_approval(approval_id, current_req)
            if not valid_approval:
                self._audit(
                    event_type="sandbox.approval_rejected",
                    tool_id=tool_id,
                    risk=tool.risk_level,
                    decision="denied",
                    success=False,
                    approval_id=approval_id,
                    error=reason,
                )
                return ExecutionResult(
                    success=False,
                    output=None,
                    error=f"Owner approval invalid: {reason}",
                    risk_level=tool.risk_level,
                    tool_id=tool_id,
                    action=tool.action_type,
                    governance_decision="denied",
                    approval_id=approval_id,
                )
            # Valid approval!
            matched_approval_id = approval_id
            governance_decision = "allowed_by_approval"
        else:
            # Case B: No approval provided — evaluate Delegated Autonomy
            # R4 requires explicit approval, cannot be delegated
            if int(tool.risk_level) >= int(RiskLevel.R4):
                return ExecutionResult(
                    success=False,
                    output=None,
                    error="R4 actions require explicit owner approval; delegated autonomy cannot bypass R4",
                    risk_level=tool.risk_level,
                    tool_id=tool_id,
                    action=tool.action_type,
                    governance_decision="approval_required",
                )

            del_ok, del_reason, grant = self.delegation_registry.check_delegation(
                tool_id=tool.tool_id,
                action_type=tool.action_type,
                risk_level=tool.risk_level,
                resource_path=target_path,
                project_scope="QUAN_AI_BRAIN",
            )
            if del_ok and grant:
                matched_grant_id = grant.grant_id
                governance_decision = "allowed_by_delegation"
            else:
                # Default: Halt and demand explicit owner approval
                err_text = (
                    f"Owner consultation required: tool '{tool.tool_id}' action '{tool.action_type}' "
                    f"has neither valid one-time approval nor active delegation grant ({del_reason})"
                )
                self._audit(
                    event_type="sandbox.consent_required",
                    tool_id=tool_id,
                    risk=tool.risk_level,
                    decision="pending_owner_approval",
                    success=False,
                    error=err_text,
                )
                return ExecutionResult(
                    success=False,
                    output=None,
                    error=err_text,
                    risk_level=tool.risk_level,
                    tool_id=tool_id,
                    action=tool.action_type,
                    governance_decision="pending_owner_approval",
                )

        # Step 7: Dry run check
        if dry_run:
            if not tool.supports_dry_run:
                return ExecutionResult(
                    success=False,
                    output=None,
                    error=f"Tool '{tool_id}' does not support dry run",
                    risk_level=tool.risk_level,
                    tool_id=tool_id,
                    action=tool.action_type,
                    governance_decision="deny",
                )
            sim_output = {
                "dry_run": True,
                "tool_id": tool.tool_id,
                "action": tool.action_type,
                "simulated_params": redact_value(params),
                "risk_level": tool.risk_level.name,
                "authorized_by": governance_decision,
            }
            self._audit(
                event_type="sandbox.dry_run_executed",
                tool_id=tool_id,
                risk=tool.risk_level,
                decision="approved_dry_run",
                success=True,
                approval_id=matched_approval_id,
                grant_id=matched_grant_id,
            )
            return ExecutionResult(
                success=True,
                output=sim_output,
                error=None,
                risk_level=tool.risk_level,
                tool_id=tool_id,
                action=tool.action_type,
                governance_decision="approved_dry_run",
                approval_id=matched_approval_id,
                grant_id=matched_grant_id,
            )

        # Step 8: Execute tool handler
        try:
            output = tool.handler(params)
        except Exception as exc:
            self._audit(
                event_type="sandbox.execution_failed",
                tool_id=tool_id,
                risk=tool.risk_level,
                decision=governance_decision,
                success=False,
                approval_id=matched_approval_id,
                grant_id=matched_grant_id,
                error=str(exc),
            )
            return ExecutionResult(
                success=False,
                output=None,
                error=f"Tool execution failed: {exc}",
                risk_level=tool.risk_level,
                tool_id=tool_id,
                action=tool.action_type,
                governance_decision=governance_decision,
                approval_id=matched_approval_id,
                grant_id=matched_grant_id,
            )

        # Step 9: Post-execution state updates
        if matched_approval_id:
            # One-time consumption of approval token
            self.approval_gate.consume_approval(matched_approval_id)

        if matched_grant_id:
            # Increment call count for delegation grant
            self.delegation_registry.record_usage(matched_grant_id)

        # Step 10: Audit logging
        self._audit(
            event_type="sandbox.execution_succeeded",
            tool_id=tool_id,
            risk=tool.risk_level,
            decision=governance_decision,
            success=True,
            approval_id=matched_approval_id,
            grant_id=matched_grant_id,
        )

        return ExecutionResult(
            success=True,
            output=output,
            error=None,
            risk_level=tool.risk_level,
            tool_id=tool_id,
            action=tool.action_type,
            governance_decision=governance_decision,
            approval_id=matched_approval_id,
            grant_id=matched_grant_id,
        )

    def _audit(
        self,
        event_type: str,
        tool_id: str,
        risk: RiskLevel,
        decision: str,
        success: bool,
        approval_id: str | None = None,
        grant_id: str | None = None,
        error: str | None = None,
    ) -> None:
        details: dict[str, Any] = {
            "tool_id": tool_id,
            "risk_level": risk.name if hasattr(risk, "name") else str(risk),
            "decision": decision,
            "success": success,
        }
        if approval_id:
            details["approval_id"] = approval_id
        if grant_id:
            details["grant_id"] = grant_id
        if error:
            details["error"] = error
        self.audit_logger.record(event_type, details)
