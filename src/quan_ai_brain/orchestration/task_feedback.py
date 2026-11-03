"""DEOM M6 — TaskFeedbackRecorder: kinh nghiệm sau mỗi task (GAP #14, DEOM §11).

Thiết kế: reports/DEOM_M6_DESIGN.md §3. Nguyên tắc:
- Sau mỗi task terminal → bản ghi feedback + lesson (trong data/task_feedback.db).
- Lesson LUÔN là candidate (verification_status='candidate') — KHÔNG BAO GIỜ
  tự promote thành fact (đường promote là Q-4: verifier + owner).
- Idempotent: (task_id, attempt) trùng → bỏ qua.
- Feedback lỗi (DB sai...) KHÔNG BAO GIỜ giết task (caller dùng safe wrapper).
"""
from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from quan_ai_brain.core.redaction import redact_text
from quan_ai_brain.orchestration.models import TaskRecord, TaskStatus

_TERMINAL_OK = (TaskStatus.COMPLETED, TaskStatus.COMPLETED_VERIFIED, TaskStatus.COMPLETED_UNVERIFIED)
_TERMINAL_BAD = (TaskStatus.FAILED, TaskStatus.CANCELLED)
_TERMINAL_ALL = _TERMINAL_OK + _TERMINAL_BAD + (TaskStatus.BLOCKED,)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class TaskFeedbackRecorder:
    """Ghi kinh nghiệm sau task — lessons luôn ở mức candidate."""

    def __init__(self, db_path: str | Path = "data/task_feedback.db") -> None:
        self.db_path = Path(db_path)
        if str(self.db_path) != ":memory:":
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS task_feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    attempt INTEGER NOT NULL DEFAULT 1,
                    outcome TEXT NOT NULL,
                    duration_sec REAL,
                    retry_count INTEGER,
                    risk_level TEXT,
                    source TEXT,
                    agent TEXT,
                    error_summary TEXT,
                    recorded_at_utc TEXT NOT NULL,
                    UNIQUE(task_id, attempt)
                )
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS task_lessons (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    lesson TEXT NOT NULL,
                    kind TEXT NOT NULL,             -- success_pattern | failure_cause
                    verification_status TEXT NOT NULL DEFAULT 'candidate',
                    created_at_utc TEXT NOT NULL,
                    promoted_at_utc TEXT
                )
                """
            )

    # ------------------------------------------------------------------
    def record_feedback(self, task: TaskRecord) -> dict[str, Any] | None:
        """Ghi feedback 1 task (đã terminal). Trả dict tổng kết hoặc None nếu bỏ qua.

        - task chưa terminal → None (không ghi).
        - (task_id, attempt) đã ghi → None (idempotent).
        """
        if task.status not in _TERMINAL_ALL:
            return None
        attempt = int(task.retry_count or 0) + 1
        duration_sec: float | None = None
        try:
            if task.completed_at_utc:
                t0 = datetime.fromisoformat(task.created_at_utc)
                t1 = datetime.fromisoformat(task.completed_at_utc)
                duration_sec = (t1 - t0).total_seconds()
        except (ValueError, TypeError):
            duration_sec = None

        outcome = task.status.value
        error_summary = redact_text(task.error_message)[:300] if task.error_message else None
        agent = ",".join(task.assigned_agents) if task.assigned_agents else None

        with self._lock, self._conn:
            try:
                self._conn.execute(
                    """
                    INSERT INTO task_feedback (
                        task_id, attempt, outcome, duration_sec, retry_count,
                        risk_level, source, agent, error_summary, recorded_at_utc
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        task.task_id, attempt, outcome, duration_sec,
                        task.retry_count, task.risk_level, task.source,
                        agent, error_summary, _now(),
                    ),
                )
            except sqlite3.IntegrityError:
                return None  # đã ghi rồi (idempotent)

            # Lesson: luôn candidate — tự promote là cấm (Q-4)
            lesson = self._lesson_from(task, outcome, error_summary)
            if lesson:
                kind = "success_pattern" if outcome.startswith("COMPLETED") else "failure_cause"
                self._conn.execute(
                    """
                    INSERT INTO task_lessons (task_id, lesson, kind, verification_status, created_at_utc)
                    VALUES (?, ?, ?, 'candidate', ?)
                    """,
                    (task.task_id, redact_text(lesson)[:500], kind, _now()),
                )
            self._conn.commit()

        return {
            "task_id": task.task_id,
            "attempt": attempt,
            "outcome": outcome,
            "duration_sec": duration_sec,
            "lesson_created": bool(lesson),
        }

    # ------------------------------------------------------------------
    def _lesson_from(self, task: TaskRecord, outcome: str, error_summary: str | None) -> str | None:
        if outcome.startswith("COMPLETED_VERIFIED"):
            return (
                f"Task '{task.goal[:80]}' hoàn tất có xác minh (risk {task.risk_level}, "
                f"retry {task.retry_count}) — quy trình này lặp lại được cho mục tiêu tương tự."
            )
        if outcome == TaskStatus.COMPLETED.value:
            return (
                f"Task '{task.goal[:80]}' hoàn tất KHÔNG qua xác minh — nên kiểm chứng "
                f"bằng evidence trước khi tái sử dụng quy trình."
            )
        if outcome == TaskStatus.FAILED.value and error_summary:
            return (
                f"Task '{task.goal[:80]}' thất bại (risk {task.risk_level}): {error_summary[:200]} — "
                f"cần xử lý nguyên nhân này trước khi thử lại."
            )
        if outcome == TaskStatus.CANCELLED.value:
            return f"Task '{task.goal[:80]}' bị hủy — ghi nhận ngữ cảnh để tránh lặp lại yêu cầu tương tự."
        if outcome == TaskStatus.BLOCKED.value and error_summary:
            return f"Task '{task.goal[:80]}' bị chặn: {error_summary[:200]}"
        return None

    # ------------------------------------------------------------------
    def lessons_for(self, task_id: str) -> list[dict[str, Any]]:
        with self._lock, self._conn:
            rows = self._conn.execute(
                "SELECT lesson, kind, verification_status, created_at_utc FROM task_lessons WHERE task_id = ? ORDER BY id",
                (task_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def stats(self) -> dict[str, int]:
        with self._lock, self._conn:
            fb = self._conn.execute("SELECT COUNT(*) AS n FROM task_feedback").fetchone()["n"]
            ls = self._conn.execute("SELECT COUNT(*) AS n FROM task_lessons").fetchone()["n"]
        return {"feedback": fb, "lessons": ls}

    def close(self) -> None:
        self._conn.close()


def safe_record_feedback(recorder: TaskFeedbackRecorder | None, task: TaskRecord) -> dict[str, Any] | None:
    """Wrapper an toàn: feedback lỗi KHÔNG BAO GIỜ giết task (fail-honest log)."""
    if recorder is None:
        return None
    try:
        return recorder.record_feedback(task)
    except Exception as exc:  # noqa: BLE001 — cố ý: feedback phải không nguy hiểm
        return {"error": f"feedback_failed:{type(exc).__name__}:{exc}"[:200]}
