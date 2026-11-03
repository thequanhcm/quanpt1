"""SENTINEL-S3: AgentIdentityRegistry + ThreatLevelMachine + ContainmentEngine + DM.

Mock 100% (tmp_path DB, monkeypatch actions). 30 kịch bản theo card
TASK-SENTINEL-S3 — bao phủ: phân loại, scoring, threat levels, authorization
gates 3 cấp, evidence, false-positive, SENTINEL không tự nâng quyền.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE / "src"))
sys.path.insert(0, str(WORKSPACE))

from quan_ai_brain.security.agent_identity import (  # noqa: E402
    COMPROMISED, MALICIOUS, ST_CONTAINED, ST_NORMAL, ST_RESTRICTED, SUSPICIOUS,
    TRUSTED, UNAUTHORIZED, UNKNOWN, AgentIdentityRegistry)
from quan_ai_brain.security.threat_levels import ThreatLevelMachine  # noqa: E402
from quan_ai_brain.security.containment import (  # noqa: E402
    ContainmentEngine, EvidenceStore)


@pytest.fixture()
def reg(tmp_path: Path) -> AgentIdentityRegistry:
    return AgentIdentityRegistry(tmp_path / "agents.db")


@pytest.fixture()
def tlm(tmp_path: Path) -> ThreatLevelMachine:
    return ThreatLevelMachine(tmp_path / "levels.db")


@pytest.fixture()
def engine(tmp_path: Path) -> ContainmentEngine:
    return ContainmentEngine(EvidenceStore(tmp_path / "evidence.db"))


# ---------------------------------------------------------------------------
# M01+M04 — AgentIdentityRegistry
# ---------------------------------------------------------------------------
class TestAgentIdentity:
    def test_observe_new_unknown(self, reg: AgentIdentityRegistry) -> None:
        ident = reg.observe("proc_100", "codex.exe", "PROCESS")
        assert ident.classification == UNKNOWN
        assert ident.trust_score == 20 and ident.risk_score == 20
        assert ident.security_status == "MONITORED"

    def test_observe_registered_trusted(self, reg: AgentIdentityRegistry) -> None:
        ident = reg.observe("edge_pi5", "Pi5", "EDGE", registered=True)
        assert ident.classification == TRUSTED
        assert ident.trust_score == 60 and ident.security_status == ST_NORMAL

    def test_observe_contract_trusted(self, reg: AgentIdentityRegistry) -> None:
        ident = reg.observe("proc_200", "agent.exe", "PROCESS", contract_active=True)
        assert ident.classification == TRUSTED and ident.trust_score == 50

    def test_observe_idempotent_no_rescore(self, reg: AgentIdentityRegistry) -> None:
        reg.observe("proc_100", "codex.exe", "PROCESS")
        ident = reg.observe("proc_100", "codex.exe", "PROCESS")  # gặp lại
        assert ident.trust_score == 20                           # không cộng dồn
        assert ident.classification == UNKNOWN

    def test_observe_validation(self, reg: AgentIdentityRegistry) -> None:
        with pytest.raises(ValueError):
            reg.observe("", "x", "PROCESS")
        with pytest.raises(ValueError):
            reg.observe("a", "x", "UFO")

    def test_find_by_name(self, reg: AgentIdentityRegistry) -> None:
        reg.observe("proc_1", "codex.exe", "PROCESS")
        reg.observe("proc_2", "claude.exe", "PROCESS")
        assert len(reg.find_by_name("codex")) == 1

    def test_counts_by_classification(self, reg: AgentIdentityRegistry) -> None:
        reg.observe("a", "a", "PROCESS")
        reg.observe("b", "b", "PROCESS", registered=True)
        c = reg.counts()
        assert c["UNKNOWN"] == 1 and c["TRUSTED"] == 1

    def test_violation_unknown_becomes_unauthorized(self, reg) -> None:
        reg.observe("p1", "x.exe", "PROCESS")
        ident = reg.apply_violation("p1", "OUT_OF_SCOPE_PATH")
        assert ident.classification == UNAUTHORIZED
        assert ident.trust_score == 0 and ident.risk_score == 45  # clamp 0, 20+25
        assert ident.evidence_count == 1

    def test_violation_trusted_becomes_suspicious(self, reg) -> None:
        reg.observe("p2", "y.exe", "PROCESS", registered=True)
        ident = reg.apply_violation("p2", "OVER_CONTRACT")
        assert ident.classification == SUSPICIOUS
        assert ident.security_status == ST_RESTRICTED

    def test_violation_requires_existing(self, reg) -> None:
        with pytest.raises(ValueError):
            reg.apply_violation("ghost", "X")

    def test_set_classification_by_sentinel_refused(self, reg) -> None:
        reg.observe("p3", "z.exe", "PROCESS")
        with pytest.raises(PermissionError):
            reg.set_classification("p3", MALICIOUS, by="sentinel")

    def test_set_classification_owner_allowed(self, reg) -> None:
        reg.observe("p4", "w.exe", "PROCESS")
        ident = reg.set_classification("p4", COMPROMISED, by="owner",
                                       evidence_ref="inv_001")
        assert ident.classification == COMPROMISED
        assert ident.security_status == ST_RESTRICTED

    def test_set_classification_sentinel_with_evidence_ok(self, reg) -> None:
        reg.observe("p5", "v.exe", "PROCESS")
        ident = reg.set_classification("p5", COMPROMISED, by="sentinel",
                                       evidence_ref="investigation_42")
        assert ident.classification == COMPROMISED

    def test_behavior_history_capped(self, reg) -> None:
        reg.observe("p6", "u.exe", "PROCESS")
        for i in range(60):
            reg.record_behavior("p6", {"n": i})
        ident = reg.get("p6")
        import json as _json
        with reg._connect() as conn:
            row = conn.execute(
                "SELECT behavior_history FROM sentinel_identities WHERE agent_id='p6'"
            ).fetchone()
        assert len(_json.loads(row["behavior_history"])) == 50

    def test_false_positive_trusted_untouched(self, reg) -> None:
        """Kịch bản False Positive: agent TRUSTED hoạt động đúng → không bị làm phiền."""
        reg.observe("good", "responder.py", "PROCESS", contract_active=True)
        before = reg.get("good")
        # watchdog quét lại nhiều lần — không vi phạm
        for _ in range(5):
            reg.observe("good", "responder.py", "PROCESS")
        after = reg.get("good")
        assert after.classification == TRUSTED
        assert after.trust_score == before.trust_score
        assert after.security_status == ST_NORMAL


# ---------------------------------------------------------------------------
# ThreatLevelMachine — 5 cấp + governance
# ---------------------------------------------------------------------------
class TestThreatLevels:
    def test_initial_L0(self, tlm: ThreatLevelMachine) -> None:
        assert tlm.current_level() == ThreatLevelMachine.L0

    def test_set_level_with_evidence(self, tlm: ThreatLevelMachine) -> None:
        r = tlm.set_level(tlm.L2, reason="vi phạm đo được", by="sentinel",
                          evidence_ref="ev_7")
        assert r["to"] == tlm.L2 and tlm.current_level() == tlm.L2

    def test_set_level_sentinel_no_evidence_refused(self, tlm) -> None:
        with pytest.raises(PermissionError):
            tlm.set_level(tlm.L3, reason="nghi ngờ", by="sentinel")

    def test_set_level_invalid(self, tlm) -> None:
        with pytest.raises(ValueError):
            tlm.set_level("L9", reason="x", by="owner")

    def test_set_level_no_reason_refused(self, tlm) -> None:
        with pytest.raises(ValueError):
            tlm.set_level(tlm.L1, reason="  ", by="owner")

    def test_lower_from_L4_owner_only(self, tlm) -> None:
        tlm.set_level(tlm.L4, reason="sự cố thật", by="sentinel",
                      evidence_ref="ev_9")
        with pytest.raises(PermissionError):
            tlm.set_level(tlm.L0, reason="hồi phục", by="sentinel")
        r = tlm.set_level(tlm.L0, reason="owner xác nhận an toàn", by="owner")
        assert r["to"] == tlm.L0

    def test_L4_notifies_owner(self, tmp_path: Path) -> None:
        sent: list[str] = []
        t = ThreatLevelMachine(tmp_path / "l2.db",
                               notify_owner=lambda msg: sent.append(msg))
        t.set_level(t.L4, reason="ransomware behavior", by="sentinel",
                    evidence_ref="ev_10")
        assert len(sent) == 1 and "L4" in sent[0]

    def test_history_append_only(self, tlm: ThreatLevelMachine) -> None:
        tlm.set_level(tlm.L1, reason="a", by="owner")
        tlm.set_level(tlm.L0, reason="b", by="owner")
        h = tlm.history()
        assert len(h) == 2 and h[0]["to_level"] == tlm.L0  # mới nhất đầu, cột to_level


# ---------------------------------------------------------------------------
# Containment — phân quyền 3 cấp + evidence
# ---------------------------------------------------------------------------
class TestContainment:
    def test_evidence_roundtrip(self, tmp_path: Path) -> None:
        ev = EvidenceStore(tmp_path / "e.db")
        eid = ev.capture("SNAPSHOT", "pid:99", {"pid": 99, "cmd": "x"})
        got = ev.get(eid)
        assert got["payload"]["pid"] == 99 and len(got["sha256"]) == 64

    def test_human_action_refused_for_sentinel(self, engine: ContainmentEngine) -> None:
        r = engine.execute("DELETE_EVIDENCE", "ev_1", by="sentinel")
        assert r.success is False and r.executed is False and r.authority == "HUMAN"

    def test_controlled_needs_approval(self, engine: ContainmentEngine) -> None:
        r = engine.execute("STOP_IMPORTANT_AGENT", "responder", by="sentinel")
        assert r.executed is False and r.authority == "CONTROLLED"

    def test_controlled_with_approval_ok(self, tmp_path: Path) -> None:
        eng = ContainmentEngine(
            EvidenceStore(tmp_path / "e.db"),
            approval_check=lambda action, target: True)
        r = eng.execute("STOP_IMPORTANT_AGENT", "responder", by="sentinel")
        assert r.success is True            # đã qua gate — ghi kế hoạch chờ sprint R4
        assert r.details["planned_only"] is True

    def test_owner_bypasses_controlled(self, engine: ContainmentEngine) -> None:
        r = engine.execute("SECURITY_CONFIG_CHANGE", "policy", by="owner")
        assert r.success is True and r.authority == "CONTROLLED"

    def test_preserve_evidence_before_action(self, engine: ContainmentEngine) -> None:
        eid = engine.preserve_evidence(999999, "agent_x")   # PID không tồn tại vẫn chụp
        got = engine.evidence.get(eid)
        assert got["kind"] == "SNAPSHOT" and "pid" in got["payload"]

    def test_suspend_delegates_to_actions(self, engine: ContainmentEngine, monkeypatch) -> None:
        called: dict = {}

        def fake_suspend(pid: int):
            called["pid"] = pid
            return {"success": True, "action": "suspend", "pid": pid,
                    "reason": "đã TẠM GIỮ"}
        from quan_ai_brain.security import actions as actions_mod
        monkeypatch.setattr(actions_mod, "suspend_process", fake_suspend)
        r = engine.execute("SUSPEND_PID", "4321", by="sentinel", preapproved=True,
                           evidence_id=7)
        assert called["pid"] == 4321
        assert r.success is True and r.details["tool_result"] == "đã TẠM GIỮ"
        assert r.evidence_id == 7

    def test_whitelist_refuses_via_actions(self, engine: ContainmentEngine) -> None:
        """SENTINEL không được đụng tiến trình bảo vệ (tự bảo vệ S1 giữ nguyên)."""
        # watchdog PID thật đang chạy → whitelist phải refuse
        import subprocess as sp

        r = sp.run(["tasklist", "/FI", "IMAGENAME eq pythonw.exe", "/FO", "CSV"],
                   capture_output=True, text=True)
        pids = []
        for ln in (r.stdout or "").splitlines()[1:]:
            parts = [p.strip('"') for p in ln.split('","')]
            if len(parts) >= 2 and parts[1].isdigit():
                pids.append(parts[1])          # cột 1 = PID trong CSV
        if not pids:
            pytest.skip("không có pythonw để test whitelist")
        res = engine.execute("SUSPEND_PID", pids[0], by="sentinel", preapproved=True)
        assert res.success is False     # whitelist fail-closed chặn

    def test_result_to_dict(self, engine: ContainmentEngine) -> None:
        r = engine.execute("DELETE_EVIDENCE", "ev_1", by="sentinel")
        d = r.to_dict()
        assert d["authority"] == "HUMAN" and d["executed"] is False


# ---------------------------------------------------------------------------
# DM commands SENTINEL
# ---------------------------------------------------------------------------
class TestSentinelDm:
    def test_dashboard(self, tmp_path: Path, monkeypatch) -> None:
        import tools.netchat_security_center as sec

        monkeypatch.setattr(sec, "WORKSPACE", tmp_path)
        intent, reply = sec.route_security_command("sentinel")
        assert intent == "sentinel"
        assert "SENTINEL" in reply and "L0_NORMAL" in reply

    def test_agent_profile_not_found(self, tmp_path: Path, monkeypatch) -> None:
        import tools.netchat_security_center as sec

        monkeypatch.setattr(sec, "WORKSPACE", tmp_path)
        intent, reply = sec.route_security_command("sentinel agent ghost.exe")
        assert intent == "sentinel_agent"
        assert "Không có hồ sơ" in reply

    def test_agent_profile_found(self, tmp_path: Path, monkeypatch) -> None:
        import tools.netchat_security_center as sec
        from quan_ai_brain.security.agent_identity import AgentIdentityRegistry

        monkeypatch.setattr(sec, "WORKSPACE", tmp_path)
        reg = AgentIdentityRegistry(tmp_path / "data" / "sentinel_agents.db")
        reg.observe("proc_777", "codex.exe", "PROCESS")
        intent, reply = sec.route_security_command("sentinel agent codex")
        assert intent == "sentinel_agent"
        assert "codex.exe" in reply and "UNKNOWN" in reply

    def test_level_change_via_owner_dm(self, tmp_path: Path, monkeypatch) -> None:
        import tools.netchat_security_center as sec

        monkeypatch.setattr(sec, "WORKSPACE", tmp_path)
        intent, reply = sec.route_security_command("sentinel mức L2")
        assert intent == "sentinel_level"
        assert "L0_NORMAL → L2_RESTRICT" in reply
        # trạng thái giữ thật qua DB
        from quan_ai_brain.security.threat_levels import ThreatLevelMachine
        assert ThreatLevelMachine(
            tmp_path / "data" / "sentinel_threat_levels.db").current_level() == \
            ThreatLevelMachine.L2

    def test_route_message_integration(self, tmp_path: Path, monkeypatch) -> None:
        from tools.netchat_command_center import route_message

        monkeypatch.setattr("tools.netchat_security_center.WORKSPACE", tmp_path)
        intent, reply = route_message("sentinel")
        assert intent == "sentinel"

    def test_no_crash_on_empty_registry(self, tmp_path: Path, monkeypatch) -> None:
        import tools.netchat_security_center as sec

        monkeypatch.setattr(sec, "WORKSPACE", tmp_path)
        _, reply = sec.route_security_command("sentinel")
        assert "0" in reply or "TRUSTED 0" in reply
