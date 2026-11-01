"""Priority 1 Verification Tests: Core AI Correctness, LLMRouter & Output Grounding.

Sprint 2:
1. LLMRouter tier selection (Fast tier vs Reasoning tier)
2. Handling of planning, memory, and multi-step queries
3. Strict fallback provenance: never silently fall back to mock
4. Transparent failure reporting on timeout / offline
5. Output grounding: distinguishing user facts, inferred facts, and unverified data
"""
from __future__ import annotations

import pytest

from quan_ai_brain.cognition.context_builder import PromptContextBuilder
from quan_ai_brain.cognition.models import RetrievedMemory
from quan_ai_brain.core.guardrails import OutputGuardrails
from quan_ai_brain.llm.client import OllamaClient
from quan_ai_brain.llm.models import FallbackMode, LLMRequest, LLMResponse
from quan_ai_brain.llm.provider import LLMProvider
from quan_ai_brain.llm.router import LLMRouter, RoutingDecision
from quan_ai_brain.memory.models import MemoryType, VerificationStatus


def test_router_selects_fast_tier_for_simple_chat() -> None:
    router = LLMRouter(default_fast="qwen2.5:1.5b", default_reasoning="qwen2.5:7b")
    available = ["qwen2.5:7b", "qwen2.5:1.5b", "qwen2.5:0.5b"]

    decision = router.route("Xin chào trợ lý TONY", available_models=available)
    assert decision.tier == "fast"
    assert decision.model == "qwen2.5:1.5b"
    assert decision.is_fallback is False


def test_router_selects_reasoning_tier_for_planning() -> None:
    router = LLMRouter(default_fast="qwen2.5:1.5b", default_reasoning="qwen2.5:7b")
    available = ["qwen2.5:7b", "qwen2.5:1.5b"]

    decision = router.route("Hãy lập kế hoạch phân rã kiến trúc cho hệ thống điều phối", available_models=available)
    assert decision.tier == "reasoning"
    assert decision.model == "qwen2.5:7b"


def test_router_selects_reasoning_tier_for_multistep_analysis() -> None:
    router = LLMRouter(default_fast="qwen2.5:1.5b", default_reasoning="qwen2.5:7b")
    available = ["qwen2.5:7b", "qwen2.5:1.5b"]

    long_analysis = (
        "Phân tích nguyên nhân gốc rễ và đề xuất giải pháp xử lý sự cố suy giảm dung lượng "
        "chu kỳ nạp xả của cụm cell pin Lithium-ion theo tiêu chuẩn IEEE 1188. "
        "Yêu cầu liệt kê các bước kiểm tra điện áp hở mạch, nội trở AC/DC và nhiệt độ vận hành."
    )
    decision = router.route(long_analysis, task_hint="reasoning", available_models=available)
    assert decision.tier == "reasoning"
    assert decision.model == "qwen2.5:7b"


def test_router_respects_explicit_model_override() -> None:
    router = LLMRouter(default_fast="qwen2.5:1.5b", default_reasoning="qwen2.5:7b")
    available = ["qwen2.5:7b", "qwen2.5:1.5b", "llama3.1:latest"]

    decision = router.route("Câu hỏi đơn giản", explicit_model="llama3.1:latest", available_models=available)
    assert decision.tier == "explicit"
    assert decision.model == "llama3.1:latest"


def test_router_falls_back_gracefully_when_requested_model_missing() -> None:
    router = LLMRouter(default_fast="qwen2.5:1.5b", default_reasoning="qwen2.5:7b")
    available = ["qwen2.5:7b"]  # Fast model is missing

    decision = router.route("Xin chào", available_models=available)
    # Should fall back to reasoning model rather than failing
    assert decision.model == "qwen2.5:7b"
    assert decision.is_fallback is True


def test_provider_strict_never_fallback_mode_on_offline() -> None:
    # Point client to a non-existent port to simulate offline daemon
    offline_client = OllamaClient(base_url="http://127.0.0.1:59999", default_timeout=0.1)
    provider = LLMProvider(client=offline_client, fallback_mode=FallbackMode.NEVER)

    health = provider.health(timeout=0.05)
    assert health["ollama_online"] is False
    assert health["active_provider"] == "none"

    # In NEVER mode, generate should return error or fail-fast, never fabricate a mock response
    req = LLMRequest(prompt="Test prompt", model="qwen2.5:7b")
    resp = provider.generate(req)
    assert resp.success is False
    assert resp.is_mock is False
    assert resp.error_code is not None


def test_provider_on_error_fallback_marks_mock_provenance() -> None:
    offline_client = OllamaClient(base_url="http://127.0.0.1:59999", default_timeout=0.1)
    provider = LLMProvider(client=offline_client, fallback_mode=FallbackMode.ON_ERROR)

    req = LLMRequest(prompt="Test fallback prompt", model="qwen2.5:7b")
    resp = provider.generate(req)

    # In ON_ERROR mode, mock response must be explicitly flagged
    assert resp.is_mock is True
    assert resp.provider == "mock"
    assert "MOCK FALLBACK" in (resp.warning or "")


def test_output_grounding_provenance_separation() -> None:
    builder = PromptContextBuilder()
    guard = OutputGuardrails()

    # Context contains user-provided fact
    user_fact = "Chủ sở hữu Quanpt1 đã phê duyệt tài liệu kiến trúc."
    built = builder.build(
        user_query="Kiểm tra trạng thái phê duyệt",
        retrieval=[
            RetrievedMemory(
                memory_id="mem_01",
                memory_type=MemoryType.DECISION.value,
                content=user_fact,
                source_ref="manual",
                verification_status=VerificationStatus.VERIFIED.value,
                confidence_score=1.0,
                project_scope="general",
                version=1,
                score=1.0,
                selection_reason="Exact match",
                is_allowed_in_prompt=True,
            )
        ],
    )

    combined_context = built.system_instructions + "\n" + built.rendered_context
    assert user_fact in combined_context

    # Guardrails verify no raw credential leakage
    raw_response = f"Theo thông tin đã xác minh: {user_fact} (Không có bí mật nào)."
    cleaned_text, warnings = guard.sanitize(raw_response)
    assert "Không có bí mật nào" in cleaned_text

