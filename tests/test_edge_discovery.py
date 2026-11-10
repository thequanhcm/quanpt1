"""(10/11/2026) Test cho _discover_core_host + EdgeConfig discovery fields.

Mục tiêu: PC Wi-Fi IP nhảy DHCP (.9→.13→.11 trong 3 ngày) khiến Pi mất dấu
PC vĩnh viễn. Helper _discover_core_host quét subnet tìm host mở core_port
+ trả /api/health 200. Test fail-honest: không mock giả, dùng socket thật
+ HTTP server thật trên localhost.
"""
from __future__ import annotations

import http.server
import json
import socket
import threading
import time
from pathlib import Path

import pytest

# Import module-level helper (chạy trong subprocess vì client_daemon.py có
# nhiều import nặng — tránh side effect khi chỉ test helper).
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "edge_client"))


def _free_port() -> int:
    """Tìm cổng trống trên localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _start_health_server(port: int, body: dict) -> http.server.HTTPServer:
    """Khởi HTTP server trả /api/health 200 + JSON body."""
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/api/health":
                payload = json.dumps(body).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, *args, **kwargs):
            pass  # im lặng

    server = http.server.HTTPServer(("127.0.0.1", port), Handler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server


def test_discover_finds_localhost_health_server():
    """Tìm thấy localhost server trả /api/health 200."""
    from client_daemon import _discover_core_host

    port = _free_port()
    server = _start_health_server(port, {"service": "quan-ai-brain", "status": "ok"})
    try:
        # Quét /24 nhưng chỉ có 127.0.0.1 mở port → phải tìm được
        result = _discover_core_host("127.0.0.0/24", port, 0.5)
        assert result == "127.0.0.1", f"expected 127.0.0.1, got {result}"
    finally:
        server.shutdown()


def test_discover_returns_none_when_no_server():
    """Không tìm thấy server nào → trả None (không crash)."""
    from client_daemon import _discover_core_host

    # Cổng chắc chắn không ai dùng
    port = _free_port()
    # Không start server
    result = _discover_core_host("127.0.0.0/24", port, 0.2)
    assert result is None, f"expected None, got {result}"


def test_discover_skips_404_health():
    """Server mở port nhưng /api/health trả 404 → bỏ qua, không nhầm là PC."""
    from client_daemon import _discover_core_host

    port = _free_port()

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(404)
            self.end_headers()

        def log_message(self, *args, **kwargs):
            pass

    server = http.server.HTTPServer(("127.0.0.1", port), Handler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    try:
        result = _discover_core_host("127.0.0.0/24", port, 0.2)
        assert result is None, f"expected None (404), got {result}"
    finally:
        server.shutdown()


def test_discover_rejects_invalid_subnet():
    """Subnet không hợp lệ → trả None (fail-closed)."""
    from client_daemon import _discover_core_host

    result = _discover_core_host("not-a-cidr", 8766, 0.5)
    assert result is None


def test_discover_rejects_too_large_subnet():
    """Subnet > /24 → trả None (giới hạn quét 254 host)."""
    from client_daemon import _discover_core_host

    result = _discover_core_host("10.0.0.0/8", 8766, 0.5)
    assert result is None


def test_edgeconfig_has_discovery_fields():
    """EdgeConfig có đủ 5 trường discovery mới."""
    from config import EdgeConfig

    cfg = EdgeConfig()
    assert cfg.core_host_discovery_enabled is True
    assert cfg.core_host_discovery_subnet == "192.168.1.0/24"
    assert cfg.core_host_discovery_after_sec == 30.0
    assert cfg.core_host_discovery_interval_sec == 60.0
    assert cfg.core_host_discovery_probe_timeout_sec == 1.0


def test_edgeconfig_discovery_roundtrip():
    """Discovery fields sống qua save/load config."""
    from config import EdgeConfig

    cfg = EdgeConfig()
    cfg.core_host_discovery_enabled = False
    cfg.core_host_discovery_subnet = "10.0.0.0/24"
    cfg.core_host_discovery_after_sec = 45.0

    tmp = Path("/tmp/test_edge_discovery_config.json")
    cfg.save_to_file(tmp)
    loaded = EdgeConfig.load_from_file(tmp)
    assert loaded.core_host_discovery_enabled is False
    assert loaded.core_host_discovery_subnet == "10.0.0.0/24"
    assert loaded.core_host_discovery_after_sec == 45.0
    tmp.unlink()


def test_detect_connection_lost_uses_stale_check():
    """detect_connection_lost fire LOST khi heartbeat stale dù core_connected=True.

    (10/11/2026) Sửa fail-honest: trước đây chỉ dựa vào core_connected sticky-True
    → event LOST không bao giờ fire đúng khi PC chết âm thầm.
    """
    from edge_agent import EdgeAgent

    agent = EdgeAgent()
    # Giả lập: trước đó connected, giờ heartbeat stale 20s (> 4*3=12s)
    # nhưng core_connected vẫn True (sticky-True bug cũ).
    was_connected = True
    core_connected = True  # sticky-True
    last_hb = time.time() - 20.0  # 20s trước → stale
    lost = agent.detect_connection_lost(
        core_connected=core_connected,
        was_connected=was_connected,
        last_heartbeat_epoch=last_hb,
        heartbeat_timeout_sec=4.0,
    )
    assert lost is True, "Phải fire LOST khi heartbeat stale dù core_connected=True"


def test_detect_connection_lost_no_false_positive_when_fresh():
    """Heartbeat tươi (< 12s) + core_connected=True → KHÔNG fire LOST."""
    from edge_agent import EdgeAgent

    agent = EdgeAgent()
    was_connected = True
    core_connected = True
    last_hb = time.time() - 2.0  # 2s trước → fresh
    lost = agent.detect_connection_lost(
        core_connected=core_connected,
        was_connected=was_connected,
        last_heartbeat_epoch=last_hb,
        heartbeat_timeout_sec=4.0,
    )
    assert lost is False, "Không được fire LOST khi heartbeat còn tươi"


def test_detect_connection_lost_backward_compat():
    """Gọi không truyền last_heartbeat_epoch (backward compat) → không crash."""
    from edge_agent import EdgeAgent

    agent = EdgeAgent()
    # Gọi kiểu cũ — chỉ 2 tham số
    lost = agent.detect_connection_lost(
        core_connected=False,
        was_connected=True,
    )
    assert lost is True  # core_connected=False → LOST bình thường
