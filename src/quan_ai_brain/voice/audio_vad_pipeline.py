"""Integrated Audio Capture & VAD Pipeline for QUAN AI BRAIN V36.

This module combines audio capture and VAD into a unified pipeline:
- Real-time microphone capture
- Voice Activity Detection
- Speech event handling
- Barge-in support
- Callback-based event streaming

Usage:
    pipeline = AudioVADPipeline()
    pipeline.start(on_speech_event=handle_event)
    # ... audio processing happens automatically ...
    pipeline.stop()
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, Optional

from .audio_capture import AudioCapture, AudioConfig, AudioChunk
from .vad_processor import VADProcessor, VADConfig, SpeechEvent, SpeechEventType

logger = logging.getLogger(__name__)


@dataclass
class AudioVADConfig:
    """Combined audio and VAD configuration."""
    audio: AudioConfig = None
    vad: VADConfig = None
    
    def __post_init__(self):
        if self.audio is None:
            self.audio = AudioConfig()
        if self.vad is None:
            self.vad = VADConfig()


class AudioVADPipeline:
    """Integrated audio capture and VAD pipeline."""
    
    def __init__(self, config: Optional[AudioVADConfig] = None):
        self.config = config or AudioVADConfig()
        self._audio_capture = AudioCapture(self.config.audio)
        self._vad_processor = VADProcessor(self.config.vad)
        
        # Event callbacks
        self._on_speech_start: Optional[Callable[[SpeechEvent], None]] = None
        self._on_speech_continue: Optional[Callable[[SpeechEvent], None]] = None
        self._on_speech_end: Optional[Callable[[SpeechEvent], None]] = None
        self._on_barge_in: Optional[Callable[[SpeechEvent], None]] = None
        
        # State
        self._is_running = False
        
    def start(self,
              on_speech_start: Optional[Callable[[SpeechEvent], None]] = None,
              on_speech_continue: Optional[Callable[[SpeechEvent], None]] = None,
              on_speech_end: Optional[Callable[[SpeechEvent], None]] = None,
              on_barge_in: Optional[Callable[[SpeechEvent], None]] = None) -> bool:
        """Start audio capture and VAD processing.
        
        Args:
            on_speech_start: Callback when speech starts
            on_speech_continue: Callback for ongoing speech
            on_speech_end: Callback when speech ends
            on_barge_in: Callback when barge-in detected
            
        Returns:
            True if started successfully
        """
        if self._is_running:
            logger.warning("Pipeline already running")
            return False
            
        # Set callbacks
        self._on_speech_start = on_speech_start
        self._on_speech_continue = on_speech_continue
        self._on_speech_end = on_speech_end
        self._on_barge_in = on_barge_in
        
        # Start audio capture with callback
        def audio_callback(chunk: AudioChunk):
            self._process_audio_chunk(chunk)
            
        if not self._audio_capture.start(callback=audio_callback):
            logger.error("Failed to start audio capture")
            return False
            
        self._is_running = True
        logger.info("AudioVAD pipeline started")
        return True
        
    def stop(self) -> bool:
        """Stop audio capture and VAD processing."""
        if not self._is_running:
            logger.warning("Pipeline not running")
            return False
            
        self._audio_capture.stop()
        self._is_running = False
        logger.info("AudioVAD pipeline stopped")
        return True
        
    def _process_audio_chunk(self, chunk: AudioChunk):
        """Process audio chunk through VAD."""
        event = self._vad_processor.process_chunk(chunk)
        
        if event is None:
            return
            
        # Dispatch to appropriate callback
        if event.event_type == SpeechEventType.SPEECH_START:
            logger.debug(f"Speech started (confidence={event.confidence:.2f})")
            if self._on_speech_start:
                self._on_speech_start(event)
                
        elif event.event_type == SpeechEventType.SPEECH_CONTINUE:
            if self._on_speech_continue:
                self._on_speech_continue(event)
                
        elif event.event_type == SpeechEventType.SPEECH_END:
            logger.debug(f"Speech ended (duration={event.duration_ms:.0f}ms)")
            if self._on_speech_end:
                self._on_speech_end(event)
                
        elif event.event_type == SpeechEventType.BARGE_IN:
            logger.info("Barge-in detected!")
            if self._on_barge_in:
                self._on_barge_in(event)
                
    def set_system_speaking(self, speaking: bool):
        """Set system speaking state for barge-in detection."""
        self._vad_processor.set_system_speaking(speaking)
        
    def get_speech_buffer(self) -> bytes:
        """Get accumulated speech audio data."""
        return self._vad_processor.get_speech_buffer()
        
    def clear_speech_buffer(self):
        """Clear speech buffer."""
        self._vad_processor.clear_buffer()
        
    @property
    def is_running(self) -> bool:
        """Check if pipeline is running."""
        return self._is_running
        
    @property
    def is_speeching(self) -> bool:
        """Check if currently detecting speech."""
        return self._vad_processor.is_speeching()
        
    @property
    def audio_state(self) -> dict:
        """Get audio capture state."""
        return self._audio_capture.state_info
        
    @property
    def vad_state(self) -> dict:
        """Get VAD state."""
        return self._vad_processor.state_info
        
    @property
    def full_state(self) -> dict:
        """Get complete pipeline state."""
        return {
            "running": self._is_running,
            "speeching": self.is_speeching,
            "audio": self.audio_state,
            "vad": self.vad_state,
        }