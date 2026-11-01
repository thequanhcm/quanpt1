"""Sprint 9 (D): Experience retrieval — tìm kinh nghiệm liên quan từ memory HIỆN CÓ.

KHÔNG tạo memory store mới. Dùng MemorySQLiteStore.search_memories với:
- memory_type = PROCEDURAL (kinh nghiệm quy trình) / EPISODIC (bài học từ nhiệm vụ)
- verification_status chỉ lấy VERIFIED/OBSERVED cho "kinh nghiệm đã xác nhận";
  CANDIDATE/UNVERIFIED trả về riêng, đánh dấu "ứng viên, chưa duyệt" (§VII.2).

Nguyên tắc (master prompt §VII.3): kinh nghiệm là THAM CHIẾU cho suy luận —
không bao giờ tự thành quyền thực thi. Hàm này chỉ trả dữ liệu có nguồn gốc.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from quan_ai_brain.memory.models import MemoryType, VerificationStatus
from quan_ai_brain.memory.sqlite_store import MemoryStore

# Token Việt/tiếng Anh tối thiểu — truy vấn LIKE từng từ khoá dài ≥3 ký tự
_TOKEN_RE = re.compile(r"[\wàáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]{3,}", re.IGNORECASE)

# Stopword Việt + Anh phổ biến — loại khỏi truy vấn kinh nghiệm
_STOPWORDS = {
    "the", "and", "for", "with", "this", "that", "have", "from", "not",
    "của", "và", "cho", "là", "các", "có", "được", "một", "trong", "khi",
    "này", "tôi", "anh", "em", "việc", "gì", "như", "để", "theo", "về",
}


@dataclass
class ExperienceMatch:
    """1 kinh nghiệm tìm được — luôn kèm trạng thái xác minh + nguồn gốc."""

    memory_id: str
    content: str
    memory_type: str
    verification_status: str
    lifecycle_status: str
    project_scope: str = ""
    source_ref: str = ""
    is_confirmed: bool = False      # VERIFIED/OBSERVED/USER_PROVIDED mới là confirmed
    matched_terms: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "memory_id": self.memory_id,
            "content": self.content,
            "memory_type": self.memory_type,
            "verification_status": self.verification_status,
            "lifecycle_status": self.lifecycle_status,
            "project_scope": self.project_scope,
            "source_ref": self.source_ref,
            "is_confirmed": self.is_confirmed,
            "matched_terms": self.matched_terms,
        }


_CONFIRMED_STATUSES = {
    VerificationStatus.VERIFIED.value,
    VerificationStatus.OBSERVED.value,
    VerificationStatus.USER_PROVIDED.value,
}


def _keywords(text: str) -> list[str]:
    """Từ khoá ≥3 ký tự, bỏ stopword, dedupe giữ thứ tự."""
    seen: list[str] = []
    for tok in _TOKEN_RE.findall(text or ""):
        low = tok.lower()
        if low in _STOPWORDS or low in seen:
            continue
        seen.append(low)
    return seen[:8]  # giới hạn — không bão hoà LIKE


def find_similar_experiences(
    store: MemoryStore,
    task_context: str,
    *,
    limit: int = 5,
) -> dict[str, Any]:
    """Tìm kinh nghiệm liên quan theo từ khoá của bối cảnh nhiệm vụ.

    Trả về {"confirmed": [...], "candidates": [...], "keywords": [...]}:
    - confirmed: memory VERIFIED/OBSERVED/USER_PROVIDED, lifecycle active —
      dùng làm tham chiếu mạnh (vẫn KHÔNG tự thực thi).
    - candidates: memory CANDIDATE/UNVERIFIED — chỉ là "ứng viên, chưa duyệt",
      không được trình bày như kinh nghiệm đã chấp nhận (§VII.2).
    """
    keywords = _keywords(task_context)
    if not keywords:
        return {"confirmed": [], "candidates": [], "keywords": []}

    confirmed: list[ExperienceMatch] = []
    candidates: list[ExperienceMatch] = []

    for mem_type in (MemoryType.PROCEDURAL, MemoryType.EPISODIC):
        for kw in keywords:
            if len(confirmed) >= limit and len(candidates) >= limit:
                break
            try:
                records = store.search_memories(
                    query=kw, memory_type=mem_type, limit=limit * 2
                )
            except Exception:
                continue  # DB lỗi → bỏ từ khoá này, không chết
            for rec in records:
                match = _to_match(rec, keywords)
                if match is None:
                    continue
                if match.is_confirmed and len(confirmed) < limit:
                    if not any(m.memory_id == match.memory_id for m in confirmed):
                        confirmed.append(match)
                elif not match.is_confirmed and len(candidates) < limit:
                    if not any(m.memory_id == match.memory_id for m in candidates):
                        candidates.append(match)

    return {
        "confirmed": [m.to_dict() for m in confirmed],
        "candidates": [m.to_dict() for m in candidates],
        "keywords": keywords,
    }


def _to_match(rec: Any, keywords: list[str]) -> ExperienceMatch | None:
    """Chuyển MemoryRecord thành ExperienceMatch; None nếu không khớp từ khoá."""
    content = getattr(rec, "content", "") or ""
    low = content.lower()
    matched = [kw for kw in keywords if kw in low]
    if not matched:
        return None
    ver = getattr(rec, "verification_status", "")
    ver_val = ver.value if hasattr(ver, "value") else str(ver)
    life = getattr(rec, "lifecycle_status", "")
    life_val = life.value if hasattr(life, "value") else str(life)
    mtype = getattr(rec, "memory_type", "")
    return ExperienceMatch(
        memory_id=str(getattr(rec, "id", "") or ""),
        content=content,
        memory_type=mtype.value if hasattr(mtype, "value") else str(mtype),
        verification_status=ver_val,
        lifecycle_status=life_val,
        project_scope=str(getattr(rec, "project_scope", "") or ""),
        source_ref=str(getattr(rec, "source_ref", "") or ""),
        is_confirmed=ver_val in _CONFIRMED_STATUSES,
        matched_terms=matched,
    )
