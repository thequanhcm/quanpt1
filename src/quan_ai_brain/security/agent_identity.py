"""SENTINEL-S3 (M01+M04): Sổ cái Danh tính Agent — Trust/Risk scoring deterministic.

Master prompt v1.0 (owner 02/11/2026): mỗi đối tượng phải có Identity, Trust
Score, Risk Score, Permission Scope, Behavior History, Security Status,
Evidence, Recommended Response. Phân loại A-F:
TRUSTED / UNKNOWN / SUSPICIOUS / COMPROMISED / MALICIOUS / UNAUTHORIZED.

Nguyên tắc bắt buộc (prompt mục 4): KHÔNG mặc định coi đối tượng chưa xác minh
là độc hại — nghi vấn (SUSPICIOUS, bằng chứng chưa đủ) phải tách khỏi đã xác
nhận (COMPROMISED/MALICIOUS — chỉ owner hoặc điều tra xác nhận mới gán được).

SENTINEL KHÔNG tự cấp quyền: set_classification chỉ cho phép SENTINEL tự nâng
tối đa SUSPICIOUS/UNAUTHORIZED (dựa vi phạm đo được); COMPROMISED/MALICIOUS
phải có actor=owner hoặc evidence_ref trỏ vào hồ sơ điều tra.

Scoring DETERMINISTIC (không AI tự mơ): base 20, đăng ký +40, hợp đồng ACTIVE
+30, mỗi vi phạm −25 trust / +25 risk (cắt [0,100]).
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# A-F classifications (master prompt MODULE 04)
TRUSTED = "TRUSTED"            # A
UNKNOWN = "UNKNOWN"            # B
SUSPICIOUS = "SUSPICIOUS"      # C
COMPROMISED = "COMPROMISED"    # D
MALICIOUS = "MALICIOUS"        # E
UNAUTHORIZED = "UNAUTHORIZED"  # F

CLASSIFICATIONS = (TRUSTED, UNKNOWN, SUSPICIOUS, COMPROMISED, MALICIOUS, UNAUTHORIZED)

# SENTINEL chỉ tự gán được các mức này (còn lại cần owner/evidence_ref)
SELF_ASSIGNABLE = {UNKNOWN, SUSPICIOUS, UNAUTHORIZED}

# Security status
ST_NORMAL = "NORMAL"
ST_MONITORED = "MONITORED"
ST_RESTRICTED = "RESTRICTED"
ST_CONTAINED = "CONTAINED"
ST_TERMINATED = "TERMINATED"

_RECOMMENDED = {
    TRUSTED: "Cho hoạt động; giám sát thường quy.",
    UNKNOWN: "Giám sát chặt hơn (L1); mời đăng ký/hợp đồng; không khống chế.",
    SUSPICIOUS: "Giới hạn quyền (L2); giữ bằng chứng; chờ owner xác minh.",
    COMPROMISED: "Cô lập (L3) sau phê duyệt; bảo toàn bằng chứng; điều tra.",
    MALICIOUS: "Khống chế triệt để (L3-L4); owner quyết định hạ gục.",
    UNAUTHORIZED: "Chặn truy cập; cảnh báo owner; mời đăng ký nếu hợp lệ.",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clamp(v: int, lo: int = 0, hi: int = 100) -> int:
    return max(lo, min(hi, int(v)))


@dataclass
class AgentIdentity:
    agent_id: str
    name: str
    kind: str                      # PROCESS | EDGE | CONNECTOR | SERVICE
    classification: str = UNKNOWN
    trust_score: int = 20
    risk_score: int = 20
    permission_scope: list[str] = field(default_factory=list)
    security_status: str = ST_NORMAL
    evidence_count: int = 0
    recommended_response: str = _RECOMMENDED[UNKNOWN]
    first_seen_at: str = ""
    last_seen_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id, "name": self.name, "kind": self.kind,
            "classification": self.classification,
            "trust_score": self.trust_score, "risk_score": self.risk_score,
            "permission_scope": self.permission_scope,
            "security_status": self.security_status,
            "evidence_count": self.evidence_count,
            "recommended_response": self.recommended_response,
            "first_seen_at": self.first_seen_at, "last_seen_at": self.last_seen_at,
        }


class AgentIdentityRegistry:
    """Sổ cái danh tính — SQLite data/sentinel_agents.db. Fail-honest."""

    def __init__(self, db_path: str | Any) -> None:
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sentinel_identities (
                    agent_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    classification TEXT NOT NULL,
                    trust_score INTEGER NOT NULL,
                    risk_score INTEGER NOT NULL,
                    permission_scope TEXT NOT NULL DEFAULT '[]',
                    security_status TEXT NOT NULL,
                    evidence_count INTEGER NOT NULL DEFAULT 0,
                    violation_count INTEGER NOT NULL DEFAULT 0,
                    behavior_history TEXT NOT NULL DEFAULT '[]',
                    first_seen_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL
                )
                """
            )

    # ------------------------------------------------------------------
    def _row_to_identity(self, row: sqlite3.Row) -> AgentIdentity:
        return AgentIdentity(
            agent_id=row["agent_id"], name=row["name"], kind=row["kind"],
            classification=row["classification"],
            trust_score=row["trust_score"], risk_score=row["risk_score"],
            permission_scope=json.loads(row["permission_scope"]),
            security_status=row["security_status"],
            evidence_count=row["evidence_count"],
            recommended_response=_RECOMMENDED.get(row["classification"], "?"),
            first_seen_at=row["first_seen_at"], last_seen_at=row["last_seen_at"],
        )

    def observe(self, agent_id: str, name: str, kind: str, *,
                registered: bool = False, contract_active: bool = False,
                scope: list[str] | None = None) -> AgentIdentity:
        """Ghi nhận lần gặp (mới hoặc cũ) — scoring deterministic, idempotent."""
        if not agent_id or not name:
            raise ValueError("agent_id và name là bắt buộc")
        if kind not in ("PROCESS", "EDGE", "CONNECTOR", "SERVICE"):
            raise ValueError(f"kind không hợp lệ: {kind}")
        now = _now()
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM sentinel_identities WHERE agent_id=?", (agent_id,)
            ).fetchone()
            if row is None:
                trust = 20 + (40 if registered else 0) + (30 if contract_active else 0)
                classification = TRUSTED if (registered or contract_active) else UNKNOWN
                status = ST_NORMAL if classification == TRUSTED else ST_MONITORED
                conn.execute(
                    """
                    INSERT INTO sentinel_identities (
                        agent_id, name, kind, classification, trust_score, risk_score,
                        permission_scope, security_status, first_seen_at, last_seen_at
                    ) VALUES (?,?,?,?,?,?,?,?,?,?)
                    """,
                    (agent_id, name, kind, classification, _clamp(trust), 20,
                     json.dumps(scope or [], ensure_ascii=False), status, now, now),
                )
            else:
                conn.execute(
                    "UPDATE sentinel_identities SET last_seen_at=?, name=? WHERE agent_id=?",
                    (now, name, agent_id),
                )
        return self.get(agent_id)  # type: ignore[return-value]

    def get(self, agent_id: str) -> AgentIdentity | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM sentinel_identities WHERE agent_id=?", (agent_id,)
            ).fetchone()
            return self._row_to_identity(row) if row else None

    def find_by_name(self, name: str) -> list[AgentIdentity]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM sentinel_identities WHERE name LIKE ? ORDER BY last_seen_at DESC",
                (f"%{name}%",),
            ).fetchall()
            return [self._row_to_identity(r) for r in rows]

    def list_identities(self, classification: str | None = None) -> list[AgentIdentity]:
        with self._connect() as conn:
            if classification:
                rows = conn.execute(
                    "SELECT * FROM sentinel_identities WHERE classification=?"
                    " ORDER BY risk_score DESC", (classification,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM sentinel_identities ORDER BY risk_score DESC"
                ).fetchall()
            return [self._row_to_identity(r) for r in rows]

    def counts(self) -> dict[str, int]:
        out = {c: 0 for c in CLASSIFICATIONS}
        for ident in self.list_identities():
            out[ident.classification] = out.get(ident.classification, 0) + 1
        return out

    # ------------------------------------------------------------------
    def record_behavior(self, agent_id: str, event: dict[str, Any]) -> None:
        """Append hành vi vào history (giữ tối đa 50 mục — chống phình)."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT behavior_history FROM sentinel_identities WHERE agent_id=?",
                (agent_id,),
            ).fetchone()
            if row is None:
                return
            history = json.loads(row["behavior_history"])
            history.append({**event, "at": _now()})
            conn.execute(
                "UPDATE sentinel_identities SET behavior_history=? WHERE agent_id=?",
                (json.dumps(history[-50:], ensure_ascii=False), agent_id),
            )

    def apply_violation(self, agent_id: str, violation: str, *,
                        evidence_ref: str = "") -> AgentIdentity:
        """Một vi phạm ĐO ĐƯỢC: trust −25, risk +25, đếm evidence.

        Phân loại tự động (deterministic, trung thực):
        - UNAUTHORIZED: tiến trình không hợp đồng không đăng ký (F)
        - SUSPICIOUS: đã đăng ký/hợp đồng nhưng vi phạm (C — nghi vấn,
          chờ owner/điều tra xác nhận trước khi lên D/E)
        """
        now = _now()
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM sentinel_identities WHERE agent_id=?", (agent_id,)
            ).fetchone()
            if row is None:
                raise ValueError(f"Chưa observe agent {agent_id}")
            vcount = row["violation_count"] + 1
            trust = _clamp(row["trust_score"] - 25)
            risk = _clamp(row["risk_score"] + 25)
            if row["classification"] == UNKNOWN:
                new_class = UNAUTHORIZED
            elif row["classification"] in (TRUSTED, SUSPICIOUS, UNAUTHORIZED):
                new_class = SUSPICIOUS if row["classification"] == TRUSTED else row["classification"]
                if row["classification"] == UNAUTHORIZED:
                    new_class = UNAUTHORIZED
            else:  # COMPROMISED/MALICIOUS chỉ owner hạ xuống, không tự đổi
                new_class = row["classification"]
            status = ST_RESTRICTED if new_class == SUSPICIOUS else row["security_status"]
            history = json.loads(row["behavior_history"])
            history.append(
                {"event": "VIOLATION", "violation": violation,
                 "evidence_ref": evidence_ref, "at": now}
            )
            conn.execute(
                """
                UPDATE sentinel_identities SET trust_score=?, risk_score=?,
                    classification=?, security_status=?, evidence_count=?,
                    violation_count=?, behavior_history=? WHERE agent_id=?
                """,
                (trust, risk, new_class, status, row["evidence_count"] + 1,
                 vcount, json.dumps(history[-50:], ensure_ascii=False), agent_id),
            )
        return self.get(agent_id)  # type: ignore[return-value]

    def set_classification(self, agent_id: str, classification: str, *,
                           by: str, evidence_ref: str = "") -> AgentIdentity:
        """Đổi phân loại. FAIL-CLOSED:
        - COMPROMISED/MALICIOUS: CHỈ owner hoặc kèm evidence_ref điều tra.
        - SENTINEL (by != owner) không được tự gán D/E — đúng prompt mục 2
          (không tự cấp quyền) + mục 4 (tách nghi vấn khỏi xác nhận).
        - SENTINEL không được 'trắng tay' nâng D/E không bằng chứng.
        """
        if classification not in CLASSIFICATIONS:
            raise ValueError(f"Phân loại không hợp lệ: {classification}")
        is_owner = by.strip().lower() in ("owner", "quanpt1", "owner_dm")
        if classification in (COMPROMISED, MALICIOUS) and not is_owner and not evidence_ref:
            raise PermissionError(
                "SENTINEL không tự gán COMPROMISED/MALICIOUS: cần owner hoặc "
                "evidence_ref từ hồ sơ điều tra (phân biệt nghi vấn vs xác nhận)."
            )
        now = _now()
        with self._connect() as conn:
            row = conn.execute(
                "SELECT security_status, behavior_history FROM sentinel_identities WHERE agent_id=?",
                (agent_id,),
            ).fetchone()
            if row is None:
                raise ValueError(f"Không có agent {agent_id}")
            status = row["security_status"]
            if classification in (COMPROMISED, MALICIOUS, UNAUTHORIZED):
                status = ST_RESTRICTED
            elif classification == TRUSTED:
                status = ST_NORMAL
            history = json.loads(row["behavior_history"])
            history.append(
                {"event": "RECLASSIFY", "to": classification, "by": by,
                 "evidence_ref": evidence_ref, "at": now}
            )
            conn.execute(
                "UPDATE sentinel_identities SET classification=?, security_status=?,"
                " behavior_history=? WHERE agent_id=?",
                (classification, status,
                 json.dumps(history[-50:], ensure_ascii=False), agent_id),
            )
        return self.get(agent_id)  # type: ignore[return-value]

    def set_security_status(self, agent_id: str, status: str) -> None:
        if status not in (ST_NORMAL, ST_MONITORED, ST_RESTRICTED, ST_CONTAINED, ST_TERMINATED):
            raise ValueError(f"Status không hợp lệ: {status}")
        with self._connect() as conn:
            conn.execute(
                "UPDATE sentinel_identities SET security_status=? WHERE agent_id=?",
                (status, agent_id),
            )
