"""Tests — M1.7: HTTP endpoints /api/health/machine, /api/health/monitor,
trang /health. Server chạy thật trên port ngẫu nhiên; collectors được mock
để không đụng SSH/psutil thật; AlertEngine sender được mock để KHÔNG gửi DM.
"""
from __future__ import annotations

import json
import sys
import threading
import time
import urllib.request
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE / "src"))

from quan_ai_brain.web import server as web_server  # noqa: E402
from quan_ai_brain.web.server import BrainAPIHandler, ThreadedHTTPServer  # noqa: E402


@pytest.fixture(scope="module")
def health_server(tmp_path_factory: pytest.TempPathFactory):
    test_workspace = tmp_path_factory.mktemp("health_workspace")
    (test_workspace / "data").mkdir(parents=True, exist_ok=True)

    # --- Mock aggregator snapshot (không đo thật) ---
    fake_snap = {
        "measured_at": "2026-11-01T03:00:00+00:00",
        "pc": {
            "component_id": "pc_host", "available": True,
            "measured_at": "2026-11-01T03:00:00+00:00",
            "status": "NORMAL",
            "checks": {"cpu_percent": {"value": 12.0, "status": "ok",
                                       "severity": "NORMAL",
                                       "reason": "measured",
                                       "measured_at": "t"}},
        },
        "pi5": {
            "component_id": "pi5_edge", "reachable": True,
            "measured_at": "2026-11-01T03:00:00+00:00",
            "status": "WARNING",
            "checks": {"bt_speaker_connected": {"value": "no", "status": "ok",
                                                "severity": "WARNING",
                                                "reason": "measured",
                                                "measured_at": "t"}},
        },
        "overall_status": "WARNING",
    }

    class FakeAgg:
        def snapshot(self, force=False):
            return fake_snap

    old_agg = web_server._GLOBAL_HEALTH_AGGREGATOR
    old_mon = web_server._GLOBAL_HEALTH_MONITOR
    web_server._GLOBAL_HEALTH_AGGREGATOR = FakeAgg()
    # Giả lập monitor đã chạy:
    class FakeMon:
        def status(self):
            return {"running": True, "cycle_sec": 120.0, "cycles_done": 3,
                    "last_overall_status": "WARNING",
                    "recent_alerts": [{"ts_utc": "2026-11-01T02:59:00+00:00",
                                       "check_id": "pi5_edge:bt_speaker_connected",
                                       "severity": "WARNING", "value": '"no"',
                                       "message": "m", "sent": 1,
                                       "suppressed_reason": None}]}

    web_server._GLOBAL_HEALTH_MONITOR = FakeMon()

    server = ThreadedHTTPServer(("127.0.0.1", 0), BrainAPIHandler)
    host, port = server.server_address
    url = f"http://127.0.0.1:{port}"
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    time.sleep(0.3)
    yield url
    server.shutdown()
    web_server._GLOBAL_HEALTH_AGGREGATOR = old_agg
    web_server._GLOBAL_HEALTH_MONITOR = old_mon


def _get(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=10) as resp:
        return json.loads(resp.read().decode())


class TestHealthMachineEndpoint:
    def test_returns_snapshot(self, health_server):
        data = _get(health_server + "/api/health/machine")
        assert data["success"] is True
        assert data["overall_status"] == "WARNING"
        assert data["pc"]["component_id"] == "pc_host"
        assert data["pi5"]["checks"]["bt_speaker_connected"]["severity"] == "WARNING"

    def test_force_param_accepted(self, health_server):
        data = _get(health_server + "/api/health/machine?force=1")
        assert data["success"] is True


class TestHealthMonitorEndpoint:
    def test_monitor_status(self, health_server):
        data = _get(health_server + "/api/health/monitor")
        assert data["success"] is True
        assert data["running"] is True
        assert data["cycles_done"] == 3
        assert data["recent_alerts"][0]["check_id"] == "pi5_edge:bt_speaker_connected"


class TestHealthPage:
    def test_health_page_served(self, health_server):
        with urllib.request.urlopen(health_server + "/health", timeout=10) as resp:
            body = resp.read().decode()
        assert "Sức khoẻ Hệ thống" in body
        assert "/api/health/machine" in body
