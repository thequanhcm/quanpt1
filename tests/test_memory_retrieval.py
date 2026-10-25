"""Unit tests for QUAN AI BRAIN Cognitive Memory Retriever (Sprint 2C)."""
from __future__ import annotations

from pathlib import Path
import pytest

from quan_ai_brain.cognition.models import (
    MEMORY_TYPE_WEIGHTS,
    VERIFICATION_STATUS_WEIGHTS,
    MemoryQuery,
    RetrievedMemory,
)
from quan_ai_brain.cognition.retrieval import CognitiveRetriever, _tokenize
from quan_ai_brain.memory.models import LifecycleStatus, MemoryType, VerificationStatus
from quan_ai_brain.memory.sqlite_store import MemoryStore


@pytest.fixture
def memory_store(tmp_path: Path) -> MemoryStore:
    db_file = tmp_path / "brain_test.db"
    store = MemoryStore(db_file, workspace=tmp_path)
    return store


def test_tokenize():
    tokens = _tokenize("Hạ tải hệ thống DC-COMMAND khi nhiệt độ > 45°C!")
    assert "hạ" in tokens
    assert "tải" in tokens
    assert "thống" in tokens
    assert "dc" in tokens
    assert "command" in tokens
    assert "nhiệt" in tokens


def test_memory_query_validation():
    # Valid query
    q = MemoryQuery(query="hạ tải khẩn cấp", top_k=5, max_chars=2000)
    assert q.query == "hạ tải khẩn cấp"
    assert q.top_k == 5
    assert q.max_chars == 2000

    # Empty query rejected
    with pytest.raises(ValueError, match="Query must be a non-empty string"):
        MemoryQuery(query="")

    with pytest.raises(ValueError, match="Query must be a non-empty string"):
        MemoryQuery(query="   ")

    # Invalid top_k
    with pytest.raises(ValueError, match="top_k must be an integer between 1 and 50"):
        MemoryQuery(query="test", top_k=0)

    with pytest.raises(ValueError, match="top_k must be an integer between 1 and 50"):
        MemoryQuery(query="test", top_k=51)

    # Invalid max_chars
    with pytest.raises(ValueError, match="max_chars budget must be an integer between 100 and 50,000"):
        MemoryQuery(query="test", max_chars=50)

    with pytest.raises(ValueError, match="max_chars budget must be an integer between 100 and 50,000"):
        MemoryQuery(query="test", max_chars=60_000)


def test_retriever_exact_phrase_and_token_search(memory_store: MemoryStore):
    # Seed memories
    m1 = memory_store.store_memory(
        content="Quy trình hạ tải khẩn cấp cho Data Center khi mất nguồn lưới",
        memory_type=MemoryType.PROCEDURAL,
        source_ref="SOP-DC-01",
        verification_status=VerificationStatus.VERIFIED,
        project_scope="DC-COMMAND",
        tags=["sop", "ha_tai", "datacenter"],
    )
    m2 = memory_store.store_memory(
        content="Thông số pin lưu điện đạt 98% dung lượng định mức",
        memory_type=MemoryType.SEMANTIC,
        source_ref="telemetry",
        verification_status=VerificationStatus.VERIFIED,
        project_scope="BATTERY_AI",
        tags=["battery", "telemetry"],
    )

    retriever = CognitiveRetriever(memory_store)

    # Search for "hạ tải"
    res = retriever.retrieve(MemoryQuery(query="hạ tải khẩn cấp"))
    assert res.total_found >= 1
    found_ids = [m.memory_id for m in res.memories]
    assert m1.id in found_ids
    assert m2.id not in found_ids

    # First result should be m1
    top = res.memories[0]
    assert top.memory_id == m1.id
    assert top.memory_type == MemoryType.PROCEDURAL.value
    assert top.verification_status == VerificationStatus.VERIFIED.value
    assert "exact_phrase_match" in top.selection_reason


def test_retriever_memory_type_ranking(memory_store: MemoryStore):
    # Two records matching same query tokens, one is SEMANTIC, one is EPISODIC
    m_sem = memory_store.store_memory(
        content="Ngưỡng nhiệt độ an toàn của trạm pin là 35 độ C",
        memory_type=MemoryType.SEMANTIC,
        source_ref="Doc-Safety-Spec",
        verification_status=VerificationStatus.VERIFIED,
        project_scope="general",
    )
    m_epi = memory_store.store_memory(
        content="Hôm qua ghi nhận nhiệt độ an toàn của trạm pin là 35 độ C",
        memory_type=MemoryType.EPISODIC,
        source_ref="Incident-Log-101",
        verification_status=VerificationStatus.VERIFIED,
        project_scope="general",
    )

    retriever = CognitiveRetriever(memory_store)
    res = retriever.retrieve(MemoryQuery(query="nhiệt độ an toàn trạm pin"))

    assert len(res.memories) == 2
    # SEMANTIC should outrank EPISODIC due to type weight (1.0 vs 0.70)
    assert res.memories[0].memory_id == m_sem.id
    assert res.memories[1].memory_id == m_epi.id
    assert res.memories[0].score > res.memories[1].score


def test_retriever_verification_status_ranking(memory_store: MemoryStore):
    # Two records matching same content, one VERIFIED, one USER_PROVIDED
    m_ver = memory_store.store_memory(
        content="Máy chủ DC-01 sử dụng nguồn điện kép 2N",
        memory_type=MemoryType.SEMANTIC,
        source_ref="Electrical-Blueprint",
        verification_status=VerificationStatus.VERIFIED,
        project_scope="DC-COMMAND",
    )
    m_user = memory_store.store_memory(
        content="Máy chủ DC-01 sử dụng nguồn điện kép 2N theo nhận định",
        memory_type=MemoryType.SEMANTIC,
        source_ref="Quanpt1 chat",
        verification_status=VerificationStatus.USER_PROVIDED,
        project_scope="DC-COMMAND",
    )

    retriever = CognitiveRetriever(memory_store)
    res = retriever.retrieve(MemoryQuery(query="Máy chủ DC-01 nguồn điện kép 2N"))

    assert len(res.memories) == 2
    # VERIFIED (1.0) must outrank USER_PROVIDED (0.85)
    assert res.memories[0].memory_id == m_ver.id
    assert res.memories[1].memory_id == m_user.id
    assert res.memories[0].score > res.memories[1].score


def test_retriever_candidate_quarantined_by_default(memory_store: MemoryStore):
    # Seed a candidate memory
    cand = memory_store.store_memory(
        content="Thuật toán tối ưu năng lượng mới tiết kiệm 20% điện năng",
        memory_type=MemoryType.CANDIDATE,
        source_ref="AI-Experiment-Unverified",
        verification_status=VerificationStatus.CANDIDATE,
        project_scope="general",
    )
    verified = memory_store.store_memory(
        content="Thuật toán tối ưu năng lượng tiêu chuẩn tiết kiệm 5% điện năng",
        memory_type=MemoryType.SEMANTIC,
        source_ref="Verified-Standard",
        verification_status=VerificationStatus.VERIFIED,
        project_scope="general",
    )

    retriever = CognitiveRetriever(memory_store)

    # 1. Default retrieval: CANDIDATE must be completely absent from results!
    res_default = retriever.retrieve(MemoryQuery(query="thuật toán tối ưu năng lượng"))
    returned_ids = [m.memory_id for m in res_default.memories]
    assert verified.id in returned_ids
    assert cand.id not in returned_ids

    # 2. Explicit inclusion: only when include_candidates=True AND allowed_statuses includes CANDIDATE
    res_with_cand = retriever.retrieve(
        MemoryQuery(
            query="thuật toán tối ưu năng lượng",
            include_candidates=True,
            memory_types=[MemoryType.SEMANTIC, MemoryType.CANDIDATE],
            allowed_verification_statuses=[VerificationStatus.VERIFIED, VerificationStatus.CANDIDATE],
        )
    )
    cand_ids = [m.memory_id for m in res_with_cand.memories]
    assert cand.id in cand_ids
    # Even if included, verified item must rank higher
    assert res_with_cand.memories[0].memory_id == verified.id


def test_retriever_project_scope_filtering(memory_store: MemoryStore):
    m_dc = memory_store.store_memory(
        content="Khởi động máy phát điện dự phòng khi mất điện lưới",
        memory_type=MemoryType.PROCEDURAL,
        source_ref="SOP-GEN-01",
        verification_status=VerificationStatus.VERIFIED,
        project_scope="DC-COMMAND",
    )
    m_battery = memory_store.store_memory(
        content="Khởi động bộ sạc pin khi mất điện lưới",
        memory_type=MemoryType.PROCEDURAL,
        source_ref="SOP-BAT-02",
        verification_status=VerificationStatus.VERIFIED,
        project_scope="BATTERY_AI",
    )

    retriever = CognitiveRetriever(memory_store)

    # Scoped to DC-COMMAND
    res = retriever.retrieve(
        MemoryQuery(query="khởi động khi mất điện lưới", project_scope="DC-COMMAND")
    )
    ids = [m.memory_id for m in res.memories]
    assert m_dc.id in ids
    assert m_battery.id not in ids


def test_retriever_empty_result(memory_store: MemoryStore):
    retriever = CognitiveRetriever(memory_store)
    res = retriever.retrieve(MemoryQuery(query="từ khóa hoàn toàn không tồn tại trong DB xyz123"))
    assert res.total_found == 0
    assert len(res.memories) == 0
    assert res.total_chars == 0


def test_retriever_traceability_and_top_k(memory_store: MemoryStore):
    for i in range(10):
        memory_store.store_memory(
            content=f"Dữ liệu kiểm tra hiệu năng hệ thống cụm số {i}",
            memory_type=MemoryType.SEMANTIC,
            source_ref=f"Audit-Log-{i}",
            verification_status=VerificationStatus.VERIFIED,
            project_scope="general",
        )

    retriever = CognitiveRetriever(memory_store)
    res = retriever.retrieve(MemoryQuery(query="hiệu năng hệ thống", top_k=3))

    assert len(res.memories) == 3
    for m in res.memories:
        assert m.memory_id != ""
        assert m.source_ref.startswith("Audit-Log-")
        assert m.version == 1
        assert m.is_allowed_in_prompt is True
        assert m.score > 0.0


def test_retriever_superseded_memory_exclusion(memory_store: MemoryStore):
    old_rec = memory_store.store_memory(
        content="Địa chỉ IP của gateway DC-COMMAND là 192.168.1.1",
        memory_type=MemoryType.SEMANTIC,
        source_ref="Old Config",
        verification_status=VerificationStatus.VERIFIED,
        project_scope="DC-COMMAND",
    )
    new_rec = memory_store.supersede_memory(
        old_rec.id,
        new_content="Địa chỉ IP của gateway DC-COMMAND là 10.0.0.1",
        source_ref="New Config",
    )

    retriever = CognitiveRetriever(memory_store)
    res = retriever.retrieve(MemoryQuery(query="gateway DC-COMMAND", project_scope="DC-COMMAND"))

    ids = [m.memory_id for m in res.memories]
    assert new_rec.id in ids
    assert old_rec.id not in ids
