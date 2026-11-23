# -*- coding: utf-8 -*-
"""MemoryAdapter — CHERRY VMAIL INTELLIGENCE V1.0 — Sprint 3 (card TASK-VMAIL-S3).

Owner duyệt (24/11 chat): "duyệt" → Sprint 3 MEMORY-ADAPTER. Master prompt §6:
KHÔNG tạo database trí nhớ độc lập — PHẢI dùng Memory Service hiện có của
QUAN AI BRAIN qua adapter.

Lớp mỏng TRÊN memory hiện có (§2.1 không core thứ 2):
- Đọc  (Retrieval): MemoryFacade.search (unified: semantic OBSERVED/VERIFIED/FACT
  + episodes) — 3.107 records hiện có (3020 OBSERVED + 13 USER_PROVIDED + 72 VERIFIED).
- Ghi  (Candidate): MemoryFacade.add(memory_type="candidate") → R4 quarantine
  (KHÔNG tự vào semantic — đúng §6.4); promote chỉ qua MemoryFacade.promote_to_fact
  (approved_by owner) — adapter KHÔNG BAO GIỜ tự promote.
- Lesson: ExperienceStore.add_experience (OutcomeType.PENDING) cho cam kết/deadline
  phát hiện từ email — phục vụ LessonLearner hiện có.

Retrieval Policy §6.3 (trong retrieve_context):
- Ưu tiên VERIFIED/FACT > OBSERVED > INFERENCE (sort weight).
- Phân biệt sự kiện/nhận định/đề xuất qua fact_level của hit (không bịa).
- Mỗi hit trả kèm source_ref + score + fact_level để owner kiểm tra được.
- Mâu thuẫn: 2 hit cùng chủ đề khác nội dung → trả CẢ HAI kèm nguồn (không chọn hộ).

Update Policy §6.4 (trong create_memory_candidate):
- CHỈ tạo candidate khi nội dung thuộc nhóm có giá trị dài hạn: quyết định, cam
  kết, deadline, thay đổi trạng thái, nhiệm vụ mới, thay đổi trách nhiệm.
- Text email thô KHÔNG được lưu (lưu câu đã trích xuất có nguồn mail #id).
- Candidate chứa: content + source_email_id + thread_key + timestamp + confidence
  + verification_status=CANDIDATE + sensitivity.

R2 bất biến: chỉ ĐỌC mail; ghi memory chỉ theo §6.4; KHÔNG tự promote.
Fail-honest: lỗi memory → trả status="error" + evidence, không fake hit.
"""
from __future__ import annotations

import datetime as _dt
import re
from dataclasses import dataclass, field
from typing import Any

# ---- Nhóm nội dung ĐƯỢC PHÉP tạo candidate (§6.4) ----
_CANDIDATE_WORTHY = re.compile(
    r"(quyết định|quyet dinh|chốt|chot|thống nhất|thong nhat|cam kết|cam ket|"
    r"đồng ý|dong y|phê duyệt|phe duyet|đã duyệt|da duyet|deadline|hạn|han |"
    r"trước \d|truoc \d|trước ngày|truoc ngay|giao nhiệm vụ|giao nhiem vu|"
    r"được giao|duoc giao|chịu trách nhiệm|chiu trach nhiem|thay đổi trạng thái|"
    r"thay doi trang thai|bắt đầu \d|bat dau \d|hoàn thành \d|hoan thanh \d)",
    re.I,
)

# Nhóm KHÔNG được lưu (§6.4 — không giá trị dài hạn / rủi ro)
_CANDIDATE_BANNED = re.compile(
    r"(mật khẩu|mat khau|password|token|otp|pin|secret|chúc mừng|chuc mung|"
    r"khuyến mãi|khuyen mai|newsletter|spam)", re.I,
)


@dataclass
class RetrievalHit:
    """1 kết quả truy xuất — giữ nguồn để owner kiểm tra (§6.3)."""

    content: str
    fact_level: str           # FACT | OBSERVED | INFERENCE | QUARANTINED
    verification: str         # VERIFIED | OBSERVED | INFERRED | CANDIDATE | ...
    source_layer: str         # semantic | episode | ...
    score: float
    source_ref: str = ""
    created_at: str = ""

    @classmethod
    def from_unified(cls, h: Any) -> "RetrievalHit":
        return cls(
            content=str(getattr(h, "content", "") or ""),
            fact_level=str(getattr(h, "fact_level", "") or ""),
            verification=str(getattr(h, "verification_status", "") or ""),
            source_layer=str(getattr(h, "source_layer", "") or ""),
            score=float(getattr(h, "score", 0.0) or 0.0),
            source_ref=str((getattr(h, "metadata", None) or {}).get("source_ref", "") if isinstance(getattr(h, "metadata", None), dict) else ""),
            created_at=str(getattr(h, "created_at", "") or ""),
        )

    def tier(self) -> int:
        """§6.3: ưu tiên nguồn xác thực. 0 = cao nhất."""
        return {"VERIFIED": 0, "FACT": 0, "OBSERVED": 1, "INFERRED": 2,
                "INFERENCE": 2, "CANDIDATE": 3, "UNVERIFIED": 3}.get(
            self.verification.upper(), 3)


@dataclass
class RetrievalResult:
    """Kết quả retrieve_context — mỗi hit giữ nguyên nguồn (§6.3)."""

    query: str
    hits: list[RetrievalHit] = field(default_factory=list)
    contradictions: list[str] = field(default_factory=list)
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "count": len(self.hits),
            "hits": [
                {"content": h.content[:300], "fact_level": h.fact_level,
                 "verification": h.verification, "layer": h.source_layer,
                 "score": h.score, "source_ref": h.source_ref}
                for h in self.hits
            ],
            "contradictions": self.contradictions,
            "error": self.error,
        }


@dataclass
class CandidateResult:
    """Kết quả create_memory_candidate (§6.4)."""

    created: bool
    layer: str = ""            # quarantine | semantic | episode
    id: str = ""
    fact_level: str = ""
    reason: str = ""           # vì sao tạo / vì sao TỪ CHỐI tạo
    content: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"created": self.created, "layer": self.layer, "id": self.id,
                "fact_level": self.fact_level, "reason": self.reason,
                "content": self.content[:300]}


class CherryMemoryAdapter:
    """Adapter duy nhất giữa CHERRY VMAIL/Office và Memory Service hiện có.

    KHÔNG tạo db mới — mọi đường đi qua MemoryFacade (unified: semantic + episode
    + quarantine) và ExperienceStore (lesson). Fail-honest: lỗi → result.error.
    """

    def __init__(self, facade: Any | None = None,
                 experience_store: Any | None = None,
                 quarantine_store: Any | None = None,
                 *, auto_create_stores: bool = True) -> None:
        # Import lười + wrap lỗi để test mock dễ, import thật khi chạy live.
        if facade is None:
            from quan_ai_brain.memory.unified_memory import MemoryFacade
            facade = MemoryFacade()
        self.facade = facade
        if experience_store is None and auto_create_stores:
            try:
                from quan_ai_brain.memory.experience_store import ExperienceStore
                experience_store = ExperienceStore()
            except Exception:
                experience_store = None  # lesson path degraded — retrieval vẫn chạy
        self.experience_store = experience_store
        # Quarantine R4: MemoryFacade() mặc định quarantine=None → candidate sẽ
        # rơi vào semantic (LỖ §6.4). Adapter tự wire QuarantineStore hiện có
        # (data/quarantine.db, approval workflow list_pending/approve/reject).
        if quarantine_store is None and auto_create_stores:
            try:
                from quan_ai_brain.memory.quarantine_store import QuarantineStore
                quarantine_store = QuarantineStore()
            except Exception:
                quarantine_store = None  # degraded — candidate sẽ bị TỪ CHỐI ghi
        self.quarantine_store = quarantine_store

    # ---------------- §6.1 RETRIEVAL ----------------
    def retrieve_context(self, query: str, *, top_k: int = 6) -> RetrievalResult:
        """Ngữ cảnh tổng hợp cho 1 câu hỏi (email/project/task/decision...).

        §6.3: sort VERIFIED trước; phát hiện mâu thuẫn (2 hit VERIFIED/OBSERVED
        cùng chủ đề khác nội dung) → trả CẢ HAI + nguồn, không chọn hộ."""
        out = RetrievalResult(query=query)
        if not query or len(query.strip()) < 2:
            out.error = "Query quá ngắn (< 2 ký tự)."
            return out
        try:
            raw = self.facade.search(query, top_k=max(top_k, 10))
        except Exception as exc:
            out.error = f"{type(exc).__name__}: {exc}"
            return out
        hits = sorted((RetrievalHit.from_unified(h) for h in raw),
                      key=lambda h: (h.tier(), -h.score))
        out.hits = hits[:top_k]
        out.contradictions = self._detect_contradictions(out.hits)
        return out

    def retrieve_email_history(self, subject_key: str, *, top_k: int = 5) -> RetrievalResult:
        """Lịch sử trao đổi đã ghi nhớ về 1 luồng/chủ đề email."""
        return self.retrieve_context(f"email {subject_key}", top_k=top_k)

    def retrieve_project_history(self, project: str, *, top_k: int = 6) -> RetrievalResult:
        return self.retrieve_context(f"dự án {project}", top_k=top_k)

    def retrieve_decisions(self, topic: str, *, top_k: int = 5) -> RetrievalResult:
        res = self.retrieve_context(f"quyết định {topic}", top_k=top_k)
        # Lọc giữ hit có tính quyết định (từ khóa trong nội dung)
        keep = [h for h in res.hits
                if re.search(r"(quyết định|chốt|thống nhất|duyệt|đồng ý|cam kết)",
                             h.content, re.I)]
        if keep:
            res.hits = keep
        return res

    def retrieve_related_tasks(self, topic: str, *, top_k: int = 5) -> RetrievalResult:
        res = self.retrieve_context(f"nhiệm vụ {topic}", top_k=top_k)
        keep = [h for h in res.hits
                if re.search(r"(nhiệm vụ|giao|hoàn thành|deadline|hạn|trách nhiệm)",
                             h.content, re.I)]
        if keep:
            res.hits = keep
        return res

    # ---------------- §6.4 UPDATE (candidate) ----------------
    def create_memory_candidate(self, content: str, *, source_email_id: str = "",
                                thread_key: str = "", confidence: float = 0.6,
                                category_hint: str = "") -> CandidateResult:
        """Tạo Memory Candidate từ email — CHỈ khi nội dung có giá trị dài hạn.

        Đường đi: facade.add(memory_type='candidate') → R4 quarantine (hiện có).
        KHÔNG BAO GIỜ tự promote — owner duyệt qua promote_to_fact riêng."""
        text = (content or "").strip()
        if not text:
            return CandidateResult(created=False, reason="Nội dung rỗng.")
        if len(text) < 12:
            return CandidateResult(created=False, reason="Nội dung quá ngắn (<12 ký tự) — không đủ giá trị lưu.")
        if _CANDIDATE_BANNED.search(text):
            return CandidateResult(created=False, reason="Nội dung chứa dữ liệu nhạy cảm/không giá trị (mật khẩu, spam...) — TỪ CHỐI theo §6.4.")
        if not _CANDIDATE_WORTHY.search(text):
            return CandidateResult(created=False, reason="Không thuộc nhóm có giá trị dài hạn (quyết định/cam kết/deadline/nhiệm vụ/thay đổi) — không lưu theo §6.4.")
        # Metadata nguồn đầy đủ (truy vết được về mail gốc)
        now_iso = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
        meta = {
            "source": "vmail_email",
            "source_email_id": source_email_id,
            "thread_key": thread_key,
            "extracted_at": now_iso,
            "confidence": confidence,
            "category": category_hint,
            "adapter": "CherryMemoryAdapter/S3",
        }
        source_ref = f"email:{source_email_id}" if source_email_id else "email:unknown"
        # §6.4 bất biến: candidate PHẢI vào quarantine — KHÔNG bao giờ tự vào
        # semantic. Wire QuarantineStore trực tiếp (không phụ thuộc facade có
        # quarantine hay không — MemoryFacade() mặc định quarantine=None).
        if self.quarantine_store is None:
            return CandidateResult(
                created=False, content=text,
                reason="Quarantine store không khả dụng — TỪ CHỐI ghi để bảo đảm không tự xác minh (fail-honest §6.4).")
        try:
            qid = self.quarantine_store.add_knowledge(
                text,
                source_ref=source_ref,
                metadata=meta,
            )
        except Exception as exc:
            return CandidateResult(created=False, content=text,
                                   reason=f"Lỗi quarantine (fail-honest): {type(exc).__name__}: {exc}")
        return CandidateResult(
            created=True,
            layer="quarantine",
            id=str(qid),
            fact_level="QUARANTINED",
            reason="Đã vào quarantine R4 (PENDING_REVIEW) — chờ owner duyệt approve; KHÔNG tự promote.",
            content=text,
        )

    def extract_candidates_from_thread(self, analysis: Any, *, max_items: int = 3) -> list[CandidateResult]:
        """Quét ThreadAnalysis (Sprint 2) → candidate cho từng mục đáng lưu.

        Ưu tiên: decisions > commitments > changes (§6.4 danh sách). Câu đã trích
        sẵn kèm nguồn mail #id — nguồn được giữ nguyên vào metadata."""
        results: list[CandidateResult] = []
        buckets = [
            ("decision", getattr(analysis, "decisions", []) or []),
            ("commitment", getattr(analysis, "commitments", []) or []),
            ("change", getattr(analysis, "changes", []) or []),
        ]
        thread_key = getattr(analysis, "key", "")
        for cat, items in buckets:
            for item in items:
                if len(results) >= max_items:
                    return results
                # Trích mail #id từ chuỗi nguồn của ThreadAnalyzer "(mail #123 ...)"
                m = re.search(r"mail #(\d+)", str(item))
                email_id = m.group(1) if m else ""
                # Nội dung candidate: bỏ phần nguồn (đã vào metadata)
                content = re.sub(r"\s*\(mail #\d+[^\)]*\)\s*$", "", str(item)).strip("“” ")
                results.append(self.create_memory_candidate(
                    content, source_email_id=email_id,
                    thread_key=thread_key, confidence=0.6, category_hint=cat))
        return results

    # ---------------- Lesson path (LessonLearner hiện có) ----------------
    def record_followup_experience(self, title: str, description: str, *,
                                   source_email_id: str = "",
                                   thread_key: str = "") -> dict[str, Any]:
        """Ghi experience PENDING (OutcomeType.PENDING) cho việc cần theo dõi —
        phục vụ LessonLearner.extract_lessons khi có kết quả thật."""
        if self.experience_store is None:
            return {"ok": False, "reason": "ExperienceStore không khả dụng (degraded)."}
        try:
            from quan_ai_brain.memory.experience_store import ExperienceType, OutcomeType
            exp = self.experience_store.add_experience(
                experience_type=ExperienceType.TASK,
                title=title[:120],
                description=description[:600],
                context={"source": "vmail_email", "source_email_id": source_email_id,
                         "thread_key": thread_key},
                action_taken="CHERRY ghi nhận từ email — chờ kết quả thật",
                outcome=OutcomeType.UNKNOWN,
                tags=["vmail", "followup"],
                metadata={"adapter": "CherryMemoryAdapter/S3"},
            )
            return {"ok": True, "id": getattr(exp, "id", "")}
        except Exception as exc:
            return {"ok": False, "reason": f"{type(exc).__name__}: {exc}"}

    # ---------------- §6.3 mâu thuẫn ----------------
    @staticmethod
    def _detect_contradictions(hits: list[RetrievalHit]) -> list[str]:
        """2 hit 'tin được' (VERIFIED/FACT/OBSERVED) cùng chủ đề, khác nội dung →
        báo CẢ HAI kèm nguồn (§6.3: đối chiếu, không tự thay quyết định cũ)."""
        def _tokens(text: str) -> set[str]:
            # Tiếng Việt từ ngắn có dấu → bỏ dấu trước khi tách từ (≥4 ký tự)
            import unicodedata
            plain = unicodedata.normalize("NFD", text.lower())
            plain = "".join(c for c in plain if unicodedata.category(c) != "Mn")
            return set(re.findall(r"\w{4,}", plain))

        out: list[str] = []
        trusted = [h for h in hits if h.tier() <= 1 and len(h.content) >= 20]
        for i in range(len(trusted)):
            for j in range(i + 1, len(trusted)):
                a, b = trusted[i], trusted[j]
                # cùng chủ đề: chia sẻ ≥1 từ dài; khác nội dung: không chứa nhau
                wa, wb = _tokens(a.content), _tokens(b.content)
                if wa & wb and a.content[:80] != b.content[:80] \
                        and a.content[:60] not in b.content and b.content[:60] not in a.content:
                    out.append(
                        f"MAU THUẪN TRÍ NHỚ — [A] ({a.verification}, {a.source_ref or a.source_layer}): "
                        f"“{a.content[:140]}…” ⇄ [B] ({b.verification}, {b.source_ref or b.source_layer}): "
                        f"“{b.content[:140]}…” — trình bày CẢ HAI, cần owner xác nhận bản đúng."
                    )
                    if len(out) >= 2:
                        return out
        return out


# Singleton — dùng CherryMemoryAdapter() hoặc get_adapter()
_default_adapter: CherryMemoryAdapter | None = None


def get_adapter() -> CherryMemoryAdapter:
    global _default_adapter
    if _default_adapter is None:
        _default_adapter = CherryMemoryAdapter()
    return _default_adapter
