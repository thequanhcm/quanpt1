"""Cherry Body Motion Engine — Sprint 6: Body Motion Engine (14/11/2026).

Mirror Python của edge_client/body_motion_engine.js — BodyMotionEngine +
BODY_PRESETS + BREATH_PRESETS + ARM_REACH_PRESETS + tick + setState +
setSpeaking + setSpeechEnergy. Dùng cho test pytest (mock 100%).

Nguồn thiết kế: CHERRY_EMBODIMENT_SPRINT_PLAN.md §8 (Performance) — thay
bằng Body Motion Engine theo yêu cầu owner "hình thể linh hoạt uyển chuyển".
"""
from __future__ import annotations

import math
import time
from typing import Any, Callable, Dict, List, Optional

__all__ = [
    "VERSION", "BODY_PRESETS", "BREATH_PRESETS", "ARM_REACH_PRESETS",
    "BodyMotionEngine",
]

VERSION = "s6_1411"


# ===== 1. BODY_PRESETS =====
BODY_PRESETS: Dict[str, Dict[str, float]] = {
    "IDLE": {"leanX": 0, "leanY": 0, "swayX": 0.3, "swayY": 0.2},
    "LISTENING": {"leanX": 0.1, "leanY": 0.05, "swayX": 0.2, "swayY": 0.15},
    "THINKING": {"leanX": -0.15, "leanY": 0, "swayX": 0.1, "swayY": 0.1},
    "ANALYTICAL_THINKING": {"leanX": -0.1, "leanY": 0, "swayX": 0.15, "swayY": 0.1},
    "CURIOUS": {"leanX": 0.2, "leanY": 0, "swayX": 0.25, "swayY": 0.15},
    "WARM_GREETING": {"leanX": 0.1, "leanY": 0.1, "swayX": 0.4, "swayY": 0.3},
    "HAPPY": {"leanX": 0.05, "leanY": 0, "swayX": 0.5, "swayY": 0.4},
    "PROUD": {"leanX": 0, "leanY": -0.1, "swayX": 0.3, "swayY": 0.2},
    "CONFIDENT_SUCCESS": {"leanX": 0, "leanY": -0.15, "swayX": 0.35, "swayY": 0.25},
    "SURPRISED": {"leanX": 0, "leanY": -0.2, "swayX": 0.6, "swayY": 0.5},
    "WARNING": {"leanX": 0, "leanY": 0, "swayX": 0.2, "swayY": 0.15},
    "SERIOUS_ALERT": {"leanX": 0, "leanY": 0, "swayX": 0.1, "swayY": 0.1},
    "APOLOGETIC": {"leanX": -0.1, "leanY": 0.15, "swayX": 0.15, "swayY": 0.1},
    "EMPATHETIC": {"leanX": 0.05, "leanY": 0.05, "swayX": 0.25, "swayY": 0.2},
    "CONSULTATIVE_INQUIRING": {"leanX": 0.1, "leanY": 0, "swayX": 0.2, "swayY": 0.15},
    "SPEAKING": {"leanX": 0, "leanY": 0, "swayX": 0.3, "swayY": 0.2},
    "ERROR": {"leanX": 0, "leanY": 0.1, "swayX": 0.15, "swayY": 0.1},
    "SLEEPING": {"leanX": 0, "leanY": 0.2, "swayX": 0.05, "swayY": 0.05},
    "OFFLINE": {"leanX": 0, "leanY": 0, "swayX": 0, "swayY": 0},
    "RECONNECTING": {"leanX": 0, "leanY": 0, "swayX": 0.1, "swayY": 0.1},
    "NEUTRAL": {"leanX": 0, "leanY": 0, "swayX": 0.2, "swayY": 0.15},
}


# ===== 2. BREATH_PRESETS =====
BREATH_PRESETS: Dict[str, Dict[str, float]] = {
    "IDLE": {"rate": 4.0, "amplitude": 0.3},
    "LISTENING": {"rate": 3.5, "amplitude": 0.25},
    "THINKING": {"rate": 5.0, "amplitude": 0.2},
    "SPEAKING": {"rate": 3.0, "amplitude": 0.4},
    "SLEEPING": {"rate": 6.0, "amplitude": 0.5},
    "default": {"rate": 4.0, "amplitude": 0.3},
}


# ===== 3. ARM_REACH_PRESETS =====
ARM_REACH_PRESETS: Dict[str, Dict[str, float]] = {
    "IDLE": {"leftArm": 0, "rightArm": 0, "leftReach": 0.3, "rightReach": 0.3},
    "LISTENING": {"leftArm": 5, "rightArm": 5, "leftReach": 0.4, "rightReach": 0.4},
    "SPEAKING": {"leftArm": 15, "rightArm": 15, "leftReach": 0.6, "rightReach": 0.6},
    "WARM_GREETING": {"leftArm": 30, "rightArm": 30, "leftReach": 0.7, "rightReach": 0.7},
    "HAPPY": {"leftArm": 25, "rightArm": 25, "leftReach": 0.6, "rightReach": 0.6},
    "PROUD": {"leftArm": 10, "rightArm": 10, "leftReach": 0.5, "rightReach": 0.5},
    "SURPRISED": {"leftArm": 45, "rightArm": 45, "leftReach": 0.8, "rightReach": 0.8},
    "APOLOGETIC": {"leftArm": -10, "rightArm": -10, "leftReach": 0.2, "rightReach": 0.2},
    "default": {"leftArm": 0, "rightArm": 0, "leftReach": 0.3, "rightReach": 0.3},
}


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


# ===== 4. BodyMotionEngine =====
class BodyMotionEngine:
    """Máy trạng thái body motion: tick(now) cập nhật sway/lean/breath/arm.
    set_state(state): đổi state → áp preset. set_speaking(bool): tăng sway.
    set_speech_energy(0..1): tăng arm reach theo audio energy."""

    def __init__(self, now_fn: Optional[Callable[[], float]] = None):
        self._now_fn = now_fn or (lambda: time.time() * 1000.0)
        self._state: str = "IDLE"
        self._speaking: bool = False
        self._speech_energy: float = 0.0
        self._current: Dict[str, float] = {
            "leanX": 0.0, "leanY": 0.0, "swayX": 0.0, "swayY": 0.0,
            "breathOffset": 0.0,
            "leftArm": 0.0, "rightArm": 0.0,
            "leftReach": 0.3, "rightReach": 0.3,
        }
        # Init _target từ IDLE preset để oscillation có biên độ ngay từ tick đầu
        _idle_body = BODY_PRESETS["IDLE"]
        _idle_arm = ARM_REACH_PRESETS["IDLE"]
        self._target: Dict[str, float] = {
            "leanX": _idle_body["leanX"], "leanY": _idle_body["leanY"],
            "swayX": _idle_body["swayX"], "swayY": _idle_body["swayY"],
            "leftArm": _idle_arm["leftArm"], "rightArm": _idle_arm["rightArm"],
            "leftReach": _idle_arm["leftReach"], "rightReach": _idle_arm["rightReach"],
        }
        self._last_tick: float = 0.0
        self._log: List[Dict[str, Any]] = []
        self._max_log = 16

    def _push_log(self, entry: Dict[str, Any]) -> None:
        self._log.append(entry)
        if len(self._log) > self._max_log:
            self._log.pop(0)

    def get_log(self) -> List[Dict[str, Any]]:
        return list(self._log)

    def get_transform(self) -> Dict[str, float]:
        return dict(self._current)

    def set_state(self, state: str) -> None:
        if self._state == state:
            return
        self._state = state
        body = BODY_PRESETS.get(state, BODY_PRESETS["IDLE"])
        arm = ARM_REACH_PRESETS.get(state, ARM_REACH_PRESETS["default"])
        self._target["leanX"] = body["leanX"]
        self._target["leanY"] = body["leanY"]
        self._target["swayX"] = body["swayX"]
        self._target["swayY"] = body["swayY"]
        self._target["leftArm"] = arm["leftArm"]
        self._target["rightArm"] = arm["rightArm"]
        self._target["leftReach"] = arm["leftReach"]
        self._target["rightReach"] = arm["rightReach"]
        self._push_log({"t": self._now_fn(), "kind": "state", "state": state})

    def set_speaking(self, speaking: bool) -> None:
        self._speaking = bool(speaking)

    def set_speech_energy(self, energy: float) -> None:
        self._speech_energy = max(0.0, min(1.0, energy or 0.0))

    def tick(self, now_ms: Optional[float] = None) -> Dict[str, float]:
        now = now_ms if now_ms is not None else self._now_fn()
        dt = (now - self._last_tick) if self._last_tick else 16.0
        self._last_tick = now

        # 1. Breath oscillation
        breath = BREATH_PRESETS.get(self._state, BREATH_PRESETS["default"])
        breath_phase = (now / 1000.0) * (2 * math.pi / breath["rate"])
        breath_offset = math.sin(breath_phase) * breath["amplitude"]

        # 2. Sway oscillation
        sway_phase = (now / 1000.0) * 1.2
        sway_x = self._target["swayX"] * (0.7 + 0.3 * math.sin(sway_phase))
        sway_y = self._target["swayY"] * (0.7 + 0.3 * math.cos(sway_phase * 0.8))

        # 3. Speaking boost
        if self._speaking:
            speech_boost = 1 + self._speech_energy * 0.5
            sway_x *= speech_boost
            sway_y *= speech_boost
            self._target["leftArm"] = min(60, self._target["leftArm"] + 10 * self._speech_energy)
            self._target["rightArm"] = min(60, self._target["rightArm"] + 10 * self._speech_energy)
            self._target["leftReach"] = min(1.0, self._target["leftReach"] + 0.2 * self._speech_energy)
            self._target["rightReach"] = min(1.0, self._target["rightReach"] + 0.2 * self._speech_energy)

        # 4. Lerp current toward target
        lerp_factor = min(1.0, dt / 100.0)
        self._current["leanX"] = _lerp(self._current["leanX"], self._target["leanX"], lerp_factor)
        self._current["leanY"] = _lerp(self._current["leanY"], self._target["leanY"], lerp_factor)
        self._current["swayX"] = sway_x
        self._current["swayY"] = sway_y
        self._current["breathOffset"] = breath_offset
        self._current["leftArm"] = _lerp(self._current["leftArm"], self._target["leftArm"], lerp_factor)
        self._current["rightArm"] = _lerp(self._current["rightArm"], self._target["rightArm"], lerp_factor)
        self._current["leftReach"] = _lerp(self._current["leftReach"], self._target["leftReach"], lerp_factor)
        self._current["rightReach"] = _lerp(self._current["rightReach"], self._target["rightReach"], lerp_factor)

        return self.get_transform()
