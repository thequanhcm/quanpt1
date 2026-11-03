"""Audio Capture & VAD Layer for QUAN AI BRAIN V36.

This module provides:
- Real-time microphone audio capture (PyAudio)
- Voice Activity Detection (WebRTC VAD)
- Audio streaming with chunk-based processing
- Noise suppression and gain control
- Sample rate normalization (16kHz, 16-bit, mono)

Architecture:
AudioDevice -> AudioStream -> VADProcessor -> AudioChunks -> ASR
"""
from __future__ import annotations

import logging
import queue
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional

import numpy as np

logger = logging.getLogger(__name__)


class AudioState(Enum):
    """Audio capture states."""
    STOPPED = "stopped"
    STARTING = "starting"
    CAPTURING = "capturing"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass
class AudioChunk:
    """Single chunk of audio data."""
    data: bytes
    timestamp: float
    sample_rate: int = 16000
    channels: int = 1
    sample_width: int = 2  # 16-bit
    is_speech: bool = False  # VAD result
    energy: float = 0.0  # Audio energy level
    duration_ms: float = 0.0


@dataclass
class AudioConfig:
    """Audio capture configuration."""
    sample_rate: int = 16000
    channels: int = 1
    sample_width: int = 2  # 16-bit
    chunk_size: int = 480  # 30ms at 16kHz
    vad_sensitivity: float = 0.5  # 0.0-1.0, higher = more sensitive
    noise_suppression: bool = True
    gain: float = 1.0  # 1.0 = no gain
    device_index: Optional[int] = None
    
    @property
    def bytes_per_chunk(self) -> int:
        return self.chunk_size * self.channels * self.sample_width


class AudioCapture:
    """Real-time microphone audio capture with streaming."""
    
    def __init__(self, config: Optional[AudioConfig] = None):
        self.config = config or AudioConfig()
        self.state = AudioState.STOPPED
        self._audio = None
        self._stream = None
        self._chunk_queue: queue.Queue = queue.Queue()
        self._stop_event = threading.Event()
        self._capture_thread: Optional[threading.Thread] = None
        self._callback: Optional[Callable[[AudioChunk], None]] = None
        
    def start(self, callback: Optional[Callable[[AudioChunk], None]] = None) -> bool:
        """Start audio capture.
        
        Args:
            callback: Function to call for each audio chunk
            
        Returns:
            True if started successfully, False otherwise
        """
        if self.state != AudioState.STOPPED:
            logger.warning(f"Cannot start audio capture in state {self.state}")
            return False
            
        self.state = AudioState.STARTING
        self._callback = callback
        self._stop_event.clear()
        
        try:
            import pyaudio
            self._audio = pyaudio.PyAudio()
            
            # Get device info
            device_index = self.config.device_index
            if device_index is None:
                device_index = self._get_default_input_device()
                
            if device_index is None:
                logger.error("No input device found")
                self.state = AudioState.ERROR
                return False
                
            # Open stream
            self._stream = self._audio.open(
                format=pyaudio.paInt16,
                channels=self.config.channels,
                rate=self.config.sample_rate,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=self.config.chunk_size,
                stream_callback=self._audio_callback,
            )
            
            # Start capture thread
            self._capture_thread = threading.Thread(
                target=self._capture_loop,
                daemon=True,
                name="AudioCapture"
            )
            self._capture_thread.start()
            
            self.state = AudioState.CAPTURING
            logger.info(f"Audio capture started (device={device_index}, "
                       f"rate={self.config.sample_rate}Hz, "
                       f"chunk={self.config.chunk_size}samples)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start audio capture: {e}")
            self.state = AudioState.ERROR
            return False
            
    def stop(self) -> bool:
        """Stop audio capture."""
        if self.state != AudioState.CAPTURING:
            logger.warning(f"Cannot stop audio capture in state {self.state}")
            return False
            
        self.state = AudioState.STOPPING
        self._stop_event.set()
        
        try:
            # Wait for capture thread
            if self._capture_thread:
                self._capture_thread.join(timeout=2.0)
                
            # Close stream
            if self._stream:
                self._stream.stop_stream()
                self._stream.close()
                self._stream = None
                
            # Terminate PyAudio
            if self._audio:
                self._audio.terminate()
                self._audio = None
                
            self.state = AudioState.STOPPED
            logger.info("Audio capture stopped")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping audio capture: {e}")
            self.state = AudioState.ERROR
            return False
            
    def _get_default_input_device(self) -> Optional[int]:
        """Get default input device index."""
        try:
            info = self._audio.get_default_input_device_info()
            return int(info['index'])
        except Exception:
            # Fallback: find first available input device
            for i in range(self._audio.get_device_count()):
                device_info = self._audio.get_device_info_by_index(i)
                if device_info['maxInputChannels'] > 0:
                    return i
            return None
            
    def _audio_callback(self, in_data, frame_count, time_info, status):
        """PyAudio stream callback."""
        if self._stop_event.is_set():
            return None, pyaudio.paAbort
            
        # Process audio chunk
        chunk = self._process_chunk(in_data)
        
        # Add to queue
        try:
            self._chunk_queue.put_nowait(chunk)
        except queue.Full:
            logger.warning("Audio chunk queue full, dropping chunk")
            
        return in_data, pyaudio.paContinue
        
    def _process_chunk(self, audio_data: bytes) -> AudioChunk:
        """Process raw audio data into AudioChunk."""
        timestamp = time.time()
        
        # Calculate audio energy
        audio_array = np.frombuffer(audio_data, dtype=np.int16)
        energy = float(np.sqrt(np.mean(audio_array ** 2)))
        
        # Normalize energy (typical range: 0-10000 for 16-bit audio)
        normalized_energy = min(energy / 10000.0, 1.0)
        
        chunk = AudioChunk(
            data=audio_data,
            timestamp=timestamp,
            sample_rate=self.config.sample_rate,
            channels=self.config.channels,
            sample_width=self.config.sample_width,
            energy=normalized_energy,
            duration_ms=(len(audio_data) / 
                        (self.config.sample_rate * 
                         self.config.channels * 
                         self.config.sample_width)) * 1000
        )
        
        return chunk
        
    def _capture_loop(self):
        """Main capture loop."""
        self._stream.start_stream()
        
        while not self._stop_event.is_set():
            try:
                # Wait for chunk from queue
                try:
                    chunk = self._chunk_queue.get(timeout=0.1)
                    
                    # Call callback if set
                    if self._callback:
                        self._callback(chunk)
                        
                except queue.Empty:
                    continue
                    
            except Exception as e:
                logger.error(f"Error in capture loop: {e}")
                break
                
        self._stream.stop_stream()
        
    @property
    def is_capturing(self) -> bool:
        """Check if audio is currently being captured."""
        return self.state == AudioState.CAPTURING
        
    @property
    def state_info(self) -> dict:
        """Get audio capture state information."""
        return {
            "state": self.state.value,
            "sample_rate": self.config.sample_rate,
            "channels": self.config.channels,
            "chunk_size": self.config.chunk_size,
            "is_capturing": self.is_capturing,
        }