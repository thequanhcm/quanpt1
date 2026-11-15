"""Đo profile giọng Hoài My (TTS hiện tại) cùng phương pháp với 6.mp4 → đối chiếu.
Dùng câu tiếng Việt mẫu, synth qua edge-tts trực tiếp (không cần server)."""
import asyncio
import json
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, r"E:\BRAIN\src")

OUT = Path(r"E:\BRAIN\data\voice_profile_hoaimy.json")

TEXT = ("Chào anh Quân, em là Cherry. Hôm nay em xin phép báo cáo tiến độ "
        "của hệ thống. Các chỉ số đều ổn định và em đã cập nhật chuyển động mới. "
        "Anh cần em hỗ trợ gì thêm không ạ?")


def analyze_wav(path: Path) -> dict:
    with wave.open(str(path), "rb") as w:
        sr = w.getframerate()
        data = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    if sr != 16000:
        # resample đơn giản bằng ffmpeg về 16k
        import imageio_ffmpeg
        p2 = path.with_suffix(".16k.wav")
        subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-i", str(path),
                        "-ac", "1", "-ar", "16000", str(p2)], capture_output=True, timeout=120)
        with wave.open(str(p2), "rb") as w:
            sr = w.getframerate()
            data = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0

    frame = int(0.025 * sr)
    hop = int(0.010 * sr)
    n_frames = (len(data) - frame) // hop
    rms = np.array([np.sqrt(np.mean(data[i * hop:i * hop + frame] ** 2)) for i in range(n_frames)])
    thr = 0.35 * (np.percentile(rms, 75) + 1e-9)
    voiced = rms > thr
    speech_ratio = float(voiced.mean())
    d = np.diff(voiced.astype(int))
    starts = int(np.sum((d[1:] == 1) & (d[:-1] == 0)) + (1 if voiced[0] else 0))
    dur_s = len(data) / sr
    wpm = (starts / max(dur_s, 0.1)) * 60.0 * 0.62

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

    return {
        "duration_s": round(dur_s, 2),
        "speech_ratio": round(speech_ratio, 3),
        "burst_rate_est_words_per_min": round(float(wpm), 1),
        "f0_mean_hz": round(float(np.mean(f0s)), 1) if len(f0s) else None,
        "f0_std_hz": round(float(np.std(f0s)), 1) if len(f0s) else None,
        "f0_p10": round(float(np.percentile(f0s, 10)), 1) if len(f0s) else None,
        "f0_p90": round(float(np.percentile(f0s, 90)), 1) if len(f0s) else None,
        "f0_frames": int(len(f0s)),
    }


async def synth(rate_pct: int, pitch_hz: int, tag: str) -> dict:
    import edge_tts
    mp3 = Path(tempfile.gettempdir()) / f"hoaimy_{tag}.mp3"
    wav = Path(tempfile.gettempdir()) / f"hoaimy_{tag}.wav"
    communicate = edge_tts.Communicate(
        text=TEXT, voice="vi-VN-HoaiMyNeural",
        rate=f"{rate_pct:+d}%", pitch=f"{pitch_hz:+d}Hz", volume="+0%",
    )
    with open(mp3, "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
    import imageio_ffmpeg
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-i", str(mp3),
                    "-ac", "1", "-ar", "16000", str(wav)], capture_output=True, timeout=120)
    prof = analyze_wav(wav)
    prof["rate"] = f"{rate_pct:+d}%"
    prof["pitch"] = f"{pitch_hz:+d}Hz"
    return prof


def main():
    # Baseline + 3 biến thể quanh profile 6.mp4 (F0 190Hz, wpm ~69, speech 51%)
    variants = [
        (0, 0, "baseline"),
        (-8, 0, "cham8"),      # chậm 8% → gần wpm mẫu
        (-8, -4, "cham8_thap4"),  # chậm + pitch thấp hơn 4Hz
        (-12, -2, "cham12_thap2"),
    ]
    results = {}
    for rate, pitch, tag in variants:
        try:
            results[tag] = asyncio.run(synth(rate, pitch, tag))
            print(tag, "->", json.dumps(results[tag], ensure_ascii=False))
        except Exception as e:
            results[tag] = {"error": str(e)[:200]}
            print(tag, "ERROR", e)

    sample_6 = json.loads(Path(r"E:\BRAIN\data\voice_profile_6mp4.json").read_text(encoding="utf-8"))
    summary = {
        "hoaimy_variants": results,
        "sample_6mp4_aggregate": sample_6.get("aggregate"),
        "note": "same analyzer, same 25ms/10ms frame, autocorr pitch 70-400Hz",
    }
    OUT.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print("SAVED", OUT)


if __name__ == "__main__":
    main()
