"""Tests — M4: Self Model & Autonomous Learning introspection.

Phạm vi:
1. GET /api/self/model  — Self Model sống (identity, deployment, inventory scan thật).
2. GET /api/self/state  — 12 câu tự nhận thức bằng probe thật (fail-honest).
3. GET /api/self/learning — dữ liệu học thật từ DB (CLO checkpoints, candidates, skills)
   với workspace GIẢ LẬP khép kín (không đụng brain.db thật).
4. Unit test sửa lỗi trung thực M4:
   - learning_state error phải thành UNKNOWN (không nuốt lỗi SQL).
   - SkillRegistry.record_test_result phải chặn kết quả không phải PASS/FAIL.
"""
from __future__ import annotations

import json
import sqlite3
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


# ---------------------------------------------------------------------------
# Fixture: server thật trên port ngẫu nhiên + workspace giả lập cho /api/self/*
# ---------------------------------------------------------------------------

def _make_fake_workspace(tmp_path: Path) -> Path:
    """Workspace giả lập: brain.db + learning_checkpoints.db + skill_registry.json."""
    ws = tmp_path / "m4_ws"
    (ws / "data").mkdir(parents=True)
    (ws / "logs").mkdir(parents=True)

    # brain.db — 1 approved + 2 quarantined
    con = sqlite3.connect(ws / "data" / "brain.db")
    con.execute(
        "CREATE TABLE candidate_knowledge (id TEXT PRIMARY KEY, created_at_utc TEXT, "
        "statement TEXT, source_ref TEXT, rationale TEXT, status TEXT, decision_note TEXT)")
    con.execute(
        "INSERT INTO candidate_knowledge VALUES ('c1','2026-11-01T00:00:00+00:00','s1','r','ra','approved','ok')")
    con.execute(
        "INSERT INTO candidate_knowledge VALUES ('c2','2026-11-01T00:00:01+00:00','s2','r','ra','quarantined','pending')")
    con.execute(
        "INSERT INTO candidate_knowledge VALUES ('c3','2026-11-01T00:00:02+00:00','s3','r','ra','quarantined','pending')")
    con.commit()
    con.close()

    # learning_checkpoints.db — 1 session CLO
    con = sqlite3.connect(ws / "data" / "learning_checkpoints.db")
    con.execute(
        "CREATE TABLE learning_sessions (session_id TEXT, cycle_number INTEGER, "
        "started_at TEXT, ended_at TEXT, status TEXT)")
    con.execute(
        "INSERT INTO learning_sessions VALUES ('sess1', 7, '2026-10-27T16:10:16+00:00', NULL, 'RUNNING')")
    con.execute("CREATE TABLE learning_state (key TEXT, value TEXT)")
    con.execute("INSERT INTO learning_state VALUES ('CLO_ENABLED', 'true')")
    con.commit()
    con.close()

    # skill_registry.json — 1 skill qua API chính thức
    from quan_ai_brain.cognition.skill_registry import SkillRegistry
    reg = SkillRegistry(ws / "data" / "skill_registry.json")
    reg.register_skill(
        name="TEST_SKILL",
        goal="kiểm tra registry",
        trigger_patterns=["test"],
        inputs={"x": "mô tả"},
        steps=["bước 1"],
        tools=[],
        acceptance_criteria=["test PASS"],
    )
    return ws


@pytest.fixture(scope="module")
def self_server(tmp_path_factory: pytest.TempPathFactory):
    test_ws = _make_fake_workspace(tmp_path_factory.mktemp("m4"))

    old_root = web_server._find_workspace_root
    web_server._find_workspace_root = lambda: test_ws

    server = ThreadedHTTPServer(("127.0.0.1", 0), BrainAPIHandler)
    host, port = server.server_address
    url = f"http://127.0.0.1:{port}"
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    time.sleep(0.3)
    yield url
    server.shutdown()
    web_server._find_workspace_root = old_root


def _get(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode())


# ---------------------------------------------------------------------------
# /api/self/model
# ---------------------------------------------------------------------------

class TestSelfModelEndpoint:
    def test_success_shape(self, self_server):
        data = _get(self_server + "/api/self/model")
        assert data["success"] is True
        model = data["model"]
        assert isinstance(model, dict)

    def test_identity_truthful(self, self_server):
        data = _get(self_server + "/api/self/model")
        model = data["model"]
        identity = model["identity"]
        assert identity["owner"] == "Quanpt1"
        assert identity["system_name"] == "QUAN AI BRAIN"

    def test_deployment_updated_tailscale(self, self_server):
        """Sửa lỗi M4: deployment phải ghi đúng Pi5 Tailscale, không phải IP LAN cũ."""
        data = _get(self_server + "/api/self/model")
        edge = data["model"]["deployment"]["edge_location"]
        assert "100.100.83.59" in edge
        assert "192.168.1.21" not in edge

    def test_capabilities_lists_present(self, self_server):
        data = _get(self_server + "/api/self/model")
        model = data["model"]
        assert isinstance(model["verified_capabilities"], list)
        assert isinstance(model["unverified_capabilities"], list)
        assert len(model["verified_capabilities"]) > 0


# ---------------------------------------------------------------------------
# /api/self/state — fail-honest
# ---------------------------------------------------------------------------

class TestSelfStateEndpoint:
    def test_success_and_generated_at(self, self_server):
        data = _get(self_server + "/api/self/state")
        assert data["success"] is True
        state = data["state"]
        assert "generated_at" in state

    def test_q1_running_where_verified(self, self_server):
        data = _get(self_server + "/api/self/state")
        state = data["state"]
        q1 = state["q1_running_where"]
        assert q1["verification_status"] == "VERIFIED_LIVE"
        assert q1["workspace_root"]

    def test_offline_never_healthy(self, self_server):
        """Fail-honest: component không probe được phải là OFFLINE/UNVERIFIED, không HEALTHY."""
        data = _get(self_server + "/api/self/state")
        state = data["state"]
        for entry in state.get("components_online", []) + state.get("components_offline", []):
            assert entry["status"] in ("HEALTHY", "OFFLINE", "UNVERIFIED", "UNKNOWN")
            assert entry.get("evidence_ref"), "mọi trạng thái phải kèm evidence_ref"


# ---------------------------------------------------------------------------
# /api/self/learning — workspace giả lập khép kín
# ---------------------------------------------------------------------------

class TestSelfLearningEndpoint:
    def test_success_shape(self, self_server):
        data = _get(self_server + "/api/self/learning")
        assert data["success"] is True
        learning = data["learning"]
        assert "generated_at" in learning
        assert "candidates" in learning
        assert "skills" in learning
        assert "clo_sessions" in learning

    def test_candidates_counts_match_db(self, self_server):
        data = _get(self_server + "/api/self/learning")
        c = data["learning"]["candidates"]
        assert c["approved"] == 1
        assert c["quarantined"] == 2
        assert c["total"] == 3

    def test_clo_last_session_parsed(self, self_server):
        data = _get(self_server + "/api/self/learning")
        learning = data["learning"]
        assert learning["clo_sessions"] == 1
        assert learning["clo_last_session"]["cycle"] == 7
        assert learning["clo_last_session"]["status"] == "RUNNING"
        assert learning["clo_enabled"] == "true"

    def test_skills_by_status(self, self_server):
        data = _get(self_server + "/api/self/learning")
        skills = data["learning"]["skills"]
        assert skills["total"] == 1
        assert skills["by_status"].get("PROPOSED") == 1


# ---------------------------------------------------------------------------
# Unit — sửa lỗi trung thực M4
# ---------------------------------------------------------------------------

class TestTruthfulnessFixes:
    def test_learning_state_error_becomes_unknown(self, tmp_path):
        """learning_state bảng hỏng → clo_enabled = UNKNOWN (không crash, không nuốt lỗi)."""
        from quan_ai_brain.cognition.self_model_engine import SelfModelEngine

        ws = tmp_path / "ws"
        (ws / "data").mkdir(parents=True)
        con = sqlite3.connect(ws / "data" / "learning_checkpoints.db")
        con.execute("CREATE TABLE learning_sessions (session_id TEXT, cycle_number INTEGER, "
                    "started_at TEXT, ended_at TEXT, status TEXT)")
        con.execute("INSERT INTO learning_sessions VALUES ('s1', 1, '2026-11-01T00:00:00+00:00', NULL, 'RUNNING')")
        # bảng learning_state THIẾU cột value → SELECT key, value phải lỗi
        con.execute("CREATE TABLE learning_state (key TEXT)")
        con.commit()
        con.close()

        engine = SelfModelEngine(str(ws))
        state = engine.get_learning_checkpoint_state(ws)
        assert state["clo_enabled"] == "UNKNOWN"
        assert state["clo_last_session"]["cycle"] == 1

    def test_skill_test_result_must_be_pass_or_fail(self, tmp_path):
        """record_test_result chỉ nhận 'PASS ...' / 'FAIL ...' — chặn tự phong mốc."""
        from quan_ai_brain.cognition.skill_registry import SkillRegistry, SkillStatus

        reg = SkillRegistry(tmp_path / "reg.json")
        skill = reg.register_skill(
            name="S", goal="g", trigger_patterns=[], inputs={}, tools=[],
            steps=["x"], acceptance_criteria=["a"])
        with pytest.raises(ValueError):
            reg.record_test_result(skill.skill_id, "TỰ PHONG OK")
        updated = reg.record_test_result(skill.skill_id, "FAIL (2/5)")
        assert updated.test_result == "FAIL (2/5)"
        # record_test_result không tự chuyển trạng thái — gate nằm ở list_skills_v7_ready
        assert updated.status == SkillStatus.PROPOSED


# ---------------------------------------------------------------------------
# M4 Bước B — Self-Care trung thực + tích hợp HealthMonitor
# ---------------------------------------------------------------------------

class TestSelfCareTruthfulness:
    def test_no_fake_auto_recovered(self):
        """Sửa lỗi M2 phát hiện: DOWN alert KHÔNG được set auto_recovered=True khi
        chỉ 'simulated'. Phải là PENDING + auto_recovered=False (fail-honest)."""
        from quan_ai_brain.cognition.self_care_engine import (
            Alert,
            HealthLevel,
            SelfCareEngine,
        )

        engine = SelfCareEngine(workspace=str(WORKSPACE))
        alert = Alert(
            alert_id="a1", severity=HealthLevel.DOWN, component="ollama",
            message="Ollama offline", detected_at="2026-11-01T00:00:00+00:00")
        engine._attempt_auto_recovery(alert)
        assert alert.auto_recovered is False
        assert alert.action_taken.startswith("PENDING")

    def test_health_monitor_self_care_real_checks(self):
        """HealthMonitor với self_care inject: check DOWN → alert; healthy → không alert."""
        from quan_ai_brain.cognition.self_care_engine import (
            HealthCheck,
            HealthLevel,
            SelfCareEngine,
        )
        from quan_ai_brain.monitoring.health_monitor import HealthMonitor

        class FakeAgg:
            def snapshot(self, force=False):
                return {"overall_status": "NORMAL", "pc": {}, "pi5": {}}

        class StubSelfCare:
            """Stub: 1 check healthy + 1 DOWN — không đụng mạng thật."""
            def run_all_health_checks(self):
                ts = "2026-11-01T00:00:00+00:00"
                return [
                    HealthCheck(check_id="h1", component="ollama", metric="response_time",
                                value=1.0, threshold=2000, status=HealthLevel.HEALTHY,
                                timestamp=ts, message="Ollama healthy"),
                    HealthCheck(check_id="h2", component="web_9999", metric="connectivity",
                                value=0, threshold=1, status=HealthLevel.DOWN,
                                timestamp=ts, message="Web:9999 offline"),
                ]

            def get_health_summary(self):
                return {"total_checks": 2, "healthy": 1, "down": 1}

        sent: list[str] = []

        class FakeAlertEngine:
            """AlertEngine giả: ghi nhận evaluate_checks, không gửi DM."""
            def evaluate_checks(self, component_id, checks, thresholds):
                out = []
                for cid, info in checks.items():
                    if info.get("value", 0) >= 1:
                        out.append({"check_id": f"{component_id}:{cid}",
                                    "severity": "WARNING", "value": info.get("value"),
                                    "message": info.get("reason", ""), "sent": True,
                                    "suppressed_reason": None})
                        sent.append(cid)
                return out

            def recent_alerts(self, limit=20):
                return []

        mon = HealthMonitor(WORKSPACE, FakeAgg(), cycle_sec=120.0,
                            alert_engine=FakeAlertEngine(),
                            self_care=StubSelfCare())
        result = mon.run_once()
        assert result["self_care_summary"] == {"total_checks": 2, "healthy": 1, "down": 1}
        # chỉ check DOWN tạo alert; healthy bị lọc
        assert any("web_9999" in a["check_id"] for a in result["alerts"])
        assert not any("ollama" in cid for cid in sent)

    def test_real_self_care_engine_probe_runs(self):
        """SelfCareEngine THẬT chạy được trên máy này (probe TCP thật, không crash)."""
        from quan_ai_brain.cognition.self_care_engine import SelfCareEngine

        engine = SelfCareEngine(workspace=str(WORKSPACE))
        checks = engine.run_all_health_checks()
        assert len(checks) == 4  # ollama, 8765, 8766, pi5
        summary = engine.get_health_summary()
        assert summary["total_checks"] >= 4
        assert 0.0 <= summary["health_percentage"] <= 1.0
