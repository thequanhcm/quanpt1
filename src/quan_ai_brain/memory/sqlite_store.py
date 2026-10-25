"""Local SQLite memory store for episodic events and quarantined knowledge."""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any

from quan_ai_brain.core.redaction import redact_text, redact_value
from quan_ai_brain.memory.models import LifecycleStatus, MemoryRecord, MemoryType, VerificationStatus
from quan_ai_brain.tools.path_guard import PathGuard


class MemoryStore:
    def __init__(self, db_path: str | Path = ":memory:", workspace: str | Path | None = None) -> None:
        self._lock = RLock()
        self._is_memory = str(db_path) == ":memory:"
        if self._is_memory:
            self.db_path = ":memory:"
        else:
            requested = Path(db_path)
            if workspace is not None:
                guard = PathGuard(workspace)
                if requested.is_absolute():
                    # A DB path may be absolute only when the caller deliberately resolves it
                    # before construction and it is located below the authorized workspace.
                    try:
                        resolved = requested.resolve(strict=False)
                        resolved.relative_to(guard.workspace)
                    except ValueError as exc:
                        raise ValueError("Database path must be inside the authorized workspace") from exc
                    self.db_path = resolved
                else:
                    self.db_path = guard.resolve(requested)
            else:
                self.db_path = requested.resolve(strict=False)
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._create_schema()

    def _create_schema(self) -> None:
        with self._connection:
            self._connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS episodes (
                    id TEXT PRIMARY KEY,
                    created_at_utc TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    source_ref TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'recorded',
                    metadata_json TEXT NOT NULL DEFAULT '{}'
                );
                CREATE INDEX IF NOT EXISTS idx_episodes_created_at ON episodes(created_at_utc);
                CREATE TABLE IF NOT EXISTS candidate_knowledge (
                    id TEXT PRIMARY KEY,
                    created_at_utc TEXT NOT NULL,
                    statement TEXT NOT NULL,
                    source_ref TEXT NOT NULL,
                    rationale TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'quarantined',
                    decision_note TEXT NOT NULL DEFAULT ''
                );
                CREATE INDEX IF NOT EXISTS idx_candidate_status ON candidate_knowledge(status);
                CREATE TABLE IF NOT EXISTS semantic_memory (
                    id TEXT PRIMARY KEY,
                    created_at_utc TEXT NOT NULL,
                    statement TEXT NOT NULL,
                    source_ref TEXT NOT NULL,
                    approved_by TEXT NOT NULL,
                    regression_passed INTEGER NOT NULL CHECK(regression_passed = 1)
                );
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    memory_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    source_ref TEXT NOT NULL DEFAULT '',
                    verification_status TEXT NOT NULL DEFAULT 'UNVERIFIED',
                    confidence_score REAL NOT NULL DEFAULT 1.0,
                    project_scope TEXT NOT NULL DEFAULT 'general',
                    tags_json TEXT NOT NULL DEFAULT '[]',
                    lifecycle_status TEXT NOT NULL DEFAULT 'active',
                    version INTEGER NOT NULL DEFAULT 1,
                    superseded_by TEXT,
                    created_at_utc TEXT NOT NULL,
                    updated_at_utc TEXT NOT NULL,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    FOREIGN KEY (superseded_by) REFERENCES memories(id)
                );
                CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(memory_type);
                CREATE INDEX IF NOT EXISTS idx_memories_verification ON memories(verification_status);
                CREATE INDEX IF NOT EXISTS idx_memories_lifecycle ON memories(lifecycle_status);
                CREATE INDEX IF NOT EXISTS idx_memories_project ON memories(project_scope);
                CREATE INDEX IF NOT EXISTS idx_memories_created_at ON memories(created_at_utc);
                """
            )

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def add_episode(
        self,
        summary: str,
        *,
        kind: str = "task",
        source_ref: str = "",
        status: str = "recorded",
        metadata: dict[str, Any] | None = None,
    ) -> str:
        if not summary.strip():
            raise ValueError("Episode summary must not be empty")
        record_id = str(uuid.uuid4())
        safe_summary = redact_text(summary)
        safe_source = redact_text(source_ref)
        safe_metadata = json.dumps(redact_value(metadata or {}), ensure_ascii=False)
        with self._lock, self._connection:
            self._connection.execute(
                "INSERT INTO episodes(id, created_at_utc, kind, summary, source_ref, status, metadata_json) VALUES(?,?,?,?,?,?,?)",
                (record_id, self._now(), redact_text(kind), safe_summary, safe_source, status, safe_metadata),
            )
        return record_id

    def list_episodes(self, limit: int = 50) -> list[dict[str, Any]]:
        if not 1 <= limit <= 500:
            raise ValueError("limit must be between 1 and 500")
        with self._lock:
            rows = self._connection.execute(
                "SELECT id, created_at_utc, kind, summary, source_ref, status, metadata_json FROM episodes ORDER BY created_at_utc DESC LIMIT ?",
                (limit,),
            ).fetchall()
        output: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            try:
                item["metadata"] = json.loads(item.pop("metadata_json"))
            except json.JSONDecodeError:
                item["metadata"] = {}
            output.append(item)
        return output

    def add_candidate(self, statement: str, source_ref: str, rationale: str = "") -> str:
        if not statement.strip():
            raise ValueError("Candidate statement must not be empty")
        if not source_ref.strip():
            raise ValueError("Candidate knowledge requires a source reference")
        candidate_id = str(uuid.uuid4())
        with self._lock, self._connection:
            self._connection.execute(
                "INSERT INTO candidate_knowledge(id, created_at_utc, statement, source_ref, rationale) VALUES(?,?,?,?,?)",
                (candidate_id, self._now(), redact_text(statement), redact_text(source_ref), redact_text(rationale)),
            )
        return candidate_id

    def promote_candidate(
        self,
        candidate_id: str,
        *,
        approved_by: str | None,
        regression_passed: bool,
        decision_note: str = "",
        approval_verified: bool = False,
    ) -> None:
        """Internal promotion primitive; caller must provide externally verified approval."""
        if not approval_verified:
            raise PermissionError("No verified approval proof supplied; candidate remains quarantined")
        if not approved_by or not approved_by.strip():
            raise PermissionError("Human approval is required before promotion")
        if not regression_passed:
            raise ValueError("Regression tests must pass before promotion")
        with self._lock, self._connection:
            row = self._connection.execute(
                "SELECT id, statement, source_ref, status FROM candidate_knowledge WHERE id = ?",
                (candidate_id,),
            ).fetchone()
            if row is None:
                raise KeyError("Candidate knowledge not found")
            if row["status"] != "quarantined":
                raise ValueError("Only quarantined candidates can be promoted")
            self._connection.execute(
                "INSERT INTO semantic_memory(id, created_at_utc, statement, source_ref, approved_by, regression_passed) VALUES(?,?,?,?,?,1)",
                (row["id"], self._now(), row["statement"], row["source_ref"], redact_text(approved_by)),
            )
            self._connection.execute(
                "UPDATE candidate_knowledge SET status = 'promoted', decision_note = ? WHERE id = ?",
                (redact_text(decision_note), candidate_id),
            )

    def list_candidates(self, limit: int = 50) -> list[dict[str, Any]]:
        if not 1 <= limit <= 500:
            raise ValueError("limit must be between 1 and 500")
        with self._lock:
            rows = self._connection.execute(
                "SELECT id, created_at_utc, statement, source_ref, rationale, status, decision_note FROM candidate_knowledge ORDER BY created_at_utc DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def store_memory(
        self,
        content: str,
        memory_type: MemoryType | str,
        *,
        source_ref: str = "",
        verification_status: VerificationStatus | str = VerificationStatus.UNVERIFIED,
        confidence_score: float = 1.0,
        project_scope: str = "general",
        tags: list[str] | None = None,
        lifecycle_status: LifecycleStatus | str = LifecycleStatus.ACTIVE,
        metadata: dict[str, Any] | None = None,
        memory_id: str | None = None,
    ) -> MemoryRecord:
        if not content or not content.strip():
            raise ValueError("Memory content must not be empty")
        if not 0.0 <= confidence_score <= 1.0:
            raise ValueError("confidence_score must be between 0.0 and 1.0")

        m_type = memory_type.value if isinstance(memory_type, MemoryType) else str(memory_type)
        v_status = verification_status.value if isinstance(verification_status, VerificationStatus) else str(verification_status)
        l_status = lifecycle_status.value if isinstance(lifecycle_status, LifecycleStatus) else str(lifecycle_status)

        rec_id = memory_id or str(uuid.uuid4())
        safe_content = redact_text(content.strip())
        safe_source = redact_text(source_ref.strip())
        safe_project = redact_text(project_scope.strip()) or "general"
        clean_tags = [redact_text(t.strip()) for t in (tags or []) if t and t.strip()]
        safe_tags_json = json.dumps(clean_tags, ensure_ascii=False)
        safe_metadata_json = json.dumps(redact_value(metadata or {}), ensure_ascii=False)
        now_ts = self._now()

        with self._lock, self._connection:
            self._connection.execute(
                """
                INSERT INTO memories (
                    id, memory_type, content, source_ref, verification_status,
                    confidence_score, project_scope, tags_json, lifecycle_status,
                    version, superseded_by, created_at_utc, updated_at_utc, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, NULL, ?, ?, ?)
                """,
                (
                    rec_id,
                    m_type,
                    safe_content,
                    safe_source,
                    v_status,
                    confidence_score,
                    safe_project,
                    safe_tags_json,
                    l_status,
                    now_ts,
                    now_ts,
                    safe_metadata_json,
                ),
            )
        return self.get_memory(rec_id)  # type: ignore[return-value]

    def get_memory(self, memory_id: str) -> MemoryRecord | None:
        if not memory_id or not memory_id.strip():
            return None
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM memories WHERE id = ?",
                (memory_id.strip(),),
            ).fetchone()
        if row is None:
            return None
        return MemoryRecord.from_row(row)

    def search_memories(
        self,
        query: str = "",
        *,
        memory_type: MemoryType | str | None = None,
        verification_status: VerificationStatus | str | None = None,
        project_scope: str | None = None,
        tag: str | None = None,
        lifecycle_status: LifecycleStatus | str | None = "active",
        limit: int = 50,
    ) -> list[MemoryRecord]:
        if not 1 <= limit <= 500:
            raise ValueError("limit must be between 1 and 500")

        clauses: list[str] = []
        params: list[Any] = []

        if query and query.strip():
            clauses.append("content LIKE ?")
            params.append(f"%{query.strip()}%")

        if memory_type is not None:
            m_val = memory_type.value if isinstance(memory_type, MemoryType) else str(memory_type)
            clauses.append("memory_type = ?")
            params.append(m_val)

        if verification_status is not None:
            v_val = verification_status.value if isinstance(verification_status, VerificationStatus) else str(verification_status)
            clauses.append("verification_status = ?")
            params.append(v_val)

        if project_scope is not None:
            clauses.append("project_scope = ?")
            params.append(str(project_scope))

        if tag is not None and tag.strip():
            clauses.append("tags_json LIKE ?")
            params.append(f'%"{tag.strip()}"%')

        if lifecycle_status is not None:
            l_val = lifecycle_status.value if isinstance(lifecycle_status, LifecycleStatus) else str(lifecycle_status)
            clauses.append("lifecycle_status = ?")
            params.append(l_val)

        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = f"SELECT * FROM memories {where_sql} ORDER BY created_at_utc DESC LIMIT ?"
        params.append(limit)

        with self._lock:
            rows = self._connection.execute(sql, params).fetchall()

        return [MemoryRecord.from_row(row) for row in rows]

    def supersede_memory(
        self,
        old_memory_id: str,
        new_content: str,
        *,
        source_ref: str = "",
        verification_status: VerificationStatus | str | None = None,
        confidence_score: float | None = None,
        project_scope: str | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryRecord:
        if not new_content or not new_content.strip():
            raise ValueError("New memory content must not be empty")

        with self._lock, self._connection:
            old_row = self._connection.execute(
                "SELECT * FROM memories WHERE id = ?",
                (old_memory_id,),
            ).fetchone()
            if old_row is None:
                raise KeyError(f"Memory record '{old_memory_id}' not found")
            old = MemoryRecord.from_row(old_row)
            if old.lifecycle_status == LifecycleStatus.SUPERSEDED.value:
                raise ValueError(f"Memory record '{old_memory_id}' has already been superseded")

            new_id = str(uuid.uuid4())
            new_version = old.version + 1
            now_ts = self._now()

            m_type = old.memory_type
            v_status = (
                verification_status.value
                if isinstance(verification_status, VerificationStatus)
                else (str(verification_status) if verification_status is not None else old.verification_status)
            )
            c_score = confidence_score if confidence_score is not None else old.confidence_score
            p_scope = project_scope if project_scope is not None else old.project_scope
            new_tags = tags if tags is not None else old.tags
            new_meta = metadata if metadata is not None else old.metadata

            safe_content = redact_text(new_content.strip())
            safe_source = redact_text(source_ref.strip()) or old.source_ref
            safe_tags_json = json.dumps([redact_text(t) for t in new_tags], ensure_ascii=False)
            safe_meta_json = json.dumps(redact_value(new_meta), ensure_ascii=False)

            self._connection.execute(
                """
                INSERT INTO memories (
                    id, memory_type, content, source_ref, verification_status,
                    confidence_score, project_scope, tags_json, lifecycle_status,
                    version, superseded_by, created_at_utc, updated_at_utc, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, NULL, ?, ?, ?)
                """,
                (
                    new_id,
                    m_type,
                    safe_content,
                    safe_source,
                    v_status,
                    c_score,
                    p_scope,
                    safe_tags_json,
                    new_version,
                    now_ts,
                    now_ts,
                    safe_meta_json,
                ),
            )

            self._connection.execute(
                "UPDATE memories SET lifecycle_status = 'superseded', superseded_by = ?, updated_at_utc = ? WHERE id = ?",
                (new_id, now_ts, old_memory_id),
            )

        return self.get_memory(new_id)  # type: ignore[return-value]

    def archive_memory(self, memory_id: str) -> None:
        now_ts = self._now()
        with self._lock, self._connection:
            cur = self._connection.execute(
                "UPDATE memories SET lifecycle_status = 'archived', updated_at_utc = ? WHERE id = ?",
                (now_ts, memory_id),
            )
            if cur.rowcount == 0:
                raise KeyError(f"Memory record '{memory_id}' not found")

    def record_task_result(
        self,
        task_id: str,
        goal: str,
        result: str,
        status: str = "completed",
        metadata: dict[str, Any] | None = None,
    ) -> MemoryRecord:
        meta = metadata or {}
        meta["task_id"] = task_id
        meta["task_status"] = status
        content = f"Task [{task_id}]: {goal}\nStatus: {status}\nResult: {result}"
        self.add_episode(
            summary=f"Task [{task_id}]: {goal} -> {status}",
            kind="task",
            source_ref=f"task:{task_id}",
            status=status,
            metadata=meta,
        )
        return self.store_memory(
            content=content,
            memory_type=MemoryType.EPISODIC,
            source_ref=f"task:{task_id}",
            verification_status=VerificationStatus.OBSERVED,
            confidence_score=1.0,
            tags=["task", status],
            metadata=meta,
        )

    def quarantine_candidate_knowledge(
        self,
        statement: str,
        source_ref: str,
        rationale: str = "",
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryRecord:
        if not statement or not statement.strip():
            raise ValueError("Candidate statement must not be empty")
        if not source_ref or not source_ref.strip():
            raise ValueError("Candidate knowledge requires a source reference")

        cand_id = self.add_candidate(statement, source_ref, rationale)

        meta = metadata or {}
        meta["rationale"] = rationale
        meta["candidate_id"] = cand_id

        all_tags = list(tags or [])
        if "candidate" not in all_tags:
            all_tags.append("candidate")
        if "quarantined" not in all_tags:
            all_tags.append("quarantined")

        return self.store_memory(
            content=statement,
            memory_type=MemoryType.CANDIDATE,
            source_ref=source_ref,
            verification_status=VerificationStatus.CANDIDATE,
            confidence_score=0.5,
            tags=all_tags,
            lifecycle_status=LifecycleStatus.QUARANTINED,
            metadata=meta,
            memory_id=cand_id,
        )

    def trace_source(self, memory_id: str) -> dict[str, Any]:
        record = self.get_memory(memory_id)
        if record is None:
            raise KeyError(f"Memory record '{memory_id}' not found")

        history: list[dict[str, Any]] = []
        curr_id: str | None = memory_id
        while curr_id:
            with self._lock:
                pred_row = self._connection.execute(
                    "SELECT * FROM memories WHERE superseded_by = ?",
                    (curr_id,),
                ).fetchone()
            if pred_row:
                pred_rec = MemoryRecord.from_row(pred_row)
                history.append(pred_rec.to_dict())
                curr_id = pred_rec.id
            else:
                curr_id = None

        return {
            "memory_id": record.id,
            "memory_type": record.memory_type,
            "verification_status": record.verification_status,
            "source_ref": record.source_ref,
            "version": record.version,
            "lifecycle_status": record.lifecycle_status,
            "created_at_utc": record.created_at_utc,
            "updated_at_utc": record.updated_at_utc,
            "predecessor_count": len(history),
            "predecessors": history,
            "record": record.to_dict(),
        }


    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def __enter__(self) -> "MemoryStore":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()
