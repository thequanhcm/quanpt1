"""Unit tests for Wake Word Configuration and Voice State Machine."""
from __future__ import annotations

import pytest

from quan_ai_brain.voice import (
    DEFAULT_WAKE_WORDS,
    VoiceState,
    VoiceStateMachine,
    WakeWordConfig,
    normalize_text,
)


def test_default_wake_words_loaded():
    cfg = WakeWordConfig()
    assert len(cfg.items) == 10
    phrases = [w.phrase for w in cfg.items.values()]
    assert "Hi TONY" in phrases
    assert "Tony ơi" in phrases
    assert "Chào trợ lý" in phrases
    assert "Hello assistant" in phrases
    assert "QUAN AI" in phrases
    assert "Quan AI Brain" in phrases


def test_normalization():
    assert normalize_text("  Hi,   TONY!  ") == "hi tony"
    assert normalize_text("Chào Trợ Lý...") == "chào trợ lý"
    assert normalize_text("QUAN   AI: Brain?") == "quan ai brain"
    assert normalize_text("") == ""


def test_exact_matches():
    cfg = WakeWordConfig()
    m1 = cfg.match("Hi TONY")
    assert m1.matched is True
    assert m1.keyword == "Hi TONY"
    assert m1.extracted_payload == ""
    assert m1.is_control_command is False

    m2 = cfg.match("Tony ơi")
    assert m2.matched is True
    assert m2.keyword == "Tony ơi"

    m3 = cfg.match("Chào trợ lý")
    assert m3.matched is True
    assert m3.keyword == "Chào trợ lý"

    m4 = cfg.match("Hello assistant")
    assert m4.matched is True
    assert m4.keyword == "Hello assistant"


def test_payload_extraction():
    cfg = WakeWordConfig()
    res = cfg.match("Hi TONY hãy lập kế hoạch kiểm tra pin")
    assert res.matched is True
    assert res.keyword == "Hi TONY"
    assert res.extracted_payload == "hãy lập kế hoạch kiểm tra pin"
    assert res.confidence >= 0.90

    res2 = cfg.match("Chào trợ lý, hôm nay em làm được gì?")
    assert res2.matched is True
    assert res2.keyword == "Chào trợ lý"
    assert res2.extracted_payload == "hôm nay em làm được gì"


def test_near_miss_rejection():
    cfg = WakeWordConfig()
    # Just "Tony" without "Hi" or "Hey" or "ơi"
    assert cfg.match("Tony").matched is False
    assert cfg.match("Hôm nay trời đẹp quá").matched is False
    assert cfg.match("Ai đó ở ngoài kia").matched is False
    assert cfg.match("Xin chào các bạn").matched is False


def test_disabled_keyword():
    cfg = WakeWordConfig()
    assert cfg.match("QUAN AI").matched is True

    # Disable "ww_quan_ai"
    cfg.update_item("ww_quan_ai", enabled=False)
    assert cfg.match("QUAN AI").matched is False


def test_control_commands():
    cfg = WakeWordConfig()
    c1 = cfg.match("dừng đọc")
    assert c1.matched is True
    assert c1.is_control_command is True
    assert c1.control_action == "STOP_SPEAKING"

    c2 = cfg.match("ngủ đi")
    assert c2.matched is True
    assert c2.is_control_command is True
    assert c2.control_action == "SLEEP"

    c3 = cfg.match("dừng nghe")
    assert c3.matched is True
    assert c3.is_control_command is True
    assert c3.control_action == "STOP_LISTENING"

    c4 = cfg.match("tắt trợ lý")
    assert c4.matched is True
    assert c4.is_control_command is True
    assert c4.control_action == "DISABLE"


def test_state_machine_valid_transitions():
    sm = VoiceStateMachine(VoiceState.DISABLED)
    assert sm.transition_to(VoiceState.STANDBY, "User enabled wake word") is True
    assert sm.transition_to(VoiceState.WAKE_DETECTED, "Spotted 'Hi TONY'") is True
    assert sm.transition_to(VoiceState.LISTENING, "Mic recording command") is True
    assert sm.transition_to(VoiceState.TRANSCRIBING, "End of speech") is True
    assert sm.transition_to(VoiceState.THINKING, "Calling local Ollama") is True
    assert sm.transition_to(VoiceState.SPEAKING, "TTS reading answer") is True
    assert sm.transition_to(VoiceState.STANDBY, "Follow-up silence timeout") is True
    assert len(sm.history) == 7


def test_state_machine_invalid_transitions():
    sm = VoiceStateMachine(VoiceState.DISABLED)
    # Cannot jump from DISABLED to SPEAKING
    assert sm.transition_to(VoiceState.SPEAKING) is False
    assert sm.current_state == VoiceState.DISABLED

    # Cannot jump from STANDBY to TRANSCRIBING
    sm.transition_to(VoiceState.STANDBY)
    assert sm.transition_to(VoiceState.TRANSCRIBING) is False
    assert sm.current_state == VoiceState.STANDBY
