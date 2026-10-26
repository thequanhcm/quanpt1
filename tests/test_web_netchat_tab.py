"""Tests for the Executive Dashboard NetChat management endpoints (tab-netchat).

These tests never talk to the real NetChat server and never touch the bot
token: the bridge module is monkeypatched with in-memory fakes. The bridge
itself shells out to the netchat skill script only in production use.
"""
from __future__ import annotations

import json
import threading
import time
import urllib.request

import pytest

from quan_ai_brain.web.server import BrainAPIHandler, ThreadedHTTPServer


@pytest.fixture(scope="module")
def netchat_server_url(tmp_path_factory: pytest.TempPathFactory):
    test_workspace = tmp_path_factory.mktemp("netchat_ws")
    (test_workspace / "data").mkdir(parents=True, exist_ok=True)

    server = ThreadedHTTPServer(("127.0.0.1", 0), BrainAPIHandler)
    host, port = server.server_address
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    time.sleep(0.1)
    yield f"http://{host}:{port}"
    server.shutdown()
    server.server_close()


@pytest.fixture()
def fake_bridge(monkeypatch):
    """Patch the bridge functions the server handlers import."""
    import quan_ai_brain.integration.netchat_bridge as bridge

    monkeypatch.setattr(
        bridge,
        "get_status",
        lambda channel_id=bridge.DEFAULT_CHANNEL_ID: {
            "success": True,
            "bot": {"id": "bot-id-123", "username": "bot_quanpt1", "is_bot": True},
            "channel": {"id": channel_id, "name": "Trợ lý Tony Pham"},
            "checked_at_utc": "2026-10-26T00:00:00+00:00",
        },
        raising=True,
    )
    monkeypatch.setattr(
        bridge,
        "get_messages",
        lambda channel_id, count=20: {
            "success": True,
            "channel_id": channel_id,
            "messages": [
                {"id": "m2", "user_id": "owner", "sender": "owner",
                 "message": "trạng thái", "create_at": 1793030000000},
                {"id": "m1", "user_id": "bot", "sender": "bot",
                 "message": "📊 HIỆN TRẠNG…", "create_at": 1793030001000},
            ],
        },
        raising=True,
    )
    monkeypatch.setattr(
        bridge,
        "send_message",
        lambda channel_id, text: {"success": True, "post_id": "new_post_1", "channel_id": channel_id},
        raising=True,
    )
    monkeypatch.setattr(
        bridge,
        "run_command",
        lambda text: {
            "success": True,
            "intent": "status" if "trạng thái" in text else None,
            "response": "📊 HIỆN TRẠNG (fake)…",
            "note": "",
        },
        raising=True,
    )
    return bridge


def test_netchat_status_endpoint(netchat_server_url: str, fake_bridge) -> None:
    with urllib.request.urlopen(f"{netchat_server_url}/api/executive/netchat/status", timeout=5) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
    assert data["success"] is True
    assert data["bot"]["username"] == "bot_quanpt1"
    assert data["channel"]["name"] == "Trợ lý Tony Pham"


def test_netchat_messages_endpoint(netchat_server_url: str, fake_bridge) -> None:
    with urllib.request.urlopen(f"{netchat_server_url}/api/executive/netchat/messages?count=5", timeout=5) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
    assert data["success"] is True
    assert isinstance(data["messages"], list)
    assert data["messages"][0]["sender"] in ("bot", "owner")


def test_netchat_send_endpoint(netchat_server_url: str, fake_bridge) -> None:
    payload = json.dumps({"message": "Test từ dashboard"}).encode("utf-8")
    req = urllib.request.Request(
        f"{netchat_server_url}/api/executive/netchat/send",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
    assert data["success"] is True
    assert data["post_id"] == "new_post_1"


def test_netchat_command_endpoint(netchat_server_url: str, fake_bridge) -> None:
    payload = json.dumps({"command": "trạng thái"}).encode("utf-8")
    req = urllib.request.Request(
        f"{netchat_server_url}/api/executive/netchat/command",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
    assert data["success"] is True
    assert data["intent"] == "status"
    assert "HIỆN TRẠNG" in data["response"]


def test_netchat_tab_in_executive_html(netchat_server_url: str) -> None:
    with urllib.request.urlopen(f"{netchat_server_url}/executive.html", timeout=5) as resp:
        content = resp.read().decode("utf-8")
    assert "tab-netchat" in content
    assert "Quản Trị Kênh NetChat" in content
    assert "netchat-avatar-canvas" in content


# ---------------------------------------------------------------------------
# Bridge unit tests (REAL logic — validation & routing don't need subprocess)
# ---------------------------------------------------------------------------


def test_bridge_send_rejects_empty() -> None:
    import quan_ai_brain.integration.netchat_bridge as bridge

    with pytest.raises(bridge.NetChatBridgeError):
        bridge.send_message("chan", "   ")


def test_bridge_send_rejects_too_long() -> None:
    import quan_ai_brain.integration.netchat_bridge as bridge

    with pytest.raises(bridge.NetChatBridgeError):
        bridge.send_message("chan", "x" * 4000)


def test_bridge_run_command_routes_intent() -> None:
    import quan_ai_brain.integration.netchat_bridge as bridge

    result = bridge.run_command("giúp")
    assert result["success"] is True
    assert result["intent"] == "help"

    result2 = bridge.run_command("1 + 1 bằng mấy?")
    assert result2["intent"] is None
    assert "không phải lệnh" in result2["note"].lower()


def test_bridge_run_command_question_never_approves() -> None:
    import quan_ai_brain.integration.netchat_bridge as bridge

    result = bridge.run_command("anh có thể phê duyệt qua kênh được không?")
    assert result["success"] is True
    assert result["intent"] is None  # safety: question must not execute
