"""Unit and integration tests for BGE-M3 Embedding Service and Hybrid Semantic Retrieval."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch
import pytest

from quan_ai_brain.cognition.embedding import BGEEmbeddingService, cosine_similarity
from quan_ai_brain.cognition.models import MemoryQuery
from quan_ai_brain.cognition.retrieval import CognitiveRetriever
from quan_ai_brain.llm.client import OllamaClient
from quan_ai_brain.memory.models import LifecycleStatus, MemoryRecord, MemoryType, VerificationStatus
from quan_ai_brain.memory.sqlite_store import MemoryStore


def test_cosine_similarity_mathematics():
    """Verify standard-library cosine similarity correctness across geometric properties."""
    # Identical vectors
    v1 = [1.0, 2.0, 3.0]
    assert pytest.approx(cosine_similarity(v1, v1), rel=1e-5) == 1.0

    # Orthogonal vectors
    v_x = [1.0, 0.0, 0.0]
    v_y = [0.0, 1.0, 0.0]
    assert pytest.approx(cosine_similarity(v_x, v_y), abs=1e-5) == 0.0

    # Opposite vectors
    v_neg = [-1.0, -2.0, -3.0]
    assert pytest.approx(cosine_similarity(v1, v_neg), rel=1e-5) == -1.0

    # Empty, zero, or mismatched lengths
    assert cosine_similarity([], [1.0]) == 0.0
    assert cosine_similarity([0.0, 0.0], [1.0, 2.0]) == 0.0
    assert cosine_similarity([1.0, 2.0], [1.0, 2.0, 3.0]) == 0.0


def test_ollama_client_embed_mock():
    """Verify OllamaClient.embed() handles successful response and error scenarios."""
    client = OllamaClient(base_url="http://127.0.0.1:11434")

    # Empty prompt returns empty list immediately
    assert client.embed("") == []
    assert client.embed("   ") == []

    # Mock successful embedding
    fake_vector = [0.123] * 1024
    fake_response = json.dumps({"embedding": fake_vector}).encode("utf-8")

    mock_resp = MagicMock()
    mock_resp.read.return_value = fake_response
    mock_resp.__enter__.return_value = mock_resp

    with patch("quan_ai_brain.llm.client.urllib.request.urlopen", return_value=mock_resp):
        with patch.object(client, "is_daemon_online", return_value=True):
            vec = client.embed("Nguồn điện dự phòng Data Center", model="bge-m3")
            assert len(vec) == 1024
            assert vec[0] == pytest.approx(0.123)


def test_bge_embedding_service_cache_and_similarity():
    """Verify BGEEmbeddingService vector caching and similarity computation."""
    mock_client = MagicMock(spec=OllamaClient)
    # Return different vectors for different inputs
    mock_client.embed.side_effect = lambda text, model, timeout: (
        [1.0, 0.0, 0.0] if "pin" in text.lower() else [0.0, 1.0, 0.0]
    )
    mock_client.ping.return_value = True

    svc = BGEEmbeddingService(client=mock_client, model_name="bge-m3", max_cache_entries=100)
    assert svc.is_available() is True

    # 1. First call triggers embed
    v1 = svc.embed_text("bình pin ắc quy")
    assert v1 == [1.0, 0.0, 0.0]
    assert mock_client.embed.call_count == 1

    # 2. Second identical call hits cache
    v1_cached = svc.embed_text("bình pin ắc quy")
    assert v1_cached == [1.0, 0.0, 0.0]
    assert mock_client.embed.call_count == 1  # No extra call

    # 3. Compute similarity
    sim = svc.compute_similarity("bình pin ắc quy", "máy lạnh chiller")
    # [1, 0, 0] vs [0, 1, 0] orthogonal -> 0.0
    assert pytest.approx(sim, abs=1e-5) == 0.0

    stats = svc.stats()
    assert stats["model_name"] == "bge-m3"
    assert stats["cached_entries"] == 2


def test_cognitive_retriever_hybrid_bge_m3():
    """Verify CognitiveRetriever leverages BGE-M3 semantic similarity to discover relevant memories."""
    store = MemoryStore(":memory:")

    # Seed 2 verified memories
    # Memory 1: Talks about backup battery without using the exact phrase "nguồn điện dự phòng"
    rec1 = store.store_memory(
        content="Bình ắc quy UPS trạm Pháp Vân cần được đo nội trở định kỳ hàng tháng.",
        memory_type=MemoryType.SEMANTIC.value,
        verification_status=VerificationStatus.VERIFIED.value,
        project_scope="datacenter",
    )
    # Memory 2: Unrelated topic
    rec2 = store.store_memory(
        content="Giao diện Web UI Cockpit hoạt động trên cổng 8766.",
        memory_type=MemoryType.SEMANTIC.value,
        verification_status=VerificationStatus.VERIFIED.value,
        project_scope="web",
    )

    # 1. Test classic retriever without BGE-M3
    retriever_classic = CognitiveRetriever(store=store, embedding_service=None)
    # Searching with "nguồn điện dự phòng" has zero keyword overlap with rec1 or rec2
    res_classic = retriever_classic.retrieve("nguồn điện dự phòng")
    assert len(res_classic.memories) == 0

    # 2. Test hybrid retriever with BGE-M3 embedding service mock
    mock_svc = MagicMock(spec=BGEEmbeddingService)
    # Simulate high semantic similarity (0.82) between "nguồn điện dự phòng" and battery UPS rec1
    mock_svc.compute_similarity.side_effect = lambda q, c: (
        0.82 if "ắc quy" in c else 0.05
    )

    retriever_hybrid = CognitiveRetriever(store=store, embedding_service=mock_svc)
    res_hybrid = retriever_hybrid.retrieve("nguồn điện dự phòng")

    assert len(res_hybrid.memories) == 1
    matched = res_hybrid.memories[0]
    assert matched.memory_id == rec1.id
    assert "semantic_dense_match" in matched.selection_reason
    assert "bge_m3_semantic(0.82)" in matched.selection_reason


def test_candidate_quarantine_preserved_under_bge_m3():
    """Verify CANDIDATE quarantine boundary remains impenetrable even with 1.0 semantic similarity."""
    store = MemoryStore(":memory:")

    # Candidate quarantined memory
    cand = store.store_memory(
        content="Đề xuất thay thế toàn bộ giàn bình ắc quy sang pin Lithium chưa được duyệt.",
        memory_type=MemoryType.CANDIDATE.value,
        verification_status=VerificationStatus.CANDIDATE.value,
    )

    mock_svc = MagicMock(spec=BGEEmbeddingService)
    mock_svc.compute_similarity.return_value = 1.0  # Perfect semantic match

    retriever = CognitiveRetriever(store=store, embedding_service=mock_svc)

    # Default query must exclude candidate despite perfect semantic similarity
    res = retriever.retrieve("pin Lithium ắc quy")
    assert len(res.memories) == 0

    # Only when explicitly requested
    res_with_cand = retriever.retrieve(
        MemoryQuery(
            query="pin Lithium ắc quy",
            include_candidates=True,
            memory_types=[MemoryType.SEMANTIC, MemoryType.CANDIDATE],
            allowed_verification_statuses=[VerificationStatus.VERIFIED, VerificationStatus.CANDIDATE],
        )
    )
    assert len(res_with_cand.memories) == 1
    assert res_with_cand.memories[0].is_allowed_in_prompt is False


def test_bge_m3_live_probe():
    """Live integration probe verifying BGE-M3 against local Ollama service if daemon is online."""
    client = OllamaClient()
    if not client.ping(timeout=0.2):
        pytest.skip("Local Ollama daemon is offline; live test skipped.")

    models = [m.name.lower() for m in client.list_models()]
    if not any("bge-m3" in m for m in models):
        pytest.skip("bge-m3 model not loaded in Ollama; live test skipped.")

    svc = BGEEmbeddingService(client=client, model_name="bge-m3")
    vec = svc.embed_text("Kiểm tra điện áp bình ắc quy")
    assert len(vec) == 1024
    assert any(x != 0.0 for x in vec)

    # Test semantic similarity between two related phrases vs an unrelated phrase
    sim_related = svc.compute_similarity("hệ thống ắc quy UPS", "bộ lưu điện dự phòng trạm nguồn")
    sim_unrelated = svc.compute_similarity("hệ thống ắc quy UPS", "nấu cơm bằng nồi cơm điện")

    assert sim_related > sim_unrelated
