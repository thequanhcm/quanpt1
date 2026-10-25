"""Unified LLM Provider facade with explicit, audited fallback control."""
from __future__ import annotations

from typing import Any

from quan_ai_brain.llm.client import OllamaClient
from quan_ai_brain.llm.mock_provider import MockLLMProvider
from quan_ai_brain.llm.models import FallbackMode, LLMRequest, LLMResponse, ModelInfo


class LLMProvider:
    """Facade for LLM inference. Mediates between local Ollama and offline Mock provider."""

    def __init__(
        self,
        client: OllamaClient | None = None,
        mock: MockLLMProvider | None = None,
        fallback_mode: FallbackMode | str = FallbackMode.NEVER,
        default_model: str = "qwen2.5:7b",
    ) -> None:
        self.client = client or OllamaClient()
        self.mock = mock or MockLLMProvider()
        if isinstance(fallback_mode, FallbackMode):
            self.fallback_mode = fallback_mode
        else:
            self.fallback_mode = FallbackMode(str(fallback_mode).lower())
        self.default_model = default_model

    def is_online(self, timeout: float = 2.0) -> bool:
        """Check if real Ollama service is currently online."""
        return self.client.ping(timeout=timeout)

    def health(self, timeout: float = 2.0) -> dict[str, Any]:
        """Inspect health status of both local Ollama service and fallback readiness."""
        online = self.is_online(timeout=timeout)
        models_available: list[str] = []
        has_target = False

        if online:
            try:
                models = self.client.list_models(timeout=timeout)
                models_available = [m.name for m in models]
                has_target = any(
                    self.default_model.lower() in m.name.lower()
                    for m in models
                )
            except Exception:
                online = False

        return {
            "ollama_online": online,
            "endpoint": self.client.base_url,
            "default_model": self.default_model,
            "has_target_model": has_target,
            "available_models": models_available,
            "fallback_mode": self.fallback_mode.value,
            "active_provider": "ollama" if online else ("mock" if self.fallback_mode != FallbackMode.NEVER else "none"),
        }

    def list_models(self, allow_fallback: bool | None = None) -> list[ModelInfo]:
        """List models from real Ollama if online; optionally fallback to mock."""
        fallback = self._should_fallback(allow_fallback)
        try:
            return self.client.list_models()
        except (ConnectionError, ValueError) as exc:
            if fallback:
                return self.mock.list_models()
            raise ConnectionError(f"Ollama is unreachable and fallback is disabled: {exc}") from exc

    def _should_fallback(self, allow_fallback: bool | None) -> bool:
        if allow_fallback is not None:
            return allow_fallback
        return self.fallback_mode in (FallbackMode.ON_ERROR, FallbackMode.ALWAYS_MOCK)

    def generate(
        self,
        request: LLMRequest | str,
        allow_fallback: bool | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Generate response via Ollama or Mock with strict provenance markers."""
        if isinstance(request, str):
            request = LLMRequest(prompt=request, model=self.default_model, **kwargs)

        fallback = self._should_fallback(allow_fallback)

        if self.fallback_mode == FallbackMode.ALWAYS_MOCK or request.model == "mock":
            return self.mock.generate(request)

        # 1. Try real Ollama first
        if self.is_online(timeout=2.0):
            response = self.client.generate(request)
            if response.success:
                return response

            # If Ollama responded with an error and fallback is allowed
            if fallback:
                mock_resp = self.mock.generate(request)
                mock_resp.warning = (
                    f"MOCK FALLBACK — Ollama request failed with [{response.error_code}], "
                    "mock provider used instead. NO REAL LLM INFERENCE."
                )
                return mock_resp

            return response

        # 2. Ollama is offline
        if fallback:
            mock_resp = self.mock.generate(request)
            mock_resp.warning = (
                f"MOCK FALLBACK — Ollama daemon is offline at {self.client.base_url}. "
                "Synthetic mock output used. NO REAL LLM INFERENCE."
            )
            return mock_resp

        # 3. Fallback not allowed and Ollama is offline
        return LLMResponse(
            text="",
            model=request.model,
            provider="ollama",
            is_mock=False,
            elapsed_ms=0.0,
            success=False,
            error_code="OLLAMA_OFFLINE",
            error_message=(
                f"Ollama daemon is offline at {self.client.base_url} "
                "and mock fallback is disabled. Start Ollama or set fallback_mode='on_error'."
            ),
        )
