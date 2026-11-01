"""Text-to-Speech (TTS) Interface for QUAN AI BRAIN V36.

This module defines the abstract interface for speech synthesis providers:
- TTSProvider: Base interface for all TTS backends
- TTSConfig: TTS configuration
- TTSSession: Streaming synthesis session
- VoiceProfile: Voice selection and customization

Supported providers:
- AzureNeuralTTS (Phase 3)
- GoogleCloudTTS (Future)
- CoquiTTS (Future - offline)
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class TTSState(Enum):
    """TTS session states."""
    IDLE = "idle"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    SYNTHESIZING = "synthesizing"
    PLAYING = "playing"
    PAUSED = "paused"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class VoiceGender(Enum):
    """Voice gender."""
    MALE = "male"
    FEMALE = "female"


@dataclass
class VoiceProfile:
    """Voice profile for TTS."""
    voice_id: str  # e.g., "vi-VN-HoaiMyNeural"
    language: str  # e.g., "vi-VN"
    gender: VoiceGender
    name: str = ""  # e.g., "Hoai My"
    style: str = ""  # e.g., "chat", "customerservice", "newscast"
    age: str = ""  # e.g., "adult", "elderly"
    description: str = ""
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> VoiceProfile:
        """Create from dictionary."""
        return cls(
            voice_id=data.get("voice_id", ""),
            language=data.get("language", ""),
            gender=VoiceGender(data.get("gender", "female")),
            name=data.get("name", ""),
            style=data.get("style", ""),
            age=data.get("age", ""),
            description=data.get("description", "")
        )


@dataclass
class TTSConfig:
    """TTS configuration."""
    # Provider settings
    provider: str = "azure"  # azure, google, coqui
    language: str = "vi-VN"  # Vietnamese (Vietnam)
    
    # Azure-specific
    azure_subscription_id: Optional[str] = None
    azure_region: Optional[str] = None  # e.g., "southeastasia"
    azure_speech_key: Optional[str] = None
    
    # Voice settings
    voice_id: str = "vi-VN-HoaiMyNeural"  # Default Vietnamese neural voice
    voice_style: str = ""  # e.g., "chat", "newscast"
    speaking_rate: float = 1.0  # 0.25-4.0
    pitch: float = 0.0  # -100 to 100 Hz
    volume: float = 100.0  # 0-100
    
    # Audio format
    output_format: str = "audio-16khz-16bit-mono-pcm"
    sample_rate: int = 16000
    bits_per_sample: int = 16
    channels: int = 1
    
    # Streaming settings
    enable_streaming: bool = True
    chunk_size: int = 1024  # Audio chunk size in bytes
    
    # SSML settings
    enable_ssml: bool = True
    prosody_enabled: bool = True
    pronunciation_dict: Optional[Dict[str, str]] = None
    
    # Playback settings
    auto_play: bool = True
    interruptible: bool = True
    fade_in_ms: int = 50
    fade_out_ms: int = 100
    
    # Timeout and retry
    connection_timeout: float = 30.0
    request_timeout: float = 60.0
    max_retries: int = 3
    
    # Fallback
    fallback_enabled: bool = True
    fallback_voice_id: str = "vi-VN-NamMinhNeural"


@dataclass
class TTSResult:
    """TTS synthesis result."""
    audio_data: bytes
    duration_ms: float
    text_length: int
    voice_id: str
    is_streaming: bool = False
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "audio_data_length": len(self.audio_data),
            "duration_ms": self.duration_ms,
            "text_length": self.text_length,
            "voice_id": self.voice_id,
            "is_streaming": self.is_streaming,
            "error": self.error,
        }


class TTSProvider(ABC):
    """Abstract base class for text-to-speech providers."""
    
    def __init__(self, config: TTSConfig):
        self.config = config
        self.state = TTSState.IDLE
        self._session = None
        self._on_audio_chunk: Optional[Callable[[bytes], None]] = None
        self._on_end: Optional[Callable[[], None]] = None
        
    @abstractmethod
    def connect(self) -> bool:
        """Connect to TTS service.
        
        Returns:
            True if connected successfully
        """
        pass
    
    @abstractmethod
    def disconnect(self) -> bool:
        """Disconnect from TTS service.
        
        Returns:
            True if disconnected successfully
        """
        pass
    
    @abstractmethod
    def synthesize(self, text: str) -> Optional[TTSResult]:
        """Synthesize speech from text (one-shot).
        
        Args:
            text: Text to synthesize
            
        Returns:
            TTSResult or None if synthesis failed
        """
        pass
    
    @abstractmethod
    def synthesize_stream(self, text: str, 
                         on_chunk: Callable[[bytes], None]) -> bool:
        """Synthesize speech with streaming output.
        
        Args:
            text: Text to synthesize
            on_chunk: Callback for audio chunks
            
        Returns:
            True if synthesis started successfully
        """
        pass
    
    @abstractmethod
    def stop(self) -> bool:
        """Stop current synthesis/playback.
        
        Returns:
            True if stopped successfully
        """
        pass
    
    @abstractmethod
    def pause(self) -> bool:
        """Pause playback.
        
        Returns:
            True if paused successfully
        """
        pass
    
    @abstractmethod
    def resume(self) -> bool:
        """Resume playback.
        
        Returns:
            True if resumed successfully
        """
        pass
    
    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if connected to TTS service."""
        pass
    
    @property
    @abstractmethod
    def is_playing(self) -> bool:
        """Check if currently playing audio."""
        pass
    
    def get_state_info(self) -> Dict[str, Any]:
        """Get TTS state information."""
        return {
            "state": self.state.value,
            "is_connected": self.is_connected,
            "is_playing": self.is_playing,
            "provider": self.config.provider,
            "voice_id": self.config.voice_id,
            "language": self.config.language,
        }
    
    def generate_ssml(self, text: str) -> str:
        """Generate SSML from text.
        
        Args:
            text: Plain text
            
        Returns:
            SSML string
        """
        # Escape special characters
        text = text.replace("&", "&")
        text = text.replace("<", "<")
        text = text.replace(">", ">")
        
        ssml = f'''<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="{self.config.language}">
    <voice name="{self.config.voice_id}">
        <prosody rate="{self.config.speaking_rate}" pitch="{self.config.pitch}Hz" volume="{self.config.volume}">
            {text}
        </prosody>
    </voice>
</speak>'''
        return ssml


class MockTTSProvider(TTSProvider):
    """Mock TTS provider for testing without cloud services."""
    
    def __init__(self, config: Optional[TTSConfig] = None):
        super().__init__(config or TTSConfig(provider="mock"))
        self._is_playing = False
        self._audio_buffer: List[bytes] = []
        
    def connect(self) -> bool:
        """Mock connection."""
        self.state = TTSState.CONNECTED
        logger.info("Mock TTS connected")
        return True
        
    def disconnect(self) -> bool:
        """Mock disconnection."""
        self.state = TTSState.DISCONNECTED
        logger.info("Mock TTS disconnected")
        return True
        
    def synthesize(self, text: str) -> Optional[TTSResult]:
        """Mock one-shot synthesis."""
        # Generate dummy audio (silence)
        duration_ms = len(text) * 100  # Rough estimate: 100ms per char
        audio_data = bytes([0] * (duration_ms * self.config.sample_rate // 1000 * 2))
        
        return TTSResult(
            audio_data=audio_data,
            duration_ms=duration_ms,
            text_length=len(text),
            voice_id=self.config.voice_id,
            is_streaming=False
        )
        
    def synthesize_stream(self, text: str,
                         on_chunk: Callable[[bytes], None]) -> bool:
        """Mock streaming synthesis."""
        self.state = TTSState.SYNTHESIZING
        self._is_playing = True
        
        # Simulate streaming with chunks
        chunk_size = 4800  # 150ms at 16kHz
        num_chunks = max(1, len(text) // 10)
        
        for i in range(num_chunks):
            chunk = bytes([0] * chunk_size)
            if on_chunk:
                on_chunk(chunk)
                
        self.state = TTSState.IDLE
        self._is_playing = False
        return True
        
    def stop(self) -> bool:
        """Stop synthesis."""
        self._is_playing = False
        self.state = TTSState.IDLE
        return True
        
    def pause(self) -> bool:
        """Pause playback."""
        if self._is_playing:
            self.state = TTSState.PAUSED
        return True
        
    def resume(self) -> bool:
        """Resume playback."""
        if self.state == TTSState.PAUSED:
            self.state = TTSState.SYNTHESIZING
        return True
        
    @property
    def is_connected(self) -> bool:
        return self.state == TTSState.CONNECTED
        
    @property
    def is_playing(self) -> bool:
        return self._is_playing


def create_tts_provider(config: TTSConfig) -> TTSProvider:
    """Factory function to create TTS provider.
    
    Args:
        config: TTS configuration
        
    Returns:
        TTSProvider instance
    """
    if config.provider == "azure":
        from .azure_tts import AzureNeuralTTS
        return AzureNeuralTTS(config)
    elif config.provider == "mock":
        return MockTTSProvider(config)
    else:
        raise ValueError(f"Unknown TTS provider: {config.provider}")