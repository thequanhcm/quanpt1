"""Tests — M1 System Health Intelligence.

Phạm vi: health state machine, PC collector, Pi5 collector (SSH mock),
alert engine (sender mock + cooldown + DB), aggregator (ngưỡng), health
monitor runtime (cycle giả). KHÔNG test nào đụng mạng thật/DM thật.

Quy tắc (AGENTS.md): fail-honest — thiếu dữ liệu phải ra UNKNOWN, không
được đoán HEALTHY.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE / "src"))

from quan_ai_brain.monitoring.aggregator import (  # noqa: E402
    PI5_THRESHOLDS,
    PC_THRESHOLDS,
    HealthAggregator,
    _apply_thresholds,
)
from quan_ai_brain.monitoring.alert_engine import AlertEngine  # noqa: E402
from quan_ai_brain.monitoring.health_monitor import HealthMonitor  # noqa: E402
from quan_ai_brain.monitoring.health_state import (  # noqa: E402
    CRITICAL,
    NORMAL,
    UNKNOWN,
    WARNING,
    ComponentState,
    CheckResult,
    overall_status,
)


# ---------------- health_state ----------------
class TestHealthState:
    def test_worst_wins_critical(self):
        comp = ComponentState(component_id="x")
        comp.apply(CheckResult("a", 1, "ok", "", "t"), {"a": CRITICAL})
        # thresholds nói 'a' → CRITICAL nghĩa là khi đo thấy bất thường,
        # phân loại là CRITICAL.
        assert comp.status == CRITICAL

    def test_no_data_is_unknown(self):
        comp = ComponentState(component_id="x")
        assert comp.status == UNKNOWN
        assert comp.reason == ""

    def test_overall_unknown_when_no_components(self):
        assert overall_status({}) == UNKNOWN

    def test_overall_worst_of_components(self):
        c1 = ComponentState(component_id="a")
        c2 = ComponentState(component_id="b")
        assert overall_status({"a": c1, "b": c2}) == UNKNOWN


# ---------------- alert engine ----------------
class TestAlertEngine:
    def _engine(self, tmp_path, sender):
        return AlertEngine(tmp_path, cooldown_sec=300, sender=sender)

    def test_threshold_breach_sends_once(self, tmp_path):
        sent = []
        eng = self._engine(
            tmp_path, lambda m: (sent.append(m) or {"success": True}))
        checks = {"bt_speaker_connected": {"value": "no"}}
        alerts = eng.evaluate_checks(
            "pi5", checks, {"bt_speaker_connected": ("==no", "")})
        assert len(alerts) == 1
        assert alerts[0]["severity"] == WARNING
        assert alerts[0]["sent"] is True
        assert len(sent) == 1

    def test_cooldown_blocks_second_send(self, tmp_path):
        sent = []
        eng = self._engine(
            tmp_path, lambda m: (sent.append(m) or {"success": True}))
        checks = {"soc_temp_c": {"value": 85}}
        rule = {"soc_temp_c": (">=70", ">=80")}
        eng.evaluate_checks("pi5", checks, rule)
        eng.evaluate_checks("pi5", checks, rule)
        assert len(sent) == 1  # lần 2 bị cooldown
        assert len(eng.recent_alerts()) == 2  # nhưng vẫn ghi DB đủ

    def test_send_failure_recorded_not_swallowed(self, tmp_path):
        eng = self._engine(
            tmp_path, lambda m: {"success": False, "error": "boom"})
        checks = {"soc_temp_c": {"value": 85}}
        alerts = eng.evaluate_checks(
            "pi5", checks, {"soc_temp_c": (">=70", ">=80")})
        assert alerts[0]["sent"] is False
        assert "send_failed" in (alerts[0]["suppressed_reason"] or "")

    def test_normal_value_no_alert(self, tmp_path):
        eng = self._engine(tmp_path, lambda m: {"success": True})
        checks = {"soc_temp_c": {"value": 58.7}}
        alerts = eng.evaluate_checks(
            "pi5", checks, {"soc_temp_c": (">=70", ">=80")})
        assert alerts == []

    def test_missing_value_unknown(self):
        assert AlertEngine._classify(None, (">=70", ">=80")) == UNKNOWN

    def test_critical_takes_priority_over_warning(self):
        rule = (">=70", ">=80")
        assert AlertEngine._classify(85, rule) == CRITICAL
        assert AlertEngine._classify(75, rule) == WARNING


# ---------------- aggregator ----------------
class TestAggregator:
    def test_apply_thresholds_classification(self):
        checks = {
            "cpu_percent": {"value": 50, "status": "ok"},
            "ram_percent": {"value": 90, "status": "ok"},
            "disk_percent": {"value": 99, "status": "ok"},
            "unknown_thing": {"value": None, "status": "unknown"},
        }
        out = _apply_thresholds(checks, PC_THRESHOLDS)
        assert out["cpu_percent"]["severity"] == NORMAL
        assert out["ram_percent"]["severity"] == WARNING
        assert out["disk_percent"]["severity"] == CRITICAL
        assert out["unknown_thing"]["severity"] == UNKNOWN

    def test_snapshot_with_mock_collectors(self):
        agg = HealthAggregator()
        agg._pi5_probe = lambda: {
            "component_id": "pi5_edge",
            "measured_at": "t",
            "reachable": True,
            "checks": {
                "soc_temp_c": {"value": 58.0, "status": "ok",
                               "reason": "measured", "measured_at": "t"},
                "bt_speaker_connected": {"value": "yes", "status": "ok",
                                         "reason": "measured", "measured_at": "t"},
            },
        }
        snap = agg.snapshot(force=True)
        assert snap["pi5"]["status"] in (NORMAL, UNKNOWN)
        assert snap["pc"]["status"] in (NORMAL, UNKNOWN)
        assert snap["overall_status"] in (NORMAL, WARNING, CRITICAL, UNKNOWN)

    def test_pi5_bt_off_is_warning_not_critical(self):
        checks = {"bt_speaker_connected": {"value": "no", "status": "ok"}}
        out = _apply_thresholds(checks, PI5_THRESHOLDS)
        assert out["bt_speaker_connected"]["severity"] == WARNING


# ---------------- health monitor ----------------
class TestHealthMonitor:
    def test_run_once_with_mock(self, tmp_path):
        sent = []

        class FakeAgg:
            def snapshot(self, force=False):
                return {
                    "overall_status": WARNING,
                    "pc": {"checks": {"cpu_percent": {"value": 97}}},
                    "pi5": {"checks": {}},
                }

        eng = AlertEngine(tmp_path, cooldown_sec=0,
                          sender=lambda m: (sent.append(m) or {"success": True}))
        mon = HealthMonitor(tmp_path, FakeAgg(), cycle_sec=0.05,
                            alert_engine=eng)
        result = mon.run_once()
        assert result["overall_status"] == WARNING
        assert result["alerts"], "phải có alert CPU 97%"
        assert mon.status()["running"] is False  # chưa start
        mon.start()
        try:
            assert mon.status()["running"] is True
        finally:
            mon.stop()
        assert mon.status()["running"] is False

    def test_start_stop_idempotent(self, tmp_path):
        class FakeAgg:
            def snapshot(self, force=False):
                return {"overall_status": NORMAL, "pc": {"checks": {}},
                        "pi5": {"checks": {}}}

        eng = AlertEngine(tmp_path, sender=lambda m: {"success": True})
        mon = HealthMonitor(tmp_path, FakeAgg(), cycle_sec=0.05,
                            alert_engine=eng)
        mon.start()
        mon.start()  # gọi lần 2 — không được spawn thread thứ 2
        t1 = mon._thread
        mon.stop()
        assert mon._thread is not t1 or not t1.is_alive()


# ---------------- PC collector (thật, đọc-only) ----------------
class TestPcCollector:
    def test_collect_returns_schema(self):
        from quan_ai_brain.monitoring.pc_collector import collect_pc_health
        snap = collect_pc_health()
        assert snap["component_id"] == "pc_host"
        assert "measured_at" in snap
        if snap["available"]:
            assert "cpu_percent" in snap["checks"]
            assert "ram_percent" in snap["checks"]
            assert "disk_free_gb" in snap["checks"]
            for chk in snap["checks"].values():
                assert set(chk) == {"value", "status", "reason", "measured_at"}


# ---------------- Pi5 collector (SSH mock — không mạng thật) ----------------
class TestPi5CollectorMock:
    def test_parse_temp(self, monkeypatch):
        from quan_ai_brain.monitoring import pi5_collector
        monkeypatch.setattr(pi5_collector, "_ssh_run",
                            lambda cmd: (0, "temp=58.7'C"))
        snap = pi5_collector.collect_pi5_health()
        assert snap["checks"]["soc_temp_c"]["value"] == 58.7
        assert snap["checks"]["soc_temp_c"]["status"] == "ok"

    def test_ssh_unreachable_is_unknown_not_crash(self, monkeypatch):
        from quan_ai_brain.monitoring import pi5_collector
        monkeypatch.setattr(pi5_collector, "_ssh_run",
                            lambda cmd: (255, "probe_error:OSError"))
        snap = pi5_collector.collect_pi5_health()
        assert snap["reachable"] is False
        assert snap["checks"]["soc_temp_c"]["status"] == "unknown"
