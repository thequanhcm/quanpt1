"""Sprint 14 (b): Semantic search kinh nghiệm — BGE-M3 dense (Module 3) + keyword fallback.

Bổ sung cho experience_retrieval (Sprint 9, keyword LIKE):
- find_similar_experiences_semantic(): embed truy vấn + toàn bộ EPISODIC/PROCEDURAL
  active bằng BGE-M3 (cognition/embedding.py — Module 3 nghiệm thu 10/10), xếp theo
  cosine similarity. Kinh nghiệm vẫn chỉ là THAM CHIẾU cho suy luận (§VII.3) —
  KHÔNG tự thành quyền thực thi; candidates (chưa duyệt) vẫn tách khỏi confirmed.
- Fail-open: Ollama offline / DB lỗi / embedding rỗng → trả rỗng + semantic_available
  = False (trung thực), KHÔNG chết luồng gọi; caller có thể fallback keyword.
- Không ghi DB, không mạng ngoài (chỉ Ollama local), không tạo store mới.
"""
from __future__ import annotations

from typing import Any

from quan_ai_brain.cognition.embedding import BGEEmbeddingService, cosine_similarity
from quan_ai_brain.memory.models import MemoryType, VerificationStatus
from quan_ai_brain.memory.sqlite_store import MemoryStore

_CONFIRMED_STATUSES = {
    VerificationStatus.VERIFIED.value,
    VerificationStatus.OBSERVED.value,
    VerificationStatus.USER_PROVIDED.value,
}

# Ngưỡng lọc nhiễu: BGE-M3 cosine thường >= 0.5 cho liên quan thực sự
_MIN_SIMILARITY = 0.30

# Cap số ứng viên được embed mỗi request (prefilter keyword trước) — tránh
# embed cả trăm memory mỗi lần tìm (Ollama local, mỗi call có thể ~0.5-2s).
_MAX_EMBED_CANDIDATES = 40

_SERVICE: BGEEmbeddingService | None = None


def _get_service() -> BGEEmbeddingService:
    """Singleton — cache embedding ấm dùng chung giữa các request."""
    global _SERVICE
    if _SERVICE is None:
        _SERVICE = BGEEmbeddingService()
    return _SERVICE


def find_similar_experiences_semantic(
    store: MemoryStore,
    task_context: str,
    *,
    embedding: BGEEmbeddingService | None = None,
    limit: int = 5,
    min_similarity: float = _MIN_SIMILARITY,
) -> dict[str, Any]:
    """Tìm kinh nghiệm liên quan bằng dense embedding, xếp theo cosine similarity.

    Trả về dict cùng shape keyword search (Sprint 9) cộng "similarity" per match
    và cờ "semantic_available" để UI/API hiển thị trung thực khi Ollama offline.
    """
    result: dict[str, Any] = {
        "confirmed": [],
        "candidates": [],
        "keywords": [],
        "semantic_available": False,
        "model": "",
    }
    text = (task_context or "").strip()
    if not text:
        return result

    service = embedding or _get_service()
    result["model"] = service.model_name

    qvec = service.embed_text(text)
    if not qvec:  # Ollama offline / lỗi — fail-open trung thực
        return result

    try:
        records = store.search_memories(limit=200)
    except Exception:
        return result  # DB lỗi — fail-open, không chết luồng

    # Prefilter keyword (dùng tokenizer Sprint 9) — chỉ embed tối đa
    # _MAX_EMBED_CANDIDATES ứng viên khớp ít nhất 1 từ khoá. Không đổi ngữ nghĩa
    # xếp hạng — chỉ giới hạn số vector hoá.
    from quan_ai_brain.memory.experience_retrieval import _keywords

    kws = _keywords(text)
    scored: list[tuple[float, Any]] = []
    embedded = 0
    for rec in records:
        if embedded >= _MAX_EMBED_CANDIDATES:
            break
        content = (getattr(rec, "content", "") or "").strip()
        if not content:
            continue
        low = content.lower()
        if kws and not any(k in low for k in kws):
            continue
        cvec = service.embed_text(content)
        if not cvec:
            continue
        embedded += 1
        sim = cosine_similarity(qvec, cvec)
        if sim >= min_similarity:
            scored.append((sim, rec))

    # Fallback: prefilter keyword cho 0 ứng viên (từ vựng khác hoàn toàn —
    # đúng trường hợp semantic cần phát huy) → embed N memory gần nhất.
    if embedded == 0:
        for rec in records[:_MAX_EMBED_CANDIDATES]:
            content = (getattr(rec, "content", "") or "").strip()
            if not content:
                continue
            cvec = service.embed_text(content)
            if not cvec:
                continue
            sim = cosine_similarity(qvec, cvec)
            if sim >= min_similarity:
                scored.append((sim, rec))

    scored.sort(key=lambda t: t[0], reverse=True)

    confirmed: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    for sim, rec in scored:
        if len(confirmed) >= limit and len(candidates) >= limit:
            break
        mtype = getattr(rec, "memory_type", "")
        mtype_val = mtype.value if hasattr(mtype, "value") else str(mtype)
        if mtype_val not in (MemoryType.EPISODIC.value, MemoryType.PROCEDURAL.value):
            continue
        ver = getattr(rec, "verification_status", "")
        ver_val = ver.value if hasattr(ver, "value") else str(ver)
        life = getattr(rec, "lifecycle_status", "")
        life_val = life.value if hasattr(life, "value") else str(life)
        match = {
            "memory_id": str(getattr(rec, "id", "") or ""),
            "content": content,
            "memory_type": mtype_val,
            "verification_status": ver_val,
            "lifecycle_status": life_val,
            "project_scope": str(getattr(rec, "project_scope", "") or ""),
            "source_ref": str(getattr(rec, "source_ref", "") or ""),
            "is_confirmed": ver_val in _CONFIRMED_STATUSES,
            "matched_terms": [],
            "similarity": round(float(sim), 4),
        }
        if match["is_confirmed"] and len(confirmed) < limit:
            confirmed.append(match)
        elif not match["is_confirmed"] and len(candidates) < limit:
            candidates.append(match)

    result["confirmed"] = confirmed
    result["candidates"] = candidates
    result["semantic_available"] = True
    return result
