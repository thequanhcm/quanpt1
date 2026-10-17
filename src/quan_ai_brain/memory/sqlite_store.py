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

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def __enter__(self) -> "MemoryStore":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()
