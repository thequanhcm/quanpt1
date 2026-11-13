# -*- coding: utf-8 -*-
"""Test 13/11: Truyền tin 2 chiều PC ↔ Pi 5 (yêu cầu owner image_347232).

Owner: 'cấu hình mục truyền tin để anh có thể copy hoặc lưu trữ tập tin qua lại
giữa Pi5 và máy tính này. có thể gửi cả các file đính kèm, hình ảnh qua lại'.

Kiểm tra:
1. PC-side endpoint /api/executive/edge/files/download — proxy Pi5 + fallback
   PC-local khi Pi5 offline (mock _send_edge_request).
2. Pi-side handler _handle_api_kiosk_download_file — barrier nhạy cảm, whitelist
   ext, traversal chặn, đọc đúng file (test thuần qua instance handler mock).
3. Đầy đủ chu trình upload (đã có) + download (mới) với file hình ảnh thật.
"""
from __future__ import annotations

import base64
import importlib.util
import json
import os
import sys
import threading
import time
import urllib.request
from pathlib import Path
from unittest import mock

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))


# ---------------------------------------------------------------------------
# 1) Pi-side handler: test thuần logic (không mở socket thật)
# ---------------------------------------------------------------------------
def _load_daemon_module():
    """Import edge_client/client_daemon.py như một module độc lập."""
    spec = importlib.util.spec_from_file_location(
        "client_daemon_test", REPO / "edge_client" / "client_daemon.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _FakeHandler:
    """Bắt chước phần handler cần thiết của KioskRequestHandler (không mở socket)."""

    def __init__(self, static_dir: Path):
        self.STATIC_DIR = static_dir
        self.captured = None
        self.error = None

    def _send_json(self, payload: dict) -> None:
        self.captured = payload

    def _send_error_json(self, msg: str, code: int) -> None:
        self.error = {"error": msg, "code": code}


def _make_handler(static_dir: Path):
    mod = _load_daemon_module()
    # Method download đọc module-global STATIC_DIR — patch về static_dir của test
    patcher = mock.patch.object(mod, "STATIC_DIR", static_dir)
    patcher.start()
    # Lấy class handler thật nhưng chỉ dùng method download (chưa init socket)
    handler_cls = None
    for name in dir(mod):
        obj = getattr(mod, name)
        if isinstance(obj, type) and hasattr(obj, "_handle_api_kiosk_download_file"):
            handler_cls = obj
            break
    assert handler_cls is not None, "không tìm thấy handler chứa download"
    inst = _FakeHandler(static_dir)
    # Gắn method thật vào fake instance (unbound call)
    inst.DOWNLOAD_ALLOWED_EXTS = handler_cls.DOWNLOAD_ALLOWED_EXTS
    inst._handle_api_kiosk_download_file = (
        lambda raw_path: handler_cls._handle_api_kiosk_download_file(inst, raw_path))
    return inst


def test_pi_download_ok(tmp_path: Path) -> None:
    static_dir = tmp_path / "edge"
    avatar = static_dir / "assets" / "avatar"
    avatar.mkdir(parents=True)
    (avatar / "anh_test.png").write_bytes(b"\x89PNG-fake-image-1234")

    h = _make_handler(static_dir)
    h._handle_api_kiosk_download_file("/api/kiosk/files/download?name=anh_test.png")
    assert h.error is None
    assert h.captured is not None
    assert h.captured["success"] is True
    assert h.captured["filename"] == "anh_test.png"
    assert base64.b64decode(h.captured["content_b64"]) == b"\x89PNG-fake-image-1234"
    assert h.captured["source"] == "assets\\avatar\\anh_test.png" or "anh_test.png" in h.captured["source"]


def test_pi_download_blocked_sensitive(tmp_path: Path) -> None:
    static_dir = tmp_path / "edge"
    avatar = static_dir / "assets" / "avatar"
    avatar.mkdir(parents=True)
    (avatar / "secrets.env").write_text("TOP_SECRET=1")
    (avatar / "bot_token.txt").write_text("tok")
    (avatar / "core.db").write_bytes(b"x")

    for name in ("secrets.env", "bot_token.txt", "core.db"):
        h = _make_handler(static_dir)
        h._handle_api_kiosk_download_file(f"/api/kiosk/files/download?name={name}")
        assert h.error is not None, f"{name} phải bị chặn"
        assert h.error["code"] == 403
        assert h.captured is None


def test_pi_download_traversal_chained(tmp_path: Path) -> None:
    static_dir = tmp_path / "edge"
    (static_dir / "assets" / "avatar").mkdir(parents=True)
    secret = tmp_path / "outside.txt"
    secret.write_text("dữ liệu ngoài phạm vi")

    h = _make_handler(static_dir)
    # Path.name trong handler cắt traversal → tìm không thấy → 404, KHÔNG đọc outside.txt
    h._handle_api_kiosk_download_file(
        "/api/kiosk/files/download?name=..%2F..%2Foutside.txt")
    assert h.error is not None and h.error["code"] == 404
    assert h.captured is None


def test_pi_download_ext_not_permitted(tmp_path: Path) -> None:
    static_dir = tmp_path / "edge"
    (static_dir / "assets" / "avatar").mkdir(parents=True)
    h = _make_handler(static_dir)
    h._handle_api_kiosk_download_file("/api/kiosk/files/download?name=run.exe")
    assert h.error is not None and h.error["code"] == 400


def test_pi_download_missing(tmp_path: Path) -> None:
    static_dir = tmp_path / "edge"
    (static_dir / "assets" / "avatar").mkdir(parents=True)
    h = _make_handler(static_dir)
    h._handle_api_kiosk_download_file("/api/kiosk/files/download?name=khong_co.png")
    assert h.error is not None and h.error["code"] == 404


# ---------------------------------------------------------------------------
# 2) PC-side endpoint qua HTTP server thật (mock edge request)
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def transfer_server(tmp_path_factory: pytest.TempPathFactory):
    test_ws = tmp_path_factory.mktemp("transfer_ws")
    (test_ws / "edge_client" / "assets" / "avatar").mkdir(parents=True)
    old_env = os.environ.get("QUAN_AI_BRAIN_WORKSPACE")
    os.environ["QUAN_AI_BRAIN_WORKSPACE"] = str(test_ws)

    from quan_ai_brain.web.server import BrainAPIHandler, ThreadedHTTPServer
    server = ThreadedHTTPServer(("127.0.0.1", 0), BrainAPIHandler)
    host, port = server.server_address
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    time.sleep(0.1)
    base = f"http://{host}:{port}"

    yield base, test_ws

    server.shutdown()
    server.server_close()
    if old_env is None:
        os.environ.pop("QUAN_AI_BRAIN_WORKSPACE", None)
    else:
        os.environ["QUAN_AI_BRAIN_WORKSPACE"] = old_env


def test_pc_download_proxy_from_pi5(transfer_server) -> None:
    base, _ = transfer_server
    payload = {
        "success": True,
        "filename": "chup_tu_pi.jpg",
        "size_bytes": 9,
        "content_b64": base64.b64encode(b"PI-IMAGE!").decode("ascii"),
        "source": "assets/avatar/chup_tu_pi.jpg",
    }
    with mock.patch("quan_ai_brain.web.server._send_edge_request", return_value=payload):
        with urllib.request.urlopen(
                f"{base}/api/executive/edge/files/download?name=chup_tu_pi.jpg",
                timeout=5.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    assert data["success"] is True
    assert base64.b64decode(data["content_b64"]) == b"PI-IMAGE!"
    assert "PC-local" not in data["source"]


def test_pc_download_fallback_local_khi_pi5_offline(transfer_server) -> None:
    base, ws = transfer_server
    local_file = ws / "edge_client" / "assets" / "avatar" / "anh_offline.png"
    local_file.write_bytes(b"\x89PNG-local-copy")

    offline_resp = {"success": False, "error": "Port 8768 not reachable", "offline": True}
    with mock.patch("quan_ai_brain.web.server._send_edge_request", return_value=offline_resp):
        with urllib.request.urlopen(
                f"{base}/api/executive/edge/files/download?name=anh_offline.png",
                timeout=5.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    assert data["success"] is True
    assert base64.b64decode(data["content_b64"]) == b"\x89PNG-local-copy"
    assert "PC-local" in data["source"]


def test_pc_download_khong_co_gi_hat_404(transfer_server) -> None:
    import urllib.error
    base, _ = transfer_server
    offline_resp = {"success": False, "error": "Port 8768 not reachable", "offline": True}
    with mock.patch("quan_ai_brain.web.server._send_edge_request", return_value=offline_resp):
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(
                f"{base}/api/executive/edge/files/download?name=khong_ton_tai.png",
                timeout=5.0)
        assert exc_info.value.code == 502


def test_pc_download_missing_name_400(transfer_server) -> None:
    import urllib.error
    base, _ = transfer_server
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        urllib.request.urlopen(f"{base}/api/executive/edge/files/download", timeout=5.0)
    assert exc_info.value.code == 400


def test_pc_upload_then_list_roundtrip(transfer_server) -> None:
    """Truyền tin chiều PC→Pi5 (đã có, hồi quy): upload + liệt kê thấy file."""
    base, ws = transfer_server
    img = b"\x89PNG-rk-roundtrip"
    up = json.dumps({
        "filename": "truyen_tin_roundtrip.png",
        "content_b64": base64.b64encode(img).decode("ascii"),
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{base}/api/executive/edge/files/upload", data=up,
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=5.0) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    assert data["success"] is True
    assert data["local_saved"] is True

    saved = ws / "edge_client" / "assets" / "avatar" / "truyen_tin_roundtrip.png"
    assert saved.exists() and saved.read_bytes() == img

    # Tải ngược lại về (fallback local — không mock Pi5) → khớp byte
    with mock.patch("quan_ai_brain.web.server._send_edge_request",
                    return_value={"success": False, "offline": True, "error": "x"}):
        with urllib.request.urlopen(
                f"{base}/api/executive/edge/files/download?name=truyen_tin_roundtrip.png",
                timeout=5.0) as resp:
            dl = json.loads(resp.read().decode("utf-8"))
    assert base64.b64decode(dl["content_b64"]) == img


def test_ui_co_nut_tai_ve_va_endpoint_trong_js() -> None:
    """UI phải có nút Tải Về + gọi đúng endpoint download."""
    js = (REPO / "src" / "quan_ai_brain" / "web" / "static" / "executive.js").read_text(encoding="utf-8")
    assert "btn-file-dl" in js
    assert "/api/executive/edge/files/download" in js
    assert "⬇️ Tải Về" in js  # nút trong template JS
    html = (REPO / "src" / "quan_ai_brain" / "web" / "static" / "executive.html").read_text(encoding="utf-8")
    assert "2 CHIỀU" in html
