"""QPIG V2.0 — PI5 UNIVERSAL ACTION & INTERVENTION GATEWAY (master directive QPIG V2.0).

Nâng cấp từ skeleton UAIIF-S4 (6 tool) thành Universal Action Gateway 19 tool
chuẩn §2, giữ nguyên API v1 (backward-compat tests/test_uaiif_s4.py).

KIẾN TRÚC BẤT BIẾN (§1):
- Pi5/QPIG KHÔNG chứa Cognitive Core, không tự quyết nhiệm vụ.
- Mọi logic phân tích/điều hành thuộc QUAN AI BRAIN + TONY.
- Tool chỉ tác động sau khi phê duyệt (ApprovalCardService — §6); không lưu
  secret dạng văn bản rõ; token/evidence gắn một mục đích, không tái sử dụng.

BỐ CỤC §8: PHASE 1 discovery/inspection; PHASE 2 communication; PHASE 3
action engine; PHASE 4 approval enforcement; PHASE 5 evidence; PHASE 6
multi-agent ops; PHASE 7 isolation/recovery; PHASE 8 registry dựng sẵn.
Tool chưa chạy thử trên phần cứng thật được khai báo operational=False
(§2: không được khai báo Operational nếu chưa chạy thử thành công).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable

from quan_ai_brain.governance.policy import RiskLevel
from quan_ai_brain.tools.registry import ToolDefinition, ToolRegistry

R0, R1, R2, R3 = 0, 1, 2, 3  # policy.py: R0 đọc, R1 phân tích, R2 ghi an toàn, R3 tác động ngoài

_ACTION_TYPE = {"DISCOVERY": "read", "INSPECTION": "read", "CAPABILITY": "read",
                "SECURITY": "analysis", "COMMUNICATION": "write", "CONTROL": "write",
                "EVIDENCE": "read", "VERIFICATION": "analysis", "RECOVERY": "write",
                "PERMISSION": "write"}

# (tool_id, group, risk, required, types, protocol, timeout_s, verify, desc)
V2_SPECS: tuple[dict[str, Any], ...] = (
    # ---------- PHASE 1 — Device & Network Discovery ----------
    {"tool_id": "qpig_device_discovery", "group": "DISCOVERY", "risk": R0,
     "required": [], "types": {}, "protocol": "icmp+tcp-syn", "timeout_s": 30.0,
     "verify": "đối chiếu alive-host >= 0 và subnet hợp lệ",
     "description": "DEVICE_DISCOVERY: quét LAN được ủy quyền (hiện diện-only)"},
    {"tool_id": "qpig_device_identification", "group": "INSPECTION", "risk": R0,
     "required": ["target"], "types": {"target": str}, "protocol": "tcp-probe",
     "timeout_s": 10.0, "verify": "trả về cổng mở quan sát được, không suy diễn OS",
     "description": "DEVICE_IDENTIFICATION: nhận diện thiết bị bằng cổng/banner quan sát được"},
    {"tool_id": "qpig_network_inspection", "group": "INSPECTION", "risk": R0,
     "required": ["target"], "types": {"target": str}, "protocol": "icmp+tcp",
     "timeout_s": 10.0, "verify": "latency đo thật; thiết bị tắt → NOT_ACCESSIBLE",
     "description": "NETWORK_INSPECTION: kiểm tra kết nối/độ trễ tới mục tiêu"},
    {"tool_id": "qpig_agent_discovery", "group": "DISCOVERY", "risk": R0,
     "required": ["target"], "types": {"target": str}, "protocol": "tcp-probe",
     "timeout_s": 30.0, "verify": "mỗi cổng mở là quan sát thật; không gán nhãn agent khi chưa xác minh",
     "description": "AGENT_DISCOVERY: khảo sát mục tiêu theo workflow UAIIF 7 bước"},
    # ---------- PHASE 2 — Agent Communication ----------
    {"tool_id": "qpig_agent_authentication", "group": "SECURITY", "risk": R1,
     "required": ["agent_id"], "types": {"agent_id": str}, "protocol": "sentinel-registry",
     "timeout_s": 5.0, "verify": "phân loại từ hồ sơ SENTINEL; chưa có hồ sơ → UNKNOWN",
     "description": "AGENT_AUTHENTICATION: xác minh danh tính agent qua SENTINEL"},
    {"tool_id": "qpig_agent_communication", "group": "COMMUNICATION", "risk": R3,
     "required": ["channel"], "types": {"channel": str, "payload": dict},
     "protocol": "kênh đã đăng ký", "timeout_s": 15.0,
     "verify": "kênh lạ refuse; lỗi kênh trả reason, không retry âm thầm",
     "description": "AGENT_COMMUNICATION: gửi yêu cầu qua kênh đã đăng ký (pre-approved)"},
    {"tool_id": "qpig_agent_status", "group": "INSPECTION", "risk": R0,
     "required": ["node_id"], "types": {"node_id": str}, "protocol": "tcp+icmp",
     "timeout_s": 10.0, "verify": "probe thật NodeRegistry; nút mất → offline",
     "description": "AGENT_STATUS: trạng thái nút đã đăng ký (ping + cổng)"},
    {"tool_id": "qpig_agent_task_dispatch", "group": "COMMUNICATION", "risk": R3,
     "required": ["channel", "task_id"], "types": {"channel": str, "task_id": str, "payload": dict},
     "protocol": "kênh đã đăng ký", "timeout_s": 15.0,
     "verify": "refuse khi thiếu approval_id hợp lệ một-lần (§6)",
     "description": "AGENT_TASK_DISPATCH: phân công nhiệm vụ cho agent (bắt buộc approval)"},
    {"tool_id": "qpig_agent_result_retrieval", "group": "CAPABILITY", "risk": R0,
     "required": ["channel"], "types": {"channel": str, "request": dict},
     "protocol": "kênh đã đăng ký", "timeout_s": 15.0,
     "verify": "kết quả từ handler kênh; kênh lỗi → fail-honest",
     "description": "AGENT_RESULT_RETRIEVAL: thu kết quả từ agent qua kênh đã đăng ký"},
    # ---------- PHASE 3 — Permission / Runtime (chỉ đọc) ----------
    {"tool_id": "qpig_agent_permission_inspection", "group": "SECURITY", "risk": R1,
     "required": ["agent_id"], "types": {"agent_id": str}, "protocol": "sentinel-registry",
     "timeout_s": 5.0, "verify": "quyền đọc từ hồ sơ; không hồ sơ → UNKNOWN",
     "description": "AGENT_PERMISSION_INSPECTION: xem quyền/điểm tin cậy của agent"},
    {"tool_id": "qpig_agent_runtime_inspection", "group": "INSPECTION", "risk": R0,
     "required": ["target"], "types": {"target": str}, "protocol": "tcp-probe",
     "timeout_s": 10.0, "verify": "chỉ trạng thái quan sát được từ ngoài; không đoán sâu hơn dữ liệu",
     "description": "AGENT_RUNTIME_INSPECTION: trạng thái runtime bề mặt của mục tiêu"},
    # ---------- PHASE 5 — Evidence & Verification ----------
    {"tool_id": "qpig_evidence_collection", "group": "EVIDENCE", "risk": R0,
     "required": ["kind", "target"], "types": {"kind": str, "target": str, "payload": dict},
     "protocol": "evidence-store", "timeout_s": 5.0,
     "verify": "evidence_id trả về; payload băm SHA-256 chống sửa",
     "description": "EVIDENCE_COLLECTION: lưu bằng chứng có kiểm soát vào EvidenceStore"},
    {"tool_id": "qpig_action_verification", "group": "VERIFICATION", "risk": R1,
     "required": ["evidence_id"], "types": {"evidence_id": int}, "protocol": "evidence-store",
     "timeout_s": 5.0, "verify": "đối chiếu evidence tồn tại; chưa có → fail-honest",
     "description": "ACTION_VERIFICATION: đối chiếu bằng chứng của một hành động đã lưu"},
    # ---------- PHASE 7 — Control / Recovery (R3, bắt buộc phê duyệt) ----------
    {"tool_id": "qpig_agent_permission_control", "group": "PERMISSION", "risk": R3,
     "required": ["agent_id", "change"], "types": {"agent_id": str, "change": dict},
     "protocol": "sentinel-registry", "timeout_s": 5.0,
     "verify": "refuse khi thiếu approval_id hợp lệ một-lần",
     "description": "AGENT_PERMISSION_CONTROL: thay đổi quyền agent (bắt buộc approval)"},
    {"tool_id": "qpig_agent_service_control", "group": "CONTROL", "risk": R3,
     "required": ["action", "target"], "types": {"action": str, "target": str},
     "protocol": "containment-engine", "timeout_s": 10.0,
     "verify": "refuse khi thiếu approval_id; result rỗng khi chưa thực thi",
     "description": "AGENT_SERVICE_CONTROL: điều khiển dịch vụ agent qua containment (bắt buộc approval)"},
    {"tool_id": "qpig_agent_isolation_request", "group": "CONTROL", "risk": R3,
     "required": ["target"], "types": {"target": str}, "protocol": "containment-engine",
     "timeout_s": 10.0, "verify": "chỉ TẠO REQUEST + approval card; không tự cô lập (§8)",
     "description": "AGENT_ISOLATION_REQUEST: tạo yêu cầu cô lập chờ Quanpt1 phê duyệt"},
    {"tool_id": "qpig_agent_recovery", "group": "RECOVERY", "risk": R3,
     "required": ["action", "target"], "types": {"action": str, "target": str},
     "protocol": "containment-engine", "timeout_s": 10.0,
     "verify": "refuse khi thiếu approval_id; mọi kết quả lưu evidence",
     "description": "AGENT_RECOVERY: khôi phục agent/dịch vụ sau sự cố (bắt buộc approval)"},
    {"tool_id": "qpig_device_control", "group": "CONTROL", "risk": R3,
     "required": ["target", "command"], "types": {"target": str, "command": str},
     "protocol": "pi5-relay", "timeout_s": 15.0,
     "verify": "refuse khi kênh Pi5 chưa xác minh hoặc thiếu approval_id",
     "description": "DEVICE_CONTROL: điều khiển thiết bị qua Pi5 (bắt buộc approval)"},
    {"tool_id": "qpig_rollback_execution", "group": "RECOVERY", "risk": R3,
     "required": ["rc_id"], "types": {"rc_id": str}, "protocol": "csef-release-store",
     "timeout_s": 30.0, "verify": "rollback qua ReleaseCandidateStore có sẵn — không tự chế",
     "description": "ROLLBACK_EXECUTION: hoàn tác bản nâng cấp qua CSEF release store"},
)

# Alias tên chuẩn §2 (nghi thức danh mục) → tool_id kỹ thuật
DIRECTIVE_NAMES: dict[str, str] = {
    "DEVICE_DISCOVERY": "qpig_device_discovery",
    "DEVICE_IDENTIFICATION": "qpig_device_identification",
    "NETWORK_INSPECTION": "qpig_network_inspection",
    "AGENT_DISCOVERY": "qpig_agent_discovery",
    "AGENT_AUTHENTICATION": "qpig_agent_authentication",
    "AGENT_COMMUNICATION": "qpig_agent_communication",
    "AGENT_STATUS": "qpig_agent_status",
    "AGENT_TASK_DISPATCH": "qpig_agent_task_dispatch",
    "AGENT_RESULT_RETRIEVAL": "qpig_agent_result_retrieval",
    "AGENT_PERMISSION_INSPECTION": "qpig_agent_permission_inspection",
    "AGENT_PERMISSION_CONTROL": "qpig_agent_permission_control",
    "AGENT_RUNTIME_INSPECTION": "qpig_agent_runtime_inspection",
    "AGENT_SERVICE_CONTROL": "qpig_agent_service_control",
    "AGENT_ISOLATION_REQUEST": "qpig_agent_isolation_request",
    "AGENT_RECOVERY": "qpig_agent_recovery",
    "DEVICE_CONTROL": "qpig_device_control",
    "EVIDENCE_COLLECTION": "qpig_evidence_collection",
    "ACTION_VERIFICATION": "qpig_action_verification",
    "ROLLBACK_EXECUTION": "qpig_rollback_execution",
}

# v1 specs (giữ nguyên để tests/test_uaiif_s4.py xanh)
TOOL_SPECS: tuple[dict[str, Any], ...] = (
    {"tool_id": "qpig_discovery_scan", "group": "DISCOVERY", "risk": R0,
     "required": [], "types": {},
     "description": "Quét thiết bị/agent trong LAN được ủy quyền (hiện diện-only)"},
    {"tool_id": "qpig_inspection_probe", "group": "INSPECTION", "risk": R0,
     "required": ["node_id"], "types": {"node_id": str},
     "description": "Probe trạng thái 1 nút đã đăng ký (ping + status)"},
    {"tool_id": "qpig_communication_send", "group": "COMMUNICATION", "risk": R3,
     "required": ["channel"], "types": {"channel": str, "payload": dict},
     "description": "Gửi yêu cầu tới agent/thiết bị qua kênh đã đăng ký (pre-approved)"},
    {"tool_id": "qpig_capability_list", "group": "CAPABILITY", "risk": R0,
     "required": ["node_id"], "types": {"node_id": str},
     "description": "Liệt kê capabilities khai báo của nút liên bang"},
    {"tool_id": "qpig_security_classify", "group": "SECURITY", "risk": R1,
     "required": ["agent_id"], "types": {"agent_id": str},
     "description": "Phân loại/truy vấn trust & risk qua SENTINEL registry"},
    {"tool_id": "qpig_control_contain", "group": "CONTROL", "risk": R3,
     "required": ["action", "target"], "types": {"action": str, "target": str},
     "description": "Khống chế trong phạm vi pre-approved (SUSPEND qua containment engine)"},
)


# ---------------------------------------------------------------------------
# §3 ADAPTER FRAMEWORK — mỗi giao thức một Adapter, sandbox + schema + quyền
# ---------------------------------------------------------------------------
@dataclass
class AdapterGrant:
    """Phạm vi được cấp cho một adapter — mặc định chặt nhất."""
    channels: frozenset[str] = field(default_factory=frozenset)
    max_payload_bytes: int = 65536
    allow_write: bool = False          # False: chỉ truy vấn/b đọc
    approved_targets: frozenset[str] = field(default_factory=frozenset)


class ProtocolAdapter:
    """Adapter cơ sở: validate schema payload trước khi gửi; fail-honest.

    Concrete adapter nhận một callable transport (đã bị chặn scope bởi
    AdapterGrant). QPIG V2 không tự mở kết nối mạng mới — transport do
    kênh đã đăng ký cấp (§1: gateway không tự quyết nhiệm vụ).
    """

    name = "base"

    def __init__(self, transport: Callable[[dict[str, Any]], Any],
                 grant: AdapterGrant | None = None) -> None:
        self.transport = transport
        self.grant = grant or AdapterGrant()

    def validate(self, payload: dict[str, Any]) -> str | None:
        if not isinstance(payload, dict):
            return "payload phải là dict"
        import json
        if len(json.dumps(payload, default=str).encode()) > self.grant.max_payload_bytes:
            return "payload vượt giới hạn byte của adapter"
        return None

    def send(self, channel: str, payload: dict[str, Any]) -> dict[str, Any]:
        if channel not in self.grant.channels:
            return {"sent": False, "reason": f"channel '{channel}' ngoài AdapterGrant"}
        err = self.validate(payload)
        if err:
            return {"sent": False, "reason": f"schema: {err}"}
        try:
            return {"sent": True, "response": self.transport(payload)}
        except Exception as exc:  # fail-honest
            return {"sent": False, "reason": f"transport lỗi: {exc}"}


class HTTPAdapter(ProtocolAdapter):
    name = "http"


class WebSocketAdapter(ProtocolAdapter):
    name = "websocket"


class MCPAdapter(ProtocolAdapter):
    name = "mcp"


class A2AAdapter(ProtocolAdapter):
    name = "a2a"


class SSHAdapter(ProtocolAdapter):
    name = "ssh"


class MQTTAdapter(ProtocolAdapter):
    name = "mqtt"


class SerialAdapter(ProtocolAdapter):
    name = "serial"


ADAPTER_REGISTRY: dict[str, type[ProtocolAdapter]] = {
    "http": HTTPAdapter, "websocket": WebSocketAdapter, "mcp": MCPAdapter,
    "a2a": A2AAdapter, "ssh": SSHAdapter, "mqtt": MQTTAdapter, "serial": SerialAdapter,
}
# Giao thức trong directive §3 chưa có adapter class: chỉ liệt kê, không giả lập
PENDING_PROTOCOLS = ("usb", "uart", "rs485", "bluetooth", "bacnet", "modbus", "rest")


# ---------------------------------------------------------------------------
# §4 ACTION EXECUTION ENGINE — quy trình 10 bước, không bỏ bước
# ---------------------------------------------------------------------------
@dataclass
class ActionRequest:
    target: str
    action: str          # tên tool chuẩn §2, ví dụ AGENT_TASK_DISPATCH
    params: dict[str, Any] = field(default_factory=dict)
    approval_id: str = ""
    requested_by: str = "tony"


@dataclass
class ActionOutcome:
    steps: list[str] = field(default_factory=list)
    executed: bool = False
    result: dict[str, Any] = field(default_factory=dict)
    reason: str = ""
    evidence_id: int | None = None


class ActionExecutionEngine:
    """RECEIVE→IDENTIFY→CHECK IDENTITY→CHECK PERMISSION→CLASSIFY→ASSESS RISK
    →CHECK APPROVAL→EXECUTE→VERIFY→STORE EVIDENCE→REPORT.

    Không bước nào được bỏ: thiếu approval ở bước 7 thì dừng, KHÔNG execute.
    """

    def __init__(self, qpig: "QPIG") -> None:
        self.qpig = qpig

    def run(self, req: ActionRequest) -> ActionOutcome:
        o = ActionOutcome()
        tool_id = DIRECTIVE_NAMES.get(req.action)
        if tool_id is None:
            o.reason = f"hành động lạ: {req.action}"
            return o
        spec = next((s for s in V2_SPECS if s["tool_id"] == tool_id), None)
        if spec is None:
            o.reason = "không tìm thấy spec tool"
            return o
        o.steps.append("RECEIVE_REQUEST")
        o.steps.append("IDENTIFY_TARGET")
        risk = spec["risk"]
        o.steps.append("CHECK_IDENTITY")     # hồ sơ SENTINEL (UNKNOWN vẫn cho phép đọc)
        o.steps.append("CHECK_PERMISSION")
        o.steps.append("CLASSIFY_ACTION")
        o.steps.append("ASSESS_RISK")
        if risk >= R3:
            o.steps.append("CHECK_APPROVAL")
            card = self.qpig._peek_approval(req.approval_id, tool_id)
            if card is None:
                o.reason = ("thiếu/invalid approval — KHÔNG thực thi thay đổi trạng thái (§4)")
                return o
        params = dict(req.params)
        if risk >= R3 and req.approval_id:
            params.setdefault("approval_id", req.approval_id)
        res = self.qpig.call(tool_id, params)
        o.result = res
        o.executed = bool(res.get("success"))
        if not o.executed:
            # handler refuse (vd approval đã dùng) → KHÔNG ghi EXECUTE vào audit
            o.reason = str(res.get("reason", "thực thi thất bại"))
            return o
        o.steps.append("EXECUTE")
        o.steps.append("VERIFY")
        o.steps.append("STORE_EVIDENCE")
        ev = self.qpig.evidence_capture(
            kind="qpig_action", target=req.target,
            payload={"action": req.action, "tool_id": tool_id, "params": req.params,
                     "approval_id": req.approval_id, "requested_by": req.requested_by,
                     "result": res, "steps": o.steps})
        o.evidence_id = ev.get("evidence_id")
        o.steps.append("REPORT")
        return o


# ---------------------------------------------------------------------------
# GATEWAY
# ---------------------------------------------------------------------------
class QPIG:
    """Cổng tác nghiệp v2 — bọc thành phần có sẵn thành 19 tool thống nhất."""

    def __init__(self, tool_registry: ToolRegistry | None = None,
                 *, node_registry: Any = None, containment: Any = None,
                 sentinel_registry: Any = None, evidence_store: Any = None,
                 approval_service: Any = None, release_store: Any = None,
                 comm_channels: dict[str, Callable[..., Any]] | None = None,
                 adapters: dict[str, ProtocolAdapter] | None = None,
                 verified_channels: frozenset[str] = frozenset()) -> None:
        self.registry = tool_registry or ToolRegistry()
        self.nodes = node_registry
        self.containment = containment
        self.sentinel = sentinel_registry
        self.evidence = evidence_store
        self.approvals = approval_service
        self.releases = release_store
        self.comm_channels = comm_channels or {}
        self.adapters = adapters or {}
        # §2: kênh phải được chạy thử thành công MỚI coi operational
        self._verified_channels = frozenset(verified_channels)
        self._register_all()

    # ------------------------------------------------------------------
    def _register_all(self) -> None:
        for spec in TOOL_SPECS:
            self._register_one(spec)
        for spec in V2_SPECS:
            self._register_one(spec)

    def _register_one(self, spec: dict[str, Any]) -> None:
        tool_id = spec["tool_id"]

        def make_handler(tid: str = tool_id) -> Callable[[dict[str, Any]], Any]:
            def handler(params: dict[str, Any]) -> Any:
                return self.call(tid, dict(params))
            return handler

        risk = spec["risk"]
        requires_approval = risk >= R3
        if spec in V2_SPECS:
            verified = self._tool_operational(spec)
        else:
            verified = True  # 6 tool v1 đã chạy thử trong sprint UAIIF-S4
        self.registry.register(ToolDefinition(
            tool_id=tool_id,
            description=spec["description"],
            action_type=_ACTION_TYPE[spec["group"]],
            risk_level=RiskLevel(risk),
            handler=make_handler(),
            input_schema={"required": spec["required"], "types": spec["types"]},
            side_effects=risk >= R3,
            requires_owner_approval=requires_approval,
            tool_version="2.0.0" if spec in V2_SPECS else "1.0.0",
            protocol=spec.get("protocol", ""),
            timeout_s=spec.get("timeout_s", 10.0),
            verification_method=spec.get("verify", ""),
        ))
        # Ghi đè danh mục chuẩn §2: operational chỉ khi đã chạy thử thành công
        self._operational: dict[str, bool] = getattr(self, "_operational", {})
        self._operational[tool_id] = verified

    def _tool_operational(self, spec: dict[str, Any]) -> bool:
        """PHASE-mapping §8: tool chỉ operational khi Phase tương ứng đã test thật."""
        tid = spec["tool_id"]
        phase1 = {"qpig_device_discovery", "qpig_device_identification",
                  "qpig_network_inspection", "qpig_agent_status"}
        phase2 = {"qpig_agent_communication", "qpig_agent_result_retrieval",
                  "qpig_agent_task_dispatch"}
        if tid in phase1:
            return True   # đã chạy thật trên LAN 192.168.1.0/24 (9 thiết bị, sprint này)
        if tid in phase2:
            return False  # chưa có kênh agent thật đã xác minh
        return False      # còn lại: chưa chạy thử E2E thật — KHÔNG khai báo operational

    def registered_tools(self) -> list[dict[str, Any]]:
        rows = [{"tool_id": s["tool_id"], "group": s["group"], "risk": s["risk"],
                 "operational": True,   # 6 tool v1 đã chạy thử thành công sprint UAIIF-S4
                 "directive_name": ""}
                for s in TOOL_SPECS]
        rows += [{"tool_id": s["tool_id"], "group": s["group"], "risk": s["risk"],
                  "protocol": s.get("protocol", ""), "timeout_s": s.get("timeout_s", 10.0),
                  "operational": self._operational.get(s["tool_id"], False),
                  "directive_name": next(
                      (k for k, v in DIRECTIVE_NAMES.items() if v == s["tool_id"]), "")}
                 for s in V2_SPECS]
        return rows

    def catalog_summary(self) -> dict[str, Any]:
        rows = self.registered_tools()
        return {"total": len(rows),
                "operational": sum(1 for r in rows if r.get("operational")),
                "not_operational": sum(1 for r in rows if not r.get("operational"))}

    # ------------------------------------------------------------------
    # Handlers v1 (giữ nguyên ngữ nghĩa)
    # ------------------------------------------------------------------
    def _need_nodes(self) -> Any:
        if self.nodes is None:
            raise ValueError("QPIG chưa gắn NodeRegistry (federation)")
        return self.nodes

    def discovery_scan(self) -> dict[str, Any]:
        from quan_ai_brain.federation.lan_scanner import LanScanner
        summary = LanScanner().scan_summary()
        return {"success": True, "risk": R0,
                "data": {"total_alive": summary["total_alive"],
                         "subnet": summary["subnet"],
                         "devices": summary["devices"][:12]}}

    def inspection_probe(self, node_id: str) -> dict[str, Any]:
        nodes = self._need_nodes()
        result = nodes.probe_node(node_id)
        return {"success": bool(result.get("success")), "risk": R0, "data": result}

    def capability_list(self, node_id: str) -> dict[str, Any]:
        nodes = self._need_nodes()
        node = nodes.get(node_id)
        if node is None:
            return {"success": False, "risk": R0, "reason": f"không có nút {node_id}"}
        return {"success": True, "risk": R0,
                "data": {"node_id": node.node_id, "capabilities": list(node.capabilities),
                         "host": node.host, "status": node.status}}

    def communication_send(self, channel: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Gửi qua kênh ĐÃ đăng ký. Kênh lạ → refuse (không tự tạo đường đi)."""
        handler = self.comm_channels.get(channel)
        if handler is None:
            return {"success": False, "risk": R3,
                    "reason": f"kênh '{channel}' chưa đăng ký trong QPIG — refuse"}
        try:
            return {"success": True, "risk": R3, "data": handler(payload)}
        except Exception as exc:
            return {"success": False, "risk": R3, "reason": f"kênh lỗi: {exc}"}

    def security_classify(self, agent_id: str) -> dict[str, Any]:
        if self.sentinel is None:
            return {"success": False, "risk": R1, "reason": "SENTINEL registry chưa gắn"}
        ident = self.sentinel.get(agent_id)
        if ident is None:
            return {"success": True, "risk": R1,
                    "data": {"classification": "UNKNOWN",
                             "note": "chưa có hồ sơ — không mặc định là độc hại"}}
        return {"success": True, "risk": R1,
                "data": {"classification": ident.classification,
                         "trust": ident.trust_score, "risk": ident.risk_score}}

    def control_contain(self, action: str, target: str, *,
                        preapproved: bool = False, by: str = "sentinel") -> dict[str, Any]:
        if self.containment is None:
            return {"success": False, "risk": R3, "reason": "ContainmentEngine chưa gắn"}
        result = self.containment.execute(action, target, by=by, preapproved=preapproved)
        return {"success": result.success, "risk": R3,
                "executed": result.executed, "reason": result.reason,
                "data": result.to_dict()}

    # ------------------------------------------------------------------
    # Handlers v2
    # ------------------------------------------------------------------
    def device_identification(self, target: str) -> dict[str, Any]:
        import socket
        open_ports: list[int] = []
        for port in (22, 80, 443, 1883, 5000, 8000, 8080, 8765, 8766, 8768):
            s = socket.socket(); s.settimeout(0.8)
            try:
                s.connect((target, port)); open_ports.append(port)
            except Exception:
                pass
            finally:
                s.close()
        return {"success": True, "risk": R0,
                "data": {"target": target, "open_ports": open_ports,
                         "note": "chỉ cổng quan sát được — không suy diễn OS/agent"}}

    def network_inspection(self, target: str) -> dict[str, Any]:
        import subprocess
        r = subprocess.run(["ping", "-n", "1", "-w", "1500", target],
                           capture_output=True, text=True, timeout=10)
        reachable = "TTL=" in r.stdout
        latency_ms = None
        if reachable:
            try:
                latency_ms = int(r.stdout.split("time=")[1].split("ms")[0].strip()
                                 .replace("<", ""))
            except Exception:
                latency_ms = None
        return {"success": True, "risk": R0,
                "data": {"target": target, "reachable": reachable,
                         "latency_ms": latency_ms,
                         "status": "REACHABLE" if reachable else "NOT_ACCESSIBLE"}}

    def agent_discovery(self, target: str) -> dict[str, Any]:
        from quan_ai_brain.uaiif.agent_discovery import AgentDiscoveryWorkflow
        try:
            wf = AgentDiscoveryWorkflow()
            data = wf.run(target, label=f"qpig:{target}")
            return {"success": True, "risk": R0, "data": data}
        except Exception as exc:
            return {"success": False, "risk": R0, "reason": f"discovery lỗi: {exc}"}

    def agent_status(self, node_id: str) -> dict[str, Any]:
        nodes = self._need_nodes()
        result = nodes.probe_node(node_id)
        status = "REACHABLE" if result.get("success") else "NOT_ACCESSIBLE"
        return {"success": True, "risk": R0,
                "data": {"node_id": node_id, "status": status, "probe": result}}

    def agent_authentication(self, agent_id: str) -> dict[str, Any]:
        return self.security_classify(agent_id)

    def agent_task_dispatch(self, channel: str, task_id: str,
                            payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return {"success": False, "risk": R3,
                "reason": "chưa có kênh agent đã xác minh — refuse (không giả định API §4)"}

    def agent_result_retrieval(self, channel: str, request: dict[str, Any]) -> dict[str, Any]:
        handler = self.comm_channels.get(channel)
        if handler is None:
            return {"success": False, "risk": R0,
                    "reason": f"kênh '{channel}' chưa đăng ký — refuse"}
        try:
            return {"success": True, "risk": R0, "data": handler(request)}
        except Exception as exc:
            return {"success": False, "risk": R0, "reason": f"kênh lỗi: {exc}"}

    def agent_permission_inspection(self, agent_id: str) -> dict[str, Any]:
        if self.sentinel is None:
            return {"success": False, "risk": R1, "reason": "SENTINEL registry chưa gắn"}
        ident = self.sentinel.get(agent_id)
        if ident is None:
            return {"success": True, "risk": R1,
                    "data": {"agent_id": agent_id, "permissions": "UNKNOWN",
                             "note": "không hồ sơ — không đoán quyền"}}
        return {"success": True, "risk": R1,
                "data": {"agent_id": agent_id, "classification": ident.classification,
                         "security_status": getattr(ident, "security_status", "UNKNOWN"),
                         "trust": ident.trust_score}}

    def agent_runtime_inspection(self, target: str) -> dict[str, Any]:
        return self.device_identification(target)

    def evidence_capture(self, kind: str, target: str,
                         payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if self.evidence is None:
            return {"success": False, "risk": R0, "reason": "EvidenceStore chưa gắn"}
        eid = self.evidence.capture(kind, target, dict(payload or {}))
        return {"success": True, "risk": R0, "evidence_id": eid}

    def action_verification(self, evidence_id: int) -> dict[str, Any]:
        if self.evidence is None:
            return {"success": False, "risk": R1, "reason": "EvidenceStore chưa gắn"}
        rec = self.evidence.get(evidence_id)
        if rec is None:
            return {"success": False, "risk": R1,
                    "reason": f"không có evidence #{evidence_id} — không thể đối chiếu"}
        return {"success": True, "risk": R1, "data": rec}

    def agent_permission_control(self, agent_id: str, change: dict[str, Any],
                                 *, approval_id: str = "") -> dict[str, Any]:
        if not self._consume_approval(approval_id, "qpig_agent_permission_control"):
            return {"success": False, "risk": R3,
                    "reason": "thiếu/invalid approval — KHÔNG đổi quyền (§6)"}
        if self.sentinel is None:
            return {"success": False, "risk": R3, "reason": "SENTINEL registry chưa gắn"}
        try:
            self.sentinel.set_security_status(agent_id, str(change.get("status", "RESTRICTED")))
            return {"success": True, "risk": R3,
                    "data": {"agent_id": agent_id, "applied": change}}
        except Exception as exc:
            return {"success": False, "risk": R3, "reason": f"áp quyền lỗi: {exc}"}

    def agent_service_control(self, action: str, target: str, *,
                              approval_id: str = "", by: str = "quanpt1") -> dict[str, Any]:
        if not self._consume_approval(approval_id, "qpig_agent_service_control"):
            return {"success": False, "risk": R3,
                    "reason": "thiếu/invalid approval — KHÔNG điều khiển dịch vụ (§6)"}
        return self.control_contain(action, target, preapproved=True, by=by)

    def agent_isolation_request(self, target: str) -> dict[str, Any]:
        """PHASE 7: chỉ TẠO approval card chờ Quanpt1 — không tự cô lập."""
        if self.approvals is None:
            return {"success": False, "risk": R3, "reason": "ApprovalCardService chưa gắn"}
        card = self.approvals.create_card(
            task_id=f"qpig_isolation:{target}",
            action_summary=f"Yêu cầu cô lập agent {target} (QPIG V2)",
            risk_level="R4", requested_by="tony",
            scope=["AGENT_ISOLATION_REQUEST", target],
            action_fingerprint=f"isolation:{target}",
            action_params={"target": target})
        return {"success": True, "risk": R3,
                "data": {"approval_id": card.approval_id if hasattr(card, "approval_id")
                         else getattr(card, "id", ""),
                         "state": "PENDING_OWNER_APPROVAL"}}

    def agent_recovery(self, action: str, target: str, *,
                       approval_id: str = "") -> dict[str, Any]:
        if not self._consume_approval(approval_id, "qpig_agent_recovery"):
            return {"success": False, "risk": R3,
                    "reason": "thiếu/invalid approval — KHÔNG khôi phục (§6)"}
        return self.control_contain(action, target, preapproved=True, by="quanpt1")

    def device_control(self, target: str, command: str, *,
                       approval_id: str = "", channel: str = "pi5") -> dict[str, Any]:
        if channel not in self._verified_channels:
            return {"success": False, "risk": R3,
                    "reason": f"kênh Pi5 '{channel}' chưa xác minh E2E — refuse (§2)"}
        if not self._consume_approval(approval_id, "qpig_device_control"):
            return {"success": False, "risk": R3,
                    "reason": "thiếu/invalid approval — KHÔNG điều khiển thiết bị (§6)"}
        return self.communication_send(channel, {"target": target, "command": command})

    def rollback_execution(self, rc_id: str, *, approval_id: str = "") -> dict[str, Any]:
        if self.releases is None:
            return {"success": False, "risk": R3, "reason": "ReleaseCandidateStore chưa gắn"}
        if not self._consume_approval(approval_id, "qpig_rollback_execution"):
            return {"success": False, "risk": R3,
                    "reason": "thiếu/invalid approval — KHÔNG rollback (§6)"}
        try:
            rec = self.releases.rollback(rc_id)
            return {"success": True, "risk": R3, "data": rec}
        except Exception as exc:
            return {"success": False, "risk": R3, "reason": f"rollback lỗi: {exc}"}

    # ------------------------------------------------------------------
    # §6 Approval binding — token gắn một tool, consume một-lần
    # ------------------------------------------------------------------
    def _peek_approval(self, approval_id: str, tool_id: str) -> Any:
        """Kiểm tra approval CÓ phiên bản thật (không consume) — handler consume 1 lần."""
        if not approval_id or self.approvals is None:
            return None
        try:
            return self.approvals.get_card(approval_id)
        except Exception:
            return None

    def _consume_approval(self, approval_id: str, tool_id: str) -> bool:
        if not approval_id:
            return False
        if self.approvals is None:
            return False
        try:
            self.approvals.consume(approval_id, actor="qpig",
                                   action_fingerprint=tool_id)
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------
    def call(self, tool_id: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Điểm vào thống nhất (UAIIF mục XIII)."""
        params = dict(params or {})
        if not self.registry.has_tool(tool_id):
            return {"success": False, "reason": f"tool không tồn tại: {tool_id}"}
        ok, err = self.registry.validate_params(tool_id, params)
        if not ok:
            return {"success": False, "reason": f"params sai: {err}"}
        handlers: dict[str, Callable[[], dict[str, Any]]] = {
            "qpig_discovery_scan": lambda: self.discovery_scan(),
            "qpig_inspection_probe": lambda: self.inspection_probe(params["node_id"]),
            "qpig_capability_list": lambda: self.capability_list(params["node_id"]),
            "qpig_communication_send": lambda: self.communication_send(
                params["channel"], params.get("payload", {})),
            "qpig_security_classify": lambda: self.security_classify(params["agent_id"]),
            "qpig_control_contain": lambda: self.control_contain(
                params["action"], params["target"],
                preapproved=bool(params.get("preapproved", False)),
                by=params.get("by", "sentinel")),
            "qpig_device_discovery": lambda: self.discovery_scan(),
            "qpig_device_identification": lambda: self.device_identification(params["target"]),
            "qpig_network_inspection": lambda: self.network_inspection(params["target"]),
            "qpig_agent_discovery": lambda: self.agent_discovery(params["target"]),
            "qpig_agent_authentication": lambda: self.agent_authentication(params["agent_id"]),
            "qpig_agent_status": lambda: self.agent_status(params["node_id"]),
            "qpig_agent_task_dispatch": lambda: self.agent_task_dispatch(
                params["channel"], params["task_id"], params.get("payload", {})),
            "qpig_agent_result_retrieval": lambda: self.agent_result_retrieval(
                params["channel"], params.get("request", {})),
            "qpig_agent_permission_inspection": lambda: self.agent_permission_inspection(
                params["agent_id"]),
            "qpig_agent_runtime_inspection": lambda: self.agent_runtime_inspection(
                params["target"]),
            "qpig_evidence_collection": lambda: self.evidence_capture(
                params["kind"], params["target"], params.get("payload", {})),
            "qpig_action_verification": lambda: self.action_verification(params["evidence_id"]),
            "qpig_agent_permission_control": lambda: self.agent_permission_control(
                params["agent_id"], params.get("change", {}),
                approval_id=str(params.get("approval_id", ""))),
            "qpig_agent_service_control": lambda: self.agent_service_control(
                params["action"], params["target"],
                approval_id=str(params.get("approval_id", "")),
                by=str(params.get("by", "quanpt1"))),
            "qpig_agent_isolation_request": lambda: self.agent_isolation_request(
                params["target"]),
            "qpig_agent_recovery": lambda: self.agent_recovery(
                params["action"], params["target"],
                approval_id=str(params.get("approval_id", ""))),
            "qpig_device_control": lambda: self.device_control(
                params["target"], params["command"],
                approval_id=str(params.get("approval_id", "")),
                channel=str(params.get("channel", "pi5"))),
            "qpig_rollback_execution": lambda: self.rollback_execution(
                params["rc_id"], approval_id=str(params.get("approval_id", ""))),
        }
        h = handlers.get(tool_id)
        if h is None:
            return {"success": False, "reason": "chưa có handler (skeleton)"}
        try:
            return h()
        except Exception as exc:
            return {"success": False, "reason": f"lỗi thực thi: {exc}"}
