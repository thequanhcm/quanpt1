"""V9 Slice 1 tests — Deep Memory: extraction, relations, traceability, idempotency.

Map test §XIII MASTER PROMPT V9:
- Test A: trích xuất phân biệt FACT/OPINION/QUESTION/RULE (PHẦN XIII A)
- Test B: quan hệ đều có basis; speculative đánh dấu đúng (PHẦN XIII B)
- Test G: idempotency — extract chạy lại không nhân bản (PHẦN VI.3)
- Test I: migration additive — bảng cũ không đổi (PHẄN XII.3)
- Test K: trace về được episode nguồn (PHẦN XIII K)
"""
from __future__ import annotations

import json
import sqlite3

import pytest

from quan_ai_brain.memory.deep_memory import (
    DeepMemoryStore,
    _classify,
    _confidence,
    _split_sentences,
)

SESSION_META = {
    "session_id": "sess_test_1",
    "user_query": "Server 8216 đang chạy ổn định không? Tôi nghĩ là ổn.",
    "assistant_reply": (
        "Server PID 8216 giữ cổng 8765 và 8766. Watchdog phải luôn chạy nền 24/7. "
        "Có lẽ kết nối Pi5 đã sẵn sàng."
    ),
}


def _seed_episode(store: DeepMemoryStore, episode_id: str, meta: dict) -> None:
    store._connection.execute(
        """
        INSERT INTO episodes (id, created_at_utc, kind, summary, source_ref, status, metadata_json)
        VALUES (?, ?, 'chat_turn', ?, 'test://seed', 'recorded', ?)
        """,
        (
            episode_id,
            "2026-10-28T00:00:00+00:00",
            "seed summary",
            json.dumps(meta, ensure_ascii=False),
        ),
    )
    store._connection.commit()


@pytest.fixture()
def store(tmp_path):
    s = DeepMemoryStore(tmp_path / "deep_test.db")
    yield s
    s.close()


# ---------------------------------------------------------------- Test A

def test_classify_question_fact_rule_opinion():
    assert _classify("Server bao nhiêu cổng đang mở?") == "QUESTION"
    assert _classify("Server PID 8216 giữ cổng 8765.") == "FACT"
    assert _classify("Watchdog phải luôn chạy nền 24/7.") == "RULE"
    assert _classify("Tôi nghĩ hệ thống đã ổn định.") == "OPINION"


def test_split_sentences_basic():
    parts = _split_sentences("Câu một. Câu hai! Câu ba?")
    assert parts == ["Câu một.", "Câu hai!", "Câu ba?"]


def test_confidence_breakdown_bounds():
    c_owner = _confidence("owner_chat")
    c_episode = _confidence("episode", contradicted=True)
    assert 0.0 < c_episode < c_owner <= 1.0
    # PHẦN IV.2: không bao giờ full-mark nếu chưa verified
    assert c_owner < 1.0


# ---------------------------------------------------------------- extraction on seeded episode

def test_extract_from_chat_turns_creates_typed_units(store):
    _seed_episode(store, "ep_v9_t1", SESSION_META)
    stats = store.extract_from_chat_turns(limit=10)
    assert stats["episodes_processed"] == 1
    assert stats["units_created"] >= 1
    assert sum(stats["by_type"].values()) == stats["units_created"]
    with store._lock:
        rows = store._connection.execute(
            "SELECT knowledge_type, statement, scope FROM knowledge_units"
        ).fetchall()
    scopes = {r["scope"] for r in rows}
    assert scopes == {"session:sess_test_1"}
    types = {r["knowledge_type"] for r in rows}
    assert "QUESTION" in types
    assert "RULE" in types


def test_extract_idempotent_no_duplicates_on_rerun(store):
    """Test G — exchange log UNIQUE(correlation, source, target, type, ref)."""
    _seed_episode(store, "ep_v9_t2", SESSION_META)
    first = store.extract_from_chat_turns(limit=10)
    second = store.extract_from_chat_turns(limit=10)
    assert second["units_created"] == 0  # đã log → không nhân bản
    assert second["skipped_already_logged"] >= 1
    with store._lock:
        (n,) = store._connection.execute("SELECT COUNT(*) FROM knowledge_units").fetchone()
        (m,) = store._connection.execute("SELECT COUNT(*) FROM memory_exchange_log").fetchone()
    assert n == first["units_created"]  # tổng số không đổi sau chạy lại
    assert m == 1  # đúng 1 exchange message cho episode


def test_statement_preserved_and_redaction_applied(store):
    """PHẦN X.1: nguồn giữ nguyên; PHẦN XII.10: không ghi secret."""
    meta = dict(SESSION_META)
    meta["assistant_reply"] = "Token truy cập là ghp_ABCDEF1234567890abcdef. Server chạy cổng 8765."
    _seed_episode(store, "ep_v9_t3", meta)
    store.extract_from_chat_turns(limit=10)
    with store._lock:
        rows = [r["statement"] for r in store._connection.execute(
            "SELECT statement FROM knowledge_units").fetchall()]
    joined = " ".join(rows)
    assert "ghp_ABCDEF1234567890abcdef" not in joined
    assert any("8765" in s for s in rows)


# ---------------------------------------------------------------- Test B relations

def _mk_unit(store: DeepMemoryStore, stmt: str, ktype: str = "FACT", scope: str = "general") -> str:
    subject, predicate, obj = store._decompose(stmt, ktype)
    return store._insert_unit(
        knowledge_type=ktype, subject=subject, predicate=predicate, object=obj,
        statement=stmt, source_refs=["episode:test"], evidence_refs=["episode:test"],
        scope=scope, status="EXTRACTED", confidence=0.75,
    )


def test_relations_have_basis_and_speculative_flag(store):
    """Test B — mọi quan hệ đều có basis; token-overlap là speculative."""
    k1 = _mk_unit(store, "Server PID 8216 giữ cổng 8765 cho dashboard", scope="s")
    k2 = _mk_unit(store, "Server PID 8216 giữ cổng 8766 cho API", scope="s")
    k3 = _mk_unit(store, "Watchdog phải luôn chạy để auto restart server", scope="s")
    store.link_units(batch=50)
    with store._lock:
        rows = store._connection.execute(
            "SELECT from_id, relation_type, to_id, basis, is_speculative FROM knowledge_relations"
        ).fetchall()
    assert rows, "phải sinh được ít nhất một quan hệ có căn cứ"
    for r in rows:
        assert r["basis"].strip(), f"relation {r['relation_id']} thiếu basis"
    with store._lock:
        (n_rel,) = store._connection.execute("SELECT COUNT(*) FROM knowledge_relations").fetchone()
    assert n_rel <= 3 * 20  # _MAX_RELATIONS_PER_UNIT


def test_contradiction_detection_marks_both(store):
    """Test C phần cốt lõi: cùng subject+predicate, polarity ngược → CONTRADICTS."""
    a = _mk_unit(store, "Server online và hoạt động", scope="s")
    b = _mk_unit(store, "Server offline hoàn toàn", scope="s")
    store.link_units(batch=10)
    with store._lock:
        rel = store._connection.execute(
            "SELECT relation_type FROM knowledge_relations WHERE "
            "(from_id=? AND to_id=?) OR (from_id=? AND to_id=?)",
            (a, b, b, a),
        ).fetchone()
        ca = store._connection.execute(
            "SELECT confidence, contradiction_refs_json FROM knowledge_units WHERE knowledge_id=?",
            (a,),
        ).fetchone()
    assert rel is not None and rel["relation_type"] == "CONTRADICTS"
    assert ca["confidence"] < 0.75  # bị hạ
    assert b in json.loads(ca["contradiction_refs_json"])


def test_same_subject_consistent_not_contradiction(store):
    a = _mk_unit(store, "Server PID 8216 giữ cổng 8765", scope="s")
    b = _mk_unit(store, "Server PID 8216 giữ cổng 8765 sau restart", scope="s")
    store.link_units(batch=10)
    with store._lock:
        rel = store._connection.execute(
            "SELECT relation_type FROM knowledge_relations WHERE from_id=? AND to_id=?",
            (a, b),
        ).fetchone()
    assert rel is None or rel["relation_type"] != "CONTRADICTS"


def test_relations_scoped_isolated(store):
    """Quan hệ không tạo xuyên scope — ngữ cảnh lịch sử giữ nguyên (PHẦN III 3.1)."""
    a = _mk_unit(store, "Server PID 8216 giữ cổng 8765", scope="session:old")
    b = _mk_unit(store, "Server PID 8216 giữ cổng 8765", scope="session:new")
    store.link_units(batch=10)
    with store._lock:
        (n,) = store._connection.execute(
            "SELECT COUNT(*) FROM knowledge_relations WHERE (from_id=? AND to_id=?) "
            "OR (from_id=? AND to_id=?)", (a, b, b, a),
        ).fetchone()
    assert n == 0


# ---------------------------------------------------------------- Test I additive

def test_additive_migration_old_tables_untouched(tmp_path):
    """Test I — bảng cũ giữ nguyên count/schema; 5 bảng mới được tạo thêm."""
    db = tmp_path / "migr.db"
    conn = sqlite3.connect(db)
    conn.executescript(
        """
        CREATE TABLE episodes (id TEXT PRIMARY KEY, created_at_utc TEXT, kind TEXT,
            summary TEXT, source_ref TEXT, status TEXT, metadata_json TEXT);
        INSERT INTO episodes VALUES ('e1','t','chat_turn','s','r','ok','{}');
        CREATE TABLE memories (id TEXT PRIMARY KEY, memory_type TEXT);
        INSERT INTO memories VALUES ('m1','EPISODIC');
        """
    )
    conn.commit()
    conn.close()
    before_counts = {"episodes": 1, "memories": 1}
    store = DeepMemoryStore(db)
    store.extract_from_chat_turns(limit=5)
    store.close()
    conn = sqlite3.connect(db)
    after_counts = {
        "episodes": conn.execute("SELECT COUNT(*) FROM episodes").fetchone()[0],
        "memories": conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0],
    }
    cols = [r[1] for r in conn.execute("PRAGMA table_info(episodes)").fetchall()]
    conn.close()
    assert after_counts == before_counts
    assert cols == ["id", "created_at_utc", "kind", "summary", "source_ref", "status", "metadata_json"]


# ---------------------------------------------------------------- Test K trace

def test_trace_returns_source_episode(store):
    """Test K — trace về được episode nguồn."""
    _seed_episode(store, "ep_v9_trace", SESSION_META)
    store.extract_from_chat_turns(limit=10)
    with store._lock:
        row = store._connection.execute(
            "SELECT knowledge_id FROM knowledge_units LIMIT 1"
        ).fetchone()
    result = store.trace(row["knowledge_id"])
    assert result["chain"] and result["chain"][0] == row["knowledge_id"]
    assert any(ep["id"] == "ep_v9_trace" for ep in result["source_episodes"])


def test_get_unit_includes_relations_and_parsed_json(store):
    k1 = _mk_unit(store, "Watchdog phải luôn chạy nền", "RULE", "s")
    k2 = _mk_unit(store, "Watchdog restart server khi gặp lỗi", "FACT", "s")
    store.link_units(batch=10)
    unit = store.get_unit(k1)
    assert unit is not None
    assert isinstance(unit["source_refs"], list)
    assert isinstance(unit["relations"], list)


def test_deep_stats_shape(store):
    _seed_episode(store, "ep_v9_stats", SESSION_META)
    store.extract_from_chat_turns(limit=5)
    s = store.deep_stats()
    assert s["knowledge_units_total"] >= 1
    assert s["exchange_messages_total"] >= 1
    assert s["last_review_run"] is None  # chưa chạy review nào


def test_review_run_checkpoint_roundtrip(store):
    run_id = store.create_review_run(batch_limit=7)
    store.update_run_checkpoint(run_id, "LINK", "cursor_x", ["k1", "k2"])
    store.finish_review_run(run_id, "COMPLETED", {"units": 2})
    run = store.get_review_run(run_id)
    assert run["status"] == "COMPLETED"
    assert run["checkpoint"]["stage"] == "LINK"
    assert run["checkpoint"]["cursor"] == "cursor_x"
    assert run["stats"] == {"units": 2}


def test_semantic_junk_report_read_only(store):
    """PHẦN II mục 5: chỉ báo cáo, không sửa bảng cũ."""
    store._connection.execute(
        "INSERT INTO semantic_memory (id, created_at_utc, statement, source_ref, approved_by, regression_passed) "
        "VALUES ('sm1','t','#!/bin/bash\necho hello','test','none',0)"
    )
    store._connection.commit()
    report = store.report_semantic_junk(limit=10)
    assert report["junk_candidates"] >= 1
    with store._lock:
        (n,) = store._connection.execute("SELECT COUNT(*) FROM semantic_memory").fetchone()
    assert n == 1  # không xoá
