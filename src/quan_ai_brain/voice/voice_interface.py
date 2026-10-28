"""
Voice Interface (V24.3) - QUAN AI BRAIN.

SIMULATED: speech I/O via in-memory MockASR / MockTTS implementing the
ASRInterface/TTSInterface contracts. No microphone, no audio files, no
network, no PyAudio/Cloud STT as sketched in the V24 plan.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set


class VoiceState(str, Enum):
    """Voice session states: idle -> listening -> transcribing -> responding."""
    IDLE = "idle"
    LISTENING = "listening"
    TRANSCRIBING = "transcribing"
    RESPONDING = "responding"


VALID_TRANSITIONS: Dict[VoiceState, Set[VoiceState]] = {
    VoiceState.IDLE: {VoiceState.LISTENING},
    VoiceState.LISTENING: {VoiceState.TRANSCRIBING, VoiceState.IDLE},
    VoiceState.TRANSCRIBING: {VoiceState.RESPONDING, VoiceState.IDLE},
    VoiceState.RESPONDING: {VoiceState.IDLE},
}


# ---------------------------------------------------------------------------
# ASR / TTS interfaces + mocks (simulated)
# ---------------------------------------------------------------------------

class ASRError(Exception):
    """Raised when the (mock) ASR cannot produce a transcript."""


class TTSError(Exception):
    """Raised when the (mock) TTS cannot speak."""


class ASRInterface:
    """Abstract speech-to-text interface."""

    def start_listening(self) -> None:
        raise NotImplementedError

    def stop_listening(self) -> None:
        raise NotImplementedError

    def transcribe(self, audio: Any = None) -> str:
        raise NotImplementedError


class TTSInterface:
    """Abstract text-to-speech interface."""

    def speak(self, text: str) -> str:
        raise NotImplementedError

    def stop(self) -> None:
        raise NotImplementedError


@dataclass
class MockASR(ASRInterface):
    """In-memory ASR stub: replays a scripted transcript; optionally fails.

    SIMULATED speech recognition - no audio, just scripted strings.
    """
    script: List[str] = field(default_factory=list)
    fail: bool = False
    is_listening: bool = False
    _cursor: int = 0

    def start_listening(self) -> None:
        self.is_listening = True

    def stop_listening(self) -> None:
        self.is_listening = False

    def transcribe(self, audio: Any = None) -> str:
        if self.fail:
            raise ASRError("simulated ASR failure")
        if self._cursor >= len(self.script):
            raise ASRError("no more scripted audio")
        text = self.script[self._cursor]
        self._cursor += 1
        return text


@dataclass
class MockTTS(TTSInterface):
    """In-memory TTS stub: records spoken lines instead of playing audio.

    SIMULATED speech synthesis - lines are captured in `spoken`.
    """
    spoken: List[str] = field(default_factory=list)
    speaking: bool = False

    def speak(self, text: str) -> str:
        self.speaking = True
        self.spoken.append(text)
        return text

    def stop(self) -> None:
        self.speaking = False


# ---------------------------------------------------------------------------
# Session / turn results
# ---------------------------------------------------------------------------

@dataclass
class VoiceTurn:
    """One listen->respond cycle within a session."""
    transcript: str = ""
    response: str = ""
    interrupted: bool = False
    started_at: Optional[float] = None
    ended_at: Optional[float] = None

    @property
    def duration(self) -> Optional[float]:
        if self.started_at is None or self.ended_at is None:
            return None
        return self.ended_at - self.started_at


@dataclass
class VoiceSessionResult:
    """Aggregate result of a full voice session."""
    turns: List[VoiceTurn] = field(default_factory=list)
    barge_in_count: int = 0
    timeouts: int = 0
    errors: List[str] = field(default_factory=list)
    ended_reason: str = "completed"


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class VoiceInterface:
    """Deterministic (non-threaded) voice session state machine.

    State flow: IDLE -> LISTENING -> TRANSCRIBING -> RESPONDING -> IDLE.
    - timeout: max seconds for LISTENING before auto-return to IDLE
      (checked with an injectable clock - no real sleeps in tests).
    - barge-in: user speech cancels the pending/in-progress response;
      call barge_in() from TRANSCRIBING/RESPONDING, or pass
      interrupt_during_speech=True to respond() to simulate mid-speech
      interruption deterministically.
    - Multiple turns per session: use next_turn() between utterances.
    """

    def __init__(self, asr: ASRInterface, tts: TTSInterface,
                 timeout: float = 5.0,
                 clock: Optional[Callable[[], float]] = None) -> None:
        self.asr = asr
        self.tts = tts
        self.timeout = timeout
        self._clock = clock or time.monotonic
        self.state: VoiceState = VoiceState.IDLE
        self.turns: List[VoiceTurn] = []
        self.barge_in_count = 0
        self.timeouts = 0
        self.errors: List[str] = []
        self._interrupt_requested = False
        self._listen_started: Optional[float] = None

    # -- state machine core --------------------------------------------------

    def _transition(self, new_state: VoiceState) -> None:
        if new_state not in VALID_TRANSITIONS[self.state]:
            raise RuntimeError(
                f"invalid transition {self.state.value} -> {new_state.value}")
        self.state = new_state

    # -- session control ------------------------------------------------------

    def start_session(self) -> None:
        """IDLE -> LISTENING. Starts a new turn and resets session counters."""
        if self.state is not VoiceState.IDLE:
            raise RuntimeError("session already active")
        self.turns = []
        self.barge_in_count = 0
        self.timeouts = 0
        self.errors = []
        self._interrupt_requested = False
        self._listen_started = None
        self._transition(VoiceState.LISTENING)
        self.asr.start_listening()
        self._listen_started = self._clock()
        self.turns.append(VoiceTurn(started_at=self._clock()))

    def end_session(self) -> VoiceSessionResult:
        """Any state -> IDLE; returns the session summary."""
        self.asr.stop_listening()
        self.tts.stop()
        if self.timeouts:
            reason = "timeout"
        elif any(t.interrupted for t in self.turns):
            reason = "barge_in"
        else:
            reason = "completed"
        result = VoiceSessionResult(
            turns=list(self.turns),
            barge_in_count=self.barge_in_count,
            timeouts=self.timeouts,
            errors=list(self.errors),
            ended_reason=reason,
        )
        self.state = VoiceState.IDLE
        return result

    # -- listening ------------------------------------------------------------

    def listen(self) -> bool:
        """Poll LISTENING state; False => timeout elapsed (back to IDLE)."""
        if self.state is not VoiceState.LISTENING:
            raise RuntimeError("listen() called outside LISTENING state")
        if self._listen_started is None:
            self._listen_started = self._clock()
        if self._clock() - self._listen_started > self.timeout:
            self.timeouts += 1
            self.asr.stop_listening()
            self.state = VoiceState.IDLE
            return False
        return True

    # -- transcribe + respond --------------------------------------------------

    def transcribe(self) -> str:
        """LISTENING -> TRANSCRIBING; returns text via the ASR mock."""
        self._transition(VoiceState.TRANSCRIBING)
        try:
            text = self.asr.transcribe()
        except ASRError:
            self.errors.append("asr_error")
            self.state = VoiceState.IDLE
            raise
        self.turns[-1].transcript = text
        return text

    def respond(self, text: str,
                interrupt_during_speech: bool = False) -> VoiceTurn:
        """TRANSCRIBING -> RESPONDING -> IDLE; speaks via the TTS mock.

        interrupt_during_speech=True deterministically simulates the user
        starting to talk mid-response (barge-in) - no threads needed.
        """
        if self.state is not VoiceState.TRANSCRIBING:
            raise RuntimeError("respond() called outside TRANSCRIBING state")
        turn = self.turns[-1]
        self._transition(VoiceState.RESPONDING)
        interrupted = self._interrupt_requested or interrupt_during_speech
        if not interrupted:
            turn.response = self.tts.speak(text.upper())
        turn.interrupted = interrupted
        turn.ended_at = self._clock()
        if interrupted:
            self.barge_in_count += 1
            self.tts.stop()
        self._interrupt_requested = False
        self.state = VoiceState.IDLE
        return turn

    # -- barge-in --------------------------------------------------------------

    def barge_in(self) -> bool:
        """External speech detected: cancel the current response.

        Works from TRANSCRIBING (before TTS starts) or RESPONDING
        (mid-speech). Returns True when the response was cancelled.
        """
        if self.state in (VoiceState.TRANSCRIBING, VoiceState.RESPONDING):
            self._interrupt_requested = True
            self.tts.stop()
            return True
        return False

    # -- multi-turn convenience ---------------------------------------------------

    def next_turn(self) -> None:
        """Start a new turn inside the running session (IDLE -> LISTENING)."""
        if self.state is not VoiceState.IDLE:
            raise RuntimeError(
                "next_turn() requires IDLE state inside an active session")
        self._interrupt_requested = False
        self._listen_started = None
        self.state = VoiceState.LISTENING
        self.asr.start_listening()
        self._listen_started = self._clock()
        self.turns.append(VoiceTurn(started_at=self._clock()))

    def process_utterance(self, text: str,
                          interrupt_during_speech: bool = False) -> VoiceTurn:
        """Drive one full turn with a supplied transcript (test convenience)."""
        self.start_session()
        try:
            self.transcribe()
            turn = self.respond(text,
                                interrupt_during_speech=interrupt_during_speech)
        except ASRError:
            self.end_session()
            raise
        return turn
