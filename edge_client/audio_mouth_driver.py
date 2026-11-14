"""Cherry Audio Mouth Driver — Sprint 4: Natural Voice & Lip-Sync (14/11/2026).

Mirror Python của edge_client/audio_mouth_driver.js — AudioMouthDriver +
computeRMS + smoothEnvelope + visemeFromRMS + interrupt + barge-in.
Dùng cho test pytest (mock 100%).

Nguồn thiết kế: CHERRY_EMBODIMENT_SPRINT_PLAN.md §6 (Sprint 4).
"""
from __future__ import annotations

import math
import time
from typing import Any, Callable, Dict, List, Optional

__all__ = [
    "VERSION", "VISEME_THRESHOLDS", "compute_rms", "smooth_envelope",
    "viseme_from_rms", "AudioMouthDriver",
]

VERSION = "s4_1411"


# ===== 1. compute_rms — RMS từ byte frequency data (0..255) =====
def compute_rms(data: Optional[List[int]]) -> float:
    if not data:
        return 0.0
    s = 0.0
    for v in data:
        n = (v - 128) / 128.0
        s += n * n
    return math.sqrt(s / len(data))


# ===== 2. smooth_envelope — EMA =====
def smooth_envelope(prev: Optional[float], current: float, alpha: float = 0.4) -> float:
    if prev is None:
        return current
    return prev * (1 - alpha) + current * alpha


# ===== 3. viseme_from_rms =====
VISEME_THRESHOLDS: List[Dict[str, Any]] = [
    {"max": 0.05, "viseme": "REST", "open": 0.0},
    {"max": 0.15, "viseme": "A", "open": 0.25},
    {"max": 0.30, "viseme": "O", "open": 0.45},
    {"max": 0.50, "viseme": "E", "open": 0.55},
    {"max": 0.70, "viseme": "I", "open": 0.65},
    {"max": 1.01, "viseme": "U", "open": 0.75},
]


def viseme_from_rms(rms: float) -> Dict[str, Any]:
    for t in VISEME_THRESHOLDS:
        if rms < t["max"]:
            return {"viseme": t["viseme"], "open": t["open"]}
    return {"viseme": "REST", "open": 0.0}


# ===== 4. AudioMouthDriver =====
class AudioMouthDriver:
    """Máy trạng thái lip-sync: start(audio) → update() mỗi frame → stop().
    interrupt(): audio mới bắt đầu. barge_in(): người dùng ngắt lời."""

    def __init__(self, alpha: float = 0.4,
                 on_viseme: Optional[Callable[[str, float], None]] = None,
                 on_end: Optional[Callable[[str], None]] = None,
                 on_interrupt: Optional[Callable[[], None]] = None,
                 on_barge_in: Optional[Callable[[], None]] = None):
        self._audio: Any = None
        self._analyser: Any = None
        self._data_array: Optional[List[int]] = None
        self._envelope: float = 0.0
        self._alpha = alpha
        self._active: bool = False
        self._interrupted: bool = False
        self._barged_in: bool = False
        self._current_viseme: str = "REST"
        self._current_open: float = 0.0
        self._on_viseme = on_viseme or (lambda v, o: None)
        self._on_end = on_end or (lambda r: None)
        self._on_interrupt = on_interrupt or (lambda: None)
        self._on_barge_in = on_barge_in or (lambda: None)
        self._log: List[Dict[str, Any]] = []
        self._max_log = 16

    def _push_log(self, entry: Dict[str, Any]) -> None:
        self._log.append(entry)
        if len(self._log) > self._max_log:
            self._log.pop(0)

    def get_log(self) -> List[Dict[str, Any]]:
        return list(self._log)

    def is_active(self) -> bool:
        return self._active

    def get_current(self) -> Dict[str, Any]:
        return {"viseme": self._current_viseme, "open": self._current_open,
                "envelope": self._envelope, "active": self._active}

    def start(self, audio: Any = None, *, data_array: Optional[List[int]] = None,
              existing_analyser: Any = None) -> bool:
        if self._active:
            self.interrupt()
        self._audio = audio
        self._envelope = 0.0
        self._interrupted = False
        self._barged_in = False
        self._active = True
        # data_array có thể truyền trực tiếp (test) hoặc qua existing_analyser (production)
        if data_array is not None:
            self._data_array = data_array
            self._analyser = existing_analyser or True  # truthy marker
        elif existing_analyser is not None:
            self._analyser = existing_analyser
            self._data_array = [0] * 128
        self._push_log({"t": time.time() * 1000, "kind": "start",
                        "has_analyser": self._analyser is not None})
        return True

    def update(self, data_array: Optional[List[int]] = None) -> Dict[str, Any]:
        if not self._active:
            return self.get_current()
        # Gate 4: không có analyser → KHÔNG đọc data, giữ REST
        if self._analyser is None:
            self._current_viseme = "REST"
            self._current_open = 0.0
            return self.get_current()
        data = data_array if data_array is not None else self._data_array
        if not data:
            self._current_viseme = "REST"
            self._current_open = 0.0
            return self.get_current()
        rms = compute_rms(data)
        self._envelope = smooth_envelope(self._envelope, rms, self._alpha)
        v = viseme_from_rms(self._envelope)
        if v["viseme"] != self._current_viseme or abs(v["open"] - self._current_open) > 0.01:
            self._current_viseme = v["viseme"]
            self._current_open = v["open"]
            self._on_viseme(v["viseme"], v["open"])
        return self.get_current()

    def stop(self, reason: str = "stop") -> None:
        if not self._active:
            return
        self._active = False
        self._envelope = 0.0
        self._current_viseme = "REST"
        self._current_open = 0.0
        self._on_viseme("REST", 0.0)
        self._on_end(reason)
        self._push_log({"t": time.time() * 1000, "kind": "stop", "reason": reason})

    def interrupt(self) -> None:
        if not self._active:
            return
        self._interrupted = True
        self._push_log({"t": time.time() * 1000, "kind": "interrupt"})
        self._on_interrupt()
        self.stop("interrupt")

    def barge_in(self) -> None:
        if not self._active:
            return
        self._barged_in = True
        if self._audio is not None:
            try:
                self._audio.pause()
            except Exception:
                pass
        self._push_log({"t": time.time() * 1000, "kind": "barge_in"})
        self._on_barge_in()
        self.stop("barge_in")
