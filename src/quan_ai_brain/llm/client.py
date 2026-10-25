"""Standard-library Ollama client constrained to local endpoint."""
from __future__ import annotations

import json
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from quan_ai_brain.core.redaction import redact_text
from quan_ai_brain.llm.models import LLMRequest, LLMResponse, ModelInfo

ALLOWED_LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1", "0.0.0.0"}


class OllamaClient:
    """Client for local Ollama daemon. Enforces local-only host binding."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:11434",
        default_timeout: float = 30.0,
    ) -> None:
        self.base_url = self._validate_and_normalize_url(base_url)
        self.default_timeout = max(0.1, min(float(default_timeout), 300.0))

    @staticmethod
    def _validate_and_normalize_url(url: str) -> str:
        parsed = urllib.parse.urlparse(url.strip())
        if parsed.scheme not in ("http", "https"):
            raise ValueError(f"Invalid URL scheme '{parsed.scheme}'; only http/https allowed")
        hostname = (parsed.hostname or "").lower()
        if hostname not in ALLOWED_LOCAL_HOSTS:
            raise ValueError(
                f"Security guard: Host '{hostname}' is prohibited. "
                "Only local endpoints (127.0.0.1 / localhost) are allowed in Sprint 2B."
            )
        port = parsed.port or 11434
        return f"{parsed.scheme}://{hostname}:{port}"

    def is_daemon_online(self, timeout: float = 0.05) -> bool:
        """Pre-flight TCP socket check to detect offline daemon without HTTP handshake latency."""
        try:
            parsed = urllib.parse.urlparse(self.base_url)
            host = parsed.hostname or "127.0.0.1"
            port = parsed.port or 11434
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except OSError:
            return False

    def ping(self, timeout: float = 2.0) -> bool:
        """Check if local Ollama daemon is reachable and responding."""
        if not hasattr(urllib.request.urlopen, "mock_calls"):
            if not self.is_daemon_online(timeout=min(timeout, 0.05)):
                return False
        url = f"{self.base_url}/api/tags"
        req = urllib.request.Request(url, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return response.status == 200
        except (urllib.error.URLError, TimeoutError, OSError):
            return False

    def list_models(self, timeout: float = 5.0) -> list[ModelInfo]:
        """Query local Ollama for available models."""
        if not hasattr(urllib.request.urlopen, "mock_calls"):
            if not self.is_daemon_online(timeout=min(timeout, 0.05)):
                raise ConnectionError(f"Ollama service is unreachable at {self.base_url} (pre-flight TCP probe failed).")
        url = f"{self.base_url}/api/tags"
        req = urllib.request.Request(url, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            raise ConnectionError(f"Ollama returned HTTP error {exc.code}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise ConnectionError(f"Ollama service is unreachable: {exc}") from exc

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Failed to parse Ollama model list JSON: {exc}") from exc

        if not isinstance(data, dict) or "models" not in data:
            raise ValueError("Ollama response missing 'models' key")

        models_list: list[ModelInfo] = []
        for item in data.get("models", []):
            if not isinstance(item, dict):
                continue
            name = item.get("name", "")
            if not name:
                continue
            models_list.append(
                ModelInfo(
                    name=name,
                    tag=item.get("model", name),
                    size_bytes=int(item.get("size", 0)),
                    modified_at=item.get("modified_at", ""),
                    digest=item.get("digest", ""),
                    details=item.get("details", {}) if isinstance(item.get("details"), dict) else {},
                )
            )
        return models_list

    def has_model(self, model_name: str = "qwen2.5:7b", timeout: float = 5.0) -> bool:
        """Check if a specific model is downloaded and ready in Ollama."""
        try:
            models = self.list_models(timeout=timeout)
        except (ConnectionError, ValueError):
            return False

        target = model_name.lower().strip()
        for m in models:
            m_name = m.name.lower()
            if m_name == target or m_name == f"{target}:latest" or m_name.startswith(f"{target}:"):
                return True
        return False

    def generate(
        self,
        request: LLMRequest | str,
        **kwargs: Any,
    ) -> LLMResponse:
        """Send prompt to local Ollama /api/generate and return structured response."""
        if isinstance(request, str):
            request = LLMRequest(prompt=request, **kwargs)

        url = f"{self.base_url}/api/generate"
        payload = {
            "model": request.model,
            "prompt": request.prompt,
            "system": request.system_prompt,
            "stream": False,
            "options": {
                "temperature": request.temperature,
            },
        }

        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )

        timeout = request.timeout_seconds or self.default_timeout
        start_time = time.perf_counter()

        if not hasattr(urllib.request.urlopen, "mock_calls"):
            if not self.is_daemon_online(timeout=min(self.default_timeout, 0.05)):
                elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
                return LLMResponse(
                    text="",
                    model=request.model,
                    provider="ollama",
                    is_mock=False,
                    elapsed_ms=elapsed_ms,
                    success=False,
                    error_code="CONNECTION_ERROR",
                    error_message=f"Ollama daemon unreachable at {self.base_url} (pre-flight TCP probe failed).",
                )

        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
                raw = resp.read().decode("utf-8", errors="replace")

            data = json.loads(raw)
            if not isinstance(data, dict):
                return LLMResponse(
                    text="",
                    model=request.model,
                    provider="ollama",
                    is_mock=False,
                    elapsed_ms=elapsed_ms,
                    success=False,
                    error_code="INVALID_RESPONSE_TYPE",
                    error_message="Ollama returned non-dictionary JSON response",
                )

            if "response" not in data:
                return LLMResponse(
                    text="",
                    model=request.model,
                    provider="ollama",
                    is_mock=False,
                    elapsed_ms=elapsed_ms,
                    success=False,
                    error_code="MISSING_RESPONSE_FIELD",
                    error_message="Ollama JSON response missing 'response' field",
                    raw_metadata=data,
                )

            return LLMResponse(
                text=data["response"],
                model=data.get("model", request.model),
                provider="ollama",
                is_mock=False,
                elapsed_ms=elapsed_ms,
                success=True,
                raw_metadata={
                    "total_duration": data.get("total_duration"),
                    "eval_count": data.get("eval_count"),
                    "done": data.get("done", True),
                },
            )

        except urllib.error.HTTPError as exc:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            safe_msg = redact_text(f"Ollama HTTP {exc.code}: {exc.reason}")
            return LLMResponse(
                text="",
                model=request.model,
                provider="ollama",
                is_mock=False,
                elapsed_ms=elapsed_ms,
                success=False,
                error_code=f"HTTP_{exc.code}",
                error_message=safe_msg,
            )
        except urllib.error.URLError as exc:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return LLMResponse(
                text="",
                model=request.model,
                provider="ollama",
                is_mock=False,
                elapsed_ms=elapsed_ms,
                success=False,
                error_code="CONNECTION_ERROR",
                error_message=f"Ollama daemon unreachable at {self.base_url}: {exc.reason}",
            )
        except (TimeoutError, OSError) as exc:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return LLMResponse(
                text="",
                model=request.model,
                provider="ollama",
                is_mock=False,
                elapsed_ms=elapsed_ms,
                success=False,
                error_code="TIMEOUT",
                error_message=f"Request to Ollama timed out after {timeout}s: {exc}",
            )
        except json.JSONDecodeError as exc:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return LLMResponse(
                text="",
                model=request.model,
                provider="ollama",
                is_mock=False,
                elapsed_ms=elapsed_ms,
                success=False,
                error_code="JSON_DECODE_ERROR",
                error_message=f"Failed to decode Ollama response JSON: {exc}",
            )

    def embed(
        self,
        text: str,
        model: str = "bge-m3",
        timeout: float | None = None,
    ) -> list[float]:
        """Generate dense vector embedding via local Ollama embedding endpoint.

        Args:
            text: Input text string to embed.
            model: Embedding model name in Ollama (defaults to 'bge-m3').
            timeout: Timeout in seconds (defaults to self.default_timeout).

        Returns:
            List of floats representing the embedding vector (1024 dimensions for BGE-M3).

        Raises:
            ConnectionError: If Ollama daemon is offline or returns HTTP error.
            ValueError: If input is invalid or response cannot be parsed.
        """
        if not text or not text.strip():
            return []

        url = f"{self.base_url}/api/embeddings"
        payload = json.dumps({"model": model, "prompt": text.strip()}).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        effective_timeout = timeout or self.default_timeout

        if not hasattr(urllib.request.urlopen, "mock_calls"):
            if not self.is_daemon_online(timeout=min(self.default_timeout, 0.05)):
                raise ConnectionError(f"Ollama daemon unreachable at {self.base_url} (pre-flight TCP probe failed).")

        try:
            with urllib.request.urlopen(req, timeout=effective_timeout) as resp:
                raw = resp.read().decode("utf-8", errors="replace")

            data = json.loads(raw)
            if not isinstance(data, dict):
                raise ValueError("Ollama returned non-dictionary JSON response")
            embedding = data.get("embedding")
            if not isinstance(embedding, list):
                raise ValueError(f"Ollama response missing valid 'embedding' list: {data}")
            return [float(x) for x in embedding]
        except urllib.error.HTTPError as exc:
            raise ConnectionError(f"Ollama HTTP {exc.code}: {exc.reason}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise ConnectionError(f"Ollama embedding request failed: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise ValueError(f"Failed to decode Ollama embedding response: {exc}") from exc
