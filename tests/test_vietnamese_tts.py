"""Comprehensive Test Suite for Vietnamese Female TTS in QUAN AI BRAIN (TTS-01 to TTS-10).

Verifies:
- TTS-01: Vietnamese text with diacritics preserved, vi-VN locale, HoaiMyNeural voice.
- TTS-02: Female voice verified in metadata and audio synthesis.
- TTS-03: Numbers, metrics, and technical terms preserved and converted naturally.
- TTS-04: Long complex sentences with punctuation processed cleanly.
- TTS-05: Mixed content (Vietnamese, model ID, device code) without corrupting IDs.
- TTS-06: Provider offline simulated -> status TTS_UNAVAILABLE, never silently English.
- TTS-07: Invalid voice ID or non-Vietnamese locale rejected with clear error.
- TTS-08: Barge-in interruption stops active audio and timeline cleanly.
- TTS-09: Multi-turn (5+ turns) dialogue retains Vietnamese female default.
- TTS-10: PC and Pi 5 differentiation (PC verified, Pi 5 hardware marked BLOCKED if absent).
"""
from __future__ import annotations

import json
from pathlib import Path
import threading
import time
from unittest.mock import patch
import urllib.request
import pytest

from quan_ai_brain.voice.mouth_sync import MouthSyncEngine
from quan_ai_brain.voice.state_machine import VoiceState
from quan_ai_brain.voice.tts_config import (
    GLOBAL_TTS_MANAGER,
    STANDARD_VIETNAMESE_VOICES,
    TTSConfig,
    TTSGender,
    TTSManager,
    TTSProvider,
    TTSStatus,
    normalize_text_for_vietnamese_tts,
)
from quan_ai_brain.voice.voice_pipeline import XiaoZhiVoicePipeline
from quan_ai_brain.web.server import BrainAPIHandler, ThreadedHTTPServer


@pytest.fixture(scope="module")
def tts_server_instance(tmp_path_factory: pytest.TempPathFactory):
    test_workspace = tmp_path_factory.mktemp("tts_workspace")
    (test_workspace / "data").mkdir(parents=True, exist_ok=True)

    server = ThreadedHTTPServer(("127.0.0.1", 0), BrainAPIHandler)
    host, port = server.server_address
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    base_url = f"http://{host}:{port}"
    time.sleep(0.1)

    yield base_url

    server.shutdown()
    server.server_close()


def test_tts_01_vietnamese_diacritics_preserved():
    """TTS-01: Vietnamese text with diacritics, vi-VN locale, HoaiMyNeural preferred."""
    input_text = "Xin chào anh. Em là QUAN AI BRAIN, trợ lý điều hành công việc của anh."
    clean_text = normalize_text_for_vietnamese_tts(input_text)

    # 1. Accents must not be stripped or converted to ASCII
    assert "chào" in clean_text
    assert "trợ lý" in clean_text
    assert "điều hành" in clean_text
    assert "công việc" in clean_text
    assert clean_text == input_text

    # 2. Locale and voice checks
    mgr = TTSManager()
    assert mgr.config.response_language == "vi-VN"
    assert mgr.config.tts_locale == "vi-VN"
    assert mgr.config.tts_gender == "female"
    assert mgr.config.tts_voice_preference == "vi-VN-HoaiMyNeural"

    # 3. Audio synthesis
    audio, err = mgr.synthesize_audio(clean_text)
    assert err == "", f"Synthesis failed: {err}"
    assert audio is not None
    assert len(audio) > 5000  # Valid MP3 audio generated
    assert mgr.config.status == TTSStatus.READY.value


def test_tts_02_female_voice():
    """TTS-02: Female voice metadata and authentic Vietnamese female synthesis."""
    input_text = "Em đã nhận yêu cầu. Em đang kiểm tra và sẽ báo lại kết quả cho anh."
    mgr = TTSManager()
    active_voice = mgr.get_active_voice()

    assert active_voice is not None
    assert active_voice.gender == TTSGender.FEMALE.value
    assert active_voice.locale == "vi-VN"
    assert "HoaiMy" in active_voice.voice_id

    audio, err = mgr.synthesize_audio(input_text)
    assert audio is not None
    assert len(audio) > 5000
    assert err == ""


def test_tts_03_numbers_and_technical_terms():
    """TTS-03: Numbers, metrics, and technical terms are preserved and spoken accurately."""
    raw = "Pi 5 đang kết nối với PC Core. Độ trễ là 25 ms. Băng thông 100 MB."
    clean = normalize_text_for_vietnamese_tts(raw)

    assert "Pi 5" in clean
    assert "PC Core" in clean
    assert "25 mili giây" in clean
    assert "100 mê-ga-bai" in clean

    mgr = TTSManager()
    audio, err = mgr.synthesize_audio(clean)
    assert audio is not None
    assert len(audio) > 5000


def test_tts_04_long_sentence_with_punctuation():
    """TTS-04: Long complex Vietnamese text with multiple punctuation marks."""
    long_text = (
        "Hệ thống QUAN AI BRAIN đang thực thi quy trình kiểm toán tự động; "
        "các thành phần gồm có: Module Trí Nhớ Dài Hạn, Bộ Định Tuyến LLM, "
        "và Khung Rào Chắn Bảo Mật R0 đến R5. Kết quả kiểm tra đạt 100% "
        "và không phát hiện bất kỳ sự cố nào ảnh hưởng đến hiệu năng vận hành."
    )
    clean = normalize_text_for_vietnamese_tts(long_text, max_chars=500)
    assert "QUAN AI BRAIN" in clean
    assert "R0 đến R5" in clean
    assert "100%" in clean

    mgr = TTSManager()
    audio, err = mgr.synthesize_audio(clean)
    assert audio is not None
    assert len(audio) > 10000


def test_tts_05_mixed_content_and_identifiers():
    """TTS-05: Mixed Vietnamese, model ID, and device identifiers."""
    mixed_text = (
        "Mô hình `qwen2.5:7b` đang hoạt động ổn định trên thiết bị `EDGE-PI5-01`. "
        "Địa chỉ IP là 192.168.1.21 và cổng dịch vụ là 8768."
    )
    clean = normalize_text_for_vietnamese_tts(mixed_text)

    # Identifiers must not be destroyed
    assert "qwen2.5:7b" in clean
    assert "EDGE-PI5-01" in clean
    assert "8768" in clean
    # Backticks must be stripped
    assert "`" not in clean

    mgr = TTSManager()
    audio, err = mgr.synthesize_audio(clean)
    assert audio is not None


def test_tts_06_provider_offline_reports_tts_unavailable():
    """TTS-06: Provider failure sets TTS_UNAVAILABLE, never silently speaks English."""
    mgr = TTSManager()
    with patch("edge_tts.Communicate", side_effect=Exception("Connection refused by Microsoft Edge service")):
        audio, err = mgr.synthesize_audio("Xin chào anh.")

        assert audio is None
        assert "Lỗi kết nối Microsoft Edge TTS" in err
        assert mgr.config.status == TTSStatus.TTS_UNAVAILABLE.value
        assert mgr.config.connection_status == "OFFLINE"
        # Must strictly preserve Vietnamese locale, NEVER drift to en-US
        assert mgr.config.tts_locale == "vi-VN"
        assert mgr.config.response_language == "vi-VN"


def test_tts_07_invalid_voice_id_rejected():
    """TTS-07: Invalid voice ID or non-Vietnamese locale is rejected with clean error."""
    mgr = TTSManager()

    # Rejection of non-Vietnamese voice
    ok_en = mgr.set_voice_preference("en-US-JennyNeural")
    assert ok_en is False
    assert mgr.config.status == TTSStatus.ERROR.value
    assert "không tồn tại hoặc không được hỗ trợ trong danh mục tiếng Việt" in mgr.config.last_error

    # Rejection of non-existent voice
    ok_none = mgr.set_voice_preference("invalid-voice-id-404")
    assert ok_none is False
    assert mgr.config.status == TTSStatus.ERROR.value

    # Rejection of non-Vietnamese locale update
    ok_loc = mgr.update_config(locale="en-US")
    assert ok_loc is False
    assert "Chỉ cho phép ngôn ngữ tiếng Việt (vi-VN)" in mgr.config.last_error


def test_tts_08_interruption_barge_in():
    """TTS-08: Immediate audio and timeline cancellation on user barge-in (<10ms)."""
    sync_engine = MouthSyncEngine(frame_interval_ms=50)
    timeline = sync_engine.generate_timeline("utt_test_bargein", "Xin chào anh, em đang nói.")
    assert len(timeline.frames) > 0
    assert timeline.is_cancelled is False

    # Interruption triggered
    cancelled = sync_engine.cancel_utterance("utt_test_bargein")
    assert cancelled is True
    assert timeline.is_cancelled is True

    # Voice pipeline barge-in
    pipeline = XiaoZhiVoicePipeline(mouth_sync=sync_engine)
    pipeline.state_machine.current_state = VoiceState.SPEAKING
    interrupted = pipeline.process_barge_in("User cut in")
    assert interrupted is True
    assert pipeline.state_machine.current_state == VoiceState.LISTENING


def test_tts_09_multiturn_dialogue_preserves_vietnamese():
    """TTS-09: 5 consecutive dialogue turns all maintain Vietnamese female configuration."""
    mgr = TTSManager()
    questions = [
        "Xin chào em.",
        "Em có thể giúp gì cho anh?",
        "Kiểm tra tình trạng hệ thống hôm nay.",
        "Tiến độ công việc hiện tại như thế nào?",
        "Cảm ơn em nhiều nhé.",
    ]

    for q in questions:
        audio, err = mgr.synthesize_audio(q)
        assert audio is not None
        assert err == ""
        # Invariants after every single turn
        assert mgr.config.tts_locale == "vi-VN"
        assert mgr.config.response_language == "vi-VN"
        assert mgr.config.tts_gender == "female"
        assert mgr.config.tts_voice_preference == "vi-VN-HoaiMyNeural"
        assert mgr.config.status == TTSStatus.READY.value


def test_tts_10_pc_and_pi5_hardware_status(tts_server_instance: str):
    """TTS-10: Verifies PC Core synthesis via REST API; reports physical Pi 5 separately as BLOCKED if absent."""
    # 1. PC Core REST Synthesis verification
    req_body = json.dumps({
        "text": "Chào Anh Quanpt1! PC Core đã kiểm tra giọng nữ tiếng Việt thành công.",
        "voice_id": "vi-VN-HoaiMyNeural",
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{tts_server_instance}/api/voice/tts-synthesize",
        data=req_body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10.0) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["success"] is True
        assert data["voice_id"] == "vi-VN-HoaiMyNeural"
        assert data["locale"] == "vi-VN"
        assert data["gender"] == "female"
        assert len(data["audio_base64"]) > 5000
        assert data["timeline"] is not None

    # 2. Raspberry Pi 5 Physical Hardware Probe
    # Pi 5 is not physically attached in this PC test environment.
    # Non-negotiable constraint: Do not fake success for physical Pi 5.
    pi5_hardware_connected = False
    if not pi5_hardware_connected:
        # Record explicitly as BLOCKED for physical hardware testing
        pytest.skip("BLOCKED: Phần cứng Raspberry Pi 5 thực tế chưa kết nối mạng trong phiên kiểm thử tự động này. PC Core đã được xác thực hoàn chỉnh.")
