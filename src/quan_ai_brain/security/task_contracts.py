"""SEC-S1 (a): Hợp đồng nhiệm vụ — chuẩn "phạm vi được phép" cho AI/script khác.

Owner giao việc cho một AI/agent khác → khai báo với TONY: subject (tên/keyword
nhận diện tiến trình), goal, allowed_paths, allowed_domains, hạn thời gian,
cpu/mem cap, auto_contain. Vệ sĩ (watcher.py) so hành vi thật ↔ hợp đồng này.

Fail-honest: thiếu subject/goal khi tạo từ DM → raise ValueError (không đoán mạo).
Schema SQLite idempotent (data/security_contracts.db), chuẩn TodoStore.
"""
from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

DEFAULT_DB = Path(__file__).resolve().parents[2] / "data" / "security_contracts.db"

CONTRACT_STATUSES = ("ACTIVE", "SUSPENDED", "EXPIRED", "REVOKED")


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


@dataclass
class TaskContract:
    """Hợp đồng nhiệm vụ cho 1 AI/agent được owner thuê."""

    subject: str                      # keyword nhận diện tiến trình (không phân biệt hoa/thường)
    goal: str                         # nhiệm vụ được giao
    contract_id: str = ""
    allowed_paths: list[str] = field(default_factory=list)
    allowed_domains: list[str] = field(default_factory=list)
    cpu_cap_pct: float = 0.0          # 0 = không giới hạn
    mem_cap_mb: float = 0.0
    auto_contain: bool = False        # True = TONY được TẠM GIỮ ngay khi phát hiện vi phạm
    status: str = "ACTIVE"
    created_at: str = ""
    expires_at: str = ""              # ISO UTC; rỗng = không hạn

    def is_expired(self, at: datetime | None = None) -> bool:
        if not self.expires_at:
            return False
        try:
            return (at or _now_utc()) > datetime.fromisoformat(self.expires_at)
        except ValueError:
            return True  # hạn sai định dạng → fail-closed coi như hết hạn

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "subject": self.subject,
            "goal": self.goal,
            "allowed_paths": list(self.allowed_paths),
            "allowed_domains": list(self.allowed_domains),
            "cpu_cap_pct": self.cpu_cap_pct,
            "mem_cap_mb": self.mem_cap_mb,
            "auto_contain": self.auto_contain,
            "status": self.status,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "expired": self.is_expired(),
        }


class TaskContractStore:
    """CRUD hợp đồng nhiệm vụ. Mọi lần ĐỌC đều cập nhật trạng thái EXPIRED nếu quá hạn."""

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
                CREATE TABLE IF NOT EXISTS task_contracts (
                    contract_id TEXT PRIMARY KEY,
                    subject TEXT NOT NULL,
                    goal TEXT NOT NULL,
                    allowed_paths_json TEXT NOT NULL DEFAULT '[]',
                    allowed_domains_json TEXT NOT NULL DEFAULT '[]',
                    cpu_cap_pct REAL NOT NULL DEFAULT 0,
                    mem_cap_mb REAL NOT NULL DEFAULT 0,
                    auto_contain INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'ACTIVE',
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL DEFAULT ''
                )
                """
            )

    # ------------------------------------------------------------------
    # Tạo / đọc / đổi trạng thái
    # ------------------------------------------------------------------
    def create_contract(
        self,
        subject: str,
        goal: str,
        *,
        allowed_paths: list[str] | None = None,
        allowed_domains: list[str] | None = None,
        cpu_cap_pct: float = 0.0,
        mem_cap_mb: float = 0.0,
        auto_contain: bool = False,
        duration_minutes: int = 0,
    ) -> TaskContract:
        subject = (subject or "").strip()
        goal = (goal or "").strip()
        if not subject or not goal:
            raise ValueError("Thiếu subject hoặc goal — fail-honest, không đoán mạo")
        now = _now_utc()
        expires = _iso(now + timedelta(minutes=duration_minutes)) if duration_minutes > 0 else ""
        contract = TaskContract(
            subject=subject,
            goal=goal,
            contract_id=f"sec_{int(now.timestamp() * 1000):013d}_{abs(hash((subject, goal))) % 10000:04d}",
            allowed_paths=list(allowed_paths or []),
            allowed_domains=list(allowed_domains or []),
            cpu_cap_pct=float(cpu_cap_pct),
            mem_cap_mb=float(mem_cap_mb),
            auto_contain=bool(auto_contain),
            status="ACTIVE",
            created_at=_iso(now),
            expires_at=expires,
        )
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO task_contracts VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (
                    contract.contract_id, contract.subject, contract.goal,
                    __import__("json").dumps(contract.allowed_paths, ensure_ascii=False),
                    __import__("json").dumps(contract.allowed_domains, ensure_ascii=False),
                    contract.cpu_cap_pct, contract.mem_cap_mb,
                    int(contract.auto_contain), contract.status,
                    contract.created_at, contract.expires_at,
                ),
            )
        return contract

    def list_contracts(self, status: str | None = None) -> list[TaskContract]:
        rows: list[sqlite3.Row]
        with self._connect() as conn:
            if status:
                rows = conn.execute(
                    "SELECT * FROM task_contracts WHERE status = ? ORDER BY created_at DESC",
                    (status,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM task_contracts ORDER BY created_at DESC"
                ).fetchall()
        contracts = [self._row_to_contract(r) for r in rows]
        # lazily expire
        for c in contracts:
            if c.status == "ACTIVE" and c.is_expired():
                self.set_status(c.contract_id, "EXPIRED")
                c.status = "EXPIRED"
        return contracts

    def active_contracts(self) -> list[TaskContract]:
        return [c for c in self.list_contracts() if c.status == "ACTIVE" and not c.is_expired()]

    def get_contract(self, contract_id: str) -> TaskContract | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM task_contracts WHERE contract_id = ?", (contract_id,)
            ).fetchone()
        return self._row_to_contract(row) if row else None

    def set_status(self, contract_id: str, status: str) -> bool:
        if status not in CONTRACT_STATUSES:
            raise ValueError(f"Trạng thái không hợp lệ: {status}")
        with self._connect() as conn:
            cur = conn.execute(
                "UPDATE task_contracts SET status = ? WHERE contract_id = ?",
                (status, contract_id),
            )
            return cur.rowcount > 0

    # ------------------------------------------------------------------
    # Ghép tiến trình ↔ hợp đồng
    # ------------------------------------------------------------------
    def match_process(self, cmdline: str) -> TaskContract | None:
        """Trả về hợp đồng ACTIVE đầu tiên mà subject xuất hiện trong cmdline.

        cmdline đã lower-case trước khi so. None = không thuộc hợp đồng nào.
        """
        line = (cmdline or "").lower()
        if not line:
            return None
        for c in self.active_contracts():
            if c.subject.lower() in line:
                return c
        return None

    def subject_family_keywords(self) -> list[str]:
        """Tất cả subject keyword từng đăng ký (kể cả hết hạn) — để nhận diện 'họ hàng'."""
        with self._connect() as conn:
            rows = conn.execute("SELECT subject FROM task_contracts").fetchall()
        return sorted({r["subject"].strip().lower() for r in rows if r["subject"].strip()})

    # ------------------------------------------------------------------
    @staticmethod
    def _row_to_contract(r: sqlite3.Row) -> TaskContract:
        import json as _json

        return TaskContract(
            contract_id=r["contract_id"],
            subject=r["subject"],
            goal=r["goal"],
            allowed_paths=_json.loads(r["allowed_paths_json"]),
            allowed_domains=_json.loads(r["allowed_domains_json"]),
            cpu_cap_pct=float(r["cpu_cap_pct"]),
            mem_cap_mb=float(r["mem_cap_mb"]),
            auto_contain=bool(r["auto_contain"]),
            status=r["status"],
            created_at=r["created_at"],
            expires_at=r["expires_at"],
        )


# ---------------------------------------------------------------------------
# Parse lệnh DM: "giao nhiệm vụ cho <subject>: <goal> | phạm vi: p1, p2 |
# miền: d1, d2 | hạn: N phút [tự giữ]"
# ---------------------------------------------------------------------------
_DM_CONTRACT_RE = re.compile(
    r"^\s*giao\s+nhiệm\s+vụ\s+cho\s+(?P<subject>.+?)\s*[:：]\s*(?P<rest>.+)$",
    re.IGNORECASE,
)


def parse_dm_contract(text: str) -> dict[str, Any]:
    """Parse lệnh DM tạo hợp đồng. Fail-honest: raise ValueError khi thiếu subject/goal."""
    m = _DM_CONTRACT_RE.match((text or "").strip())
    if not m:
        raise ValueError(
            "Cú pháp: giao nhiệm vụ cho <tên AI>: <mục tiêu> | phạm vi: <đường dẫn> | "
            "miền: <domain> | hạn: <N> phút | tự giữ"
        )
    subject = m.group("subject").strip()
    rest = m.group("rest")
    # goal = phần trước '|' đầu tiên
    parts = [p.strip() for p in rest.split("|")]
    goal = parts[0].strip()
    if not subject or not goal:
        raise ValueError("Thiếu tên AI hoặc mục tiêu — không tạo hợp đồng mạo danh")

    allowed_paths: list[str] = []
    allowed_domains: list[str] = []
    duration_minutes = 0
    auto_contain = False
    for extra in parts[1:]:
        low = extra.lower()
        if low.startswith(("phạm vi", "pham vi", "paths")):
            body = extra.split(":", 1)[-1]
            allowed_paths = [p.strip() for p in body.split(",") if p.strip()]
        elif low.startswith(("miền", "mien", "domain")):
            body = extra.split(":", 1)[-1]
            allowed_domains = [d.strip().lower() for d in body.split(",") if d.strip()]
        elif low.startswith(("hạn", "han", "hạn:", "deadline")):
            mm = re.search(r"(\d+)\s*(phút|giờ|gio|h|minutes?|hours?)", low)
            if mm:
                n = int(mm.group(1))
                duration_minutes = n if "phút" in mm.group(2) or "minute" in mm.group(2) else n * 60
        elif "tự giữ" in low or "tu giu" in low or "auto" in low:
            auto_contain = True
    return {
        "subject": subject,
        "goal": goal,
        "allowed_paths": allowed_paths,
        "allowed_domains": allowed_domains,
        "duration_minutes": duration_minutes,
        "auto_contain": auto_contain,
    }
