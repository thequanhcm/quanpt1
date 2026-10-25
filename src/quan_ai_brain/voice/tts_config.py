"""Centralized Vietnamese Female TTS Configuration & Management for QUAN AI BRAIN.

Enforces strict compliance with:
- Default Language: vi-VN (Vietnamese)
- Preferred Voice: vi-VN-HoaiMyNeural (Microsoft Edge Natural Female)
- Gender: female
- Strict fallback policy: Never silently speak in English or use default OS voice
  when Vietnamese voice is missing. Cleanly report TTS_UNAVAILABLE instead.
"""
from __future__ import annotations

import asyncio
import concurrent.futures
from dataclasses import asdict, dataclass, field
from enum import Enum
import re
import time
from typing import Any


class TTSProvider(str, Enum):
    EDGE_TTS = "edge-tts"
    BROWSER_SPEECH = "browser-speech-synthesis"
    MOCK = "mock"


class TTSGender(str, Enum):
    FEMALE = "female"
    MALE = "male"


class TTSStatus(str, Enum):
    READY = "READY"
    SPEAKING = "SPEAKING"
    TTS_UNAVAILABLE = "TTS_UNAVAILABLE"
    ERROR = "ERROR"


@dataclass
class TTSVoiceInfo:
    voice_id: str
    name: str
    locale: str
    gender: str
    provider: str
    is_online: bool = True
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# Canonical verified Vietnamese voices
STANDARD_VIETNAMESE_VOICES: list[TTSVoiceInfo] = [
    TTSVoiceInfo(
        voice_id="vi-VN-HoaiMyNeural",
        name="Microsoft HoaiMy Online (Natural) - Vietnamese (Vietnam)",
        locale="vi-VN",
        gender=TTSGender.FEMALE.value,
        provider=TTSProvider.EDGE_TTS.value,
        is_online=True,
        description="Giọng nữ Việt Nam tự nhiên, biểu cảm ấm áp, rõ ràng, phù hợp trợ lý điều hành.",
    ),
    TTSVoiceInfo(
        voice_id="vi-VN-NamMinhNeural",
        name="Microsoft NamMinh Online (Natural) - Vietnamese (Vietnam)",
        locale="vi-VN",
        gender=TTSGender.MALE.value,
        provider=TTSProvider.EDGE_TTS.value,
        is_online=True,
        description="Giọng nam Việt Nam tự nhiên, phong thái nghiêm túc.",
    ),
]


@dataclass
class TTSConfig:
    """Centralized configuration contract for QUAN AI BRAIN TTS."""

    response_language: str = "vi-VN"
    tts_locale: str = "vi-VN"
    tts_gender: str = "female"
    tts_enabled: bool = True
    tts_voice_preference: str = "vi-VN-HoaiMyNeural"
    provider: str = "edge-tts"
    rate: float = 1.0
    pitch: float = 1.0
    volume: float = 1.0
    status: str = TTSStatus.READY.value
    connection_status: str = "CONNECTED"
    last_error: str = ""
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalize_text_for_vietnamese_tts(text: str, max_chars: int = 500) -> str:
    """Sanitize and normalize text for Vietnamese TTS synthesis.
    
    Guarantees:
    - 100% preservation of Vietnamese diacritics and tone marks.
    - Strips code blocks, markdown tags, JSON, stack traces, raw file paths.
    - Preserves numbers, metrics, device identifiers, and technical terms.
    - Redacts any sensitive tokens/secrets before synthesis.
    - Clean sentence splitting avoiding mid-word truncation.
    """
    if not text:
        return ""

    s = text.strip()

    # 1. Redact credentials/tokens if present
    s = re.sub(r"(?i)(token|bearer|password|secret|api_key)\s*[:=]\s*[\w\.\-]+", "[đã bảo mật]", s)

    # 2. Strip Markdown code blocks
    s = re.sub(r"```[\s\S]*?```", " [Khối mã nguồn kỹ thuật] ", s)

    # 3. Strip inline code formatting backticks while keeping inner technical terms
    s = re.sub(r"`([^`]+)`", r" \1 ", s)

    # 4. Strip JSON structures {...}
    s = re.sub(r"\{[^{}]*\}", "", s)

    # 5. Strip URLs and raw Windows/Unix file paths
    s = re.sub(r"https?://\S+", "", s)
    s = re.sub(r"[A-Za-z]:\\[\w\\\.-]+", "", s)
    s = re.sub(r"/\S+/\S+", "", s)

    # 6. Strip Markdown symbols (bold, italic, headers, bullet dashes)
    s = re.sub(r"^#+\s*", "", s, flags=re.MULTILINE)
    s = re.sub(r"^\s*[-*+]\s+", "", s, flags=re.MULTILINE)
    s = re.sub(r"[*_~]", "", s)

    # 7. Normalize common technical units for natural Vietnamese reading
    s = re.sub(r"\b(\d+)\s*ms\b", r"\1 mili giây", s, flags=re.IGNORECASE)
    s = re.sub(r"\b(\d+)\s*s\b", r"\1 giây", s, flags=re.IGNORECASE)
    s = re.sub(r"\b(\d+)\s*KB\b", r"\1 ki-lô-bai", s, flags=re.IGNORECASE)
    s = re.sub(r"\b(\d+)\s*MB\b", r"\1 mê-ga-bai", s, flags=re.IGNORECASE)
    s = re.sub(r"\b(\d+)\s*GB\b", r"\1 ghi-ga-bai", s, flags=re.IGNORECASE)
    s = re.sub(r"\bRTT\b", "độ trễ", s, flags=re.IGNORECASE)

    # 8. Collapse whitespace
    s = re.sub(r"\s+", " ", s).strip()

    # 9. Smart sentence boundary truncation if text exceeds max_chars
    if len(s) > max_chars:
        sentences = re.split(r"(?<=[.!?])\s+", s)
        truncated = ""
        for sent in sentences:
            if len(truncated) + len(sent) + 1 <= max_chars:
                truncated = f"{truncated} {sent}".strip()
            else:
                break
        if not truncated:
            # Cut at last space before max_chars
            last_space = s[:max_chars].rfind(" ")
            truncated = (s[:last_space] if last_space > 0 else s[:max_chars]) + "..."
        s = truncated

    return s


class TTSManager:
    """Centralized manager for Vietnamese Female TTS configuration, synthesis, and lifecycle."""

    def __init__(self, config: TTSConfig | None = None) -> None:
        self.config = config or TTSConfig()
        self.available_voices = list(STANDARD_VIETNAMESE_VOICES)
        self.active_voice_id = self.config.tts_voice_preference

    def get_config(self) -> dict[str, Any]:
        voice_info = self.get_active_voice()
        return {
            "config": self.config.to_dict(),
            "active_voice": voice_info.to_dict() if voice_info else None,
            "available_voices": [v.to_dict() for v in self.available_voices],
            "status": self.config.status,
            "connection_status": self.config.connection_status,
        }

    def get_active_voice(self) -> TTSVoiceInfo | None:
        for v in self.available_voices:
            if v.voice_id == self.active_voice_id:
                return v
        return self.available_voices[0] if self.available_voices else None

    def set_voice_preference(self, voice_id: str) -> bool:
        """Sets voice preference. Rejects non-Vietnamese or invalid voices."""
        found = None
        for v in self.available_voices:
            if v.voice_id == voice_id:
                found = v
                break

        if not found:
            self.config.status = TTSStatus.ERROR.value
            self.config.last_error = f"Giọng đọc '{voice_id}' không tồn tại hoặc không được hỗ trợ trong danh mục tiếng Việt."
            return False

        if not found.locale.startswith("vi"):
            self.config.status = TTSStatus.ERROR.value
            self.config.last_error = f"Chỉ cho phép giọng tiếng Việt (vi-VN), từ chối: {found.locale}."
            return False

        self.active_voice_id = found.voice_id
        self.config.tts_voice_preference = found.voice_id
        self.config.tts_locale = found.locale
        self.config.tts_gender = found.gender
        self.config.status = TTSStatus.READY.value
        self.config.last_error = ""
        self.config.updated_at = time.time()
        return True

    def update_config(
        self,
        enabled: bool | None = None,
        voice_id: str | None = None,
        rate: float | None = None,
        pitch: float | None = None,
        volume: float | None = None,
        provider: str | None = None,
        locale: str | None = None,
    ) -> bool:
        """Updates configuration safely with policy validation."""
        if locale is not None:
            if not locale.startswith("vi"):
                self.config.status = TTSStatus.ERROR.value
                self.config.last_error = f"Chỉ cho phép ngôn ngữ tiếng Việt (vi-VN), từ chối: {locale}"
                return False
            self.config.tts_locale = locale

        if voice_id is not None:
            if not self.set_voice_preference(voice_id):
                return False

        if enabled is not None:
            self.config.tts_enabled = bool(enabled)

        if rate is not None:
            self.config.rate = max(0.5, min(2.0, float(rate)))

        if pitch is not None:
            self.config.pitch = max(0.5, min(1.5, float(pitch)))

        if volume is not None:
            self.config.volume = max(0.0, min(1.0, float(volume)))

        if provider is not None:
            prov_str = str(provider).strip().lower()
            valid_providers = [p.value for p in TTSProvider]
            if prov_str in valid_providers:
                self.config.provider = prov_str
            else:
                self.config.status = TTSStatus.ERROR.value
                self.config.last_error = f"Provider không hợp lệ: {provider}. Cho phép: {valid_providers}"
                return False

        self.config.updated_at = time.time()
        return True

    def mark_unavailable(self, reason: str = "Không tìm thấy giọng đọc tiếng Việt phù hợp.") -> None:
        """Sets status to TTS_UNAVAILABLE instead of silently switching to English."""
        self.config.status = TTSStatus.TTS_UNAVAILABLE.value
        self.config.last_error = reason
        self.config.connection_status = "OFFLINE"
        self.config.updated_at = time.time()

    def mark_ready(self) -> None:
        self.config.status = TTSStatus.READY.value
        self.config.last_error = ""
        self.config.connection_status = "CONNECTED"
        self.config.updated_at = time.time()

    def synthesize_audio(
        self,
        text: str,
        voice_id: str | None = None,
    ) -> tuple[bytes | None, str]:
        """Synthesize Vietnamese speech audio.
        
        Guarantees:
        - Input text diacritics are 100% preserved.
        - Strict Vietnamese female voice preference (vi-VN-HoaiMyNeural).
        - Rejects invalid voices or non-Vietnamese locales with clear error.
        - Sets TTS_UNAVAILABLE on connection/network failure rather than falling back to English.
        - Returns (audio_bytes, error_message).
        """
        if not self.config.tts_enabled:
            return None, "TTS hiện đang bị tắt trong cấu hình."

        target_voice_id = voice_id or self.active_voice_id
        # Verify target voice
        voice_info = None
        for v in self.available_voices:
            if v.voice_id == target_voice_id:
                voice_info = v
                break

        if not voice_info or not voice_info.locale.startswith("vi"):
            self.config.status = TTSStatus.ERROR.value
            err = f"Giọng đọc '{target_voice_id}' không hợp lệ hoặc không phải tiếng Việt."
            self.config.last_error = err
            return None, err

        clean_text = normalize_text_for_vietnamese_tts(text)
        if not clean_text:
            return None, "Văn bản sau chuẩn hóa rỗng."

        # Handle Mock provider
        if self.config.provider == TTSProvider.MOCK.value:
            self.config.status = TTSStatus.READY.value
            self.config.connection_status = "CONNECTED"
            # Return synthetic test MP3 header + silent frame
            mock_audio = b"ID3\x03\x00\x00\x00\x00\x00\n" + b"\xff\xfb\x90d" * 50
            return mock_audio, ""

        # Handle Edge-TTS provider
        if self.config.provider == TTSProvider.EDGE_TTS.value:
            try:
                import edge_tts
            except ImportError:
                self.mark_unavailable("Gói thư viện edge-tts chưa được cài đặt trong môi trường.")
                return None, self.config.last_error

            # Format rate/pitch/volume strings for edge-tts
            rate_pct = int((self.config.rate - 1.0) * 100)
            rate_str = f"{rate_pct:+d}%" if rate_pct != 0 else "+0%"

            pitch_hz = int((self.config.pitch - 1.0) * 50)
            pitch_str = f"{pitch_hz:+d}Hz" if pitch_hz != 0 else "+0Hz"

            volume_pct = int((self.config.volume - 1.0) * 100)
            volume_str = f"{volume_pct:+d}%" if volume_pct != 0 else "+0%"

            async def _do_synth() -> bytes:
                communicate = edge_tts.Communicate(
                    text=clean_text,
                    voice=target_voice_id,
                    rate=rate_str,
                    pitch=pitch_str,
                    volume=volume_str,
                )
                chunks = []
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        chunks.append(chunk["data"])
                return b"".join(chunks)

            def _run_coroutine(coro):
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                            return pool.submit(asyncio.run, coro).result(timeout=15.0)
                    else:
                        return loop.run_until_complete(coro)
                except RuntimeError:
                    return asyncio.run(coro)

            try:
                self.config.status = TTSStatus.SPEAKING.value
                audio_bytes = _run_coroutine(_do_synth())
                if audio_bytes and len(audio_bytes) > 0:
                    self.config.status = TTSStatus.READY.value
                    self.config.connection_status = "CONNECTED"
                    self.config.last_error = ""
                    return audio_bytes, ""
                else:
                    self.mark_unavailable("Microsoft Edge TTS không trả về luồng âm thanh.")
                    return None, self.config.last_error
            except Exception as exc:
                self.mark_unavailable(f"Lỗi kết nối Microsoft Edge TTS: {exc}")
                return None, self.config.last_error

        # Handle Browser-Speech (client side only)
        if self.config.provider == TTSProvider.BROWSER_SPEECH.value:
            return None, "Browser Speech Synthesis provider được chỉ định; âm thanh sẽ được phát trực tiếp tại trình duyệt."

        self.mark_unavailable(f"Provider '{self.config.provider}' không hỗ trợ tổng hợp âm thanh tại Core.")
        return None, self.config.last_error


# Global singleton instance for centralized configuration
GLOBAL_TTS_MANAGER = TTSManager()

