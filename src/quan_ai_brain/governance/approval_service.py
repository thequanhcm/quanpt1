"""DEOM M4 — ApprovalCardService: vòng đời thẻ phê duyệt R4 (DEOM §5.2–5.3).

Thiết kế: reports/DEOM_M4_DESIGN.md (§3). Nguyên tắc bất di bất dịch:
- Quyền phê duyệt duy nhất thuộc owner (quanpt1) — self-approval bị CHẶN BẰNG CODE.
- Fail-closed: card hết hạn / đã consumed / sai người quyết → từ chối, không mô phỏng.
- 1 card APPROVED = 1 lần dùng (consume) — tái dùng bị từ chối.
- R5 KHÔNG BAO GIỜ tạo card (hard-block ở policy.py — card chỉ cho R4).
- DB riêng data/approval_cards_v2.db — không đụng governance.db hiện có.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

# Người có quyền phê duyệt cuối cùng (charter — CHỈ chủ hệ thống)
OWNER_ID = "quanpt1"

CARD_STATE_PENDING = "PENDING"
CARD_STATE_APPROVED = "APPROVED"
CARD_STATE_REJECTED = "REJECTED"
CARD_STATE_CANCELLED = "CANCELLED"
CARD_STATE_EXPIRED = "EXPIRED"

TERMINAL_CARD_STATES = (
    CARD_STATE_APPROVED,
    CARD_STATE_REJECTED,
    CARD_STATE_CANCELLED,
    CARD_STATE_EXPIRED,
)


class ApprovalCardError(Exception):
    """Lỗi nghiệp vụ thẻ phê duyệt (từ chối có lý do — không nuốt)."""


@dataclass
class ApprovalCard:
    """Thẻ phê duyệt 12 trường DEOM §5.3 + action_fingerprint (DEOM V4 §6.2)."""

    approval_id: str
    task_id: str
    action_summary: str
    risk_level: str  # chỉ 'R4' hợp lệ
    requested_by: str
    scope: list[str]
    evidence_bundle: list[str]
    created_at_utc: str
    expires_at_utc: str
    state: str = CARD_STATE_PENDING
    decided_by: str | None = None
    decided_at_utc: str | None = None
    consumed_at_utc: str | None = None
    action_fingerprint: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "approval_id": self.approval_id,
            "task_id": self.task_id,
            "action_summary": self.action_summary,
            "risk_level": self.risk_level,
            "requested_by": self.requested_by,
            "scope": list(self.scope),
            "evidence_bundle": list(self.evidence_bundle),
            "created_at_utc": self.created_at_utc,
            "expires_at_utc": self.expires_at_utc,
            "state": self.state,
            "decided_by": self.decided_by,
            "decided_at_utc": self.decided_at_utc,
            "consumed_at_utc": self.consumed_at_utc,
            "action_fingerprint": self.action_fingerprint,
        }


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def compute_action_fingerprint(
    *,
    action_summary: str,
    scope: list[str] | None = None,
    params: dict[str, Any] | None = None,
) -> str:
    """DEOM V4 §6.2 — vân tay nội dung hành động được duyệt.

    Bọc nội dung TRƯỚC khi trình owner. Consume bắt buộc trình đúng nội dung đó
    (fingerprint lệch → fail-closed). Không bao gồm thời gian/id (những thứ tự
    nhiên khác nhau giữa 2 lần tạo) — chỉ gồm nội dung có ý nghĩa nghiệp vụ.
    """
    payload = {
        "action_summary": " ".join(str(action_summary).split()).strip(),
        "scope": sorted(str(s).strip() for s in (scope or [])),
        "params": json.dumps(params or {}, sort_keys=True, ensure_ascii=False, default=str),
    }
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class ApprovalCardService:
    """Service quản lý thẻ phê duyệt R4 — fail-closed, tách đề xuất/phê duyệt."""

    def __init__(self, db_path: str | Path = "data/approval_cards_v2.db") -> None:
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
                CREATE TABLE IF NOT EXISTS approval_cards_v2 (
                    approval_id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    action_summary TEXT NOT NULL,
                    risk_level TEXT NOT NULL,
                    requested_by TEXT NOT NULL,
                    scope_json TEXT NOT NULL DEFAULT '[]',
                    evidence_bundle_json TEXT NOT NULL DEFAULT '[]',
                    created_at_utc TEXT NOT NULL,
                    expires_at_utc TEXT NOT NULL,
                    state TEXT NOT NULL DEFAULT 'PENDING',
                    decided_by TEXT,
                    decided_at_utc TEXT,
                    consumed_at_utc TEXT,
                    action_fingerprint TEXT
                )
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS card_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    approval_id TEXT NOT NULL,
                    event TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    reason TEXT NOT NULL DEFAULT '',
                    at_utc TEXT NOT NULL
                )
                """
            )

    # ------------------------------------------------------------------
    # Nội bộ
    # ------------------------------------------------------------------
    def _log_event(self, approval_id: str, event: str, actor: str, reason: str = "") -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO card_events (approval_id, event, actor, reason, at_utc) VALUES (?, ?, ?, ?, ?)",
                (approval_id, event, actor, reason, _now()),
            )

    def _row_to_card(self, row: sqlite3.Row) -> ApprovalCard:
        return ApprovalCard(
            approval_id=row["approval_id"],
            task_id=row["task_id"],
            action_summary=row["action_summary"],
            risk_level=row["risk_level"],
            requested_by=row["requested_by"],
            scope=json.loads(row["scope_json"]),
            evidence_bundle=json.loads(row["evidence_bundle_json"]),
            created_at_utc=row["created_at_utc"],
            expires_at_utc=row["expires_at_utc"],
            state=row["state"],
            decided_by=row["decided_by"],
            decided_at_utc=row["decided_at_utc"],
            consumed_at_utc=row["consumed_at_utc"],
            action_fingerprint=row["action_fingerprint"] if "action_fingerprint" in row.keys() else None,
        )

    def _is_expired(self, card: ApprovalCard, now: datetime | None = None) -> bool:
        try:
            expires = datetime.fromisoformat(card.expires_at_utc)
        except ValueError:
            return True  # expires hỏng → coi như hết hạn (fail-closed)
        now = now or datetime.now(timezone.utc)
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return now >= expires

    # ------------------------------------------------------------------
    # Tạo card
    # ------------------------------------------------------------------
    def create_card(
        self,
        *,
        task_id: str,
        action_summary: str,
        risk_level: str = "R4",
        requested_by: str = "tony",
        scope: list[str] | None = None,
        evidence_bundle: list[str] | None = None,
        ttl_hours: int = 24,
        action_fingerprint: str | None = None,
        action_params: dict[str, Any] | None = None,
    ) -> ApprovalCard:
        """Tạo thẻ PENDING. R5 → từ chối tuyệt đối (policy đã block, không card).

        DEOM V4 §6.2: nếu `action_fingerprint` không cung cấp thì tự tính từ
        (action_summary, scope, action_params) — card luôn có binding nội dung
        hành động; consume sau này bắt buộc khớp.
        """
        risk = str(risk_level).upper()
        if risk == "R5":
            raise ApprovalCardError("R5 is hard-blocked — approval cards are never created for R5")
        if risk != "R4":
            raise ApprovalCardError(f"approval cards are for R4 only, got {risk}")
        if not action_summary.strip():
            raise ApprovalCardError("action_summary is required")
        if action_fingerprint is None:
            action_fingerprint = compute_action_fingerprint(
                action_summary=action_summary, scope=scope, params=action_params
            )

        now = datetime.now(timezone.utc)
        card = ApprovalCard(
            approval_id=f"appr_{uuid.uuid4().hex[:12]}",
            task_id=task_id,
            action_summary=action_summary.strip(),
            risk_level="R4",
            requested_by=requested_by,
            scope=list(scope or []),
            evidence_bundle=list(evidence_bundle or []),
            created_at_utc=now.isoformat(),
            expires_at_utc=(now + timedelta(hours=max(1, int(ttl_hours)))).isoformat(),
            action_fingerprint=action_fingerprint,
        )
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO approval_cards_v2 (
                    approval_id, task_id, action_summary, risk_level, requested_by,
                    scope_json, evidence_bundle_json, created_at_utc, expires_at_utc, state,
                    action_fingerprint
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    card.approval_id,
                    card.task_id,
                    card.action_summary,
                    card.risk_level,
                    card.requested_by,
                    json.dumps(card.scope),
                    json.dumps(card.evidence_bundle),
                    card.created_at_utc,
                    card.expires_at_utc,
                    card.state,
                    card.action_fingerprint,
                ),
            )
        self._log_event(card.approval_id, "CREATED", requested_by, action_summary)
        return card

    # ------------------------------------------------------------------
    # Đọc
    # ------------------------------------------------------------------
    def get_card(self, approval_id: str) -> ApprovalCard | None:
        with self._lock, self._conn:
            row = self._conn.execute(
                "SELECT * FROM approval_cards_v2 WHERE approval_id = ?", (approval_id,)
            ).fetchone()
        return self._row_to_card(row) if row else None

    def list_cards(self, state: str | None = None, limit: int = 100) -> list[ApprovalCard]:
        with self._lock, self._conn:
            if state:
                rows = self._conn.execute(
                    "SELECT * FROM approval_cards_v2 WHERE state = ? ORDER BY created_at_utc DESC LIMIT ?",
                    (state, limit),
                ).fetchall()
            else:
                rows = self._conn.execute(
                    "SELECT * FROM approval_cards_v2 ORDER BY created_at_utc DESC LIMIT ?",
                    (limit,),
                ).fetchall()
        return [self._row_to_card(r) for r in rows]

    def events(self, approval_id: str, limit: int = 100) -> list[dict[str, Any]]:
        with self._lock, self._conn:
            rows = self._conn.execute(
                "SELECT event, actor, reason, at_utc FROM card_events WHERE approval_id = ? ORDER BY id ASC LIMIT ?",
                (approval_id, limit),
            ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Quyết định (approve / reject / cancel) — tách đề xuất & phê duyệt
    # ------------------------------------------------------------------
    def approve(self, approval_id: str, *, decided_by: str, approval_evidence: str = "") -> ApprovalCard:
        """Owner duyệt card. Self-approval → từ chối (chặn bằng code, có vết)."""
        card = self.get_card(approval_id)
        if card is None:
            raise ApprovalCardError(f"approval card {approval_id} not found")
        # 1. Self-approval: người đề xuất KHÔNG THỂ tự duyệt — trừ trường hợp
        # đặc biệt owner giao task TRỰC TIẾP (requested_by=owner): owner phê
        # duyệt lệnh của chính mình là actor=owner, không phải TONY tự duyệt
        # (M1 §4). Self-approval chặn khi requestor là tony/agent.
        if decided_by == card.requested_by and card.requested_by != OWNER_ID:
            self._log_event(approval_id, "APPROVE_REJECTED_SELF_APPROVAL", decided_by, "requestor cannot approve own card")
            raise ApprovalCardError(
                f"self-approval blocked: {decided_by} requested this card and cannot approve it (owner-only approval)"
            )
        # 2. Agent escalation: ai đó ≠ owner → từ chối (quyền phê duyệt duy nhất owner)
        if decided_by != OWNER_ID:
            self._log_event(approval_id, "APPROVE_REJECTED_NOT_OWNER", decided_by, f"{decided_by} is not the owner")
            raise ApprovalCardError(f"approval denied: only {OWNER_ID} can approve cards, got {decided_by}")
        # 3. Trạng thái
        if card.state != CARD_STATE_PENDING:
            raise ApprovalCardError(f"card is {card.state}, only PENDING can be approved")
        # 4. Hết hạn → EXPIRED + từ chối
        if self._is_expired(card):
            self._set_state(card, CARD_STATE_EXPIRED, actor="system", reason="expired before decision")
            raise ApprovalCardError(f"card {approval_id} expired at {card.expires_at_utc} — request a new one")
        if not approval_evidence.strip():
            # fail-closed: quyết định phải có bằng chứng (lệnh DM / HMAC token)
            raise ApprovalCardError("approval_evidence is required (DM message id / HMAC token)")

        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE approval_cards_v2 SET state = ?, decided_by = ?, decided_at_utc = ? WHERE approval_id = ?",
                (CARD_STATE_APPROVED, decided_by, _now(), approval_id),
            )
        self._log_event(approval_id, "APPROVED", decided_by, approval_evidence)
        return self.get_card(approval_id)  # type: ignore[return-value]

    def reject(self, approval_id: str, *, decided_by: str, reason: str = "") -> ApprovalCard:
        card = self.get_card(approval_id)
        if card is None:
            raise ApprovalCardError(f"approval card {approval_id} not found")
        if decided_by != OWNER_ID:
            raise ApprovalCardError(f"approval denied: only {OWNER_ID} can reject cards, got {decided_by}")
        if card.state != CARD_STATE_PENDING:
            raise ApprovalCardError(f"card is {card.state}, only PENDING can be rejected")
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE approval_cards_v2 SET state = ?, decided_by = ?, decided_at_utc = ? WHERE approval_id = ?",
                (CARD_STATE_REJECTED, decided_by, _now(), approval_id),
            )
        self._log_event(approval_id, "REJECTED", decided_by, reason)
        return self.get_card(approval_id)  # type: ignore[return-value]

    def cancel(self, approval_id: str, *, actor: str, reason: str = "") -> ApprovalCard:
        """Requestor tự hủy card PENDING của mình (không phải phê duyệt — hợp lệ)."""
        card = self.get_card(approval_id)
        if card is None:
            raise ApprovalCardError(f"approval card {approval_id} not found")
        if card.state != CARD_STATE_PENDING:
            raise ApprovalCardError(f"card is {card.state}, only PENDING can be cancelled")
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE approval_cards_v2 SET state = ?, decided_by = ?, decided_at_utc = ? WHERE approval_id = ?",
                (CARD_STATE_CANCELLED, actor, _now(), approval_id),
            )
        self._log_event(approval_id, "CANCELLED", actor, reason)
        return self.get_card(approval_id)  # type: ignore[return-value]

    def _set_state(self, card: ApprovalCard, state: str, *, actor: str, reason: str = "") -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE approval_cards_v2 SET state = ? WHERE approval_id = ?",
                (state, card.approval_id),
            )
        self._log_event(card.approval_id, state, actor, reason)

    # ------------------------------------------------------------------
    # Consume (1 lần) + quét hết hạn
    # ------------------------------------------------------------------
    def consume(
        self,
        approval_id: str,
        *,
        actor: str = "supervisor",
        action_fingerprint: str | None = None,
    ) -> ApprovalCard:
        """Đánh dấu card đã dùng khi bắt đầu thực thi. Tái dùng → từ chối (nonce).

        DEOM V4 §6.2: nếu `action_fingerprint` được cung cấp → bắt buộc khớp
        fingerprint đã lưu khi tạo card. Lệch → FINGERPRINT_MISMATCH, card KHÔNG
        bị tiêu (vẫn consume được sau khi làm rõ). Card cũ chưa có fingerprint
        (NULL) → từ chối khi consume kèm fingerprint (fail-closed).
        """
        card = self.get_card(approval_id)
        if card is None:
            raise ApprovalCardError(f"approval card {approval_id} not found")
        # Hết hạn → từ chối dù đang ở state nào (fail-closed, cả APPROVED)
        if self._is_expired(card):
            if card.state != CARD_STATE_EXPIRED:
                self._set_state(card, CARD_STATE_EXPIRED, actor="system", reason="expired at consume time")
            raise ApprovalCardError(f"card {approval_id} expired — cannot consume")
        if card.state != CARD_STATE_APPROVED:
            raise ApprovalCardError(f"card is {card.state}, only APPROVED can be consumed")
        if card.consumed_at_utc:
            raise ApprovalCardError(
                f"card {approval_id} already consumed at {card.consumed_at_utc} — one-time use enforced"
            )
        # DEOM V4 §6.2 — binding nội dung hành động đã duyệt
        if action_fingerprint is not None:
            stored = getattr(card, "action_fingerprint", None)
            if not stored:
                self._log_event(
                    approval_id,
                    "FINGERPRINT_REJECTED_NO_BINDING",
                    actor,
                    "card has no stored fingerprint — re-request approval with binding",
                )
                raise ApprovalCardError(
                    f"card {approval_id} has no action_fingerprint binding — fail-closed, request a new card"
                )
            if stored != action_fingerprint:
                self._log_event(
                    approval_id,
                    "FINGERPRINT_MISMATCH",
                    actor,
                    "action content changed after approval — consume refused, card intact",
                )
                raise ApprovalCardError(
                    f"card {approval_id} fingerprint mismatch — action changed after approval (fail-closed)"
                )
        now = _now()
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE approval_cards_v2 SET consumed_at_utc = ? WHERE approval_id = ?",
                (now, approval_id),
            )
        self._log_event(approval_id, "CONSUMED", actor, "one-time use")
        return self.get_card(approval_id)  # type: ignore[return-value]

    def expire_overdue(self) -> list[str]:
        """Quét card PENDING quá hạn → EXPIRED (watchdog gọi định kỳ)."""
        now = datetime.now(timezone.utc).isoformat()
        with self._lock, self._conn:
            rows = self._conn.execute(
                "SELECT * FROM approval_cards_v2 WHERE state = ?",
                (CARD_STATE_PENDING,),
            ).fetchall()
        expired: list[str] = []
        for row in rows:
            if row["expires_at_utc"] <= now:
                self._set_state(
                    self._row_to_card(row), CARD_STATE_EXPIRED, actor="system", reason="ttl passed (watchdog sweep)"
                )
                expired.append(row["approval_id"])
        return expired

    def close(self) -> None:
        self._conn.close()
