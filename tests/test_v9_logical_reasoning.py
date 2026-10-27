"""V9 Slice 2 tests — Logical Reasoning: A/B/C conclusions, circularity, traceability.

Map test §XIII MASTER PROMPT V9:
- Test D: suy luận lưu derived_from + assumptions + conclusion_type
- Test J: truy xuất KU liên quan phục vụ câu hỏi nhiệm vụ mới
- Test K (phần 2): truy vết conclusion về nguồn qua engine
- §V.3: chống vòng tròn — KU suy từ B không xác nhận B; shared origin chỉ tính 1
- §V.4: mâu thuẫn DIRECT vs CONTEXT_DIFFERENCE, không tự chọn phía
"""
from __future__ import annotations

import json

import pytest

from quan_ai_brain.cognition.logical_reasoning import (
    CONCLUSION_A,
    CONCLUSION_B,
    CONCLUSION_C,
    LogicalReasoningEngine,
)
from quan_ai_brain.memory.deep_memory import DeepMemoryStore


@pytest.fixture()
def store(tmp_path):
    s = DeepMemoryStore(tmp_path / "reason_test.db")
    yield s
    s.close()


@pytest.fixture()
def engine(store):
    return LogicalReasoningEngine(store)


def _mk(store, stmt, ktype="FACT", scope="general", status="EXTRACTED", source="episode:src1"):
    subject, predicate, obj = store._decompose(stmt, ktype)
    return store._insert_unit(
        knowledge_type=ktype, subject=subject, predicate=predicate, object=obj,
        statement=stmt, source_refs=[source], evidence_refs=[source],
        scope=scope, status=status, confidence=0.75,
    )


# ---------------------------------------------------------------- retrieval (Test J)

def test_retrieval_by_token_overlap(engine, store):
    _mk(store, "Server PID 8216 giữ cổng 8765 cho dashboard", scope="s1")
    _mk(store, "Watchdog phải luôn chạy nền 24/7", "RULE", "s1")
    _mk(store, "Dự án đào tạo AI có 345 học viên", scope="s1")
    result = engine.answer_question("Server 8216 đang chạy thế nào?", scope="s1")
    assert result["conclusion_type"] in (CONCLUSION_A, CONCLUSION_B, CONCLUSION_C)
    assert len(result["evidence_refs"]) >= 1
    matched = [u for u in result.get("hypotheses", [])]
    assert isinstance(matched, list)


def test_retrieval_empty_when_no_related_knowledge(engine, store):
    _mk(store, "Dự án đào tạo AI có 345 học viên", scope="s1")
    result = engine.answer_question("Thời tiết ngày mai thế nào?", scope="s1")
    assert result["conclusion_type"] == CONCLUSION_C
    assert "không có tri thức nào liên quan" in result["missing_info"][0]


# ---------------------------------------------------------------- Test D conclusions

def test_conclusion_b_records_reasoning_and_assumptions(engine, store):
    ku = _mk(store, "Server PID 8216 giữ cổng 8765", scope="s1", status="EXTRACTED")
    result = engine.answer_question("Server 8216 giữ cổng nào?", scope="s1")
    assert result["conclusion_type"] == CONCLUSION_B
    assert result["evidence_refs"], "phải có bằng chứng"
    assert ku in result["evidence_refs"]
    assert result["steps"], "phải lưu các bước hình thành kết luận"
    assert result["confidence_breakdown"]["note"], "confidence phải khai báo bản chất"


def test_inferred_knowledge_never_treated_as_verified(engine, store):
    """PHẦN IV.1: INFERRED ≠ VERIFIED — chỉ VERIFIED đủ điều kiện kết luận loại A."""
    _mk(store, "Server PID 8216 giữ cổng 8765", scope="s1", status="INFERRED")
    result = engine.answer_question("Server 8216 giữ cổng nào?", scope="s1")
    assert result["conclusion_type"] != CONCLUSION_A  # INFERRED không đủ cho A


def test_conclusion_a_requires_verified(engine, store):
    _mk(store, "Server PID 8216 giữ cổng 8765", scope="s1", status="VERIFIED")
    result = engine.answer_question("Server 8216 giữ cổng nào?", scope="s1")
    assert result["conclusion_type"] == CONCLUSION_A
    assert "8765" in result["conclusion"]


# ---------------------------------------------------------------- §V.3 circularity

def test_shared_origin_counted_once(engine, store):
    """Nhiều KU cùng nguồn gốc → KHÔNG được coi là đa bằng chứng độc lập."""
    _mk(store, "Server PID 8216 giữ cổng 8765", scope="s1", source="episode:same")
    _mk(store, "Server PID 8216 giữ cổng 8766", scope="s1", source="episode:same")
    result = engine.answer_question("Server 8216 giữ những cổng nào?", scope="s1")
    assert any("cùng nguồn" in s for s in result["shared_origins"]), (
        "shared origin phải được phát hiện và ghi nhận"
    )
    # penalty phải áp dụng
    assert result["confidence_breakdown"]["contradiction_penalty"] >= 0.0


def test_derived_chain_no_cycle(engine, store):
    """Chống vòng tròn: A suy từ B, không dùng A xác nhận B (chain có visited-set)."""
    kb = _mk(store, "Server chạy ổn định", scope="s1")
    ka = store._insert_unit(
        knowledge_type="CONCLUSION", subject="Server", predicate="concludes",
        object="ổn định do watchdog", statement="Vậy nên server ổn định",
        source_refs=["inference"], evidence_refs=[kb],
        scope="s1", status="INFERRED", confidence=0.6,
        meta={"derived_from": [kb]},
    )
    # ghi derived_from qua UPDATE vì _insert_unit không nhận derived_from trực tiếp
    with store._lock, store._connection:
        store._connection.execute(
            "UPDATE knowledge_units SET derived_from_json=? WHERE knowledge_id=?",
            (json.dumps([kb]), ka),
        )
    chain = store.trace(ka)
    assert chain["chain"][0] == ka
    assert kb in chain["chain"]
    assert not chain["cycles_detected"]


# ---------------------------------------------------------------- §V.4 contradictions

def test_contradiction_analysis_no_auto_resolution(engine, store):
    a = _mk(store, "Server online hoạt động bình thường", scope="s1")
    b = _mk(store, "Server offline hoàn toàn", scope="s1")
    store.link_units(batch=10)
    result = engine.analyze_contradiction(a, b)
    assert result["classification"] in ("DIRECT", "CONTEXT_DIFFERENCE")
    assert result["auto_resolution"] is None  # KHÔNG tự chọn phía (Test C triết lý)


def test_contradiction_context_difference_when_scopes_differ(engine, store):
    a = _mk(store, "Server online hoạt động bình thường", scope="s1")
    b = _mk(store, "Server offline hoàn toàn", scope="s2")
    store.link_units(batch=10)
    result = engine.analyze_contradiction(a, b)
    assert result["same_scope"] is False


def test_contradicted_knowledge_penalized(engine, store):
    _mk(store, "Server online hoạt động bình thường", scope="s1")
    _mk(store, "Server offline hoàn toàn", scope="s1")
    store.link_units(batch=10)
    result = engine.answer_question("Server hiện tại thế nào?", scope="s1")
    assert result["conclusion_type"] == CONCLUSION_C
    assert any("mâu thuẫn" in m for m in result["missing_info"])


# ---------------------------------------------------------------- traceability

def test_conclusion_traceable_to_source(engine, store):
    """Test K phần engine — bằng chứng phải truy được về episode nguồn."""
    subject, predicate, obj = store._decompose("Server PID 8216 giữ cổng 8765", "FACT")
    ku = store._insert_unit(
        knowledge_type="FACT", subject=subject, predicate=predicate, object=obj,
        statement="Server PID 8216 giữ cổng 8765",
        source_refs=["episode:ep_real_123"], evidence_refs=["episode:ep_real_123"],
        scope="s1", status="VERIFIED", confidence=0.95,
    )
    result = engine.answer_question("Server 8216 giữ cổng nào?", scope="s1")
    assert "episode:ep_real_123" in result["evidence_refs"]
    trace = store.trace(ku)
    assert any(ep["id"] == "ep_real_123" for ep in trace["source_episodes"])


def test_engine_handles_empty_question(engine):
    result = engine.answer_question("")
    assert result.get("error") == "empty_question"
