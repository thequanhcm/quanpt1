"""V9 Slice 4 tests — Owner Feedback: classify, versioning, supersede, Test F/L.

Map test §XIII MASTER PROMPT V9:
- Test F: phản hồi chủ cập nhật đúng tri thức, đúng phạm vi, giữ lịch sử (SUPERSEDES)
- Test L: trả lời làm rõ tri thức KHÔNG tự động phê duyệt production
- §IX.7-8: phản hồi mâu thuẫn nguồn VERIFIED → giữ CONFLICTED + không âm thầm đổi
- §IX.9-10: phiên bản + quan hệ SUPERSEDES + audit trail
"""
from __future__ import annotations

import json

import pytest

from quan_ai_brain.memory.deep_memory import DeepMemoryStore
from quan_ai_brain.memory.owner_feedback import (
    FEEDBACK_KIND_DECISION,
    FEEDBACK_KIND_SCOPE,
    OwnerFeedbackProcessor,
)


@pytest.fixture()
def store(tmp_path):
    s = DeepMemoryStore(tmp_path / "feedback_test.db")
    yield s
    s.close()


@pytest.fixture()
def processor(store):
    return OwnerFeedbackProcessor(store)


def _mk(store, stmt, ktype="FACT", scope="general", status="EXTRACTED"):
    subject, predicate, obj = store._decompose(stmt, ktype)
    return store._insert_unit(
        knowledge_type=ktype, subject=subject, predicate=predicate, object=obj,
        statement=stmt, source_refs=["episode:src"], evidence_refs=["episode:src"],
        scope=scope, status=status, confidence=0.5,
    )


def _mk_question(store, id_a, id_b, scope_hint="phạm vi session:s1") -> str:
    return store.create_owner_question(
        problem="Hai tri thức mâu thuẫn cùng phạm vi.",
        evidence=f"{id_a}: \"statement A\" | {id_b}: \"statement B\"",
        current_view="Đang giữ CONFLICTED.",
        interpretations_json=json.dumps([{"option": 1, "view": "A"}, {"option": 2, "view": "B"}],
                                        ensure_ascii=False),
        question="Thông tin nào đúng?",
        impact="Ảnh hưởng suy luận sau này.",
        scope_hint=scope_hint,
    )


# ---------------------------------------------------------------- Test F

def test_answer_updates_version_and_keeps_history(processor, store):
    """Test F — SUPERSEDES giữ lịch sử: KU cũ SUPERSEDED, KU mới derived_from cũ."""
    a = _mk(store, "Server online hoạt động bình thường", scope="s1")
    b = _mk(store, "Server offline hoàn toàn", scope="s1")
    store.link_units(batch=10)
    q_id = _mk_question(store, a, b)
    result = processor.answer_owner_question(q_id, "Chọn phương án 1: server online", "quanpt1")
    assert result["feedback_kind"] == FEEDBACK_KIND_DECISION
    assert result["affected_units"] >= 1
    # KU cũ giữ lại nhưng SUPERSEDED — không xoá
    ua = store.get_unit(a)
    assert ua is not None and ua["status"] == "SUPERSEDED"
    # KU mới tồn tại, derived_from → KU cũ, version tăng
    updates = result["version_updates"]
    new_id = updates[0]["knowledge_id"]
    un = store.get_unit(new_id)
    assert un is not None
    assert un["version"] == 2
    assert a in un["derived_from"]
    assert un["review_status"] in ("OWNER_CONFIRMED", "OWNER_CLARIFIED")
    # quan hệ SUPERSEDES cũ→mới
    rels = un["relations"]
    assert any(r["relation_type"] == "SUPERSEDES" and r["from_id"] == a for r in rels)
    # câu hỏi đóng
    q = store.get_owner_question(q_id)
    assert q["status"] == "ANSWERED"
    assert q["answer_text"].strip()
    assert q["answered_at_utc"]


def test_answer_not_allowed_twice(processor, store):
    q_id = _mk_question(store, "k_" + "a" * 12, "k_" + "b" * 12)
    processor.answer_owner_question(q_id, "Xác nhận phương án 1", "quanpt1")
    with pytest.raises(ValueError):
        processor.answer_owner_question(q_id, "Trả lời lại lần nữa", "quanpt1")


def test_scope_general_when_owner_says_so(processor, store):
    _mk(store, "Backup phải chạy lúc 2AM", "RULE", scope="s1")
    q_id = store.create_owner_question(
        problem="RULE lặp lại chưa rõ chính thức.",
        evidence="3 KU RULE",
        current_view="Đang giữ EXTRACTED.",
        interpretations_json="[]",
        question="Đây có phải quy tắc chính thức?",
        impact="Ưu tiên áp khi suy luận.",
        scope_hint="",
    )
    result = processor.answer_owner_question(q_id, "Đây là quy tắc tổng quát áp dụng mọi trường hợp",
                                             "quanpt1")
    assert result["scope"] == "general"


# ---------------------------------------------------------------- Test L

def test_answer_never_approves_production(processor, store):
    """Test L — câu trả lời làm rõ tri thức KHÔNG vượt qua phê duyệt production."""
    a = _mk(store, "Server online hoạt động bình thường", scope="s1")
    b = _mk(store, "Server offline hoàn toàn", scope="s1")
    store.link_units(batch=10)
    q_id = _mk_question(store, a, b)
    result = processor.answer_owner_question(q_id, "Chọn phương án 1", "quanpt1")
    assert result["production_approved"] is False
    # approval cards không bị đụng tới
    with store._lock:
        rows = store._connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='approval_cards'"
        ).fetchall()
    assert rows == []  # module feedback không tạo/sửa approval cards


# ---------------------------------------------------------------- §IX.7-8 conflict with VERIFIED

def test_answer_conflicting_with_verified_keeps_conflicted(processor, store):
    """Phản hồi mâu thuẫn nguồn VERIFIED → không âm thầm đổi, giữ CONFLICTED."""
    a = _mk(store, "Server online hoạt động bình thường", scope="s1")
    v = _mk(store, "Server offline hoàn toàn", scope="s1", status="VERIFIED")
    store.link_units(batch=10)
    q_id = _mk_question(store, a, v)
    result = processor.answer_owner_question(q_id, "Chắc chắn server online", "quanpt1")
    kept = [u for u in result["version_updates"]
            if u.get("action") == "kept_conflicted" or "kept_conflicted" in str(u.get("reason", ""))]
    assert kept, "phải giữ CONFLICTED thay vì âm thầm áp dụng"
    ua = store.get_unit(a)
    assert ua["status"] == "CONFLICTED"


# ---------------------------------------------------------------- idempotency + audit

def test_feedback_audit_logged_once(processor, store):
    _mk(store, "Server online", scope="s1")
    _mk(store, "Server offline", scope="s1")
    store.link_units(batch=10)
    q_id = _mk_question(store, "k_" + "c" * 12, "k_" + "d" * 12)
    processor.answer_owner_question(q_id, "Chọn phương án 1", "quanpt1")
    with store._lock:
        (n,) = store._connection.execute(
            "SELECT COUNT(*) FROM memory_exchange_log WHERE payload_type='owner_feedback_applied'"
        ).fetchone()
    assert n == 1
    # chạy lại blocked ở tầng câu hỏi — không có log thứ 2
    with pytest.raises(ValueError):
        processor.answer_owner_question(q_id, "lần 2", "quanpt1")
    with store._lock:
        (n2,) = store._connection.execute(
            "SELECT COUNT(*) FROM memory_exchange_log WHERE payload_type='owner_feedback_applied'"
        ).fetchone()
    assert n2 == 1


def test_empty_answer_rejected(processor, store):
    q_id = _mk_question(store, "k_" + "e" * 12, "k_" + "f" * 12)
    with pytest.raises(ValueError):
        processor.answer_owner_question(q_id, "   ", "quanpt1")


def test_unknown_question_rejected(processor, store):
    with pytest.raises(ValueError):
        processor.answer_owner_question("q_nothere", "câu trả lời", "quanpt1")
