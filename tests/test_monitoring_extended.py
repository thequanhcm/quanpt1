"""Tests — M1 mở rộng: network/service/database/voice collectors, RCA engine,
telemetry history, MAINTENANCE state, thresholds network/service.

Quy tắc: KHÔNG đụng mạng thật (ping mock), KHÔNG gửi DM thật (sender mock),
KHÔNG sửa DB hệ thống (dùng tmp workspace), SSH Pi5 không được gọi trong test.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE / "src"))

from quan_ai_brain.monitoring import rca_engine  # noqa: E402
from quan_ai_brain.monitoring.aggregator import (  # noqa: E402
    NETWORK_THRESHOLDS,
    SERVICE_THRESHOLDS,
    VOICE_THRESHOLDS,
    HealthAggregator,
    _apply_thresholds,
    classify_measured_status,
)
from quan_ai_brain.monitoring.database_collector import collect_database_health  # noqa: E402
from quan_ai_brain.monitoring.health_state import (  # noqa: E402
    MAINTENANCE,
    UNKNOWN,
)
from quan_ai_brain.monitoring.network_collector import collect_network_health  # noqa: E402


class TestNetworkCollector:
    def test_ping_ok(self, monkeypatch):
        import quan_ai_brain.monitoring.network_collector as nc
        monkeypatch.setattr(nc.subprocess, "run", lambda *a, **k: _FakeProc(
            0, "Reply from 100.100.83.59: bytes=32 time=30ms TTL=64"))
        snap = nc.collect_network_health()
        assert snap["reachable"] is True
        assert snap["checks"]["pc_to_pi5_rtt_ms"]["value"] == 30.0
        assert snap["checks"]["pc_to_pi5_loss_pct"]["value"] == 0.0

    def test_ping_lost_is_warn_not_normal(self, monkeypatch):
        import quan_ai_brain.monitoring.network_collector as nc
        monkeypatch.setattr(nc.subprocess, "run", lambda *a, **k: _FakeProc(
            1, "Request timed out."))
        snap = nc.collect_network_health()
        assert snap["reachable"] is False
        assert snap["checks"]["pc_to_pi5_rtt_ms"]["status"] == "warn"

    def test_ping_crash_is_unknown(self, monkeypatch):
        import quan_ai_brain.monitoring.network_collector as nc
        def boom(*a, **k):
            raise OSError("no route")
        monkeypatch.setattr(nc.subprocess, "run", boom)
        snap = nc.collect_network_health()
        assert snap["checks"]["pc_to_pi5_rtt_ms"]["status"] == "unknown"

    def test_rtt_thresholds(self):
        checks = {"pc_to_pi5_rtt_ms": {"value": 600}}
        out = _apply_thresholds(checks, NETWORK_THRESHOLDS)
        assert out["pc_to_pi5_rtt_ms"]["severity"] == "CRITICAL"
        checks2 = {"pc_to_pi5_rtt_ms": {"value": 200}}
        out2 = _apply_thresholds(checks2, NETWORK_THRESHOLDS)
        assert out2["pc_to_pi5_rtt_ms"]["severity"] == "WARNING"


class _FakeProc:
    def __init__(self, returncode, stdout):
        self.returncode = returncode
        self.stdout = stdout


class TestServiceCollector:
    def test_http_probe_real_localhost_closed(self):
        # Port chắc chắn đóng — probe phải fail-honest, không crash.
        from quan_ai_brain.monitoring.service_collector import _probe_http
        ok, detail = _probe_http(1, timeout=0.5)
        assert ok is False
        assert "probe_error" in detail

    def test_thresholds_down_is_critical(self):
        checks = {"executive_server": {"value": "down"}}
        out = _apply_thresholds(checks, SERVICE_THRESHOLDS)
        assert out["executive_server"]["severity"] == "CRITICAL"

    def test_thresholds_stale_heartbeat(self):
        checks = {"learning_daemon_heartbeat": {"value": 700.0}}
        out = _apply_thresholds(checks, SERVICE_THRESHOLDS)
        assert out["learning_daemon_heartbeat"]["severity"] == "CRITICAL"


class TestDatabaseCollector:
    def test_real_db_readonly_quick_check(self, tmp_path):
        # Tạo DB con trong tmp/data — KHÔNG đụng brain.db thật.
        import sqlite3
        data = tmp_path / "data"
        data.mkdir()
        db = data / "brain.db"
        with sqlite3.connect(db) as conn:
            conn.execute("CREATE TABLE episodes (id INTEGER PRIMARY KEY, t TEXT)")
            conn.execute("INSERT INTO episodes (t) VALUES ('x')")
        snap = collect_database_health(tmp_path)
        assert snap["checks"]["brain.db"]["status"] == "ok"
        assert snap["checks"]["brain.db"]["value"]["quick_check"] == "ok"
        assert snap["checks"]["brain.db"]["value"]["rows"]["episodes"] == 1

    def test_missing_db_is_unknown(self, tmp_path):
        snap = collect_database_health(tmp_path)
        assert snap["checks"]["brain.db"]["status"] == "unknown"


class TestVoiceCollector:
    def test_schema_and_fail_honest(self):
        from quan_ai_brain.monitoring.voice_collector import collect_voice_health
        snap = collect_voice_health()
        assert snap["component_id"] == "voice"
        for name in ("stt_engine", "llm_netmind", "tts_engine"):
            assert name in snap["checks"]
            assert snap["checks"][name]["status"] in ("ok", "warn", "crit", "unknown")

    def test_disabled_by_policy_is_not_warning(self):
        # Policy chặn cloud (không key) là hành vi đúng — phải NORMAL khi classify.
        checks = {"llm_netmind": {"value": "DISABLED_BY_POLICY", "status": "ok"}}
        out = _apply_thresholds(checks, VOICE_THRESHOLDS)
        assert out["llm_netmind"]["severity"] == "NORMAL"


class TestRcaEngine:
    def test_fact_for_warning(self):
        snap = {"pc": {"checks": {"cpu_percent": {"value": 97, "severity": "CRITICAL"}}},
                "pi5": {"checks": {}}, "network": {"checks": {}},
                "services": {"checks": {}}, "databases": {"checks": {}},
                "voice": {"checks": {}}}
        rca = rca_engine.build_rca(snap)
        facts = [r for r in rca if r["kind"] == rca_engine.FACT]
        assert facts and facts[0]["component"] == "pc"

    def test_unknown_reported_as_insufficient(self):
        snap = {"pc": {"checks": {"x": {"value": None, "severity": "UNKNOWN"}}},
                "pi5": {"checks": {}}, "network": {"checks": {}},
                "services": {"checks": {}}, "databases": {"checks": {}},
                "voice": {"checks": {}}}
        rca = rca_engine.build_rca(snap)
        assert any(r["kind"] == rca_engine.INSUFFICIENT for r in rca)

    def test_no_confirmed_without_deep_evidence(self):
        # Snapshot có vấn đề nhưng KHÔNG được tự sinh CONFIRMED_CAUSE.
        snap = {"pc": {"checks": {"cpu_percent": {"value": 99, "severity": "CRITICAL"}}},
                "pi5": {"checks": {}}, "network": {"checks": {}},
                "services": {"checks": {}}, "databases": {"checks": {}},
                "voice": {"checks": {}}}
        rca = rca_engine.build_rca(snap)
        assert not any(r["kind"] == rca_engine.CONFIRMED for r in rca)


class TestAggregatorExtended:
    def _mini_agg(self, tmp_path):
        agg = HealthAggregator(workspace=tmp_path)
        # Mock toàn bộ collectors để không đụng hệ thống thật:
        import quan_ai_brain.monitoring.aggregator as aggmod
        agg._pi5_probe = lambda: {"component_id": "pi5_edge", "measured_at": "t",
                                  "reachable": True, "checks": {}}
        monkey_patch = {
            "pc": ("quan_ai_brain.monitoring.pc_collector", "collect_pc_health"),
            "network": ("quan_ai_brain.monitoring.network_collector", "collect_network_health"),
            "services": ("quan_ai_brain.monitoring.service_collector", "collect_service_health"),
            "databases": ("quan_ai_brain.monitoring.database_collector", "collect_database_health"),
            "voice": ("quan_ai_brain.monitoring.voice_collector", "collect_voice_health"),
        }
        return agg, monkey_patch

    def test_snapshot_6_components_with_mocks(self, tmp_path, monkeypatch):
        import quan_ai_brain.monitoring.aggregator as aggmod

        def fake_pc():
            return {"component_id": "pc_host", "measured_at": "t", "available": True,
                    "checks": {"cpu_percent": {"value": 10, "status": "ok",
                                               "reason": "m", "measured_at": "t"}}}

        def fake_net():
            return {"component_id": "network", "measured_at": "t", "reachable": True,
                    "checks": {"pc_to_pi5_rtt_ms": {"value": 30.0, "status": "ok",
                                                    "reason": "m", "measured_at": "t"}}}

        def fake_svc():
            return {"component_id": "services", "measured_at": "t", "reachable": True,
                    "checks": {"executive_server": {"value": "up", "status": "ok",
                                                    "reason": "m", "measured_at": "t"}}}

        def fake_db(ws=None):
            return {"component_id": "databases", "measured_at": "t", "reachable": True,
                    "checks": {"brain.db": {"value": {"quick_check": "ok"}, "status": "ok",
                                            "reason": "m", "measured_at": "t"}}}

        def fake_voice():
            return {"component_id": "voice", "measured_at": "t", "reachable": True,
                    "checks": {"stt_engine": {"value": "ready", "status": "ok",
                                              "reason": "m", "measured_at": "t"}}}

        monkeypatch.setattr(aggmod.pc_collector, "collect_pc_health", fake_pc)
        monkeypatch.setattr(aggmod.network_collector, "collect_network_health", fake_net)
        monkeypatch.setattr(aggmod.service_collector, "collect_service_health", fake_svc)
        monkeypatch.setattr(aggmod.database_collector, "collect_database_health", fake_db)
        monkeypatch.setattr(aggmod.voice_collector, "collect_voice_health", fake_voice)

        agg = HealthAggregator(workspace=tmp_path)
        # pi5 có ít nhất 1 check (nếu không → UNKNOWN, không phải NORMAL):
        agg._pi5_probe = lambda: {
            "component_id": "pi5_edge", "measured_at": "t", "reachable": True,
            "checks": {"soc_temp_c": {"value": 57.0, "status": "ok",
                                      "reason": "m", "measured_at": "t"}}}
        snap = agg.snapshot(force=True)
        for comp in ("pc", "pi5", "network", "services", "databases", "voice"):
            assert comp in snap, f"thiếu component {comp}"
        assert snap["overall_status"] == "NORMAL"
        # History được ghi:
        assert len(agg.history()) >= 1

    def test_maintenance_state(self, tmp_path):
        agg = HealthAggregator(workspace=tmp_path)
        assert agg.is_maintenance() is False
        agg.set_maintenance(True)
        assert agg.is_maintenance() is True
        # classify map:
        assert classify_measured_status("ok") == "NORMAL"
        assert classify_measured_status("unknown") == UNKNOWN
        assert MAINTENANCE == "MAINTENANCE"

    def test_history_pruned(self, tmp_path):
        agg = HealthAggregator(workspace=tmp_path)
        snap = {"measured_at": "t", "overall_status": "NORMAL",
                "pc": {"status": "NORMAL", "checks": {}},
                "pi5": {"status": "NORMAL", "checks": {}},
                "network": {"status": "NORMAL", "checks": {}},
                "services": {"status": "NORMAL", "checks": {}},
                "databases": {"status": "NORMAL", "checks": {}},
                "voice": {"status": "NORMAL", "checks": {}}}
        for _ in range(5):
            agg._append_history(snap)
        assert len(agg.history()) == 5
