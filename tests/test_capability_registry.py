"""Tests for CapabilityRegistry in QUAN AI BRAIN."""
from __future__ import annotations

import pytest

from quan_ai_brain.cognition.capability_registry import (
    CapabilityRegistry,
    CapabilityStatus,
    SystemCapability,
    SYSTEM_CAPABILITIES,
)
from quan_ai_brain.cognition.context_builder import PromptContextBuilder
from quan_ai_brain.cognition.retrieval import CognitiveRetriever
from quan_ai_brain.memory.sqlite_store import MemoryStore


def test_capability_registry_defaults():
    registry = CapabilityRegistry()
    caps = registry.list_capabilities()
    assert len(caps) >= 7
    ids = [c.capability_id for c in caps]
    assert "long_term_memory" in ids
    assert "local_llm_inference" in ids
    assert "self_learning_v1" in ids
    assert "web_ui_voice" in ids


def test_system_capability_to_dict():
    cap = SystemCapability(
        capability_id="test_cap",
        name="Test Capability",
        description="A test capability description.",
        domain="Test",
        status=CapabilityStatus.VERIFIED_ACTIVE,
        risk_level=1,
        dependencies=("dep1", "dep2"),
        evidence_notes="Test note",
    )
    d = cap.to_dict()
    assert d["capability_id"] == "test_cap"
    assert d["status"] == "VERIFIED_ACTIVE"
    assert d["dependencies"] == ["dep1", "dep2"]


def test_is_capability_query():
    registry = CapabilityRegistry()
    assert registry.is_capability_query("Em có những trợ lý nào?") is True
    assert registry.is_capability_query("Bạn làm được gì?") is True
    assert registry.is_capability_query("Hệ thống hoạt động offline thế nào?") is True
    assert registry.is_capability_query("Chức năng của em là gì?") is True
    assert registry.is_capability_query("1 + 1 bằng mấy?") is False


def test_format_for_prompt():
    registry = CapabilityRegistry()
    prompt_text = registry.format_for_prompt()
    assert "[VERIFIED CAPABILITIES & ARCHITECTURE REALITY]" in prompt_text
    assert "Trí Nhớ Dài Hạn" in prompt_text
    assert "Suy Luận AI Cục Bộ" in prompt_text
    assert "VERIFIED_ACTIVE" in prompt_text
    assert "INERT_STAGING" in prompt_text


def test_context_builder_injects_capabilities():
    registry = CapabilityRegistry()
    builder = PromptContextBuilder(capability_registry=registry)

    # Capability query should trigger injection into rendered_context
    ctx = builder.build(
        user_query="Em có những trợ lý nào trong hệ thống?",
    )
    assert "[VERIFIED CAPABILITIES & ARCHITECTURE REALITY]" in ctx.rendered_context
    assert "Trí Nhớ Dài Hạn" in ctx.rendered_context
    assert "capabilities" in ctx.section_stats

    # Non-capability query should NOT inject capability registry section
    ctx2 = builder.build(
        user_query="Hôm nay hãy lập kế hoạch dự toán tài chính",
    )
    assert "[VERIFIED CAPABILITIES & ARCHITECTURE REALITY]" not in ctx2.rendered_context
    assert "capabilities" not in ctx2.section_stats

