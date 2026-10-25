"""Voice and Wake Word subsystem for QUAN AI BRAIN."""
from __future__ import annotations

from quan_ai_brain.voice.state_machine import VoiceState, VoiceStateMachine
from quan_ai_brain.voice.wake_word_config import (
    DEFAULT_WAKE_WORDS,
    WakeWordConfig,
    WakeWordItem,
    WakeWordMatchResult,
    normalize_text,
)

__all__ = [
    "VoiceState",
    "VoiceStateMachine",
    "WakeWordConfig",
    "WakeWordItem",
    "WakeWordMatchResult",
    "DEFAULT_WAKE_WORDS",
    "normalize_text",
]
