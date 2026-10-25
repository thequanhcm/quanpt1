"""Consultation & Interactive Approval Inbox for QUAN AI BRAIN.

Provides an auditable, SQLite-backed consultation inbox where QUAN AI BRAIN
submits strategic proposals, architecture questions, code upgrade proposals,
and risk evaluations for the owner (Quanpt1) to review, approve, reject, or direct.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import json
from pathlib import Path
import sqlite3
from threading import RLock
from typing import Any
import uuid


class ConsultationCategory(str, Enum):
    CODE_PATCH_R4 = "CODE_PATCH_R4"
    STRATEGIC_DIRECTION = "STRATEGIC_DIRECTION"
    ECOSYSTEM_ADAPTER = "ECOSYSTEM_ADAPTER"
    TASK_ORCHESTRATION = "TASK_ORCHESTRATION"
    RISK_ESCALATION = "RISK_ESCALATION"
    CONTINUOUS_LEARNING = "CONTINUOUS_LEARNING"


class TicketStatus(str, Enum):
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    DIRECTED = "DIRECTED"


@dataclass
class ConsultationTicket:
    ticket_id: str
    title: str
    category: ConsultationCategory
    priority: str  # "URGENT", "HIGH", "MEDIUM", "LOW"
    context_summary: str
    proposed_action: str
    options: list[dict[str, str]] = field(default_factory=list)
    status: TicketStatus = TicketStatus.PENDING_REVIEW
    owner_decision: str = ""
    owner_guidance: str = ""
    created_at: str = ""
    resolved_at: str | None = None
    evidence_notes: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ticket_id": self.ticket_id,
            "title": self.title,
            "category": self.category.value if isinstance(self.category, ConsultationCategory) else str(self.category),
            "priority": self.priority,
            "context_summary": self.context_summary,
            "proposed_action": self.proposed_action,
            "options": self.options,
            "status": self.status.value if isinstance(self.status, TicketStatus) else str(self.status),
            "owner_decision": self.owner_decision,
            "owner_guidance": self.owner_guidance,
            "created_at": self.created_at,
            "resolved_at": self.resolved_at,
            "evidence_notes": self.evidence_notes,
            "metadata": self.metadata,
        }


DEFAULT_SEED_TICKETS: list[ConsultationTicket] = [
    ConsultationTicket(
        ticket_id="cst_ollama_r4",
        title="Phê duyệt Áp dụng Bản vá Tự Động Phát Hiện Ollama Offline <=50ms (R4)",
        category=ConsultationCategory.CODE_PATCH_R4,
        priority="HIGH",
        context_summary=(
            "Khi daemon Ollama ngoại tuyến hoặc chưa được bật, các tiến trình gọi LLM mất 3.0s chờ timeout "
            "do TCP connection refused lặp lại. Cơ chế tự học đã nghiên cứu và sinh bản vá pre-flight socket probe "
            "với độ tự tin 91.0%, giúp phát hiện trong <=50ms và kích hoạt fallback mô phỏng ngay lập tức."
        ),
        proposed_action=(
            "Cập nhật `src/quan_ai_brain/llm/ollama_client.py` với socket probe pre-flight và bộ đếm cooldown an toàn. "
            "Toàn bộ 214 bài kiểm thử hồi quy đã vượt qua trong vùng cách ly."
        ),
        options=[
            {"id": "opt_apply", "label": "Đồng ý áp dụng bản vá ngay vào mã nguồn", "action": "APPROVE"},
            {"id": "opt_manual", "label": "Giữ nguyên, chỉ chạy thử nghiệm dry-run", "action": "REJECT"},
            {"id": "opt_adjust", "label": "Chỉ đạo chỉnh sửa thêm tham số timeout", "action": "DIRECT"},
        ],
        status=TicketStatus.PENDING_REVIEW,
        created_at="2026-10-19T06:45:00Z",
        evidence_notes="Verified by SelfLearningEngine dry-run cycle & proposal prop_34405581",
        metadata={"proposal_id": "prop_34405581", "confidence": 0.91},
    ),
    ConsultationTicket(
        ticket_id="cst_satellite_dc",
        title="Tham vấn Ý Kiến về Kế hoạch Kết Nối Read-Only Adapter sang DC-COMMAND & SKILL_BAT_AI",
        category=ConsultationCategory.ECOSYSTEM_ADAPTER,
        priority="MEDIUM",
        context_summary=(
            "Theo điều lệ bảo tồn của Chủ nhân, các dự án vệ tinh `DC-COMMAND`, `SKILL_BAT_AI`, `BATTERY_AI_V4` "
            "và `BOT` đang được bảo toàn nguyên vẹn. Để nâng cao năng lực trợ lý điều hành số trong quản trị "
            "trung tâm dữ liệu và giám sát pin, Brain đề xuất xây dựng Adapter một chiều (read-only)."
        ),
        proposed_action=(
            "Xây dựng `dc_command_reader_adapter.py` và `battery_ai_reader_adapter.py` với PathGuard nghiêm ngặt, "
            "chỉ đọc sơ đồ cảm biến và tài liệu SOP, tuyệt đối không ghi đè bất kỳ tệp tin nào."
        ),
        options=[
            {"id": "opt_allow_readonly", "label": "Đồng ý cho phép mở Adapter Read-Only", "action": "APPROVE"},
            {"id": "opt_keep_isolated", "label": "Chưa kết nối, tiếp tục giữ cô lập 100%", "action": "REJECT"},
            {"id": "opt_specific_scope", "label": "Chỉ đạo phạm vi dữ liệu được phép đọc", "action": "DIRECT"},
        ],
        status=TicketStatus.PENDING_REVIEW,
        created_at="2026-10-19T07:10:00Z",
        evidence_notes="Preservation rule compliant; zero-write boundary enforced",
        metadata={"target_ecosystems": ["DC-COMMAND", "SKILL_BAT_AI"]},
    ),
    ConsultationTicket(
        ticket_id="cst_nightly_learning",
        title="Tham vấn Khung Giờ & Nội Dung Kế Hoạch Tự Học Định Kỳ Ban Đêm",
        category=ConsultationCategory.CONTINUOUS_LEARNING,
        priority="MEDIUM",
        context_summary=(
            "Hệ thống đã có Động cơ Tự học V1 (SelfLearningEngine). Brain cần ý kiến chỉ đạo của Anh về "
            "lịch trình tự học định kỳ tự động và nội dung cần ưu tiên tích lũy hàng ngày."
        ),
        proposed_action=(
            "Lên lịch chạy chu kỳ tự học lúc 02:00 sáng: tự phân tích log lỗi, rà soát khoảng trống tri thức "
            "về quản trị hệ thống, lập báo cáo tóm tắt sẵn sàng cho Anh phê duyệt trên giao diện lúc 07:00 sáng."
        ),
        options=[
            {"id": "opt_nightly_ok", "label": "Đồng ý lịch trình tự học 02:00 sáng hàng ngày", "action": "APPROVE"},
            {"id": "opt_manual_only", "label": "Chỉ tự học khi Anh nhấn nút thủ công trên UI", "action": "DIRECT"},
            {"id": "opt_custom_hours", "label": "Điều chỉnh sang khung giờ khác theo chỉ đạo", "action": "DIRECT"},
        ],
        status=TicketStatus.PENDING_REVIEW,
        created_at="2026-10-19T08:00:00Z",
        evidence_notes="Complies with quarantine-first learning policy",
        metadata={"scheduled_time": "02:00", "report_time": "07:00"},
    ),
]


class ConsultationStore:
    """Persistent SQLite store for consultation tickets and owner decisions."""

    def __init__(self, db_path: str | Path = "data/consultations.db") -> None:
        self._lock = RLock()
        self.is_memory = str(db_path) == ":memory:"
        if not self.is_memory:
            path = Path(db_path).resolve()
            path.parent.mkdir(parents=True, exist_ok=True)
            self.db_path = path
            self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        else:
            self.db_path = Path(":memory:")
            self._conn = sqlite3.connect(":memory:", check_same_thread=False)

        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        if not self.is_memory:
            self._conn.execute("PRAGMA journal_mode = WAL")
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS consultation_tickets (
                    ticket_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    category TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    context_summary TEXT NOT NULL,
                    proposed_action TEXT NOT NULL,
                    options_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    owner_decision TEXT DEFAULT '',
                    owner_guidance TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    resolved_at TEXT,
                    evidence_notes TEXT DEFAULT '',
                    metadata_json TEXT DEFAULT '{}'
                )
                """
            )
            # Check if empty, seed defaults
            cursor = self._conn.execute("SELECT COUNT(*) as cnt FROM consultation_tickets")
            row = cursor.fetchone()
            if row and row["cnt"] == 0:
                for t in DEFAULT_SEED_TICKETS:
                    self._insert_ticket_unlocked(t)

    def _insert_ticket_unlocked(self, t: ConsultationTicket) -> None:
        self._conn.execute(
            """
            INSERT OR REPLACE INTO consultation_tickets (
                ticket_id, title, category, priority, context_summary, proposed_action,
                options_json, status, owner_decision, owner_guidance, created_at,
                resolved_at, evidence_notes, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                t.ticket_id,
                t.title,
                t.category.value if isinstance(t.category, ConsultationCategory) else str(t.category),
                t.priority,
                t.context_summary,
                t.proposed_action,
                json.dumps(t.options, ensure_ascii=False),
                t.status.value if isinstance(t.status, TicketStatus) else str(t.status),
                t.owner_decision,
                t.owner_guidance,
                t.created_at or datetime.now(timezone.utc).isoformat(),
                t.resolved_at,
                t.evidence_notes,
                json.dumps(t.metadata, ensure_ascii=False),
            ),
        )

    def create_ticket(self, ticket: ConsultationTicket) -> str:
        with self._lock, self._conn:
            if not ticket.ticket_id:
                ticket.ticket_id = f"cst_{uuid.uuid4().hex[:8]}"
            if not ticket.created_at:
                ticket.created_at = datetime.now(timezone.utc).isoformat()
            self._insert_ticket_unlocked(ticket)
            return ticket.ticket_id

    def list_tickets(
        self,
        status: TicketStatus | str | None = None,
        category: ConsultationCategory | str | None = None,
    ) -> list[ConsultationTicket]:
        with self._lock:
            query = "SELECT * FROM consultation_tickets WHERE 1=1"
            params: list[Any] = []
            if status is not None:
                val = status.value if isinstance(status, TicketStatus) else str(status)
                query += " AND status = ?"
                params.append(val)
            if category is not None:
                val = category.value if isinstance(category, ConsultationCategory) else str(category)
                query += " AND category = ?"
                params.append(val)
            query += " ORDER BY CASE priority WHEN 'URGENT' THEN 1 WHEN 'HIGH' THEN 2 WHEN 'MEDIUM' THEN 3 ELSE 4 END, created_at DESC"

            cursor = self._conn.execute(query, params)
            results: list[ConsultationTicket] = []
            for r in cursor.fetchall():
                results.append(
                    ConsultationTicket(
                        ticket_id=r["ticket_id"],
                        title=r["title"],
                        category=ConsultationCategory(r["category"]) if r["category"] in ConsultationCategory._value2member_map_ else ConsultationCategory.STRATEGIC_DIRECTION,
                        priority=r["priority"],
                        context_summary=r["context_summary"],
                        proposed_action=r["proposed_action"],
                        options=json.loads(r["options_json"] or "[]"),
                        status=TicketStatus(r["status"]) if r["status"] in TicketStatus._value2member_map_ else TicketStatus.PENDING_REVIEW,
                        owner_decision=r["owner_decision"],
                        owner_guidance=r["owner_guidance"],
                        created_at=r["created_at"],
                        resolved_at=r["resolved_at"],
                        evidence_notes=r["evidence_notes"],
                        metadata=json.loads(r["metadata_json"] or "{}"),
                    )
                )
            return results

    def get_ticket(self, ticket_id: str) -> ConsultationTicket | None:
        with self._lock:
            cursor = self._conn.execute(
                "SELECT * FROM consultation_tickets WHERE ticket_id = ?",
                (ticket_id,),
            )
            r = cursor.fetchone()
            if not r:
                return None
            return ConsultationTicket(
                ticket_id=r["ticket_id"],
                title=r["title"],
                category=ConsultationCategory(r["category"]) if r["category"] in ConsultationCategory._value2member_map_ else ConsultationCategory.STRATEGIC_DIRECTION,
                priority=r["priority"],
                context_summary=r["context_summary"],
                proposed_action=r["proposed_action"],
                options=json.loads(r["options_json"] or "[]"),
                status=TicketStatus(r["status"]) if r["status"] in TicketStatus._value2member_map_ else TicketStatus.PENDING_REVIEW,
                owner_decision=r["owner_decision"],
                owner_guidance=r["owner_guidance"],
                created_at=r["created_at"],
                resolved_at=r["resolved_at"],
                evidence_notes=r["evidence_notes"],
                metadata=json.loads(r["metadata_json"] or "{}"),
            )

    def respond_ticket(
        self,
        ticket_id: str,
        decision: str,
        guidance: str = "",
    ) -> ConsultationTicket:
        """Owner responds to a consultation ticket: APPROVE, REJECT, or DIRECT."""
        with self._lock, self._conn:
            ticket = self.get_ticket(ticket_id)
            if not ticket:
                raise ValueError(f"Consultation ticket '{ticket_id}' not found")

            decision_norm = decision.strip().upper()
            if decision_norm in ("APPROVE", "APPROVED", "DONG_Y", "ĐỒNG Ý"):
                new_status = TicketStatus.APPROVED
            elif decision_norm in ("REJECT", "REJECTED", "TU_CHOI", "TỪ CHỐI"):
                new_status = TicketStatus.REJECTED
            elif decision_norm in ("DIRECT", "DIRECTED", "CHI_DAO", "CHỈ ĐẠO"):
                new_status = TicketStatus.DIRECTED
            else:
                new_status = TicketStatus.DIRECTED

            now_iso = datetime.now(timezone.utc).isoformat()
            self._conn.execute(
                """
                UPDATE consultation_tickets
                SET status = ?, owner_decision = ?, owner_guidance = ?, resolved_at = ?
                WHERE ticket_id = ?
                """,
                (new_status.value, decision.strip(), guidance.strip(), now_iso, ticket_id),
            )
            return self.get_ticket(ticket_id)  # type: ignore[return-value]

    def count_pending(self) -> int:
        with self._lock:
            cursor = self._conn.execute(
                "SELECT COUNT(*) as cnt FROM consultation_tickets WHERE status = ?",
                (TicketStatus.PENDING_REVIEW.value,),
            )
            row = cursor.fetchone()
            return int(row["cnt"]) if row else 0

    def close(self) -> None:
        with self._lock:
            self._conn.close()
