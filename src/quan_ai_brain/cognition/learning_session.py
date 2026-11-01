"""Learning Session Manager — CLO V1.

Manages individual learning sessions with state machine, checkpointing, and continuous handoff.

Session lifecycle:
  DISABLED → INITIALIZING → PLANNING → RUNNING → EVALUATING → CONSOLIDATING → HANDOFF
                                                                      ↓
  STOPPED ← STOPPING ← (STOP_REQUEST) ← RUNNING/EVALUATING/CONSOLIDATING
                              ↓
                        PAUSED ← (PAUSE_REQUEST)

Each session:
- session_id (UUID)
- cycle_number (int, auto-increment)
- started_at, ended_at (ISO8601)
- status (LearningSessionStatus)
- learning_objectives (list[str])
- source_manifest (dict)
- tasks_completed, tasks_failed (list[str])
- evidence_refs (list[str])
- knowledge_candidates (list[dict])
- evaluation_result (dict)
- unresolved_questions (list[str])
- resource_usage (dict)
- checkpoint_ref (str, path to checkpoint file)
- next_session_plan (dict, plan for session N+1)
- stop_or_pause_reason (str, if applicable)
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


class LearningSessionStatus(str, Enum):
    """Session lifecycle status."""
    DISABLED = "DISABLED"
    INITIALIZING = "INITIALIZING"
    PLANNING = "PLANNING"
    RUNNING = "RUNNING"
    EVALUATING = "EVALUATING"
    CONSOLIDATING = "CONSOLIDATING"
    HANDOFF = "HANDOFF"
    PAUSED = "PAUSED"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"
    FAILED = "FAILED"
    INTERRUPTED = "INTERRUPTED"


@dataclass
class LearningSession:
    """A single learning session record."""
    session_id: str
    cycle_number: int
    started_at: str
    ended_at: str | None
    status: LearningSessionStatus
    learning_objectives: list[str] = field(default_factory=list)
    source_manifest: dict[str, Any] = field(default_factory=dict)
    tasks_completed: list[str] = field(default_factory=list)
    tasks_failed: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    knowledge_candidates: list[dict[str, Any]] = field(default_factory=list)
    evaluation_result: dict[str, Any] = field(default_factory=dict)
    unresolved_questions: list[str] = field(default_factory=list)
    resource_usage: dict[str, float] = field(default_factory=dict)
    checkpoint_ref: str | None = None
    next_session_plan: dict[str, Any] = field(default_factory=dict)
    stop_or_pause_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict."""
        d = asdict(self)
        d['status'] = self.status.value
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LearningSession:
        """Deserialize from dict."""
        data['status'] = LearningSessionStatus(data['status'])
        return cls(**data)


class LearningSessionManager:
    """Manages learning sessions with persistent state."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Create tables if not exist."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS learning_sessions (
                    session_id TEXT PRIMARY KEY,
                    cycle_number INTEGER UNIQUE NOT NULL,
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    status TEXT NOT NULL,
                    learning_objectives TEXT NOT NULL,
                    source_manifest TEXT NOT NULL,
                    tasks_completed TEXT NOT NULL,
                    tasks_failed TEXT NOT NULL,
                    evidence_refs TEXT NOT NULL,
                    knowledge_candidates TEXT NOT NULL,
                    evaluation_result TEXT NOT NULL,
                    unresolved_questions TEXT NOT NULL,
                    resource_usage TEXT NOT NULL,
                    checkpoint_ref TEXT,
                    next_session_plan TEXT NOT NULL,
                    stop_or_pause_reason TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS learning_state (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)
            conn.commit()

    def _serialize(self, obj: Any) -> str:
        """Serialize object to JSON string."""
        return json.dumps(obj, ensure_ascii=False, default=str)

    def _deserialize(self, s: str) -> Any:
        """Deserialize JSON string to object."""
        return json.loads(s) if s else None

    def get_current_session(self) -> LearningSession | None:
        """Get the most recent session (by cycle_number)."""
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute(
                "SELECT * FROM learning_sessions ORDER BY cycle_number DESC LIMIT 1"
            )
            row = cursor.fetchone()
            if not row:
                return None
            columns = [desc[0] for desc in cursor.description]
            data = dict(zip(columns, row))
            data['learning_objectives'] = self._deserialize(data['learning_objectives'])
            data['source_manifest'] = self._deserialize(data['source_manifest'])
            data['tasks_completed'] = self._deserialize(data['tasks_completed'])
            data['tasks_failed'] = self._deserialize(data['tasks_failed'])
            data['evidence_refs'] = self._deserialize(data['evidence_refs'])
            data['knowledge_candidates'] = self._deserialize(data['knowledge_candidates'])
            data['evaluation_result'] = self._deserialize(data['evaluation_result'])
            data['unresolved_questions'] = self._deserialize(data['unresolved_questions'])
            data['resource_usage'] = self._deserialize(data['resource_usage'])
            data['next_session_plan'] = self._deserialize(data['next_session_plan'])
            return LearningSession.from_dict(data)

    def get_session_by_id(self, session_id: str) -> LearningSession | None:
        """Get session by ID."""
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute(
                "SELECT * FROM learning_sessions WHERE session_id = ?", (session_id,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            columns = [desc[0] for desc in cursor.description]
            data = dict(zip(columns, row))
            data['learning_objectives'] = self._deserialize(data['learning_objectives'])
            data['source_manifest'] = self._deserialize(data['source_manifest'])
            data['tasks_completed'] = self._deserialize(data['tasks_completed'])
            data['tasks_failed'] = self._deserialize(data['tasks_failed'])
            data['evidence_refs'] = self._deserialize(data['evidence_refs'])
            data['knowledge_candidates'] = self._deserialize(data['knowledge_candidates'])
            data['evaluation_result'] = self._deserialize(data['evaluation_result'])
            data['unresolved_questions'] = self._deserialize(data['unresolved_questions'])
            data['resource_usage'] = self._deserialize(data['resource_usage'])
            data['next_session_plan'] = self._deserialize(data['next_session_plan'])
            return LearningSession.from_dict(data)

    def create_session(self, objectives: list[str], source_manifest: dict[str, Any]) -> LearningSession:
        """Create a new session (cycle_number = previous + 1)."""
        current = self.get_current_session()
        cycle_number = (current.cycle_number + 1) if current else 1

        session = LearningSession(
            session_id=str(uuid.uuid4()),
            cycle_number=cycle_number,
            started_at=datetime.now(timezone.utc).isoformat(),
            ended_at=None,
            status=LearningSessionStatus.INITIALIZING,
            learning_objectives=objectives,
            source_manifest=source_manifest,
        )

        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                INSERT INTO learning_sessions (
                    session_id, cycle_number, started_at, ended_at, status,
                    learning_objectives, source_manifest, tasks_completed, tasks_failed,
                    evidence_refs, knowledge_candidates, evaluation_result,
                    unresolved_questions, resource_usage, checkpoint_ref,
                    next_session_plan, stop_or_pause_reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session.session_id, session.cycle_number, session.started_at,
                session.ended_at, session.status.value,
                self._serialize(session.learning_objectives),
                self._serialize(session.source_manifest),
                self._serialize(session.tasks_completed),
                self._serialize(session.tasks_failed),
                self._serialize(session.evidence_refs),
                self._serialize(session.knowledge_candidates),
                self._serialize(session.evaluation_result),
                self._serialize(session.unresolved_questions),
                self._serialize(session.resource_usage),
                session.checkpoint_ref,
                self._serialize(session.next_session_plan),
                session.stop_or_pause_reason,
            ))
            conn.commit()

        return session

    def update_session(self, session: LearningSession):
        """Update session record."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                UPDATE learning_sessions SET
                    ended_at = ?, status = ?, tasks_completed = ?, tasks_failed = ?,
                    evidence_refs = ?, knowledge_candidates = ?, evaluation_result = ?,
                    unresolved_questions = ?, resource_usage = ?, checkpoint_ref = ?,
                    next_session_plan = ?, stop_or_pause_reason = ?
                WHERE session_id = ?
            """, (
                session.ended_at, session.status.value,
                self._serialize(session.tasks_completed),
                self._serialize(session.tasks_failed),
                self._serialize(session.evidence_refs),
                self._serialize(session.knowledge_candidates),
                self._serialize(session.evaluation_result),
                self._serialize(session.unresolved_questions),
                self._serialize(session.resource_usage),
                session.checkpoint_ref,
                self._serialize(session.next_session_plan),
                session.stop_or_pause_reason,
                session.session_id,
            ))
            conn.commit()

    def set_status(self, session_id: str, status: LearningSessionStatus, reason: str | None = None):
        """Update session status."""
        session = self.get_session_by_id(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        session.status = status
        if reason:
            session.stop_or_pause_reason = reason
        self.update_session(session)

    def get_learning_state(self, key: str) -> Any:
        """Get persistent learning state (e.g., CLO_ENABLED, STOP_FLAG)."""
        with sqlite3.connect(str(self.db_path)) as conn:
            row = conn.execute(
                "SELECT value FROM learning_state WHERE key = ?", (key,)
            ).fetchone()
            return self._deserialize(row[0]) if row else None

    def set_learning_state(self, key: str, value: Any):
        """Set persistent learning state."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO learning_state (key, value) VALUES (?, ?)
            """, (key, self._serialize(value)))
            conn.commit()

    def is_clo_enabled(self) -> bool:
        """Check if continuous learning mode is enabled."""
        return self.get_learning_state("CLO_ENABLED") is True

    def enable_clo(self):
        """Enable continuous learning mode."""
        self.set_learning_state("CLO_ENABLED", True)
        self.set_learning_state("CLO_STARTED_AT", datetime.now(timezone.utc).isoformat())

    def disable_clo(self):
        """Disable continuous learning mode."""
        self.set_learning_state("CLO_ENABLED", False)
        self.set_learning_state("CLO_STOPPED_AT", datetime.now(timezone.utc).isoformat())

    def set_stop_flag(self, reason: str):
        """Set persistent stop flag."""
        self.set_learning_state("STOP_FLAG", True)
        self.set_learning_state("STOP_REASON", reason)
        self.set_learning_state("STOPPED_AT", datetime.now(timezone.utc).isoformat())

    def clear_stop_flag(self):
        """Clear stop flag (only after owner explicitly restarts)."""
        self.set_learning_state("STOP_FLAG", False)
        self.set_learning_state("STOP_REASON", None)

    def get_stop_flag(self) -> tuple[bool, str | None]:
        """Get stop flag and reason."""
        enabled = self.get_learning_state("STOP_FLAG") is True
        reason = self.get_learning_state("STOP_REASON")
        return enabled, reason

    def list_sessions(self, limit: int = 10) -> list[LearningSession]:
        """List recent sessions."""
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute(
                "SELECT * FROM learning_sessions ORDER BY cycle_number DESC LIMIT ?",
                (limit,)
            )
            rows = cursor.fetchall()
            sessions = []
            for row in rows:
                columns = [desc[0] for desc in cursor.description]
                data = dict(zip(columns, row))
                data['learning_objectives'] = self._deserialize(data['learning_objectives'])
                data['source_manifest'] = self._deserialize(data['source_manifest'])
                data['tasks_completed'] = self._deserialize(data['tasks_completed'])
                data['tasks_failed'] = self._deserialize(data['tasks_failed'])
                data['evidence_refs'] = self._deserialize(data['evidence_refs'])
                data['knowledge_candidates'] = self._deserialize(data['knowledge_candidates'])
                data['evaluation_result'] = self._deserialize(data['evaluation_result'])
                data['unresolved_questions'] = self._deserialize(data['unresolved_questions'])
                data['resource_usage'] = self._deserialize(data['resource_usage'])
                data['next_session_plan'] = self._deserialize(data['next_session_plan'])
                sessions.append(LearningSession.from_dict(data))
            return sessions