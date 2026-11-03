"""Tests M3 Memory API consolidation (01/11/2026, ĐÃ DUYỆT).

Phủ: classify_statement heuristic, MemoryFacade add/search/fact_only/stats,
promotion fail-closed, và facade cũ MemoryService (bug add() đã fix).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

WS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WS / "src"))

from quan_ai_brain.memory.sqlite_store import (  # noqa: E402
    MemoryStore,
    MemoryType,
    VerificationStatus,
)
from quan_ai_brain.memory.unified_memory import (  # noqa: E402
    FactLevel,
    MemoryFacade,
    classify_statement,
)


@pytest.fixture()
def facade() -> MemoryFacade:
    st = MemoryStore(":memory:")
    f = MemoryFacade(st)
    yield f
    st.close()


# ---------------------------------------------------------------
# classify_statement — sàng lọc FACT/INFERENCE
# ---------------------------------------------------------------

@pytest.mark.parametrize("text,expected", [
    ("Có thể mai trời mưa", FactLevel.INFERENCE),
    ("Tôi nghĩ hệ thống sẽ ổn định", FactLevel.INFERENCE),
    ("Dự kiến hoàn thành tuần sau", FactLevel.INFERENCE),
    ("maybe the server is down", FactLevel.INFERENCE),
    ("pytest 3.013 PASS đã xác minh", FactLevel.OBSERVED),
    ("telemetry đo temp 58.7C", FactLevel.OBSERVED),
    ("log cho thấy không lỗi", FactLevel.OBSERVED),
])
def test_classify_statement(text, expected):
    assert classify_statement(text) == expected


def test_classify_empty_is_inference():
    assert classify_statement("") == FactLevel.INFERENCE
    assert classify_statement("   ") == FactLevel.INFERENCE


# ---------------------------------------------------------------
# MemoryFacade.add — route + gắn nhãn đúng
# ---------------------------------------------------------------

def test_add_heuristic_default_marks_inference(facade):
    r = facade.add("Có thể cần restart server")
    assert r["layer"] == "semantic"
    assert r["fact_level"] == "INFERENCE"


def test_add_fact_level_str_coerced(facade):
    r = facade.add("pytest PASS đã xác minh", fact_level="FACT")
    assert r["fact_level"] == "FACT"


def test_add_fact_level_enum(facade):
    r = facade.add("Đo temp 58.7C", fact_level=FactLevel.OBSERVED)
    assert r["fact_level"] == "OBSERVED"


def test_add_empty_raises(facade):
    with pytest.raises(ValueError):
        facade.add("   ")


def test_add_verification_status_wins_over_heuristic(facade):
    r = facade.add("Có thể mưa", verification_status="VERIFIED")
    assert r["fact_level"] == "FACT"


# ---------------------------------------------------------------
# MemoryFacade.search — sàng lọc
# ---------------------------------------------------------------

def test_search_fact_only_filters_inference(facade):
    facade.add("Có thể mai trời mưa")
    facade.add("pytest 3.013 PASS đã xác minh", fact_level="FACT")
    all_hits = facade.search("", top_k=10)
    assert {h.fact_level.value for h in all_hits} == {"INFERENCE", "FACT"}
    fact_hits = facade.search("", top_k=10, fact_only=True)
    assert len(fact_hits) == 1
    assert fact_hits[0].fact_level == FactLevel.FACT


def test_search_query_match(facade):
    facade.add("Piper TTS đã cài xong", fact_level="FACT")
    facade.add("Kiến thức khác hoàn toàn", fact_level="FACT")
    hits = facade.search("Piper", fact_only=True)
    assert len(hits) == 1
    assert "Piper" in hits[0].content


def test_hit_to_dict_shape(facade):
    facade.add("Xác minh rồi", fact_level="FACT")
    d = facade.search("", top_k=1)[0].to_dict()
    for key in ("source_layer", "id", "content", "fact_level", "verification_status"):
        assert key in d


# ---------------------------------------------------------------
# add_episode — sự kiện đã xảy ra
# ---------------------------------------------------------------

def test_add_episode(facade):
    eid = facade.add_episode("[TEST] M3 episode", kind="test", source_ref="m3")
    assert eid


# ---------------------------------------------------------------
# stats — tổng quan theo fact level
# ---------------------------------------------------------------

def test_stats_counts_by_fact_level(facade):
    facade.add("Có thể chậm", )                      # INFERENCE
    facade.add("Đã xác minh 3.013 PASS", fact_level="FACT")
    s = facade.stats()
    assert s["semantic_by_fact_level"]["INFERENCE"] == 1
    assert s["semantic_by_fact_level"]["FACT"] == 1


# ---------------------------------------------------------------
# promote_to_fact — fail-closed (chuẩn R4)
# ---------------------------------------------------------------

def test_promote_without_governance_db_fails_closed(facade):
    rid = facade.add("Có thể cần restart", )["id"]
    with pytest.raises(PermissionError):
        facade.promote_to_fact(rid, approved_by="Quanpt1", approval_evidence="TASK-NOPE")


def test_promote_missing_memory_raises(facade, tmp_path, monkeypatch):
    # Cung cấp governance.db rỗng (đúng schema tối thiểu) để tới được bước get_memory
    import sqlite3
    gov = tmp_path / "data" / "governance.db"
    gov.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(gov)
    con.execute("CREATE TABLE approval_cards (task_code TEXT PRIMARY KEY, title TEXT, "
                "card_markdown TEXT, status TEXT, version INTEGER DEFAULT 1, "
                "created_at_utc TEXT, updated_at_utc TEXT, ttl_expires_at_utc TEXT, "
                "request_id TEXT DEFAULT '', evidence_json TEXT DEFAULT '[]')")
    con.execute("CREATE TABLE approvals (approval_id TEXT PRIMARY KEY, request_id TEXT, "
                "approver TEXT, tool_id TEXT, action TEXT, params_json TEXT, "
                "resource_scope TEXT, risk_level INTEGER, fingerprint TEXT, status TEXT, "
                "granted_at_utc TEXT, expires_at_utc TEXT, consumed INTEGER DEFAULT 0, "
                "consumed_at_utc TEXT, revoked INTEGER DEFAULT 0, revocation_reason TEXT, "
                "auth_method TEXT, notes TEXT, audit_ref TEXT)")
    con.commit()
    con.close()
    monkeypatch.setattr("quan_ai_brain.memory.unified_memory.Path.cwd", lambda: tmp_path)
    with pytest.raises(KeyError):
        facade.promote_to_fact("no-such-id", approved_by="Quanpt1", approval_evidence="TASK-X")


# ---------------------------------------------------------------
# Facade cũ MemoryService — bug add() gọi method không tồn tại
# ---------------------------------------------------------------

def test_memory_service_add_no_longer_silent_bug(tmp_path, monkeypatch):
    """MemoryService.add_memory gọi vector_store.add (không tồn tại) → luôn error.

    Fix M3: dùng add_memory(MemoryChunk) chuẩn của LongTermMemoryStore.
    Note: chromadb embedding service có thể cần model — mock để test logic facade.
    """
    from quan_ai_brain.memory.memory_service import MemoryService
    from quan_ai_brain.memory.vector_store import MemoryChunk

    svc = MemoryService()

    class FakeVector:
        def add_memory(self, chunk: MemoryChunk) -> str:
            return chunk.id

        def search(self, query, top_k=5):
            return []

    svc.vector_store = FakeVector()
    result = svc.add_memory("kiến thức test", memory_type="semantic")
    assert "error" not in result, f"bug cũ còn: {result}"
    assert result.get("id")
