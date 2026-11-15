"""Đo PROFILE GIỌNG NÓI thật của 6.mp4 (English with CTM) để tinh chỉnh TTS
Hoài My về phía giống mẫu: tốc độ từ/phút, tỷ lệ nói/nghỉ, pitch (F0) mean/std,
năng lượng envelope. Dùng imageio_ffmpeg trích 3 đoạn ~60s (đầu/giữa/cuối)
→ mono 16k wav → phân tích numpy + autocorrelation pitch.

Output: data/voice_profile_6mp4.json
"""
import json
import subprocess
import tempfile
import wave
from pathlib import Path

import imageio_ffmpeg
import numpy as np

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
SRC = r"E:\BRAIN\Pi5\6.mp4"
OUT = Path(r"E:\BRAIN\data\voice_profile_6mp4.json")

# 3 đoạn đại diện ~60s mỗi đoạn (bỏ intro/outro)
SEGMENTS = [
    ("intro", 30, 90),
    ("middle", 2900, 2960),
    ("late", 5700, 5760),
]

DURATION_TOTAL = 5924.0


def extract_segment(name: str, start: float, dur: float) -> Path:
    wav_path = Path(tempfile.gettempdir()) / f"seg6_{name}.wav"
    cmd = [
        FFMPEG, "-y", "-ss", str(start), "-t", str(dur),
        "-i", SRC, "-vn", "-ac", "1", "-ar", "16000",
        "-af", "highpass=f=70,lowpass=f=4000",
        str(wav_path),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg fail {name}: {r.stderr[-300:]}")
    return wav_path


def read_wav(path: Path) -> np.ndarray:
    with wave.open(str(path), "rb") as w:
        sr = w.getframerate()
        n = w.getnframes()
        data = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32) / 32768.0
    return data, sr


def analyze(data: np.ndarray, sr: int) -> dict:
    frame = int(0.025 * sr)   # 25ms
    hop = int(0.010 * sr)     # 10ms
    n_frames = (len(data) - frame) // hop
    rms = np.array([
        np.sqrt(np.mean(data[i * hop:i * hop + frame] ** 2))
        for i in range(n_frames)
    ])
    thr = 0.35 * (np.percentile(rms, 75) + 1e-9)
    voiced = rms > thr
    speech_ratio = float(voiced.mean())

    # tốc độ nói: đếm "burst" (đoạn voiced liên tục = từ/cụm)
    d = np.diff(voiced.astype(int))
    starts = int(np.sum((d[1:] == 1) & (d[:-1] == 0)) + (1 if voiced[0] else 0))
    dur_s = len(data) / sr
    words_per_min = (starts / max(dur_s, 0.1)) * 60.0 * 0.62  # hệ số hiệu chỉnh syllable→word ~0.62

    # pitch F0 bằng autocorrelation trên frame voiced (70–400Hz)
    f0s = []
    for i in range(n_frames):
        if not voiced[i]:
            continue
        seg = data[i * hop:i * hop + frame]
        seg = seg - seg.mean()
        if seg.std() < 1e-4:
            continue
        ac = np.correlate(seg, seg, "full")[frame - 1:]
        ac = ac / (ac[0] + 1e-9)
        lo, hi = int(sr / 400), int(sr / 70)
        if hi >= len(ac):
            continue
        seg_ac = ac[lo:hi]
        peak = np.argmax(seg_ac) + lo
        if ac[peak] > 0.45:
            f0s.append(sr / peak)
    f0s = np.array(f0s)

    # năng lượng envelope chuẩn hoá (đối chiếu với MAU band 0.42..0.78)
    env_norm = rms / (np.percentile(rms, 95) + 1e-9)

    return {
        "duration_s": round(dur_s, 1),
        "speech_ratio": round(speech_ratio, 3),
        "pause_ratio": round(1 - speech_ratio, 3),
        "burst_rate_est_words_per_min": round(float(words_per_min), 1),
        "f0_mean_hz": round(float(np.mean(f0s)), 1) if len(f0s) else None,
        "f0_std_hz": round(float(np.std(f0s)), 1) if len(f0s) else None,
        "f0_p10": round(float(np.percentile(f0s, 10)), 1) if len(f0s) else None,
        "f0_p90": round(float(np.percentile(f0s, 90)), 1) if len(f0s) else None,
        "env_p10": round(float(np.percentile(env_norm, 10)), 3),
        "env_p90": round(float(np.percentile(env_norm, 90)), 3),
        "f0_frames": int(len(f0s)),
    }


results = {}
for name, start, dur in SEGMENTS:
    wav = extract_segment(name, start, dur)
    data, sr = read_wav(wav)
    results[name] = analyze(data, sr)
    print(name, "->", json.dumps(results[name]))

# trung bình có trọng số theo độ dài
f0m = [v["f0_mean_hz"] for v in results.values() if v["f0_mean_hz"]]
f0s_ = [v["f0_std_hz"] for v in results.values() if v["f0_std_hz"]]
wpm = [v["burst_rate_est_words_per_min"] for v in results.values()]
sp = [v["speech_ratio"] for v in results.values()]

summary = {
    "source": "6.mp4 (English with CTM) — người nói camera 5924s",
    "segments": results,
    "aggregate": {
        "f0_mean_hz": round(float(np.mean(f0m)), 1) if f0m else None,
        "f0_std_hz": round(float(np.mean(f0s_)), 1) if f0s_ else None,
        "est_words_per_min": round(float(np.mean(wpm)), 1),
        "speech_ratio": round(float(np.mean(sp)), 3),
    },
    "measured": "2026-11-15 23:45 ICT, ffmpeg via imageio_ffmpeg, autocorr pitch 70-400Hz",
}
OUT.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
print("SAVED", OUT)
