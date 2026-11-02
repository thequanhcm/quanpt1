"""QPIG V2.0 — test 19-tool Universal Action Gateway (mock 100% tmp_path).

Chứng minh:
- §2: 19 tool chuẩn directive, 10 thuộc tính/tool, operational chỉ khai khi đã chạy thật
- §3: adapter framework sandbox + grant scope
- §4: engine 10 bước — KHÔNG execute khi thiếu approval
- §6: approval token gắn một tool, consume một-lần, không tái sử dụng
- §7: evidence lưu + đối chiếu được
- Pi5 thật: REACHABLE nhưng SSH đóng → tool Pi5 refuse fail-honest
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from quan_ai_brain.uaiif.qpig import (  # noqa: E402
    ADAPTER_REGISTRY, DIRECTIVE_NAMES, PENDING_PROTOCOLS, ActionExecutionEngine,
    ActionRequest, AdapterGrant, HTTPAdapter, QPIG,
)
from quan_ai_brain.security.containment import EvidenceStore  # noqa: E402


class FakeApprovalService:
    """Mô phỏng ApprovalCardService: consume một-lần, gắn action_fingerprint."""

    def __init__(self, valid_ids: set[str] | None = None) -> None:
        self.valid = valid_ids or set()
        self.consumed: list[tuple[str, str]] = []

    def get_card(self, approval_id: str):
        if approval_id not in self.valid:
            return None
        return object()  # thẻ tồn tại — chưa consume

    def consume(self, approval_id: str, *, actor: str = "",
                action_fingerprint: str | None = None) -> object:
        if approval_id not in self.valid:
            raise ValueError("không tìm thấy approval")
        if any(c[0] == approval_id for c in self.consumed):
            raise ValueError("approval đã dùng — không tái sử dụng (§6)")
        self.consumed.append((approval_id, action_fingerprint or ""))
        return object()


class FakeSentinel:
    def get(self, agent_id): return None  # chưa có hồ sơ → UNKNOWN


class FakeNodes:
    def probe_node(self, node_id): return {"success": True, "node_id": node_id}


def make_qpig(tmp_path, **kw) -> QPIG:
    ev = EvidenceStore(tmp_path / "ev.db")
    return QPIG(evidence_store=ev, sentinel_registry=FakeSentinel(),
                node_registry=FakeNodes(), **kw)


# ---------------------------------------------------------------------------
def test_catalog_19_tools_with_10_attributes(tmp_path) -> None:
    """§2: đủ 19 tên directive + mỗi tool có 10 thuộc tính bắt buộc."""
    q = make_qpig(tmp_path)
    rows = {r["tool_id"]: r for r in q.registered_tools()}
    # 25 = 19 tool chuẩn §2 + 6 alias v1 (backward-compat UAIIF-S4)
    assert len(rows) == 25
    assert set(DIRECTIVE_NAMES.values()) <= set(rows)
    assert set(DIRECTIVE_NAMES) == {
        "DEVICE_DISCOVERY", "DEVICE_IDENTIFICATION", "NETWORK_INSPECTION",
        "AGENT_DISCOVERY", "AGENT_AUTHENTICATION", "AGENT_COMMUNICATION",
        "AGENT_STATUS", "AGENT_TASK_DISPATCH", "AGENT_RESULT_RETRIEVAL",
        "AGENT_PERMISSION_INSPECTION", "AGENT_PERMISSION_CONTROL",
        "AGENT_RUNTIME_INSPECTION", "AGENT_SERVICE_CONTROL", "AGENT_ISOLATION_REQUEST",
        "AGENT_RECOVERY", "DEVICE_CONTROL", "EVIDENCE_COLLECTION",
        "ACTION_VERIFICATION", "ROLLBACK_EXECUTION"}
    for tid, row in rows.items():
        td = q.registry.get(tid)
        assert td is not None
        assert td.description and td.input_schema and td.output_schema is not None
        assert td.timeout_s > 0
        # 19 tool chuẩn §2 phải có protocol + verification_method; alias v1 không bắt buộc
        if tid in DIRECTIVE_NAMES.values():
            assert td.protocol, f"{tid} thiếu protocol"
            assert td.verification_method, f"{tid} thiếu verification_method"
        assert td.risk_level is not None
        # approval requirement & execution log & verification nằm ở RiskLevel>=R3
        if td.risk_level.value >= 3:
            assert td.requires_owner_approval and td.side_effects


def test_operational_honesty(tmp_path) -> None:
    """§2: không được khai báo Operational nếu chưa chạy thử thành công."""
    q = make_qpig(tmp_path)
    cat = q.catalog_summary()
    # 10 operational = 4 tool Phase 1 chạy thật (LAN 9 thiết bị) + 6 alias v1
    # đã chạy thử sprint UAIIF-S4; 15 tool chuẩn còn lại khai thẳng thắn chưa E2E
    assert cat["operational"] == 10
    assert cat["not_operational"] == 15
    rows = {r["tool_id"]: r for r in q.registered_tools()}
    assert rows["qpig_device_discovery"]["operational"] is True
    assert rows["qpig_agent_task_dispatch"]["operational"] is False


def test_engine_refuses_without_approval(tmp_path) -> None:
    """§4: engine dừng ở CHECK_APPROVAL — KHÔNG execute, KHÔNG evidence."""
    q = make_qpig(tmp_path)
    eng = ActionExecutionEngine(q)
    o = eng.run(ActionRequest(target="agent-x", action="AGENT_SERVICE_CONTROL",
                              params={"action": "SUSPEND", "target": "agent-x"}))
    assert not o.executed
    assert "CHECK_APPROVAL" in o.steps and "EXECUTE" not in o.steps
    assert o.evidence_id is None
    assert "KHÔNG thực thi" in o.reason


def test_engine_executes_with_approval_and_logs_evidence(tmp_path) -> None:
    """§4+§7: đủ approval → execute → verify → evidence → report; token 1-lần."""
    class FakeEngine:
        def execute(self, action, target, *, by="", preapproved=False):
            class R:
                success = True; executed = True
                reason = "ok"
                def to_dict(self): return {"action": action, "target": target}
            return R()

    ap = FakeApprovalService(valid_ids={"ap-001"})
    q = make_qpig(tmp_path, approval_service=ap, containment=FakeEngine())
    eng = ActionExecutionEngine(q)
    o = eng.run(ActionRequest(target="agent-x", action="AGENT_SERVICE_CONTROL",
                              params={"action": "SUSPEND", "target": "agent-x"},
                              approval_id="ap-001"))
    assert o.executed and o.evidence_id is not None
    assert o.steps[-1] == "REPORT" and "EXECUTE" in o.steps
    # §7: đối chiếu độc lập qua ACTION_VERIFICATION
    v = q.call("qpig_action_verification", {"evidence_id": o.evidence_id})
    assert v["success"] and v["data"]["kind"] == "qpig_action"
    # §6: token đã consume — tái sử dụng phải bị refuse
    o2 = eng.run(ActionRequest(target="agent-x", action="AGENT_SERVICE_CONTROL",
                               params={"action": "SUSPEND", "target": "agent-x"},
                               approval_id="ap-001"))
    assert not o2.executed and "EXECUTE" not in o2.steps


def test_token_bound_to_one_tool(tmp_path) -> None:
    """§6: token dùng cho tool khác phải bị từ chối (gắn action_fingerprint)."""
    class FakeEngine:
        def execute(self, action, target, *, by="", preapproved=False):
            class R:
                success = True; executed = True; reason = ""
                def to_dict(self): return {}
            return R()

    ap = FakeApprovalService(valid_ids={"ap-777"})
    q = make_qpig(tmp_path, approval_service=ap, containment=FakeEngine())
    # ap-777 đã consume cho SERVICE_CONTROL
    assert q.call("qpig_agent_service_control",
                  {"action": "RESTART", "target": "a1", "approval_id": "ap-777"})["success"]
    # dùng lại cho RECOVERY → refuse
    r = q.call("qpig_agent_recovery",
               {"action": "RESTART", "target": "a1", "approval_id": "ap-777"})
    assert r["success"] is False and "approval" in r["reason"].lower()


def test_isolation_request_creates_approval_not_action(tmp_path) -> None:
    """§8: AGENT_ISOLATION_REQUEST chỉ tạo yêu cầu chờ duyệt — không tự cô lập."""
    created = {}

    class FakeCards:
        def create_card(self, **kw):
            created.update(kw)

            class C:
                approval_id = "card-iso-1"
            return C()

    q = make_qpig(tmp_path, approval_service=FakeCards())
    r = q.call("qpig_agent_isolation_request", {"target": "rogue-agent"})
    assert r["success"] and r["data"]["state"] == "PENDING_OWNER_APPROVAL"
    assert created["task_id"].startswith("qpig_isolation:")


def test_device_control_refuses_unverified_pi5(tmp_path) -> None:
    """§2+§4: Pi5 thật chưa có kênh đã xác minh → refuse, không giả lập API."""
    q = make_qpig(tmp_path, approval_service=FakeApprovalService(valid_ids={"ap-9"}))
    r = q.call("qpig_device_control",
               {"target": "light-1", "command": "on", "approval_id": "ap-9"})
    assert r["success"] is False
    assert "chưa xác minh" in r["reason"]


def test_adapters_sandbox_and_grants() -> None:
    """§3: adapter validate schema payload + grant giới hạn channel/byte."""
    g = AdapterGrant(channels=frozenset({"api-1"}), max_payload_bytes=64)
    a = HTTPAdapter(transport=lambda p: {"ok": True}, grant=g)
    assert ADAPTER_REGISTRY and len(ADAPTER_REGISTRY) == 7
    assert PENDING_PROTOCOLS  # giao thức chưa adapter — khai thẳng thắn
    ok = a.send("api-1", {"x": 1})
    assert ok["sent"] is True
    refused = a.send("api-2", {"x": 1})           # ngoài grant
    assert refused["sent"] is False
    big = a.send("api-1", {"blob": "y" * 200})    # vượt byte
    assert big["sent"] is False and "byte" in big["reason"]


def test_honest_tool_failures(tmp_path) -> None:
    q = make_qpig(tmp_path)
    # kênh lạ refuse
    r = q.call("qpig_agent_communication", {"channel": "ghost", "payload": {}})
    assert r["success"] is False
    # task dispatch chưa có kênh xác minh → refuse
    r = q.call("qpig_agent_task_dispatch", {"channel": "x", "task_id": "t1"})
    assert r["success"] is False
    # permission control thiếu approval → refuse
    r = q.call("qpig_agent_permission_control",
               {"agent_id": "a", "change": {"status": "SUSPENDED"}})
    assert r["success"] is False and "KHÔNG đổi quyền" in r["reason"]
    # rollback thiếu store + approval → refuse
    r = q.call("qpig_rollback_execution", {"rc_id": "rc-1", "approval_id": "nope"})
    assert r["success"] is False
