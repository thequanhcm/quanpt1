"""Plan Orchestrator for QUAN AI BRAIN.

Bridges TaskPlan and DAG Validation directly with DurableTaskRegistry,
ApprovalGate, and SafeToolSandbox (Inert Sandbox) to achieve an auditable,
resilient, fail-closed task lifecycle:

  User Request -> Intent -> TaskPlan -> DAG Validation -> Risk Assessment ->
  DurableTaskRegistry -> Approval Gate -> Inert Sandbox -> Result Verification ->
  TaskOutcome -> Report

Core Safety Invariants:
1. R5 Hard-Blocked: Any R5 step halts the entire plan immediately and marks the task BLOCKED.
2. R4 Approval Required: Halts in WAITING_APPROVAL until explicit owner approval is verified.
3. Safe Execution: Confined to Inert Sandbox / Dry-run. No real OS subprocess or production executor.
4. Idempotent & Durable: Persists all state across restarts; prevents duplicate execution.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import uuid

from quan_ai_brain.contract.models import EvidenceRecord, TaskOutcome, TaskState
from quan_ai_brain.core.redaction import redact_text, redact_value
from quan_ai_brain.governance.consultation_inbox import (
    ConsultationCategory,
    ConsultationStore,
    ConsultationTicket,
)
from quan_ai_brain.governance.state_store import GovernanceStateStore
from quan_ai_brain.orchestration.models import (
    AutonomyLevel,
    TaskRecord,
    TaskStatus,
    TaskStepRecord,
)
from quan_ai_brain.orchestration.task_registry import DurableTaskRegistry
from quan_ai_brain.planning.models import StepStatus, TaskPlan, TaskStatus as PlanStatus
from quan_ai_brain.tools.approval import ApprovalGate, ApprovalRequest, ApprovalStatus
from quan_ai_brain.tools.sandbox import SafeToolSandbox


class PlanOrchestrator:
    """Coordinates end-to-end task execution lifecycle with strict safety containment."""

    def __init__(
        self,
        task_registry: DurableTaskRegistry,
        workspace: str | Path | None = None,
        sandbox: SafeToolSandbox | None = None,
        approval_gate: ApprovalGate | None = None,
        governance_store: GovernanceStateStore | None = None,
        consultation_store: ConsultationStore | None = None,
    ) -> None:
        self.workspace = Path(workspace).resolve() if workspace else Path.cwd().resolve()
        self.task_registry = task_registry
        self.sandbox = sandbox or SafeToolSandbox(self.workspace)
        self.approval_gate = approval_gate or self.sandbox.approval_gate
        self.governance_store = governance_store or GovernanceStateStore(self.workspace / "data" / "governance.db", workspace=self.workspace)
        self.consultation_store = consultation_store or ConsultationStore(self.workspace / "data" / "consultations.db")

    def submit_plan(
        self,
        plan: TaskPlan,
        *,
        correlation_id: str | None = None,
        idempotency_key: str | None = None,
        autonomy_level: AutonomyLevel = AutonomyLevel.LEVEL_A,
    ) -> TaskRecord:
        """Validates DAG, assesses risk, and registers task + steps in DurableTaskRegistry.

        Returns existing task if idempotency_key matches (anti-replay guarantee).
        """
        # 1. DAG Validation
        plan.validate()

        # 2. Risk Assessment
        max_step_risk = max((s.risk_level for s in plan.steps), default=0)
        overall_risk_str = f"R{max_step_risk}"
        if plan.blocked or max_step_risk >= 5:
            overall_risk_str = "R5"
        elif plan.requires_approval or max_step_risk == 4:
            overall_risk_str = "R4"

        # 3. Idempotency Key
        key = idempotency_key or f"idem_plan_{plan.plan_id}"
        corr_id = correlation_id or f"corr_{uuid.uuid4().hex[:10]}"

        # 4. Register master task in DurableTaskRegistry
        acceptance = [f"Step {s.sequence}: {s.expected_output}" for s in plan.steps if s.expected_output]
        task_rec = self.task_registry.register_task(
            goal=plan.goal,
            risk_level=overall_risk_str,
            autonomy_level=autonomy_level,
            idempotency_key=key,
            correlation_id=corr_id,
            acceptance_criteria=acceptance,
            resource_budget={"max_steps": len(plan.steps), "mode": "inert_sandbox"},
            approved_scope=[s.name for s in plan.steps],
        )

        # 5. Register discrete steps in durable_task_steps
        step_id_map: dict[str, str] = {}
        for idx, step in enumerate(plan.steps):
            raw_id = step.step_id or f"step_{idx + 1}"
            existing = self.task_registry.get_step(raw_id)
            if existing is not None and existing.task_id != task_rec.task_id:
                step_id_map[raw_id] = f"{task_rec.task_id}_{raw_id}"
            else:
                step_id_map[raw_id] = raw_id

        for idx, step in enumerate(plan.steps):
            raw_id = step.step_id or f"step_{idx + 1}"
            step_id = step_id_map[raw_id]
            initial_status = TaskStatus.PENDING
            if step.risk_level >= 5:
                initial_status = TaskStatus.BLOCKED

            mapped_deps = [step_id_map.get(d, d) for d in step.dependencies]

            step_rec = TaskStepRecord(
                step_id=step_id,
                task_id=task_rec.task_id,
                sequence=step.sequence if step.sequence else (idx + 1),
                name=step.name,
                description=step.description,
                risk_level=step.risk_level,
                status=initial_status,
                requires_approval=step.requires_approval or (step.risk_level >= 4),
                dependencies=mapped_deps,
                expected_output=step.expected_output,
                verification_method=step.verification_method,
            )
            self.task_registry.save_step(step_rec)

        return task_rec

    def execute_lifecycle(
        self,
        task_id: str,
        dry_run: bool = True,
    ) -> TaskOutcome:
        """Executes the task through DAG ordering, approval gates, and inert sandbox.

        Enforces:
        - Emergency STOP / FREEZE check.
        - R5 Hard-Block: immediate fail-closed halt.
        - R4 Approval Gate: pauses in WAITING_APPROVAL if unapproved.
        - R0-R2: runs in Inert Sandbox, verifies results, collects evidence.
        """
        task = self.task_registry.get_task(task_id)
        if not task:
            raise KeyError(f"Task '{task_id}' not found in registry")

        # 1. Terminal State Guard
        if task.status in (TaskStatus.COMPLETED, TaskStatus.CANCELLED, TaskStatus.BLOCKED):
            return self._build_outcome(task)

        # 2. Emergency State Guard
        emergency = self.governance_store.get_emergency_state()
        if emergency.state == "stop":
            self.task_registry.update_task_status(
                task_id,
                TaskStatus.BLOCKED,
                error_message=f"Emergency STOP is active: {emergency.reason}",
            )
            task = self.task_registry.get_task(task_id)  # type: ignore[assignment]
            return self._build_outcome(task)

        if emergency.state == "freeze":
            self.task_registry.update_task_status(
                task_id,
                TaskStatus.WAITING_APPROVAL,
                error_message=f"Emergency FREEZE is active: {emergency.reason}",
            )
            task = self.task_registry.get_task(task_id)  # type: ignore[assignment]
            return self._build_outcome(task)

        # 3. Transition to IN_PROGRESS
        self.task_registry.update_task_status(task_id, TaskStatus.IN_PROGRESS)

        steps = self.task_registry.list_steps_for_task(task_id)
        completed_step_ids: set[str] = {s.step_id for s in steps if s.status == TaskStatus.COMPLETED}

        for step in steps:
            if step.status == TaskStatus.COMPLETED:
                continue

            # Check Dependencies
            if step.dependencies:
                unmet = [dep for dep in step.dependencies if dep not in completed_step_ids]
                if unmet:
                    # Check if any dependency failed or blocked
                    dep_records = [s for s in steps if s.step_id in unmet]
                    if any(d.status in (TaskStatus.FAILED, TaskStatus.BLOCKED, TaskStatus.CANCELLED) for d in dep_records):
                        self.task_registry.update_step_status(
                            step.step_id,
                            TaskStatus.BLOCKED,
                            error_message=f"Dependency failed or blocked: {unmet}",
                        )
                        self.task_registry.update_task_status(
                            task_id,
                            TaskStatus.BLOCKED,
                            error_message=f"Step '{step.name}' blocked due to dependency failure: {unmet}",
                        )
                        task = self.task_registry.get_task(task_id)  # type: ignore[assignment]
                        return self._build_outcome(task)
                    continue

            # 4. SAFETY INVARIANT: R5 Hard-Block
            if step.risk_level >= 5:
                err_msg = f"R5 PROHIBITED: Step '{step.name}' is categorized as R5. Hard-blocked by safety policy."
                self.task_registry.update_step_status(
                    step.step_id,
                    TaskStatus.BLOCKED,
                    error_message=err_msg,
                )
                self.task_registry.update_task_status(
                    task_id,
                    TaskStatus.BLOCKED,
                    error_message=err_msg,
                )
                task = self.task_registry.get_task(task_id)  # type: ignore[assignment]
                return self._build_outcome(task)

            # 5. SAFETY INVARIANT: R4 Owner Approval Gate
            if step.risk_level == 4 or step.requires_approval:
                # Check for existing approval in ConsultationStore or ApprovalGate
                approval = self._check_step_approval(step, task)
                if not approval:
                    # Automatically ensure consultation ticket exists for owner review
                    ticket_id = f"cst_{task_id}_{step.step_id}"
                    if self.consultation_store:
                        try:
                            existing = self.consultation_store.get_ticket(ticket_id)
                            if not existing:
                                name_lower = (step.name or "").lower()
                                desc_lower = (step.description or "").lower()
                                is_code = any(k in name_lower or k in desc_lower for k in ("code", "patch", "nâng cấp", "bản vá", "mã nguồn"))
                                self.consultation_store.create_ticket(
                                    ConsultationTicket(
                                        ticket_id=ticket_id,
                                        title=f"[R4 Cần Phê Duyệt] Bước {step.sequence}: {step.name}",
                                        category=ConsultationCategory.CODE_PATCH_R4 if is_code else ConsultationCategory.TASK_ORCHESTRATION,
                                        priority="HIGH",
                                        context_summary=f"Nhiệm vụ '{task.goal}' (ID: {task_id}) tạm dừng tại bước rủi ro R4 '{step.name}' chờ chủ sở hữu (Quanpt1) xác thực phê duyệt.",
                                        proposed_action=f"Thực thi bước '{step.name}': {step.description} (Kỳ vọng: {step.expected_output})",
                                        options=[
                                            {"action": "APPROVE", "label": "Chấp thuận thực thi bước R4 này"},
                                            {"action": "REJECT", "label": "Từ chối thực thi và dừng bước này"},
                                            {"action": "DIRECT", "label": "Chỉ thị can thiệp hoặc điều chỉnh tham số"},
                                        ],
                                        evidence_notes=f"Task ID: {task_id}, Step ID: {step.step_id}, Risk: R{step.risk_level}",
                                        metadata={
                                            "task_id": task_id,
                                            "step_id": step.step_id,
                                            "risk_level": step.risk_level,
                                        },
                                    )
                                )
                        except Exception:
                            pass

                    # Halt and wait for owner consent
                    self.task_registry.update_step_status(
                        step.step_id,
                        TaskStatus.WAITING_APPROVAL,
                    )
                    self.task_registry.update_task_status(
                        task_id,
                        TaskStatus.WAITING_APPROVAL,
                        checkpoint_data={"blocked_step_id": step.step_id, "risk": f"R{step.risk_level}", "consultation_ticket_id": ticket_id},
                    )
                    task = self.task_registry.get_task(task_id)  # type: ignore[assignment]
                    return self._build_outcome(task)

            # 6. Execute step in Inert Sandbox
            self.task_registry.update_step_status(step.step_id, TaskStatus.IN_PROGRESS)

            step_result, evidence = self._execute_step_inert(step, task, dry_run=dry_run)

            # 7. Result Verification
            verified = self._verify_step_result(step, step_result)
            if verified:
                self.task_registry.update_step_status(
                    step.step_id,
                    TaskStatus.COMPLETED,
                    result_payload=step_result,
                )
                completed_step_ids.add(step.step_id)
            else:
                err = f"Verification failed for step '{step.name}': criteria not satisfied"
                self.task_registry.update_step_status(
                    step.step_id,
                    TaskStatus.FAILED,
                    error_message=err,
                    result_payload=step_result,
                )
                self.task_registry.update_task_status(
                    task_id,
                    TaskStatus.FAILED,
                    error_message=err,
                )
                task = self.task_registry.get_task(task_id)  # type: ignore[assignment]
                return self._build_outcome(task)

        # 8. All steps completed successfully
        refreshed_steps = self.task_registry.list_steps_for_task(task_id)
        all_done = all(s.status == TaskStatus.COMPLETED for s in refreshed_steps)
        if all_done:
            summary_payload = {
                "total_steps": len(refreshed_steps),
                "completed_steps": len(completed_step_ids),
                "execution_mode": "inert_sandbox" if dry_run else "sandboxed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }
            self.task_registry.update_task_status(
                task_id,
                TaskStatus.COMPLETED,
                result_payload=summary_payload,
                evidence_ref=f"evidence:plan_execution_{task_id}",
            )

        task = self.task_registry.get_task(task_id)  # type: ignore[assignment]
        return self._build_outcome(task)

    def cancel_task(self, task_id: str, reason: str = "User requested cancellation") -> TaskRecord:
        """Safely cancels a task and all its pending steps."""
        task = self.task_registry.get_task(task_id)
        if not task:
            raise KeyError(f"Task '{task_id}' not found")

        steps = self.task_registry.list_steps_for_task(task_id)
        for s in steps:
            if s.status not in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.BLOCKED):
                self.task_registry.update_step_status(
                    s.step_id,
                    TaskStatus.CANCELLED,
                    error_message=reason,
                )

        updated = self.task_registry.update_task_status(
            task_id,
            TaskStatus.CANCELLED,
            error_message=reason,
        )
        return updated

    def recover_tasks(self) -> list[TaskRecord]:
        """Recovers any interrupted IN_PROGRESS tasks to OUTCOME_UNKNOWN."""
        return self.task_registry.recover_in_flight_tasks()

    def get_task_outcome(self, task_id: str) -> TaskOutcome | None:
        """Retrieves and reconstructs TaskOutcome for the specified task."""
        task = self.task_registry.get_task(task_id)
        if not task:
            return None
        return self._build_outcome(task)

    # -------------------------------------------------------------------------
    # Private Helpers
    # -------------------------------------------------------------------------

    def _check_step_approval(self, step: TaskStepRecord, task: TaskRecord) -> bool:
        """Checks if a valid, unconsumed approval exists in ConsultationStore or ApprovalGate."""
        # 1. Check ConsultationStore if ticket was approved by owner
        ticket_id = f"cst_{task.task_id}_{step.step_id}"
        if self.consultation_store:
            try:
                ticket = self.consultation_store.get_ticket(ticket_id)
                if ticket and ticket.status.value in ("APPROVED", "DIRECTED"):
                    return True
            except Exception:
                pass

        # 2. Check active approvals in ApprovalGate
        for app in self.approval_gate._approvals.values():
            if (app.action == step.name or app.tool_id == f"step_{step.step_id}") and app.status == ApprovalStatus.APPROVED and not app.consumed and not app.revoked:
                return True

        # 3. Check if request already created in ApprovalGate
        already_requested = any(
            (r.action == step.name or r.tool_id == f"step_{step.step_id}") and r.status == ApprovalStatus.PENDING_OWNER_APPROVAL
            for r in self.approval_gate._requests.values()
        )
        if not already_requested:
            try:
                from quan_ai_brain.governance.policy import RiskLevel
                self.approval_gate.create_request(
                    tool_id=f"step_{step.step_id}",
                    action=step.name,
                    params={"task_id": task.task_id, "step_id": step.step_id, "description": step.description},
                    risk_level=RiskLevel.R4,
                    goal=f"Step: {step.name}",
                )
            except Exception:
                pass
        return False

    def _execute_step_inert(
        self,
        step: TaskStepRecord,
        task: TaskRecord,
        dry_run: bool = True,
    ) -> tuple[dict[str, Any], EvidenceRecord]:
        """Simulates step execution in Inert Sandbox without real OS side effects."""
        now_utc = datetime.now(timezone.utc).isoformat()
        simulated_output = {
            "step_id": step.step_id,
            "step_name": redact_text(step.name),
            "executed_in": "inert_sandbox",
            "dry_run": dry_run,
            "simulated_at_utc": now_utc,
            "status": "success",
            "details": f"Safely executed {step.name} in bounded inert sandbox.",
        }

        evidence = EvidenceRecord(
            evidence_id=f"ev_{uuid.uuid4().hex[:8]}",
            source_type="inert_sandbox",
            description=f"Evidence for step {step.name}",
            evidence_payload=simulated_output,
            collected_at_utc=now_utc,
            provenance_ref=f"task:{task.task_id}/step:{step.step_id}",
        )
        return simulated_output, evidence

    def _verify_step_result(self, step: TaskStepRecord, result: dict[str, Any]) -> bool:
        """Validates that output satisfies basic acceptance criteria."""
        if not result or result.get("status") != "success":
            return False
        return True

    def _build_outcome(self, task: TaskRecord) -> TaskOutcome:
        """Reconstructs TaskOutcome envelope from TaskRecord and step records."""
        steps = self.task_registry.list_steps_for_task(task.task_id)

        # Map registry TaskStatus to contract TaskState
        state_map = {
            TaskStatus.PENDING: TaskState.RECEIVED,
            TaskStatus.IN_PROGRESS: TaskState.RUNNING,
            TaskStatus.WAITING_APPROVAL: TaskState.WAITING_FOR_APPROVAL,
            TaskStatus.APPROVED: TaskState.AUTHORIZED,
            TaskStatus.COMPLETED: TaskState.SUCCEEDED,
            TaskStatus.FAILED: TaskState.FAILED,
            TaskStatus.CANCELLED: TaskState.CANCELLED,
            TaskStatus.OUTCOME_UNKNOWN: TaskState.OUTCOME_UNKNOWN,
            TaskStatus.BLOCKED: TaskState.BLOCKED,
        }
        state = state_map.get(task.status, TaskState.OUTCOME_UNKNOWN)

        planned_actions = [s.to_dict() for s in steps]
        observed_outcomes = [s.result_payload for s in steps if s.result_payload]
        evidence_list = [
            EvidenceRecord(
                evidence_id=f"ev_reg_{ref}",
                source_type="durable_registry",
                description=f"Persistent evidence {ref}",
                evidence_payload={"ref": ref},
                provenance_ref=f"task:{task.task_id}",
            )
            for ref in task.evidence_refs
        ]

        return TaskOutcome(
            task_id=task.task_id,
            request_id=f"req_{task.task_id}",
            correlation_id=task.correlation_id,
            state=state,
            planned_actions=planned_actions,
            authorized_actions=[s.to_dict() for s in steps if s.status == TaskStatus.COMPLETED],
            attempted_actions=[],  # Invariant: empty in inert mode
            observed_outcomes=observed_outcomes,
            evidence=evidence_list,
            governance_decision="R5_BLOCKED" if state == TaskState.BLOCKED else ("WAITING_APPROVAL" if state == TaskState.WAITING_FOR_APPROVAL else "AUTHORIZED_INERT"),
            is_outcome_certain=(state != TaskState.OUTCOME_UNKNOWN),
            error_message=task.error_message,
            is_inert=True,
            completed_at_utc=task.completed_at_utc or task.updated_at_utc,
        )
