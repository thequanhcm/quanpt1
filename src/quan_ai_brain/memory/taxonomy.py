"""V7 SUPER MEMORY V2 — Taxonomy Adapter (G2 / WP1).

Map thuần hàm từ các enum/store hiện có sang 8 lớp nhớ đích M1–M8 của
V7.0 SUPER MEMORY ARCHITECTURE (docs/V7_SUPER_MEMORY_ARCHITECTURE.md §C.2).

Thiết kế bắt buộc (§C.1):
- Overlay mỏng, KHÔNG giữ dữ liệu, KHÔNG store mới, KHÔNG I/O.
- Thuần hàm: cùng input → cùng output, không state toàn cục.
- Giá trị lạ / không map được → trả UNMAPPED (fail-honest), không đoán.
- Không đổi enum hiện có; DECISION/CANDIDATE không thành lớp nhớ mới.

Lớp đích:
  M1 EPISODIC      — sự kiện, trao đổi, kết quả nhiệm vụ
  M2 SEMANTIC      — tri thức/dữ kiện đã xác minh
  M3 PROCEDURAL    — quy trình/SOP đã kiểm thử
  M4 PREFERENCE    — ưu tiên của owner
  M5 EXPERIENCE    — bài học kinh nghiệm (context→action→outcome)
  M6 EMOTIONAL     — tín hiệu cảm xúc/xã hội (DESIGNED, OFF mặc định)
  M7 TASK_STATE    — trạng thái nhiệm vụ (view trên tasks.db)
  M8 REFLECTIVE    — phản tư/metacognitive (journal, lessons tổng hợp)
"""
from __future__ import annotations

from enum import Enum


class MemoryCategory(str, Enum):
    """8 lớp nhớ đích V7 SUPER MEMORY V2 (docs/V7_...md §C.2)."""
    M1_EPISODIC = "M1_EPISODIC"
    M2_SEMANTIC = "M2_SEMANTIC"
    M3_PROCEDURAL = "M3_PROCEDURAL"
    M4_PREFERENCE = "M4_PREFERENCE"
    M5_EXPERIENCE = "M5_EXPERIENCE"
    M6_EMOTIONAL = "M6_EMOTIONAL"
    M7_TASK_STATE = "M7_TASK_STATE"
    M8_REFLECTIVE = "M8_REFLECTIVE"
    UNMAPPED = "UNMAPPED"  # fail-honest: không đoán lớp cho giá trị lạ


# ---------------------------------------------------------------------------
# 1) MemoryType (models.py) → M1–M8
#    DECISION là content-kind phủ trên Episodic/Reflective, không phải lớp
#    thứ 9 (§C.2) → map về M1_EPISODIC (kind=decision).
#    CANDIDATE là trạng thái lifecycle/quarantine → không phải lớp nhớ.
# ---------------------------------------------------------------------------
_MEMORY_TYPE_MAP: dict[str, MemoryCategory] = {
    "EPISODIC": MemoryCategory.M1_EPISODIC,
    "SEMANTIC": MemoryCategory.M2_SEMANTIC,
    "PROCEDURAL": MemoryCategory.M3_PROCEDURAL,
    "DECISION": MemoryCategory.M1_EPISODIC,
    "PREFERENCE": MemoryCategory.M4_PREFERENCE,
    "CANDIDATE": MemoryCategory.UNMAPPED,  # lifecycle, không phải lớp nhớ
}

# Content-kind cho DECISION khi caller cần (đọc từ tags/metadata)
DECISION_KIND = "decision"


# ---------------------------------------------------------------------------
# 2) KNOWLEDGE_TYPES (deep_memory.py V9) → M1–M8
#    FACT → M2 (tri thức); OPINION → M2 (kèm fact_level thấp);
#    RULE/PROCESS → M3 (quy trình); QUESTION → M8 (phản tư/câu hỏi mở);
#    CONCLUSION → M2 (kết luận đã tổng hợp).
# ---------------------------------------------------------------------------
_KNOWLEDGE_TYPE_MAP: dict[str, MemoryCategory] = {
    "FACT": MemoryCategory.M2_SEMANTIC,
    "OPINION": MemoryCategory.M2_SEMANTIC,
    "RULE": MemoryCategory.M3_PROCEDURAL,
    "PROCESS": MemoryCategory.M3_PROCEDURAL,
    "QUESTION": MemoryCategory.M8_REFLECTIVE,
    "CONCLUSION": MemoryCategory.M2_SEMANTIC,
}


# ---------------------------------------------------------------------------
# 3) episodes.kind (brain.db) → M1–M8
#    kind thật probe 05/11: chat_turn (2829), experience_lesson (113), task (1).
# ---------------------------------------------------------------------------
_EPISODE_KIND_MAP: dict[str, MemoryCategory] = {
    "chat_turn": MemoryCategory.M1_EPISODIC,
    "task": MemoryCategory.M7_TASK_STATE,
    "experience_lesson": MemoryCategory.M5_EXPERIENCE,
    # Biến thể mở rộng phòng khi xuất hiện (map theo ngữ nghĩa, vẫn fail-honest
    # với kind lạ):
    "session": MemoryCategory.M1_EPISODIC,
    "reflection": MemoryCategory.M8_REFLECTIVE,
    "emotional_signal": MemoryCategory.M6_EMOTIONAL,
}


# ---------------------------------------------------------------------------
# 4) tasks.db durable_tasks.status → M7 (đều thuộc Task/State layer)
# ---------------------------------------------------------------------------
_TASK_STATUS_SET = {
    "PENDING", "RUNNING", "COMPLETED", "COMPLETED_VERIFIED", "FAILED",
    "CANCELLED", "EXPIRED", "READY", "archived", "completed", "cancelled",
}


def map_memory_type(memory_type: str) -> MemoryCategory:
    """MemoryType/memories.memory_type → MemoryCategory. Lạ → UNMAPPED."""
    if not memory_type:
        return MemoryCategory.UNMAPPED
    return _MEMORY_TYPE_MAP.get(str(memory_type).strip().upper(), MemoryCategory.UNMAPPED)


def map_knowledge_type(kt: str) -> MemoryCategory:
    """KNOWLEDGE_TYPES (Deep Memory V9) → MemoryCategory. Lạ → UNMAPPED."""
    if not kt:
        return MemoryCategory.UNMAPPED
    return _KNOWLEDGE_TYPE_MAP.get(str(kt).strip().upper(), MemoryCategory.UNMAPPED)


def map_episode_kind(kind: str) -> MemoryCategory:
    """episodes.kind → MemoryCategory. Lạ → UNMAPPED."""
    if not kind:
        return MemoryCategory.UNMAPPED
    return _EPISODE_KIND_MAP.get(str(kind).strip().lower(), MemoryCategory.UNMAPPED)


def map_task_status(status: str) -> MemoryCategory:
    """durable_tasks.status → M7_TASK_STATE; lạ → UNMAPPED."""
    if not status:
        return MemoryCategory.UNMAPPED
    return MemoryCategory.M7_TASK_STATE if str(status).strip() in _TASK_STATUS_SET else MemoryCategory.UNMAPPED


def map_memory_record(record: dict) -> tuple[MemoryCategory, str | None]:
    """Map 1 dòng bảng memories.

    Returns:
        (MemoryCategory, kind) — kind chỉ khác None khi là DECISION
        (kind='decision' theo §C.2), ngược lại None.
    """
    mt = str(record.get("memory_type", "") or "")
    cat = map_memory_type(mt)
    kind = DECISION_KIND if mt.strip().upper() == "DECISION" else None
    return cat, kind


def taxonomy_summary() -> dict:
    """Tóm tắt bảng map để test/report đối chiếu (thuần, không I/O)."""
    return {
        "memory_type": dict(_MEMORY_TYPE_MAP),
        "knowledge_type": dict(_KNOWLEDGE_TYPE_MAP),
        "episode_kind": dict(_EPISODE_KIND_MAP),
        "task_status_layer": MemoryCategory.M7_TASK_STATE.value,
    }
