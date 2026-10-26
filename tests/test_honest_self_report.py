"""Tests for honest self-report: Living Grounding Facts + Owner Teach pipeline.

Background (owner requirement 27/10/2026): the bot must never lie about
itself — e.g. claiming inference runs on the PC while it actually runs on
NetMind cloud, or presenting unverified architecture as verified fact.
"""
from __future__ import annotations

import pytest

from quan_ai_brain.cognition.grounding_facts import (
    collect_grounding_facts,
    render_grounding_block,
)
from quan_ai_brain.cognition.teach_pipeline import (
    detect_teaching,
    persist_taught_memory,
)


# ---------------------------------------------------------------------------
# Grounding facts — real probes (no network beyond localhost TCP)
# ---------------------------------------------------------------------------


def test_grounding_facts_cloud_model_says_cloud() -> None:
    facts = collect_grounding_facts(current_model="zai-org/GLM-5.3-Flash")
    assert "cloud" in facts["llm"]["runs_on"].lower()
    assert facts["llm"]["model"] == "zai-org/GLM-5.3-Flash"
    # The architecture truth must NOT claim local inference for a cloud model
    assert "cloud" in facts["architecture_truth"].lower()


def test_grounding_facts_ollama_offline_is_reported_offline() -> None:
    facts = collect_grounding_facts(current_model="zai-org/GLM-5.3-Flash")
    # In this test environment Ollama is offline; the probe must say so
    # (if someone starts Ollama locally the test still passes — both are honest)
    comp = facts["components"]
    assert comp["ollama_local"] in ("ONLINE", "OFFLINE")
    if comp["ollama_local"] == "OFFLINE":
        assert "OFFLINE" in facts["architecture_truth"] or "cloud" in facts["architecture_truth"].lower()


def test_grounding_block_contains_truth_rules() -> None:
    facts = collect_grounding_facts(current_model="zai-org/GLM-5.3-Flash")
    block = render_grounding_block(facts)
    assert "BỘ SỰ THẬT SỐNG" in block
    assert "GLM" in block or "cloud" in block.lower()
    # avatar honesty rule present
    assert "giao diện 2D" in block
    # offline must not be beautified
    assert facts["pi5_status"].startswith(("ONLINE", "OFFLINE"))


def test_grounding_runtime_reports_real_python() -> None:
    import sys as _sys

    facts = collect_grounding_facts()
    assert facts["runtime"]["python"] == f"{_sys.version_info.major}.{_sys.version_info.minor}.{_sys.version_info.micro}"


# ---------------------------------------------------------------------------
# Teach pipeline — owner transfers knowledge → persisted as USER_PROVIDED
# ---------------------------------------------------------------------------


@pytest.fixture()
def mem_store(tmp_path):
    from quan_ai_brain.memory.sqlite_store import MemoryStore

    db = tmp_path / "brain.db"
    store = MemoryStore(str(db), workspace=tmp_path)
    yield store
    store.close()


def test_detect_teaching_positive() -> None:
    assert detect_teaching("nhớ rằng PC đặt ở phòng làm việc A").is_teaching
    assert detect_teaching("ghi nhớ rằng: tôi thích báo cáo ngắn").is_teaching
    r = detect_teaching("từ giờ luôn trả lời bằng tiếng Việt")
    assert r.is_teaching


def test_detect_teaching_negative() -> None:
    assert not detect_teaching("em tên là gì?").is_teaching
    assert not detect_teaching("báo cáo trạng thái").is_teaching
    assert not detect_teaching("").is_teaching


def test_detect_teaching_preference_hint() -> None:
    r = detect_teaching("nhớ rằng tôi thích nhận báo cáo vào 7h sáng")
    assert r.is_teaching
    assert r.memory_type == "PREFERENCE"
    r2 = detect_teaching("nhớ rằng server đặt ở tầng 3 tòa B")
    assert r2.memory_type == "FACT"


def test_persist_taught_memory_user_provided(mem_store) -> None:
    saved = persist_taught_memory(mem_store, "PC Core đặt tại phòng máy chủ", "FACT")
    assert saved["memory_type"] == "SEMANTIC"
    rec = mem_store.get_memory(saved["id"])
    assert rec is not None
    assert str(rec.verification_status.value if hasattr(rec.verification_status, "value") else rec.verification_status) == "USER_PROVIDED"
    assert rec.source_ref.startswith("owner_teach:")


def test_taught_memory_is_retrievable(mem_store) -> None:
    persist_taught_memory(mem_store, "Quanpt1 thích uống cà phê sữa mỗi sáng", "FACT")
    from quan_ai_brain.cognition.models import MemoryQuery
    from quan_ai_brain.cognition.retrieval import CognitiveRetriever

    retriever = CognitiveRetriever(mem_store)
    result = retriever.retrieve(MemoryQuery(query="cà phê sữa"))
    texts = [m.content for m in result.memories]
    assert any("cà phê sữa" in t for t in texts)
