"""Voice STT cho QUAN AI BRAIN — nhận diện giọng nói file âm thanh DM.

(31/10/2026, owner) Anh Quân gửi bản ghi âm qua DM (m4a từ iPhone) và yêu cầu
nhận diện + phân tích để lần sau ra lệnh bằng giọng nói qua DM.

Pipeline: file audio -> faster-whisper (small, int8, CPU, language=vi)
-> text -> responder đưa text vào router lệnh như tin nhắn thường.

Chạy bằng BRAIN .venv python (faster-whisper cài trong venv đó).
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

AUDIO_EXTS = {".m4a", ".mp3", ".wav", ".amr", ".opus", ".aac", ".ogg",
              ".webm", ".flac", ".wma", ".mp4"}

_MODEL = None  # cache singleton trong process


def _get_model():
    """Load model 1 lần (55s lần đầu sau đó ~1.5s/audio)."""
    global _MODEL
    if _MODEL is None:
        from faster_whisper import WhisperModel
        _MODEL = WhisperModel("small", device="cpu", compute_type="int8")
    return _MODEL


def is_audio_file(name: str) -> bool:
    ext = Path(name).suffix.lower()
    return ext in AUDIO_EXTS


def transcribe(path: str | Path, language: str = "vi") -> str:
    """Nhận diện giọng nói file audio -> text tiếng Việt (fail-honest)."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"không tìm thấy file {p}")
    t0 = time.time()
    model = _get_model()
    segments, info = model.transcribe(str(p), language=language, vad_filter=True)
    text = " ".join(seg.text.strip() for seg in segments).strip()
    print(f"[STT] {p.name} [{info.duration:.1f}s] -> {text!r} "
          f"({time.time() - t0:.1f}s)", flush=True)
    return text


if __name__ == "__main__":
    # CLI: python voice_stt.py <file>
    if len(sys.argv) < 2:
        print("usage: voice_stt.py <audio_file>")
        sys.exit(2)
    try:
        print(transcribe(sys.argv[1]))
    except Exception as exc:  # fail-honest
        print(f"STT_FAIL: {exc}")
        sys.exit(1)
