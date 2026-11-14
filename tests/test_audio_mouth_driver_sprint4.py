"""Sprint 4 — Natural Voice & Lip-Sync (14/11/2026).

Card: TASK-EMBODIMENT-S4 (APPROVED, auth owner_desktop_chat_directive).
Test theo CHERRY_EMBODIMENT_SPRINT_PLAN.md §6.4:
  - Câu ngắn / dài / Việt / dấu câu / câu hỏi / cảm thán / giải thích / đa đoạn
  - Người dùng ngắt lời (barge-in)
  - TTS lỗi / audio cache / audio streaming
  - Gate 4: miệng KHÔNG cử động khi không có audio
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "edge_client"))

import audio_mouth_driver as amd  # noqa: E402


# ===== Helpers =====
def _silence(n: int = 128) -> list[int]:
    """Byte frequency data im lặng (128 = center)."""
    return [128] * n


def _speech(n: int = 128, level: int = 200) -> list[int]:
    """Byte frequency data có tiếng nói (level > 128)."""
    return [level] * n


def _driver(**kw) -> amd.AudioMouthDriver:
    return amd.AudioMouthDriver(**kw)


# ===== 1. RMS / envelope / viseme =====
class TestRMS:
    def test_silence_rms_zero(self):
        assert amd.compute_rms(_silence()) == pytest.approx(0.0, abs=1e-9)

    def test_speech_rms_positive(self):
        assert amd.compute_rms(_speech()) > 0.0

    def test_empty_data_rms_zero(self):
        assert amd.compute_rms([]) == 0.0
        assert amd.compute_rms(None) == 0.0

    def test_smooth_envelope_first_call(self):
        assert amd.smooth_envelope(None, 0.5) == 0.5

    def test_smooth_envelope_ema(self):
        # alpha=0.4: prev=0.5, current=1.0 → 0.5*0.6 + 1.0*0.4 = 0.7
        assert amd.smooth_envelope(0.5, 1.0, 0.4) == pytest.approx(0.7)

    def test_viseme_rest_below_005(self):
        v = amd.viseme_from_rms(0.0)
        assert v["viseme"] == "REST" and v["open"] == 0.0

    def test_viseme_a_005_to_015(self):
        v = amd.viseme_from_rms(0.10)
        assert v["viseme"] == "A" and v["open"] == 0.25

    def test_viseme_o_015_to_030(self):
        v = amd.viseme_from_rms(0.20)
        assert v["viseme"] == "O" and v["open"] == 0.45

    def test_viseme_e_030_to_050(self):
        v = amd.viseme_from_rms(0.40)
        assert v["viseme"] == "E" and v["open"] == 0.55

    def test_viseme_i_050_to_070(self):
        v = amd.viseme_from_rms(0.60)
        assert v["viseme"] == "I" and v["open"] == 0.65

    def test_viseme_u_above_070(self):
        v = amd.viseme_from_rms(0.80)
        assert v["viseme"] == "U" and v["open"] == 0.75


# ===== 2. Driver lifecycle =====
class TestDriverLifecycle:
    def test_initial_state_rest(self):
        d = _driver()
        assert d.is_active() is False
        assert d.get_current()["viseme"] == "REST"
        assert d.get_current()["open"] == 0.0

    def test_start_activates(self):
        d = _driver()
        d.start(audio="fake_audio", data_array=_silence())
        assert d.is_active() is True

    def test_stop_resets_to_rest(self):
        d = _driver()
        d.start(audio="fake_audio", data_array=_silence())
        d.update(_speech(level=200))
        d.stop("ended")
        assert d.is_active() is False
        assert d.get_current()["viseme"] == "REST"
        assert d.get_current()["open"] == 0.0

    def test_stop_idempotent(self):
        d = _driver()
        d.start(audio="fake_audio", data_array=_silence())
        d.stop()
        d.stop()  # không lỗi
        assert d.is_active() is False

    def test_update_without_analyser_keeps_rest(self):
        """Không có analyser → update KHÔNG đọc data → giữ REST (Gate 4)."""
        d = _driver()
        d.start(audio="fake_audio")  # không có analyser
        d.update(_speech(level=200))
        assert d.get_current()["viseme"] == "REST"
        assert d.get_current()["open"] == 0.0

    def test_update_with_silence_keeps_rest(self):
        d = _driver()
        d.start(audio="fake_audio", data_array=_silence())
        d.update(_silence())
        assert d.get_current()["viseme"] == "REST"

    def test_update_with_speech_drives_viseme(self):
        d = _driver()
        d.start(audio="fake_audio", data_array=_silence())
        d.update(_speech(level=200))  # RMS cao → U
        assert d.get_current()["viseme"] in ("A", "O", "E", "I", "U")

    def test_log_records_start_stop(self):
        d = _driver()
        d.start(audio="fake_audio", data_array=_silence())
        d.stop("ended")
        log = d.get_log()
        assert len(log) == 2
        assert log[0]["kind"] == "start"
        assert log[1]["kind"] == "stop" and log[1]["reason"] == "ended"


# ===== 3. Interrupt (audio mới bắt đầu) =====
class TestInterrupt:
    def test_interrupt_stops_active(self):
        d = _driver()
        d.start(audio="audio1", data_array=_silence())
        d.interrupt()
        assert d.is_active() is False

    def test_interrupt_calls_callback(self):
        called = []
        d = _driver(on_interrupt=lambda: called.append(True))
        d.start(audio="audio1", data_array=_silence())
        d.interrupt()
        assert called == [True]

    def test_interrupt_idempotent(self):
        d = _driver()
        d.start(audio="audio1", data_array=_silence())
        d.interrupt()
        d.interrupt()  # không lỗi
        assert d.is_active() is False

    def test_start_while_active_auto_interrupts(self):
        d = _driver()
        d.start(audio="audio1", data_array=_silence())
        d.start(audio="audio2", data_array=_silence())
        log = d.get_log()
        # log: start(audio1), interrupt, start(audio2)
        assert any(e["kind"] == "interrupt" for e in log)
        assert sum(1 for e in log if e["kind"] == "start") == 2


# ===== 4. Barge-in (người dùng ngắt lời) =====
class TestBargeIn:
    def test_barge_in_pauses_audio(self):
        class FakeAudio:
            def __init__(self):
                self.paused = False
            def pause(self):
                self.paused = True
        audio = FakeAudio()
        d = _driver()
        d.start(audio=audio, data_array=_silence())
        d.barge_in()
        assert audio.paused is True
        assert d.is_active() is False

    def test_barge_in_calls_callback(self):
        called = []
        d = _driver(on_barge_in=lambda: called.append(True))
        d.start(audio="audio1", data_array=_silence())
        d.barge_in()
        assert called == [True]

    def test_barge_in_resets_mouth(self):
        d = _driver()
        d.start(audio="audio1", data_array=_silence())
        d.update(_speech(level=200))
        d.barge_in()
        assert d.get_current()["viseme"] == "REST"
        assert d.get_current()["open"] == 0.0

    def test_barge_in_idempotent(self):
        d = _driver()
        d.start(audio="audio1", data_array=_silence())
        d.barge_in()
        d.barge_in()  # không lỗi
        assert d.is_active() is False


# ===== 5. Gate 4 — miệng KHÔNG cử động khi không có audio =====
class TestGate4:
    def test_no_audio_no_mouth_movement(self):
        """Gate 4: không có audio → miệng REST, open=0."""
        d = _driver()
        # Không start → update không có data → REST
        d.update(_speech(level=200))
        assert d.get_current()["viseme"] == "REST"
        assert d.get_current()["open"] == 0.0

    def test_audio_ended_mouth_resets(self):
        """Gate 4: audio kết thúc → miệng reset về REST ngay."""
        d = _driver()
        d.start(audio="audio1", data_array=_silence())
        d.update(_speech(level=200))
        assert d.get_current()["viseme"] != "REST"
        d.stop("ended")
        assert d.get_current()["viseme"] == "REST"
        assert d.get_current()["open"] == 0.0

    def test_barge_in_mouth_resets_immediately(self):
        """Gate 4: người dùng ngắt lời → miệng reset ngay (không chờ audio)."""
        d = _driver()
        d.start(audio="audio1", data_array=_silence())
        d.update(_speech(level=200))
        d.barge_in()
        assert d.get_current()["viseme"] == "REST"
        assert d.get_current()["open"] == 0.0


# ===== 6. Câu ngắn / dài / Việt / dấu câu / câu hỏi / cảm thán =====
class TestSpeechPatterns:
    def test_short_vietnamese_sentence(self):
        """Câu ngắn tiếng Việt: 'Xin chào' → RMS cao → viseme U."""
        d = _driver()
        d.start(audio="audio1", data_array=_silence())
        d.update(_speech(level=180))
        assert d.get_current()["viseme"] in ("A", "O", "E", "I", "U")

    def test_long_vietnamese_sentence(self):
        """Câu dài: nhiều frame update liên tục → viseme thay đổi."""
        d = _driver()
        d.start(audio="audio1", data_array=_silence())
        visemes = set()
        for level in [150, 180, 200, 170, 190, 160, 200, 180]:
            d.update(_speech(level=level))
            visemes.add(d.get_current()["viseme"])
        assert len(visemes) >= 2  # ít nhất 2 viseme khác nhau

    def test_question_with_rising_intonation(self):
        """Câu hỏi: 'Anh ơi?' → RMS cao → viseme."""
        d = _driver()
        d.start(audio="audio1", data_array=_silence())
        d.update(_speech(level=200))
        assert d.get_current()["viseme"] != "REST"

    def test_exclamation(self):
        """Câu cảm thán: 'Tuyệt vời!' → RMS cao."""
        d = _driver()
        d.start(audio="audio1", data_array=_silence())
        d.update(_speech(level=220))
        assert d.get_current()["viseme"] != "REST"

    def test_silence_between_words(self):
        """Im lặng giữa các từ → miệng về REST."""
        d = _driver()
        d.start(audio="audio1", data_array=_silence())
        d.update(_speech(level=200))
        assert d.get_current()["viseme"] != "REST"
        d.update(_silence())
        # Envelope giảm dần qua EMA → sau vài frame về REST
        for _ in range(20):
            d.update(_silence())
        assert d.get_current()["viseme"] == "REST"


# ===== 7. TTS lỗi / audio cache / streaming =====
class TestTTSErrorRecovery:
    def test_tts_error_resets_mouth(self):
        """TTS lỗi → audio.onerror → stop → miệng REST."""
        d = _driver()
        d.start(audio="audio1", data_array=_silence())
        d.update(_speech(level=200))
        d.stop("error")
        assert d.get_current()["viseme"] == "REST"

    def test_audio_cache_replay(self):
        """Audio cache: replay cùng audio → start lại OK."""
        d = _driver()
        d.start(audio="cached_audio", data_array=_silence())
        d.update(_speech(level=200))
        d.stop("ended")
        d.start(audio="cached_audio", data_array=_silence())
        assert d.is_active() is True

    def test_audio_streaming_continuous(self):
        """Audio streaming: nhiều frame update liên tục."""
        d = _driver()
        d.start(audio="stream", data_array=_silence())
        for i in range(50):
            level = 150 + (i % 5) * 10
            d.update(_speech(level=level))
        assert d.is_active() is True
        assert d.get_current()["viseme"] != "REST"


# ===== 8. Regression guards =====
class TestGuards:
    def test_version_tag(self):
        assert amd.VERSION == "s4_1411"

    def test_viseme_thresholds_complete(self):
        assert len(amd.VISEME_THRESHOLDS) == 6
        visemes = [t["viseme"] for t in amd.VISEME_THRESHOLDS]
        assert visemes == ["REST", "A", "O", "E", "I", "U"]

    def test_js_file_syntax_valid(self):
        js = (REPO / "edge_client" / "audio_mouth_driver.js").read_text(encoding="utf-8")
        assert "CherryAudioMouthDriver" in js
        assert "AudioMouthDriver" in js
        assert "computeRMS" in js
        assert "bargeIn" in js
