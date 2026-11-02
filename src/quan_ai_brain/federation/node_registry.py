"""SEC-S2 (a): Sổ cái Nút Liên bang — PC lõi + Pi5 + đầu nối cloud.

Owner 02/11/2026: "PC toàn quyền điều khiển, xử lý, khống chế" — mọi nút
(Pi5, thiết bị, connector cloud) đều ĐĂNG KÝ vào lõi này trước khi lõi điều
khiển. Lõi probe (ping) định kỳ qua watchdog → status REACHABLE/UNREACHABLE.

Fail-honest: nút không phản hồi → UNREACHABLE + ghi nhật ký, không bịa trạng thái.
SQLite data/federation_nodes.db, schema idempotent, chuẩn TodoStore/contracts.
"""
from __future__ import annotations

import json
import sqlite3
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_DB = Path(__file__).resolve().parents[2] / "data" / "federation_nodes.db"

NODE_KINDS = ("PC", "EDGE", "CONNECTOR")
NODE_STATUSES = ("UNKNOWN", "REACHABLE", "UNREACHABLE")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class FedNode:
    node_id: str
    kind: str                 # PC | EDGE | CONNECTOR
    host: str                 # IP/hostname (connector: domain)
    label: str = ""
    capabilities: list[str] = field(default_factory=list)
    status: str = "UNKNOWN"
    last_probe_at: str = ""
    last_seen_at: str = ""
    registered_at: str = ""
    # connector only
    daily_cap: int = 0
    calls_today: int = 0
    calls_date: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id, "kind": self.kind, "host": self.host,
            "label": self.label, "capabilities": list(self.capabilities),
            "status": self.status, "last_probe_at": self.last_probe_at,
            "last_seen_at": self.last_seen_at, "daily_cap": self.daily_cap,
            "calls_today": self.calls_today,
        }


class NodeRegistry:
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
                CREATE TABLE IF NOT EXISTS federation_nodes (
                    node_id TEXT PRIMARY KEY,
                    kind TEXT NOT NULL,
                    host TEXT NOT NULL,
                    label TEXT NOT NULL DEFAULT '',
                    capabilities_json TEXT NOT NULL DEFAULT '[]',
                    status TEXT NOT NULL DEFAULT 'UNKNOWN',
                    last_probe_at TEXT NOT NULL DEFAULT '',
                    last_seen_at TEXT NOT NULL DEFAULT '',
                    registered_at TEXT NOT NULL,
                    daily_cap INTEGER NOT NULL DEFAULT 0,
                    calls_today INTEGER NOT NULL DEFAULT 0,
                    calls_date TEXT NOT NULL DEFAULT ''
                )
                """
            )

    # ------------------------------------------------------------------
    # Đăng ký / đọc / xóa
    # ------------------------------------------------------------------
    def register(
        self,
        kind: str,
        host: str,
        *,
        node_id: str = "",
        label: str = "",
        capabilities: list[str] | None = None,
        daily_cap: int = 0,
    ) -> FedNode:
        if kind not in NODE_KINDS:
            raise ValueError(f"Loại nút không hợp lệ: {kind} (cho phép: {NODE_KINDS})")
        host = (host or "").strip()
        if not host:
            raise ValueError("Thiếu host — fail-honest")
        nid = node_id.strip() or f"{kind.lower()}_{host.replace('.', '_')}"
        now = _now_iso()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO federation_nodes
                    (node_id, kind, host, label, capabilities_json, status,
                     last_probe_at, last_seen_at, registered_at, daily_cap,
                     calls_today, calls_date)
                VALUES (?,?,?,?,?,?,?,?,?,?,0,'')
                ON CONFLICT(node_id) DO UPDATE SET
                    kind=excluded.kind, host=excluded.host, label=excluded.label,
                    capabilities_json=excluded.capabilities_json,
                    daily_cap=excluded.daily_cap
                """,
                (nid, kind, host, label,
                 json.dumps(capabilities or [], ensure_ascii=False),
                 "UNKNOWN", "", "", now, int(daily_cap)),
            )
        return self.get(nid)  # type: ignore[return-value]

    def get(self, node_id: str) -> FedNode | None:
        with self._connect() as conn:
            r = conn.execute(
                "SELECT * FROM federation_nodes WHERE node_id = ?", (node_id,)
            ).fetchone()
        return self._row_to_node(r) if r else None

    def list_nodes(self, kind: str | None = None) -> list[FedNode]:
        with self._connect() as conn:
            if kind:
                rows = conn.execute(
                    "SELECT * FROM federation_nodes WHERE kind = ? ORDER BY registered_at",
                    (kind,)).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM federation_nodes ORDER BY registered_at").fetchall()
        return [self._row_to_node(r) for r in rows]

    def remove(self, node_id: str) -> bool:
        with self._connect() as conn:
            cur = conn.execute(
                "DELETE FROM federation_nodes WHERE node_id = ?", (node_id,)
            )
            return cur.rowcount > 0

    # ------------------------------------------------------------------
    # Probe (ping thật qua subprocess, stdlib)
    # ------------------------------------------------------------------
    @staticmethod
    def ping_host(host: str, timeout_ms: int = 1200) -> bool:
        """Ping 1 lần; 'TTL=' trong output = có reply (heuristic đa ngôn ngữ)."""
        try:
            r = subprocess.run(
                ["ping", "-n", "1", "-w", str(timeout_ms), host],
                capture_output=True, text=True, timeout=5,
                encoding="utf-8", errors="replace",
            )
            return "ttl=" in (r.stdout or "").lower()
        except Exception:
            return False

    def probe_node(self, node_id: str) -> dict[str, Any]:
        node = self.get(node_id)
        if node is None:
            return {"success": False, "error": "node không tồn tại"}
        if node.kind == "CONNECTOR":
            return {"success": False,
                    "error": "connector không probe bằng ping (dùng kênh riêng của nó)"}
        alive = self.ping_host(node.host)
        prev = node.status
        new_status = "REACHABLE" if alive else "UNREACHABLE"
        with self._connect() as conn:
            conn.execute(
                "UPDATE federation_nodes SET status = ?, last_probe_at = ?, "
                "last_seen_at = CASE WHEN ? = 'REACHABLE' THEN ? ELSE last_seen_at END "
                "WHERE node_id = ?",
                (new_status, _now_iso(), new_status, _now_iso(), node_id),
            )
        return {
            "success": True, "node_id": node_id, "host": node.host,
            "status": new_status, "previous_status": prev,
            "changed": prev != new_status,
        }

    def probe_all(self) -> list[dict[str, Any]]:
        return [self.probe_node(n.node_id) for n in self.list_nodes()
                if n.kind in ("PC", "EDGE")]

    @staticmethod
    def _row_to_node(r: sqlite3.Row) -> FedNode:
        return FedNode(
            node_id=r["node_id"], kind=r["kind"], host=r["host"], label=r["label"],
            capabilities=json.loads(r["capabilities_json"]),
            status=r["status"], last_probe_at=r["last_probe_at"],
            last_seen_at=r["last_seen_at"], registered_at=r["registered_at"],
            daily_cap=int(r["daily_cap"]), calls_today=int(r["calls_today"]),
            calls_date=r["calls_date"],
        )
