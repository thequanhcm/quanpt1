"""UAIIF-S4 (GĐ1): QPIG — QUAN Physical Interaction Gateway (skeleton).

Master prompt UAIIF v1.0 mục V: Pi5 = Physical Interaction Gateway của TONY.
6 nhóm tool: DISCOVERY / INSPECTION / COMMUNICATION / CAPABILITY / SECURITY /
CONTROL. Đăng ký vào ToolRegistry HIỆN CÓ (tools/registry.py) — không tạo
cơ chế tool mới. Mỗi tool có risk level (R0-R3) theo policy R0-R5 sẵn có.

NGUYÊN TẮC (mục II): Pi5/tool KHÔNG chứa logic quản trị; mất kết nối → tool
trả NOT_ACCESSIBLE fail-honest, TONY vẫn nhận thức bình thường. CONTROL tool
chỉ chạy trong phạm vi đã phê duyệt (pre-approved scope / approval card).
"""
from __future__ import annotations

from typing import Any, Callable

from quan_ai_brain.governance.policy import RiskLevel
from quan_ai_brain.tools.registry import ToolDefinition, ToolRegistry

# Risk levels theo policy.py (R0 đọc, R1 phân tích, R2 ghi an toàn, R3 tác động ngoài thấp)
R0, R1, R2, R3 = 0, 1, 2, 3

_ACTION_TYPE = {"DISCOVERY": "read", "INSPECTION": "read", "CAPABILITY": "read",
                "SECURITY": "analysis", "COMMUNICATION": "write", "CONTROL": "write"}

# CONTROL chỉ pre-approved (hợp đồng auto_contain / approval card) — không tự tung
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


class QPIG:
    """Cổng tương tác vật lý — bọc thành phần có sẵn thành tool thống nhất."""

    def __init__(self, tool_registry: ToolRegistry | None = None,
                 *, node_registry: Any = None, containment: Any = None,
                 sentinel_registry: Any = None,
                 comm_channels: dict[str, Callable[..., Any]] | None = None) -> None:
        self.registry = tool_registry or ToolRegistry()
        self.nodes = node_registry
        self.containment = containment
        self.sentinel = sentinel_registry
        self.comm_channels = comm_channels or {}   # {channel_name: callable}
        self._register_all()

    # ------------------------------------------------------------------
    def _register_all(self) -> None:
        for spec in TOOL_SPECS:
            tool_id = spec["tool_id"]

            def make_handler(tid: str = tool_id) -> Callable[[dict[str, Any]], Any]:
                def handler(params: dict[str, Any]) -> dict[str, Any]:
                    return self.call(tid, dict(params))
                return handler

            self.registry.register(ToolDefinition(
                tool_id=tool_id,
                description=spec["description"],
                action_type=_ACTION_TYPE[spec["group"]],
                risk_level=RiskLevel(spec["risk"]),
                handler=make_handler(),
                input_schema={"required": spec["required"], "types": spec["types"]},
                side_effects=spec["risk"] >= R3,
                requires_owner_approval=spec["risk"] >= R3,
            ))

    def registered_tools(self) -> list[dict[str, Any]]:
        return [{"tool_id": s["tool_id"], "group": s["group"],
                 "risk": s["risk"]} for s in TOOL_SPECS]

    # ------------------------------------------------------------------
    # Handlers — mỗi handler fail-honest, không raise ra ngoài
    # ------------------------------------------------------------------
    def _need_nodes(self) -> Any:
        if self.nodes is None:
            raise ValueError("QPIG chưa gắn NodeRegistry (federation)")
        return self.nodes

    def discovery_scan(self) -> dict[str, Any]:
        from quan_ai_brain.federation.lan_scanner import LanScanner

        scanner = LanScanner()
        summary = scanner.scan_summary()
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
            return {"success": False, "risk": R0,
                    "reason": f"không có nút {node_id}"}
        return {"success": True, "risk": R0,
                "data": {"node_id": node.node_id,
                         "capabilities": list(node.capabilities),
                         "host": node.host, "status": node.status}}

    def communication_send(self, channel: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Gửi qua kênh ĐÃ đăng ký. Kênh lạ → refuse (không tự tạo đường đi)."""
        handler = self.comm_channels.get(channel)
        if handler is None:
            return {"success": False, "risk": R3,
                    "reason": f"kênh '{channel}' chưa đăng ký trong QPIG — refuse"}
        try:
            result = handler(payload)
            return {"success": True, "risk": R3, "data": result}
        except Exception as exc:
            return {"success": False, "risk": R3, "reason": f"kênh lỗi: {exc}"}

    def security_classify(self, agent_id: str) -> dict[str, Any]:
        if self.sentinel is None:
            return {"success": False, "risk": R1,
                    "reason": "SENTINEL registry chưa gắn"}
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
            return {"success": False, "risk": R3,
                    "reason": "ContainmentEngine chưa gắn"}
        result = self.containment.execute(action, target, by=by,
                                          preapproved=preapproved)
        return {"success": result.success, "risk": R3,
                "executed": result.executed, "reason": result.reason,
                "data": result.to_dict()}

    # ------------------------------------------------------------------
    def call(self, tool_id: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Điểm vào thống nhất (master prompt mục XIII: cơ chế giao tiếp thống nhất)."""
        params = dict(params or {})
        if not self.registry.has_tool(tool_id):
            return {"success": False, "reason": f"tool không tồn tại: {tool_id}"}
        ok, err = self.registry.validate_params(tool_id, params)
        if not ok:
            return {"success": False, "reason": f"params sai: {err}"}
        handlers = {
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
        }
        h = handlers.get(tool_id)
        if h is None:
            return {"success": False, "reason": "chưa có handler (skeleton)"}
        try:
            return h()
        except Exception as exc:
            return {"success": False, "reason": f"lỗi thực thi: {exc}"}
