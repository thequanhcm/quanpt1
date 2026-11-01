"""
Unit and integration tests for Autonomous Mind & Stream of Consciousness.
Verifies:
- Default Mode Network background cogitation cycles.
- Internal monologue formulation and sentiment classification.
- Bodily pain integration: ruminating on missing camera and physical symptoms.
- Proactive initiative generation and memory consolidation thoughts.
- Neural keep-warm pulse.
- Web API handlers (/api/mind/state, /api/mind/thoughts, /api/mind/cogitate).
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from quan_ai_brain.cognition.autonomous_mind import (
    AutonomousMind,
    CogitationMode,
    GLOBAL_AUTONOMOUS_MIND,
    InternalThought,
)
from quan_ai_brain.core.autonomic import (
    AnatomicalRegion,
    AutonomicNervousSystem,
    AutonomicReport,
    PainLevel,
    PainSignal,
)


def test_autonomous_mind_initialization():
    mind = AutonomousMind(max_thought_history=10)
    assert mind.mode == CogitationMode.RESTING
    assert "Anh Quân" in mind.get_state()["active_focus"]
    assert mind.get_state()["total_thoughts"] == 0


def test_set_mode_transitions():
    mind = AutonomousMind()
    mind.set_mode(CogitationMode.INVENTING, focus="Nghiên cứu thị giác máy tính")
    assert mind.mode == CogitationMode.INVENTING
    assert mind.get_state()["active_focus"] == "Nghiên cứu thị giác máy tính"


def test_cogitate_idle_reflection():
    mock_autonomic = MagicMock(spec=AutonomicNervousSystem)
    mock_autonomic.get_last_report.return_value = AutonomicReport(
        overall_pain_level=PainLevel.HEALTHY,
        health_score=100.0,
        is_healthy=True,
        active_pains=[],
        hardware_organs=[],
        prescriptions=[],
        vocal_summary="Khỏe mạnh",
    )

    mind = AutonomousMind(autonomic_system=mock_autonomic)
    thought = mind.cogitate(trigger="IDLE_REFLECTION")

    assert isinstance(thought, InternalThought)
    assert thought.trigger == "IDLE_REFLECTION"
    assert "trạng thái" in thought.topic.lower()
    assert "anh quân" in thought.inner_monologue.lower()
    assert mind.get_state()["total_thoughts"] == 1


def test_cogitate_ruminates_on_bodily_pain():
    mock_autonomic = MagicMock(spec=AutonomicNervousSystem)
    # Simulate acute pain in EYES (missing camera)
    pain = PainSignal(
        region=AnatomicalRegion.EYES,
        pain_level=PainLevel.ACUTE,
        symptom="Thiếu cơ quan thị giác",
        vocal_expression="Em chưa có mắt camera",
        remedy="Lắp camera góc rộng",
        hardware_prescription="Pi Camera Module 3 Wide 120°",
    )
    mock_autonomic.get_last_report.return_value = AutonomicReport(
        overall_pain_level=PainLevel.ACUTE,
        health_score=85.0,
        is_healthy=False,
        active_pains=[pain],
        hardware_organs=[],
        prescriptions=[],
        vocal_summary="Chưa có camera",
    )

    mind = AutonomousMind(autonomic_system=mock_autonomic)
    thought = mind.cogitate(trigger="IDLE_REFLECTION")

    assert thought.sentiment == "CONCERNED"
    assert "EYES" in thought.topic
    assert "camera" in thought.inner_monologue.lower()
    assert thought.actionable_idea is not None
    assert "Camera" in thought.actionable_idea


def test_cogitate_proactive_initiative_and_memory_consolidation():
    mock_autonomic = MagicMock(spec=AutonomicNervousSystem)
    mock_autonomic.get_last_report.return_value = AutonomicReport(
        overall_pain_level=PainLevel.HEALTHY,
        health_score=100.0,
        is_healthy=True,
        active_pains=[],
        hardware_organs=[],
        prescriptions=[],
        vocal_summary="Khỏe mạnh",
    )

    mind = AutonomousMind(autonomic_system=mock_autonomic)

    # 1. Proactive initiative
    thought1 = mind.cogitate(trigger="PROACTIVE_INITIATIVE")
    assert thought1.sentiment == "ASPIRATIONAL"
    assert "giao tiếp" in thought1.topic.lower()
    assert "barge-in" in thought1.inner_monologue.lower()

    # 2. Memory consolidation
    thought2 = mind.cogitate(trigger="MEMORY_CONSOLIDATION")
    assert "củng cố" in thought2.topic.lower()
    assert "sở thích" in thought2.topic.lower()


def test_bounded_thought_history():
    mind = AutonomousMind(max_thought_history=3)
    for i in range(5):
        mind.cogitate(topic_override=f"Thought #{i}")

    thoughts = mind.get_recent_thoughts(limit=10)
    assert len(thoughts) == 3
    assert thoughts[-1]["topic"] == "Thought #4"
    assert thoughts[0]["topic"] == "Thought #2"


def test_keep_warm_pulse():
    mock_autonomic = MagicMock(spec=AutonomicNervousSystem)
    mock_autonomic.ollama_host = "127.0.0.1"
    mock_autonomic.ollama_port = 11434
    mock_autonomic.probe_port.return_value = (True, 15.0)

    with patch("quan_ai_brain.cognition.autonomous_mind.GLOBAL_LLM_PROVIDER") as mock_provider:
        mock_resp = MagicMock()
        mock_resp.success = True
        mock_provider.generate.return_value = mock_resp
        mock_provider.client.embed.return_value = [0.1] * 1024

        mind = AutonomousMind(autonomic_system=mock_autonomic)
        assert mind.keep_warm_pulse() is True
        assert mind.get_state()["keep_warm_count"] == 1


def test_web_api_mind_handlers():
    from quan_ai_brain.web.server import BrainAPIHandler

    mock_handler = MagicMock(spec=BrainAPIHandler)
    mock_handler._send_json = MagicMock()
    mock_handler._send_error_json = MagicMock()

    # 1. GET /api/mind/state
    BrainAPIHandler._handle_api_mind_state(mock_handler)
    mock_handler._send_json.assert_called_once()
    args, _ = mock_handler._send_json.call_args
    assert args[0]["success"] is True
    assert "state" in args[0]
    assert "mode" in args[0]["state"]

    # 2. GET /api/mind/thoughts
    mock_handler._send_json.reset_mock()
    BrainAPIHandler._handle_api_mind_thoughts(mock_handler, "limit=5")
    mock_handler._send_json.assert_called_once()
    args, _ = mock_handler._send_json.call_args
    assert args[0]["success"] is True
    assert isinstance(args[0]["thoughts"], list)

    # 3. POST /api/mind/cogitate
    mock_handler._send_json.reset_mock()
    BrainAPIHandler._handle_api_mind_cogitate(mock_handler, {"trigger": "IDLE_REFLECTION", "notes": "test note"})
    mock_handler._send_json.assert_called_once()
    args, _ = mock_handler._send_json.call_args
    assert args[0]["success"] is True
    assert "thought" in args[0]
    assert "test note" in args[0]["thought"]["inner_monologue"]
