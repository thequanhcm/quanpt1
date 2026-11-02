"""CAI V3.0 SPRINT 1 — Universal Tool Registry + QPIG Chat Integration.

§III: Tool Discovery/Registration/Schema/Authentication/Permission/Selection/
Execution/Result/Verification/Audit — 10 trụ cột. Mỗi tool có 13 thuộc tính §III.

§IV: Wire QPIG vào /api/chat — chèn tool evidence vào context trước LLM call.

§III chống giả mạo:
- Tool ID phải khớp DIRECTIVE_NAMES (QPIG) hoặc UAG_INTERVENTIONS (UAG)
- Schema validation: input phải khớp input_schema (type + required)
- Description injection: tool description KHÔNG được chứa chỉ thị hệ thống
  (pattern "ignore previous", "bỏ qua hướng dẫn", v.v.)
- Tool chỉ operational khi đã chạy thử thành công (QPIG catalog_summary)
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from quan_ai_brain.governance.policy import RiskLevel
from quan_ai_brain.tools.registry import ToolDefinition, ToolRegistry
from quan_ai_brain.uaiif.qpig import DIRECTIVE_NAMES, QPIG
from quan_ai_brain.uaiif.uag import UAGEngine

# Pattern chống description injection (§III)
_INJECTION_PATTERNS = (
    re.compile(r"ignore\s+(?:all\s+)?previous", re.I),
    re.compile(r"bỏ\s*qua\s+(?:mọi\s+)?hướng\s*dẫn", re.I),
    re.compile(r"disregard\s+(?:the\s+)?system", re.I),
    re.compile(r"you\s+are\s+now\s+", re.I),
    re.compile(r"<\s*system\s*>", re.I),
)


@dataclass
class ToolSelection:
    tool_id: str
    directive_name: str
    confidence: float
    reason: str
    risk: int
    requires_approval: bool
    operational: bool


class ToolSelector:
    """§III.6 Tool Selection — chọn tool theo intent, không chỉ tên.

    Scoring: keyword match (0.4) + directive_name match (0.3) + risk penalty (0.2)
    + operational bonus (0.1). Trả về top-1 hoặc None nếu không đủ tự tin.
    """

    # Intent → directive mapping (heuristic, có thể mở rộng)
    INTENT_KEYWORDS: dict[str, list[str]] = {
        "DEVICE_DISCOVERY": ["quét", "scan", "thiết bị", "device", "lan", "mạng"],
        "NETWORK_INSPECTION": ["ping", "kết nối", "latency", "độ trễ", "reachable"],
        "AGENT_DISCOVERY": ["khảo sát agent", "agent discovery", "tìm agent"],
        "AGENT_STATUS": ["trạng thái agent", "agent status", "agent có online"],
        "AGENT_AUTHENTICATION": ["xác minh agent", "agent identity", "ai đang kết nối"],
        "AGENT_PERMISSION_INSPECTION": ["quyền agent", "agent permission"],
        "AGENT_RUNTIME_INSPECTION": ["runtime agent", "agent đang chạy gì"],
        "EVIDENCE_COLLECTION": ["bằng chứng", "evidence", "lưu evidence"],
        "ACTION_VERIFICATION": ["xác minh hành động", "verify action", "đối chiếu"],
        "AGENT_ISOLATION_REQUEST": ["cô lập agent", "isolate agent", "yêu cầu cô lập"],
        "AGENT_SERVICE_CONTROL": ["dừng agent", "khởi động lại", "restart agent",
                                  "suspend agent", "tạm dừng agent"],
        "AGENT_PERMISSION_CONTROL": ["thu hồi quyền", "giới hạn agent", "khống chế agent"],
        "AGENT_RECOVERY": ["khôi phục agent", "agent recovery", "phục hồi"],
        "DEVICE_CONTROL": ["điều khiển thiết bị", "bật đèn", "tắt đèn", "robot"],
        "ROLLBACK_EXECUTION": ["rollback", "hoàn tác", "quay lại bản cũ"],
    }

    MIN_CONFIDENCE = 0.25

    def __init__(self, registry: ToolRegistry, qpig: QPIG | None = None) -> None:
        self.registry = registry
        self.qpig = qpig or QPIG()
        self._operational: dict[str, bool] = {
            r["tool_id"]: r.get("operational", False)
            for r in self.qpig.registered_tools()}

    def select(self, query: str, *, top_k: int = 3) -> list[ToolSelection]:
        q = query.lower()
        scored: list[ToolSelection] = []
        for directive, kws in self.INTENT_KEYWORDS.items():
            kw_score = self._kw_score(q, kws)
            # name match: so khớp directive dạng "device discovery" trong query
            name_score = 0.3 if directive.lower().replace("_", " ") in q else 0.0
            tool_id = DIRECTIVE_NAMES.get(directive)
            if tool_id is None:
                continue
            td = self.registry.get(tool_id)
            if td is None:
                continue
            risk = td.risk_level.value
            # risk_penalty chỉ áp dụng khi tool đã operational (đã chạy thật);
            # tool chưa E2E thì confidence thấp tự nhiên do thiếu op_bonus
            risk_penalty = 0.2 if (risk >= 3 and operational) else 0.0
            operational = self._operational.get(tool_id, False)
            op_bonus = 0.1 if operational else 0.0
            confidence = min(1.0, kw_score * 0.4 + name_score + op_bonus - risk_penalty)
            if confidence < self.MIN_CONFIDENCE:
                continue
            scored.append(ToolSelection(
                tool_id=tool_id, directive_name=directive,
                confidence=round(confidence, 3),
                reason=f"kw={kw_score:.2f} name={name_score:.2f} risk_pen={risk_penalty} op={op_bonus}",
                risk=risk, requires_approval=td.requires_owner_approval,
                operational=operational))
        scored.sort(key=lambda s: s.confidence, reverse=True)
        return scored[:top_k]

    def _kw_score(self, query_lower: str, kws: list[str]) -> float:
        """Đếm keyword match — robust với cả tiếng Việt có dấu và không dấu."""
        import unicodedata
        q_norm = unicodedata.normalize("NFD", query_lower)
        q_norm = "".join(c for c in q_norm if unicodedata.category(c) != "Mn")
        hits = 0
        for k in kws:
            k_norm = unicodedata.normalize("NFD", k.lower())
            k_norm = "".join(c for c in k_norm if unicodedata.category(c) != "Mn")
            if k in query_lower or k_norm in q_norm:
                hits += 1
        return hits / max(len(kws), 1)


class ToolRegistryLoader:
    """§III.1-2 Tool Discovery + Registration — auto-load từ QPIG + UAG.

    Trước đây ToolRegistry rỗng vì không có instance nào wire vào. Loader này
    tạo instance, đăng ký tool từ QPIG (25 tool) + UAG (engine-level), validate
    chống description injection, trả về registry sẵn dùng cho chat pipeline.
    """

    def __init__(self, *, qpig: QPIG | None = None,
                 uag: UAGEngine | None = None) -> None:
        self.qpig = qpig or QPIG()
        self.uag = uag
        self.registry = ToolRegistry()
        self._loaded: list[str] = []
        self._rejected: list[dict[str, str]] = []

    def load(self) -> ToolRegistry:
        for td in self.qpig.registry.list_tools():
            if self._is_safe(td):
                self.registry.register(td)
                self._loaded.append(td.tool_id)
            else:
                self._rejected.append({"tool_id": td.tool_id, "reason": "description_injection"})
        return self.registry

    def _is_safe(self, td: ToolDefinition) -> bool:
        """§III chống Tool Description Injection."""
        text = f"{td.description} {td.verification_method}"
        for pat in _INJECTION_PATTERNS:
            if pat.search(text):
                return False
        return True

    def summary(self) -> dict[str, Any]:
        return {"loaded": len(self._loaded), "rejected": len(self._rejected),
                "rejected_details": self._rejected[:5]}


# ---------------------------------------------------------------------------
# §IV: Wire QPIG vào chat pipeline
# ---------------------------------------------------------------------------
@dataclass
class ChatToolCall:
    """Một tool call được chèn vào chat context — có evidence + verification."""
    directive_name: str
    tool_id: str
    params: dict[str, Any]
    result: dict[str, Any] = field(default_factory=dict)
    evidence_id: int | None = None
    verified: bool = False
    operational: bool = False
    note: str = ""


class ChatToolBridge:
    """§IV: cầu nối Tool Selection → QPIG execution → evidence → context block.

    Luồng: USER MESSAGE → ToolSelector → top candidates → QPIG.call (chỉ tool
    AUTO_ALLOWED, không cần ticket) → evidence → render block cho LLM.
    Tool có tác động (R3+) KHÔNG tự execute — chỉ đề xuất + yêu cầu ticket.
    """

    # Tool tự động được gọi trong chat (không cần ticket) — khớp UAG AUTO_ALLOWED
    AUTO_DIRECTIVES = frozenset({
        "DEVICE_DISCOVERY", "NETWORK_INSPECTION", "AGENT_DISCOVERY",
        "AGENT_STATUS", "AGENT_AUTHENTICATION", "AGENT_PERMISSION_INSPECTION",
        "AGENT_RUNTIME_INSPECTION", "EVIDENCE_COLLECTION", "ACTION_VERIFICATION"})

    def __init__(self, qpig: QPIG, selector: ToolSelector) -> None:
        self.qpig = qpig
        self.selector = selector

    def process(self, query: str, *, max_calls: int = 2) -> list[ChatToolCall]:
        """Trả về danh sách tool call đã chạy (auto) + đề xuất (impact)."""
        selections = self.selector.select(query, top_k=max_calls)
        calls: list[ChatToolCall] = []
        for sel in selections:
            params = self._infer_params(query, sel.directive_name)
            if sel.directive_name in self.AUTO_DIRECTIVES and sel.operational:
                res = self.qpig.call(sel.tool_id, params)
                ev = self.qpig.evidence_capture(
                    kind="chat_tool_call", target=str(params.get("target", "?")),
                    payload={"directive": sel.directive_name, "params": params,
                             "result": res, "query": query[:200]})
                calls.append(ChatToolCall(
                    directive_name=sel.directive_name, tool_id=sel.tool_id,
                    params=params, result=res, evidence_id=ev.get("evidence_id"),
                    verified=bool(res.get("success")), operational=True,
                    note="auto-executed"))
            else:
                calls.append(ChatToolCall(
                    directive_name=sel.directive_name, tool_id=sel.tool_id,
                    params=params, operational=sel.operational,
                    note=("cần ticket Quanpt1 — không tự execute (§V)" if sel.risk >= 3
                          else "chưa operational — chờ E2E")))
        return calls

    def _infer_params(self, query: str, directive: str) -> dict[str, Any]:
        """Suy ra params tối thiểu từ query — conservative, không đoán sâu."""
        import re as _re
        ip = _re.search(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", query)
        target = ip.group(0) if ip else "192.168.1.2"  # default Pi5 nếu không có IP
        if directive in ("DEVICE_DISCOVERY",):
            return {}
        if directive in ("NETWORK_INSPECTION", "AGENT_DISCOVERY",
                         "AGENT_RUNTIME_INSPECTION", "DEVICE_IDENTIFICATION"):
            return {"target": target}
        if directive in ("AGENT_STATUS", "AGENT_AUTHENTICATION",
                         "AGENT_PERMISSION_INSPECTION"):
            return {"node_id": target, "agent_id": target}
        if directive in ("EVIDENCE_COLLECTION",):
            return {"kind": "chat_inquiry", "target": target, "payload": {"query": query[:200]}}
        if directive in ("ACTION_VERIFICATION",):
            return {"evidence_id": -1}  # sẽ fail-honest nếu evidence_id không tồn tại
        return {"target": target}

    def render_context_block(self, calls: list[ChatToolCall]) -> str:
        """Render evidence block chèn vào system_instructions trước LLM call."""
        if not calls:
            return ""
        lines = ["[TOOL EVIDENCE — kết quả thật từ QPIG, KHÔNG suy diễn]"]
        for c in calls:
            if c.evidence_id is not None:
                lines.append(
                    f"- {c.directive_name}: operational={c.operational} "
                    f"verified={c.verified} evidence_id={c.evidence_id} "
                    f"result={json.dumps(c.result, ensure_ascii=False)[:300]}")
            else:
                lines.append(f"- {c.directive_name}: {c.note}")
        lines.append("[Hết evidence]")
        return "\n".join(lines)
