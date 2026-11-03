"""SENTINEL-S3: Hệ phản ứng 5 cấp (L0-L4) — chuyển trạng thái có bằng chứng + audit.

Master prompt v1.0 mục 4: L0 NORMAL → L4 CRITICAL INCIDENT. Nguyên tắc:
- Mọi chuyển cấp PHẢI có reason + evidence_ref; ghi lịch sử append-only + audit.
- L4 = quy trình ứng cứu: bảo toàn bằng chứng + thông báo owner (callback) —
  KHÔNG phải nút tự ý tung quyền mới.
- HẠ cấp từ L4 (về L0/L1) CHỈ owner — SENTINEL không tự xóa sự cố.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ThreatLevelMachine:
    """SQLite data/sentinel_threat_levels.db — state machine append-only."""

    L0 = "L0_NORMAL"
    L1 = "L1_WARNING"
    L2 = "L2_RESTRICT"
    L3 = "L3_CONTAINMENT"
    L4 = "L4_CRITICAL"
    LEVELS = (L0, L1, L2, L3, L4)

    # Hành động tự động được phép ở từng cấp (prompt mục 6 governance)
    AUTO_ALLOWED = {
        L0: frozenset({"ANALYZE", "MONITOR"}),
        L1: frozenset({"ANALYZE", "MONITOR", "ALERT"}),
        L2: frozenset({"ANALYZE", "MONITOR", "ALERT", "RESTRICT"}),
        # L3 contain: chỉ trong phạm vi ĐÃ phê duyệt trước (hợp đồng auto_contain
        # hoặc approval card) — orchestration nằm ở containment.py, không tự tung.
        L3: frozenset({"ANALYZE", "MONITOR", "ALERT", "RESTRICT", "CONTAIN_PREAPPROVED"}),
        L4: frozenset({"ANALYZE", "MONITOR", "ALERT", "PRESERVE_EVIDENCE", "NOTIFY_OWNER"}),
    }

    def __init__(self, db_path: str | Any,
                 notify_owner: Callable[[str], None] | None = None) -> None:
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.notify_owner = notify_owner
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS threat_level_state (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    current_level TEXT NOT NULL,
                    since_at TEXT NOT NULL,
                    reason TEXT NOT NULL DEFAULT 'khởi tạo'
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS threat_level_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    from_level TEXT NOT NULL,
                    to_level TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    evidence_ref TEXT NOT NULL DEFAULT '',
                    by TEXT NOT NULL,
                    at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "INSERT OR IGNORE INTO threat_level_state (id, current_level, since_at, reason)"
                " VALUES (1, ?, ?, 'khởi tạo SENTINEL')", (self.L0, _now()),
            )

    # ------------------------------------------------------------------
    def current_level(self) -> str:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT current_level FROM threat_level_state WHERE id=1").fetchone()
            return row["current_level"] if row else self.L0

    def history(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM threat_level_history ORDER BY id DESC LIMIT ?",
                (limit,)).fetchall()
            return [dict(r) for r in rows]

    def set_level(self, to_level: str, *, reason: str, by: str,
                  evidence_ref: str = "") -> dict[str, Any]:
        """Chuyển cấp. Fail-closed:
        - level phải hợp lệ; reason bắt buộc.
        - L4: nếu notify_owner có sẵn → gọi (quy trình ứng cứu).
        - HẠ từ L4: CHỈ owner (SENTINEL không tự xóa sự cố).
        - SENTINEL (không phải owner) không được TỰ set L3/L4 không bằng chứng:
          bắt buộc evidence_ref.
        """
        if to_level not in self.LEVELS:
            # chấp nhận dạng ngắn L0..L4 (từ DM) → map sang tên đầy đủ
            short_map = {f"L{i}": full for i, full in enumerate(self.LEVELS)}
            to_level = short_map.get(to_level.upper(), to_level)
            if to_level not in self.LEVELS:
                raise ValueError(f"Cấp không hợp lệ: {to_level}")
        if not reason or not reason.strip():
            raise ValueError("Chuyển cấp phải có reason")
        is_owner = by.strip().lower() in ("owner", "quanpt1", "owner_dm")
        if not is_owner and not evidence_ref:
            raise PermissionError(
                "SENTINEL không được tự chuyển cấp L2+ không bằng chứng "
                "(evidence_ref bắt buộc).")
        if not is_owner and to_level == self.L4 and not evidence_ref:
            raise PermissionError("L4 không evidence_ref bị từ chối.")
        from_level = self.current_level()
        if from_level == self.L4 and to_level != self.L4 and not is_owner:
            raise PermissionError(
                "HẠ cấp từ L4 chỉ owner — SENTINEL không tự xóa sự cố.")
        at = _now()
        with self._connect() as conn:
            conn.execute(
                "UPDATE threat_level_state SET current_level=?, since_at=?, reason=?"
                " WHERE id=1", (to_level, at, reason))
            conn.execute(
                "INSERT INTO threat_level_history (from_level, to_level, reason,"
                " evidence_ref, by, at) VALUES (?,?,?,?,?,?)",
                (from_level, to_level, reason, evidence_ref, by, at))
        if to_level == self.L4 and self.notify_owner is not None:
            try:
                self.notify_owner(
                    f"🚨 **SENTINEL L4 CRITICAL INCIDENT** — {reason} (bằng chứng: {evidence_ref})")
            except Exception:
                pass  # DM hỏng không được giết state machine
        return {"from": from_level, "to": to_level, "reason": reason,
                "evidence_ref": evidence_ref, "by": by, "at": at}
