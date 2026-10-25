"""Tests for the NetMind (GLM-5.3-Flash) cloud provider.

Safety rules for this suite:
- NO test talks to the real gateway. HTTP is mocked with io.BytesIO.
- NO API key is ever read from the real environment or printed. Tests use
  monkeypatch-scoped fake keys (e.g. 'test-key-for-unit-tests-only').
- The data-export policy defaults to disabled; tests that enable it use
  monkeypatch env vars scoped to the single test function only.
"""
from __future__ import annotations

import io
import json
import urllib.error
import urllib.request

import pytest

from quan_ai_brain.llm.models import LLMRequest
from quan_ai_brain.llm.netmind_provider import (
    CHAT_MODELS,
    NETMIND_CHAT_MODEL,
    NETMIND_DEEP_REASONING_MODEL,
    NetMindProvider,
)


def _make_provider(**kwargs) -> NetMindProvider:
    kwargs.setdefault("external_data_allowed", True)
    kwargs.setdefault("reasoning_effort", "low")
    return NetMindProvider(**kwargs)


def _fake_http(body: dict, status: int = 200):
    """Return a urlopen replacement serving a canned JSON payload."""
    encoded = json.dumps(body).encode("utf-8")

    def handler(req, timeout=None, context=None):
        if status != 200:
            raise urllib.error.HTTPError(req.full_url, status, "error", None, io.BytesIO(b"{}"))
        return io.BytesIO(encoded)

    return handler


def _clear_netmind_env(monkeypatch) -> None:
    for var in ("NETMIND_API_KEY", "HERMES_CUSTOM_NETMIND_API_KEY", "NETMIND_EXTERNAL_DATA_ALLOWED", "NETMIND_BASE_URL"):
        monkeypatch.delenv(var, raising=False)


# ---------------------------------------------------------------- policy gates
def test_disabled_by_default_no_key(monkeypatch):
    """Fail-closed: without env opt-in, provider is disabled and generate() refuses."""
    _clear_netmind_env(monkeypatch)
    provider = NetMindProvider()
    assert provider.external_data_allowed is False
    resp = provider.generate("Xin chào")
    assert resp.success is False
    assert resp.error_code == "NETMIND_DISABLED"
    assert "owner approval" in (resp.error_message or "")


def test_health_reports_disabled_truthfully(monkeypatch):
    _clear_netmind_env(monkeypatch)
    provider = NetMindProvider()
    h = provider.health()
    assert h["status"] == "DISABLED_BY_POLICY"
    assert h["external_data_allowed"] is False
    assert h["api_key_present"] is False


def test_health_no_key_when_enabled(monkeypatch):
    _clear_netmind_env(monkeypatch)
    monkeypatch.setenv("NETMIND_EXTERNAL_DATA_ALLOWED", "true")
    provider = _make_provider()
    h = provider.health()
    assert h["status"] == "NO_API_KEY"
    assert h["catalog_reachable"] is False


def test_missing_key_returns_no_api_key(monkeypatch):
    _clear_netmind_env(monkeypatch)
    monkeypatch.setenv("NETMIND_EXTERNAL_DATA_ALLOWED", "true")
    provider = _make_provider()
    resp = provider.generate(LLMRequest(prompt="Kiểm tra"))
    assert resp.success is False
    assert resp.error_code == "NO_API_KEY"


def test_model_allowlist_rejects_unknown_model():
    """Only exact catalog IDs pass. Unknown or unverified model IDs are rejected."""
    provider = _make_provider()
    for bad in ("zai-org/GLM-5.3", "zai-org/GLM-5.3-FlashX", "gpt-4o", "qwen2.5:7b"):
        resp = provider.generate(LLMRequest(prompt="test", model=bad))
        assert resp.success is False
        assert resp.error_code == "MODEL_NOT_IN_NETMIND_CATALOG"
        assert resp.model == bad


def test_empty_model_rejected_by_request_validation():
    """Empty model names are blocked at the LLMRequest validation layer (fail-closed)."""
    provider = _make_provider()
    with pytest.raises(ValueError, match="non-empty string"):
        provider.generate(LLMRequest(prompt="test", model=""))


def test_chat_models_constant_matches_catalog():
    # Sprint 2: deep reasoning tier Qwen/Qwen3.5-122B-A10B-FP8 approved by owner.
    assert CHAT_MODELS == ("zai-org/GLM-5.3-Flash", "Qwen/Qwen3.5-122B-A10B-FP8")
    assert NETMIND_CHAT_MODEL == "zai-org/GLM-5.3-Flash"
    assert NETMIND_DEEP_REASONING_MODEL == "Qwen/Qwen3.5-122B-A10B-FP8"


# ---------------------------------------------------------------- happy paths
def test_generate_success_with_reasoning_effort(monkeypatch):
    _clear_netmind_env(monkeypatch)
    monkeypatch.setenv("NETMIND_EXTERNAL_DATA_ALLOWED", "true")
    monkeypatch.setenv("NETMIND_API_KEY", "test-key-for-unit-tests-only")
    provider = _make_provider(reasoning_effort="low")
    captured = {}
    real_urlopen = urllib.request.urlopen

    def handler(req, timeout=None, context=None):
        captured["payload"] = json.loads(req.data.decode("utf-8"))
        captured["auth"] = req.get_header("Authorization")
        captured["url"] = req.full_url
        return io.BytesIO(json.dumps({
            "model": NETMIND_CHAT_MODEL,
            "choices": [{"message": {"content": "Dạ chào anh, em là TONY."}, "finish_reason": "stop"}],
            "usage": {
                "prompt_tokens": 53,
                "completion_tokens": 15,
                "total_tokens": 68,
                "completion_tokens_details": {"reasoning_tokens": 0},
            },
        }).encode("utf-8"))

    urllib.request.urlopen = handler
    try:
        resp = provider.generate(LLMRequest(
            prompt="Chào em",
            model=NETMIND_CHAT_MODEL,
            system_prompt="Bạn là TONY PHAM.",
            metadata={"tier": "fast"},
        ))
    finally:
        urllib.request.urlopen = real_urlopen

    assert resp.success is True
    assert resp.provider == "netmind"
    assert resp.is_mock is False
    assert "TONY" in resp.text
    assert resp.raw_metadata["reasoning_tokens"] == 0
    assert captured["payload"]["reasoning_effort"] == "low"
    assert captured["payload"]["stream"] is False
    assert captured["payload"]["messages"][0] == {"role": "system", "content": "Bạn là TONY PHAM."}
    assert captured["payload"]["messages"][1] == {"role": "user", "content": "Chào em"}
    assert captured["auth"] == "Bearer test-key-for-unit-tests-only"
    assert captured["url"].endswith("/chat/completions")
    assert provider.last_routing is not None
    assert provider.last_routing["provider"] == "netmind"
    assert provider.last_routing["success"] is True


def test_generate_respects_metadata_max_tokens(monkeypatch):
    _clear_netmind_env(monkeypatch)
    monkeypatch.setenv("NETMIND_EXTERNAL_DATA_ALLOWED", "true")
    monkeypatch.setenv("NETMIND_API_KEY", "test-key-2")
    provider = _make_provider()
    captured = {}
    real_urlopen = urllib.request.urlopen

    def handler(req, timeout=None, context=None):
        captured["payload"] = json.loads(req.data.decode("utf-8"))
        return io.BytesIO(json.dumps({
            "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        }).encode("utf-8"))

    urllib.request.urlopen = handler
    try:
        resp = provider.generate(LLMRequest(prompt="test", model=NETMIND_CHAT_MODEL, metadata={"max_tokens": 50}))
    finally:
        urllib.request.urlopen = real_urlopen

    assert resp.success is True
    assert captured["payload"]["max_tokens"] == 50


def test_is_online_requires_policy_and_key(monkeypatch):
    _clear_netmind_env(monkeypatch)
    provider_off = NetMindProvider(external_data_allowed=False)
    assert provider_off.is_online() is False
    monkeypatch.setenv("NETMIND_EXTERNAL_DATA_ALLOWED", "true")
    provider_on = _make_provider()
    assert provider_on.is_online() is False  # no key
    monkeypatch.setenv("NETMIND_API_KEY", "test-key-3")
    real_urlopen = urllib.request.urlopen
    urllib.request.urlopen = _fake_http({"data": [{"id": "zai-org/GLM-5.3-Flash"}]})
    try:
        assert provider_on.is_online() is True
    finally:
        urllib.request.urlopen = real_urlopen


def test_list_models_maps_catalog(monkeypatch):
    _clear_netmind_env(monkeypatch)
    monkeypatch.setenv("NETMIND_EXTERNAL_DATA_ALLOWED", "true")
    monkeypatch.setenv("NETMIND_API_KEY", "test-key-4")
    provider = _make_provider()
    real_urlopen = urllib.request.urlopen
    urllib.request.urlopen = _fake_http({"data": [
        {"id": "MiniMax/MiniMax-M3"},
        {"id": "zai-org/GLM-5.3-Flash"},
    ]})
    try:
        infos = provider.list_models()
    finally:
        urllib.request.urlopen = real_urlopen
    assert [i.name for i in infos] == ["MiniMax/MiniMax-M3", "zai-org/GLM-5.3-Flash"]


# ---------------------------------------------------------------- error paths
def test_http_error_returned_structured(monkeypatch):
    _clear_netmind_env(monkeypatch)
    monkeypatch.setenv("NETMIND_EXTERNAL_DATA_ALLOWED", "true")
    monkeypatch.setenv("NETMIND_API_KEY", "test-key-5")
    provider = _make_provider(max_retries=0)
    real_urlopen = urllib.request.urlopen
    urllib.request.urlopen = _fake_http({}, status=401)
    try:
        resp = provider.generate(LLMRequest(prompt="test", model=NETMIND_CHAT_MODEL))
    finally:
        urllib.request.urlopen = real_urlopen
    assert resp.success is False
    assert resp.error_code == "HTTP_401"
    assert resp.is_mock is False
    assert "test-key-5" not in (resp.error_message or "")


def test_retry_then_success(monkeypatch):
    _clear_netmind_env(monkeypatch)
    monkeypatch.setenv("NETMIND_EXTERNAL_DATA_ALLOWED", "true")
    monkeypatch.setenv("NETMIND_API_KEY", "test-key-6")
    provider = _make_provider(max_retries=1)
    calls = {"n": 0}
    real_urlopen = urllib.request.urlopen

    def flaky(req, timeout=None, context=None):
        calls["n"] += 1
        if calls["n"] == 1:
            raise urllib.error.URLError("transient gateway hiccup")
        return io.BytesIO(json.dumps({
            "choices": [{"message": {"content": "đã phục hồi"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 3, "completion_tokens": 4, "total_tokens": 7},
        }).encode("utf-8"))

    urllib.request.urlopen = flaky
    try:
        resp = provider.generate(LLMRequest(prompt="test", model=NETMIND_CHAT_MODEL))
    finally:
        urllib.request.urlopen = real_urlopen
    assert resp.success is True
    assert calls["n"] == 2
    assert resp.raw_metadata["attempt"] == 2


def test_retry_exhaustion_returns_error(monkeypatch):
    _clear_netmind_env(monkeypatch)
    monkeypatch.setenv("NETMIND_EXTERNAL_DATA_ALLOWED", "true")
    monkeypatch.setenv("NETMIND_API_KEY", "test-key-7")
    provider = _make_provider(max_retries=1)
    real_urlopen = urllib.request.urlopen
    urllib.request.urlopen = _fake_http({}, status=500)
    try:
        resp = provider.generate(LLMRequest(prompt="test", model=NETMIND_CHAT_MODEL))
    finally:
        urllib.request.urlopen = real_urlopen
    assert resp.success is False
    assert resp.error_code == "HTTP_500"


def test_network_error_never_fakes_success(monkeypatch):
    """Transparent degradation: unreachable gateway NEVER fabricates an answer."""
    _clear_netmind_env(monkeypatch)
    monkeypatch.setenv("NETMIND_EXTERNAL_DATA_ALLOWED", "true")
    monkeypatch.setenv("NETMIND_API_KEY", "test-key-8")
    provider = _make_provider(max_retries=0)
    real_urlopen = urllib.request.urlopen
    urllib.request.urlopen = _fake_http({}, status=503)
    try:
        resp = provider.generate(LLMRequest(prompt="test", model=NETMIND_CHAT_MODEL))
    finally:
        urllib.request.urlopen = real_urlopen
    assert resp.success is False
    assert resp.error_code == "HTTP_503"
    assert resp.text == ""


def test_timeout_error_returned(monkeypatch):
    _clear_netmind_env(monkeypatch)
    monkeypatch.setenv("NETMIND_EXTERNAL_DATA_ALLOWED", "true")
    monkeypatch.setenv("NETMIND_API_KEY", "test-key-9")
    provider = _make_provider(max_retries=0)
    real_urlopen = urllib.request.urlopen

    def slow(req, timeout=None, context=None):
        raise TimeoutError("simulated gateway timeout")

    urllib.request.urlopen = slow
    try:
        resp = provider.generate(LLMRequest(prompt="test", model=NETMIND_CHAT_MODEL))
    finally:
        urllib.request.urlopen = real_urlopen
    assert resp.success is False
    assert resp.error_code == "TIMEOUT"


def test_audit_metadata_only(monkeypatch):
    """AuditLogger receives routing metadata only — never prompt content."""
    _clear_netmind_env(monkeypatch)
    monkeypatch.setenv("NETMIND_EXTERNAL_DATA_ALLOWED", "true")
    monkeypatch.setenv("NETMIND_API_KEY", "test-key-10")

    class FakeAudit:
        def __init__(self):
            self.events = []

        def record(self, event_type, details):
            self.events.append((event_type, details))

    audit = FakeAudit()
    provider = _make_provider(audit_logger=audit)
    real_urlopen = urllib.request.urlopen
    urllib.request.urlopen = _fake_http({
        "choices": [{"message": {"content": "hello"}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 2, "completion_tokens": 3, "total_tokens": 5},
    })
    try:
        provider.generate(LLMRequest(prompt="NỘI DUNG BÍ MẬT KHÔNG ĐƯỢC LƯU", model=NETMIND_CHAT_MODEL))
    finally:
        urllib.request.urlopen = real_urlopen
    assert len(audit.events) == 1
    event_type, details = audit.events[0]
    assert event_type == "llm_routing"
    assert "NỘI DUNG BÍ MẬT" not in json.dumps(details, ensure_ascii=False)
    assert details["provider"] == "netmind"


def test_key_never_stored_on_instance():
    provider = _make_provider()
    for attr_name, attr_value in vars(provider).items():
        assert "api_key" not in attr_name
        if isinstance(attr_value, str):
            assert "Bearer" not in attr_value
