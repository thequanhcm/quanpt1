"""Sprint 2 tests: streaming chat + deep reasoning tier + router fallback.

Test rules (mirroring test_netmind_provider.py):
- NO test talks to the real gateway. HTTP is mocked with io.BytesIO / canned SSE.
- NO API key is ever read from the environment, set, or printed.
"""
from __future__ import annotations

import io
import json
import urllib.request

from quan_ai_brain.llm.models import LLMRequest
from quan_ai_brain.llm.netmind_provider import (
    DEEP_REASONING_DEFAULT_MAX_TOKENS,
    NETMIND_CHAT_MODEL,
    NETMIND_DEEP_REASONING_MODEL,
    NetMindProvider,
)
from quan_ai_brain.llm.router import LLMRouter


# ------------------------------------------------------------------ SSE helpers
def _sse_frame(model: str, text: str) -> str:
    delta = json.dumps({"content": text}, ensure_ascii=False)
    event = {
        "id": "chatcmpl-test",
        "object": "chat.completion.chunk",
        "model": model,
        "choices": [{"index": 0, "delta": json.loads(delta), "finish_reason": None}],
    }
    return "data: " + json.dumps(event, ensure_ascii=False) + "\n\n"


def _sse_stream(chunks: list[str], model: str = NETMIND_CHAT_MODEL) -> bytes:
    frames = [_sse_frame(model, t) for t in chunks]
    frames.append("data")
    return "".join(frames).encode("utf-8")


def _patch_urlopen(monkeypatch, body: bytes, content_type: str = "text/event-stream; charset=utf-8", captured: dict | None = None) -> None:
    class FakeResponse(io.BytesIO):
        headers = {"Content-Type": content_type}

        def getheader(self, name, default=None):
            return self.headers.get(name, default)

    def handler(req, timeout=None, context=None):
        if captured is not None:
            captured["payload"] = json.loads(req.data.decode("utf-8"))
        return FakeResponse(body)

    monkeypatch.setattr(urllib.request, "urlopen", handler)


def _clear_env(monkeypatch) -> None:
    monkeypatch.delenv("NETMIND_API_KEY", raising=False)
    monkeypatch.delenv("HERMES_CUSTOM_NETMIND_API_KEY", raising=False)


# ------------------------------------------------------------------ stream gates
def test_stream_disabled_by_policy(monkeypatch):
    _clear_env(monkeypatch)
    provider = NetMindProvider(external_data_allowed=False)
    events = list(provider.stream_chat(LLMRequest(prompt="Chào em", model=NETMIND_CHAT_MODEL)))
    assert events[0]["type"] == "error"
    assert events[0]["code"] == "NETMIND_DISABLED"


def test_stream_missing_key(monkeypatch):
    _clear_env(monkeypatch)
    provider = NetMindProvider(external_data_allowed=True)
    events = list(provider.stream_chat(LLMRequest(prompt="Chào em", model=NETMIND_CHAT_MODEL)))
    assert events[0]["type"] == "error"
    assert events[0]["code"] == "NO_API_KEY"


def test_stream_rejects_unknown_model(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("NETMIND_API_KEY", "test-key-for-unit-tests-only")
    provider = NetMindProvider(external_data_allowed=True)
    events = list(provider.stream_chat(LLMRequest(prompt="Chào em", model="some-random-model")))
    assert events[0]["type"] == "error"
    assert events[0]["code"] == "MODEL_NOT_IN_NETMIND_CATALOG"


# ------------------------------------------------------------------ stream happy path
def test_stream_success_yields_meta_deltas_final(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("NETMIND_API_KEY", "test-key-for-unit-tests-only")
    provider = NetMindProvider(external_data_allowed=True, reasoning_effort="low")
    captured: dict = {}
    _patch_urlopen(monkeypatch, _sse_stream(["Dạ chào anh, ", "em là TONY."]), captured=captured)

    events = list(provider.stream_chat(LLMRequest(
        prompt="Chào em",
        model=NETMIND_CHAT_MODEL,
        system_prompt="Bạn là TONY PHAM.",
    )))

    assert [e["type"] for e in events] == ["meta", "delta", "delta", "final"]
    assert events[0]["model"] == NETMIND_CHAT_MODEL
    assert events[1]["text"] == "Dạ chào anh, "
    assert events[2]["text"] == "em là TONY."
    final = events[3]
    assert final["model"] == NETMIND_CHAT_MODEL
    assert final["finish_reason"] == "stop"
    assert final["elapsed_ms"] >= 0
    assert captured["payload"]["stream"] is True
    assert captured["payload"]["reasoning_effort"] == "low"
    assert provider.last_routing is not None
    assert provider.last_routing["success"] is True


def test_stream_deep_model_skips_reasoning_effort_and_sets_budget(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("NETMIND_API_KEY", "test-key-for-unit-tests-only")
    provider = NetMindProvider(external_data_allowed=True, reasoning_effort="low")
    captured: dict = {}
    _patch_urlopen(monkeypatch, _sse_stream(["Kế hoạch 3 bước..."], model=NETMIND_DEEP_REASONING_MODEL), captured=captured)

    events = list(provider.stream_chat(LLMRequest(prompt="Phân tích chuyên sâu kiến trúc", model=NETMIND_DEEP_REASONING_MODEL)))

    assert events[0]["model"] == NETMIND_DEEP_REASONING_MODEL
    payload = captured["payload"]
    assert payload["model"] == NETMIND_DEEP_REASONING_MODEL
    assert "reasoning_effort" not in payload  # verified no-effect on this model
    assert payload["max_tokens"] == DEEP_REASONING_DEFAULT_MAX_TOKENS


def test_stream_non_sse_content_type_is_error(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("NETMIND_API_KEY", "test-key-for-unit-tests-only")
    provider = NetMindProvider(external_data_allowed=True)
    _patch_urlopen(monkeypatch, b"{}" * 4, content_type="application/json")

    events = list(provider.stream_chat(LLMRequest(prompt="Chào em", model=NETMIND_CHAT_MODEL)))
    assert events[-1]["type"] == "error"
    assert events[-1]["code"] == "NOT_EVENT_STREAM"


# ------------------------------------------------------------------ router tiers
def test_router_fast_and_reasoning_default_to_glm():
    router = LLMRouter()
    d_chat = router.route("Chào em, hôm nay thế nào?")
    assert d_chat.tier == "fast"
    assert d_chat.model == NETMIND_CHAT_MODEL

    d_plan = router.route("Hãy lập kế hoạch chia nhỏ các bước thực thi DAG cho hệ thống")
    assert d_plan.tier == "reasoning"
    assert d_plan.model == NETMIND_CHAT_MODEL


def test_router_deep_tier_selection():
    router = LLMRouter()
    d_deep = router.route("Anh cần em phân tích chuyên sâu tài liệu kiến trúc này")
    assert d_deep.tier == "deep"
    assert d_deep.model == NETMIND_DEEP_REASONING_MODEL

    d_hint = router.route("Đọc báo cáo", task_hint="document_analysis")
    assert d_hint.tier == "deep"


def test_router_local_fallback_preserves_tier():
    router = LLMRouter()
    d = router.route("Hãy lập kế hoạch DAG cho hệ thống", available_models=["qwen2.5:0.5b", "qwen2.5:7b"])
    assert d.tier == "reasoning"  # tier preserved even when cloud target is absent
    assert d.model == "qwen2.5:7b"
    assert d.is_fallback is True


def test_router_fast_fallback_offline():
    router = LLMRouter()
    d = router.route("Chào em", available_models=["qwen2.5:0.5b"])
    assert d.tier == "fast"
    assert d.model == "qwen2.5:0.5b"
    assert d.is_fallback is True
