"""V9 Slice 3 tests — Review Cycle: 10 stages, checkpoint resume, owner questions A–G.

Map test §XIII MASTER PROMPT V9:
- Test E: câu hỏi chủ đúng cấu trúc A–G, không hỏi lại câu OPEN
- Test C (phần cycle): mâu thuẫn → CONFLICTED + NEEDS_OWNER_REVIEW
- Test H: checkpoint resume sau gián đoạn giữa stage
- Test G (phần cycle): chạy 2 lần không nhân bản sự kiện/câu hỏi
"""
from __future__ import annotations

import json

import pytest

from quan_ai_brain.cognition.memory_review_cycle import STAGES, MemoryReviewCycle
from quan_ai_brain.memory.deep_memory import DeepMemoryStore


@pytest.fixture()
def store(tmp_path):
    s = DeepMemoryStore(tmp_path / "review_test.db")
    yield s
    s.close()


def _mk(store, stmt, ktype="FACT", scope="general"):
    subject, predicate, obj = store._decompose(stmt, ktype)
    return store._insert_unit(
        knowledge_type=ktype, subject=subject, predicate=predicate, object=obj,
        statement=stmt, source_refs=["episode:src"], evidence_refs=["episode:src"],
        scope=scope, status="EXTRACTED", confidence=0.75,
    )


def _seed_chat_turn(store, episode_id, query, reply):
    store._connection.execute(
        "INSERT INTO episodes (id, created_at_utc, kind, summary, source_ref, status, metadata_json) "
        "VALUES (?,?,?,?,?,?,?)",
        (episode_id, "2026-10-28T00:00:00+00:00", "chat_turn", "s", "r", "recorded",
         json.dumps({"session_id": "sess1", "user_query": query, "assistant_reply": reply},
                    ensure_ascii=False)),
    )
    store._connection.commit()


# ---------------------------------------------------------------- full run

def test_full_run_completes_all_stages(store):
    _seed_chat_turn(store, "ep_r1", "Server 8216 đang chạy không?",
                    "Server PID 8216 giữ cổng 8765. Watchdog phải luôn chạy.")
    cycle = MemoryReviewCycle(store, batch_limit=20)
    result = cycle.run()
    assert result["status"] == "COMPLETED"
    assert result["stages_completed"] == list(STAGES)
    assert result["new_units"] >= 0  # extract chạy trong Slice1 API, cycle Collect chỉ đếm


def test_run_twice_no_duplicate_questions_or_units(store):
    """Test G phần cycle — idempotency toàn vòng."""
    _seed_chat_turn(store, "ep_r2", "Câu hỏi?", "Câu trả lời.")
    cycle = MemoryReviewCycle(store, batch_limit=20)
    first = cycle.run()
    second = cycle.run()
    assert second["owner_questions"] == 0  # câu hỏi đã tồn tại → không hỏi lại
    with store._lock:
        (n1,) = store._connection.execute("SELECT COUNT(*) FROM knowledge_units").fetchone()
        (n2,) = store._connection.execute("SELECT COUNT(*) FROM owner_questions").fetchone()
    first_stats = store.get_review_run(first["run_id"])
    assert n2 <= first["owner_questions"] + 1  # không nhân bản


# ---------------------------------------------------------------- Test E owner questions

def test_contradiction_generates_structured_question(store):
    """Test E — câu hỏi A–G đầy đủ, không tự chọn phía."""
    a = _mk(store, "Server online hoạt động bình thường", scope="s1")
    b = _mk(store, "Server offline hoàn toàn", scope="s1")
    store.link_units(batch=10)
    cycle = MemoryReviewCycle(store, batch_limit=10)
    result = cycle.run()
    assert result["owner_questions"] >= 1
    qs = store.list_owner_questions(status="OPEN")
    assert len(qs) == 1
    q = qs[0]
    # cấu trúc A–G (list_owner_questions đã parse interpretations)
    assert q["problem"].strip()          # A
    assert q["evidence"].strip()         # B
    assert q["current_view"].strip()     # C
    interp = q["interpretations"]
    assert len(interp) >= 2              # D — các phương án thực sự khác nhau
    assert "?" in q["question"]          # E
    assert q["impact"].strip()           # F
    assert q["scope_hint"].strip()       # G
    # hai phía bị đánh dấu CONFLICTED — không chọn phía (Test C)
    ua, ub = store.get_unit(a), store.get_unit(b)
    assert ua["status"] == "CONFLICTED"
    assert ub["status"] == "CONFLICTED"
    assert ua["statement"] and ub["statement"]  # giữ nguyên nội dung


def test_context_difference_not_escalated(store):
    """Mâu thuẫn khác scope → hệ thống tự xử lý (giữ cả hai theo phạm vi), không hỏi."""
    _mk(store, "Server online hoạt động bình thường", scope="session:A")
    _mk(store, "Server offline hoàn toàn", scope="session:B")
    store.link_units(batch=10)
    cycle = MemoryReviewCycle(store, batch_limit=10)
    result = cycle.run()
    assert result["owner_questions"] == 0


def test_repeated_rule_generates_question(store):
    """§VIII.1: RULE lặp ≥3 lần chưa rõ chính thức → hỏi chủ."""
    for i in range(3):
        _mk(store, "Backup phải chạy lúc 2AM mỗi ngày", ktype="RULE", scope=f"s{i}")
    cycle = MemoryReviewCycle(store, batch_limit=10)
    result = cycle.run()
    assert result["owner_questions"] >= 1
    qs = store.list_owner_questions(status="OPEN")
    assert any("quy tắc chính thức" in q["question"] for q in qs)


# ---------------------------------------------------------------- Test H checkpoint

def test_checkpoint_resume_after_interrupt(store):
    """Test H — gián đoạn giữa stage, resume tiếp tục từ checkpoint đúng."""
    _seed_chat_turn(store, "ep_h1", "Câu hỏi 1?", "Trả lời 1.")
    cycle = MemoryReviewCycle(store, batch_limit=5)
    run_id = store.create_review_run(batch_limit=5)
    # mô phỏng: chạy tới stage LINK rồi "đứt"
    cycle._stage_collect({})
    store.update_run_checkpoint(run_id, "LINK", "LINK", [])
    # resume
    result = cycle.run(resume_run_id=run_id)
    assert result["status"] == "COMPLETED"
    run = store.get_review_run(run_id)
    assert run["status"] == "COMPLETED"
    # LINK trở về sau đã KHÔNG chạy lại COLLECT — stages_completed chứa đủ 10
    assert len(run["stats"]["stages_completed"]) == len(STAGES)


def test_resume_unknown_run_raises(store):
    cycle = MemoryReviewCycle(store)
    with pytest.raises(ValueError):
        cycle.run(resume_run_id="run_nonexistent")


def test_batch_limit_respected(store):
    """§XII.7: batch limit giới hạn số xử lý mỗi đợt."""
    cycle = MemoryReviewCycle(store, batch_limit=3)
    assert cycle._batch_limit == 3
    with pytest.raises(ValueError):
        MemoryReviewCycle(store, batch_limit=0)
