"""Formal Voice State Machine for Hands-Free Interaction."""
from __future__ import annotations

from enum import Enum
import time
from typing import Any


class VoiceState(str, Enum):
    DISABLED = "DISABLED"
    STANDBY = "STANDBY"
    WAKE_DETECTED = "WAKE_DETECTED"
    LISTENING = "LISTENING"
    TRANSCRIBING = "TRANSCRIBING"
    THINKING = "THINKING"
    SPEAKING = "SPEAKING"
    INTERRUPTED = "INTERRUPTED"
    ERROR = "ERROR"


VALID_TRANSITIONS: dict[VoiceState, set[VoiceState]] = {
    VoiceState.DISABLED: {VoiceState.STANDBY, VoiceState.ERROR},
    VoiceState.STANDBY: {VoiceState.WAKE_DETECTED, VoiceState.DISABLED, VoiceState.ERROR},
    VoiceState.WAKE_DETECTED: {VoiceState.LISTENING, VoiceState.STANDBY, VoiceState.ERROR},
    VoiceState.LISTENING: {VoiceState.TRANSCRIBING, VoiceState.STANDBY, VoiceState.INTERRUPTED, VoiceState.ERROR},
    VoiceState.TRANSCRIBING: {VoiceState.THINKING, VoiceState.STANDBY, VoiceState.ERROR},
    VoiceState.THINKING: {VoiceState.SPEAKING, VoiceState.INTERRUPTED, VoiceState.ERROR},
    VoiceState.SPEAKING: {VoiceState.LISTENING, VoiceState.STANDBY, VoiceState.INTERRUPTED, VoiceState.ERROR},
    VoiceState.INTERRUPTED: {VoiceState.STANDBY, VoiceState.LISTENING, VoiceState.DISABLED},
    VoiceState.ERROR: {VoiceState.DISABLED, VoiceState.STANDBY},
}


class VoiceStateMachine:
    """Thread-safe state machine governing voice interaction transitions."""

    def __init__(self, initial_state: VoiceState = VoiceState.DISABLED) -> None:
        self.current_state = initial_state
        self.history: list[dict[str, Any]] = []

    def transition_to(self, new_state: VoiceState, reason: str = "") -> bool:
        allowed = VALID_TRANSITIONS.get(self.current_state, set())
        if new_state not in allowed:
            return False
        old_state = self.current_state
        self.current_state = new_state
        self.history.append({
            "from": old_state.value,
            "to": new_state.value,
            "reason": reason,
            "timestamp": time.time(),
        })
        return True

    def reset(self, to_state: VoiceState = VoiceState.DISABLED) -> None:
        self.current_state = to_state
