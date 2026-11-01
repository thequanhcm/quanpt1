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
    TERMINAL_STATES,
    AutonomyLevel,
    TaskRecord,
    TaskStatus,
    TaskStepRecord,
    TaskTransition,
    VALID_SOURCES,
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
            self._migrate_deom_schema()

    # ------------------------------------------------------------------
    # DEOM M2 (01/11/2026) — schema mở rộng AN TOÀN: ADD COLUMN nullable +
    # bảng transition log. Idempotent (chạy an toàn mỗi lần khởi tạo).
    # Backup trước migration đã làm ở tools (tasks_backup_20261101_2300.db).
    # ------------------------------------------------------------------
    _DEOM_COLUMNS: dict[str, str] = {
        "priority": "INTEGER NOT NULL DEFAULT 3",           # 1=Critical..5=Background
        "deadline_utc": "TEXT",                             # phát hiện quá hạn
        "parent_task_id": "TEXT",                           # task nhóm / milestone
        "dependencies_json": "TEXT NOT NULL DEFAULT '[]'",  # task phải xong trước
        "required_tools_json": "TEXT NOT NULL DEFAULT '[]'",
        "assigned_agents_json": "TEXT NOT NULL DEFAULT '[]'",
        "permission_scope_json": "TEXT NOT NULL DEFAULT '[]'",
        "progress_weight_json": "TEXT NOT NULL DEFAULT '{}'",
        "source": "TEXT NOT NULL DEFAULT 'owner'",          # owner|proactive|learning|system
        "verified_at_utc": "TEXT",                          # TaskVerifier xác nhận lúc nào
        "verification_note": "TEXT",                        # kết quả kiểm chứng / lý do PARTIALLY
    }

    def _migrate_deom_schema(self) -> None:
        """ADD COLUMN idempotent + tạo task_transitions. Không sửa/xoá cột cũ."""
        with self._lock, self._conn:
            existing = {row[1] for row in self._conn.execute("PRAGMA table_info(durable_tasks)")}
            for col, decl in self._DEOM_COLUMNS.items():
                if col not in existing:
                    self._conn.execute(f"ALTER TABLE durable_tasks ADD COLUMN {col} {decl}")
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS task_transitions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    from_status TEXT,
                    to_status TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    reason TEXT NOT NULL DEFAULT '',
                    evidence_ref TEXT NOT NULL DEFAULT '',
                    at_utc TEXT NOT NULL
                )
                """
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_transitions_task ON task_transitions (task_id)"
            )
            # Work queue index: chọn task READY theo priority + deadline nhanh
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_tasks_queue ON durable_tasks (status, priority, deadline_utc)"
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
        priority: int = 3,
        deadline_utc: str | None = None,
        parent_task_id: str | None = None,
        dependencies: list[str] | None = None,
        required_tools: list[str] | None = None,
        assigned_agents: list[str] | None = None,
        permission_scope: list[str] | None = None,
        progress_weight: dict[str, Any] | None = None,
        source: str = "owner",
        initial_status: TaskStatus = TaskStatus.PENDING,
    ) -> TaskRecord:
        """Register a new task or return existing task if idempotency_key matches.

        DEOM M2: nhận priority/deadline/dependencies/... + initial_status cho
        intake pipeline (RECEIVED thay vì PENDING nếu qua NL intake).
        """
        clean_goal = redact_text(goal.strip())
        key = idempotency_key or f"idem_{uuid.uuid4().hex}"
        corr_id = correlation_id or f"corr_{uuid.uuid4().hex[:12]}"

        existing = self.get_by_idempotency_key(key)
        if existing:
            return existing

        if source not in VALID_SOURCES:
            source = "owner"
        priority = max(1, min(5, int(priority)))
        task_id = f"task_{uuid.uuid4().hex[:12]}"
        now_utc = datetime.now(timezone.utc).isoformat()
        record = TaskRecord(
            task_id=task_id,
            correlation_id=corr_id,
            idempotency_key=key,
            goal=clean_goal,
            risk_level=risk_level,
            autonomy_level=autonomy_level,
            status=initial_status,
            acceptance_criteria=acceptance_criteria or [],
            approved_scope=approved_scope or [],
            created_at_utc=now_utc,
            updated_at_utc=now_utc,
            resource_budget=resource_budget or {"max_steps": 10, "max_time_sec": 300},
            priority=priority,
            deadline_utc=deadline_utc,
            parent_task_id=parent_task_id,
            dependencies=dependencies or [],
            required_tools=required_tools or [],
            assigned_agents=assigned_agents or [],
            permission_scope=permission_scope or [],
            progress_weight=progress_weight or {},
            source=source,
        )

        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO durable_tasks (
                    task_id, correlation_id, idempotency_key, goal, risk_level,
                    autonomy_level, status, acceptance_criteria_json, approved_scope_json,
                    created_at_utc, updated_at_utc, completed_at_utc, resource_budget_json,
                    retry_count, max_retries, error_message, evidence_refs_json,
                    result_payload_json, checkpoint_data_json,
                    priority, deadline_utc, parent_task_id, dependencies_json,
                    required_tools_json, assigned_agents_json, permission_scope_json,
                    progress_weight_json, source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    record.priority,
                    record.deadline_utc,
                    record.parent_task_id,
                    json.dumps(record.dependencies),
                    json.dumps(record.required_tools),
                    json.dumps(record.assigned_agents),
                    json.dumps(record.permission_scope),
                    json.dumps(record.progress_weight),
                    record.source,
                ),
            )
            self._conn.commit()
        # Transition log khai sinh (DEOM §4.4)
        self._log_transition(
            task_id, None, record.status.value, actor="system",
            reason=f"task registered (source={record.source}, priority={record.priority})",
        )
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
        actor: str = "tony",
        reason: str = "",
    ) -> TaskRecord:
        existing = self.get_task(task_id)
        if not existing:
            raise KeyError(f"Task {task_id} not found")

        now_utc = datetime.now(timezone.utc).isoformat()
        terminal_ok = status in (TaskStatus.COMPLETED, TaskStatus.COMPLETED_VERIFIED, TaskStatus.COMPLETED_PARTIALLY, TaskStatus.COMPLETED_UNVERIFIED)
        terminal = terminal_ok or status in (TaskStatus.FAILED, TaskStatus.CANCELLED, TaskStatus.REJECTED, TaskStatus.EXPIRED)
        completed_at = now_utc if terminal else existing.completed_at_utc

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
        # Transition log (DEOM §4.4) — sau khi UPDATE thành công
        self._log_transition(
            task_id,
            existing.status.value,
            status.value,
            actor=actor,
            reason=reason,
            evidence_ref=evidence_ref or "",
        )
        return self.get_task(task_id)  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # DEOM M2 — transition log + work queue + verifier + deadline
    # ------------------------------------------------------------------

    def _log_transition(
        self,
        task_id: str,
        from_status: str | None,
        to_status: str,
        *,
        actor: str = "tony",
        reason: str = "",
        evidence_ref: str = "",
    ) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO task_transitions (task_id, from_status, to_status, actor, reason, evidence_ref, at_utc)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    from_status,
                    to_status,
                    actor,
                    reason,
                    evidence_ref,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            self._conn.commit()

    def list_transitions(self, task_id: str, limit: int = 100) -> list[TaskTransition]:
        with self._lock, self._conn:
            cur = self._conn.execute(
                """
                SELECT task_id, from_status, to_status, actor, reason, evidence_ref, at_utc
                FROM task_transitions WHERE task_id = ? ORDER BY id ASC LIMIT ?
                """,
                (task_id, limit),
            )
            return [
                TaskTransition(
                    task_id=r["task_id"],
                    from_status=r["from_status"],
                    to_status=r["to_status"],
                    actor=r["actor"],
                    reason=r["reason"],
                    evidence_ref=r["evidence_ref"],
                    at_utc=r["at_utc"],
                )
                for r in cur.fetchall()
            ]

    def assign_agent(
        self,
        task_id: str,
        agent_id: str,
        *,
        actor: str = "dispatcher",
        reason: str = "",
    ) -> TaskRecord:
        """DEOM M3 — gán agent vào `assigned_agents_json` + transition log.

        Không đổi status (assignment không phải transition vòng đời); chỉ ghi
        danh sách agent + một transition 'same-status' với actor/reason rõ ràng
        để audit đầy đủ (ai gán, khi nào, vì sao).
        """
        existing = self.get_task(task_id)
        if not existing:
            raise KeyError(f"Task {task_id} not found")
        agents = list(existing.assigned_agents)
        if agent_id not in agents:
            agents.append(agent_id)
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE durable_tasks SET assigned_agents_json = ?, updated_at_utc = ? WHERE task_id = ?",
                (
                    __import__("json").dumps(agents),
                    datetime.now(timezone.utc).isoformat(),
                    task_id,
                ),
            )
        # transition 'same-status' để audit assignment (from == to = status hiện tại)
        self._log_transition(
            task_id,
            existing.status.value,
            existing.status.value,
            actor=actor,
            reason=reason or f"assigned to {agent_id}",
        )
        return self.get_task(task_id)  # type: ignore[return-value]

    def update_progress_weight(
        self,
        task_id: str,
        progress_weight: dict[str, Any],
        *,
        actor: str = "tony",
        reason: str = "",
    ) -> TaskRecord:
        """Ghi đè progress_weight (JSON) — dùng bởi RecurringTaskEngine (M6)."""
        existing = self.get_task(task_id)
        if not existing:
            raise KeyError(f"Task {task_id} not found")
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE durable_tasks SET progress_weight_json = ?, updated_at_utc = ? WHERE task_id = ?",
                (
                    json.dumps(progress_weight, ensure_ascii=False),
                    datetime.now(timezone.utc).isoformat(),
                    task_id,
                ),
            )
        self._log_transition(
            task_id,
            existing.status.value,
            existing.status.value,
            actor=actor,
            reason=reason or "progress_weight updated",
        )
        return self.get_task(task_id)  # type: ignore[return-value]

    def work_queue(self, limit: int = 20, include_learning: bool = True) -> list[TaskRecord]:
        """Work Queue 4 bậc DEOM §7.2 — READY/PENDING theo priority, deadline, tuổi.

        Chống learning chiếm tài nguyên: task source='learning' chỉ được vào
        queue khi không có task của owner chờ (caller kiểm tra qua has_owner_tasks).
        """
        with self._lock, self._conn:
            cur = self._conn.execute(
                """
                SELECT * FROM durable_tasks
                WHERE status IN ('READY', 'PENDING', 'APPROVED', 'RECEIVED', 'UNDERSTANDING',
                                 'ANALYZING', 'PLANNING')
                ORDER BY priority ASC,
                         CASE WHEN deadline_utc IS NULL THEN 1 ELSE 0 END ASC,
                         deadline_utc ASC,
                         created_at_utc ASC
                LIMIT ?
                """,
                (limit * 2,),
            )
            records = [self._row_to_record(r) for r in cur.fetchall()]
        if not include_learning:
            records = [r for r in records if r.source != "learning"]
        owner_pending = any(r.source == "owner" for r in records)
        if owner_pending:
            records = [r for r in records if r.source != "learning"]
        return records[:limit]

    def has_owner_tasks(self) -> bool:
        with self._lock, self._conn:
            cur = self._conn.execute(
                "SELECT 1 FROM durable_tasks WHERE source='owner' AND status IN ('READY','PENDING','APPROVED') LIMIT 1"
            )
            return cur.fetchone() is not None

    def expire_overdue(self) -> list[TaskRecord]:
        """Deadline đã qua mà chưa kết thúc → EXPIRED (chạy trong watchdog loop)."""
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._lock, self._conn:
            cur = self._conn.execute(
                """
                SELECT task_id FROM durable_tasks
                WHERE deadline_utc IS NOT NULL AND deadline_utc < ?
                  AND status NOT IN ('COMPLETED','COMPLETED_VERIFIED','COMPLETED_PARTIALLY',
                                     'COMPLETED_UNVERIFIED','CANCELLED','REJECTED','EXPIRED')
                """,
                (now_iso,),
            )
            overdue = [r["task_id"] for r in cur.fetchall()]
        expired: list[TaskRecord] = []
        for tid in overdue:
            expired.append(
                self.update_task_status(
                    tid, TaskStatus.EXPIRED, actor="system", reason=f"deadline passed ({now_iso})"
                )
            )
        return expired

    def verify_task(
        self,
        task_id: str,
        *,
        evidence_ok: bool,
        note: str = "",
        actor: str = "task_verifier",
        evidence_ref: str = "",
    ) -> TaskRecord:
        """Task Verifier DEOM §4.3 — COMPLETED chỉ thành COMPLETED_VERIFIED khi có
        bằng chứng acceptance criteria. Không verifier/bằng chứng → COMPLETED_UNVERIFIED
        (fail-honest, không bao giờ tự phong VERIFIED)."""
        existing = self.get_task(task_id)
        if not existing:
            raise KeyError(f"Task {task_id} not found")
        now_utc = datetime.now(timezone.utc).isoformat()
        if existing.status not in (TaskStatus.VERIFYING, TaskStatus.COMPLETED, TaskStatus.COMPLETED_UNVERIFIED):
            raise ValueError(
                f"verify_task requires task in VERIFYING/COMPLETED/COMPLETED_UNVERIFIED, got {existing.status.value}"
            )
        target = TaskStatus.COMPLETED_VERIFIED if evidence_ok else TaskStatus.COMPLETED_UNVERIFIED
        with self._lock, self._conn:
            self._conn.execute(
                """
                UPDATE durable_tasks SET status = ?, verified_at_utc = ?, verification_note = ?,
                                         updated_at_utc = ?, completed_at_utc = COALESCE(completed_at_utc, ?)
                WHERE task_id = ?
                """,
                (target.value, now_utc, note, now_utc, now_utc, task_id),
            )
        self._log_transition(
            task_id, existing.status.value, target.value, actor=actor,
            reason=note or ("evidence ok" if evidence_ok else "missing/insufficient evidence"),
            evidence_ref=evidence_ref,
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
            # DEOM M2 columns (row keys exist sau migration idempotent)
            priority=row["priority"] if "priority" in row.keys() else 3,
            deadline_utc=row["deadline_utc"] if "deadline_utc" in row.keys() else None,
            parent_task_id=row["parent_task_id"] if "parent_task_id" in row.keys() else None,
            dependencies=json.loads(row["dependencies_json"]) if "dependencies_json" in row.keys() else [],
            required_tools=json.loads(row["required_tools_json"]) if "required_tools_json" in row.keys() else [],
            assigned_agents=json.loads(row["assigned_agents_json"]) if "assigned_agents_json" in row.keys() else [],
            permission_scope=json.loads(row["permission_scope_json"]) if "permission_scope_json" in row.keys() else [],
            progress_weight=json.loads(row["progress_weight_json"]) if "progress_weight_json" in row.keys() else {},
            source=row["source"] if "source" in row.keys() else "owner",
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

