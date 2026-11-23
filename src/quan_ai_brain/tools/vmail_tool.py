# -*- coding: utf-8 -*-
"""MAIL_READ tool — CHERRY VMAIL INTELLIGENCE (mục 8 roadmap, owner duyệt 23/11).

Wire VmailConnector (Sprint 1) + ThreadAnalyzer (Sprint 2) vào Tool Registry của
ChatToolBridge/QPIG (CAI V3.0 §III) để /api/chat dùng được "đọc mail" như 1 tool
có evidence — KHÔNG tạo engine thứ 2, KHÔNG bypass QPIG (đăng ký đúng ToolDefinition,
chạy qua ToolSelector → QPIG.call như mọi tool khác).

R2 bất biến: tool CHỈ ĐỌC (risk R1, side_effects=False). Các thao tác GHI (send/
mark_read/delete) KHÔNG đăng ký — VmailConnector đã chặn unsupported_by_policy.
Fail-honest: trả {"success": False, "error": ...} khi SOAP lỗi — không fake.

Ghi chú fail-honest (24/11): tool NÀY chạy qua QPIG.call → registry handler trực
tiếp (in-process), KHÔNG đi qua web /api/chat pipeline đang tắt (manual-start,
port 8765/8766 OFF theo owner 19/11). Test mock 100% không cần server.
"""
from __future__ import annotations

from typing import Any

from quan_ai_brain.governance.policy import RiskLevel
from quan_ai_brain.tools.registry import ToolDefinition, ToolRegistry

TOOL_ID = "vmail_mail_read"

# Từ khóa intent cho ToolSelector.INTENT_KEYWORDS (được chat_bridge merge)
MAIL_INTENT_KEYWORDS: list[str] = [
    "đọc mail", "doc mail", "đọc email", "doc email", "email mới", "email moi",
    "hộp thư", "hop thu", "mail mới nhất", "mail moi nhat", "kiểm tra email",
    "kiem tra email", "tóm tắt luồng email", "tom tat luong email",
    "luồng email", "luong email", "thread email",
]


def _mail_read_handler(params: dict[str, Any]) -> dict[str, Any]:
    """Handler CHỈ ĐỌC: list inbox / search keyword / tóm tắt luồng.

    params:
        query:  Zimbra query hoặc từ khóa ("", "in:inbox", "khói", "from:dha1")
        limit:  1-20 (mặc định 5)
        mode:   "messages" (mặc định) | "threads" (Thread Analyzer 10 mục)
    """
    mode = (params.get("mode") or "messages").lower()
    query = (params.get("query") or "in:inbox").strip() or "in:inbox"
    try:
        limit = int(params.get("limit") or 5)
    except (TypeError, ValueError):
        limit = 5
    limit = max(1, min(limit, 20))

    try:
        from quan_ai_brain.office.vmail_connector import VmailConnector

        conn = VmailConnector()
        r = conn.list_messages(query, limit)
        if r.status != "ok":
            return {"success": False,
                    "error": f"SOAP error (fail-honest): {r.error or 'không rõ'}",
                    "operation": "mail_read", "params": {"query": query, "limit": limit}}
        data = r.data or {}
        msgs = data.get("messages", [])
        out: dict[str, Any] = {
            "success": True,
            "operation": "mail_read",
            "mode": mode,
            "query": query,
            "count": len(msgs),
            "messages": msgs,
            "source": "vmail.viettel.vn SOAP (READONLY R2)",
        }
        if mode == "threads":
            from quan_ai_brain.office.thread_analyzer import (
                analyze_thread,
                build_threads,
                format_thread_summary,
            )
            threads = build_threads(msgs)
            key = query if query in threads else None
            if key is None:  # chọn luồng nhiều mail nhất
                key = max(threads, key=lambda k: len(threads[k])) if threads else None
            if key is None:
                out["thread_summary"] = "(không có luồng nào)"
            else:
                a = analyze_thread(threads[key])
                out["thread_key"] = key
                out["thread_message_count"] = len(a.messages)
                out["thread_summary_text"] = format_thread_summary(a)
        return out
    except Exception as exc:  # fail-honest — không fake kết quả
        return {"success": False, "operation": "mail_read",
                "error": f"{type(exc).__name__}: {exc}"}


def build_mail_read_tool() -> ToolDefinition:
    """ToolDefinition MAIL_READ (R1, read-only, auto-allowed cho chat)."""
    return ToolDefinition(
        tool_id=TOOL_ID,
        description=("Đọc email Viettel vmail (SOAP READONLY R2): list inbox, "
                     "search từ khóa/người gửi, tóm tắt luồng thread 10 mục. "
                     "CHỈ ĐỌC — không gửi, không đánh dấu đã đọc, không xóa."),
        action_type="read",
        risk_level=RiskLevel.R1,
        handler=_mail_read_handler,
        input_schema={"required": [], "types": {"query": str, "limit": int, "mode": str}},
        allowed_resource_scope="vmail_readonly",
        side_effects=False,
        requires_owner_approval=False,  # đọc mail đã được owner duyệt (23/11)
        tool_version="1.0.0",
        protocol="soap",
        timeout_s=30.0,
        verification_method="StructuredResult status=ok từ VmailConnector + count>0 hoặc 0 hợp lệ",
    )


def register_vmail_tool(registry: ToolRegistry) -> str | None:
    """Đăng ký MAIL_READ vào registry (idempotent — nếu đã có trả None)."""
    if registry.has_tool(TOOL_ID):
        return None
    registry.register(build_mail_read_tool())
    return TOOL_ID
