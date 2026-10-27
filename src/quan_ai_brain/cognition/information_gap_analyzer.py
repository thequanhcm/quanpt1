"""QUAN AI BRAIN — Information Gap Awareness Engine (V3 Sprint 3).

Phat hien khoang trong thong tin trong yeu cau cua chu nhan, phan loai theo
9 nhom (A-I) cua Master Prompt V3 §3.2, quyet dinh READY /
NEEDS_OWNER_INPUT / NEEDS_VERIFICATION, sinh cau hoi co cau truc va dutri
trang thai cho ben vgom cho den khi du can cu tiep tuc.

Nguyen tac bat bien:
- KHONG bien thong tin chua biet thanh gia dinh ngam trinh bay nhu su that.
- KHONG nham thong tin voi quyen han: tra loi cau hoi KHONG PHAI phe duyet.
- Truong chua xac dinh ghi UNKNOWN/MISSING - khong dien gia tuong tuong.
- Nhom I (thieu phe duyet) DO ApprovalOrchestrator hien co xu ly - module nay
  chi nhan dien va chuyen huong, khong tao card phe duyet.
- Khong hoi lai chu nhan nhung gi da co nguong tin cay (VERIFIED/
  OWNER_PROVIDED con hieu luc) - tu tim truoc khi hoi (V3 §4).
- Im lang KHONG dong nghia dong y. Khong coi timeout la quyen tiep tuc (§9).
"""
from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Trang thai & phan loai (V3 §3.2, §5, §8)
# ---------------------------------------------------------------------------


class ReadinessStatus(str, Enum):
    """Ba trang thai chinh truoc khi chuyen UNDERSTANDING -> PLANNING (V3 §5)."""

    READY = "READY"
    NEEDS_OWNER_INPUT = "NEEDS_OWNER_INPUT"
    NEEDS_VERIFICATION = "NEEDS_VERIFICATION"


class GapCategory(str, Enum):
    """9 nhom thong tin thieu (Master Prompt V3 §3.2)."""

    GOAL = "A_GOAL"
    INPUT_DATA = "B_INPUT_DATA"
    CONTEXT = "C_CONTEXT"
    ACCEPTANCE = "D_ACCEPTANCE"
    CONSTRAINTS = "E_CONSTRAINTS"
    ACCESS = "F_ACCESS"
    OWNER_DECISION = "G_OWNER_DECISION"
    VERIFICATION = "H_VERIFICATION"
    APPROVAL = "I_APPROVAL"  # chuyen ApprovalOrchestrator, khong tron


class WaitingState(str, Enum):
    """Trang thai cho ben vong (V3 §8)."""

    WAITING_FOR_OWNER_INPUT = "WAITING_FOR_OWNER_INPUT"
    WAITING_FOR_OWNER_GUIDANCE = "WAITING_FOR_OWNER_GUIDANCE"
    WAITING_FOR_EVIDENCE = "WAITING_FOR_EVIDENCE"
    WAITING_FOR_OWNER_DECISION = "WAITING_FOR_OWNER_DECISION"
    RESOLVED = "RESOLVED"
    CANCELLED = "CANCELLED"

    @classmethod
    def from_readiness(cls, readiness: "ReadinessStatus") -> "WaitingState":
        if readiness is ReadinessStatus.READY:
            return cls.RESOLVED
        if readiness is ReadinessStatus.NEEDS_VERIFICATION:
            return cls.WAITING_FOR_EVIDENCE
        return cls.WAITING_FOR_OWNER_INPUT


class EvidenceKind(str, Enum):
    """Nguon goc cua moi mau thong tin trong Task Specification (V3 §3.1)."""

    VERIFIED = "VERIFIED"
    OWNER_PROVIDED = "OWNER_PROVIDED"
    RETRIEVED = "RETRIEVED"
    INFERRED = "INFERRED"
    ASSUMPTION = "ASSUMPTION"
    UNKNOWN = "UNKNOWN"
    CONFLICTED = "CONFLICTED"


# ---------------------------------------------------------------------------
# Model cau truc
# ---------------------------------------------------------------------------


@dataclass
class InfoItem:
    """Mot mau thong tin trong known_facts / required_inputs.

    value=None + evidence=UNKNOWN nghia la CHUA BIET - khong tu dien.
    """

    key: str
    value: Any = None
    evidence: EvidenceKind = EvidenceKind.UNKNOWN
    source_ref: str = ""
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["evidence"] = self.evidence.value
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "InfoItem":
        return cls(
            key=d.get("key", ""),
            value=d.get("value"),
            evidence=EvidenceKind(d.get("evidence", "UNKNOWN")),
            source_ref=d.get("source_ref", ""),
            note=d.get("note", ""),
        )


@dataclass
class ClarifyingQuestion:
    """Cau hoi cho chu nhan (V3 §6) - phai giai thich vi sao can thiet."""

    question_id: str
    related_task_id: str
    question: str
    reason: str
    why_it_matters: str
    expected_answer_type: str = "text"
    required_or_optional: str = "REQUIRED"
    impact_if_unanswered: str = ""
    options: list[str] = field(default_factory=list)  # toi da 3 lua chon
    status: str = "OPEN"  # OPEN -> ANSWERED
    category: GapCategory = GapCategory.INPUT_DATA
    answer: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["category"] = self.category.value
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ClarifyingQuestion":
        return cls(
            question_id=d.get("question_id", ""),
            related_task_id=d.get("related_task_id", ""),
            question=d.get("question", ""),
            reason=d.get("reason", ""),
            why_it_matters=d.get("why_it_matters", ""),
            expected_answer_type=d.get("expected_answer_type", "text"),
            required_or_optional=d.get("required_or_optional", "REQUIRED"),
            impact_if_unanswered=d.get("impact_if_unanswered", ""),
            options=list(d.get("options", []))[:3],
            status=d.get("status", "OPEN"),
            category=GapCategory(d.get("category", "B_INPUT_DATA")),
            answer=d.get("answer", ""),
        )


@dataclass
class TaskSpecification:
    """Task Specification co cau truc (V3 §3.1) - truong chua biet = UNKNOWN."""

    task_id: str
    task_goal: str
    expected_outcome: str = "UNKNOWN"
    acceptance_criteria: list[str] = field(default_factory=list)
    known_facts: list[InfoItem] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    available_resources: list[str] = field(default_factory=list)
    required_inputs: list[InfoItem] = field(default_factory=list)
    missing_information: list[GapCategory] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    owner_decisions_required: list[str] = field(default_factory=list)
    next_action: str = "UNKNOWN"
    task_status: str = "UNDERSTANDING"
    questions: list[ClarifyingQuestion] = field(default_factory=list)
    readiness: str = ReadinessStatus.NEEDS_OWNER_INPUT.value
    waiting_state: str = WaitingState.WAITING_FOR_OWNER_INPUT.value

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_goal": self.task_goal,
            "expected_outcome": self.expected_outcome,
            "acceptance_criteria": list(self.acceptance_criteria),
            "known_facts": [f.to_dict() for f in self.known_facts],
            "evidence_refs": list(self.evidence_refs),
            "available_resources": list(self.available_resources),
            "required_inputs": [i.to_dict() for i in self.required_inputs],
            "missing_information": [c.value for c in self.missing_information],
            "assumptions": list(self.assumptions),
            "constraints": list(self.constraints),
            "risks": list(self.risks),
            "owner_decisions_required": list(self.owner_decisions_required),
            "next_action": self.next_action,
            "task_status": self.task_status,
            "questions": [q.to_dict() for q in self.questions],
            "readiness": self.readiness,
            "waiting_state": self.waiting_state,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "TaskSpecification":
        return cls(
            task_id=d.get("task_id", ""),
            task_goal=d.get("task_goal", ""),
            expected_outcome=d.get("expected_outcome", "UNKNOWN"),
            acceptance_criteria=list(d.get("acceptance_criteria", [])),
            known_facts=[InfoItem.from_dict(x) for x in d.get("known_facts", [])],
            evidence_refs=list(d.get("evidence_refs", [])),
            available_resources=list(d.get("available_resources", [])),
            required_inputs=[InfoItem.from_dict(x) for x in d.get("required_inputs", [])],
            missing_information=[GapCategory(c) for c in d.get("missing_information", [])],
            assumptions=list(d.get("assumptions", [])),
            constraints=list(d.get("constraints", [])),
            risks=list(d.get("risks", [])),
            owner_decisions_required=list(d.get("owner_decisions_required", [])),
            next_action=d.get("next_action", "UNKNOWN"),
            task_status=d.get("task_status", "UNDERSTANDING"),
            questions=[ClarifyingQuestion.from_dict(x) for x in d.get("questions", [])],
            readiness=d.get("readiness", ReadinessStatus.NEEDS_OWNER_INPUT.value),
            waiting_state=d.get("waiting_state", WaitingState.WAITING_FOR_OWNER_INPUT.value),
        )


@dataclass
class GapAnalysis:
    """Ket qua phan tich khoang trong cua mot yeu cau."""

    task_id: str
    readiness: ReadinessStatus
    waiting_state: WaitingState
    missing: list[GapCategory] = field(default_factory=list)
    questions: list[ClarifyingQuestion] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    checked_sources: list[str] = field(default_factory=list)
    reasoning: str = ""
    approval_gate_needed: bool = False
    spec: TaskSpecification | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "readiness": self.readiness.value,
            "waiting_state": self.waiting_state.value,
            "missing": [c.value for c in self.missing],
            "questions": [q.to_dict() for q in self.questions],
            "conflicts": self.conflicts,
            "checked_sources": self.checked_sources,
            "reasoning": self.reasoning,
            "approval_gate_needed": self.approval_gate_needed,
        }


# ---------------------------------------------------------------------------
# InformationGapAnalyzer
# ---------------------------------------------------------------------------

_CLOSING_LINE = (
    "Trạng thái: ĐANG CHỜ ANH QUANPT1 CUNG CẤP THÔNG TIN HOẶC CHỈ ĐẠO. "
    "CHƯA THỰC HIỆN HÀNH ĐỘNG NGHIỆP VỤ."
)


class InformationGapAnalyzer:
    """Phan tich khoang trong thong tin, sinh cau hoi, luu trang thai cho
    ben vong (SQLite) - phuc hoi day du sau restart (V3 §8.3)."""

    def __init__(
        self,
        db_path: str | Path | None = None,
        *,
        workspace: str | Path | None = None,
        remind_interval_hours: float = 12.0,
        max_reminders: int = 5,
        clock: Any = None,
    ) -> None:
        if db_path is None:
            ws = Path(workspace).resolve() if workspace else Path.cwd().resolve()
            db_path = ws / "data" / "information_gaps.db"
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self.remind_interval_hours = remind_interval_hours
        self.max_reminders = max_reminders
        self._init_schema()

    # -- schema -----------------------------------------------------------

    def _init_schema(self) -> None:
        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS info_gap_tasks (
                    task_id TEXT PRIMARY KEY,
                    spec_json TEXT NOT NULL,
                    readiness TEXT NOT NULL,
                    waiting_state TEXT NOT NULL,
                    request_text TEXT NOT NULL DEFAULT '',
                    created_at_utc TEXT NOT NULL,
                    updated_at_utc TEXT NOT NULL,
                    netchat_message_id TEXT NOT NULL DEFAULT '',
                    reminder_count INTEGER NOT NULL DEFAULT 0,
                    last_reminder_utc TEXT NOT NULL DEFAULT ''
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS info_gap_events (
                    event_id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    detail_json TEXT NOT NULL DEFAULT '{}',
                    created_at_utc TEXT NOT NULL
                )
                """
            )

    # -- phan tich --------------------------------------------------------

    def analyze_request(
        self,
        task_id: str,
        request_text: str = "",
        *,
        goal: str = "",
        expected_outcome: str = "",
        acceptance_criteria: list[str] | None = None,
        known_facts: list[InfoItem] | None = None,
        required_inputs: list[InfoItem] | None = None,
        constraints: list[str] | None = None,
        available_resources: list[str] | None = None,
        evidence_refs: list[str] | None = None,
        conflicts: list[str] | None = None,
        owner_decisions_required: list[str] | None = None,
        checked_sources: list[str] | None = None,
        approval_gate_needed: bool = False,
        input_questions: dict[str, str] | None = None,
        input_options: dict[str, list[str]] | None = None,
    ) -> GapAnalysis:
        """Phan tich yeu cau -> GapAnalysis (readiness + cau hoi co cau truc).

        Quy tac (V3 §4, §5.1):
        - Muc tieu mo ho (goal rong) -> NEEDS_OWNER_INPUT, hoi muc tieu.
        - Co mau thuan -> NEEDS_VERIFICATION, neu mau thuan, khong tu chon.
        - required_inputs chua co gia tri (value=None) -> hoi bo sung.
        - Da co san (VERIFIED/OWNER_PROVIDED/RETRIEVED) -> KHONG hoi lai.
        - owner_decisions_required khac rong -> NEEDS_OWNER_INPUT (nhom G).
        - approval_gate_needed=True -> danh dau de caller chuyen
          ApprovalOrchestrator (nhom I); KHONG tao information request.
        """
        acceptance_criteria = list(acceptance_criteria or [])
        known_facts = list(known_facts or [])
        required_inputs = list(required_inputs or [])
        constraints = list(constraints or [])
        available_resources = list(available_resources or [])
        evidence_refs = list(evidence_refs or [])
        conflicts = list(conflicts or [])
        owner_decisions_required = list(owner_decisions_required or [])
        checked_sources = list(checked_sources or [])
        input_questions = dict(input_questions or {})
        input_options = dict(input_options or {})

        questions: list[ClarifyingQuestion] = []
        missing: list[GapCategory] = []

        # --- A. Muc tieu ---
        if not goal or not goal.strip():
            missing.append(GapCategory.GOAL)
            questions.append(
                ClarifyingQuestion(
                    question_id=f"q_{task_id}_goal",
                    related_task_id=task_id,
                    question=(
                        "Anh Quân, em chưa xác định được mục tiêu công việc này "
                        "nhằm giải quyết vấn đề gì và kết quả cuối cùng cần đạt là gì. "
                        "Anh định nghĩa mục tiêu giúp em."
                    ),
                    reason="Mục tiêu công việc chưa được xác định.",
                    why_it_matters=(
                        "Không có mục tiêu rõ ràng thì không thể chọn phương án "
                        "hay kết luận khi nào hoàn thành."
                    ),
                    expected_answer_type="text",
                    required_or_optional="REQUIRED",
                    impact_if_unanswered="Nhiệm vụ không thể lập kế hoạch.",
                    category=GapCategory.GOAL,
                )
            )

        # --- D. Tieu chi nghiem thu ---
        if not acceptance_criteria:
            missing.append(GapCategory.ACCEPTANCE)
            questions.append(
                ClarifyingQuestion(
                    question_id=f"q_{task_id}_acceptance",
                    related_task_id=task_id,
                    question=(
                        "Anh Quân, khi nào có thể kết luận nhiệm vụ đã hoàn thành? "
                        "Tiêu chí nghiệm thu cụ thể là gì?"
                    ),
                    reason="Chưa biết điều kiện coi như xong (fail-closed: không tự đặt tiêu chí thay anh).",
                    why_it_matters="Không có tiêu chí nghiệm thu thì không thể tự xác minh kết quả.",
                    expected_answer_type="list",
                    required_or_optional="REQUIRED",
                    impact_if_unanswered="Không thể VERIFYING - kết luận hoàn thành sẽ là tự ý.",
                    category=GapCategory.ACCEPTANCE,
                )
            )

        # --- B. Du lieu dau vao thieu ---
        for item in required_inputs:
            if item.value is not None:
                continue  # da co du lieu - khong hoi lai (V3 §4)
            missing.append(GapCategory.INPUT_DATA)
            questions.append(
                ClarifyingQuestion(
                    question_id=f"q_{task_id}_input_{item.key}",
                    related_task_id=task_id,
                    question=input_questions.get(item.key) or _render_input_question(item),
                    reason=f"Thiếu dữ liệu đầu vào '{item.key}'.",
                    why_it_matters=item.note or "Dữ liệu này quyết định kết quả công việc.",
                    expected_answer_type="text",
                    required_or_optional="REQUIRED",
                    impact_if_unanswered="Không thể tiếp tục bước kế hoạch.",
                    options=input_options.get(item.key, [])[:3],
                    category=GapCategory.INPUT_DATA,
                )
            )

        # --- H. Mau thuan du kien -> NEEDS_VERIFICATION ---
        for idx, conflict in enumerate(conflicts, 1):
            missing.append(GapCategory.VERIFICATION)
            questions.append(
                ClarifyingQuestion(
                    question_id=f"q_{task_id}_conflict_{idx}",
                    related_task_id=task_id,
                    question=(
                        f"Anh Quân, các nguồn đang mâu thuẫn: {conflict} "
                        "Anh chỉ đạo ưu tiên nguồn nào hoặc hướng xác minh?"
                    ),
                    reason="Có xung đột giữa dữ kiện - không tự chọn theo cảm tính.",
                    why_it_matters="Kết luận trên dữ kiện mâu thuẫn sẽ sai.",
                    expected_answer_type="choice",
                    required_or_optional="REQUIRED",
                    impact_if_unanswered="Nhiệm vụ dừng ở NEEDS_VERIFICATION.",
                    category=GapCategory.VERIFICATION,
                )
            )

        # --- G. Quyet dinh cua chu nhan ---
        for idx, decision in enumerate(owner_decisions_required, 1):
            missing.append(GapCategory.OWNER_DECISION)
            questions.append(
                ClarifyingQuestion(
                    question_id=f"q_{task_id}_decision_{idx}",
                    related_task_id=task_id,
                    question=decision,
                    reason="Có nhiều phương án hợp lý - việc chọn phụ thuộc ưu tiên của anh.",
                    why_it_matters="Không tự quyết thay chủ nhân (V3 §1, §5.1).",
                    expected_answer_type="choice",
                    required_or_optional="REQUIRED",
                    impact_if_unanswered="Không thể chọn phương án - dừng chờ chỉ đạo.",
                    category=GapCategory.OWNER_DECISION,
                )
            )

        # --- I. Phe duyet: tach rieng, khong tron (V3 §10) ---

        # --- Quyet dinh readiness (V3 §5) ---
        if approval_gate_needed and not questions:
            readiness = ReadinessStatus.NEEDS_OWNER_INPUT
            waiting = WaitingState.WAITING_FOR_OWNER_DECISION
        elif conflicts:
            readiness = ReadinessStatus.NEEDS_VERIFICATION
            waiting = WaitingState.WAITING_FOR_EVIDENCE
        elif questions:
            has_decision = any(q.category == GapCategory.OWNER_DECISION for q in questions)
            readiness = ReadinessStatus.NEEDS_OWNER_INPUT
            if has_decision and len(questions) == 1:
                waiting = WaitingState.WAITING_FOR_OWNER_DECISION
            elif has_decision:
                waiting = WaitingState.WAITING_FOR_OWNER_GUIDANCE
            else:
                waiting = WaitingState.WAITING_FOR_OWNER_INPUT
        else:
            readiness = ReadinessStatus.READY
            waiting = WaitingState.RESOLVED

        spec = TaskSpecification(
            task_id=task_id,
            task_goal=goal if goal and goal.strip() else "UNKNOWN",
            expected_outcome=expected_outcome if expected_outcome else "UNKNOWN",
            acceptance_criteria=acceptance_criteria,
            known_facts=known_facts,
            evidence_refs=evidence_refs,
            available_resources=available_resources,
            required_inputs=required_inputs,
            missing_information=missing,
            assumptions=[
                f"{f.key}: {f.note}" for f in known_facts
                if f.evidence is EvidenceKind.ASSUMPTION
            ],
            constraints=constraints,
            risks=[
                "Tự đoán khi thiếu thông tin -> kết quả sai",
                "Tự ý thực hiện khi chưa đủ căn cứ -> vượt quyền",
            ],
            owner_decisions_required=owner_decisions_required,
            next_action=(
                "CHỜ ANH CUNG CẤP THÔNG TIN HOẶC CHỈ ĐẠO"
                if readiness is ReadinessStatus.NEEDS_OWNER_INPUT
                else (
                    "ĐỀ XUẤT CÁCH XÁC MINH VÀ XIN CHỈ ĐẠO"
                    if readiness is ReadinessStatus.NEEDS_VERIFICATION
                    else "CHUYỂN PLANNING"
                )
            ),
            task_status="UNDERSTANDING",
            questions=questions,
            readiness=readiness.value,
            waiting_state=waiting.value,
        )

        return GapAnalysis(
            task_id=task_id,
            readiness=readiness,
            waiting_state=waiting,
            missing=missing,
            questions=questions,
            conflicts=conflicts,
            checked_sources=checked_sources,
            reasoning=(
                "; ".join(f"thiếu nhóm {c.value}" for c in missing)
                or "đủ thông tin thiết yếu"
            ),
            approval_gate_needed=approval_gate_needed,
            spec=spec,
        )

    # -- persistence (V3 §8) -----------------------------------------------

    def save_request(
        self,
        analysis: GapAnalysis,
        *,
        request_text: str = "",
        netchat_message_id: str = "",
    ) -> None:
        """Luu trang thai cho ben vong + spec day du (V3 §8).

        READY khong luu vi khong cho; RESOLVED/CANCELLED da cham dut.
        """
        if analysis.readiness is ReadinessStatus.READY:
            return
        now = self._clock().isoformat()
        spec_json = (
            json.dumps(analysis.spec.to_dict(), ensure_ascii=False)
            if analysis.spec else "{}"
        )
        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO info_gap_tasks (
                    task_id, spec_json, readiness, waiting_state, request_text,
                    created_at_utc, updated_at_utc, netchat_message_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(task_id) DO UPDATE SET
                    spec_json = excluded.spec_json,
                    readiness = excluded.readiness,
                    waiting_state = excluded.waiting_state,
                    request_text = excluded.request_text,
                    updated_at_utc = excluded.updated_at_utc,
                    netchat_message_id = excluded.netchat_message_id,
                    reminder_count = 0,
                    last_reminder_utc = ''
                """
                ,
                (
                    analysis.task_id,
                    spec_json,
                    analysis.readiness.value,
                    analysis.waiting_state.value,
                    request_text[:2000],
                    now,
                    now,
                    netchat_message_id,
                ),
            )
            self._record_event(conn, analysis.task_id, "REQUEST_SAVED", {
                "readiness": analysis.readiness.value,
                "questions": len(analysis.questions),
            })

    def get_waiting_task(self, task_id: str) -> dict[str, Any] | None:
        """Doc trang thai cho cua mot nhiem vu (V3 §8)."""
        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM info_gap_tasks WHERE task_id = ?", (task_id,)
            ).fetchone()
        return dict(row) if row else None

    def list_waiting(self, *, include_resolved: bool = False) -> list[dict[str, Any]]:
        """Liet ke cac nhiem vu dang cho (V3 §8.3 - phuc hoi sau restart)."""
        query = "SELECT * FROM info_gap_tasks"
        if not include_resolved:
            query += " WHERE waiting_state NOT IN ('RESOLVED', 'CANCELLED')"
        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query).fetchall()
        return [dict(r) for r in rows]

    def record_owner_reply(
        self,
        task_id: str,
        question_id: str,
        answer: str,
        *,
        source: str = "netchat:owner quanpt1",
    ) -> dict[str, Any]:
        """Tiep nhan tra loi tung phan cua chu nhan (V3 §8.1).

        Tra loi duoc danh dau OWNER_PROVIDED; phan tich lai khoang trong con
        lai. Tra loi KHONG PHAI phe duyet hanh dong (V3 §8.1, §10).
        """
        spec = self._load_spec(task_id)
        if spec is None:
            return {"ok": False, "reason": "task_not_waiting", "task_id": task_id}
        matched = False
        for q in spec.questions:
            if q.question_id == question_id and q.status == "OPEN":
                q.status = "ANSWERED"
                q.answer = answer[:2000]
                spec.known_facts.append(
                    InfoItem(
                        key=q.question_id,
                        value=answer[:2000],
                        evidence=EvidenceKind.OWNER_PROVIDED,
                        source_ref=source,
                    )
                )
                matched = True
                break
        if not matched:
            return {
                "ok": False,
                "reason": "question_not_found_or_closed",
                "task_id": task_id,
            }
        remaining = [
            q for q in spec.questions
            if q.status == "OPEN" and q.required_or_optional == "REQUIRED"
        ]
        if remaining:
            spec.waiting_state = WaitingState.WAITING_FOR_OWNER_INPUT.value
            spec.readiness = ReadinessStatus.NEEDS_OWNER_INPUT.value
            spec.next_action = "CHỜ ANH CUNG CẤP THÔNG TIN CÒN THIẾU"
            result: dict[str, Any] = {
                "ok": True,
                "task_id": task_id,
                "all_answered": False,
                "still_missing": [q.question_id for q in remaining],
            }
        else:
            spec.readiness = ReadinessStatus.READY.value
            spec.waiting_state = WaitingState.RESOLVED.value
            spec.next_action = (
                "ĐÃ ĐỦ THÔNG TIN - CHUYỂN BƯỚC TIẾP THEO ĐƯỢC PHÉP "
                "(việc phê duyệt hành động vẫn thuộc ApprovalOrchestrator)"
            )
            spec.task_status = "READY_FOR_PLANNING"
            result = {
                "ok": True,
                "task_id": task_id,
                "all_answered": True,
                "still_missing": [],
                "note": "Tra loi KHONG PHAI phe duyet hanh dong.",
            }
        spec.missing_information = sorted(
            {q.category for q in spec.questions if q.status != "ANSWERED"},
            key=lambda c: c.value,
        )
        self._persist_spec(task_id, spec)
        with self._lock, sqlite3.connect(self.db_path) as conn:
            self._record_event(conn, task_id, "OWNER_REPLY_RECORDED", {
                "question_id": question_id,
                "all_answered": result["all_answered"],
            })
        return result

    # -- nhac viec & dung cho (V3 §9, §8.2) ---------------------------------

    def should_send_reminder(self, task_id: str) -> bool:
        """Nhac viec co gioi han (V3 §9): khoang cach remind_interval_hours,
        toi da max_reminders - KHONG gui lai vo han; im lang khong dong y."""
        with self._lock, sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT reminder_count, last_reminder_utc FROM info_gap_tasks "
                "WHERE task_id = ?",
                (task_id,),
            ).fetchone()
        if not row:
            return False
        count, last = int(row[0]), row[1]
        if count >= self.max_reminders:
            return False
        if last:
            elapsed = self._clock() - datetime.fromisoformat(last)
            if elapsed < timedelta(hours=self.remind_interval_hours):
                return False
        return True

    def note_reminder_sent(self, task_id: str) -> None:
        now = self._clock().isoformat()
        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE info_gap_tasks SET reminder_count = reminder_count + 1, "
                "last_reminder_utc = ? WHERE task_id = ?",
                (now, task_id),
            )

    def mark_cancelled(self, task_id: str, reason: str = "") -> None:
        """Chu nhan chi dao dung (V3 §8.2) - cham dut cho, khong tu tiep tuc."""
        now = self._clock().isoformat()
        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE info_gap_tasks SET waiting_state = 'CANCELLED', "
                "updated_at_utc = ? WHERE task_id = ?",
                (now, task_id),
            )
            self._record_event(conn, task_id, "CANCELLED", {"reason": reason[:200]})

    # -- rendering (V3 §7) --------------------------------------------------

    def render_info_request(self, analysis: GapAnalysis, *, short_form: bool = False) -> str:
        """Tin nhan [CAN ANH QUANPT1 BO SUNG THONG TIN] (V3 §7) - nguyen van.

        Phan biet ro voi Approval Card; ket thuc bang dong trang thai bat buoc.
        """
        questions = [q for q in analysis.questions if q.status == "OPEN"]
        if not questions:
            return ""
        goal = analysis.spec.task_goal if analysis.spec else "UNKNOWN"
        if short_form and len(questions) <= 2:
            lines = [f"**[CẦN ANH QUANPT1 BỔ SUNG THÔNG TIN]** — {analysis.task_id}"]
            for i, q in enumerate(questions, 1):
                lines.append(f"{i}. {q.question}")
            lines.append(_CLOSING_LINE)
            return "\n".join(lines)

        lines: list[str] = [
            "**[CẦN ANH QUANPT1 BỔ SUNG THÔNG TIN]**",
            f"**Mã nhiệm vụ:** {analysis.task_id}",
            "",
            "**1. Mục đích**",
            f"Em đang xử lý: {goal}. Kết quả cần đạt: "
            f"{analysis.spec.expected_outcome if analysis.spec else 'UNKNOWN'}.",
            "",
            "**2. Hiện trạng / Căn cứ**",
        ]
        if analysis.checked_sources:
            lines.append("- Đã kiểm tra nguồn: " + "; ".join(analysis.checked_sources))
        if analysis.spec and analysis.spec.known_facts:
            for f in analysis.spec.known_facts[:5]:
                lines.append(
                    f"- Đã có [{f.evidence.value}] {f.key}: {str(f.value)[:120]}"
                )
        if analysis.spec and analysis.spec.assumptions:
            lines.append(
                "- Chưa xác minh (giả định, chưa là sự thật): "
                + "; ".join(analysis.spec.assumptions[:3])
            )
        if not lines[-1].startswith("-"):
            lines.append("- Chưa có căn cứ bổ sung.")
        lines += ["", "**3. Thông tin còn thiếu**"]
        for i, q in enumerate(questions[:5], 1):
            req = "Bắt buộc" if q.required_or_optional == "REQUIRED" else "Tùy chọn"
            entry = f"{i}. {q.question} (Mức độ: {req}) - Lý do: {q.why_it_matters}"
            if q.options:
                entry += " Lựa chọn: " + " / ".join(q.options)
            lines.append(entry)
        lines += [
            "",
            "**4. Hướng xử lý dự kiến**",
            analysis.spec.next_action if analysis.spec else "Chờ thông tin bổ sung.",
            "",
            "**5. Xin chỉ đạo**",
            "Anh cần gửi tài liệu/đường link, xác nhận một lựa chọn, "
            "hoặc chỉ đạo cách xử lý. Em sẽ tiếp tục ngay khi nhận được.",
            "",
            _CLOSING_LINE,
        ]
        return "\n".join(lines)

    # -- internals ------------------------------------------------------

    def _load_spec(self, task_id: str) -> TaskSpecification | None:
        with self._lock, sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT spec_json FROM info_gap_tasks WHERE task_id = ?",
                (task_id,),
            ).fetchone()
        if not row:
            return None
        return TaskSpecification.from_dict(json.loads(row[0]))

    def _persist_spec(self, task_id: str, spec: TaskSpecification) -> None:
        now = self._clock().isoformat()
        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE info_gap_tasks SET spec_json = ?, readiness = ?, "
                "waiting_state = ?, updated_at_utc = ? WHERE task_id = ?",
                (
                    json.dumps(spec.to_dict(), ensure_ascii=False),
                    spec.readiness,
                    spec.waiting_state,
                    now,
                    task_id,
                ),
            )

    def _record_event(
        self,
        conn: sqlite3.Connection,
        task_id: str,
        event_type: str,
        detail: dict[str, Any],
    ) -> None:
        conn.execute(
            "INSERT INTO info_gap_events "
            "(event_id, task_id, event_type, detail_json, created_at_utc) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                uuid.uuid4().hex,
                task_id,
                event_type,
                json.dumps(detail, ensure_ascii=False),
                self._clock().isoformat(),
            ),
        )


def _render_input_question(item: InfoItem) -> str:
    return (
        f"Anh Quân, để tiếp tục em cần dữ liệu đầu vào '{item.key}'. "
        f"{('Ghi chú: ' + item.note) if item.note else 'Dữ liệu này quyết định kết quả công việc.'} "
        "Anh cung cấp giúp em."
    )
