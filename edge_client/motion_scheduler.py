"""Cherry Motion Scheduler — Sprint 2: Natural Motion Engine (14/11/2026).

Mirror Python của edge_client/motion_scheduler.js (MotionScheduler + Gesture
Library). Dùng cho test pytest (mock 100% theo policy) + có thể dùng cho
server-side motion planning trong tương lai.

Card: TASK-EMBODIMENT-S2 (APPROVED, auth owner_desktop_chat_directive).
Thiết kế: CHERRY_MOTION_ENGINE_DESIGN.md §3 (Scheduler) + §4 (Blending)
+ §5 (Gesture Library).
"""
from __future__ import annotations

import math
import random
import time
from typing import Any, Callable

PROTOCOL_VERSION = "s2_1411"

# ===== Motion Priority (design §3.2) =====
PRIORITY: dict[str, int] = {
    "SAFETY": 100,
    "SPEAKING": 80,
    "LISTENING": 70,
    "THINKING": 60,
    "EMOTION": 50,
    "IDLE": 30,
    "DECORATIVE": 10,
}


# ===== Easing Functions (design §3.3) =====
def _ease_linear(t: float) -> float:
    return t


def _ease_in(t: float) -> float:
    return t * t


def _ease_out(t: float) -> float:
    return 1 - (1 - t) * (1 - t)


def _ease_in_out(t: float) -> float:
    return 2 * t * t if t < 0.5 else 1 - math.pow(-2 * t + 2, 2) / 2


def _ease_cosine(t: float) -> float:
    return 0.5 - 0.5 * math.cos(math.pi * t)


EASING: dict[str, Callable[[float], float]] = {
    "linear": _ease_linear,
    "ease-in": _ease_in,
    "ease-out": _ease_out,
    "ease-in-out": _ease_in_out,
    "cosine": _ease_cosine,
}


def _apply_easing(t: float, name: str) -> float:
    fn = EASING.get(name, EASING["ease-out"])
    return fn(max(0.0, min(1.0, t)))


def _interpolate(start: Any, target: Any, t: float) -> Any:
    if isinstance(start, (int, float)) and isinstance(target, (int, float)):
        return start + (target - start) * t
    if isinstance(start, list) and isinstance(target, list):
        return [start[i] + (target[i] - start[i]) * t for i in range(len(start))]
    return target if t >= 1 else start


class MotionScheduler:
    """Stateful motion scheduler — mirror JS MotionScheduler.

    add(motion): validate, check priority, interrupt lower, push active.
    update(now): tick all active motions, apply easing, blend by target key.
    interrupt_lower(priority, target_key): drop interruptible motions có
        priority thấp hơn.
    clear(): reset (state change / disconnect).
    """

    def __init__(self) -> None:
        self.active: list[dict[str, Any]] = []
        self.queued: list[dict[str, Any]] = []
        self.last_update: float = 0.0
        self._blend_cache: dict[str, dict[str, Any]] = {}

    def add(self, motion: dict[str, Any], *, now_ms: float | None = None) -> bool:
        if not isinstance(motion, dict):
            return False
        # target_key: string (group key); target_value: number (end value)
        target_key = motion.get("target_key") or motion.get("target")
        if target_key is None or motion.get("start") is None:
            return False
        target_value = motion.get("target_value")
        if target_value is None:
            target_value = motion.get("end", 0)
        if not motion.get("duration") or motion["duration"] <= 0:
            return False
        m = {
            "priority": PRIORITY["IDLE"],
            "interruptible": True,
            "additive": False,
            "easing": "ease-out",
            "startTime": 0.0,
            "progress": 0.0,
            "target": target_key,
            "target_value": target_value,
            **motion,
        }
        if not m["startTime"]:
            m["startTime"] = now_ms if now_ms is not None else time.time() * 1000.0
        self.interrupt_lower(m["priority"], m["target"])
        self.active.append(m)
        return True

    def interrupt_lower(self, priority: int, target_key: str | None) -> None:
        for i in range(len(self.active) - 1, -1, -1):
            m = self.active[i]
            if not m.get("interruptible", True):
                continue
            if m["priority"] < priority:
                if target_key is None or m["target"] == target_key or m["priority"] < priority - 10:
                    self.active.pop(i)

    def update(self, now: float | None = None) -> dict[str, dict[str, Any]]:
        if now is None:
            now = time.time() * 1000.0
        self._blend_cache = {}
        for i in range(len(self.active) - 1, -1, -1):
            m = self.active[i]
            m["progress"] = min(1.0, (now - m["startTime"]) / m["duration"])
            eased = _apply_easing(m["progress"], m["easing"])
            value = _interpolate(m["start"], m["target_value"], eased)
            key = m["target"]
            existing = self._blend_cache.get(key)
            if existing is None or m["priority"] > existing["priority"]:
                self._blend_cache[key] = {"value": value, "priority": m["priority"], "motion": m}
            elif (m["priority"] == existing["priority"] and m.get("additive") and
                  isinstance(value, (int, float)) and isinstance(existing["value"], (int, float))):
                existing["value"] = existing["value"] + (value - m["start"])
            if m["progress"] >= 1.0:
                cb = m.get("onComplete")
                if callable(cb):
                    try:
                        cb()
                    except Exception:
                        pass
                self.active.pop(i)
        return self._blend_cache

    def clear(self) -> None:
        self.active.clear()
        self.queued.clear()
        self._blend_cache = {}

    def size(self) -> int:
        return len(self.active)


# ===== Gesture Library (design §5) — 10 gestures =====
GESTURE_LIBRARY: dict[str, dict[str, Any]] = {
    "greeting": {
        "motions": [
            {"target": "head.tilt", "start": 0, "target": 5, "duration": 500,
             "easing": "ease-out", "priority": PRIORITY["EMOTION"]},
            {"target": "eye.contact", "start": 0, "target": 1, "duration": 300,
             "easing": "ease-out", "priority": PRIORITY["EMOTION"]},
            {"target": "mouth.smile", "start": 0, "target": 0.5, "duration": 400,
             "easing": "ease-out", "priority": PRIORITY["EMOTION"]},
        ],
        "priority": PRIORITY["EMOTION"],
        "context": "user_greeting",
    },
    "listening": {
        "motions": [
            {"target": "eye.contact", "start": 0, "target": 1, "duration": 200,
             "easing": "ease-out", "priority": PRIORITY["LISTENING"]},
            {"target": "head.nod", "start": 0, "target": 2, "duration": 500,
             "easing": "ease-in-out", "priority": PRIORITY["LISTENING"], "repeat": True},
        ],
        "priority": PRIORITY["LISTENING"],
        "context": "user_speaking",
    },
    "thinking": {
        "motions": [
            {"target": "eye.saccade", "start": 0, "target": 0.3, "duration": 800,
             "easing": "ease-in-out", "priority": PRIORITY["THINKING"]},
            {"target": "head.tilt", "start": 0, "target": 8, "duration": 600,
             "easing": "ease-out", "priority": PRIORITY["THINKING"]},
        ],
        "priority": PRIORITY["THINKING"],
        "context": "processing",
    },
    "curious": {
        "motions": [
            {"target": "head.tilt", "start": 0, "target": 10, "duration": 700,
             "easing": "ease-out", "priority": PRIORITY["EMOTION"]},
            {"target": "eye.gaze", "start": 0, "target": 0.6, "duration": 500,
             "easing": "ease-in-out", "priority": PRIORITY["EMOTION"]},
        ],
        "priority": PRIORITY["EMOTION"],
        "context": "curious",
    },
    "empathic": {
        "motions": [
            {"target": "head.tilt", "start": 0, "target": 3, "duration": 800,
             "easing": "ease-in-out", "priority": PRIORITY["EMOTION"]},
            {"target": "eye.contact", "start": 0, "target": 0.8, "duration": 600,
             "easing": "ease-out", "priority": PRIORITY["EMOTION"]},
        ],
        "priority": PRIORITY["EMOTION"],
        "context": "empathic",
    },
    "emphatic": {
        "motions": [
            {"target": "head.nod", "start": 0, "target": 4, "duration": 400,
             "easing": "ease-out", "priority": PRIORITY["EMOTION"]},
            {"target": "mouth.smile", "start": 0, "target": 0.7, "duration": 500,
             "easing": "ease-out", "priority": PRIORITY["EMOTION"]},
        ],
        "priority": PRIORITY["EMOTION"],
        "context": "emphatic",
    },
    "acknowledging": {
        "motions": [
            {"target": "head.nod", "start": 0, "target": 3, "duration": 350,
             "easing": "ease-out", "priority": PRIORITY["LISTENING"]},
        ],
        "priority": PRIORITY["LISTENING"],
        "context": "acknowledging",
    },
    "considering": {
        "motions": [
            {"target": "head.tilt", "start": 0, "target": 6, "duration": 900,
             "easing": "ease-in-out", "priority": PRIORITY["THINKING"]},
            {"target": "eye.saccade", "start": 0, "target": 0.4, "duration": 700,
             "easing": "ease-in-out", "priority": PRIORITY["THINKING"]},
        ],
        "priority": PRIORITY["THINKING"],
        "context": "considering",
    },
    "responding": {
        "motions": [
            {"target": "head.tilt", "start": 0, "target": 2, "duration": 300,
             "easing": "ease-out", "priority": PRIORITY["SPEAKING"]},
            {"target": "mouth.smile", "start": 0, "target": 0.3, "duration": 400,
             "easing": "ease-out", "priority": PRIORITY["SPEAKING"]},
        ],
        "priority": PRIORITY["SPEAKING"],
        "context": "responding",
    },
    "closing": {
        "motions": [
            {"target": "head.tilt", "start": 0, "target": 0, "duration": 500,
             "easing": "ease-in-out", "priority": PRIORITY["EMOTION"]},
            {"target": "eye.contact", "start": 0, "target": 0.5, "duration": 400,
             "easing": "ease-out", "priority": PRIORITY["EMOTION"]},
        ],
        "priority": PRIORITY["EMOTION"],
        "context": "closing",
    },
}


def select_gesture(context: str, last_name: str | None = None) -> dict[str, Any] | None:
    """Random selection trong candidates có context khớp, tránh lặp lại."""
    candidates = [
        name for name, g in GESTURE_LIBRARY.items() if g["context"] == context
    ]
    if not candidates:
        return None
    pool = candidates
    if last_name and len(candidates) > 1:
        pool = [n for n in candidates if n != last_name]
    pick = random.choice(pool)
    return {"name": pick, "gesture": GESTURE_LIBRARY[pick]}
