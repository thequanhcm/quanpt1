"""Data models and enums for QUAN AI BRAIN LLM Engine."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
import re
from typing import Any

from quan_ai_brain.core.redaction import redact_text, redact_value


class ProviderType(str, Enum):
    OLLAMA = "ollama"
    MOCK = "mock"


class FallbackMode(str, Enum):
    NEVER = "never"            # Strict: return error or raise if real LLM is unavailable
    ON_ERROR = "on_error"      # Fallback to mock when real LLM is unreachable or errors
    ALWAYS_MOCK = "always_mock"  # Force mock mode (useful for fast local testing/CI)


@dataclass(frozen=True)
class ModelInfo:
    name: str
    tag: str = ""
    size_bytes: int = 0
    modified_at: str = ""
    digest: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class LLMRequest:
    prompt: str
    model: str = "qwen2.5:7b"
    temperature: float = 0.2
    timeout_seconds: float = 30.0
    system_prompt: str = ""
    stream: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if not isinstance(self.prompt, str) or not self.prompt.strip():
            raise ValueError("Prompt must be a non-empty string")
        if len(self.prompt) > 200_000:
            raise ValueError("Prompt exceeds maximum allowed size (200,000 characters)")

        if not isinstance(self.model, str) or not self.model.strip():
            raise ValueError("Model name must be a non-empty string")
        if not re.match(r"^[a-zA-Z0-9_.:/-]+$", self.model):
            raise ValueError(f"Model name contains invalid characters: {self.model}")

        if not isinstance(self.temperature, (int, float)):
            raise TypeError("Temperature must be a float or int")
        if not 0.0 <= float(self.temperature) <= 2.0:
            raise ValueError("Temperature must be between 0.0 and 2.0")

        if not isinstance(self.timeout_seconds, (int, float)):
            raise TypeError("timeout_seconds must be a number")
        if not 0.1 <= float(self.timeout_seconds) <= 300.0:
            raise ValueError("timeout_seconds must be between 0.1 and 300.0 seconds")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class LLMResponse:
    text: str
    model: str
    provider: str
    is_mock: bool = False
    elapsed_ms: float = 0.0
    success: bool = True
    error_code: str | None = None
    error_message: str | None = None
    warning: str | None = None
    raw_metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        safe_meta = redact_value(self.raw_metadata)
        safe_error = redact_text(self.error_message) if self.error_message else None
        safe_text = redact_text(self.text)
        return {
            "text": safe_text,
            "model": self.model,
            "provider": self.provider,
            "is_mock": self.is_mock,
            "elapsed_ms": self.elapsed_ms,
            "success": self.success,
            "error_code": self.error_code,
            "error_message": safe_error,
            "warning": self.warning,
            "raw_metadata": safe_meta,
        }
