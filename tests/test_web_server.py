"""Tests for QUAN AI BRAIN Local Web UI Server."""
from __future__ import annotations

import json
import os
from pathlib import Path
import threading
import time
import urllib.request

import pytest

from quan_ai_brain.web.server import BrainAPIHandler, ThreadedHTTPServer


@pytest.fixture(scope="module")
def web_server_instance(tmp_path_factory: pytest.TempPathFactory):
    test_workspace = tmp_path_factory.mktemp("web_workspace")
    (test_workspace / "data").mkdir(parents=True, exist_ok=True)

    # V6 hotfix (27/10/2026): isolate workspace — handler POST /api/plan
    # phải ghi vào tasks.db của test workspace, KHÔNG ghi vào production DB
    # (nguồn gốc 294 task trùng lặp 'năng lượng' — daemon chạy pytest mỗi cycle).
    old_env = os.environ.get("QUAN_AI_BRAIN_WORKSPACE")
    os.environ["QUAN_AI_BRAIN_WORKSPACE"] = str(test_workspace)

    # Find free port
    server = ThreadedHTTPServer(("127.0.0.1", 0), BrainAPIHandler)
    host, port = server.server_address
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    base_url = f"http://{host}:{port}"
    time.sleep(0.1)

    yield base_url

    server.shutdown()
    server.server_close()

    # Restore env
    if old_env is None:
        os.environ.pop("QUAN_AI_BRAIN_WORKSPACE", None)
    else:
        os.environ["QUAN_AI_BRAIN_WORKSPACE"] = old_env


def test_web_server_serves_html(web_server_instance: str) -> None:
    req = urllib.request.Request(f"{web_server_instance}/")
    with urllib.request.urlopen(req, timeout=5.0) as resp:
        assert resp.status == 200
        content = resp.read().decode("utf-8")
        assert "QUAN AI BRAIN" in content
        assert "tony-avatar-canvas" in content
        assert "avatar-waveform-canvas" in content
        assert "avatar_engine.js" in content
        assert "Loa Raspberry Pi 5" in content


def test_web_server_api_status(web_server_instance: str) -> None:
    req = urllib.request.Request(f"{web_server_instance}/api/status")
    with urllib.request.urlopen(req, timeout=5.0) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data.get("success") is True
        assert "system" in data
        assert "llm" in data


def test_web_server_api_memories(web_server_instance: str) -> None:
    req = urllib.request.Request(f"{web_server_instance}/api/memories")
    with urllib.request.urlopen(req, timeout=5.0) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data.get("success") is True
        assert isinstance(data.get("memories"), list)


def test_edge_control_speak_audio_forwarding(web_server_instance: str) -> None:
    payload = json.dumps({
        "action": "speak",
        "text": "Xin chào Anh Quanpt1, em đang nói trên loa Pi 5!",
        "state": "SPEAKING",
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{web_server_instance}/api/executive/edge/control",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10.0) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data.get("success") is True
        assert data.get("action") == "speak"
        assert "timeline" in data
        assert data.get("has_audio") is True


def test_edge_daemon_state_audio_propagation() -> None:
    from edge_client.client_daemon import EdgeDaemonState
    from edge_client.config import EdgeConfig

    cfg = EdgeConfig()
    state = EdgeDaemonState(cfg)
    state.core_connected = True
    state.pending_audio_base64 = "UklGRiQAAABXQVZFZm10"
    state.pending_timeline = {"frames": [{"time_ms": 0, "viseme": "A"}]}

    d = state.to_kiosk_dict()
    assert d["pending_audio_base64"] == "UklGRiQAAABXQVZFZm10"
    assert d["pending_timeline"] == {"frames": [{"time_ms": 0, "viseme": "A"}]}

    # Verify reset after retrieval
    d2 = state.to_kiosk_dict()
    assert d2["pending_audio_base64"] is None
    assert d2["pending_timeline"] is None


def test_web_server_api_plan_with_durable_task(web_server_instance: str) -> None:
    payload = json.dumps({
        "goal": "Thu thập báo cáo năng lượng trung tâm dữ liệu",
        "scope": "datacenter",
        "allow_fallback": True,
        "model": "mock",
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{web_server_instance}/api/plan",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30.0) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data.get("success") is True
        assert "plan" in data
        assert "durable_task" in data
        durable = data["durable_task"]
        assert durable is not None
        assert durable["task_id"].startswith("task_")
        assert durable["goal"] == "Thu thập báo cáo năng lượng trung tâm dữ liệu"




