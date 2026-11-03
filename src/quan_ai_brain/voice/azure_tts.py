"""Azure Neural Text-to-Speech Provider for QUAN AI BRAIN V36.

This module provides Azure Neural TTS integration:
- Neural voice synthesis (vi-VN-HoaiMyNeural)
- Streaming audio output
- SSML support with prosody control
- Interruptible playback
- Mouth sync integration

Requirements:
- azure-cognitiveservices-speech >= 1.30.0
- Azure Speech Services resource
- Subscription key and region

Usage:
    config = TTSConfig(
        provider="azure",
        azure_subscription_id="your-subscription-id",
        azure_region="southeastasia",
        azure_speech_key="your-key",
        voice_id="vi-VN-HoaiMyNeural"
    )
    provider = AzureNeuralTTS(config)
    provider.connect()
    provider.synthesize_stream(text, on_chunk=handle_audio)
"""
from __future__ import annotations

import logging
import os
import queue
import threading
import time
from typing import Any, Callable, Dict, Optional

from .tts_interface import (
    TTSConfig, TTSProvider, TTSResult, TTSState, VoiceGender, VoiceProfile
)

logger = logging.getLogger(__name__)


class AzureNeuralTTS(TTSProvider):
    """Azure Neural Text-to-Speech provider."""
    
    def __init__(self, config: Optional[TTSConfig] = None):
        super().__init__(config or TTSConfig(provider="azure"))
        
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
                "Azure TTS credentials not found. "
                "Set AZURE_SPEECH_KEY and AZURE_SPEECH_REGION env vars "
                "or provide them in TTSConfig."
            )
        
        self._speech_config = None
        self._synthesizer = None
        self._audio_queue: queue.Queue = queue.Queue()
        self._playback_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._on_audio_chunk: Optional[Callable[[bytes], None]] = None
        self._on_end: Optional[Callable[[], None]] = None
        
        # Mouth sync integration
        self._mouth_sync_callback: Optional[Callable[[float], None]] = None
        
        # Initialize Azure Speech SDK if available
        self._sdk_available = self._init_sdk()
        
    def _init_sdk(self) -> bool:
        """Initialize Azure Speech SDK."""
        try:
            import azure.cognitiveservices.speech as speechsdk
            logger.info("Azure Speech SDK available for TTS")
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
            self.state = TTSState.ERROR
            return False
            
        if not self._subscription_key or not self._region:
            logger.error("Azure TTS credentials not configured")
            self.state = TTSState.ERROR
            return False
        
        try:
            import azure.cognitiveservices.speech as speechsdk
            
            self.state = TTSState.CONNECTING
            
            # Create speech config
            self._speech_config = speechsdk.SpeechConfig(
                subscription=self._subscription_key,
                region=self._region
            )
            
            # Set voice
            self._speech_config.speech_synthesis_voice_name = self.config.voice_id
            
            # Set output format
            format_map = {
                "audio-16khz-16bit-mono-pcm": speechsdk.AudioStreamFormat(
                    samples_per_second=16000,
                    bits_per_sample=16,
                    channels=1
                ),
                "audio-24khz-16bit-mono-pcm": speechsdk.AudioStreamFormat(
                    samples_per_second=24000,
                    bits_per_sample=16,
                    channels=1
                ),
                "audio-48khz-16bit-mono-pcm": speechsdk.AudioStreamFormat(
                    samples_per_second=48000,
                    bits_per_sample=16,
                    channels=1
                ),
            }
            
            audio_format = format_map.get(
                self.config.output_format,
                format_map["audio-16khz-16bit-mono-pcm"]
            )
            
            # Configure stream
            self._stream = speechsdk.audio.PushAudioOutputStream(
                lambda buffer: self._handle_audio_buffer(buffer)
            )
            
            self.state = TTSState.CONNECTED
            logger.info(f"Azure TTS connected (voice={self.config.voice_id}, "
                       f"format={self.config.output_format})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Azure TTS: {e}")
            self.state = TTSState.ERROR
            return False
    
    def disconnect(self) -> bool:
        """Disconnect from Azure Speech Service."""
        try:
            self.stop()
            
            if self._synthesizer:
                self._synthesizer = None
                
            self._speech_config = None
            self.state = TTSState.DISCONNECTED
            logger.info("Azure TTS disconnected")
            return True
            
        except Exception as e:
            logger.error(f"Error disconnecting from Azure TTS: {e}")
            self.state = TTSState.ERROR
            return False
    
    def synthesize(self, text: str) -> Optional[TTSResult]:
        """Synthesize speech from text (one-shot)."""
        if not self.is_connected:
            if not self.connect():
                return None
                
        try:
            import azure.cognitiveservices.speech as speechsdk
            
            # Create synthesizer
            self._synthesizer = speechsdk.SpeechSynthesizer(
                speech_config=self._speech_config,
                audio_config=None  # Use default speaker output
            )
            
            # Generate SSML if enabled
            if self.config.enable_ssml:
                ssml = self.generate_ssml(text)
                result = self._synthesizer.speak_ssml_async(ssml).get()
            else:
                result = self._synthesizer.speak_text_async(text).get()
            
            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                audio_data = result.audio_data
                duration_ms = result.audio_duration.total_seconds() * 1000
                
                return TTSResult(
                    audio_data=audio_data,
                    duration_ms=duration_ms,
                    text_length=len(text),
                    voice_id=self.config.voice_id,
                    is_streaming=False
                )
            elif result.reason == speechsdk.ResultReason.Canceled:
                cancellation_details = result.cancellation_details
                error_msg = f"Synthesis canceled: {cancellation_details.reason}"
                if cancellation_details.reason == speechsdk.CancellationReason.Error:
                    error_msg += f" - {cancellation_details.error_details}"
                logger.error(error_msg)
                return TTSResult(
                    audio_data=b"",
                    duration_ms=0,
                    text_length=len(text),
                    voice_id=self.config.voice_id,
                    is_streaming=False,
                    error=error_msg
                )
            else:
                return TTSResult(
                    audio_data=b"",
                    duration_ms=0,
                    text_length=len(text),
                    voice_id=self.config.voice_id,
                    is_streaming=False,
                    error=f"Synthesis failed: {result.reason}"
                )
                
        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            return TTSResult(
                audio_data=b"",
                duration_ms=0,
                text_length=len(text),
                voice_id=self.config.voice_id,
                is_streaming=False,
                error=str(e)
            )
    
    def synthesize_stream(self, text: str,
                         on_chunk: Callable[[bytes], None]) -> bool:
        """Synthesize speech with streaming output."""
        if not self.is_connected:
            if not self.connect():
                return False
        
        if not self._sdk_available:
            logger.error("Azure Speech SDK not available")
            return False
            
        try:
            import azure.cognitiveservices.speech as speechsdk
            
            self._on_audio_chunk = on_chunk
            self.state = TTSState.SYNTHESIZING
            self._stop_event.clear()
            
            # Create synthesizer with stream output
            self._synthesizer = speechsdk.SpeechSynthesizer(
                speech_config=self._speech_config,
                audio_config=None
            )
            
            # Set up event handlers
            def audio_generated(evt):
                """Handle audio generated event."""
                pass  # Audio is pushed to stream
            
            def synthesis_started(evt):
                """Handle synthesis started."""
                logger.debug("TTS synthesis started")
                self.state = TTSState.SYNTHESIZING
            
            def synthesis_completed(evt):
                """Handle synthesis completed."""
                logger.debug("TTS synthesis completed")
                self.state = TTSState.IDLE
                if self._on_end:
                    self._on_end()
            
            def synthesis_canceled(evt):
                """Handle synthesis canceled."""
                logger.warning("TTS synthesis canceled")
                self.state = TTSState.IDLE
            
            self._synthesizer.synthesis_started.connect(synthesis_started)
            self._synthesizer.synthesis_completed.connect(synthesis_completed)
            self._synthesizer.synthesis_canceled.connect(synthesis_canceled)
            
            # Generate SSML
            if self.config.enable_ssml:
                ssml = self.generate_ssml(text)
                future = self._synthesizer.speak_ssml_async(ssml)
            else:
                future = self._synthesizer.speak_text_async(text)
            
            # Start playback thread
            if self.config.auto_play:
                self._start_playback_thread()
            
            logger.info(f"Azure TTS streaming started (text length={len(text)})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start streaming synthesis: {e}")
            self.state = TTSState.ERROR
            return False
    
    def _handle_audio_buffer(self, buffer: speechsdk.audio.AudioOutputStream) -> int:
        """Handle audio buffer from Azure."""
        try:
            # Read audio data from buffer
            audio_data = buffer.read(self.config.chunk_size)
            
            if audio_data:
                # Call callback if set
                if self._on_audio_chunk:
                    self._on_audio_chunk(audio_data)
                
                # Queue for playback
                if self.config.auto_play:
                    self._audio_queue.put(audio_data)
                
                return len(audio_data)
            return 0
            
        except Exception as e:
            logger.error(f"Error handling audio buffer: {e}")
            return 0
    
    def _start_playback_thread(self):
        """Start audio playback thread."""
        self._stop_event.clear()
        self._playback_thread = threading.Thread(
            target=self._playback_loop,
            daemon=True,
            name="TTSPlayback"
        )
        self._playback_thread.start()
        self.state = TTSState.PLAYING
    
    def _playback_loop(self):
        """Audio playback loop."""
        import wave
        import io
        
        try:
            while not self._stop_event.is_set():
                try:
                    # Get audio chunk from queue
                    audio_data = self._audio_queue.get(timeout=0.1)
                    
                    if audio_data:
                        # Play audio (simplified - in production use proper audio playback)
                        # For now, just simulate playback
                        time.sleep(len(audio_data) / (16000 * 2))  # Rough estimate
                        
                        # Update mouth sync
                        if self._mouth_sync_callback:
                            duration = len(audio_data) / (16000 * 2) * 1000
                            self._mouth_sync_callback(duration)
                            
                except queue.Empty:
                    continue
                except Exception as e:
                    logger.error(f"Playback error: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"Playback thread error: {e}")
        finally:
            self.state = TTSState.IDLE
    
    def stop(self) -> bool:
        """Stop synthesis and playback."""
        try:
            self._stop_event.set()
            
            if self._synthesizer:
                # Cancel ongoing synthesis
                pass  # Azure SDK doesn't have direct cancel, rely on stream close
            
            if self._playback_thread:
                self._playback_thread.join(timeout=1.0)
                self._playback_thread = None
            
            # Clear audio queue
            while not self._audio_queue.empty():
                try:
                    self._audio_queue.get_nowait()
                except queue.Empty:
                    break
            
            self.state = TTSState.IDLE
            logger.info("TTS stopped")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping TTS: {e}")
            self.state = TTSState.ERROR
            return False
    
    def pause(self) -> bool:
        """Pause playback."""
        if self.state == TTSState.PLAYING:
            self.state = TTSState.PAUSED
            logger.info("TTS paused")
            return True
        return False
    
    def resume(self) -> bool:
        """Resume playback."""
        if self.state == TTSState.PAUSED:
            self.state = TTSState.PLAYING
            logger.info("TTS resumed")
            return True
        return False
    
    def set_mouth_sync_callback(self, callback: Callable[[float], None]):
        """Set mouth sync callback for avatar lip-sync.
        
        Args:
            callback: Function to call with audio duration (ms)
        """
        self._mouth_sync_callback = callback
        logger.info("Mouth sync callback set")
    
    def generate_ssml(self, text: str) -> str:
        """Generate SSML with advanced controls.
        
        Args:
            text: Plain text
            
        Returns:
            SSML string with prosody, pronunciation, etc.
        """
        # Escape special characters
        text = text.replace("&", "&")
        text = text.replace("<", "<")
        text = text.replace(">", ">")
        
        # Build prosody attributes
        prosody_attrs = []
        if self.config.speaking_rate != 1.0:
            rate = f"{self.config.speaking_rate:.2f}"
            prosody_attrs.append(f'rate="{rate}"')
        if self.config.pitch != 0:
            pitch = f"{self.config.pitch:+.0f}Hz"
            prosody_attrs.append(f'pitch="{pitch}"')
        if self.config.volume != 100:
            prosody_attrs.append(f'volume="{self.config.volume}"')
        
        prosody_str = " ".join(prosody_attrs) if prosody_attrs else ""
        
        # Add style if specified
        style_str = f' style="{self.config.voice_style}"' if self.config.voice_style else ""
        
        ssml = f'''<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="{self.config.language}">
    <voice name="{self.config.voice_id}"{style_str}>
        {f'<prosody {prosody_str}>' if prosody_str else ''}
            {text}
        {f'</prosody>' if prosody_str else ''}
    </voice>
</speak>'''
        return ssml
    
    @property
    def is_connected(self) -> bool:
        return self.state == TTSState.CONNECTED
    
    @property
    def is_playing(self) -> bool:
        return self.state in [TTSState.PLAYING, TTSState.SYNTHESIZING]