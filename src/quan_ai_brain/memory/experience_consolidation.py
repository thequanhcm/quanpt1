"""Sprint 11 (a): Experience Memory — consolidation bài học từ nhiệm vụ.

Lớp mỏng trên MemoryStore HIỆN CÓ (không tạo store mới):
- extract_candidate_lesson(): task COMPLETED/FAILED → lesson CANDIDATE
  (VerificationStatus.UNVERIFIED, lifecycle QUARANTINED) — KHÔNG phải kinh nghiệm
  đã xác nhận; retrieval (Sprint 9 D) chỉ xem nó là "ứng viên, chưa duyệt".
- promote_lesson(): CHỈ khi owner duyệt (approval_verified=True bắt buộc) →
  VERIFIED + lifecycle active — lúc đó mới thành căn cứ mạnh cho đề xuất.
- Idempotent theo task_id (metadata.task_id) — 1 task = 1 lesson tối đa.

Nguyên tắc: lesson sinh tự động KHÔNG BAO GIỜ tự promote ("Learning is not
deployment"); không LLM; fail-closed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from quan_ai_brain.memory.models import (
    LifecycleStatus,
    MemoryRecord,
    MemoryType,
    VerificationStatus,
)
from quan_ai_brain.memory.sqlite_store import MemoryStore

_LESSON_TAG = "sprint11_lesson"


@dataclass
class LessonResult:
    """Kết quả 1 lần consolidate — trung thực về việc có sinh lesson hay không."""

    created: bool
    reason: str
    task_id: str
    outcome: str
    lesson: dict[str, Any] | None = None
    existing_lesson_id: str | None = None
    keywords: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "created": self.created,
            "reason": self.reason,
            "task_id": self.task_id,
            "outcome": self.outcome,
            "lesson": self.lesson,
            "existing_lesson_id": self.existing_lesson_id,
            "keywords": self.keywords,
        }


def _outcome_kind(outcome: str) -> str | None:
    """COMPLETED → thành công; FAILED → thất bại; còn lại → không hợp lệ."""
    val = str(outcome or "").strip().upper()
    if val in ("COMPLETED", "FAILED"):
        return val
    return None


def _lesson_content(task_id: str, goal: str, outcome: str, result_summary: str) -> str:
    prefix = "Bài học (thành công)" if outcome == "COMPLETED" else "Bài học (thất bại)"
    lines = [
        f"{prefix} — task {task_id}",
        f"Mục tiêu: {goal.strip() or '(không rõ)'}",
        f"Kết quả: {result_summary.strip() or '(không có mô tả kết quả)'}",
    ]
    return "\n".join(lines)


def _extract_keywords(text: str) -> list[str]:
    """Từ khoá đơn giản (≥4 ký tự, không dấu cách) cho mục đích tra cứu lại."""
    import re

    tokens = re.findall(r"[a-zA-Zàáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]{4,}", text or "")
    seen: list[str] = []
    for tok in tokens:
        low = tok.lower()
        if low not in seen:
            seen.append(low)
        if len(seen) >= 6:
            break
    return seen


def _find_existing_lesson(store: MemoryStore, task_id: str) -> MemoryRecord | None:
    try:
        matches = store.search_memories(
            query=f"task {task_id}",
            memory_type=MemoryType.EPISODIC,
            lifecycle_status=None,
            limit=20,
        )
    except Exception:
        return None
    for rec in matches:
        if rec.metadata.get("task_id") == task_id and _LESSON_TAG in rec.tags:
            return rec
    return None


def extract_candidate_lesson(
    store: MemoryStore,
    task_id: str,
    goal: str,
    outcome: str,
    *,
    result_summary: str = "",
    source_ref: str = "",
) -> LessonResult:
    """Sinh lesson CANDIDATE từ kết quả nhiệm vụ — idempotent, fail-closed.

    Lesson được lưu ở 2 chỗ của MemoryStore hiện có:
    - memories: EPISODIC + UNVERIFIED + lifecycle QUARANTINED (tra cứu được)
    - episodes: bản ghi sự kiện (audit trail)
    """
    kind = _outcome_kind(outcome)
    if kind is None:
        return LessonResult(False, f"outcome '{outcome}' không hợp lệ — chỉ COMPLETED/FAILED", task_id, str(outcome))
    if not task_id.strip():
        return LessonResult(False, "task_id trống", task_id, str(outcome))

    # Idempotent — lesson đã tồn tại cho task này thì không tạo nữa
    existing = _find_existing_lesson(store, task_id)
    if existing is not None:
        return LessonResult(
            False,
            "lesson đã tồn tại cho task này (idempotent — không tạo trùng)",
            task_id,
            kind,
            existing_lesson_id=existing.id,
            lesson=existing.to_dict(),
        )

    content = _lesson_content(task_id, goal, kind, result_summary)
    keywords = _extract_keywords(goal + " " + result_summary)
    safe_source = source_ref.strip() or f"task:{task_id}"

    try:
        rec = store.store_memory(
            content=content,
            memory_type=MemoryType.EPISODIC,
            source_ref=safe_source,
            verification_status=VerificationStatus.UNVERIFIED,
            confidence_score=0.5,
            project_scope="experience",
            tags=[_LESSON_TAG, kind.lower(), "unreviewed"],
            lifecycle_status=LifecycleStatus.QUARANTINED,
            metadata={
                "task_id": task_id,
                "outcome": kind,
                "goal": goal.strip(),
                "result_summary": result_summary.strip(),
                "keywords": keywords,
                "lesson_candidate": True,
            },
        )
        store.add_episode(
            summary=f"Experience lesson candidate sinh từ task {task_id} ({kind})",
            kind="experience_lesson",
            source_ref=f"memory:{rec.id}",
            status="candidate",
            metadata={"task_id": task_id, "outcome": kind, "memory_id": rec.id},
        )
    except Exception as exc:
        # Fail-closed — không thành im lặng
        return LessonResult(False, f"lỗi ghi lesson: {exc}", task_id, kind)

    return LessonResult(True, "lesson candidate đã sinh (chờ owner duyệt)", task_id, kind, lesson=rec.to_dict(), keywords=keywords)


def promote_lesson(
    store: MemoryStore,
    memory_id: str,
    *,
    lesson_note: str = "",
    approved_by: str = "quanpt1",
    approval_verified: bool = False,
) -> dict[str, Any]:
    """Owner duyệt lesson → VERIFIED + active — thành căn cứ mạnh.

    Bắt buộc approval_verified=True (đường duyệt chủ sở hữu). Không tự duyệt.
    Chỉ lesson candidate (UNVERIFIED + QUARANTINED) được promote.
    """
    if not approval_verified:
        raise PermissionError("Không có phê duyệt đã xác minh — lesson giữ nguyên quarantine")

    rec = store.get_memory(memory_id)
    if rec is None:
        raise KeyError(f"Lesson '{memory_id}' không tồn tại")
    if _LESSON_TAG not in rec.tags:
        raise ValueError(f"Memory '{memory_id}' không phải lesson Sprint 11")
    if rec.lifecycle_status == LifecycleStatus.SUPERSEDED.value:
        raise ValueError("Lesson đã superseded — không promote trên bản cũ")

    if rec.verification_status == VerificationStatus.VERIFIED.value and rec.lifecycle_status == LifecycleStatus.ACTIVE.value:
        return {"promoted": False, "reason": "đã VERIFIED+active trước đó (idempotent)", "memory": rec.to_dict()}

    new_content = rec.content if not lesson_note.strip() else rec.content + f"\nGhi chú khi duyệt: {lesson_note.strip()}"
    new_rec = store.supersede_memory(
        rec.id,
        new_content,
        verification_status=VerificationStatus.VERIFIED,
        confidence_score=1.0,
        project_scope=rec.project_scope,
        tags=[t for t in rec.tags if t != "unreviewed"] + ["reviewed"],
        metadata={
            **rec.metadata,
            "promoted_by": approved_by,
            "promoted_note": lesson_note.strip(),
        },
    )
    return {"promoted": True, "reason": "owner duyệt — lesson VERIFIED + active", "memory": new_rec.to_dict()}


def list_lessons(store: MemoryStore, *, limit: int = 20) -> dict[str, Any]:
    """Danh sách lessons: candidates (chờ duyệt) + confirmed (đã duyệt) tách riêng."""
    out: dict[str, list[dict[str, Any]]] = {"candidates": [], "confirmed": []}
    for rec in store.search_memories(memory_type=MemoryType.EPISODIC, lifecycle_status=None, limit=200):
        if _LESSON_TAG not in rec.tags:
            continue
        if rec.lifecycle_status == LifecycleStatus.QUARANTINED.value:
            out["candidates"].append(rec.to_dict())
        elif rec.verification_status == VerificationStatus.VERIFIED.value:
            out["confirmed"].append(rec.to_dict())
        if len(out["candidates"]) >= limit and len(out["confirmed"]) >= limit:
            break
    return out
