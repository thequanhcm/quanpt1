"""
Unit and integration tests for Autonomic Nervous System & Pain-Sensing Engine.
Verifies:
- Organ audit (Ears, Voice, Eyes, Skin, Body, Brain, Circulation).
- Automatic detection of missing sensory hardware (Camera, mmWave radar).
- Nociceptor pain detection and scoring.
- Natural Vietnamese vocal reflection ("ốm đau thì phải kêu").
- Web API handler endpoints (/api/autonomic/status, /api/autonomic/selftest, /api/autonomic/vocalize).
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from quan_ai_brain.core.autonomic import (
    AnatomicalRegion,
    AutonomicNervousSystem,
    AutonomicReport,
    GLOBAL_AUTONOMIC_SYSTEM,
    HardwareOrganAudit,
    HardwareStatus,
    PainLevel,
    PainSignal,
)


def test_autonomic_system_initialization(tmp_path):
    ans = AutonomicNervousSystem(
        ollama_host="127.0.0.1",
        ollama_port=11434,
        edge_ip="192.168.1.99",
        edge_port=8768,
        data_dir=str(tmp_path),
    )
    assert ans.ollama_host == "127.0.0.1"
    assert ans.ollama_port == 11434
    assert ans.edge_ip == "192.168.1.99"
    assert ans.data_dir == str(tmp_path)


def test_hardware_organs_audit_identifies_missing_camera_and_radar():
    ans = AutonomicNervousSystem()
    organs = ans.audit_hardware_organs()
    assert len(organs) >= 4

    names = {o.organ_name: o for o in organs}

    # Verify Eyes (Camera) is audited as missing and critical
    eyes_organ = [o for o in organs if o.region == AnatomicalRegion.EYES][0]
    assert eyes_organ.status == HardwareStatus.MISSING_RECOMMENDED
    assert eyes_organ.priority == "CRITICAL"
    assert "Camera" in eyes_organ.recommended_upgrade

    # Verify Skin (mmWave radar) is audited as missing and high priority
    presence_organ = [o for o in organs if "Radar" in o.organ_name][0]
    assert presence_organ.status == HardwareStatus.MISSING_RECOMMENDED
    assert presence_organ.priority == "HIGH"
    assert "LD2410" in presence_organ.recommended_upgrade


def test_brain_health_detects_unreachable_ollama():
    ans = AutonomicNervousSystem(ollama_host="127.0.0.1", ollama_port=59999)
    # Probe a definitely dead port
    pains = ans.check_brain_health()
    assert len(pains) >= 1
    critical_pains = [p for p in pains if p.pain_level == PainLevel.CRITICAL]
    assert len(critical_pains) == 1
    assert critical_pains[0].region == AnatomicalRegion.BRAIN
    assert "Ollama" in critical_pains[0].symptom
    assert "não bộ" in critical_pains[0].vocal_expression.lower()


def test_circulation_health_detects_unreachable_edge_pi5():
    ans = AutonomicNervousSystem(edge_ip="127.0.0.1", edge_port=59998)
    pains = ans.check_circulation_health()
    assert len(pains) == 1
    assert pains[0].region == AnatomicalRegion.CIRCULATION
    assert pains[0].pain_level == PainLevel.ACUTE
    assert "Raspberry Pi 5" in pains[0].symptom
    assert "thể nghiệm" in pains[0].vocal_expression.lower()


def test_run_self_test_aggregates_pains_and_prescriptions(tmp_path):
    ans = AutonomicNervousSystem(
        ollama_host="127.0.0.1",
        ollama_port=11434,
        edge_ip="127.0.0.1",
        edge_port=59998,
        data_dir=str(tmp_path),
    )
    report = ans.run_self_test()

    assert isinstance(report, AutonomicReport)
    assert report.health_score <= 100.0
    assert len(report.active_pains) > 0
    assert len(report.prescriptions) > 0
    assert len(report.vocal_summary) > 10

    # Ensure to_dict works cleanly
    d = report.to_dict()
    assert "overall_pain_level" in d
    assert "health_score" in d
    assert "prescriptions" in d
    assert "vocal_summary" in d
    assert isinstance(d["active_pains"], list)


def test_vocal_summary_expresses_pain_honestly():
    ans = AutonomicNervousSystem()
    pain1 = PainSignal(
        region=AnatomicalRegion.EYES,
        pain_level=PainLevel.ACUTE,
        symptom="Thiếu Camera",
        vocal_expression="Anh Quân ơi, em chưa có mắt camera nên chưa nhìn thấy anh!",
        remedy="Lắp thêm camera",
    )
    summary = ans._formulate_vocal_summary([pain1], score=75.0, pain_level=PainLevel.ACUTE)
    assert "Anh Quân ơi" in summary
    assert "chưa có mắt camera" in summary
    assert "75/100" in summary


def test_vocal_summary_healthy_expression():
    ans = AutonomicNervousSystem()
    summary = ans._formulate_vocal_summary([], score=100.0, pain_level=PainLevel.HEALTHY)
    assert "khỏe mạnh tuyệt đối" in summary
    assert "100 điểm" in summary


def test_web_api_autonomic_handler_mock():
    from quan_ai_brain.web.server import BrainAPIHandler

    mock_handler = MagicMock(spec=BrainAPIHandler)
    mock_handler._send_json = MagicMock()
    mock_handler._send_error_json = MagicMock()

    # Call unbound methods with mock instance
    BrainAPIHandler._handle_api_autonomic_status(mock_handler)
    mock_handler._send_json.assert_called_once()
    args, kwargs = mock_handler._send_json.call_args
    assert args[0]["success"] is True
    assert "report" in args[0]
    assert "overall_pain_level" in args[0]["report"]

    # Call selftest
    mock_handler._send_json.reset_mock()
    BrainAPIHandler._handle_api_autonomic_selftest(mock_handler, {"vocalize": False})
    mock_handler._send_json.assert_called_once()
    args, kwargs = mock_handler._send_json.call_args
    assert args[0]["success"] is True

    # Call vocalize
    mock_handler._send_json.reset_mock()
    BrainAPIHandler._handle_api_autonomic_vocalize(mock_handler, {})
    mock_handler._send_json.assert_called_once()
    args, kwargs = mock_handler._send_json.call_args
    assert args[0]["success"] is True
    assert "vocal_text" in args[0]
