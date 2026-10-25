"""Unit tests for MouthSyncEngine and real-time lip-sync timelines."""
from __future__ import annotations

import pytest

from quan_ai_brain.voice.mouth_sync import MouthSyncEngine


def test_empty_text_timeline():
    engine = MouthSyncEngine(frame_interval_ms=50)
    timeline = engine.generate_timeline("utt_empty", "")
    assert timeline.total_duration_ms == 0
    frame = engine.get_mouth_frame_at("utt_empty", 0)
    assert frame.open_ratio == 0.0
    assert frame.viseme == "REST"


def test_vietnamese_utterance_generation_and_visemes():
    engine = MouthSyncEngine(frame_interval_ms=50)
    text = "Chào Anh Quanpt1, em là Tony!"
    timeline = engine.generate_timeline("utt_greet", text)

    assert timeline.utterance_id == "utt_greet"
    assert timeline.total_duration_ms > 500
    assert len(timeline.frames) > 5

    # Check presence of dominant visemes
    visemes = {f.viseme for f in timeline.frames}
    assert "A" in visemes or "O" in visemes or "REST" in visemes

    # Sample mid-speech
    mid_offset = timeline.total_duration_ms // 3
    mid_frame = engine.get_mouth_frame_at("utt_greet", mid_offset)
    assert 0.0 <= mid_frame.open_ratio <= 1.0


def test_punctuation_pause_produces_closed_mouth():
    engine = MouthSyncEngine(frame_interval_ms=50)
    text = "Dạ. Vâng."
    timeline = engine.generate_timeline("utt_pause", text)

    # There should be frames with open_ratio == 0.0 for natural resting pauses
    closed_frames = [f for f in timeline.frames if f.open_ratio == 0.0]
    assert len(closed_frames) >= 2


def test_target_duration_scaling():
    engine = MouthSyncEngine(frame_interval_ms=50)
    text = "Hệ thống đang hoạt động bình thường."
    timeline = engine.generate_timeline("utt_scaled", text, target_duration_ms=2000)

    assert timeline.total_duration_ms == 2000
    # Last frame at end
    last_frame = engine.get_mouth_frame_at("utt_scaled", 2000)
    assert last_frame.open_ratio == 0.0
    assert last_frame.viseme == "REST"


def test_interruption_cancels_utterance_immediately():
    engine = MouthSyncEngine(frame_interval_ms=50)
    text = "Đây là một câu trả lời rất dài của trợ lý đang nói..."
    timeline = engine.generate_timeline("utt_long", text, target_duration_ms=4000)

    # Sample before cancellation
    f_before = engine.get_mouth_frame_at("utt_long", 1000)
    assert f_before.open_ratio > 0.0

    # User interrupts!
    assert engine.cancel_utterance("utt_long") is True

    # Immediately after cancellation, mouth MUST snap shut to 0.0 and REST
    f_after = engine.get_mouth_frame_at("utt_long", 1000)
    assert f_after.open_ratio == 0.0
    assert f_after.viseme == "REST"
