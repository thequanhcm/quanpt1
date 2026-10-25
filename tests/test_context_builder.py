"""Unit tests for QUAN AI BRAIN Prompt Context Builder (Sprint 2C)."""
from __future__ import annotations

from pathlib import Path
import pytest

from quan_ai_brain.cognition.context_builder import PromptContextBuilder
from quan_ai_brain.cognition.models import BuiltContext, RetrievalResult, RetrievedMemory
from quan_ai_brain.cognition.retrieval import CognitiveRetriever
from quan_ai_brain.llm import FallbackMode, LLMProvider, LLMRequest
from quan_ai_brain.memory.models import MemoryType, VerificationStatus
from quan_ai_brain.memory.sqlite_store import MemoryStore


def _make_dummy_memory(
    mem_id: str,
    content: str,
    mem_type: str = MemoryType.SEMANTIC.value,
    status: str = VerificationStatus.VERIFIED.value,
    source: str = "TestSource",
    score: float = 0.95,
    allowed: bool = True,
) -> RetrievedMemory:
    return RetrievedMemory(
        memory_id=mem_id,
        memory_type=mem_type,
        content=content,
        source_ref=source,
        verification_status=status,
        confidence_score=1.0,
        project_scope="DC-COMMAND",
        version=1,
        score=score,
        selection_reason="unit_test",
        is_allowed_in_prompt=allowed,
    )


def test_context_builder_sections_and_provenance():
    builder = PromptContextBuilder(default_max_chars=4000)

    m1 = _make_dummy_memory("m-1", "Hạ tải tủ Rack A01 khi quá nhiệt 40C", mem_type=MemoryType.PROCEDURAL.value)
    m2 = _make_dummy_memory("m-2", "DC-COMMAND sử dụng chuẩn truyền thông Modbus RTU", mem_type=MemoryType.SEMANTIC.value)
    m3 = _make_dummy_memory(
        "m-3",
        "Quanpt1 yêu cầu báo cáo qua Telegram trước khi chạy lệnh",
        mem_type=MemoryType.PREFERENCE.value,
        status=VerificationStatus.USER_PROVIDED.value,
    )

    ctx = builder.build(
        user_query="Làm sao để xử lý khi Rack A01 quá nhiệt?",
        retrieval=[m1, m2, m3],
        project_scope="DC-COMMAND",
    )

    assert isinstance(ctx, BuiltContext)
    assert not ctx.is_truncated
    assert len(ctx.used_memories) == 3
    assert len(ctx.excluded_memories) == 0

    rendered = ctx.rendered_context

    # Required section headers
    assert "[SYSTEM INSTRUCTIONS & GOVERNANCE]" in rendered
    assert "[APPROVED / VERIFIED MEMORY]" in rendered
    assert "[RELEVANT PROCEDURES & DECISIONS]" in rendered
    assert "[USER PREFERENCES & PRIORITIES]" in rendered
    assert "[SOURCE REFERENCES AUDIT]" in rendered
    assert "[USER REQUEST]" in rendered

    # Content verification in right sections
    assert "Hạ tải tủ Rack A01" in rendered
    assert "Modbus RTU" in rendered
    assert "Telegram" in rendered
    assert "Làm sao để xử lý khi Rack A01 quá nhiệt?" in rendered

    # Source audit verification
    assert "Ref #1: ID=m-1" in rendered
    assert "Ref #2: ID=m-2" in rendered
    assert "Ref #3: ID=m-3" in rendered


def test_context_builder_empty_memories():
    builder = PromptContextBuilder()
    ctx = builder.build(user_query="Có quy trình bảo dưỡng pin không?", retrieval=[])

    assert len(ctx.used_memories) == 0
    assert "(No verified memories matched the current request)" in ctx.rendered_context
    assert "(No memory references utilized)" in ctx.rendered_context
    assert "[USER REQUEST]\nCó quy trình bảo dưỡng pin không?" in ctx.rendered_context


def test_context_builder_budget_enforcement():
    builder = PromptContextBuilder()
    # Create several large memory chunks
    m1 = _make_dummy_memory("m-1", "Dữ liệu cấu hình rất dài số 1 " + "A" * 200)
    m2 = _make_dummy_memory("m-2", "Dữ liệu cấu hình rất dài số 2 " + "B" * 200)
    m3 = _make_dummy_memory("m-3", "Dữ liệu cấu hình rất dài số 3 " + "C" * 200)

    # Use very tight budget (e.g. 900 chars)
    ctx = builder.build(
        user_query="Cấu hình hệ thống",
        retrieval=[m1, m2, m3],
        max_chars=900,
    )

    assert ctx.is_truncated is True
    assert len(ctx.excluded_memories) > 0
    # Any excluded items must cite budget_exceeded
    for _, reason in ctx.excluded_memories:
        assert reason == "budget_exceeded"


def test_context_builder_disallowed_memory_exclusion():
    builder = PromptContextBuilder()
    m_allowed = _make_dummy_memory("m-ok", "Kiến thức hợp lệ", allowed=True)
    m_disallowed = _make_dummy_memory(
        "m-bad",
        "Tri thức chưa duyệt",
        mem_type=MemoryType.CANDIDATE.value,
        status=VerificationStatus.CANDIDATE.value,
        allowed=False,
    )

    ctx = builder.build(
        user_query="Kiểm tra tri thức",
        retrieval=[m_allowed, m_disallowed],
    )

    assert len(ctx.used_memories) == 1
    assert ctx.used_memories[0].memory_id == "m-ok"
    assert len(ctx.excluded_memories) == 1
    assert ctx.excluded_memories[0][0] == "m-bad"
    assert "disallowed_status" in ctx.excluded_memories[0][1]


def test_context_builder_redaction():
    builder = PromptContextBuilder()
    secret_content = "Kết nối API server với Bearer sk-ant-api03-secret1234567890abcdef"
    m_secret = _make_dummy_memory("m-sec", secret_content)

    ctx = builder.build(
        user_query="Lấy cấu hình API server",
        retrieval=[m_secret],
    )

    assert "sk-ant-api03" not in ctx.rendered_context
    assert "Bearer [REDACTED]" in ctx.rendered_context


def test_context_builder_validation():
    builder = PromptContextBuilder()

    with pytest.raises(ValueError, match="user_query must be a non-empty string"):
        builder.build(user_query="")

    with pytest.raises(ValueError, match="user_query must be a non-empty string"):
        builder.build(user_query="   ")

    with pytest.raises(ValueError, match="max_chars budget must be between 100 and 50,000"):
        builder.build(user_query="test", max_chars=50)

    with pytest.raises(ValueError, match="max_chars budget must be between 100 and 50,000"):
        builder.build(user_query="test", max_chars=100_000)


def test_end_to_end_cognitive_llm_pipeline(tmp_path: Path):
    db_file = tmp_path / "brain_e2e.db"
    with MemoryStore(db_file, workspace=tmp_path) as store:
        # Seed memories
        store.store_memory(
            content="Quy trình hạ tải khẩn cấp tủ rack DC-A1: cắt nguồn PDU-01 trước",
            memory_type=MemoryType.PROCEDURAL,
            source_ref="SOP-DC-PDU",
            verification_status=VerificationStatus.VERIFIED,
            project_scope="DC-COMMAND",
        )
        store.store_memory(
            content="Quanpt1 yêu cầu xác nhận 2 bước trước khi hạ tải",
            memory_type=MemoryType.PREFERENCE,
            source_ref="Owner Directive",
            verification_status=VerificationStatus.USER_PROVIDED,
            project_scope="DC-COMMAND",
        )

        retriever = CognitiveRetriever(store)
        retrieval = retriever.retrieve("quy trình hạ tải khẩn cấp DC-A1", project_scope="DC-COMMAND")

        assert retrieval.total_found >= 1

        builder = PromptContextBuilder()
        built_ctx = builder.build("Làm sao để hạ tải tủ rack DC-A1 an toàn?", retrieval)

        assert built_ctx.total_chars > 0
        assert len(built_ctx.used_memories) >= 1

        # Feed into LLMProvider with FallbackMode.ALWAYS_MOCK
        llm = LLMProvider(fallback_mode=FallbackMode.ALWAYS_MOCK)
        req = LLMRequest(
            prompt=built_ctx.rendered_context,
            system_prompt=built_ctx.system_instructions,
        )
        resp = llm.generate(req)

        assert resp.success is True
        assert resp.is_mock is True
        assert "[MOCK]" in resp.text
        assert "MOCK MODE" in (resp.warning or "")
        assert resp.model == "qwen2.5:7b"
