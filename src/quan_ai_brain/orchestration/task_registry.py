"""Durable SQLite Task Registry for QUAN AI BRAIN.

Guarantees atomic state persistence, anti-replay idempotency,
and safe recovery across process restarts.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from threading import RLock
from typing import Any
import uuid

from quan_ai_brain.core.redaction import redact_text
from quan_ai_brain.orchestration.models import (
    AutonomyLevel,
    TaskRecord,
    TaskStatus,
    TaskStepRecord,
)


class DuplicateTaskError(ValueError):
    """Raised when an idempotency key collision is detected with conflicting parameters."""
    pass


class DurableTaskRegistry:
    """Thread-safe, SQLite-backed task ledger with WAL mode and atomic transitions."""

    def __init__(self, db_path: str | Path, workspace: str | Path | None = None) -> None:
        self.is_memory = str(db_path) == ":memory:"
        self._lock = RLock()
        self.workspace = Path(workspace).resolve() if workspace else Path.cwd().resolve()

        if self.is_memory:
            self.db_path = Path(":memory:")
            self._conn = sqlite3.connect(":memory:", check_same_thread=False)
        else:
            self.db_path = Path(db_path).resolve()
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            with self._conn:
                self._conn.execute("PRAGMA journal_mode = WAL")
                self._conn.execute("PRAGMA busy_timeout = 5000")

        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS durable_tasks (
                    task_id TEXT PRIMARY KEY,
                    correlation_id TEXT NOT NULL,
                    idempotency_key TEXT UNIQUE NOT NULL,
                    goal TEXT NOT NULL,
                    risk_level TEXT NOT NULL,
                    autonomy_level TEXT NOT NULL,
                    status TEXT NOT NULL,
                    acceptance_criteria_json TEXT NOT NULL,
                    approved_scope_json TEXT NOT NULL,
                    created_at_utc TEXT NOT NULL,
                    updated_at_utc TEXT NOT NULL,
                    completed_at_utc TEXT,
                    resource_budget_json TEXT NOT NULL,
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    max_retries INTEGER NOT NULL DEFAULT 3,
                    error_message TEXT,
                    evidence_refs_json TEXT NOT NULL,
                    result_payload_json TEXT NOT NULL,
                    checkpoint_data_json TEXT NOT NULL
                )
                """
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_tasks_status ON durable_tasks (status)"
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_tasks_corr ON durable_tasks (correlation_id)"
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS durable_task_steps (
                    step_id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    sequence INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    risk_level INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    requires_approval INTEGER NOT NULL,
                    dependencies_json TEXT NOT NULL,
                    expected_output TEXT NOT NULL,
                    verification_method TEXT NOT NULL,
                    result_payload_json TEXT NOT NULL,
                    error_message TEXT,
                    completed_at_utc TEXT,
                    FOREIGN KEY (task_id) REFERENCES durable_tasks(task_id)
                )
                """
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_steps_task ON durable_task_steps (task_id)"
            )

    def register_task(
        self,
        goal: str,
        *,
        risk_level: str = "R1",
        autonomy_level: AutonomyLevel = AutonomyLevel.LEVEL_A,
        idempotency_key: str | None = None,
        correlation_id: str | None = None,
        acceptance_criteria: list[str] | None = None,
        resource_budget: dict[str, Any] | None = None,
        approved_scope: list[str] | None = None,
    ) -> TaskRecord:
        """Register a new task or return existing task if idempotency_key matches."""
        clean_goal = redact_text(goal.strip())
        key = idempotency_key or f"idem_{uuid.uuid4().hex}"
        corr_id = correlation_id or f"corr_{uuid.uuid4().hex[:12]}"

        existing = self.get_by_idempotency_key(key)
        if existing:
            return existing

        task_id = f"task_{uuid.uuid4().hex[:12]}"
        now_utc = datetime.now(timezone.utc).isoformat()
        record = TaskRecord(
            task_id=task_id,
            correlation_id=corr_id,
            idempotency_key=key,
            goal=clean_goal,
            risk_level=risk_level,
            autonomy_level=autonomy_level,
            status=TaskStatus.PENDING,
            acceptance_criteria=acceptance_criteria or [],
            approved_scope=approved_scope or [],
            created_at_utc=now_utc,
            updated_at_utc=now_utc,
            resource_budget=resource_budget or {"max_steps": 10, "max_time_sec": 300},
        )

        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO durable_tasks (
                    task_id, correlation_id, idempotency_key, goal, risk_level,
                    autonomy_level, status, acceptance_criteria_json, approved_scope_json,
                    created_at_utc, updated_at_utc, completed_at_utc, resource_budget_json,
                    retry_count, max_retries, error_message, evidence_refs_json,
                    result_payload_json, checkpoint_data_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.task_id,
                    record.correlation_id,
                    record.idempotency_key,
                    record.goal,
                    record.risk_level,
                    record.autonomy_level.value,
                    record.status.value,
                    json.dumps(record.acceptance_criteria),
                    json.dumps(record.approved_scope),
                    record.created_at_utc,
                    record.updated_at_utc,
                    None,
                    json.dumps(record.resource_budget),
                    record.retry_count,
                    record.max_retries,
                    None,
                    json.dumps(record.evidence_refs),
                    json.dumps(record.result_payload),
                    json.dumps(record.checkpoint_data),
                ),
            )
            self._conn.commit()
        return record

    def get_task(self, task_id: str) -> TaskRecord | None:
        with self._lock, self._conn:
            cur = self._conn.execute("SELECT * FROM durable_tasks WHERE task_id = ?", (task_id,))
            row = cur.fetchone()
            return self._row_to_record(row) if row else None

    def get_by_idempotency_key(self, idempotency_key: str) -> TaskRecord | None:
        with self._lock, self._conn:
            cur = self._conn.execute("SELECT * FROM durable_tasks WHERE idempotency_key = ?", (idempotency_key,))
            row = cur.fetchone()
            return self._row_to_record(row) if row else None

    def list_tasks(
        self, status: TaskStatus | None = None, limit: int = 50
    ) -> list[TaskRecord]:
        with self._lock, self._conn:
            if status:
                cur = self._conn.execute(
                    "SELECT * FROM durable_tasks WHERE status = ? ORDER BY created_at_utc ASC LIMIT ?",
                    (status.value, limit),
                )
            else:
                cur = self._conn.execute(
                    "SELECT * FROM durable_tasks ORDER BY created_at_utc DESC LIMIT ?",
                    (limit,),
                )
            return [self._row_to_record(row) for row in cur.fetchall()]

    def update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        *,
        error_message: str | None = None,
        checkpoint_data: dict[str, Any] | None = None,
        result_payload: dict[str, Any] | None = None,
        evidence_ref: str | None = None,
    ) -> TaskRecord:
        existing = self.get_task(task_id)
        if not existing:
            raise KeyError(f"Task {task_id} not found")

        now_utc = datetime.now(timezone.utc).isoformat()
        completed_at = now_utc if status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED) else existing.completed_at_utc

        checkpoints = dict(existing.checkpoint_data)
        if checkpoint_data:
            checkpoints.update(checkpoint_data)

        results = dict(existing.result_payload)
        if result_payload:
            results.update(result_payload)

        evidence_refs = list(existing.evidence_refs)
        if evidence_ref and evidence_ref not in evidence_refs:
            evidence_refs.append(evidence_ref)

        with self._lock, self._conn:
            self._conn.execute(
                """
                UPDATE durable_tasks SET
                    status = ?,
                    updated_at_utc = ?,
                    completed_at_utc = ?,
                    error_message = ?,
                    checkpoint_data_json = ?,
                    result_payload_json = ?,
                    evidence_refs_json = ?
                WHERE task_id = ?
                """,
                (
                    status.value,
                    now_utc,
                    completed_at,
                    error_message if error_message is not None else existing.error_message,
                    json.dumps(checkpoints),
                    json.dumps(results),
                    json.dumps(evidence_refs),
                    task_id,
                ),
            )
        return self.get_task(task_id)  # type: ignore[return-value]

    def recover_in_flight_tasks(self) -> list[TaskRecord]:
        """Transitions any IN_PROGRESS task to OUTCOME_UNKNOWN upon supervisor restart.

        Never silently re-runs an unverified action with potential side effects.
        """
        with self._lock, self._conn:
            cur = self._conn.execute(
                "SELECT task_id FROM durable_tasks WHERE status = ?",
                (TaskStatus.IN_PROGRESS.value,),
            )
            pids = [r["task_id"] for r in cur.fetchall()]

        recovered: list[TaskRecord] = []
        for pid in pids:
            rec = self.update_task_status(
                pid,
                TaskStatus.OUTCOME_UNKNOWN,
                error_message="Supervisor restarted while task was in progress; state requires owner or tool verification.",
                checkpoint_data={"recovery_note": "Recovered from unverified in-flight status"},
            )
            recovered.append(rec)
        return recovered

    def _row_to_record(self, row: sqlite3.Row) -> TaskRecord:
        # Map 'archived' (legacy) to CANCELLED for backward compatibility
        status_raw = row["status"]
        if status_raw == "archived":
            status_raw = "CANCELLED"
        try:
            status = TaskStatus(status_raw)
        except ValueError:
            status = TaskStatus.PENDING
        return TaskRecord(
            task_id=row["task_id"],
            correlation_id=row["correlation_id"],
            idempotency_key=row["idempotency_key"],
            goal=row["goal"],
            risk_level=row["risk_level"],
            autonomy_level=AutonomyLevel(row["autonomy_level"]),
            status=status,
            acceptance_criteria=json.loads(row["acceptance_criteria_json"]),
            approved_scope=json.loads(row["approved_scope_json"]),
            created_at_utc=row["created_at_utc"],
            updated_at_utc=row["updated_at_utc"],
            completed_at_utc=row["completed_at_utc"],
            resource_budget=json.loads(row["resource_budget_json"]),
            retry_count=row["retry_count"],
            max_retries=row["max_retries"],
            error_message=row["error_message"],
            evidence_refs=json.loads(row["evidence_refs_json"]),
            result_payload=json.loads(row["result_payload_json"]),
            checkpoint_data=json.loads(row["checkpoint_data_json"]),
        )

    def save_step(self, step: TaskStepRecord) -> TaskStepRecord:
        """Saves or updates a TaskStepRecord in durable_task_steps table."""
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO durable_task_steps (
                    step_id, task_id, sequence, name, description, risk_level,
                    status, requires_approval, dependencies_json, expected_output,
                    verification_method, result_payload_json, error_message, completed_at_utc
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(step_id) DO UPDATE SET
                    task_id = excluded.task_id,
                    sequence = excluded.sequence,
                    name = excluded.name,
                    description = excluded.description,
                    risk_level = excluded.risk_level,
                    status = excluded.status,
                    requires_approval = excluded.requires_approval,
                    dependencies_json = excluded.dependencies_json,
                    expected_output = excluded.expected_output,
                    verification_method = excluded.verification_method,
                    result_payload_json = excluded.result_payload_json,
                    error_message = excluded.error_message,
                    completed_at_utc = excluded.completed_at_utc
                """,
                (
                    step.step_id,
                    step.task_id,
                    step.sequence,
                    step.name,
                    step.description,
                    step.risk_level,
                    step.status.value,
                    1 if step.requires_approval else 0,
                    json.dumps(step.dependencies),
                    step.expected_output,
                    step.verification_method,
                    json.dumps(step.result_payload),
                    step.error_message,
                    step.completed_at_utc,
                ),
            )
        return step

    def get_step(self, step_id: str) -> TaskStepRecord | None:
        """Fetch step record by step_id."""
        with self._lock, self._conn:
            cur = self._conn.execute("SELECT * FROM durable_task_steps WHERE step_id = ?", (step_id,))
            row = cur.fetchone()
            return self._row_to_step_record(row) if row else None

    def list_steps_for_task(self, task_id: str) -> list[TaskStepRecord]:
        """Fetch all steps belonging to task_id ordered by sequence."""
        with self._lock, self._conn:
            cur = self._conn.execute(
                "SELECT * FROM durable_task_steps WHERE task_id = ? ORDER BY sequence ASC",
                (task_id,),
            )
            return [self._row_to_step_record(r) for r in cur.fetchall()]

    def update_step_status(
        self,
        step_id: str,
        status: TaskStatus,
        *,
        error_message: str | None = None,
        result_payload: dict[str, Any] | None = None,
    ) -> TaskStepRecord:
        """Updates step status and optional outcome."""
        existing = self.get_step(step_id)
        if not existing:
            raise KeyError(f"Step {step_id} not found")

        now_utc = datetime.now(timezone.utc).isoformat()
        completed_at = now_utc if status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED, TaskStatus.BLOCKED) else existing.completed_at_utc

        results = dict(existing.result_payload)
        if result_payload:
            results.update(result_payload)

        with self._lock, self._conn:
            self._conn.execute(
                """
                UPDATE durable_task_steps SET
                    status = ?,
                    completed_at_utc = ?,
                    error_message = ?,
                    result_payload_json = ?
                WHERE step_id = ?
                """,
                (
                    status.value,
                    completed_at,
                    error_message if error_message is not None else existing.error_message,
                    json.dumps(results),
                    step_id,
                ),
            )
        return self.get_step(step_id)  # type: ignore[return-value]

    def _row_to_step_record(self, row: sqlite3.Row) -> TaskStepRecord:
        return TaskStepRecord(
            step_id=row["step_id"],
            task_id=row["task_id"],
            sequence=row["sequence"],
            name=row["name"],
            description=row["description"],
            risk_level=row["risk_level"],
            status=TaskStatus(row["status"]),
            requires_approval=bool(row["requires_approval"]),
            dependencies=json.loads(row["dependencies_json"]),
            expected_output=row["expected_output"],
            verification_method=row["verification_method"],
            result_payload=json.loads(row["result_payload_json"]),
            error_message=row["error_message"],
            completed_at_utc=row["completed_at_utc"],
        )

