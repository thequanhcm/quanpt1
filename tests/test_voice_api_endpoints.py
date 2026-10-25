"""Tests for Voice Wake Word REST API and static asset serving."""
from __future__ import annotations

import json
from pathlib import Path
import threading
import time
import urllib.request

import pytest

from quan_ai_brain.web.server import BrainAPIHandler, ThreadedHTTPServer


@pytest.fixture(scope="module")
def voice_server_instance(tmp_path_factory: pytest.TempPathFactory):
    test_workspace = tmp_path_factory.mktemp("voice_workspace")
    (test_workspace / "data").mkdir(parents=True, exist_ok=True)

    server = ThreadedHTTPServer(("127.0.0.1", 0), BrainAPIHandler)
    host, port = server.server_address
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    base_url = f"http://{host}:{port}"
    time.sleep(0.1)

    yield base_url

    server.shutdown()
    server.server_close()


def test_wake_engine_js_served(voice_server_instance: str) -> None:
    req = urllib.request.Request(f"{voice_server_instance}/static/wake_engine.js")
    with urllib.request.urlopen(req, timeout=5.0) as resp:
        assert resp.status == 200
        content = resp.read().decode("utf-8")
        assert "class WakeWordEngine" in content
        assert "AudioContext" in content


def test_get_wake_config(voice_server_instance: str) -> None:
    req = urllib.request.Request(f"{voice_server_instance}/api/voice/wake-config")
    with urllib.request.urlopen(req, timeout=5.0) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["success"] is True
        config = data["config"]
        assert "enabled" in config
        assert "wake_words" in config
        assert isinstance(config["wake_words"], list)
        assert len(config["wake_words"]) >= 10
        assert any(w["phrase"].lower() == "hi tony" for w in config["wake_words"])


def test_update_wake_config(voice_server_instance: str) -> None:
    payload = {
        "enabled": True,
        "language_mode": "vi-VN",
        "silence_timeout_sec": 25.0,
        "chime_enabled": True,
    }
    body_bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{voice_server_instance}/api/voice/wake-config",
        data=body_bytes,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=5.0) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["success"] is True
        config = data["config"]
        assert config["enabled"] is True
        assert config["language_mode"] == "vi-VN"
        assert config["silence_timeout_sec"] == 25.0

    # Verify persistent state via GET
    req_get = urllib.request.Request(f"{voice_server_instance}/api/voice/wake-config")
    with urllib.request.urlopen(req_get, timeout=5.0) as resp_get:
        data_get = json.loads(resp_get.read().decode("utf-8"))
        assert data_get["config"]["enabled"] is True


def test_voice_telemetry(voice_server_instance: str) -> None:
    payload = {
        "state": "WAKE_DETECTED",
        "event": "wake_match",
        "keyword": "hi tony",
    }
    body_bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{voice_server_instance}/api/voice/telemetry",
        data=body_bytes,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=5.0) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["success"] is True


def test_voice_interact_endpoint(voice_server_instance: str) -> None:
    payload = {
        "query": "Hi TONY",
        "is_push_to_talk": False,
    }
    body_bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{voice_server_instance}/api/voice/interact",
        data=body_bytes,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10.0) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["success"] is True
        assert "response_text" in data
        assert "spoken_text" in data
        assert data["has_audio"] is True
        assert data["audio_base64"] is not None
        assert "mouth_timeline" in data

