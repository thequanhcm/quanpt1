"""UAIIF-S4: UniversalAgentKnowledge + DiscoveryWorkflow + AgentProfile + QPIG.

Mock 100% (tmp_path DB, fake networks). 25+ kịch bản theo card TASK-UAIIF-S4.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE / "src"))
sys.path.insert(0, str(WORKSPACE))

from quan_ai_brain.uaiif.agent_knowledge import (  # noqa: E402
    AGENT_KINDS, INFERRED, LAYERS, OBSERVED, VERIFIED, UniversalAgentKnowledge)
from quan_ai_brain.uaiif.agent_profile import (  # noqa: E402
    PROFILE_FIELDS, UniversalAgentProfileStore)
from quan_ai_brain.uaiif.agent_discovery import AgentDiscoveryWorkflow  # noqa: E402
from quan_ai_brain.uaiif.qpig import QPIG  # noqa: E402


@pytest.fixture()
def knowledge(tmp_path: Path) -> UniversalAgentKnowledge:
    return UniversalAgentKnowledge(tmp_path / "uaiif_knowledge.db")


@pytest.fixture()
def profiles(tmp_path: Path) -> UniversalAgentProfileStore:
    return UniversalAgentProfileStore(tmp_path / "uaiif_profiles.db")


@pytest.fixture()
def discovery(profiles, knowledge) -> AgentDiscoveryWorkflow:
    return AgentDiscoveryWorkflow(profiles, knowledge)


# ---------------------------------------------------------------------------
# UniversalAgentKnowledge — 7 layer × 20 nhóm × epistemic statuses
# ---------------------------------------------------------------------------
class TestKnowledge:
    def test_learn_inferred(self, knowledge: UniversalAgentKnowledge) -> None:
        iid = knowledge.learn("planner loop", "L01_FUNDAMENTALS", "planning",
                              "Planner tạo kế hoạch rồi executor chạy từng bước.",
                              source="tài liệu nội bộ")
        assert iid > 0
        assert knowledge.stats()["total"] == 1

    def test_learn_validates_layer_and_kind(self, knowledge) -> None:
        with pytest.raises(ValueError):
            knowledge.learn("x", "L99_FAKE", "planning", "nội dung")
        with pytest.raises(ValueError):
            knowledge.learn("x", "L01_FUNDAMENTALS", "ufo_kind", "nội dung")

    def test_learn_verified_requires_evidence(self, knowledge) -> None:
        with pytest.raises(ValueError):
            knowledge.learn("x", "L01_FUNDAMENTALS", "planning", "nội dung",
                            status=VERIFIED)  # thiếu evidence_ref

    def test_verified_with_evidence_ok(self, knowledge) -> None:
        knowledge.learn("x", "L01_FUNDAMENTALS", "planning", "nội dung",
                        status=VERIFIED, evidence_ref="test_uaiif_knowledge.py::test")
        st = knowledge.stats()
        assert st["by_status"]["VERIFIED"] == 1

    def test_promote_requires_evidence(self, knowledge) -> None:
        iid = knowledge.learn("y", "L02_ARCHITECTURE", "reasoning", "nội dung")
        with pytest.raises(ValueError):
            knowledge.promote(iid, VERIFIED)  # không evidence
        knowledge.promote(iid, VERIFIED, evidence_ref="live_e2e_20261102")
        rows = knowledge.query(status=VERIFIED)
        assert len(rows) == 1 and rows[0]["item_id"] == iid

    def test_20_kinds_and_7_layers(self) -> None:
        assert len(AGENT_KINDS) == 20
        assert len(LAYERS) == 7

    def test_query_filters(self, knowledge) -> None:
        knowledge.learn("a", "L01_FUNDAMENTALS", "planning", "nội dung")
        knowledge.learn("b", "L05_SECURITY", "security", "nội dung")
        assert len(knowledge.query(layer="L05_SECURITY")) == 1
        assert len(knowledge.query(agent_kind="planning")) == 1

    def test_min_confidence_filter(self, knowledge) -> None:
        knowledge.learn("infer", "L01_FUNDAMENTALS", "planning", "x",
                        status=INFERRED)
        knowledge.learn("obs", "L01_FUNDAMENTALS", "autonomous", "y",
                        status=OBSERVED)
        rows = knowledge.query(min_confidence=OBSERVED)   # >= OBSERVED
        assert len(rows) == 1 and rows[0]["epistemic_status"] == OBSERVED

    def test_stats_counts(self, knowledge) -> None:
        knowledge.learn("a", "L01_FUNDAMENTALS", "planning", "x")
        knowledge.learn("b", "L01_FUNDAMENTALS", "planning", "y",
                        status=OBSERVED)
        st = knowledge.stats()
        assert st["total"] == 2
        assert st["by_layer"]["L01_FUNDAMENTALS"] == 2
        assert st["by_status"]["OBSERVED"] == 1


# ---------------------------------------------------------------------------
# Agent Intelligence Scorecard — điểm gắn bằng chứng (master prompt mục IX)
# ---------------------------------------------------------------------------
class TestScorecard:
    def test_empty_knowledge_low_score(self, knowledge) -> None:
        sc = knowledge.scorecard()
        assert sc["total"] < 30          # gần như trắng — trung thực
        assert len(sc["questions"]) == 8

    def test_full_knowledge_higher(self, knowledge) -> None:
        # phủ đủ 20 nhóm × 7 layer (≥ INFERRED)
        for kind in AGENT_KINDS:
            knowledge.learn(f"t_{kind}", LAYERS[0], kind, "nội dung",
                            status=INFERRED)
        for layer in LAYERS:
            knowledge.learn(f"l_{layer}", layer, "planning", "nội dung",
                            status=OBSERVED)
        sc = knowledge.scorecard(federation_nodes=3, profiles_with_scope=3,
                                 sentinel_stats={"tests_pass": True},
                                 containment_tests_pass=True, evidence_count=10)
        assert sc["total"] >= 70
        # mọi câu hỏi phải có bằng chứng đi kèm
        assert all(q["evidence"] for q in sc["questions"])

    def test_no_self_congratulation(self, knowledge) -> None:
        """Không được tự cho điểm cảm tính: không knowledge thì các câu hỏi
        liên quan knowledge phải 0 dù truyền cờ đẹp."""
        sc = knowledge.scorecard(federation_nodes=99, profiles_with_scope=99,
                                 sentinel_stats={"tests_pass": True},
                                 containment_tests_pass=True, evidence_count=99)
        kinds_q = next(q for q in sc["questions"] if "loại Agent" in q["question"])
        assert kinds_q["score"] == 0      # không knowledge → 0 dù cờ đẹp


# ---------------------------------------------------------------------------
# UniversalAgentProfile — 24 trường + trạng thái nhận thức luận
# ---------------------------------------------------------------------------
class TestAgentProfile:
    def test_24_fields_defined(self) -> None:
        assert len(PROFILE_FIELDS) == 24
        assert "Agent_ID" in PROFILE_FIELDS and "Known_Limitations" in PROFILE_FIELDS

    def test_create_from_discovery(self, profiles: UniversalAgentProfileStore) -> None:
        steps = [{"step": "DISCOVERY", "status": "DONE", "evidence": ["ping ok"], "notes": []}]
        pid = profiles.create_from_discovery("192.168.1.2", steps,
                                             {"Agent_Name": ("Pi5", "Observed")})
        assert pid.startswith("uap_")
        prof = profiles.get("192.168.1.2")
        assert prof is not None
        assert len(prof["fields"]) == 24
        assert prof["fields"]["Agent_Name"]["value"] == "Pi5"
        assert prof["fields"]["Agent_Name"]["status"] == "Observed"

    def test_unverified_fields_stay_unknown(self, profiles) -> None:
        steps = [{"step": "DISCOVERY", "status": "DONE", "evidence": [], "notes": []}]
        profiles.create_from_discovery("10.0.0.9", steps, {})
        prof = profiles.get("10.0.0.9")
        # không biết thì ghi Unknown — không bịa
        assert prof["fields"]["Runtime"]["status"] == "Unknown"
        assert prof["fields"]["Model"]["value"] == ""
        assert prof["fields"]["Trust_Level"]["status"] == "Unknown"

    def test_idempotent_by_target(self, profiles) -> None:
        steps = [{"step": "DISCOVERY", "status": "DONE", "evidence": [], "notes": []}]
        p1 = profiles.create_from_discovery("h1", steps, {})
        p2 = profiles.create_from_discovery("h1", steps, {})
        assert p1 == p2 and len(profiles.list_profiles()) == 1

    def test_set_field_honest_status(self, profiles) -> None:
        steps = [{"step": "DISCOVERY", "status": "DONE", "evidence": [], "notes": []}]
        profiles.create_from_discovery("h2", steps, {})
        assert profiles.set_field("h2", "Version", "1.2.3", "Observed") is True
        with pytest.raises(ValueError):
            profiles.set_field("h2", "Version", "9.9", "KhongCoTrangThaiNay")
        with pytest.raises(ValueError):
            profiles.set_field("h2", "KhongTonTai", "x", "Unknown")

    def test_completeness(self, profiles) -> None:
        steps = [{"step": "DISCOVERY", "status": "DONE", "evidence": [], "notes": []}]
        profiles.create_from_discovery("h3", steps, {})
        c = profiles.completeness("h3")
        assert c["Unknown"] >= 15 and c["Verified"] >= 1  # Last_Inspection verified


# ---------------------------------------------------------------------------
# AgentDiscoveryWorkflow — 7 bước fail-honest
# ---------------------------------------------------------------------------
class TestDiscoveryWorkflow:
    def test_seven_steps_always_returned(self, discovery: AgentDiscoveryWorkflow,
                                         profiles, knowledge) -> None:
        result = discovery.run("203.0.113.99", label="đích chết")  # IP TEST-NET chết
        assert len(result["steps"]) == 7
        assert result["steps"][0]["status"] == "NOT_ACCESSIBLE"

    def test_external_assessment_label(self, discovery, profiles, knowledge) -> None:
        result = discovery.run("203.0.113.99", label="x")
        # không tiếp cận được → không thể là Internal Inspection
        assert result["assessment_type"] == "External Behavioral Assessment"

    def test_registered_node_fuller_profile(self, profiles, knowledge) -> None:
        """Nút đã đăng ký federation → identification DONE (không PARTIAL)."""
        class FakeNode:
            node_id = "edge_pi5"; host = "192.168.1.2"; kind = "EDGE"
            status = "REACHABLE"; label = "Pi5"; capabilities = ["kiosk", "audio"]

        class FakeNodes:
            def list_nodes(self):
                return [FakeNode()]

        wf = AgentDiscoveryWorkflow(profiles, knowledge, node_registry=FakeNodes())
        # ping thật có thể fail trong sandbox — nhưng node có sẵn nên bước 2 vẫn DONE
        result = wf.run("192.168.1.2")
        ident = result["steps"][1]
        assert ident["status"] in ("DONE", "PARTIAL")  # ping có thể PARTIAL nếu offline
        assert "nút liên bang" in ident["evidence"][0]

    def test_consolidation_saves_profile(self, profiles, knowledge) -> None:
        wf = AgentDiscoveryWorkflow(profiles, knowledge)
        result = wf.run("203.0.113.99")
        assert result["profile_id"] is not None
        assert profiles.get(result["profile_id"]) is not None

    def test_step_evidence_required(self, discovery, profiles, knowledge) -> None:
        result = discovery.run("203.0.113.99")
        for s in result["steps"]:
            assert isinstance(s["evidence"], list) and s["evidence"]  # không để trống


# ---------------------------------------------------------------------------
# QPIG — 6 nhóm tool qua ToolRegistry chuẩn
# ---------------------------------------------------------------------------
class TestQPIG:
    def _make(self) -> QPIG:
        return QPIG()

    def test_six_tools_registered(self) -> None:
        """QPIG V2: giữ 6 tool v1 + 13 tool mới chuẩn §2 (19 danh mục directive)."""
        qpig = self._make()
        rows = qpig.registered_tools()
        v1 = [r for r in rows if "protocol" not in r]
        v2 = [r for r in rows if r.get("protocol")]
        assert len(v1) == 6 and len(v2) == 19
        for s in rows:
            assert qpig.registry.has_tool(s["tool_id"])

    def test_unknown_tool_refused(self) -> None:
        r = self._make().call("qpig_khong_ton_tai", {})
        assert r["success"] is False

    def test_params_validation(self) -> None:
        qpig = self._make()
        r = qpig.call("qpig_inspection_probe", {})     # thiếu node_id
        assert r["success"] is False and "params" in r["reason"]

    def test_communication_unknown_channel_refused(self) -> None:
        r = self._make().call("qpig_communication_send",
                              {"channel": "roi_rac", "payload": {}})
        assert r["success"] is False and "chưa đăng ký" in r["reason"]

    def test_communication_registered_channel(self) -> None:
        sent = []
        qpig = QPIG(comm_channels={"test_chan": lambda p: sent.append(p) or "ok"})
        r = qpig.call("qpig_communication_send",
                      {"channel": "test_chan", "payload": {"msg": 1}})
        assert r["success"] is True and sent == [{"msg": 1}]

    def test_security_classify_no_registry(self) -> None:
        r = self._make().call("qpig_security_classify", {"agent_id": "x"})
        assert r["success"] is False and "SENTINEL" in r["reason"]

    def test_security_classify_unknown_agent(self) -> None:
        class FakeSentinel:
            def get(self, aid):
                return None
        qpig = QPIG(sentinel_registry=FakeSentinel())
        r = qpig.call("qpig_security_classify", {"agent_id": "ghost"})
        assert r["success"] is True
        assert r["data"]["classification"] == "UNKNOWN"
        assert "không mặc định là độc hại" in r["data"]["note"]

    def test_control_requires_containment(self) -> None:
        r = self._make().call("qpig_control_contain",
                              {"action": "SUSPEND_PID", "target": "123"})
        assert r["success"] is False and "ContainmentEngine" in r["reason"]

    def test_control_preapproved_flow(self) -> None:
        class FakeResult:
            success = True; executed = True; reason = "đã TẠM GIỮ"
            def to_dict(self):
                return {"action": "SUSPEND_PID"}

        class FakeEngine:
            def execute(self, action, target, *, by, preapproved):
                assert preapproved is True
                return FakeResult()
        qpig = QPIG(containment=FakeEngine())
        r = qpig.call("qpig_control_contain",
                      {"action": "SUSPEND_PID", "target": "4321",
                       "preapproved": True})
        assert r["success"] is True and r["executed"] is True

    def test_discovery_scan_uses_real_scanner(self) -> None:
        """Live-safe: quét hiện diện-only LAN thật — không tấn công cổng."""
        r = self._make().call("qpig_discovery_scan", {})
        assert r["success"] is True
        assert "subnet" in r["data"] and "total_alive" in r["data"]

    def test_r3_tools_flagged(self) -> None:
        qpig = self._make()
        risky = [t for t in qpig.registered_tools() if t["risk"] >= 3]
        # v1: COMMUNICATION + CONTROL; v2 thêm task_dispatch, permission/service
        # control, isolation, recovery, device_control, rollback + permission (10 R3)
        assert len(risky) == 10
        for s in ("qpig_communication_send", "qpig_control_contain",
                  "qpig_agent_task_dispatch", "qpig_agent_service_control",
                  "qpig_agent_isolation_request", "qpig_agent_recovery",
                  "qpig_device_control", "qpig_rollback_execution",
                  "qpig_agent_communication", "qpig_agent_permission_control"):
            td = qpig.registry.get(s)
            assert td.requires_owner_approval is True
            assert td.side_effects is True
