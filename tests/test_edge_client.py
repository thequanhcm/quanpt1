"""Unit tests for QUAN AI BRAIN — Raspberry Pi 5 Edge Client.

Validates EdgeConfig, EdgeHMACAuth anti-replay protection, fail-safe disconnect behavior,
and local Kiosk UI serving.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import time
import urllib.request

import pytest

from edge_client.auth import EdgeHMACAuth
from edge_client.client_daemon import EdgeClientDaemon, EdgeDaemonState
from edge_client.config import EdgeConfig


def test_edge_config_defaults_and_file_io(tmp_path: Path) -> None:
    config = EdgeConfig()
    assert config.device_id == "EDGE-PI5-DESK-01"
    assert config.core_port == 8766
    assert config.kiosk_port == 8768
    assert config.core_base_url == "http://127.0.0.1:8766"
    assert config.kiosk_url == "http://127.0.0.1:8768"

    # Save and reload
    cfg_file = tmp_path / "test_config.json"
    config.device_id = "EDGE-PI5-MEETING-ROOM"
    config.core_host = "192.168.1.100"
    config.save_to_file(cfg_file)

    loaded = EdgeConfig.load_from_file(cfg_file)
    assert loaded.device_id == "EDGE-PI5-MEETING-ROOM"
    assert loaded.core_host == "192.168.1.100"
    assert loaded.core_base_url == "http://192.168.1.100:8766"


def test_edge_hmac_auth_signing_and_verification() -> None:
    auth = EdgeHMACAuth(device_id="EDGE-PI5-TEST", secret="SUPER_SECRET_KEY", max_drift_seconds=5.0)

    payload = b'{"action": "test"}'
    headers = auth.create_signed_headers(payload)

    assert headers[EdgeHMACAuth.HEADER_DEVICE_ID] == "EDGE-PI5-TEST"
    assert len(headers[EdgeHMACAuth.HEADER_NONCE]) >= 32
    assert len(headers[EdgeHMACAuth.HEADER_SIGNATURE]) == 64

    # Valid verification
    ok, reason = auth.verify_request(headers, payload)
    assert ok is True
    assert reason == "VALID"

    # Forged signature fails
    headers_forged = auth.create_signed_headers(payload)
    headers_forged[EdgeHMACAuth.HEADER_SIGNATURE] = "0" * 64
    ok2, reason2 = auth.verify_request(headers_forged, payload)
    assert ok2 is False
    assert reason2 == "INVALID_SIGNATURE"

    # Tampered payload fails
    headers_tampered = auth.create_signed_headers(payload)
    ok3, reason3 = auth.verify_request(headers_tampered, b'{"action": "tampered"}')
    assert ok3 is False
    assert reason3 == "INVALID_SIGNATURE"


def test_edge_hmac_auth_replay_prevention() -> None:
    auth = EdgeHMACAuth(device_id="EDGE-PI5-TEST", secret="SUPER_SECRET_KEY")
    payload = b"test_nonce_replay"
    headers = auth.create_signed_headers(payload)

    # First attempt: valid
    ok1, reason1 = auth.verify_request(headers, payload)
    assert ok1 is True
    assert reason1 == "VALID"

    # Replay attempt with same nonce: must fail
    ok2, reason2 = auth.verify_request(headers, payload)
    assert ok2 is False
    assert reason2 == "REPLAY_DETECTED_NONCE_ALREADY_USED"


def test_edge_hmac_auth_clock_drift() -> None:
    auth = EdgeHMACAuth(device_id="EDGE-PI5-TEST", secret="SUPER_SECRET_KEY", max_drift_seconds=5.0)

    payload = b"drift_test"
    headers = auth.create_signed_headers(payload)

    # Simulate request received 12 seconds later
    current_time = time.time() + 12.0
    ok, reason = auth.verify_request(headers, payload, current_time_epoch=current_time)
    assert ok is False
    assert "CLOCK_DRIFT_EXCEEDED" in reason


def test_edge_client_daemon_local_kiosk_endpoints() -> None:
    # Use ephemeral port for kiosk server
    config = EdgeConfig(
        device_id="EDGE-PI5-TEST-DAEMON",
        kiosk_host="127.0.0.1",
        kiosk_port=0,
        core_host="127.0.0.1",
        core_port=9999,  # Intentionally offline core
    )
    daemon = EdgeClientDaemon(config)
    daemon.start()

    # Get bound port
    assert daemon._server is not None
    _, actual_port = daemon._server.server_address
    base_url = f"http://127.0.0.1:{actual_port}"

    try:
        # 1. Test Kiosk HTML served
        req_html = urllib.request.Request(f"{base_url}/kiosk.html")
        with urllib.request.urlopen(req_html, timeout=3.0) as resp:
            assert resp.status == 200
            content = resp.read().decode("utf-8")
            assert "kiosk-avatar-canvas" in content
            assert "btn-touch-stop" in content
            assert "offline-overlay" in content

        # 2. Test Kiosk CSS served
        req_css = urllib.request.Request(f"{base_url}/kiosk.css")
        with urllib.request.urlopen(req_css, timeout=3.0) as resp:
            assert resp.status == 200
            assert "kiosk-avatar-viewport" in resp.read().decode("utf-8")

        # 3. Test Kiosk JS served
        req_js = urllib.request.Request(f"{base_url}/kiosk.js")
        with urllib.request.urlopen(req_js, timeout=3.0) as resp:
            assert resp.status == 200
            assert "pollDaemonStatus" in resp.read().decode("utf-8")

        # 3b. Test Avatar Engine JS served
        req_engine = urllib.request.Request(f"{base_url}/avatar_engine.js")
        with urllib.request.urlopen(req_engine, timeout=3.0) as resp:
            assert resp.status == 200
            assert "DigitalHumanAvatar" in resp.read().decode("utf-8")

        # 4. Test Kiosk Status API
        req_status = urllib.request.Request(f"{base_url}/api/kiosk/status")
        with urllib.request.urlopen(req_status, timeout=3.0) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert data["device_id"] == "EDGE-PI5-TEST-DAEMON"
            assert "core_connected" in data
            assert "avatar_state" in data
            assert "kiosk_running" in data
            assert "embodiment_mode" in data

        # 5. Test Start Kiosk Remote Control API
        req_start = urllib.request.Request(
            f"{base_url}/api/kiosk/control",
            data=json.dumps({"action": "start_kiosk"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req_start, timeout=3.0) as resp:
            assert resp.status == 200
            start_data = json.loads(resp.read().decode("utf-8"))
            assert start_data["success"] is True
            assert start_data["kiosk_running"] is True
            assert start_data["embodiment_mode"] == "ACTIVE"

        # 6. Test Close Kiosk Remote Control API
        req_close = urllib.request.Request(
            f"{base_url}/api/kiosk/control",
            data=json.dumps({"action": "close_kiosk"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req_close, timeout=3.0) as resp:
            assert resp.status == 200
            close_data = json.loads(resp.read().decode("utf-8"))
            assert close_data["success"] is True
            assert close_data["kiosk_running"] is False
            assert close_data["embodiment_mode"] == "STANDBY"


    finally:
        daemon.stop()


def test_edge_client_daemon_fail_safe_disconnect() -> None:
    # Test that when Core is unreachable, daemon safely marks state as OFFLINE
    config = EdgeConfig(
        device_id="EDGE-PI5-OFFLINE-TEST",
        core_host="127.0.0.1",
        core_port=59999,  # Dead port
        heartbeat_timeout_sec=0.5,
    )
    daemon = EdgeClientDaemon(config)
    # Check connection directly
    connected = daemon.check_core_connection()
    assert connected is False

    kiosk_state = daemon.state.to_kiosk_dict()
    assert kiosk_state["core_connected"] is False
    assert kiosk_state["avatar_state"] == "OFFLINE"


def test_edge_actuators_relay_and_motion() -> None:
    from edge_client.actuators import ActuatorController

    controller = ActuatorController()
    status = controller.get_status()
    assert len(status["relays"]) == 8
    assert len(status["joints"]) == 6
    assert status["relays"]["relay_1"]["state"] == "OPEN"

    # 1. Switch Relay State
    res = controller.set_relay("relay_1", "CLOSED")
    assert res["success"] is True
    assert res["state"] == "CLOSED"
    assert controller.relays["relay_1"].state == "CLOSED"

    # 2. Set Joint Angle
    j_res = controller.set_joint_angle("head_yaw", 120.0)
    assert j_res["success"] is True
    assert j_res["angle"] == 120.0

    # Test clamping
    j_clamp = controller.set_joint_angle("head_yaw", 250.0)
    assert j_clamp["angle"] == 180.0

    # 3. Emergency Kill Switch (all stop)
    stop_res = controller.emergency_all_stop()
    assert stop_res["success"] is True
    assert stop_res["relays_open_count"] == 8
    assert controller.relays["relay_1"].state == "OPEN"
    assert controller.joints["head_yaw"].current_angle == 90.0


def test_edge_pairing_api_handshake() -> None:
    from quan_ai_brain.web.server import BrainAPIHandler, ThreadedHTTPServer
    import threading

    server = ThreadedHTTPServer(("127.0.0.1", 0), BrainAPIHandler)
    host, port = server.server_address
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    base_url = f"http://{host}:{port}"
    time.sleep(0.05)

    try:
        # 1. Invalid PIN -> must be rejected with 403
        bad_payload = json.dumps({
            "device_id": "EDGE-PI5-TEST",
            "device_label": "Test Kiosk",
            "pairing_pin": "WRONG_PIN",
        }).encode("utf-8")
        req_bad = urllib.request.Request(
            f"{base_url}/api/edge/pair",
            data=bad_payload,
            headers={"Content-Type": "application/json"},
        )
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(req_bad, timeout=3.0)
        assert exc_info.value.code == 403

        # 2. Valid PIN -> succeeds and generates shared secret
        good_payload = json.dumps({
            "device_id": "EDGE-PI5-TEST-OK",
            "device_label": "Test Kiosk OK",
            "pairing_pin": "888666",
        }).encode("utf-8")
        req_good = urllib.request.Request(
            f"{base_url}/api/edge/pair",
            data=good_payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req_good, timeout=3.0) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert data["success"] is True
            assert data["device_id"] == "EDGE-PI5-TEST-OK"
            assert len(data["shared_secret"]) == 64  # 32 bytes hex
            assert "core_host" in data
            assert data["core_port"] == 8766

        # 3. Check supervisor reflects paired status
        req_sup = urllib.request.Request(f"{base_url}/api/executive/supervisor")
        with urllib.request.urlopen(req_sup, timeout=3.0) as resp_sup:
            assert resp_sup.status == 200
            sup_data = json.loads(resp_sup.read().decode("utf-8"))
            assert sup_data["edge_device"]["paired"] is True
            assert sup_data["edge_device"]["status"] in ("READY", "ONLINE_PAIRED")

    finally:
        server.shutdown()
        server.server_close()


def test_pi5_7inch_dsi_and_micro_expressions() -> None:
    root = Path(__file__).resolve().parent.parent

    # 1. Verify one-click runner for 7-inch DSI Touchscreen 2
    oneclick_sh = root / "edge_client" / "oneclick_run_pi5.sh"
    assert oneclick_sh.exists()
    content_sh = oneclick_sh.read_text(encoding="utf-8")
    assert "1280x720" in content_sh
    assert "setup_pi5.py" in content_sh

    # 2. Verify config.json resolution and avatar version
    cfg_file = root / "edge_client" / "config.json"
    assert cfg_file.exists()
    cfg_data = json.loads(cfg_file.read_text(encoding="utf-8"))
    assert cfg_data["screen_width"] == 1280
    assert cfg_data["screen_height"] == 720
    assert cfg_data["avatar_version"] in ("digital_human_model_f_v1", "digital_human_model_a_v1")

    # 3. Verify Micro-Expression Engine in avatar_engine.js (both Core & Edge)
    for p in [
        root / "src" / "quan_ai_brain" / "web" / "static" / "avatar_engine.js",
        root / "edge_client" / "avatar_engine.js",
    ]:
        assert p.exists()
        code = p.read_text(encoding="utf-8")
        assert "extractVietnameseEmotion" in code
        assert "setContextFromText" in code
        assert "_renderEyebrows" in code
        assert "WARM_GREETING" in code
        assert "ANALYTICAL_THINKING" in code
        assert "SERIOUS_ALERT" in code


