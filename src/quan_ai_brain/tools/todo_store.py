"""Sprint 8 (a): To-do store — việc cần làm cá nhân của owner.

SQLite data/todos.db, schema tự khởi tạo, fail-closed (lỗi → trả list rỗng
hoặc raise có thông điệp rõ). KHÔNG gửi dữ liệu ra ngoài.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_DB = Path(__file__).resolve().parents[2] / "data" / "todos.db"


class TodoStore:
    def __init__(self, db_path: str | Path = DEFAULT_DB) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout = 5000")
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS todos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    due TEXT DEFAULT '',
                    priority TEXT DEFAULT 'normal',
                    status TEXT NOT NULL DEFAULT 'open',
                    created_at TEXT NOT NULL,
                    done_at TEXT DEFAULT ''
                )
                """
            )

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def add(self, title: str, due: str = "", priority: str = "normal") -> dict[str, Any]:
        if not title or not title.strip():
            raise ValueError("title trống — không thêm việc rỗng")
        priority = priority if priority in ("low", "normal", "high") else "normal"
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO todos (title, due, priority, created_at) VALUES (?,?,?,?)",
                (title.strip(), due, priority, self._now()),
            )
            row = conn.execute("SELECT * FROM todos WHERE id=?", (cur.lastrowid,)).fetchone()
        return dict(row)

    def list_open(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM todos WHERE status='open' ORDER BY due ASC, id DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    def mark_done(self, todo_id: int) -> bool:
        with self._connect() as conn:
            cur = conn.execute(
                "UPDATE todos SET status='done', done_at=? WHERE id=? AND status='open'",
                (self._now(), todo_id),
            )
            return cur.rowcount > 0

    # ------------------------------------------------------------------
    # Báo cáo sáng
    # ------------------------------------------------------------------

    def overdue_and_today(self, today: str | None = None) -> dict[str, list[dict[str, Any]]]:
        """Việc quá hạn (due < today) + việc đến hạn hôm nay. today='YYYY-MM-DD'."""
        if today is None:
            today = datetime.now().strftime("%Y-%m-%d")
        result: dict[str, list[dict[str, Any]]] = {"overdue": [], "today": []}
        for t in self.list_open():
            due = (t.get("due") or "").strip()
            if not due:
                continue
            if due < today:
                result["overdue"].append(t)
            elif due == today:
                result["today"].append(t)
        return result
