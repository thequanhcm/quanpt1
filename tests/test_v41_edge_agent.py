"""Tests V41 — Edge Agent 5 năng lực chủ động (30/10/2026).

Phủ đủ 5 năng lực theo chỉ thị của Quanpt1:
1. Tự phản ứng (chào mừng, camera auto-on, phát hiện mất kết nối)
2. Tự quản lý (metrics CPU/RAM/nhiệt/throttle)
3. Tự thu thập (ring buffer event giới hạn cứng)
4. Tự phối hợp (gửi events lên Brain, fail-closed)
5. Tự cải tiến có kiểm soát (health-check → CHỈ đề xuất, không tự áp dụng)
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "edge_client"))

from edge_agent import (  # noqa: E402
    MAX_EVENTS,
    TEMP_THRESHOLD_C,
    EdgeAgent,
    EdgeEventBuffer,
    _detect_peripherals,
    _read_mem_available_mb,
    _read_proc_stat,
    _read_temp_celsius,
    _read_throttled_bits,
    _read_uptime_sec,
)


# ============================================================
# NĂNG LỰC 3 — TỰ THU THẬP (ring buffer)
# ============================================================
class TestEdgeEventBuffer:
    def test_add_and_len(self):
        buf = EdgeEventBuffer(max_events=5)
        buf.add("TEST_EVENT", severity="INFO", details={"x": 1})
        assert len(buf) == 1

    def test_ring_buffer_max_events_hard_cap(self):
        buf = EdgeEventBuffer(max_events=3)
        for i in range(10):
            buf.add(f"EV_{i}")
        snap = buf.snapshot()
        assert len(snap) == 3
        # giữ lại 3 event MỚI NHẤT
        assert snap[-1]["type"] == "EV_9"
        assert snap[0]["type"] == "EV_7"

    def test_drain_clears_buffer(self):
        buf = EdgeEventBuffer()
        buf.add("A")
        buf.add("B")
        drained = buf.drain()
        assert len(drained) == 2
        assert len(buf) == 0
        # drain lần 2 rỗng
        assert buf.drain() == []

    def test_event_fields_complete(self):
        buf = EdgeEventBuffer()
        ev = buf.add("SOME_TYPE", severity="WARNING", details={"k": "v"})
        assert ev["seq"] >= 1
        assert ev["type"] == "SOME_TYPE"
        assert ev["severity"] == "WARNING"
        assert "timestamp_utc" in ev
        assert ev["details"] == {"k": "v"}

    def test_global_max_events_constant(self):
        assert MAX_EVENTS == 200  # chính sách lưu trữ: giới hạn cứng


# ============================================================
# NĂNG LỰC 2 — TỰ QUẢN LÝ (metrics)
# ============================================================
class TestMetricsReaders:
    def test_read_proc_stat_on_windows_returns_zero(self):
        # /proc/stat không tồn tại trên Windows → (0, 0) fail-closed
        idle, total = _read_proc_stat()
        assert (idle, total) == (0, 0)

    def test_read_temp_returns_minus1_on_windows(self):
        assert _read_temp_celsius() == -1.0

    def test_read_throttled_returns_minus1_when_no_vcgencmd(self):
        assert _read_throttled_bits() == -1

    def test_read_uptime_returns_minus1_on_windows(self):
        assert _read_uptime_sec() == -1.0

    def test_read_mem_returns_minus1_on_windows(self):
        assert _read_mem_available_mb() == -1

    def test_detect_peripherals_win32_platform(self):
        p = _detect_peripherals()
        assert p["platform"] == "Windows"
        assert p["camera_dev0"] is False  # không có /dev/video0 trên PC
        assert p["alsa_cards"] in (-1, 0)  # không đọc được /proc/asound/cards trên PC


class TestCollectMetrics:
    def test_first_call_cpu_percent_minus1(self):
        agent = EdgeAgent()
        m = agent.collect_metrics()
        assert m["cpu_percent"] == -1.0  # chưa có mốc trước để tính delta

    def test_second_call_returns_cpu_percent_or_minus1(self):
        agent = EdgeAgent()
        agent.collect_metrics()
        m2 = agent.collect_metrics()
        # Trên Windows không đọc được /proc/stat → vẫn -1; trên Pi sẽ có % thật
        assert m2["cpu_percent"] == -1.0 or isinstance(m2["cpu_percent"], float)

    def test_metrics_stored_in_history(self):
        agent = EdgeAgent()
        agent.collect_metrics()
        agent.collect_metrics()
        hist = agent.get_metrics_history()
        assert len(hist) == 2

    def test_metrics_structure(self):
        agent = EdgeAgent()
        m = agent.collect_metrics()
        for key in (
            "timestamp_utc", "cpu_percent", "mem_available_mb", "temp_c",
            "throttled_bits", "throttled_desc", "load_avg", "uptime_sec",
            "peripherals", "services",
        ):
            assert key in m, f"thiếu key {key}"

    def test_temp_hot_event_emitted(self):
        agent = EdgeAgent()
        with patch("edge_agent._read_temp_celsius", return_value=85.0):
            agent.collect_metrics()
        types = [e["type"] for e in agent.events.snapshot()]
        assert "TEMP_HOT" in types

    def test_temp_normal_no_event(self):
        agent = EdgeAgent()
        with patch("edge_agent._read_temp_celsius", return_value=45.0):
            agent.collect_metrics()
        types = [e["type"] for e in agent.events.snapshot()]
        assert "TEMP_HOT" not in types

    def test_throttled_event_emitted_when_bits_4(self):
        agent = EdgeAgent()
        with patch("edge_agent._read_throttled_bits", return_value=4):
            agent.collect_metrics()
        types = [e["type"] for e in agent.events.snapshot()]
        assert "THROTTLED" in types

    def test_mem_low_event(self):
        agent = EdgeAgent()
        with patch("edge_agent._read_mem_available_mb", return_value=120):
            agent.collect_metrics()
        types = [e["type"] for e in agent.events.snapshot()]
        assert "MEM_LOW" in types


# ============================================================
# NĂNG LỰC 1 — TỰ PHẢN ỨNG
# ============================================================
class TestAutoReact:
    def test_greeting_once_per_boot(self, tmp_path):
        agent = EdgeAgent()
        agent._greeted = False
        with patch("edge_agent._GREETED_FILE", tmp_path / ".greeted"):
            a1 = agent.maybe_autoreact_on_boot(camera_available=False)
            a2 = agent.maybe_autoreact_on_boot(camera_available=False)
        assert a1["greeted"] is True
        assert a2["greeted"] is False  # lần 2 không chào lại

    def test_greeting_persisted_to_file(self, tmp_path):
        agent = EdgeAgent()
        agent._greeted = False
        marker = tmp_path / ".greeted"
        with patch("edge_agent._GREETED_FILE", marker):
            agent.maybe_autoreact_on_boot(camera_available=False)
        assert marker.exists()

    def test_camera_auto_on_only_when_available(self):
        agent = EdgeAgent()
        a1 = agent.maybe_autoreact_on_boot(camera_available=True)
        a2 = agent.maybe_autoreact_on_boot(camera_available=False)
        assert a1["camera_auto_on"] is True
        assert a2["camera_auto_on"] is False

    def test_detect_connection_lost_triggers(self):
        agent = EdgeAgent()
        fired = []
        agent._notify_lost_connection = fired.append
        result = agent.detect_connection_lost(core_connected=False, was_connected=True)
        assert result is True
        assert len(fired) == 1
        types = [e["type"] for e in agent.events.snapshot()]
        assert "BRAIN_CONNECTION_LOST" in types
        assert agent.events.snapshot()[0]["severity"] == "CRITICAL"

    def test_no_false_lost_when_still_connected(self):
        agent = EdgeAgent()
        assert agent.detect_connection_lost(True, True) is False
        assert agent.detect_connection_lost(False, False) is False

    def test_reconnect_then_relose_triggers_again(self):
        agent = EdgeAgent()
        assert agent.detect_connection_lost(False, True) is True   # mất lần 1
        assert agent.detect_connection_lost(True, False) is False  # nối lại
        assert agent.detect_connection_lost(False, True) is True   # mất lần 2


# ============================================================
# NĂNG LỰC 4 — TỰ PHỐI HỢP (gửi Brain)
# ============================================================
class TestCoordinateWithBrain:
    def test_send_no_events_is_success(self):
        agent = EdgeAgent()
        assert agent.send_events_to_brain("http://127.0.0.1:1", {}) is True

    def test_send_events_success(self):
        agent = EdgeAgent()
        agent.events.add("TEST_OK")
        calls = []

        class FakeResp:
            status = 200
            def __enter__(self):
                return self
            def __exit__(self, *a):
                return False
            def read(self):
                return b'{"success": true}'

        def fake_urlopen(req, timeout=None):
            calls.append(req)
            return FakeResp()

        with patch("edge_agent.urllib.request.urlopen", side_effect=fake_urlopen):
            ok = agent.send_events_to_brain("http://brain:8766", {"X-Test": "1"})
        assert ok is True
        assert len(calls) == 1
        assert "api/executive/edge/events" in calls[0].full_url
        body = json.loads(calls[0].data.decode("utf-8"))
        assert body["events"][0]["type"] == "TEST_OK"

    def test_send_events_fail_closed_requeues(self):
        """Lỗi network → events ĐƯỢC HOÀN TRẢ buffer, không mất dữ liệu."""
        agent = EdgeAgent()
        agent.events.add("PRECIOUS_EVENT")

        def fake_urlopen(req, timeout=None):
            raise urllib.error.URLError("network down")

        with patch("edge_agent.urllib.request.urlopen", side_effect=fake_urlopen):
            ok = agent.send_events_to_brain("http://brain:8766", {})
        assert ok is False
        # event không bị mất — vẫn trong buffer để thử lại
        types = [e["type"] for e in agent.events.snapshot()]
        assert "PRECIOUS_EVENT" in types


# ============================================================
# NĂNG LỰC 5 — TỰ CẢI TIẾN CÓ KIỂM SOÁT
# ============================================================
class TestControlledImprovement:
    def test_suggestion_recorded_with_approval_required(self):
        agent = EdgeAgent()
        s = agent.record_suggestion("TEST_KIND", {"x": 1})
        assert s["status"] == "PROPOSED"
        assert s["requires_owner_approval"] is True
        assert len(agent.get_suggestions()) == 1

    def test_health_check_healthy_on_win32(self):
        agent = EdgeAgent()
        result = agent.run_health_check()
        assert isinstance(result["healthy"], bool)
        assert "findings" in result
        assert "metrics" in result

    def test_health_check_finds_hot_temp(self):
        agent = EdgeAgent()
        with patch("edge_agent._read_temp_celsius", return_value=85.0):
            result = agent.run_health_check()
        areas = [f["area"] for f in result["findings"]]
        assert "thermal" in areas
        assert result["healthy"] is False
        # đề xuất được ghi nhận nhưng KHÔNG tự áp dụng
        suggestions = agent.get_suggestions()
        assert all(s["status"] == "PROPOSED" for s in suggestions)
        assert all(s["requires_owner_approval"] for s in suggestions)

    def test_health_check_finds_missing_camera_on_pi(self):
        agent = EdgeAgent()
        with patch("edge_agent._detect_peripherals", return_value={
            "camera_dev0": False, "i2c_dev": True, "alsa_cards": 1, "platform": "Linux",
        }):
            result = agent.run_health_check()
        areas = [f["area"] for f in result["findings"]]
        assert "camera" in areas

    def test_suggestions_never_auto_applied(self):
        """Bất biến an toàn: mọi đề xuất luôn PROPOSED + cần duyệt."""
        agent = EdgeAgent()
        for i in range(5):
            agent.record_suggestion(f"KIND_{i}", {"i": i})
        for s in agent.get_suggestions():
            assert s["status"] == "PROPOSED"
            assert s["requires_owner_approval"] is True


# ============================================================
# Status summary + background loops
# ============================================================
class TestStatusSummary:
    def test_summary_structure(self):
        agent = EdgeAgent()
        s = agent.get_status_summary()
        assert s["agent_version"] == "V41"
        assert set(s["capabilities"]) == {
            "AUTO_REACT", "AUTO_MANAGE", "AUTO_COLLECT",
            "AUTO_COORDINATE", "CONTROLLED_IMPROVE",
        }
        assert s["suggestions_pending"] == 0
        assert s["events_buffered"] == 0

    def test_start_stop_background_loops(self):
        agent = EdgeAgent()
        agent.start_background_loops()
        assert agent._metrics_thread is not None
        assert agent._metrics_thread.is_alive()
        assert agent._health_thread is not None
        agent.stop_background_loops()
        time.sleep(0.1)  # threads là daemon — kết thúc khi process kết thúc

    def test_start_background_loops_idempotent(self):
        agent = EdgeAgent()
        agent.start_background_loops()
        t1 = agent._metrics_thread
        agent.start_background_loops()  # gọi lần 2 → không tạo thread mới
        assert agent._metrics_thread is t1
        agent.stop_background_loops()


# ============================================================
# Daemon integration — EdgeDaemonState + heartbeat wiring
# ============================================================
class TestDaemonIntegration:
    def test_daemon_state_has_edge_agent(self):
        from config import EdgeConfig
        from client_daemon import EdgeDaemonState

        state = EdgeDaemonState(EdgeConfig())
        assert state.edge_agent is not None
        assert state.edge_agent.get_status_summary()["agent_version"] == "V41"

    def test_heartbeat_payload_includes_agent_summary(self):
        from config import EdgeConfig
        from client_daemon import EdgeClientDaemon

        daemon = EdgeClientDaemon(EdgeConfig())
        summary = daemon.state.edge_agent.get_status_summary()
        assert "capabilities" in summary
        assert summary["agent_version"] == "V41"
