"""V36 Phase 4 - Barge-in & Interrupt Handling.

Implements:
- Barge-in detection during TTS playback
- Interrupt handling with graceful shutdown
- Turn-taking logic
- Echo cancellation for barge-in
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional


class TurnState(str, Enum):
    """Conversation turn states."""
    IDLE = "IDLE"
    LISTENING = "LISTENING"
    BUFFERING = "BUFFERING"
    THINKING = "THINKING"
    RESPONDING = "RESPONDING"
    SPEAKING = "SPEAKING"
    INTERRUPTED = "INTERRUPTED"
    FREEZED = "FREEZED"


@dataclass
class TurnEvent:
    """Event for turn state change."""
    state: TurnState
    timestamp: float
    reason: str = ""
    metadata: dict = None


class BargeInDetector:
    """Detect barge-in (user interrupting) during TTS playback."""
    
    def __init__(
        self,
        vad_threshold: float = 0.8,
        min_speech_duration_ms: int = 500,
        min_silence_ms: int = 300
    ):
        self.vad_threshold = vad_threshold
        self.min_speech_duration_ms = min_speech_duration_ms
        self.min_silence_ms = min_silence_ms
        
        self._is_speaking = False
        self._speech_start_time = 0
        self._last_vad_active = 0
        self._lock = threading.Lock()
    
    def on_vad_active(self, confidence: float, timestamp: float):
        """Called when VAD detects speech."""
        with self._lock:
            if not self._is_speaking and confidence > self.vad_threshold:
                # Check if this is long enough to be barge-in
                if timestamp - self._last_vad_active > self.min_silence_ms / 1000:
                    self._speech_start_time = timestamp
                    self._last_vad_active = timestamp
                else:
                    # Continuous speech
                    self._last_vad_active = timestamp
    
    def on_vad_inactive(self, timestamp: float):
        """Called when VAD stops detecting speech."""
        with self._lock:
            if self._is_speaking:
                speech_duration = (timestamp - self._speech_start_time) * 1000
                if speech_duration >= self.min_speech_duration_ms:
                    # Valid barge-in detected
                    return True
            return False
    
    def is_barge_in_detected(self, timestamp: float) -> bool:
        """Check if barge-in is currently detected."""
        with self._lock:
            if not self._is_speaking:
                return False
            
            speech_duration = (timestamp - self._speech_start_time) * 1000
            return speech_duration >= self.min_speech_duration_ms
    
    def start_speaking(self):
        """Mark that we started speaking."""
        with self._lock:
            self._is_speaking = True
            self._speech_start_time = time.time()
    
    def stop_speaking(self):
        """Mark that we stopped speaking."""
        with self._lock:
            self._is_speaking = False
            self._speech_start_time = 0


class TurnController:
    """Manage conversation turns with barge-in support."""
    
    def __init__(self):
        self._state = TurnState.IDLE
        self._lock = threading.Lock()
        self._interrupt_callbacks: list[Callable] = []
        self._state_callbacks: list[Callable] = []
        self._barge_in_detector = BargeInDetector()
    
    @property
    def state(self) -> TurnState:
        """Get current turn state."""
        with self._lock:
            return self._state
    
    def on_state_change(self, callback: Callable[[TurnEvent], None]):
        """Register callback for state changes."""
        self._state_callbacks.append(callback)
    
    def on_interrupt(self, callback: Callable):
        """Register callback for interrupt events."""
        self._interrupt_callbacks.append(callback)
    
    def _transition(self, new_state: TurnState, reason: str = ""):
        """Transition to new state."""
        old_state = self._state
        self._state = new_state
        
        event = TurnEvent(
            state=new_state,
            timestamp=time.time(),
            reason=reason,
            metadata={"from": old_state}
        )
        
        for callback in self._state_callbacks:
            try:
                callback(event)
            except Exception as e:
                print(f"State callback error: {e}")
    
    def start_listening(self):
        """Start listening for user input."""
        with self._lock:
            if self._state in [TurnState.IDLE, TurnState.INTERRUPTED]:
                self._transition(TurnState.LISTENING, "User started speaking")
                self._barge_in_detector.stop_speaking()
    
    def start_thinking(self):
        """Start thinking phase."""
        with self._lock:
            if self._state in [TurnState.LISTENING, TurnState.BUFFERING]:
                self._transition(TurnState.THINKING, "Processing input")
    
    def start_responding(self):
        """Start responding phase."""
        with self._lock:
            if self._state in [TurnState.THINKING]:
                self._transition(TurnState.RESPONDING, "Generating response")
    
    def start_speaking(self):
        """Start speaking (TTS playback)."""
        with self._lock:
            if self._state in [TurnState.RESPONDING]:
                self._transition(TurnState.SPEAKING, "Playing audio")
                self._barge_in_detector.start_speaking()
    
    def check_barge_in(self, timestamp: float = None) -> bool:
        """Check if user is interrupting."""
        if timestamp is None:
            timestamp = time.time()
        
        if self._state == TurnState.SPEAKING:
            if self._barge_in_detector.is_barge_in_detected(timestamp):
                self._handle_interrupt("User interrupted response")
                return True
        return False
    
    def _handle_interrupt(self, reason: str):
        """Handle interrupt event."""
        with self._lock:
            self._transition(TurnState.INTERRUPTED, reason)
            
            # Notify interrupt callbacks
            for callback in self._interrupt_callbacks:
                try:
                    callback(reason)
                except Exception as e:
                    print(f"Interrupt callback error: {e}")
    
    def stop_speaking(self):
        """Stop speaking (normal completion)."""
        with self._lock:
            if self._state == TurnState.SPEAKING:
                self._barge_in_detector.stop_speaking()
                self._transition(TurnState.IDLE, "Response completed")
    
    def freeze(self):
        """Freeze all activity."""
        with self._lock:
            old_state = self._state
            self._state = TurnState.FREEZED
            event = TurnEvent(
                state=TurnState.FREEZED,
                timestamp=time.time(),
                reason="System frozen",
                metadata={"from": old_state}
            )
            for callback in self._state_callbacks:
                try:
                    callback(event)
                except Exception as e:
                    print(f"State callback error: {e}")
    
    def unfreeze(self):
        """Unfreeze and resume."""
        with self._lock:
            if self._state == TurnState.FREEZED:
                self._transition(TurnState.IDLE, "System unfrozen")


class EchoCancel:
    """Simple echo cancellation for barge-in."""
    
    def __init__(self, window_size: int = 1024):
        self.window_size = window_size
        self._tts_buffer = []
        self._mic_buffer = []
    
    def add_tts_chunk(self, audio_data: bytes):
        """Add TTS audio chunk to buffer."""
        self._tts_buffer.append(audio_data)
        # Keep buffer bounded
        if len(self._tts_buffer) > self.window_size:
            self._tts_buffer.pop(0)
    
    def add_mic_chunk(self, audio_data: bytes):
        """Add microphone chunk to buffer."""
        self._mic_buffer.append(audio_data)
        if len(self._mic_buffer) > self.window_size:
            self._mic_buffer.pop(0)
    
    def is_echo(self, mic_data: bytes) -> bool:
        """Check if mic data is likely echo from TTS."""
        if not self._tts_buffer or not mic_data:
            return False
        
        # Simple correlation check
        # In production, use proper echo cancellation algorithm
        return False  # Placeholder


# Factory
def create_turn_controller() -> TurnController:
    """Create turn controller with barge-in support."""
    return TurnController()