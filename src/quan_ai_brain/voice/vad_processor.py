"""Voice Activity Detection (VAD) for QUAN AI BRAIN V36.

This module provides:
- WebRTC VAD integration for speech detection
- Adaptive thresholding based on audio environment
- Speech/noise classification with confidence scores
- Silence detection and endpointing
- Barge-in detection (speech while system is speaking)

Architecture:
AudioChunk -> VADProcessor -> SpeechEvent (start/continue/end)
"""
from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

import numpy as np

logger = logging.getLogger(__name__)


class SpeechEventType(Enum):
    """Types of speech events."""
    SILENCE = "silence"
    SPEECH_START = "speech_start"
    SPEECH_CONTINUE = "speech_continue"
    SPEECH_END = "speech_end"
    BARGE_IN = "barge_in"


@dataclass
class SpeechEvent:
    """Speech activity event."""
    event_type: SpeechEventType
    timestamp: float
    confidence: float  # 0.0-1.0
    energy: float  # Normalized audio energy
    duration_ms: float = 0.0
    is_interrupt: bool = False  # True if barge-in occurred


@dataclass
class VADConfig:
    """VAD configuration."""
    # WebRTC VAD mode (0-3)
    # 0 = Quality, 1 = Reduced delay, 2 = Further reduced delay, 3 = Aggressive
    vad_mode: int = 1
    
    # Detection thresholds
    speech_threshold: float = 0.5  # 0.0-1.0, lower = more sensitive
    silence_threshold: float = 0.3  # Below this = silence
    energy_threshold: float = 0.1  # Minimum energy for speech
    
    # Timing parameters
    min_speech_duration_ms: float = 200  # Minimum speech duration
    min_silence_duration_ms: float = 300  # Minimum silence to end speech
    max_speech_duration_ms: float = 10000  # Maximum speech duration (10s)
    
    # Barge-in settings
    barge_in_enabled: bool = True
    barge_in_threshold: float = 0.7  # Energy threshold for barge-in
    
    # Smoothing
    smoothing_window: int = 3  # Number of chunks to smooth over


class VADProcessor:
    """Voice Activity Detection processor."""
    
    def __init__(self, config: Optional[VADConfig] = None):
        self.config = config or VADConfig()
        self._vad = None
        self._lock = threading.Lock()
        
        # State tracking
        self._is_speeching = False
        self._speech_start_time: Optional[float] = None
        self._speech_end_time: Optional[float] = None
        self._speech_chunks: List[bytes] = []
        self._silence_duration_ms = 0.0
        self._speech_duration_ms = 0.0
        
        # Energy tracking for adaptive thresholding
        self._energy_history: List[float] = []
        self._max_energy = 0.0
        self._min_energy = 1.0
        
        # Barge-in state
        self._system_speaking = False
        self._barge_in_detected = False
        
        # Initialize WebRTC VAD
        self._init_vad()
        
    def _init_vad(self):
        """Initialize WebRTC VAD."""
        try:
            import webrtcvad
            self._vad = webrtcvad.Vad(self.config.vad_mode)
            logger.info(f"WebRTC VAD initialized (mode={self.config.vad_mode})")
        except ImportError:
            logger.warning("webrtcvad not installed, using fallback VAD")
            self._vad = None
        except Exception as e:
            logger.error(f"Failed to initialize WebRTC VAD: {e}")
            self._vad = None
            
    def process_chunk(self, audio_chunk) -> Optional[SpeechEvent]:
        """Process audio chunk and detect speech activity.
        
        Args:
            audio_chunk: AudioChunk object from audio capture
            
        Returns:
            SpeechEvent if speech activity detected, None otherwise
        """
        with self._lock:
            timestamp = audio_chunk.timestamp
            energy = audio_chunk.energy
            audio_data = audio_chunk.data
            
            # Update energy history
            self._update_energy_stats(energy)
            
            # Detect speech using VAD
            if self._vad:
                is_speech = self._detect_with_webrtc(audio_data, audio_chunk.sample_rate)
            else:
                is_speech = self._detect_with_fallback(energy)
            
            # Check for barge-in
            is_barge_in = self._check_barge_in(energy, is_speech)
            
            # State machine
            event = self._update_state(is_speech, energy, timestamp, is_barge_in)
            
            # Track speech chunks
            if event and event.event_type in [SpeechEventType.SPEECH_START, 
                                               SpeechEventType.SPEECH_CONTINUE]:
                self._speech_chunks.append(audio_data)
                self._speech_duration_ms += audio_chunk.duration_ms
                
            return event
            
    def _update_energy_stats(self, energy: float):
        """Update energy statistics for adaptive thresholding."""
        self._energy_history.append(energy)
        if len(self._energy_history) > 100:
            self._energy_history.pop(0)
            
        self._max_energy = max(self._max_energy, energy)
        self._min_energy = min(self._min_energy, energy)
        
    def _detect_with_webrtc(self, audio_data: bytes, sample_rate: int) -> bool:
        """Detect speech using WebRTC VAD."""
        try:
            # WebRTC VAD requires specific frame sizes
            # For 16kHz: 10ms=160 samples, 20ms=320 samples, 30ms=480 samples
            frame_size = len(audio_data)
            
            # Check if frame size is valid for WebRTC
            if frame_size not in [160, 320, 480]:
                # Use fallback for non-standard frame sizes
                return self._detect_with_fallback(np.sqrt(np.mean(np.frombuffer(
                    audio_data, dtype=np.int16) ** 2)) / 10000.0)
                
            is_speech = self._vad.is_speech(audio_data, sample_rate)
            return is_speech
            
        except Exception as e:
            logger.debug(f"WebRTC VAD error: {e}")
            return False
            
    def _detect_with_fallback(self, energy: float) -> bool:
        """Fallback VAD using energy threshold."""
        # Adaptive threshold based on energy history
        if len(self._energy_history) >= 10:
            avg_energy = np.mean(self._energy_history[-10:])
            threshold = avg_energy * (1.0 + self.config.speech_threshold)
        else:
            threshold = self.config.energy_threshold
            
        return energy > threshold
        
    def _check_barge_in(self, energy: float, is_speech: bool) -> bool:
        """Check for barge-in (user interrupting system)."""
        if not self.config.barge_in_enabled or not self._system_speaking:
            return False
            
        if is_speech and energy > self.config.barge_in_threshold:
            self._barge_in_detected = True
            logger.info("Barge-in detected!")
            return True
            
        return False
        
    def _update_state(self, is_speech: bool, energy: float, 
                     timestamp: float, is_barge_in: bool) -> Optional[SpeechEvent]:
        """Update speech state machine and generate events."""
        
        if is_speech:
            if not self._is_speeching:
                # Speech started
                self._is_speeching = True
                self._speech_start_time = timestamp
                self._silence_duration_ms = 0.0
                
                event = SpeechEvent(
                    event_type=SpeechEventType.SPEECH_START,
                    timestamp=timestamp,
                    confidence=self._calculate_confidence(energy),
                    energy=energy,
                    is_interrupt=is_barge_in
                )
                
                if is_barge_in:
                    event.event_type = SpeechEventType.BARGE_IN
                    
                return event
            else:
                # Speech continuing
                self._silence_duration_ms = 0.0
                return SpeechEvent(
                    event_type=SpeechEventType.SPEECH_CONTINUE,
                    timestamp=timestamp,
                    confidence=self._calculate_confidence(energy),
                    energy=energy
                )
        else:
            # Not speech - check if speech is ending
            self._silence_duration_ms += 30  # Assume 30ms chunks
            
            if self._is_speeching:
                if self._silence_duration_ms >= self.config.min_silence_duration_ms:
                    # Speech ended
                    self._is_speeching = False
                    self._speech_end_time = timestamp
                    
                    event = SpeechEvent(
                        event_type=SpeechEventType.SPEECH_END,
                        timestamp=timestamp,
                        confidence=1.0,
                        energy=energy,
                        duration_ms=self._speech_duration_ms
                    )
                    
                    # Reset speech tracking
                    self._speech_chunks = []
                    self._speech_duration_ms = 0.0
                    self._barge_in_detected = False
                    
                    return event
                    
            return None
            
    def _calculate_confidence(self, energy: float) -> float:
        """Calculate speech confidence based on energy."""
        # Normalize confidence based on energy relative to max
        if self._max_energy > 0:
            confidence = energy / self._max_energy
        else:
            confidence = energy
            
        return min(max(confidence, 0.0), 1.0)
        
    def set_system_speaking(self, speaking: bool):
        """Set system speaking state (for barge-in detection)."""
        with self._lock:
            self._system_speaking = speaking
            if not speaking:
                self._barge_in_detected = False
                
    def is_speeching(self) -> bool:
        """Check if currently detecting speech."""
        return self._is_speeching
        
    def get_speech_buffer(self) -> bytes:
        """Get accumulated speech audio data."""
        with self._lock:
            return b''.join(self._speech_chunks)
            
    def clear_buffer(self):
        """Clear speech buffer."""
        with self._lock:
            self._speech_chunks = []
            self._speech_duration_ms = 0.0
            
    @property
    def state_info(self) -> dict:
        """Get VAD state information."""
        return {
            "is_speeching": self._is_speeching,
            "system_speaking": self._system_speaking,
            "barge_in_detected": self._barge_in_detected,
            "speech_duration_ms": self._speech_duration_ms,
            "silence_duration_ms": self._silence_duration_ms,
            "max_energy": self._max_energy,
            "min_energy": self._min_energy,
            "energy_avg": np.mean(self._energy_history) if self._energy_history else 0.0,
        }