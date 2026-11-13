"""Test lọc tạp âm + âm thanh môi trường cho wake_word_service (13/11/2026).

Kiểm tra các thành phần DSP mới:
1. NoiseFloorEstimator — adaptive noise floor theo percentile RMS
2. _spectral_gate — high-pass 1 bậc cắt trầm (rumble/HVAC/TV-bass)
3. AGC nâng cấp — gain max 24x, ngưỡng speech-band, gate theo noise floor
4. Vòng lặp: chunk toàn tạp âm → bị gate (không đưa Vosk); có tiếng nói → qua
"""
import math
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "edge_client"))

try:  # vosk chỉ có trên Pi5 (wake_venv) — trên PC test chỉ cần các hàm DSP
    import wake_word_service as wws
except ImportError as _e:  # ModuleNotFoundError: vosk
    if "vosk" not in str(_e):
        raise

    import types

    _src = (Path(__file__).resolve().parents[1] / "edge_client"
            / "wake_word_service.py").read_text(encoding="utf-8")
    # cắt phần import vosk/model để nạp thuần các hàm DSP + matcher
    _src = _src.replace("from vosk import Model, KaldiRecognizer", "")
    _mod = types.ModuleType("wake_word_service_dsp")
    _mod.__dict__["__name__"] = "wake_word_service"
    exec(compile(_src, "wake_word_service.py", "exec"), _mod.__dict__)
    wws = _mod


def _pcm(rms: float, n: int = 4000, seed: int = 1) -> bytes:
    """Sinh PCM16 mono n mẫu với RMS chỉ định (sine 200Hz + noise)."""
    out = []
    amp = rms * math.sqrt(2)
    for i in range(n):
        v = amp * math.sin(2 * math.pi * 200 * i / 16000)
        if seed > 0:
            v += ((i * 2654435761 + seed * 97) % 2000 - 1000) * (rms / 700)
        out.append(int(max(-32768, min(32767, v))))
    return struct.pack("<" + "h" * n, *out)


# ---------------------------------------------------------------------------
# 1) NoiseFloorEstimator
# ---------------------------------------------------------------------------

def test_noise_floor_starts_at_first_rms():
    est = wws.NoiseFloorEstimator(init=150.0)
    # sau ~1s audio (4 chunk 0.25s) floor phải tiến về mức nền 300
    for _ in range(200):
        est.update(300.0)
    assert est.level > 150.0  # đã rời khỏi init và bám về phía nền thật


def test_noise_floor_tracks_low_rms_downward():
    est = wws.NoiseFloorEstimator(init=900.0, down=0.05)
    est.update(300.0)  # tiếng lùi xuống → floor bám nhanh
    assert est.level < 900.0


def test_noise_floor_ignores_loud_speech_upward():
    est = wws.NoiseFloorEstimator(init=150.0)
    est.update(8000.0)  # tiếng nói to không được kéo floor lên mạnh
    assert est.level < 1000.0


def test_noise_floor_slow_rise_when_persistent():
    est = wws.NoiseFloorEstimator(init=100.0)
    for _ in range(600):  # tạp âm đều đặn ~10 phút → floor lên từ từ
        est.update(500.0)
    assert 100.0 < est.level <= 500.0


# ---------------------------------------------------------------------------
# 2) High-pass filter (cắt rumble/tần số trầm)
# ---------------------------------------------------------------------------

def test_highpass_attenuates_low_rumble():
    # sine 60Hz (rumble/HVAC) → sau HP phải giảm mạnh
    n = 16000
    low = [int(8000 * math.sin(2 * math.pi * 60 * i / 16000)) for i in range(n)]
    hp = wws.make_highpass()
    out = [hp(v / 32768.0) for v in low]
    rms_in = math.sqrt(sum(v * v for v in low) / n)
    rms_out = math.sqrt(sum(v * v for v in out) / n) * 32768
    assert rms_out < rms_in * 0.5


def test_highpass_keeps_voice_band():
    # sine 400Hz (trong dải giọng nói) → phải giữ gần nguyên
    n = 16000
    voice = [int(8000 * math.sin(2 * math.pi * 400 * i / 16000)) for i in range(n)]
    hp = wws.make_highpass()
    out = [hp(v / 32768.0) for v in voice]
    # sau 2 chu kỳ đầu (transient), biên độ ổn định
    rms_in = math.sqrt(sum(v * v for v in voice[4000:]) / (n - 4000))
    rms_out = math.sqrt(sum(v * v for v in out[4000:]) / (n - 4000)) * 32768
    assert rms_out > rms_in * 0.7


# ---------------------------------------------------------------------------
# 3) Pipeline xử lý chunk: _process_chunk
# ---------------------------------------------------------------------------

def test_process_chunk_gates_pure_noise():
    # Tạp âm RMS 140 (phòng có TV) + noise floor học được 140 → chunk bị gate
    est = wws.NoiseFloorEstimator(init=140.0)
    for _ in range(50):
        est.update(140.0)
    chunk = _pcm(140)
    out, gated = wws._process_chunk(chunk, est)
    assert gated is True
    assert out is None


def test_process_chunk_passes_loud_speech():
    est = wws.NoiseFloorEstimator(init=140.0)
    for _ in range(50):
        est.update(140.0)
    chunk = _pcm(2500)  # tiếng nói gần (RMS cao)
    out, gated = wws._process_chunk(chunk, est)
    assert gated is False
    assert out is not None and len(out) > 0


def test_process_chunk_medium_speech_still_passes():
    # tiếng nói xa hơn (RMS 700) vẫn phải qua — SNR 700/140 ≈ 14dB
    est = wws.NoiseFloorEstimator(init=140.0)
    for _ in range(50):
        est.update(140.0)
    chunk = _pcm(700)
    out, gated = wws._process_chunk(chunk, est)
    assert gated is False


def test_process_chunk_never_fully_silent_output():
    # khi qua gate, output phải còn sót tín hiệu (không zero-out hoàn toàn)
    est = wws.NoiseFloorEstimator(init=100.0)
    for _ in range(50):
        est.update(100.0)
    chunk = _pcm(3000)
    out, gated = wws._process_chunk(chunk, est)
    assert gated is False
    samples = struct.unpack("<" + "h" * (len(out) // 2), out)
    assert max(abs(s) for s in samples) > 500


# ---------------------------------------------------------------------------
# 4) AGC nâng cấp
# ---------------------------------------------------------------------------

def test_agc_gain_max_raised():
    # RMS 400 → gain 9000/400 = 22.5 phải được phép (cũ max 8x)
    import array
    samples = array.array("h", _pcm(400))
    boosted = wws._agc_boost(samples, floor_level=100.0)
    rms_after = math.sqrt(sum(x * x for x in boosted) / len(boosted))
    assert rms_after > 400 * 8  # gain > 8x đã được áp dụng


def test_agc_clip_guard():
    import array
    samples = array.array("h", _pcm(20000))
    boosted = wws._agc_boost(samples, floor_level=100.0)
    assert max(abs(x) for x in boosted) <= 32000
