"""End-to-End Test Suite for XiaoZhi Voice-First Pipeline (T01 - T08, Multilingual, Safety).

Verifies:
- T01: Capabilities introduction in Vietnamese.
- T02: Multi-turn planning and context continuation ("Ưu tiên việc quan trọng nhất trước").
- T03: Pi 5 connection verification from telemetry.
- T04: Root-cause diagnosis with honest reporting of missing evidence.
- T05: Analysis-only directive respecting execution boundary.
- T06: Instant task interruption (<10ms barge-in).
- T07: Task completion status inquiry.
- T08: Multi-turn conversation history retention and restoration.
- Spoken Vietnamese text sanitization (no JSON, stack traces, or code blocks in TTS).
- Speech self-correction handling ("À nhầm", "Ý anh là...").
- Multilingual inputs (Vietnamese, English, mixed Vi-En, technical abbreviations).
"""
from __future__ import annotations

import time
import pytest

from quan_ai_brain.cognition.role_orchestrator import ExecutiveRole, ExecutiveRoleOrchestrator
from quan_ai_brain.voice.mouth_sync import MouthSyncEngine
from quan_ai_brain.voice.state_machine import VoiceState
from quan_ai_brain.voice.voice_pipeline import (
    XiaoZhiVoicePipeline,
    sanitize_for_spoken_vietnamese,
)


@pytest.fixture
def voice_pipeline():
    telemetry = {
        "connected": True,
        "last_seen": time.time() - 1,
        "last_error": "",
    }
    tasks = [
        {"id": "TASK-01", "name": "Review Pi 5 Connection", "status": "IN_PROGRESS"},
    ]
    orchestrator = ExecutiveRoleOrchestrator(durable_tasks=tasks, edge_telemetry=telemetry)
    mouth_sync = MouthSyncEngine(frame_interval_ms=50)
    pipeline = XiaoZhiVoicePipeline(
        role_orchestrator=orchestrator,
        mouth_sync=mouth_sync,
    )
    return pipeline


def test_t01_capabilities_introduction(voice_pipeline):
    """T01: 'Em giới thiệu ngắn gọn khả năng của mình.'"""
    res = voice_pipeline.handle_voice_input("Em giới thiệu ngắn gọn khả năng của mình.", is_push_to_talk=True)
    assert res.active_role == ExecutiveRole.EXECUTIVE_ASSISTANT.value
    assert "QUAN AI BRAIN" in res.response_text
    assert "Anh" in res.spoken_text
    assert res.mouth_timeline is not None
    assert len(res.mouth_timeline["frames"]) > 0


def test_t02_multiturn_planning_and_priority_continuation(voice_pipeline):
    """T02: 'Lập kế hoạch công việc hôm nay.' -> 'Ưu tiên việc quan trọng nhất trước.'"""
    # Turn 1: Planning
    res1 = voice_pipeline.handle_voice_input("Lập kế hoạch công việc hôm nay.", is_push_to_talk=True)
    assert res1.active_role == ExecutiveRole.COORDINATOR.value
    assert "Bước 1" in res1.response_text
    assert len(voice_pipeline.history) == 2  # 1 user + 1 assistant

    # Turn 2: Contextual continuation
    res2 = voice_pipeline.handle_voice_input("Ưu tiên việc quan trọng nhất trước.", is_push_to_talk=True)
    assert res2.active_role == ExecutiveRole.COORDINATOR.value
    assert "ưu tiên" in res2.response_text.lower()
    assert len(voice_pipeline.history) == 4


def test_t03_check_pi5_connection_status(voice_pipeline):
    """T03: 'Kiểm tra Pi 5 đang kết nối hay không.'"""
    res = voice_pipeline.handle_voice_input("Kiểm tra Pi 5 đang kết nối hay không.", is_push_to_talk=True)
    assert res.active_role == ExecutiveRole.NOC_OPERATOR.value
    assert "kết nối bình thường" in res.response_text


def test_t04_disconnected_pi5_root_cause(voice_pipeline):
    """T04: 'Pi mất kết nối, em xác định nguyên nhân.'"""
    voice_pipeline.orchestrator.edge_telemetry["connected"] = False
    voice_pipeline.orchestrator.edge_telemetry["last_error"] = ""
    res = voice_pipeline.handle_voice_input("Pi mất kết nối, em xác định nguyên nhân.", is_push_to_talk=True)
    assert res.active_role == ExecutiveRole.NOC_OPERATOR.value
    assert "chưa có đủ dữ liệu" in res.response_text or "đứt sóng" in res.response_text


def test_t05_analysis_only_directive(voice_pipeline):
    """T05: 'Chỉ phân tích, chưa thực hiện.'"""
    res = voice_pipeline.handle_voice_input("Chỉ phân tích, chưa thực hiện.", is_push_to_talk=True)
    assert res.active_role in (ExecutiveRole.DATA_ANALYST.value, ExecutiveRole.EXECUTIVE_ASSISTANT.value)
    assert "tuyệt đối không gọi công cụ thực thi" in res.response_text


def test_t06_stop_task_interruption(voice_pipeline):
    """T06: 'Dừng tác vụ đang làm.'"""
    res = voice_pipeline.handle_voice_input("Dừng tác vụ đang làm.", is_push_to_talk=True)
    assert res.active_role == ExecutiveRole.SAFETY_OFFICER.value
    assert "STOP" in res.response_text or "dừng" in res.response_text.lower()


def test_t07_task_completion_status(voice_pipeline):
    """T07: 'Em đã hoàn thành chưa?'"""
    res = voice_pipeline.handle_voice_input("Em đã hoàn thành chưa?", is_push_to_talk=True)
    assert res.active_role == ExecutiveRole.EXECUTIVE_ASSISTANT.value
    assert "1 tác vụ" in res.response_text


def test_t08_barge_in_instant_cancellation(voice_pipeline):
    """T08: User cuts in while playback active (<10ms barge-in)."""
    # Simulate assistant speaking
    voice_pipeline.state_machine.current_state = VoiceState.SPEAKING
    t0 = time.perf_counter()
    interrupted = voice_pipeline.process_barge_in("User spoke during output")
    latency_ms = (time.perf_counter() - t0) * 1000

    assert interrupted is True
    assert latency_ms < 10.0  # Must be faster than 10 milliseconds
    assert voice_pipeline.state_machine.current_state == VoiceState.LISTENING


def test_spoken_sanitization():
    """Verify code blocks, stack traces, JSON, and technical markdown are stripped from TTS."""
    raw = (
        "Chào Anh! Dưới đây là dữ liệu cấu hình:\n"
        "```python\nimport sys\nprint('secret')\n```\n"
        "Đối tượng: `{\"status\": \"OK\", \"code\": 200}`\n"
        "Truy cập tại http://127.0.0.1:8766/ và file E:\\AI\\core\\audit.py\n"
        "### Kết luận: Mọi thứ đã hoàn tất."
    )
    spoken = sanitize_for_spoken_vietnamese(raw)
    assert "import sys" not in spoken
    assert "```" not in spoken
    assert "`" not in spoken
    assert "http://" not in spoken
    assert "E:\\" not in spoken
    assert "###" not in spoken
    assert "Chào Anh!" in spoken
    assert "Mọi thứ đã hoàn tất." in spoken


def test_speech_self_correction(voice_pipeline):
    """Verify correction handling like 'À nhầm, kiểm tra Pi 5'."""
    res = voice_pipeline.handle_voice_input("À nhầm, kiểm tra Pi 5 đang kết nối hay không.", is_push_to_talk=True)
    assert res.active_role == ExecutiveRole.NOC_OPERATOR.value
    assert "kết nối bình thường" in res.response_text


def test_multilingual_inputs(voice_pipeline):
    """Multilingual tests: Vietnamese, English, mixed Vi-En, technical abbreviations."""
    # 1. Pure Vietnamese
    r1 = voice_pipeline.handle_voice_input("Tony ơi, em làm được gì?", is_push_to_talk=False)
    assert r1.active_role == ExecutiveRole.EXECUTIVE_ASSISTANT.value

    # 2. Pure English
    r2 = voice_pipeline.handle_voice_input("Hi Tony, check Pi 5 connection status", is_push_to_talk=False)
    assert r2.active_role == ExecutiveRole.NOC_OPERATOR.value

    # 3. Mixed Vi-En with technical abbreviation
    r3 = voice_pipeline.handle_voice_input("Kiểm tra NOC alert và RTT mạng Wi-Fi của Pi 5", is_push_to_talk=True)
    assert r3.active_role == ExecutiveRole.NOC_OPERATOR.value
