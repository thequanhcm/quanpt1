"""Cherry Presence Engine — Sprint 5: Human-Like Interaction (14/11/2026).

Mirror Python của edge_client/presence_engine.js — PresenceEngine +
IDLE_BEHAVIORS + LISTENING_GAZE + EYE_CONTACT_PRESETS + tick + notifyUser*.
Dùng cho test pytest (mock 100%).

Nguồn thiết kế: CHERRY_EMBODIMENT_SPRINT_PLAN.md §7 (Sprint 5).
"""
from __future__ import annotations

import random
import time
from typing import Any, Callable, Dict, List, Optional

__all__ = [
    "VERSION", "IDLE_BEHAVIORS", "LISTENING_GAZE", "EYE_CONTACT_PRESETS",
    "PresenceEngine",
]

VERSION = "s5_1411"


# ===== 1. IDLE_BEHAVIORS =====
IDLE_BEHAVIORS: Dict[str, Dict[str, Any]] = {
    "slow_blink": {"interval_ms": 4000, "duration_ms": 200, "weight": 0.3},
    "gaze_away": {"interval_ms": 8000, "duration_ms": 1500, "weight": 0.2},
    "head_tilt": {"interval_ms": 6000, "duration_ms": 800, "weight": 0.2},
    "breathing": {"interval_ms": 3000, "duration_ms": 1500, "weight": 0.3},
}


# ===== 2. LISTENING_GAZE =====
LISTENING_GAZE: Dict[str, Dict[str, Any]] = {
    "eye_contact": {"gazeX": 0, "gazeY": 0, "weight": 0.7},
    "thinking": {"gazeX": 0, "gazeY": -0.3, "weight": 0.2},
    "processing": {"gazeX": 0.4, "gazeY": 0, "weight": 0.1},
}


# ===== 3. EYE_CONTACT_PRESETS =====
EYE_CONTACT_PRESETS: Dict[str, float] = {
    "IDLE": 0.6,
    "LISTENING": 0.9,
    "THINKING": 0.4,
    "ANALYTICAL_THINKING": 0.5,
    "CURIOUS": 0.8,
    "WARM_GREETING": 0.9,
    "HAPPY": 0.8,
    "PROUD": 0.7,
    "CONFIDENT_SUCCESS": 0.7,
    "SURPRISED": 0.9,
    "WARNING": 0.8,
    "SERIOUS_ALERT": 0.9,
    "APOLOGETIC": 0.5,
    "EMPATHETIC": 0.8,
    "CONSULTATIVE_INQUIRING": 0.9,
    "SPEAKING": 0.7,
    "ERROR": 0.6,
    "SLEEPING": 0.0,
    "OFFLINE": 0.0,
    "RECONNECTING": 0.5,
    "NEUTRAL": 0.6,
}


def _pick_idle_behavior(rng: Callable[[], float]) -> str:
    behaviors = list(IDLE_BEHAVIORS.keys())
    total = sum(IDLE_BEHAVIORS[b]["weight"] for b in behaviors)
    r = rng() * total
    cum = 0.0
    for b in behaviors:
        cum += IDLE_BEHAVIORS[b]["weight"]
        if r < cum:
            return b
    return behaviors[-1]


# ===== 4. PresenceEngine =====
class PresenceEngine:
    """Máy trạng thái presence: tick(now) cập nhật gaze + idle + continuity.
    notify_user_speaking/stopped/interrupted đồng bộ với user activity."""

    def __init__(self, now_fn: Optional[Callable[[], float]] = None,
                 rng: Optional[Callable[[], float]] = None):
        self._now_fn = now_fn or (lambda: time.time() * 1000.0)
        self._rng = rng or random.random
        self._state: str = "IDLE"
        self._gaze_x: float = 0.0
        self._gaze_y: float = 0.0
        self._eye_contact: float = EYE_CONTACT_PRESETS["IDLE"]
        self._next_idle_behavior: float = 0.0
        self._current_idle_behavior: Optional[str] = None
        self._idle_behavior_start: float = 0.0
        self._user_speaking: bool = False
        self._last_user_activity: float = 0.0
        self._conversation_turns: int = 0
        self._last_turn_end: float = 0.0
        self._interrupted: bool = False
        self._log: List[Dict[str, Any]] = []
        self._max_log = 32

    def _push_log(self, entry: Dict[str, Any]) -> None:
        self._log.append(entry)
        if len(self._log) > self._max_log:
            self._log.pop(0)

    def get_log(self) -> List[Dict[str, Any]]:
        return list(self._log)

    def get_gaze(self) -> Dict[str, Any]:
        return {"gazeX": self._gaze_x, "gazeY": self._gaze_y,
                "eyeContact": self._eye_contact, "state": self._state}

    def get_conversation_turns(self) -> int:
        return self._conversation_turns

    def set_state(self, state: str) -> None:
        if self._state == state:
            return
        self._state = state
        self._eye_contact = EYE_CONTACT_PRESETS.get(state, 0.6)
        self._push_log({"t": self._now_fn(), "kind": "state", "state": state,
                        "eyeContact": self._eye_contact})

    def notify_user_speaking(self) -> None:
        self._user_speaking = True
        self._last_user_activity = self._now_fn()
        if self._state in ("IDLE", "SLEEPING"):
            self.set_state("LISTENING")
        self._push_log({"t": self._now_fn(), "kind": "user_speaking_start"})

    def notify_user_stopped(self) -> None:
        self._user_speaking = False
        self._last_user_activity = self._now_fn()
        self._conversation_turns += 1
        self._last_turn_end = self._now_fn()
        self._push_log({"t": self._now_fn(), "kind": "user_speaking_end",
                        "turns": self._conversation_turns})

    def notify_interrupted(self) -> None:
        self._interrupted = True
        self._push_log({"t": self._now_fn(), "kind": "interrupted"})

    def tick(self, now_ms: Optional[float] = None) -> Dict[str, Any]:
        now = now_ms if now_ms is not None else self._now_fn()

        # 1. Listening gaze khi user đang nói
        if self._user_speaking:
            r = self._rng()
            if r < 0.7:
                self._gaze_x, self._gaze_y = 0.0, 0.0
            elif r < 0.9:
                self._gaze_x, self._gaze_y = 0.0, -0.3
            else:
                self._gaze_x, self._gaze_y = 0.4, 0.0
            self._eye_contact = EYE_CONTACT_PRESETS["LISTENING"]
            return self.get_gaze()

        # 2. Return-to-idle sau 2s user dừng
        if (not self._user_speaking and self._last_user_activity > 0 and
                (now - self._last_user_activity) > 2000 and self._state == "LISTENING"):
            self.set_state("IDLE")

        # 3. Idle behavior scheduling
        if self._state in ("IDLE", "NEUTRAL"):
            if self._next_idle_behavior == 0:
                self._next_idle_behavior = now + 2000 + self._rng() * 3000
            if now >= self._next_idle_behavior and not self._current_idle_behavior:
                self._current_idle_behavior = _pick_idle_behavior(self._rng)
                self._idle_behavior_start = now
                beh = IDLE_BEHAVIORS[self._current_idle_behavior]
                self._push_log({"t": now, "kind": "idle_start",
                                "behavior": self._current_idle_behavior})
                self._next_idle_behavior = now + beh["interval_ms"]
            if self._current_idle_behavior:
                beh2 = IDLE_BEHAVIORS[self._current_idle_behavior]
                elapsed = now - self._idle_behavior_start
                if elapsed >= beh2["duration_ms"]:
                    self._push_log({"t": now, "kind": "idle_end",
                                    "behavior": self._current_idle_behavior})
                    self._current_idle_behavior = None
                elif self._current_idle_behavior == "gaze_away":
                    import math
                    phase = elapsed / beh2["duration_ms"]
                    self._gaze_x = math.sin(phase * math.pi) * 0.5
                    self._gaze_y = 0.0
                elif self._current_idle_behavior == "head_tilt":
                    import math
                    phase = elapsed / beh2["duration_ms"]
                    self._gaze_y = math.sin(phase * math.pi) * 0.1

        return self.get_gaze()
