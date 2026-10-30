"""Speech-to-Text (ASR) Interface for QUAN AI BRAIN V36.

This module defines the abstract interface for speech recognition providers:
- ASRProvider: Base interface for all ASR backends
- StreamingASRSession: Streaming recognition session
- ASRResult: Recognition result with confidence and timestamps

Supported providers:
- AzureSpeechToText (Phase 2)
- GoogleCloudSpeech (Future)
- WhisperLocal (Future - offline)
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class ASRState(Enum):
    """ASR session states."""
    IDLE = "idle"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    LISTENING = "listening"
    RECOGNIZING = "recognizing"
    RESULT = "result"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class RecognitionType(Enum):
    """Types of speech recognition."""
    SINGLE = "single"  # One-shot recognition
    STREAMING = "streaming"  # Continuous streaming
    DICTATION = "dictation"  # Long-form dictation


@dataclass
class ASRResult:
    """Speech recognition result."""
    text: str
    confidence: float  # 0.0-1.0
    is_final: bool  # True if final result, False if partial
    timestamp_start: float
    timestamp_end: float
    language: str = "vi-VN"
    words: List[Dict[str, Any]] = field(default_factory=list)
    alternatives: List[str] = field(default_factory=list)
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "text": self.text,
            "confidence": self.confidence,
            "is_final": self.is_final,
            "timestamp_start": self.timestamp_start,
            "timestamp_end": self.timestamp_end,
            "language": self.language,
            "words": self.words,
            "alternatives": self.alternatives,
            "error": self.error,
        }


@dataclass
class ASRConfig:
    """ASR configuration."""
    # Provider settings
    provider: str = "azure"  # azure, google, whisper
    language: str = "vi-VN"  # Vietnamese (Vietnam)
    
    # Azure-specific
    azure_subscription_id: Optional[str] = None
    azure_region: Optional[str] = None  # e.g., "southeastasia"
    azure_speech_key: Optional[str] = None
    
    # Google-specific
    google_project_id: Optional[str] = None
    google_credentials_path: Optional[str] = None
    
    # Recognition settings
    recognition_type: RecognitionType = RecognitionType.STREAMING
    profanity_filter: bool = True
    enable_word_time_offsets: bool = True
    enable_automatic_punctuation: bool = True
    max_alternatives: int = 3
    
    # Streaming settings
    sample_rate: int = 16000
    encoding: str = "LINEAR16"  # PCM 16-bit
    chunk_size: int = 480  # 30ms at 16kHz
    interim_results: bool = True  # Return partial results
    
    # Timeout and retry
    connection_timeout: float = 30.0
    request_timeout: float = 60.0
    max_retries: int = 3
    retry_delay: float = 2.0
    
    # Fallback
    fallback_enabled: bool = True
    fallback_provider: Optional[str] = None


class ASRProvider(ABC):
    """Abstract base class for speech-to-text providers."""
    
    def __init__(self, config: ASRConfig):
        self.config = config
        self.state = ASRState.IDLE
        self._session = None
        
    @abstractmethod
    def connect(self) -> bool:
        """Connect to ASR service.
        
        Returns:
            True if connected successfully
        """
        pass
    
    @abstractmethod
    def disconnect(self) -> bool:
        """Disconnect from ASR service.
        
        Returns:
            True if disconnected successfully
        """
        pass
    
    @abstractmethod
    def start_recognition(self, 
                         on_result: Callable[[ASRResult], None]) -> bool:
        """Start speech recognition session.
        
        Args:
            on_result: Callback for recognition results
            
        Returns:
            True if recognition started successfully
        """
        pass
    
    @abstractmethod
    def stop_recognition(self) -> bool:
        """Stop speech recognition session.
        
        Returns:
            True if recognition stopped successfully
        """
        pass
    
    @abstractmethod
    def recognize_audio(self, audio_data: bytes) -> Optional[ASRResult]:
        """Recognize speech from audio data (one-shot).
        
        Args:
            audio_data: Raw audio data (PCM 16-bit)
            
        Returns:
            ASRResult or None if recognition failed
        """
        pass
    
    @abstractmethod
    def recognize_stream(self, audio_chunk: bytes) -> Optional[ASRResult]:
        """Recognize speech from audio stream chunk.
        
        Args:
            audio_chunk: Audio chunk (30ms at 16kHz)
            
        Returns:
            ASRResult (partial or final) or None
        """
        pass
    
    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if connected to ASR service."""
        pass
    
    @property
    @abstractmethod
    def is_recognizing(self) -> bool:
        """Check if currently recognizing speech."""
        pass
    
    def get_state_info(self) -> Dict[str, Any]:
        """Get ASR state information."""
        return {
            "state": self.state.value,
            "is_connected": self.is_connected,
            "is_recognizing": self.is_recognizing,
            "provider": self.config.provider,
            "language": self.config.language,
        }


class MockASRProvider(ASRProvider):
    """Mock ASR provider for testing without cloud services."""
    
    def __init__(self, config: Optional[ASRConfig] = None):
        super().__init__(config or ASRConfig(provider="mock"))
        self._is_listening = False
        self._script: List[str] = []
        self._cursor = 0
        
    def connect(self) -> bool:
        """Mock connection."""
        self.state = ASRState.CONNECTED
        logger.info("Mock ASR connected")
        return True
        
    def disconnect(self) -> bool:
        """Mock disconnection."""
        self.state = ASRState.DISCONNECTED
        logger.info("Mock ASR disconnected")
        return True
        
    def start_recognition(self, 
                         on_result: Callable[[ASRResult], None]) -> bool:
        """Start mock recognition."""
        self._is_listening = True
        self.state = ASRState.LISTENING
        logger.info("Mock ASR recognition started")
        return True
        
    def stop_recognition(self) -> bool:
        """Stop mock recognition."""
        self._is_listening = False
        self.state = ASRState.IDLE
        logger.info("Mock ASR recognition stopped")
        return True
        
    def recognize_audio(self, audio_data: bytes) -> Optional[ASRResult]:
        """Mock one-shot recognition."""
        if not self._script:
            return ASRResult(
                text="",
                confidence=0.0,
                is_final=True,
                timestamp_start=0.0,
                timestamp_end=0.0,
                error="No script provided"
            )
            
        text = self._script[0] if self._script else ""
        return ASRResult(
            text=text,
            confidence=0.95,
            is_final=True,
            timestamp_start=0.0,
            timestamp_end=len(text) * 0.1,  # Rough estimate
            language=self.config.language
        )
        
    def recognize_stream(self, audio_chunk: bytes) -> Optional[ASRResult]:
        """Mock streaming recognition."""
        if not self._is_listening or not self._script:
            return None
            
        if self._cursor >= len(self._script):
            return None
            
        text = self._script[self._cursor]
        self._cursor += 1
        
        is_final = self._cursor >= len(self._script)
        
        return ASRResult(
            text=text,
            confidence=0.95 if is_final else 0.7,
            is_final=is_final,
            timestamp_start=(self._cursor - 1) * 0.3,
            timestamp_end=self._cursor * 0.3,
            language=self.config.language
        )
        
    @property
    def is_connected(self) -> bool:
        return self.state == ASRState.CONNECTED
        
    @property
    def is_recognizing(self) -> bool:
        return self._is_listening
        
    def set_script(self, script: List[str]):
        """Set recognition script for testing."""
        self._script = script
        self._cursor = 0