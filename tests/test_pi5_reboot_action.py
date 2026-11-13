"""Sprint-1314 — Bổ sung chức năng Khởi động lại Pi 5 (Safe Reboot).

Test 3 lớp:
1. Daemon Pi5: action=reboot_pi → ACK ngay + gọi sudo reboot (mock) + payload đúng.
2. PC forward: /api/executive/edge/control action=reboot_pi → 200 + message VN.
3. Modal HTML: có 3 thẻ opt-reboot-pi / opt-close-kiosk / opt-poweroff-pi.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.request

import pytest

# Cho phép import edge_client (không phải package chuẩn)
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(_REPO_ROOT, "edge_client"))

import client_daemon as cd  # noqa: E402


# ---- 1. Daemon Pi5: handler reboot_pi ----

class _MockState:
    lock = threading.Lock()
    avatar_state = "IDLE"
    transcript = ""


class _MockHandler:
    daemon_state = _MockState()

    def _send_json(self, payload):
        self._last_response = payload

    def _send_error_json(self, msg, code=400):
        self._last_response = {"success": False, "error": msg, "code": code}


def test_daemon_reboot_pi_action_acks_and_invokes_sudo(monkeypatch):
    """reboot_pi: ACK ngay + gọi subprocess.run(['sudo', 'reboot']) + payload đúng."""
    calls: list[list[str]] = []

    def _fake_run(cmd, *a, **kw):
        calls.append(list(cmd))
        return subprocess.CompletedProcess(cmd, 0, b"", b"")

    # Handler dùng `import subprocess` cục bộ → patch module subprocess toàn cục
    import subprocess as _sp
    monkeypatch.setattr(_sp, "run", _fake_run)

    h = _MockHandler()
    cd.KioskHTTPHandler._handle_api_kiosk_remote_control(h, {"action": "reboot_pi"})

    # ACK ngay (không chặn)
    assert h._last_response["success"] is True
    assert h._last_response["action"] == "reboot_pi"
    assert "khởi động lại" in h._last_response["message"].lower()
    assert h._last_response["expected_downtime_sec"] == 20
    # subprocess.run(['sudo', 'reboot']) đã được gọi (chạy trong thread nền
    # SAU time.sleep(1.5) — đợi đủ 1.7s)
    time.sleep(1.7)
    assert any(cmd[:2] == ["sudo", "reboot"] for cmd in calls), f"calls={calls}"


def test_daemon_reboot_pi_does_not_block_response(monkeypatch):
    """reboot_pi KHÔNG chặn HTTP response (sudo chạy nền sau 1.5s)."""
    started = time.time()

    def _slow_run(cmd, *a, **kw):
        time.sleep(2.0)  # giả lập sudo chậm
        return subprocess.CompletedProcess(cmd, 0, b"", b"")

    import subprocess as _sp
    monkeypatch.setattr(_sp, "run", _slow_run)

    h = _MockHandler()
    cd.KioskHTTPHandler._handle_api_kiosk_remote_control(h, {"action": "reboot_pi"})
    elapsed = time.time() - started
    assert elapsed < 0.5, f"reboot_pi chặn response {elapsed:.2f}s — phải ACK ngay"


def test_daemon_reboot_pi_sets_offline_state():
    """reboot_pi: avatar_state=OFFLINE + transcript thông báo reboot."""
    h = _MockHandler()
    cd.KioskHTTPHandler._handle_api_kiosk_remote_control(h, {"action": "reboot_pi"})
    assert h.daemon_state.avatar_state == "OFFLINE"
    assert "khởi động lại" in h.daemon_state.transcript.lower()


# ---- 2. PC forward: /api/executive/edge/control ----

@pytest.fixture()
def pc_server(tmp_path):
    from quan_ai_brain.web.server import BrainAPIHandler, ThreadedHTTPServer
    workspace = tmp_path / "ws"
    (workspace / "data").mkdir(parents=True, exist_ok=True)
    old_env = os.environ.get("QUAN_AI_BRAIN_WORKSPACE")
    os.environ["QUAN_AI_BRAIN_WORKSPACE"] = str(workspace)
    srv = ThreadedHTTPServer(("127.0.0.1", 0), BrainAPIHandler)
    host, port = srv.server_address
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    time.sleep(0.1)
    yield f"http://{host}:{port}"
    srv.shutdown()
    srv.server_close()
    if old_env is None:
        os.environ.pop("QUAN_AI_BRAIN_WORKSPACE", None)
    else:
        os.environ["QUAN_AI_BRAIN_WORKSPACE"] = old_env


def test_pc_forward_reboot_pi_returns_200_with_vn_message(pc_server):
    """PC forward reboot_pi: 200 + message VN + expected_downtime_sec."""
    req = urllib.request.Request(
        f"{pc_server}/api/executive/edge/control",
        data=json.dumps({"action": "reboot_pi"}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=8.0) as resp:
        assert resp.status == 200
        body = json.loads(resp.read().decode("utf-8"))
    assert body["success"] is True
    assert body["action"] == "reboot_pi"
    assert "khởi động lại" in body["message"].lower()
    assert body["expected_downtime_sec"] == 20
    # pi5_result có thể fail (Pi5 offline) — nhưng route phải nhận đúng action
    assert "pi5_result" in body


# ---- 3. Modal HTML: 3 thẻ ----

def test_modal_html_has_three_options():
    """Modal phải có đủ 3 thẻ: opt-reboot-pi, opt-close-kiosk, opt-poweroff-pi."""
    html_path = os.path.join(_REPO_ROOT, "src", "quan_ai_brain", "web", "static", "executive.html")
    html = open(html_path, encoding="utf-8").read()
    assert 'id="opt-reboot-pi"' in html, "thiếu thẻ opt-reboot-pi"
    assert 'id="opt-close-kiosk"' in html, "thiếu thẻ opt-close-kiosk"
    assert 'id="opt-poweroff-pi"' in html, "thiếu thẻ opt-poweroff-pi"
    # Tiêu đề modal đổi từ "Tắt Hình Thể / Nguồn" → "Nguồn Pi 5"
    assert "Quản Trị Nguồn Pi 5" in html
    assert "Quản Trị Tắt Hình Thể / Nguồn Pi 5" not in html
    # Nhãn thẻ reboot
    assert "Khởi Động Lại Pi 5" in html
    assert "Safe Reboot" in html


def test_modal_js_handles_reboot_pi():
    """JS phải có handler cho opt-reboot-pi gọi /api/executive/edge/control."""
    js_path = os.path.join(_REPO_ROOT, "src", "quan_ai_brain", "web", "static", "executive.js")
    js = open(js_path, encoding="utf-8").read()
    assert 'getElementById("opt-reboot-pi")' in js
    # Handler gọi action=reboot_pi (regex rộng để bám qua nhiều dòng)
    assert re.search(r'optRebootPi[\s\S]{0,2000}action:\s*"reboot_pi"', js), \
        "thiếu handler gọi action=reboot_pi"
