"""V9 Slice 4 — Owner Feedback Learning: tiếp nhận + áp dụng phản hồi của chủ nhân.

MASTER PROMPT V9 PHẦN IX:
1. Lưu câu trả lời gốc (qua redact — XII.10).        7. Kiểm tra mâu thuẫn nguồn VERIFIED.
2. Liên kết câu hỏi + đợt sàng lọc.                  8. Còn mâu thuẫn → hỏi lại / giữ chưa giải quyết.
3. Xác định nội dung được làm rõ.                    9. Cập nhật quan hệ + phiên bản.
4. Xác định phạm vi áp dụng.                        10. Tạo test case khi quy tắc thay đổi (log).
5. Phân biệt dữ kiện mới / diễn giải / quyết định.  11-12. Ghi kết luận bị ảnh hưởng (log).
6. Cập nhật candidate tri thức.

§VIII.4 (Test L): câu trả lời làm rõ tri thức KHÔNG tự động thành phê duyệt
production — không đụng approval cards, không đổi R0–R5, không nâng quyền.
"""
from __future__ import annotations

import json
from typing import Any

from quan_ai_brain.memory.deep_memory import DeepMemoryStore, _new_id, _now


FEEDBACK_KIND_FACT = "FACT"          # dữ kiện mới
FEEDBACK_KIND_CLARIFY = "CLARIFY"    # diễn giải/làm rõ ngữ nghĩa
FEEDBACK_KIND_DECISION = "DECISION"  # quyết định chọn phương án
FEEDBACK_KIND_SCOPE = "SCOPE"        # xác định phạm vi áp dụng

ANSWER_TYPE_KEYWORDS = {
    FEEDBACK_KIND_FACT: ("là", "có", "đang", "chạy", "địa chỉ", "số"),
    FEEDBACK_KIND_SCOPE: ("chỉ áp dụng", "phạm vi", "riêng", "tổng quát", "mọi trường hợp"),
    FEEDBACK_KIND_DECISION: ("chọn", "phương án", "nguyên tắc", "quy tắc", "xác nhận"),
    FEEDBACK_KIND_CLARIFY: ("ý em là", "ý tôi là", "có nghĩa", "định nghĩa", "làm rõ"),
}


class OwnerFeedbackProcessor:
    def __init__(self, store: DeepMemoryStore) -> None:
        self._store = store

    def answer_owner_question(
        self, question_id: str, answer_text: str, answered_by: str = "quanpt1"
    ) -> dict[str, Any]:
        """Xử lý phản hồi chủ nhân theo quy trình 12 bước PHẦN IX — traceable."""
        if not answer_text.strip():
            raise ValueError("answer_text must not be empty")
        q = self._store.get_owner_question(question_id)
        if q is None:
            raise ValueError(f"question not found: {question_id}")
        if q["status"] != "OPEN":
            raise ValueError(f"question {question_id} is {q['status']}, not OPEN")

        # (1) lưu câu trả lời (redact trong store) + (2) liên kết đã có sẵn qua question_id
        answered_at = _now()

        # (3)+(4)+(5) phân loại nội dung + phạm vi
        feedback_kind = self._classify_answer(answer_text)
        scope = self._extract_scope(answer_text, q)

        # (6) cập nhật KU liên quan (qua evidence refs chứa knowledge_id)
        affected_ids = self._affected_unit_ids(q)
        version_updates = []
        superseded_pairs = []
        for ku_id in affected_ids:
            unit = self._store.get_unit(ku_id)
            if unit is None:
                continue
            # (7) mâu thuẫn với nguồn VERIFIED?
            verified_conflict = self._conflicts_with_verified(unit, answer_text)
            if verified_conflict:
                # (8) hỏi lại / giữ chưa giải quyết — KHÔNG âm thầm đổi
                self._store.mark_units_conflicted(ku_id, verified_conflict)
                version_updates.append({
                    "knowledge_id": ku_id, "action": "kept_conflicted",
                    "reason": f"answer contradicts VERIFIED {verified_conflict}",
                })
                continue
            new_version = self._apply_answer(unit, answer_text, feedback_kind, scope, q)
            version_updates.append(new_version)
            if new_version.get("superseded"):
                superseded_pairs.append((new_version["superseded_from"], new_version["knowledge_id"]))

        # đóng câu hỏi
        self._close_question(question_id, answer_text, answered_by, answered_at, feedback_kind)

        # (10)-(12) audit trail qua exchange log — không âm thầm thay đổi toàn hệ thống
        self._store.log_feedback(
            question_id=question_id, answer_text=answer_text, answered_by=answered_by,
            answered_at=answered_at, feedback_kind=feedback_kind, scope=scope,
            version_updates=version_updates,
        )

        return {
            "question_id": question_id,
            "feedback_kind": feedback_kind,
            "scope": scope,
            "affected_units": len(affected_ids),
            "version_updates": version_updates,
            "superseded_pairs": superseded_pairs,
            "production_approved": False,  # Test L — câu trả lời tri thức ≠ phê duyệt production
            "answered_at": answered_at,
        }

    # ---------------------------------------------------------------- steps

    def _classify_answer(self, answer_text: str) -> str:
        low = _norm(answer_text)
        for kind, markers in ANSWER_TYPE_KEYWORDS.items():
            if any(m in low for m in markers):
                return kind
        return FEEDBACK_KIND_CLARIFY

    def _extract_scope(self, answer_text: str, question: dict[str, Any]) -> str:
        low = _norm(answer_text)
        if "tổng quát" in low or "mọi trường hợp" in low or "mọi phạm vi" in low:
            return "general"
        return question.get("scope_hint", "") or "general"

    def _affected_unit_ids(self, question: dict[str, Any]) -> list[str]:
        """Tìm KU từ evidence refs (định dạng 'k_xxx: \"statement\" | ...')."""
        import re

        return re.findall(r"\bk_[0-9a-f]{12}", question.get("evidence", "") or "")

    def _conflicts_with_verified(self, unit: dict[str, Any], answer_text: str) -> str | None:
        """(7) câu trả lời có mâu thuẫn nguồn VERIFIED không — qua antonym/polarity."""
        from quan_ai_brain.memory.deep_memory import _antonym_flip, _has_negation

        for rel in unit.get("relations", []):
            if rel["relation_type"] != "CONTRADICTS":
                continue
            other_id = rel["to_id"] if rel["from_id"] == unit["knowledge_id"] else rel["from_id"]
            other = self._store.get_unit(other_id)
            if other is None or other["status"] != "VERIFIED":
                continue
            # câu trả lời nghiêng về phía nào?
            answer_neg = _has_negation(_norm(answer_text))
            unit_neg = _has_negation(_norm(unit["statement"]))
            other_neg = _has_negation(_norm(other["statement"]))
            # nếu answer đồng polarity với unit nhưng antonym với VERIFIED → conflict
            if answer_neg == unit_neg and _antonym_flip(answer_text, other["statement"]):
                return other_id
        return None

    def _apply_answer(
        self, unit: dict[str, Any], answer_text: str, feedback_kind: str,
        scope: str, question: dict[str, Any],
    ) -> dict[str, Any]:
        """(6)+(9) cập nhật KU: version+1, review_status, SUPERSEDES giữ lịch sử."""
        old_id = unit["knowledge_id"]
        old_version = int(unit.get("version", 1))
        # SUPERSEDES: tạo KU mới chứa nội dung làm rõ, KU cũ đánh dấu SUPERSEDED
        new_id = self._store.supersede_unit(
            old_id,
            statement=unit["statement"],
            updates={
                "review_status": "OWNER_CLARIFIED"
                if feedback_kind in (FEEDBACK_KIND_CLARIFY, FEEDBACK_KIND_SCOPE)
                else "OWNER_CONFIRMED",
                "scope": scope,
                "confidence": min(0.95, float(unit.get("confidence", 0.5)) + 0.2),
                "status": unit["status"] if unit["status"] not in ("CONFLICTED",) else "CANDIDATE",
            },
            owner_answer=answer_text,
        )
        return {
            "knowledge_id": new_id,
            "superseded_from": old_id,
            "superseded": True,
            "old_version": old_version,
            "new_version": old_version + 1,
            "feedback_kind": feedback_kind,
            "scope": scope,
        }

    def _close_question(
        self, question_id: str, answer_text: str, answered_by: str,
        answered_at: str, feedback_kind: str,
    ) -> None:
        with self._store._lock, self._store._connection:
            self._store._connection.execute(
                """
                UPDATE owner_questions
                SET status='ANSWERED', answer_text=?, answered_at_utc=?
                WHERE question_id=?
                """,
                (answer_text, answered_at, question_id),
            )

    # ---------------------------------------------------------------- §IX.11-12 affected conclusions

    def affected_conclusions(self, knowledge_id: str) -> list[dict[str, Any]]:
        """Ghi kết luận bị ảnh hưởng: KU INFERRED/CONCLUSION derived từ KU này."""
        with self._store._lock:
            rows = self._store._connection.execute(
                """
                SELECT knowledge_id, statement, status FROM knowledge_units
                WHERE derived_from_json LIKE ? AND status IN ('INFERRED','CONCLUSION')
                """,
                (f"%{knowledge_id}%",),
            ).fetchall()
        return [dict(r) for r in rows]


def _norm(text: str) -> str:
    from quan_ai_brain.memory.deep_memory import _normalize

    return _normalize(text)
