# -*- coding: utf-8 -*-
"""Tests MAIL_READ tool (mục 8 roadmap CHERRY VMAIL — wire VmailConnector/ThreadAnalyzer
vào Tool Registry ChatToolBridge/QPIG).

Mock 100% — KHÔNG SOAP thật, KHÔNG server. Bao phủ:
1. ToolDefinition: R1, read-only, schema, không requires_owner_approval
2. register idempotent
3. Handler: messages mode ok / error fail-honest / limit clamp
4. Handler threads mode: dùng ThreadAnalyzer
5. ToolSelector: từ khóa mail → MAIL_READ, đủ confidence
6. ToolRegistryLoader: MAIL_READ được load, không bị reject
7. ChatToolBridge AUTO_DIRECTIVES chứa MAIL_READ
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

WORKSPACE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE / "src"))
sys.path.insert(0, str(WORKSPACE / "tools"))

from quan_ai_brain.governance.policy import RiskLevel  # noqa: E402
from quan_ai_brain.tools.chat_bridge import (  # noqa: E402
    ChatToolBridge,
    ToolRegistryLoader,
    ToolSelector,
)
from quan_ai_brain.tools.registry import ToolRegistry  # noqa: E402
from quan_ai_brain.tools.vmail_tool import (  # noqa: E402
    TOOL_ID,
    _mail_read_handler,
    build_mail_read_tool,
    register_vmail_tool,
)
from quan_ai_brain.uaiif.qpig import DIRECTIVE_NAMES  # noqa: E402

# ---- 1. ToolDefinition ----
class TestToolDefinition:
    def test_readonly_r1(self):
        td = build_mail_read_tool()
        assert td.risk_level == RiskLevel.R1
        assert td.side_effects is False
        assert td.requires_owner_approval is False
        assert td.action_type == "read"

    def test_schema_no_required(self):
        td = build_mail_read_tool()
        assert td.input_schema.get("required", []) == []

    def test_directive_mapping(self):
        assert DIRECTIVE_NAMES.get("MAIL_READ") == TOOL_ID


# ---- 2. Registration ----
class TestRegistration:
    def test_register_ok(self):
        reg = ToolRegistry()
        assert register_vmail_tool(reg) == TOOL_ID
        assert reg.has_tool(TOOL_ID)

    def test_register_idempotent(self):
        reg = ToolRegistry()
        register_vmail_tool(reg)
        assert register_vmail_tool(reg) is None  # lần 2 → None, không raise


# ---- 3. Handler messages mode (mock VmailConnector) ----
class TestHandlerMessages:
    def _fake_result(self, count=2):
        r = MagicMock()
        r.status = "ok"
        r.data = {"count": count, "messages": [
            {"id": str(i), "subject": f"Mail {i}", "date": "2026-11-23 09:00",
             "from_name": "A", "from_addr": "a@viettel.com.vn",
             "fragment": "nội dung", "has_attachment": False}
            for i in range(count)]}
        return r

    def test_messages_ok(self):
        with patch("quan_ai_brain.office.vmail_connector.VmailConnector") as MC:
            MC.return_value.list_messages.return_value = self._fake_result(2)
            out = _mail_read_handler({"query": "in:inbox", "limit": 2})
        assert out["success"] is True
        assert out["count"] == 2
        assert out["source"].startswith("vmail.viettel.vn")

    def test_error_fail_honest(self):
        r = MagicMock()
        r.status = "error"
        r.error = "SOAP lỗi: auth fail"
        with patch("quan_ai_brain.office.vmail_connector.VmailConnector") as MC:
            MC.return_value.list_messages.return_value = r
            out = _mail_read_handler({})
        assert out["success"] is False
        assert "SOAP lỗi: auth fail" in out["error"]

    def test_limit_clamped(self):
        with patch("quan_ai_brain.office.vmail_connector.VmailConnector") as MC:
            MC.return_value.list_messages.return_value = self._fake_result(1)
            _mail_read_handler({"limit": "999"})
            args = MC.return_value.list_messages.call_args
            assert args[0][1] <= 20  # (query, limit)


# ---- 4. Handler threads mode ----
class TestHandlerThreads:
    def test_threads_mode_uses_analyzer(self):
        r = MagicMock()
        r.status = "ok"
        r.data = {"count": 2, "messages": [
            {"id": "1", "subject": "Mời họp dự án X", "date": "2026-11-20 09:00",
             "from_name": "A", "from_addr": "a@viettel.com.vn", "fragment": "đề nghị anh tham dự",
             "has_attachment": False},
            {"id": "2", "subject": "[Hủy cuộc họp] Mời họp dự án X", "date": "2026-11-21 10:00",
             "from_name": "A", "from_addr": "a@viettel.com.vn", "fragment": "hủy cuộc họp",
             "has_attachment": False},
        ]}
        with patch("quan_ai_brain.office.vmail_connector.VmailConnector") as MC:
            MC.return_value.list_messages.return_value = r
            out = _mail_read_handler({"mode": "threads"})
        assert out["success"] is True
        assert out["thread_message_count"] == 2
        assert "TÓM TẮT LUỒNG" in out["thread_summary_text"]


# ---- 5. ToolSelector ----
class TestSelector:
    def _registry_with_mail(self) -> ToolRegistry:
        reg = ToolRegistry()
        # đăng ký vài tool QPIG giả lập + MAIL_READ
        for tid, desc, risk in [
            ("qpig_device_discovery", "Quét thiết bị LAN", RiskLevel.R0),
            ("qpig_network_inspection", "Probe kết nối", RiskLevel.R1),
        ]:
            reg.register(build_mail_read_tool().__class__(
                tool_id=tid, description=desc, action_type="read", risk_level=risk,
                handler=lambda p: {"success": True}, verification_method="ok"))
        register_vmail_tool(reg)
        return reg

    def test_mail_keywords_select_mail_read(self):
        sel = ToolSelector(self._registry_with_mail())
        picks = sel.select("đọc mail hôm nay giúp em")
        assert picks, "phải có ít nhất 1 lựa chọn"
        assert picks[0].directive_name == "MAIL_READ"
        assert picks[0].confidence >= ToolSelector.MIN_CONFIDENCE

    def test_non_mail_query_not_mail(self):
        sel = ToolSelector(self._registry_with_mail())
        picks = sel.select("quét thiết bị trong lan")
        if picks:
            assert picks[0].directive_name != "MAIL_READ"


# ---- 6+7. Loader + bridge ----
class TestLoaderAndBridge:
    def test_loader_loads_mail_read(self):
        loader = ToolRegistryLoader(qpig=MagicMock())
        loader.qpig.registry.list_tools.return_value = []
        loader.qpig.registered_tools.return_value = []
        reg = loader.load()
        assert reg.has_tool(TOOL_ID)
        assert TOOL_ID in loader._loaded
        assert loader.summary()["loaded"] >= 1

    def test_bridge_auto_directives_include_mail(self):
        assert "MAIL_READ" in ChatToolBridge.AUTO_DIRECTIVES
