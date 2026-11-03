"""M6-B1 — HMAC enforcement tests (duyệt bởi Quanpt1 01/11/2026).

Kiểm chứng:
1. Request mang device header NHƯNG thiếu/ sai HMAC → 401 (fail-closed).
2. Request ký đúng bằng secret thật (cùng cơ chế daemon Pi) → 200.
3. Replay nonce đã dùng → 401.
4. Tốn ít thời gian, không đụng production server.
"""
from __future__ import annotations

import hashlib
import hmac as hmac_mod
import json
import os
import threading
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone

import pytest

from quan_ai_brain.web import server as srv
from quan_ai_brain.web.server import BrainAPIHandler, ThreadedHTTPServer


@pytest.fixture(scope="module")
def hmac_server():
    test_ws = os.environ.get("QUAN_AI_BRAIN_WORKSPACE")
    server = ThreadedHTTPServer(("127.0.0.1", 0), BrainAPIHandler)
    host, port = server.server_address
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    time.sleep(0.1)
    yield f"http://{host}:{port}"
    server.shutdown()
    server.server_close()
    if test_ws is not None:
        os.environ["QUAN_AI_BRAIN_WORKSPACE"] = test_ws


def _signed_headers(device_id: str, secret: str, payload: bytes = b"") -> dict[str, str]:
    """Tạo header ký đúng chuẩn EdgeHMACAuth (mô phỏng daemon Pi)."""
    from edge_client.auth import EdgeHMACAuth

    auth = EdgeHMACAuth(device_id=device_id, secret=secret)
    headers = auth.create_signed_headers(payload)
    headers["X-QuanAI-Device"] = device_id
    headers["X-QuanAI-Device-Id"] = device_id
    headers["X-Quan-Device-Id"] = device_id
    return headers


def _restore_secret(monkeypatch_env: dict[str, str]) -> None:
    pass


def test_edge_request_without_hmac_rejected_401(hmac_server: str, monkeypatch) -> None:
    """Device header có nhưng thiếu signature → 401 fail-closed."""
    monkeypatch.setenv("EDGE_HMAC_SECRET", "test-secret-m6b1")
    payload = json.dumps({"device_id": "EDGE-PI5-DESK-01", "rtt_ms": 10}).encode()
    req = urllib.request.Request(
        f"{hmac_server}/api/executive/edge/heartbeat",
        data=payload,
        headers={"Content-Type": "application/json", "X-QuanAI-Device": "EDGE-PI5-DESK-01"},
    )
    with pytest.raises(urllib.error.HTTPError) as excinfo:
        urllib.request.urlopen(req, timeout=5)
    assert excinfo.value.code == 401


def test_edge_request_wrong_secret_rejected_401(hmac_server: str, monkeypatch) -> None:
    """Ký bằng secret sai (kẻ tấn công) → 401."""
    monkeypatch.setenv("EDGE_HMAC_SECRET", "true-secret")
    payload = json.dumps({"device_id": "EDGE-PI5-DESK-01", "rtt_ms": 10}).encode()
    headers = _signed_headers("EDGE-PI5-DESK-01", "attacker-secret", payload)
    req = urllib.request.Request(
        f"{hmac_server}/api/executive/edge/heartbeat",
        data=payload,
        headers={**headers, "Content-Type": "application/json"},
    )
    with pytest.raises(urllib.error.HTTPError) as excinfo:
        urllib.request.urlopen(req, timeout=5)
    assert excinfo.value.code == 401


def test_edge_request_valid_hmac_accepted(hmac_server: str, monkeypatch) -> None:
    """Ký đúng secret (giống daemon Pi) → 200 + heartbeat ghi nhận."""
    monkeypatch.setenv("EDGE_HMAC_SECRET", "true-secret")
    payload = json.dumps({
        "device_id": "EDGE-PI5-DESK-01",
        "rtt_ms": 12.4,
        "subsystems_ready": True,
        "telemetry": {"temp_c": 42.1},
    }).encode()
    headers = _signed_headers("EDGE-PI5-DESK-01", "true-secret", payload)
    req = urllib.request.Request(
        f"{hmac_server}/api/executive/edge/heartbeat",
        data=payload,
        headers={**headers, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode())
    assert data["success"] is True
    assert data["edge_status"]["state"] == "READY"


def test_edge_replay_nonce_rejected_401(hmac_server: str, monkeypatch) -> None:
    """Gửi lại cùng request (replay) → 401 do nonce đã dùng."""
    monkeypatch.setenv("EDGE_HMAC_SECRET", "true-secret")
    payload = json.dumps({"device_id": "EDGE-PI5-DESK-01", "rtt_ms": 5}).encode()
    headers = _signed_headers("EDGE-PI5-DESK-01", "true-secret", payload)

    req1 = urllib.request.Request(
        f"{hmac_server}/api/executive/edge/heartbeat",
        data=payload,
        headers={**headers, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req1, timeout=5) as resp:
        assert resp.status == 200

    # Replay cùng headers (cùng nonce)
    req2 = urllib.request.Request(
        f"{hmac_server}/api/executive/edge/heartbeat",
        data=payload,
        headers={**headers, "Content-Type": "application/json"},
    )
    with pytest.raises(urllib.error.HTTPError) as excinfo:
        urllib.request.urlopen(req2, timeout=5)
    assert excinfo.value.code == 401


def test_ui_request_without_device_header_unaffected(hmac_server: str) -> None:
    """Traffic UI thường (không device header) không bị ảnh hưởng."""
    req = urllib.request.Request(f"{hmac_server}/api/executive/overview")
    with urllib.request.urlopen(req, timeout=5) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode())
    assert data["success"] is True


def test_secret_file_source_monkeypatched(hmac_server: str, monkeypatch, tmp_path) -> None:
    """_load_edge_hmac_secret ưu tiên env, fallback file."""
    monkeypatch.delenv("EDGE_HMAC_SECRET", raising=False)
    secret_file = tmp_path / "edge_hmac_secret.txt"
    secret_file.write_text("file-secret\n", encoding="utf-8")
    monkeypatch.setattr(srv, "_EDGE_HMAC_SECRET_FILE", secret_file)
    assert srv._load_edge_hmac_secret() == "file-secret"

    monkeypatch.setenv("EDGE_HMAC_SECRET", "env-secret")
    assert srv._load_edge_hmac_secret() == "env-secret"
