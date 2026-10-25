"""Tests for QUAN AI BRAIN LLM Engine (Ollama + Mock + Fallback)."""
from __future__ import annotations

import io
import json
import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from quan_ai_brain.llm.client import OllamaClient
from quan_ai_brain.llm.mock_provider import MockLLMProvider
from quan_ai_brain.llm.models import (
    FallbackMode,
    LLMRequest,
    LLMResponse,
    ModelInfo,
)
from quan_ai_brain.llm.provider import LLMProvider


def test_valid_llm_request_creation():
    """Verify valid LLMRequest with defaults and custom parameters."""
    req = LLMRequest(prompt="Kiểm tra trạng thái hệ thống pin UPS")
    assert req.prompt == "Kiểm tra trạng thái hệ thống pin UPS"
    assert req.model == "qwen2.5:7b"
    assert req.temperature == 0.2
    assert req.timeout_seconds == 30.0
    assert not req.stream

    custom = LLMRequest(
        prompt="Phân tích log",
        model="qwen2.5:1.5b",
        temperature=0.7,
        timeout_seconds=45.0,
        system_prompt="Bạn là trợ lý kỹ thuật",
    )
    assert custom.model == "qwen2.5:1.5b"
    assert custom.temperature == 0.7
    assert custom.timeout_seconds == 45.0
    assert custom.system_prompt == "Bạn là trợ lý kỹ thuật"


def test_reject_empty_or_invalid_prompt():
    """Verify empty or oversized prompts are strictly rejected."""
    with pytest.raises(ValueError, match="non-empty string"):
        LLMRequest(prompt="")

    with pytest.raises(ValueError, match="non-empty string"):
        LLMRequest(prompt="   \n\t  ")

    with pytest.raises(ValueError, match="exceeds maximum allowed size"):
        LLMRequest(prompt="A" * 200_001)


def test_reject_invalid_temperature_and_timeout():
    """Verify temperature and timeout validation."""
    with pytest.raises(ValueError, match="Temperature must be between"):
        LLMRequest(prompt="Valid", temperature=-0.1)

    with pytest.raises(ValueError, match="Temperature must be between"):
        LLMRequest(prompt="Valid", temperature=2.1)

    with pytest.raises(ValueError, match="timeout_seconds must be between"):
        LLMRequest(prompt="Valid", timeout_seconds=0.0)

    with pytest.raises(ValueError, match="timeout_seconds must be between"):
        LLMRequest(prompt="Valid", timeout_seconds=301.0)


def test_prohibit_non_local_endpoints():
    """Security guard: prohibit remote/internet endpoints in Sprint 2B."""
    # Local endpoints must pass
    c1 = OllamaClient("http://127.0.0.1:11434")
    assert c1.base_url == "http://127.0.0.1:11434"

    c2 = OllamaClient("http://localhost:11434")
    assert "localhost" in c2.base_url

    # External internet hosts must be rejected
    with pytest.raises(ValueError, match="Security guard: Host 'api.openai.com' is prohibited"):
        OllamaClient("https://api.openai.com/v1")

    with pytest.raises(ValueError, match="Security guard: Host '192.168.1.100' is prohibited"):
        OllamaClient("http://192.168.1.100:11434")


def test_ping_success_on_valid_response():
    """Verify ping returns True when Ollama returns 200."""
    client = OllamaClient()
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        assert client.ping(timeout=1.0) is True


def test_ping_failure_on_connection_error():
    """Verify ping returns False cleanly when daemon is unreachable."""
    client = OllamaClient()
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Connection refused")):
        assert client.ping(timeout=1.0) is False


def test_ping_failure_on_timeout():
    """Verify ping returns False on timeout without crashing."""
    client = OllamaClient()
    with patch("urllib.request.urlopen", side_effect=TimeoutError("Request timed out")):
        assert client.ping(timeout=1.0) is False


def test_list_models_success():
    """Verify list_models parses tags JSON correctly."""
    sample_tags = json.dumps({
        "models": [
            {
                "name": "qwen2.5:7b",
                "model": "qwen2.5:7b:latest",
                "size": 4661224676,
                "modified_at": "2026-10-17T12:00:00Z",
                "digest": "sha256:abc12345",
                "details": {"family": "qwen2", "parameter_size": "7B"},
            },
            {
                "name": "llama3.1:latest",
                "model": "llama3.1:latest",
                "size": 4920739840,
                "modified_at": "2026-10-15T08:00:00Z",
                "digest": "sha256:def67890",
            },
        ]
    }).encode("utf-8")

    mock_resp = MagicMock()
    mock_resp.read.return_value = sample_tags
    mock_resp.__enter__.return_value = mock_resp

    client = OllamaClient()
    with patch("urllib.request.urlopen", return_value=mock_resp):
        models = client.list_models()
        assert len(models) == 2
        assert models[0].name == "qwen2.5:7b"
        assert models[0].size_bytes == 4661224676
        assert models[0].details["family"] == "qwen2"
        assert client.has_model("qwen2.5:7b") is True
        assert client.has_model("nonexistent:model") is False


def test_list_models_handles_invalid_json():
    """Verify list_models handles corrupt JSON gracefully."""
    mock_resp = MagicMock()
    mock_resp.read.return_value = b"<!DOCTYPE html><html>Not JSON</html>"
    mock_resp.__enter__.return_value = mock_resp

    client = OllamaClient()
    with patch("urllib.request.urlopen", return_value=mock_resp):
        with pytest.raises(ValueError, match="Failed to parse Ollama model list JSON"):
            client.list_models()


def test_generate_success():
    """Verify generate parses valid Ollama response."""
    sample_response = json.dumps({
        "model": "qwen2.5:7b",
        "response": "Nhiệt độ phòng pin UPS hiện ở mức 24.5 độ C, nằm trong dải an toàn.",
        "done": True,
        "total_duration": 1500000000,
        "eval_count": 25,
    }).encode("utf-8")

    mock_resp = MagicMock()
    mock_resp.read.return_value = sample_response
    mock_resp.__enter__.return_value = mock_resp

    client = OllamaClient()
    with patch("urllib.request.urlopen", return_value=mock_resp):
        res = client.generate(LLMRequest(prompt="Báo cáo nhiệt độ"))
        assert res.success is True
        assert res.is_mock is False
        assert res.provider == "ollama"
        assert "24.5 độ C" in res.text
        assert res.model == "qwen2.5:7b"
        assert res.error_code is None


def test_generate_handles_http_error():
    """Verify generate handles HTTP errors without crashing."""
    http_err = urllib.error.HTTPError(
        url="http://127.0.0.1:11434/api/generate",
        code=404,
        msg="Model 'unknown:model' not found",
        hdrs={},  # type: ignore[arg-type]
        fp=io.BytesIO(b"model not found"),
    )

    client = OllamaClient()
    with patch("urllib.request.urlopen", side_effect=http_err):
        res = client.generate(LLMRequest(prompt="Test", model="unknown:model"))
        assert res.success is False
        assert res.is_mock is False
        assert res.error_code == "HTTP_404"
        assert "404" in (res.error_message or "")


def test_generate_handles_timeout():
    """Verify generate handles timeouts cleanly."""
    client = OllamaClient()
    with patch("urllib.request.urlopen", side_effect=TimeoutError("Connection timed out")):
        res = client.generate(LLMRequest(prompt="Test timeout", timeout_seconds=5.0))
        assert res.success is False
        assert res.error_code == "TIMEOUT"
        assert "timed out" in (res.error_message or "").lower()


def test_generate_handles_missing_response_field():
    """Verify generate detects JSON lacking 'response' key."""
    corrupted_data = json.dumps({"status": "running"}).encode("utf-8")
    mock_resp = MagicMock()
    mock_resp.read.return_value = corrupted_data
    mock_resp.__enter__.return_value = mock_resp

    client = OllamaClient()
    with patch("urllib.request.urlopen", return_value=mock_resp):
        res = client.generate(LLMRequest(prompt="Test missing response"))
        assert res.success is False
        assert res.error_code == "MISSING_RESPONSE_FIELD"


def test_mock_provider_always_marks_is_mock_and_warns():
    """Verify MockLLMProvider always sets is_mock=True and provides clear warning."""
    mock = MockLLMProvider()
    assert mock.ping() is True
    models = mock.list_models()
    assert len(models) >= 1
    assert any(m.name == "qwen2.5:7b" for m in models)

    res = mock.generate("Xin chào trợ lý")
    assert res.success is True
    assert res.is_mock is True
    assert res.provider == "mock"
    assert "MOCK MODE" in (res.warning or "")
    assert "[MOCK]" in res.text


def test_provider_fallback_only_when_configured():
    """Verify fallback to mock occurs ONLY when explicitly permitted."""
    # 1. FallbackMode.NEVER (default): offline Ollama returns error, NO fake answer
    client_offline = OllamaClient()
    with patch.object(client_offline, "ping", return_value=False):
        provider_strict = LLMProvider(client=client_offline, fallback_mode=FallbackMode.NEVER)
        res_strict = provider_strict.generate("Câu hỏi quan trọng")
        assert res_strict.success is False
        assert res_strict.is_mock is False
        assert res_strict.error_code == "OLLAMA_OFFLINE"
        assert "offline" in (res_strict.error_message or "")

    # 2. FallbackMode.ON_ERROR: offline Ollama engages mock WITH warning
    with patch.object(client_offline, "ping", return_value=False):
        provider_fallback = LLMProvider(client=client_offline, fallback_mode=FallbackMode.ON_ERROR)
        res_fallback = provider_fallback.generate("Câu hỏi kiểm thử")
        assert res_fallback.success is True
        assert res_fallback.is_mock is True
        assert res_fallback.provider == "mock"
        assert "MOCK FALLBACK" in (res_fallback.warning or "")


def test_provider_uses_real_ollama_when_online():
    """Verify LLMProvider uses real Ollama client when it is online."""
    mock_client = MagicMock()
    mock_client.ping.return_value = True
    mock_client.generate.return_value = LLMResponse(
        text="Phản hồi thực từ Qwen2.5:7b",
        model="qwen2.5:7b",
        provider="ollama",
        is_mock=False,
        success=True,
    )

    provider = LLMProvider(client=mock_client, fallback_mode=FallbackMode.ON_ERROR)
    res = provider.generate("Xin chào")
    assert res.success is True
    assert res.is_mock is False
    assert res.provider == "ollama"
    assert res.text == "Phản hồi thực từ Qwen2.5:7b"


def test_provider_health_snapshot():
    """Verify health() provides structured status for diagnostics."""
    mock_client = MagicMock()
    mock_client.base_url = "http://127.0.0.1:11434"
    mock_client.ping.return_value = False

    provider = LLMProvider(client=mock_client, fallback_mode=FallbackMode.NEVER)
    h = provider.health()
    assert h["ollama_online"] is False
    assert h["endpoint"] == "http://127.0.0.1:11434"
    assert h["default_model"] == "qwen2.5:7b"
    assert h["fallback_mode"] == "never"
    assert h["active_provider"] == "none"


def test_no_credential_leakage_in_error_or_response():
    """Verify sensitive tokens are redacted in responses and error messages."""
    resp = LLMResponse(
        text="Thông tin bình thường",
        model="qwen2.5:7b",
        provider="ollama",
        error_message='Failed auth with password="super_secret_password" and token=abc12345678',
        raw_metadata={"api_key": "sk-1234567890", "safe": "ok"},
    )
    dumped = resp.to_dict()
    assert "super_secret_password" not in str(dumped)
    assert "sk-1234567890" not in str(dumped)
    assert "[REDACTED]" in str(dumped)
