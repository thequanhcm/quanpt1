"""Sprint 10 (a): Email Intelligence — đề xuất xử lý có căn cứ cho email đã tiếp nhận.

Deterministic (không LLM): luật phân loại từ keyword + kinh nghiệm liên quan từ
experience_retrieval (Sprint 9 D). Đề xuất đủ 11 trường §VI.3 của master prompt.
Nguyên tắc trung thực:
- Giả định chưa xác minh được liệt kê RÕ trong "assumptions", ghi nguồn mock.
- Kinh nghiệm candidates xuất hiện ở "candidates_not_confirmed" — không đếm là căn cứ.
- Email FYI/NEWSLETTER/DUPLICATE/UNCLEAR KHÔNG tạo đề xuất xử lý.
"""
from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from quan_ai_brain.integration.email_intake import (
    EmailCategory,
    EmailIntakeStore,
    EmailMessage,
)
from quan_ai_brain.memory.experience_retrieval import find_similar_experiences
from quan_ai_brain.memory.sqlite_store import MemoryStore

PROPOSAL_STATUSES = ("PROPOSED", "TASK_CREATED", "DISMISSED")


@dataclass
class EmailProposal:
    """Đề xuất xử lý 1 email — đủ §VI.3, truy vết được nguồn."""

    proposal_id: str
    message_id: str
    subject: str
    sender: str
    goal: str
    basis: list[str] = field(default_factory=list)          # căn cứ + nguồn
    conclusion: str = ""
    assumptions: list[str] = field(default_factory=list)     # giả định CHƯA xác minh
    recommended_action: str = ""
    alternatives: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    action_scope: str = ""                                   # phạm vi hành động đề xuất
    success_criteria: list[str] = field(default_factory=list)
    rollback: str = ""
    owner_decision_needed: str = ""
    experience_confirmed: list[dict[str, Any]] = field(default_factory=list)
    experience_candidates: list[dict[str, Any]] = field(default_factory=list)
    research_links: list[dict[str, Any]] = field(default_factory=list)  # Sprint 12 (d)
    status: str = "PROPOSED"
    linked_task_id: str = ""
    created_at_utc: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "message_id": self.message_id,
            "subject": self.subject,
            "sender": self.sender,
            "goal": self.goal,
            "basis": self.basis,
            "conclusion": self.conclusion,
            "assumptions": self.assumptions,
            "recommended_action": self.recommended_action,
            "alternatives": self.alternatives,
            "risks": self.risks,
            "action_scope": self.action_scope,
            "success_criteria": self.success_criteria,
            "rollback": self.rollback,
            "owner_decision_needed": self.owner_decision_needed,
            "experience_confirmed": self.experience_confirmed,
            "experience_candidates": self.experience_candidates,
            "research_links": self.research_links,
            "status": self.status,
            "linked_task_id": self.linked_task_id,
            "created_at_utc": self.created_at_utc,
        }


# ---------------------------------------------------------------------------
# Proposal store — bảng riêng trong cùng DB intake (đơn giản, cùng nguồn)
# ---------------------------------------------------------------------------

class ProposalStore:
    """Lưu đề xuất email; idempotent theo message_id (1 email ACTIVE = 1 đề xuất)."""

    def __init__(self, db_path: str | Path) -> None:
        path = Path(db_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS email_proposals (
                    proposal_id TEXT PRIMARY KEY,
                    message_id TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    sender TEXT NOT NULL,
                    goal TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'PROPOSED',
                    linked_task_id TEXT DEFAULT '',
                    created_at_utc TEXT NOT NULL
                )
                """
            )
            self._conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_proposals_msg ON email_proposals (message_id)"
            )

    def has_for_message(self, message_id: str) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM email_proposals WHERE message_id = ?", (message_id,)
        ).fetchone()
        return row is not None

    def save(self, proposal: EmailProposal) -> bool:
        """Lưu đề xuất. False nếu email này đã có đề xuất (không ghi đè)."""
        if self.has_for_message(proposal.message_id):
            return False
        import json as _json

        with self._conn:
            self._conn.execute(
                """
                INSERT INTO email_proposals
                    (proposal_id, message_id, subject, sender, goal, payload_json,
                     status, linked_task_id, created_at_utc)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    proposal.proposal_id,
                    proposal.message_id,
                    proposal.subject,
                    proposal.sender,
                    proposal.goal,
                    _json.dumps(proposal.to_dict(), ensure_ascii=False),
                    proposal.status,
                    proposal.linked_task_id,
                    proposal.created_at_utc
                    or datetime.now(timezone.utc).isoformat(),
                ),
            )
        return True

    def get(self, proposal_id: str) -> dict[str, Any] | None:
        import json as _json

        row = self._conn.execute(
            "SELECT * FROM email_proposals WHERE proposal_id = ?", (proposal_id,)
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        d["payload"] = _json.loads(d.pop("payload_json"))
        return d

    def link_task(self, proposal_id: str, task_id: str) -> bool:
        """Gắn task_id; False nếu proposal không tồn tại hoặc đã gắn task khác."""
        row = self._conn.execute(
            "SELECT linked_task_id FROM email_proposals WHERE proposal_id = ?",
            (proposal_id,),
        ).fetchone()
        if not row:
            return False
        if row["linked_task_id"] and row["linked_task_id"] != task_id:
            return False
        with self._conn:
            self._conn.execute(
                "UPDATE email_proposals SET status = 'TASK_CREATED', linked_task_id = ? WHERE proposal_id = ?",
                (task_id, proposal_id),
            )
        return True

    def list_proposals(self, limit: int = 50) -> list[dict[str, Any]]:
        import json as _json

        cur = self._conn.execute(
            "SELECT * FROM email_proposals ORDER BY created_at_utc DESC LIMIT ?", (limit,)
        )
        out = []
        for row in cur.fetchall():
            d = dict(row)
            d["payload"] = _json.loads(d.pop("payload_json"))
            out.append(d)
        return out


# ---------------------------------------------------------------------------
# Proposal builder — deterministic
# ---------------------------------------------------------------------------

# Điểm khảo sát nội dung email để dựng đề xuất (luật rõ ràng, kiểm tra được)
_ACTION_FACTORS = {
    "deadline": ("deadline", "hạn", "trước", "gấp"),
    "report": ("báo cáo", "report", "tổng hợp"),
    "meeting": ("họp", "cuộc họp", "lịch", "meeting"),
    "approval": ("duyệt", "phê duyệt", "xác nhận", "ký"),
}


def build_proposal(
    msg: EmailMessage,
    memory_store: MemoryStore,
    *,
    proposal_id: str | None = None,
) -> EmailProposal | None:
    """Dựng đề xuất cho email ACTION_REQUIRED. None nếu email không đủ điều kiện.

    Trả None cho FYI/NEWSLETTER/DUPLICATE/UNCLEAR — không tạo đề xuất cưỡng bách.
    """
    if msg.category != EmailCategory.ACTION_REQUIRED:
        return None

    text = f"{msg.subject}\n{msg.body_preview}".lower()
    factors = [name for name, keys in _ACTION_FACTORS.items() if any(k in text for k in keys)]

    basis = [
        f"Email {msg.message_id} (nguồn: {msg.source}) từ {msg.sender} — chủ đề: {msg.subject}",
        f"Phân loại ACTION_REQUIRED do chứa tín hiệu: {', '.join(factors) if factors else 'yêu cầu trực tiếp'}",
        "Luật phân loại deterministic Sprint 10 — chưa có LLM; email thật chưa khả dụng (Vmail BLOCKED)",
    ]
    assumptions = [
        f"Nội dung email hiểu từ 500 ký tự đầu (body_preview) — chưa đọc toàn văn",
        f"Người gửi '{msg.sender}' chưa xác minh danh tính/xác thực",
        "Connector nguồn là MOCK — khi có email thật, đề xuất phải dựng lại từ dữ liệu thật",
    ]
    if not factors:
        assumptions.append("Không nhận diện tín hiệu cụ thể (deadline/báo cáo/họp/duyệt) — đề xuất chung")

    goal = f"Xử lý yêu cầu từ email: {msg.subject}"

    # Kinh nghiệm liên quan — confirmed là căn cứ phụ, candidates chỉ liệt kê
    exp = find_similar_experiences(memory_store, f"{msg.subject} {msg.body_preview}", limit=3)
    confirmed_titles = [e["content"] for e in exp["confirmed"]]
    candidate_titles = [e["content"] for e in exp["candidates"]]
    for t in confirmed_titles:
        basis.append(f"Kinh nghiệm đã xác nhận liên quan: {t}")

    # Sprint 12 (d): research links khi bối cảnh cần nghiên cứu — fail-closed,
    # lỗi web KHÔNG phá proposal (bỏ qua im lặng nhưng ghi vào basis nếu có).
    research_links: list[dict[str, Any]] = []
    research_signals = ("nghiên cứu", "tìm hiểu", "tham khảo", "research", "tìm kiếm", "tra cứu")
    if any(s in text for s in research_signals):
        try:
            from quan_ai_brain.integration.web_connector import BingRssSearcher

            hits = BingRssSearcher().search(msg.subject, max_results=3)
            research_links = [
                {"title": h["title"], "url": h["url"], "source": "web_read_only", "verified": False}
                for h in hits
            ]
            if research_links:
                basis.append(
                    "Nguồn tham khảo web READ-ONLY (chưa xác minh — chỉ để đọc thêm): "
                    + "; ".join(h["url"] for h in research_links)
                )
        except Exception:
            research_links = []  # fail-closed — không có mạng thì proposal như cũ

    recommended = "Soạn nhiệm vụ ứng viên cho anh duyệt: xác minh yêu cầu, chuẩn bị bản nháp trả lời/báo cáo (draft-only, không gửi)"
    alternatives = [
        "Bỏ qua email (nếu anh xác nhận không quan trọng)",
        "Hỏ lại người gửi để làm rõ yêu cầu trước khi hành động",
    ]
    risks = [
        "Hiểu sai yêu cầu từ nội dung email (đặc biệt nếu email thật phức tạp hơn mock)",
        "Kinh nghiệm liên quan có thể không áp dụng được cho tình huống mới (bối cảnh khác)",
        "Email nguồn là mock — mọi quyết định dựa trên email thật phải dựng lại đề xuất",
    ]
    success = [
        "Anh xác nhận đề xuất đúng ý yêu cầu của email",
        "Nhiệm vụ ứng viên được tạo PENDING (không tự thực thi)",
        "Bản nháp trả lời (nếu có) là draft-only, anh tự quyết định gửi",
    ]

    return EmailProposal(
        proposal_id=proposal_id or f"prop_{uuid.uuid4().hex[:12]}",
        message_id=msg.message_id,
        subject=msg.subject,
        sender=msg.sender,
        goal=goal,
        basis=basis,
        conclusion=f"Email cần xử lý: {msg.subject} (tín hiệu: {', '.join(factors) or 'yêu cầu trực tiếp'})",
        assumptions=assumptions,
        recommended_action=recommended,
        alternatives=alternatives,
        risks=risks,
        action_scope="Đọc + soạn nháp trong workspace (R1–R2); KHÔNG gửi mail, KHÔNG ra ngoài",
        success_criteria=success,
        rollback="Xoá đề xuất + nhiệm vụ ứng viên PENDING; không có side effect bên ngoài",
        owner_decision_needed="Duyệt tạo nhiệm vụ ứng viên, hoặc bỏ qua, hoặc yêu cầu làm rõ",
        experience_confirmed=exp["confirmed"],
        experience_candidates=exp["candidates"],
        research_links=research_links,
        status="PROPOSED",
        created_at_utc=datetime.now(timezone.utc).isoformat(),
    )


def generate_proposals_for_intake(
    intake_db: str | Path,
    memory_store: MemoryStore,
) -> dict[str, Any]:
    """Quét intake_emails, tạo đề xuất cho email ACTION_REQUIRED chưa có đề xuất."""
    intake = EmailIntakeStore(intake_db)
    store = ProposalStore(intake_db)
    created, skipped_category, already = 0, 0, 0
    for row in intake.list_emails(limit=100):
        msg = EmailMessage(
            message_id=row["message_id"],
            sender=row["sender"],
            subject=row["subject"],
            body_preview=row["body_preview"],
            received_at_utc=row["received_at_utc"],
            source=row["source"],
            category=EmailCategory(row["category"]),
        )
        if msg.category != EmailCategory.ACTION_REQUIRED:
            skipped_category += 1
            continue
        if store.has_for_message(msg.message_id):
            already += 1
            continue
        proposal = build_proposal(msg, memory_store)
        if proposal and store.save(proposal):
            created += 1
    return {"created": created, "skipped_category": skipped_category, "already_existed": already}
