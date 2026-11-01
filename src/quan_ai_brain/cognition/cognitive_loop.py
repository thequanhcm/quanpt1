"""QUAN AI BRAIN — Cognitive Loop (Sprint B).

Closes the task lifecycle defined in the Digital Employee Brain Master Prompt:

RECEIVED -> CONTEXT_BUILDING -> UNDERSTANDING -> PLANNING -> RISK_ASSESSMENT
-> WAITING_APPROVAL (if policy requires) -> EXECUTING|SIMULATING -> VERIFYING
-> REFLECTING -> LEARNING_CANDIDATE -> terminal state.

Design rules (docs/DIGITAL_EMPLOYEE_BRAIN_DESIGN.md):
- WRAP + EXTEND: reuses PlanOrchestrator, DurableTaskRegistry, Supervisor,
  PolicyEngine, AuditLogger — does NOT reimplement any of them.
- LLM is optional and only used for reasoning; every state transition is
  deterministic Python and audited.
- Fail-closed: missing acceptance criteria => NEEDS_APPROVAL, never guessed.
- Checkpoint durability: task state lives in DurableTaskRegistry (tasks.db);
  a killed process resumes from the last checkpoint via resume_incomplete().
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from quan_ai_brain.cognition.information_gap_analyzer import (
    EvidenceKind,
    GapAnalysis,
    InformationGapAnalyzer,
    InfoItem,
    ReadinessStatus,
)
from quan_ai_brain.cognition.reflection import ReflectionLoop
from quan_ai_brain.core.audit import AuditLogger
from quan_ai_brain.orchestration.models import AutonomyLevel, TaskStatus
from quan_ai_brain.orchestration.plan_orchestrator import PlanOrchestrator
from quan_ai_brain.orchestration.task_registry import DurableTaskRegistry


class CognitiveLoopError(RuntimeError):
    """Raised when the loop receives a malformed task submission."""


@dataclass(frozen=True)
class TaskSpec:
    """Owner- or supervisor-authored description of a task to execute.

    Acceptance criteria are mandatory: without them the loop cannot verify
    completion, so the task is rejected into NEEDS_APPROVAL (fail-closed).
    """

    goal: str
    context_refs: list[str] = field(default_factory=list)
    acceptance_criteria: list[str] = field(default_factory=list)
    risk_hint: int = 0
    deadline_utc: str | None = None
    priority: int = 5  # 1 = highest
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> list[str]:
        problems: list[str] = []
        if not self.goal or not self.goal.strip():
            problems.append("goal is empty")
        if not self.acceptance_criteria or not any(
            c.strip() for c in self.acceptance_criteria
        ):
            problems.append("acceptance_criteria is empty (fail-closed: NEEDS_APPROVAL)")
        if not isinstance(self.risk_hint, int) or not 0 <= self.risk_hint <= 5:
            problems.append(f"risk_hint must be 0..5, got {self.risk_hint!r}")
        return problems


# Ordered lifecycle states per Master Prompt Part 3.1.
LIFECYCLE_STATES: tuple[str, ...] = (
    "RECEIVED",
    "CONTEXT_BUILDING",
    "UNDERSTANDING",
    "PLANNING",
    "RISK_ASSESSMENT",
    "WAITING_APPROVAL",
    "EXECUTING",
    "VERIFYING",
    "REFLECTING",
    "LEARNING_CANDIDATE",
)

TERMINAL_STATUSES = {
    TaskStatus.COMPLETED,
    TaskStatus.FAILED,
    TaskStatus.CANCELLED,
    TaskStatus.BLOCKED,
}

# Backlog policy (GAP-R7): PENDING tasks older than this are expired.
DEFAULT_PENDING_TTL_HOURS = 48


class CognitiveLoop:
    """Orchestrates the full cognitive task lifecycle on top of existing
    orchestration primitives. Every transition writes to the audit ledger."""

    def __init__(
        self,
        task_registry: DurableTaskRegistry,
        orchestrator: PlanOrchestrator,
        workspace: str | Path | None = None,
        reflection: ReflectionLoop | None = None,
        *,
        pending_ttl_hours: int = DEFAULT_PENDING_TTL_HOURS,
        clock: Any = None,
        gap_analyzer: InformationGapAnalyzer | None = None,
    ) -> None:
        self.workspace = Path(workspace).resolve() if workspace else Path.cwd().resolve()
        self.registry = task_registry
        self.orchestrator = orchestrator
        self.gap_analyzer = gap_analyzer or InformationGapAnalyzer(
            workspace=self.workspace, clock=clock
        )
        self.reflection = reflection or ReflectionLoop(
            workspace=self.workspace, task_registry=task_registry
        )
        self.pending_ttl_hours = pending_ttl_hours
        self._clock = clock or datetime.now(timezone.utc)
        self._audit = AuditLogger(self.workspace)

    # ------------------------------------------------------------------
    # Lifecycle submission
    # ------------------------------------------------------------------

    def submit_task(
        self,
        spec: TaskSpec,
        *,
        plan_builder: Any = None,
        autonomy_level: AutonomyLevel = AutonomyLevel.LEVEL_A,
        gap_check: bool = True,
    ) -> dict[str, Any]:
        """RECEIVED -> ... -> PLANNING: validate spec, register task + plan.

        plan_builder: optional callable(spec) -> TaskPlan. When omitted the
        loop registers a durable, un- executable placeholder plan consisting
        of one R0 verification step so the task is tracked and auditable but
        can never silently execute anything.

        V3 Sprint 3 gap_check (default ON): after UNDERSTANDING the
        InformationGapAnalyzer decides READY vs NEEDS_OWNER_INPUT vs
        NEEDS_VERIFICATION. Non-READY tasks park in WAITING_FOR_OWNER_INPUT
        and NEVER reach plan registration until the owner supplies the
        missing information (im silence is NOT consent). Pass gap_check=False
        to opt out explicitly (e.g. internal self-checks).
        """
        problems = spec.validate()
        audit_ctx = {
            "goal": spec.goal[:200],
            "problems": problems,
        }
        if problems:
            self._audit.record("cognitive_loop.task_rejected", audit_ctx)
            raise CognitiveLoopError(f"Invalid TaskSpec: {'; '.join(problems)}")

        # ---- V3 Sprint 3: Information Gap Awareness (after UNDERSTANDING) ----
        if gap_check:
            known_facts: list[InfoItem] = []
            for ref in spec.context_refs:
                known_facts.append(
                    InfoItem(key=f"context_ref_{len(known_facts)}", value=ref, evidence=EvidenceKind.RETRIEVED)
                )
            for meta_key, meta_val in (spec.metadata or {}).items():
                known_facts.append(
                    InfoItem(key=str(meta_key), value=meta_val, evidence=EvidenceKind.OWNER_PROVIDED)
                )
            metadata = spec.metadata or {}
            required_inputs_meta = metadata.get("required_inputs", [])
            required_inputs = (
                [
                    i if isinstance(i, InfoItem) else InfoItem.from_dict(i)
                    for i in required_inputs_meta
                ]
                if isinstance(required_inputs_meta, list)
                else []
            )
            conflicts_meta = metadata.get("conflicts", [])
            decisions_meta = metadata.get("owner_decisions_required", [])
            gap = self.gap_analyzer.analyze_request(
                task_id=f"TASK-{abs(hash((spec.goal, spec.deadline_utc))) % 10**8:08d}",
                request_text=spec.goal[:2000],
                goal=spec.goal.strip() or "",
                acceptance_criteria=list(spec.acceptance_criteria),
                known_facts=known_facts,
                required_inputs=required_inputs,
                conflicts=[str(c) for c in conflicts_meta]
                if isinstance(conflicts_meta, list)
                else [],
                owner_decisions_required=[str(d) for d in decisions_meta]
                if isinstance(decisions_meta, list)
                else [],
                constraints=[str(v) for v in metadata.get("constraints", [])]
                if isinstance(metadata.get("constraints"), list)
                else [],
                available_resources=[str(r) for r in metadata.get("available_resources", [])]
                if isinstance(metadata.get("available_resources"), list)
                else [],
            )
            if gap.readiness is not ReadinessStatus.READY:
                self._audit.record(
                    "cognitive_loop.info_gap_blocked",
                    {
                        "readiness": gap.readiness.value,
                        "missing": [c.value for c in gap.missing],
                        "questions": len(gap.questions),
                    },
                )
                return {
                    "task_id": None,
                    "status": "NOT_SUBMITTED",
                    "readiness": gap.readiness.value,
                    "waiting_state": gap.waiting_state.value,
                    "missing": [c.value for c in gap.missing],
                    "questions": [q.to_dict() for q in gap.questions],
                    "info_request_text": self.gap_analyzer.render_info_request(gap),
                    "gap_analysis": gap.to_dict(),
                    "note": (
                        "Nhiệm vụ CHƯA được đăng ký và CHƯA thực hiện hành động nào: "
                        "thiếu thông tin thiết yếu. Trả lời ≠ phê duyệt."
                    ),
                }

        self._audit.record("cognitive_loop.task_received", audit_ctx)

        if plan_builder is not None:
            plan = plan_builder(spec)
            task = self.orchestrator.submit_plan(
                plan,
                autonomy_level=autonomy_level,
                idempotency_key=f"idem_cogloop_{abs(hash((spec.goal, spec.deadline_utc))) % 10**12}",
            )
        else:
            from quan_ai_brain.planning.models import TaskPlan, TaskStep

            placeholder = TaskPlan(
                goal=f"[COGNITIVE_LOOP] {spec.goal}",
                steps=[
                    TaskStep(
                        name="await_plan_builder",
                        description="Task registered by CognitiveLoop without an executable plan; requires an owner- or supervisor-authored plan before execution.",
                        expected_output="A validated TaskPlan supplied via plan_builder",
                        risk_level=0,
                        requires_approval=False,
                    )
                ],
                summary="CognitiveLoop placeholder plan (no auto-execution)",
                source="cognitive_loop",
            )
            task = self.orchestrator.submit_plan(
                placeholder,
                autonomy_level=autonomy_level,
                idempotency_key=f"idem_cogloop_{abs(hash((spec.goal, spec.deadline_utc))) % 10**12}",
            )

        self._audit.record(
            "cognitive_loop.task_registered",
            {"task_id": task.task_id, "risk_level": task.risk_level},
        )
        return {
            "task_id": task.task_id,
            "status": task.status.value,
            "risk_level": task.risk_level,
            "lifecycle_state": "RECEIVED",
        }

    # ------------------------------------------------------------------
    # Execution driving
    # ------------------------------------------------------------------

    def tick(self, task_id: str, *, dry_run: bool = True) -> dict[str, Any]:
        """Advance one task through EXECUTING/VERIFYING (PlanOrchestrator).

        dry_run=True keeps execution inside the inert sandbox — the default
        and only mode until Controlled Execution (Sprint F) is approved.
        """
        task = self.registry.get_task(task_id)
        if not task:
            raise KeyError(f"Task '{task_id}' not found")

        if task.status in TERMINAL_STATUSES:
            return self._snapshot(task, lifecycle_state="TERMINAL")

        if task.status == TaskStatus.WAITING_APPROVAL:
            return self._snapshot(task, lifecycle_state="WAITING_APPROVAL")

        self._audit.record(
            "cognitive_loop.executing",
            {"task_id": task_id, "dry_run": dry_run},
        )
        outcome = self.orchestrator.execute_lifecycle(task_id, dry_run=dry_run)

        refreshed = self.registry.get_task(task_id)
        state = (
            "EXECUTING"
            if refreshed.status == TaskStatus.IN_PROGRESS
            else self._lifecycle_for_status(refreshed.status)
        )
        return self._snapshot(refreshed, lifecycle_state=state, outcome=outcome)

    def approve(self, task_id: str, decision: str, guidance: str = "") -> dict[str, Any]:
        """Owner approval path for tasks parked in WAITING_APPROVAL.

        Resolves the pending consultation ticket(s) for this task; only then
        can tick() resume execution. Rejected tickets BLOCK the task.
        """
        task = self.registry.get_task(task_id)
        if not task:
            raise KeyError(f"Task '{task_id}' not found")

        tickets = [
            t
            for t in self.orchestrator.consultation_store.list_tickets(limit=200)
            if getattr(t, "task_id", None) == task_id
            or (t.metadata or {}).get("task_id") == task_id
        ]
        if not tickets:
            return {"task_id": task_id, "approved": False, "reason": "no_pending_tickets"}

        approved_any = False
        for t in tickets:
            if getattr(t, "status", None) and getattr(t.status, "value", "") in (
                "APPROVED",
                "DIRECTED",
            ):
                continue
            self.orchestrator.consultation_store.respond_ticket(
                t.ticket_id, decision=decision, guidance=guidance
            )
            approved_any = decision.upper().startswith("APPROVE") or decision.upper().startswith(
                "DIRECT"
            )

        self._audit.record(
            "cognitive_loop.approval_resolved",
            {"task_id": task_id, "decision": decision, "tickets": len(tickets)},
        )
        return {
            "task_id": task_id,
            "approved": approved_any,
            "tickets_resolved": len(tickets),
        }

    def cancel(self, task_id: str, reason: str) -> dict[str, Any]:
        task = self.orchestrator.cancel_task(task_id, reason=reason)
        self._audit.record(
            "cognitive_loop.task_cancelled", {"task_id": task_id, "reason": reason[:200]}
        )
        return {"task_id": task_id, "status": task.status.value}

    # ------------------------------------------------------------------
    # Reflection + learning + recovery + backlog policy
    # ------------------------------------------------------------------

    def reflect(self, task_id: str) -> dict[str, Any]:
        """REFLECTING state: evidence-based reflection via ReflectionLoop."""
        report = self.reflection.reflect_task(task_id)
        self._audit.record(
            "cognitive_loop.reflected",
            {
                "task_id": task_id,
                "lessons_verified": len(report.get("lessons_verified", [])),
                "lessons_hypothesis": len(report.get("lessons_hypothesis", [])),
            },
        )
        return report

    def promote_lessons(self, task_id: str) -> dict[str, Any]:
        """LEARNING_CANDIDATE: verified lessons -> episodic memory;
        hypotheses -> quarantine (candidate_knowledge), never semantic."""
        return self.reflection.persist_lessons(task_id)

    def resume_incomplete(self) -> dict[str, Any]:
        """Post-restart recovery: never silently re-runs in-flight work."""
        recovered = self.orchestrator.recover_tasks()
        self._audit.record(
            "cognitive_loop.recovery", {"recovered": [t.task_id for t in recovered]}
        )
        return {
            "recovered": [
                {"task_id": t.task_id, "status": t.status.value} for t in recovered
            ]
        }

    def expire_stale_pending(self, *, ttl_hours: int | None = None) -> dict[str, Any]:
        """GAP-R7 backlog policy: PENDING tasks older than TTL -> CANCELLED
        with an explicit reason (age-out, auditable, reversible via registry)."""
        ttl = ttl_hours if ttl_hours is not None else self.pending_ttl_hours
        cutoff = datetime.now(timezone.utc) - timedelta(hours=ttl)
        expired: list[dict[str, Any]] = []
        for task in self.registry.list_tasks(status=TaskStatus.PENDING, limit=500):
            created = datetime.fromisoformat(task.created_at_utc)
            if created < cutoff:
                self.registry.update_task_status(
                    task.task_id,
                    TaskStatus.CANCELLED,
                    error_message=f"Age-out policy: PENDING exceeded {ttl}h TTL (created {task.created_at_utc})",
                    checkpoint_data={"age_out": True},
                )
                expired.append({"task_id": task.task_id, "created_at": task.created_at_utc})
        if expired:
            self._audit.record(
                "cognitive_loop.pending_age_out",
                {"ttl_hours": ttl, "expired": len(expired)},
            )
        return {"ttl_hours": ttl, "expired_count": len(expired), "expired": expired[:20]}

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _lifecycle_for_status(self, status: TaskStatus) -> str:
        return {
            TaskStatus.PENDING: "PLANNING",
            TaskStatus.WAITING_APPROVAL: "WAITING_APPROVAL",
            TaskStatus.APPROVED: "EXECUTING",
            TaskStatus.IN_PROGRESS: "EXECUTING",
            TaskStatus.COMPLETED: "COMPLETED",
            TaskStatus.FAILED: "FAILED",
            TaskStatus.CANCELLED: "CANCELLED",
            TaskStatus.BLOCKED: "BLOCKED",
            TaskStatus.OUTCOME_UNKNOWN: "VERIFYING",
        }.get(status, "UNKNOWN")

    def _snapshot(
        self,
        task: Any,
        *,
        lifecycle_state: str,
        outcome: Any = None,
    ) -> dict[str, Any]:
        snap: dict[str, Any] = {
            "task_id": task.task_id,
            "goal": task.goal,
            "status": task.status.value,
            "lifecycle_state": lifecycle_state,
            "risk_level": task.risk_level,
            "checkpoint": task.checkpoint_data,
        }
        if outcome is not None:
            snap["outcome"] = outcome.to_dict() if hasattr(outcome, "to_dict") else str(outcome)
        return snap


def build_default_cognitive_loop(
    workspace: str | Path | None = None,
    *,
    db_path: str | Path | None = None,
) -> CognitiveLoop:
    """Factory wiring the loop to the standard project stores."""
    ws = Path(workspace).resolve() if workspace else Path.cwd().resolve()
    db = Path(db_path) if db_path else ws / "data" / "tasks.db"
    registry = DurableTaskRegistry(db, workspace=ws)
    orchestrator = PlanOrchestrator(registry, workspace=ws)
    return CognitiveLoop(registry, orchestrator, workspace=ws)
