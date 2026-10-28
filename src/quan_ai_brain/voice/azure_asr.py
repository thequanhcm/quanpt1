"""Azure Speech-to-Text Provider for QUAN AI BRAIN V36.

This module provides Azure Speech Services integration:
- Streaming speech recognition
- Vietnamese language support (vi-VN)
- Partial results and confidence scores
- Word-level timestamps
- Automatic punctuation

Requirements:
- azure-cognitiveservices-speech >= 1.30.0
- Azure Speech Services resource
- Subscription key and region

Usage:
    config = ASRConfig(
        provider="azure",
        azure_subscription_id="your-subscription-id",
        azure_region="southeastasia",
        azure_speech_key="your-key"
    )
    provider = AzureSpeechToText(config)
    provider.connect()
    provider.start_recognition(on_result=handle_result)
"""
from __future__ import annotations

import logging
import os
import time
from typing import Any, Callable, Dict, Optional

from .asr_interface import (
    ASRConfig, ASRProvider, ASRResult, ASRState, RecognitionType
)

logger = logging.getLogger(__name__)


class AzureSpeechToText(ASRProvider):
    """Azure Speech-to-Text provider for Vietnamese recognition."""
    
    def __init__(self, config: Optional[ASRConfig] = None):
        super().__init__(config or ASRConfig(provider="azure"))
        
        # Validate credentials
        self._subscription_key = (
            self.config.azure_speech_key or 
            os.getenv("AZURE_SPEECH_KEY")
        )
        self._region = (
            self.config.azure_region or 
            os.getenv("AZURE_SPEECH_REGION")
        )
        
        if not self._subscription_key or not self._region:
            logger.warning(
                "Azure credentials not found. "
                "Set AZURE_SPEECH_KEY and AZURE_SPEECH_REGION env vars "
                "or provide them in ASRConfig."
            )
        
        self._speech_config = None
        self._recognizer = None
        self._on_result_callback: Optional[Callable[[ASRResult], None]] = None
        self._audio_stream = None
        
        # Initialize Azure Speech SDK if available
        self._sdk_available = self._init_sdk()
        
    def _init_sdk(self) -> bool:
        """Initialize Azure Speech SDK."""
        try:
            import azure.cognitiveservices.speech as speechsdk
            logger.info("Azure Speech SDK available")
            return True
        except ImportError:
            logger.warning(
                "Azure Speech SDK not installed. "
                "Install with: pip install azure-cognitiveservices-speech"
            )
            return False
    
    def connect(self) -> bool:
        """Connect to Azure Speech Service."""
        if not self._sdk_available:
            logger.error("Azure Speech SDK not available")
            self.state = ASRState.ERROR
            return False
            
        if not self._subscription_key or not self._region:
            logger.error("Azure credentials not configured")
            self.state = ASRState.ERROR
            return False
        
        try:
            import azure.cognitiveservices.speech as speechsdk
            
            self.state = ASRState.CONNECTING
            
            # Create speech config
            self._speech_config = speechsdk.SpeechConfig(
                subscription=self._subscription_key,
                region=self._region
            )
            
            # Configure for Vietnamese
            self._speech_config.speech_recognition_language = self.config.language
            
            # Set audio format
            self._speech_config.set_property(
                property_id=speechsdk.PropertyId.SpeechServiceResponse_RequestSentenceBoundary,
                value='true'
            )
            
            self._speech_config.set_property(
                property_id=speechsdk.PropertyId.SpeechServiceResponse_RequestWordBoundary,
                value='true'
            )
            
            # Profanity filter
            if self.config.profanity_filter:
                self._speech_config.set_profanity(
                    speechsdk.ProfanityOption.Masked
                )
            
            self.state = ASRState.CONNECTED
            logger.info(f"Azure Speech connected (region={self._region}, "
                       f"language={self.config.language})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Azure Speech: {e}")
            self.state = ASRState.ERROR
            return False
    
    def disconnect(self) -> bool:
        """Disconnect from Azure Speech Service."""
        try:
            if self._recognizer:
                self._recognizer.stop_continuous_recognition()
                self._recognizer = None
                
            if self._audio_stream:
                self._audio_stream.close()
                self._audio_stream = None
                
            self._speech_config = None
            self.state = ASRState.DISCONNECTED
            logger.info("Azure Speech disconnected")
            return True
            
        except Exception as e:
            logger.error(f"Error disconnecting from Azure Speech: {e}")
            self.state = ASRState.ERROR
            return False
    
    def start_recognition(self,
                         on_result: Callable[[ASRResult], None]) -> bool:
        """Start continuous speech recognition."""
        if not self.is_connected:
            if not self.connect():
                return False
        
        if not self._sdk_available:
            logger.error("Azure Speech SDK not available")
            return False
            
        try:
            import azure.cognitiveservices.speech as speechsdk
            
            self._on_result_callback = on_result
            self.state = ASRState.LISTENING
            
            # Create audio config from default microphone
            audio_config = speechsdk.AudioConfig(use_default_microphone=True)
            
            # Create speech recognizer
            self._recognizer = speechsdk.SpeechRecognizer(
                speech_config=self._speech_config,
                audio_config=audio_config
            )
            
            # Set up event handlers
            self._recognizer.recognizing.connect(
                lambda evt: self._handle_recognizing(evt)
            )
            self._recognizer.recognized.connect(
                lambda evt: self._handle_recognized(evt)
            )
            self._recognizer.session_started.connect(
                lambda evt: self._handle_session_started(evt)
            )
            self._recognizer.session_stopped.connect(
                lambda evt: self._handle_session_stopped(evt)
            )
            self._recognizer.canceled.connect(
                lambda evt: self._handle_canceled(evt)
            )
            
            # Start continuous recognition
            self._recognizer.start_continuous_recognition()
            self.state = ASRState.RECOGNIZING
            
            logger.info("Azure Speech recognition started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start recognition: {e}")
            self.state = ASRState.ERROR
            return False
    
    def stop_recognition(self) -> bool:
        """Stop continuous speech recognition."""
        try:
            if self._recognizer:
                self._recognizer.stop_continuous_recognition()
                self._recognizer = None
                
            self.state = ASRState.IDLE
            logger.info("Azure Speech recognition stopped")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping recognition: {e}")
            self.state = ASRState.ERROR
            return False
    
    def recognize_audio(self, audio_data: bytes) -> Optional[ASRResult]:
        """Recognize speech from audio data (one-shot)."""
        if not self.is_connected:
            if not self.connect():
                return None
                
        try:
            import azure.cognitiveservices.speech as speechsdk
            
            # Create audio stream from data
            push_stream = speechsdk.audio.PushAudioInputStream(
                stream_format=speechsdk.audio.AudioStreamFormat(
                    samples_per_second=self.config.sample_rate,
                    bits_per_sample=16,
                    channels=1
                )
            )
            push_stream.write(audio_data)
            push_stream.close()
            
            audio_config = speechsdk.AudioConfig(stream=push_stream)
            recognizer = speechsdk.SpeechRecognizer(
                speech_config=self._speech_config,
                audio_config=audio_config
            )
            
            # Single recognition
            result = recognizer.recognize_once()
            
            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                return ASRResult(
                    text=result.text,
                    confidence=1.0,  # Azure doesn't provide confidence for single
                    is_final=True,
                    timestamp_start=time.time() - 1.0,
                    timestamp_end=time.time(),
                    language=self.config.language
                )
            elif result.reason == speechsdk.ResultReason.NoMatch:
                return ASRResult(
                    text="",
                    confidence=0.0,
                    is_final=True,
                    timestamp_start=0.0,
                    timestamp_end=0.0,
                    error="No speech recognized"
                )
            else:
                return ASRResult(
                    text="",
                    confidence=0.0,
                    is_final=True,
                    timestamp_start=0.0,
                    timestamp_end=0.0,
                    error=f"Recognition failed: {result.reason}"
                )
                
        except Exception as e:
            logger.error(f"Audio recognition failed: {e}")
            return ASRResult(
                text="",
                confidence=0.0,
                is_final=True,
                timestamp_start=0.0,
                timestamp_end=0.0,
                error=str(e)
            )
    
    def recognize_stream(self, audio_chunk: bytes) -> Optional[ASRResult]:
        """Write audio chunk to stream (for streaming recognition)."""
        # For continuous recognition, chunks are written to the stream
        # Results are delivered via callbacks
        if self._audio_stream:
            try:
                self._audio_stream.write(audio_chunk)
            except Exception as e:
                logger.error(f"Error writing audio chunk: {e}")
                return None
        
        return None  # Results come via callbacks
    
    def _handle_recognizing(self, evt):
        """Handle partial recognition result."""
        if not self._on_result_callback:
            return
            
        try:
            result = ASRResult(
                text=evt.result.text,
                confidence=0.7,  # Partial results have lower confidence
                is_final=False,
                timestamp_start=evt.result.offset / 10000000.0,
                timestamp_end=(evt.result.offset + evt.result.duration) / 10000000.0,
                language=self.config.language
            )
            self._on_result_callback(result)
        except Exception as e:
            logger.error(f"Error handling recognizing event: {e}")
    
    def _handle_recognized(self, evt):
        """Handle final recognition result."""
        if not self._on_result_callback:
            return
            
        try:
            # Extract word-level information if available
            words = []
            if hasattr(evt.result, 'json') and evt.result.json:
                import json
                json_result = json.loads(evt.result.json)
                if 'NBest' in json_result and len(json_result['NBest']) > 0:
                    for word in json_result['NBest'][0].get('Words', []):
                        words.append({
                            'word': word.get('Word', ''),
                            'offset': word.get('Offset', 0),
                            'duration': word.get('Duration', 0)
                        })
            
            result = ASRResult(
                text=evt.result.text,
                confidence=1.0,  # Final results
                is_final=True,
                timestamp_start=evt.result.offset / 10000000.0,
                timestamp_end=(evt.result.offset + evt.result.duration) / 10000000.0,
                language=self.config.language,
                words=words
            )
            self._on_result_callback(result)
        except Exception as e:
            logger.error(f"Error handling recognized event: {e}")
    
    def _handle_session_started(self, evt):
        """Handle session started event."""
        logger.debug("Azure Speech session started")
        self.state = ASRState.LISTENING
    
    def _handle_session_stopped(self, evt):
        """Handle session stopped event."""
        logger.debug("Azure Speech session stopped")
        self.state = ASRState.IDLE
    
    def _handle_canceled(self, evt):
        """Handle canceled event."""
        logger.warning(f"Azure Speech recognition canceled: {evt.reason}")
        if evt.reason == speechsdk.CancellationReason.Error:
            logger.error(f"Azure Speech error: {evt.error_details}")
            self.state = ASRState.ERROR
    
    @property
    def is_connected(self) -> bool:
        return self.state == ASRState.CONNECTED
    
    @property
    def is_recognizing(self) -> bool:
        return self.state == ASRState.RECOGNIZING


def create_asr_provider(config: ASRConfig) -> ASRProvider:
    """Factory function to create ASR provider.
    
    Args:
        config: ASR configuration
        
    Returns:
        ASRProvider instance
    """
    if config.provider == "azure":
        return AzureSpeechToText(config)
    elif config.provider == "mock":
        from .asr_interface import MockASRProvider
        return MockASRProvider(config)
    else:
        raise ValueError(f"Unknown ASR provider: {config.provider}")