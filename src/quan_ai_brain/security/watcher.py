"""SEC-S1 (b): Vệ sĩ giám sát — quét tiến trình + mạng, so với hợp đồng nhiệm vụ.

Chỉ ĐỌC (an toàn tuyệt đối). Phát hiện vi phạm → trả cấu trúc {violation, pid,
evidence} — KHÔNG tự khống chế; hành động thuộc actions.py + lệnh owner
(riêng auto_contain=True thì watcher/router được phép gọi suspend ngay).

Chiến lược chống noise: chỉ quét SÂU khi CÓ ít nhất 1 hợp đồng ACTIVE — không
có hợp đồng nào thì không có "chuẩn phạm vi" để so, chỉ đếm tổng quan.
"""
from __future__ import annotations

import csv
import io
import json
import re
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from quan_ai_brain.security.task_contracts import TaskContract, TaskContractStore

DEFAULT_DB = Path(__file__).resolve().parents[2] / "data" / "security_events.db"

VIOLATION_TYPES = (
    "UNREGISTERED",        # tiến trình khớp "họ hàng" subject nhưng không còn hợp đồng ACTIVE
    "OUT_OF_SCOPE_PATH",   # cmdline truy cập đường dẫn ngoài allowed_paths
    "OUT_OF_SCOPE_DOMAIN", # cmdline trỏ tới domain ngoài allowed_domains
    "OVER_CONTRACT",       # hợp đồng EXPIRED/SUSPENDED nhưng tiến trình vẫn chạy
    "SUSPICIOUS_NET",      # kết nối mạng lạ từ tiến trình có hợp đồng (ngoài allowed_domains)
)


class SecurityEventStore:
    """Bằng chứng append-only — chỉ INSERT + SELECT, không UPDATE/DELETE."""

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
                CREATE TABLE IF NOT EXISTS security_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts_utc TEXT NOT NULL,
                    violation TEXT NOT NULL,
                    pid INTEGER NOT NULL,
                    process_name TEXT NOT NULL,
                    cmdline TEXT NOT NULL,
                    contract_id TEXT DEFAULT '',
                    evidence_json TEXT NOT NULL DEFAULT '{}',
                    handled TEXT NOT NULL DEFAULT 'PENDING',
                    action_taken TEXT DEFAULT ''
                )
                """
            )

    def record(self, violation: str, pid: int, process_name: str, cmdline: str,
               contract_id: str = "", evidence: dict[str, Any] | None = None,
               handled: str = "PENDING", action_taken: str = "") -> int:
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO security_events (ts_utc, violation, pid, process_name, "
                "cmdline, contract_id, evidence_json, handled, action_taken) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (datetime.now(timezone.utc).isoformat(), violation, int(pid),
                 process_name, cmdline[:500], contract_id,
                 json.dumps(evidence or {}, ensure_ascii=False)[:2000],
                 handled, action_taken),
            )
            return int(cur.lastrowid)

    def recent(self, limit: int = 20, unhandled_only: bool = False) -> list[dict[str, Any]]:
        q = "SELECT * FROM security_events"
        if unhandled_only:
            q += " WHERE handled = 'PENDING'"
        q += " ORDER BY id DESC LIMIT ?"
        with self._connect() as conn:
            rows = conn.execute(q, (int(limit),)).fetchall()
        return [dict(r) for r in rows]

    def mark_handled(self, event_id: int, action_taken: str) -> bool:
        with self._connect() as conn:
            cur = conn.execute(
                "UPDATE security_events SET handled = 'HANDLED', action_taken = ? WHERE id = ?",
                (action_taken, int(event_id)),
            )
            return cur.rowcount > 0

    def mark_handled_by_pid(self, pid: int, action_taken: str) -> int:
        """Đánh dấu mọi event PENDING của 1 PID là đã xử lý. Trả số dòng cập nhật."""
        with self._connect() as conn:
            cur = conn.execute(
                "UPDATE security_events SET handled = 'HANDLED', action_taken = ? "
                "WHERE pid = ? AND handled = 'PENDING'",
                (action_taken, int(pid)),
            )
            return cur.rowcount


class SecurityWatcher:
    """Vệ sĩ: quét + phát hiện. stdlib only."""

    def __init__(self, contracts: TaskContractStore | None = None,
                 events: SecurityEventStore | None = None) -> None:
        self.contracts = contracts or TaskContractStore()
        self.events = events or SecurityEventStore()

    # ------------------------------------------------------------------
    # Thu thập (chỉ đọc)
    # ------------------------------------------------------------------
    @staticmethod
    def list_processes() -> list[dict[str, Any]]:
        """tasklist CSV — name, pid, mem_usage_kb. Nhẹ, không cần admin."""
        try:
            r = subprocess.run(
                ["tasklist", "/FO", "CSV", "/NH"],
                capture_output=True, text=True, timeout=20, encoding="utf-8", errors="replace",
            )
            procs: list[dict[str, Any]] = []
            for row in csv.reader(io.StringIO(r.stdout)):
                if len(row) >= 5 and row[1].strip().isdigit():
                    mem = row[4].replace("K", "").replace(",", "").replace(".", "").strip()
                    procs.append({
                        "name": row[0].strip().strip('"'),
                        "pid": int(row[1]),
                        "mem_kb": int(mem) if mem.isdigit() else 0,
                    })
            return procs
        except Exception:
            return []

    @staticmethod
    def get_cmdline(pid: int) -> str:
        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 f"(Get-CimInstance Win32_Process -Filter 'ProcessId = {int(pid)}').CommandLine"],
                capture_output=True, text=True, timeout=15, encoding="utf-8", errors="replace",
            )
            return (r.stdout or "").strip()
        except Exception:
            return ""

    @staticmethod
    def list_network_connections() -> list[dict[str, Any]]:
        """netstat -ano — PID + đích ngoài (không loopback)."""
        try:
            r = subprocess.run(["netstat", "-ano"], capture_output=True, text=True,
                               timeout=20, encoding="utf-8", errors="replace")
            conns: list[dict[str, Any]] = []
            for line in (r.stdout or "").splitlines():
                parts = line.split()
                if len(parts) >= 5 and parts[-1].isdigit() and parts[3].count(":") == 1:
                    remote_ip = parts[2].rsplit(":", 1)[0]
                    if remote_ip in ("0.0.0.0", "[::]", "::", "*") or remote_ip.startswith("127."):
                        continue
                    conns.append({"remote": parts[2], "state": parts[3], "pid": int(parts[-1])})
            return conns
        except Exception:
            return []

    # ------------------------------------------------------------------
    # So hành vi ↔ hợp đồng
    # ------------------------------------------------------------------
    @staticmethod
    def _path_in_scope(cmdline: str, allowed_paths: list[str]) -> tuple[bool, str]:
        """Kiểm cmdline có trỏ ra ngoài allowed_paths không. (True, '') = trong phạm vi."""
        if not allowed_paths:
            return True, ""
        low = cmdline.lower()
        for p in allowed_paths:
            if p.lower() in low:
                return True, ""
        # cmdline có chứa đường dẫn nào không?
        path_like = re.findall(r"[a-z]:\\[^\"']+", low)
        for pl in path_like:
            if not any(p.lower() in pl for p in allowed_paths):
                return False, pl
        return True, ""

    def detect_violations(self, deep: bool = True) -> list[dict[str, Any]]:
        """Quét 1 vòng. deep=True → có cmdline (đắt hơn). Trả danh sách vi phạm MỚI (đã record)."""
        contracts = self.contracts.active_contracts()
        family = [c.subject.lower() for c in self.contracts.list_contracts()]
        if not family:
            return []  # không có hợp đồng nào từng đăng ký → không có chuẩn so

        procs = self.list_processes()
        new_violations: list[dict[str, Any]] = []

        matched_pids: set[int] = set()
        for proc in procs:
            name_low = proc["name"].lower()
            if not any(s in name_low for s in family):
                continue
            cmdline = self.get_cmdline(proc["pid"]) if deep else ""
            matched_pids.add(proc["pid"])
            contract = self.contracts.match_process(cmdline or name_low)
            if contract is None:
                # tên khớp subject nhưng không có hợp đồng ACTIVE → vượt thẩm quyền rồi
                ev = {"name": proc["name"], "mem_kb": proc["mem_kb"], "cmdline": cmdline[:300]}
                self.events.record("UNREGISTERED", proc["pid"], proc["name"], cmdline,
                                   evidence=ev)
                new_violations.append({"violation": "UNREGISTERED", "pid": proc["pid"],
                                       "process_name": proc["name"], "evidence": ev})
                continue

            # hợp đồng hết hạn/suspend mà vẫn chạy?
            c_now = self.contracts.get_contract(contract.contract_id)
            if c_now and c_now.status != "ACTIVE":
                ev = {"contract_status": c_now.status, "cmdline": cmdline[:300]}
                self.events.record("OVER_CONTRACT", proc["pid"], proc["name"], cmdline,
                                   contract_id=contract.contract_id, evidence=ev)
                new_violations.append({"violation": "OVER_CONTRACT", "pid": proc["pid"],
                                       "process_name": proc["name"], "evidence": ev})
                continue

            if deep and cmdline:
                in_scope, bad_path = self._path_in_scope(cmdline, contract.allowed_paths)
                if not in_scope:
                    ev = {"out_of_scope_path": bad_path, "allowed_paths": contract.allowed_paths}
                    self.events.record("OUT_OF_SCOPE_PATH", proc["pid"], proc["name"], cmdline,
                                       contract_id=contract.contract_id, evidence=ev)
                    new_violations.append({"violation": "OUT_OF_SCOPE_PATH", "pid": proc["pid"],
                                           "process_name": proc["name"], "evidence": ev})
                doms = contract.allowed_domains
                if doms:
                    bad_dom = [d for d in re.findall(
                        r"https?://([a-z0-9.-]+)", cmdline.lower()) if d not in doms]
                    if bad_dom:
                        ev = {"out_of_scope_domains": bad_dom[:5], "allowed_domains": doms}
                        self.events.record("OUT_OF_SCOPE_DOMAIN", proc["pid"], proc["name"],
                                           cmdline, contract_id=contract.contract_id, evidence=ev)
                        new_violations.append({"violation": "OUT_OF_SCOPE_DOMAIN",
                                               "pid": proc["pid"], "process_name": proc["name"],
                                               "evidence": ev})

        # Hợp đồng ACTIVE nhưng tiến trình đã chết → không phải vi phạm, chỉ ghi chú nhẹ
        return new_violations

    def check_network_for_contract(self, contract: TaskContract) -> list[dict[str, Any]]:
        """Kết nối mạng ngoài allowed_domains của tiến trình đang mang hợp đồng."""
        if not contract.allowed_domains:
            return []
        violations: list[dict[str, Any]] = []
        by_pid: dict[int, list[dict[str, Any]]] = {}
        for conn in self.list_network_connections():
            by_pid.setdefault(conn["pid"], []).append(conn)
        for proc in self.list_processes():
            cmdline = self.get_cmdline(proc["pid"])
            if contract.subject.lower() not in (cmdline or "").lower():
                continue
            for c in by_pid.get(proc["pid"], []):
                host = c["remote"].rsplit(":", 1)[0].lower()
                if any(d in host for d in contract.allowed_domains):
                    continue
                # IP lạ — chỉ cảnh báo, IP không so được với domain allowlist
                ev = {"remote": c["remote"], "state": c["state"], "note": "IP lạ ngoài miền cho phép"}
                self.events.record("SUSPICIOUS_NET", proc["pid"], proc["name"], cmdline,
                                   contract_id=contract.contract_id, evidence=ev)
                violations.append({"violation": "SUSPICIOUS_NET", "pid": proc["pid"],
                                   "process_name": proc["name"], "evidence": ev})
        return violations
