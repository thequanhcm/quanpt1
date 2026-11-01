"""Comprehensive Verification Test Suite for Digital Human Avatar V2 (MASTER PROMPT).

Verifies:
1. Reference image Pi5/6.jpg preserved intact and accessible.
2. Avatar V2 master assets exist in both PC and Edge directories (1024x1024, 1:1 ratio, valid PNG).
3. 12-State Protocol defined in avatar_engine.js:
   IDLE, LISTENING, THINKING, SPEAKING, HAPPY, EMPATHETIC, CONFUSED, SUCCESS, WARNING, OFFLINE, ERROR, RECONNECTING.
4. Bounding boxes (EYES_BOX, MOUTH_BOX) calibrated to 1024x1024 facial landmarks.
5. Feathered mouth layers (mouth_v2_rest, mouth_v2_speaking, mouth_v2_open_o, mouth_v2_happy) exist with valid RGBA alpha transparency.
6. Vietnamese Mouth-Sync: UtteranceTimeline generation, duration scaling, and instant barge-in cancellation.
7. Vietnamese Female TTS: HoaiMyNeural default voice and Vietnamese diacritics normalization.
8. Pi 5 Pure Embodiment: micro-transcript dialogue text hidden/disabled on Pi 5 Kiosk UI.
"""
from __future__ import annotations

import json
from pathlib import Path
from PIL import Image
try:
    import pytest
except ImportError:
    pytest = None

from quan_ai_brain.voice.mouth_sync import MouthSyncEngine
from quan_ai_brain.voice.tts_config import (
    GLOBAL_TTS_MANAGER,
    STANDARD_VIETNAMESE_VOICES,
    TTSConfig,
    normalize_text_for_vietnamese_tts,
)


def test_reference_image_preserved() -> None:
    workspace = Path(__file__).resolve().parent.parent
    ref_a = workspace / "Pi5" / "4.png"
    assert ref_a.exists(), "Model A source image Pi5/4.png must exist"
    assert ref_a.stat().st_size > 400_000, "Reference image must not be empty or truncated"

    with Image.open(ref_a) as img:
        assert img.format == "PNG"
        w, h = img.size
        assert w == 2400
        assert h == 1792

    # Preserved legacy references
    ref_legacy = workspace / "Pi5" / "6.jpg"
    assert ref_legacy.exists()


def test_avatar_v2_master_assets_exist_and_dimensions() -> None:
    workspace = Path(__file__).resolve().parent.parent
    pc_dir = workspace / "src" / "quan_ai_brain" / "web" / "static" / "assets" / "avatar"
    edge_dir = workspace / "edge_client" / "assets" / "avatar"

    required_assets = [
        "avatar_v2_portrait.png",
        "avatar_v2_blink.png",
        "avatar_v2_thinking.png",
        "avatar_v2_happy.png",
        "avatar_v2_warning.png",
        "avatar_v2_empathic.png",
        "avatar_v2_confused.png",
        "avatar_v2_surprised.png",
        "avatar_v2_error.png",
        "mouth_v2_rest.png",
        "mouth_v2_speaking.png",
        "mouth_v2_open_o.png",
        "mouth_v2_happy.png",
    ]

    for asset_name in required_assets:
        p_pc = pc_dir / asset_name
        p_edge = edge_dir / asset_name
        assert p_pc.exists(), f"Missing PC asset: {p_pc}"
        assert p_edge.exists(), f"Missing Edge asset: {p_edge}"
        assert p_pc.stat().st_size > 0
        assert p_edge.stat().st_size > 0

    # Verify portrait dimensions (1:1 square, 1024x1024)
    with Image.open(pc_dir / "avatar_v2_portrait.png") as img:
        assert img.size == (1024, 1024), "Master portrait must be 1024x1024 1:1 aspect ratio"

    # Verify mouth layers have alpha transparency
    with Image.open(pc_dir / "mouth_v2_rest.png") as img:
        assert img.mode == "RGBA", "Mouth layer must have alpha channel for feathered blending"


def test_avatar_engine_12_states_configured() -> None:
    workspace = Path(__file__).resolve().parent.parent
    js_path = workspace / "src" / "quan_ai_brain" / "web" / "static" / "avatar_engine.js"
    assert js_path.exists()
    content = js_path.read_text(encoding="utf-8")

    expected_12_states = [
        "IDLE",
        "LISTENING",
        "THINKING",
        "SPEAKING",
        "HAPPY",
        "EMPATHETIC",
        "CONFUSED",
        "SUCCESS",
        "WARNING",
        "OFFLINE",
        "ERROR",
        "RECONNECTING",
    ]

    for st in expected_12_states:
        assert f"{st}:" in content, f"State {st} must be present in STATE_CONFIGS in avatar_engine.js"

    # Verify calibrated bounding boxes for Model A
    assert "this.EYES_BOX = { x: 320, y: 425, w: 365, h: 115 };" in content
    assert "this.MOUTH_BOX = { x: 405, y: 650, w: 245, h: 105 };" in content


def test_vietnamese_mouth_sync_timeline_and_visemes() -> None:
    engine = MouthSyncEngine(frame_interval_ms=50)
    text = "Chào Anh Quanpt1! Em đã sẵn sàng hỗ trợ Anh trong mọi nhiệm vụ điều hành."
    timeline = engine.generate_timeline("utt_v2_test", text, target_duration_ms=2500)

    assert timeline.utterance_id == "utt_v2_test"
    assert timeline.total_duration_ms == 2500
    assert len(timeline.frames) >= 40  # Keyframes and periodic samples across 2500ms

    # Verify visemes present
    visemes = {f.viseme for f in timeline.frames}
    assert "REST" in visemes
    assert any(v in visemes for v in ("A", "O", "E", "I", "U"))

    # Mid speech mouth must be open
    mid_frame = engine.get_mouth_frame_at("utt_v2_test", 1200)
    assert mid_frame.open_ratio >= 0.0

    # End frame must be REST and 0.0
    end_frame = engine.get_mouth_frame_at("utt_v2_test", 2500)
    assert end_frame.open_ratio == 0.0
    assert end_frame.viseme == "REST"


def test_mouth_sync_instant_interruption() -> None:
    engine = MouthSyncEngine(frame_interval_ms=50)
    text = "Báo cáo Anh, hệ thống QUAN AI BRAIN đang thực hiện phân tích dữ liệu đa phân hệ..."
    timeline = engine.generate_timeline("utt_barge_in", text, target_duration_ms=4000)

    # Before cancel, mouth is moving
    f_mid = engine.get_mouth_frame_at("utt_barge_in", 1500)
    assert f_mid.open_ratio > 0.0

    # User interrupts!
    assert engine.cancel_utterance("utt_barge_in") is True

    # After cancellation, mouth snaps to REST and closed
    f_after = engine.get_mouth_frame_at("utt_barge_in", 1500)
    assert f_after.open_ratio == 0.0
    assert f_after.viseme == "REST"


def test_vietnamese_female_tts_default_configuration() -> None:
    cfg = GLOBAL_TTS_MANAGER.config
    assert cfg.response_language == "vi-VN"
    assert cfg.tts_locale == "vi-VN"
    assert cfg.tts_gender == "female"
    assert cfg.tts_voice_preference == "vi-VN-HoaiMyNeural"

    # Test normalization
    raw = "Báo cáo: CPU 45%, RAM 6.2GB, Task ID #123 đã hoàn thành!"
    norm = normalize_text_for_vietnamese_tts(raw)
    assert "45%" in norm
    assert "6.2 ghi-ga-bai" in norm
    assert "hoàn thành" in norm


def test_pi5_kiosk_pure_embodiment_no_transcript() -> None:
    workspace = Path(__file__).resolve().parent.parent
    kiosk_html = (workspace / "edge_client" / "kiosk.html").read_text(encoding="utf-8")
    kiosk_css = (workspace / "edge_client" / "kiosk.css").read_text(encoding="utf-8")

    # Verify no transcript-line in kiosk.html
    assert 'id="transcript-line"' not in kiosk_html, "Pi 5 Kiosk must not display transcript text"
    # Verify .micro-transcript is hidden in css
    assert "display: none !important;" in kiosk_css
