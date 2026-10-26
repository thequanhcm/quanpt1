"""Approval Card Store — persistent approval cards bound to the formal
ApprovalGate/GovernanceStateStore lifecycle (Master Prompt V3, Section V).

Design (Sprint 2, audit-backed):
- Cards are FIRST-CLASS records in ``data/governance.db`` (table
  ``approval_cards`` — additive schema). Every card sent to NetChat has a
  row here BEFORE the message is posted, so the owner's reply can always be
  matched to a real, pending record.
- Formal approval lifecycle reuses the VERIFIED_ACTIVE stack:
  ApprovalGate.create_request / grant_approval / deny_approval with
  GovernanceStateStore persistence (one-time consume, fingerprint,
  revoke). This module never bypasses those gates.
- State machine per card: DRAFT -> PENDING_APPROVAL -> APPROVED | REJECTED
  | EXPIRED | CANCELLED; amend() returns a card to PENDING_APPROVAL with a
  new version (re-approval required, V3 Section 5.1).
- Every mutating call appends to the card's evidence trail (who, when,
  what channel proof) — no silent decisions.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from quan_ai_brain.governance.policy import RiskLevel
from quan_ai_brain.governance.state_store import GovernanceStateStore
from quan_ai_brain.tools.approval import ApprovalGate, ApprovalStatus
from quan_ai_brain.tools.path_guard import PathGuard  # noqa: F401  (workspace contract)


CARD_STATUSES = (
    "DRAFT",
    "PENDING_APPROVAL",
    "APPROVED",
    "REJECTED",
    "EXPIRED",
    "CANCELLED",
)

DEFAULT_TTL_DAYS = 7


@dataclass
class ApprovalCard:
    task_code: str
    title: str
    card_markdown: str
    status: str = "DRAFT"
    version: int = 1
    created_at_utc: str = ""
    updated_at_utc: str = ""
    ttl_expires_at_utc: str = ""
    request_id: str = ""
    evidence: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_code": self.task_code,
            "title": self.title,
            "status": self.status,
            "version": self.version,
            "created_at_utc": self.created_at_utc,
            "updated_at_utc": self.updated_at_utc,
            "ttl_expires_at_utc": self.ttl_expires_at_utc,
            "request_id": self.request_id,
            "card_markdown": self.card_markdown,
            "evidence": self.evidence,
        }


class ApprovalCardStore:
    """Persistent card registry + formal approval lifecycle binding."""

    def __init__(self, governance_db: str | Path, workspace: str | Path | None = None) -> None:
        self.db_path = Path(governance_db)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.workspace = Path(workspace).resolve() if workspace else None
        self._store = GovernanceStateStore(self.db_path, workspace=workspace) if self.workspace else None
        self._gate = ApprovalGate(trusted_approvers={"quanpt1"}, store=self._store)
        self._init_schema()

    # ------------------------------------------------------------------
    # schema
    # ------------------------------------------------------------------

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout = 5000")
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS approval_cards (
                    task_code TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    card_markdown TEXT NOT NULL,
                    status TEXT NOT NULL,
                    version INTEGER NOT NULL DEFAULT 1,
                    created_at_utc TEXT NOT NULL,
                    updated_at_utc TEXT NOT NULL,
                    ttl_expires_at_utc TEXT NOT NULL,
                    request_id TEXT DEFAULT '',
                    evidence_json TEXT NOT NULL DEFAULT '[]'
                )
                """
            )

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    def _ttl(self, days: int = DEFAULT_TTL_DAYS) -> str:
        return (self._now() + timedelta(days=days)).isoformat()

    def _touch(self, card: ApprovalCard, evidence_event: dict[str, Any]) -> None:
        card.updated_at_utc = self._now().isoformat()
        card.evidence.append({"at": card.updated_at_utc, **evidence_event})
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE approval_cards
                SET status=?, version=?, updated_at_utc=?, ttl_expires_at_utc=?,
                    request_id=?, evidence_json=?
                WHERE task_code=?
                """,
                (
                    card.status,
                    card.version,
                    card.updated_at_utc,
                    card.ttl_expires_at_utc,
                    card.request_id,
                    json.dumps(card.evidence, ensure_ascii=False),
                    card.task_code,
                ),
            )

    def _load(self, row: sqlite3.Row) -> ApprovalCard:
        return ApprovalCard(
            task_code=row["task_code"],
            title=row["title"],
            card_markdown=row["card_markdown"],
            status=row["status"],
            version=row["version"],
            created_at_utc=row["created_at_utc"],
            updated_at_utc=row["updated_at_utc"],
            ttl_expires_at_utc=row["ttl_expires_at_utc"],
            request_id=row["request_id"],
            evidence=json.loads(row["evidence_json"] or "[]"),
        )

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    def create_card(
        self,
        task_code: str,
        title: str,
        card_markdown: str,
        *,
        risk_level: int = RiskLevel.R2,
        goal: str = "",
        params: dict[str, Any] | None = None,
        ttl_days: int = DEFAULT_TTL_DAYS,
    ) -> ApprovalCard:
        """Register a card BEFORE it is announced on NetChat. Fail-closed:
        duplicate task_code raises — one live card per task code.
        R5 actions are NEVER cardable (V3 Section X.13: R5 hard-block, no
        approval path bypasses it)."""
        if not task_code or not task_code.strip():
            raise ValueError("task_code is required")
        if int(risk_level) == int(RiskLevel.R5):
            raise ValueError(
                "R5 is hard-blocked: no approval card can be created for a "
                "prohibited operation (no exception, V3 Section X.13)."
            )
        if self.get_card(task_code) is not None:
            raise ValueError(f"Approval card '{task_code}' already exists")
        if not card_markdown.strip():
            raise ValueError("card_markdown is required")

        now = self._now().isoformat()
        req = self._gate.create_request(
            tool_id="netchat_approval",
            action="owner_decision",
            params=dict(params or {"title": title}),
            resource_scope="workspace",
            risk_level=RiskLevel(int(risk_level)),
            goal=goal or title,
            request_id=task_code,
        )
        card = ApprovalCard(
            task_code=task_code,
            title=title,
            card_markdown=card_markdown,
            status="PENDING_APPROVAL",
            version=1,
            created_at_utc=now,
            updated_at_utc=now,
            ttl_expires_at_utc=self._ttl(ttl_days),
            request_id=req.request_id,
            evidence=[{"at": now, "event": "CREATED", "request_id": req.request_id}],
        )
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO approval_cards (
                    task_code, title, card_markdown, status, version,
                    created_at_utc, updated_at_utc, ttl_expires_at_utc,
                    request_id, evidence_json
                ) VALUES (?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    card.task_code, card.title, card.card_markdown, card.status,
                    card.version, card.created_at_utc, card.updated_at_utc,
                    card.ttl_expires_at_utc, card.request_id,
                    json.dumps(card.evidence, ensure_ascii=False),
                ),
            )
        return card

    def get_card(self, task_code: str) -> ApprovalCard | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM approval_cards WHERE task_code=?", (task_code,)
            ).fetchone()
        return self._load(row) if row else None

    def list_cards(self, status: str | None = None) -> list[ApprovalCard]:
        query = "SELECT * FROM approval_cards"
        params: tuple = ()
        if status:
            query += " WHERE status=?"
            params = (status,)
        query += " ORDER BY created_at_utc ASC"
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._load(r) for r in rows]

    def refresh_expiry(self) -> int:
        """Mark PENDING cards past TTL as EXPIRED (honest state, V3 5.3)."""
        now = self._now().isoformat()
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT task_code FROM approval_cards WHERE status='PENDING_APPROVAL' AND ttl_expires_at_utc < ?",
                (now,),
            ).fetchall()
            n = 0
            for r in rows:
                card = self.get_card(r["task_code"])
                if card:
                    card.status = "EXPIRED"
                    self._touch(card, {"event": "EXPIRED_BY_TTL"})
                    n += 1
        return n

    def approve_card(self, task_code: str, approver: str, *, auth_method: str = "", notes: str = "", evidence: dict[str, Any] | None = None) -> ApprovalCard:
        """Grant formal owner approval via ApprovalGate (one-time use)."""
        card = self._require(task_code)
        if card.status == "APPROVED":
            raise PermissionError(
                f"Hồ sơ {task_code} đã được phê duyệt trước đó (không duyệt trùng)."
            )
        if card.status != "PENDING_APPROVAL":
            raise PermissionError(
                f"Hồ sơ {task_code} đang ở trạng thái {card.status}, không thể duyệt."
            )
        req = self._gate.get_request(card.request_id)
        if req is None:
            raise RuntimeError(f"Formal request '{card.request_id}' missing — data integrity failure")
        approval = self._gate.grant_approval(
            req, approver=approver,
            expires_at=card.ttl_expires_at_utc,
            notes=notes or f"Approved via {auth_method or 'unknown channel'}",
        )
        card.status = "APPROVED"
        self._touch(card, {
            "event": "APPROVED",
            "approver": approver,
            "approval_id": approval.approval_id,
            "auth_method": auth_method,
            **(evidence or {}),
        })
        return card

    def reject_card(self, task_code: str, reason: str, *, evidence: dict[str, Any] | None = None) -> ApprovalCard:
        card = self._require(task_code)
        if card.status != "PENDING_APPROVAL":
            raise PermissionError(
                f"Hồ sơ {task_code} đang ở trạng thái {card.status}, không thể từ chối."
            )
        self._gate.deny_approval(card.request_id, reason=reason)
        card.status = "REJECTED"
        self._touch(card, {"event": "REJECTED", "reason": reason, **(evidence or {})})
        return card

    def cancel_card(self, task_code: str, reason: str) -> ApprovalCard:
        card = self._require(task_code)
        card.status = "CANCELLED"
        self._touch(card, {"event": "CANCELLED", "reason": reason})
        return card

    def amend_card(self, task_code: str, new_markdown: str, reason: str) -> ApprovalCard:
        """V3 5.1: changed plan => back to PENDING_APPROVAL, re-approval needed."""
        card = self._require(task_code)
        card.version += 1
        card.card_markdown = new_markdown
        card.status = "PENDING_APPROVAL"
        card.ttl_expires_at_utc = self._ttl()
        self._touch(card, {"event": "AMENDED", "reason": reason, "version": card.version})
        return card

    def consume_if_execution_started(self, task_code: str) -> bool:
        """Mark the formal approval consumed when approved work begins."""
        card = self._require(task_code)
        if card.status != "APPROVED":
            return False
        with self._connect() as conn:
            row = conn.execute(
                "SELECT approval_id FROM approvals WHERE request_id=?", (card.request_id,)
            ).fetchone()
        if not row:
            return False
        return self._gate.consume_approval(row["approval_id"])

    def _require(self, task_code: str) -> ApprovalCard:
        card = self.get_card(task_code)
        if card is None:
            raise KeyError(f"Approval card '{task_code}' not found")
        return card


def new_task_code(prefix: str = "TASK") -> str:
    """Generate a unique task code, e.g. TASK-A1B2C3D4."""
    return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"
