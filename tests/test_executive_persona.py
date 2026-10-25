"""Tests for ExecutivePersona and ExecutiveDirective in QUAN AI BRAIN."""
from __future__ import annotations

import pytest

from quan_ai_brain.cognition.context_builder import PromptContextBuilder
from quan_ai_brain.cognition.executive_persona import (
    DEFAULT_DIRECTIVES,
    ExecutiveDirective,
    ExecutivePersona,
)


def test_default_executive_persona():
    persona = ExecutivePersona()
    assert persona.name == "QUAN AI BRAIN"
    assert "Bản sao" in persona.title or "Nhân Sự Số" in persona.title
    assert "Quanpt1" in persona.owner_name
    assert len(persona.directives) >= 5

    data = persona.to_dict()
    assert data["name"] == "QUAN AI BRAIN"
    assert data["operational_mode"] == "EXECUTIVE_REPLICA"
    assert len(data["directives"]) >= 5


def test_persona_format_for_prompt():
    persona = ExecutivePersona()
    prompt = persona.format_for_prompt()
    assert "DIGITAL EXECUTIVE PERSONA" in prompt
    assert "QUANPT1" in prompt
    assert "DIR-01" in prompt
    assert "DIR-02" in prompt
    assert "DIR-03" in prompt


def test_context_builder_with_persona():
    persona = ExecutivePersona(owner_name="Quanpt1")
    builder = PromptContextBuilder(persona=persona)
    ctx = builder.build(user_query="Báo cáo tiến độ hôm nay thế nào em?")

    assert "DIGITAL EXECUTIVE PERSONA" in ctx.rendered_context
    assert "persona" in ctx.section_stats
    assert ctx.section_stats["persona"] > 0
