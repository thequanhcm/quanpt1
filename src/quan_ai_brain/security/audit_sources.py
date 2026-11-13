"""Audit Data Source Labels — TASK-AGENTIC-SEC-1 Slice (d).

Áp dụng khung ATTT Agentic AI (MIT + Viettel Cyber Security 261113_VTNET_ATTT_Agentic_AI_v4):
- Slide 11: "sự cố đi qua cả 3 nhóm (con người / dữ liệu / hệ thống)" — audit phải
  truy vết được ĐƯỜNG ĐI của dữ liệu, không chỉ action.
- GAP-4 audit hiện tại thiếu field nguồn dữ liệu → thêm `data_source_labels`.

record_shield_event(): ghi security event khi InputInjectionShield bắt SANITIZE/BLOCK.
Schema append-only (SecurityEventStore — security_events), thêm label vào evidence_json.
"""
from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # tránh circular import
    from quan_ai_brain.security.input_shield import ShieldResult

log = logging.getLogger(__name__)

# Nhãn nguồn chuẩn hóa (GAP-4) — nguồn dữ liệu đầu vào của shield
DATA_SOURCE_API_CHAT = "api_chat"          # request /api/chat từ browser owner
DATA_SOURCE_NETCHAT_DM = "netchat_dm"      # tin nhắn NetChat DM (EchoLeak surface)
DATA_SOURCE_EMAIL = "email"                # email nội bộ (EchoLeak slide 8)
DATA_SOURCE_WEB = "web"                    # kết quả tra cứu ngoài
DATA_SOURCE_DOCUMENT = "document"          # tài liệu/RAG ngoài

_ALL_SOURCES = {
    DATA_SOURCE_API_CHAT, DATA_SOURCE_NETCHAT_DM, DATA_SOURCE_EMAIL,
    DATA_SOURCE_WEB, DATA_SOURCE_DOCUMENT,
}


def record_shield_event(result: "ShieldResult", source: str = DATA_SOURCE_API_CHAT) -> int | None:
    """Ghi audit event khi shield bắt injection (SANITIZE/BLOCK).

    Trả security_events.id hoặc None nếu fail (fail-open — shield không chết vì audit).
    """
    try:
        from quan_ai_brain.security.watcher import SecurityEventStore
        store = SecurityEventStore()
        evidence = {
            "data_source_labels": [source if source in _ALL_SOURCES else "unknown"],
            "verdict": result.verdict.value,
            "score": result.score,
            "matched_patterns": result.matched[:10],
            "reason": result.reason,
        }
        return store.record(
            violation=f"INPUT_INJECTION_{result.verdict.value}",
            pid=0,
            process_name="input_shield",
            cmdline="",
            contract_id="TASK-AGENTIC-SEC-1",
            evidence=evidence,
            handled="AUTO_HANDLED" if result.verdict.value == "SANITIZE" else "PENDING",
            action_taken="SANITIZED" if result.verdict.value == "SANITIZE" else "BLOCKED",
        )
    except Exception as exc:  # fail-open
        log.warning("record_shield_event failed: %s", exc)
        return None


def record_trifecta_event(description: str, task_class: str,
                          effective_class: str, flags_count: int) -> int | None:
    """Ghi audit event khi trifecta guard nâng cấp AUTO → PROPOSE (slide 13)."""
    try:
        from quan_ai_brain.security.watcher import SecurityEventStore
        store = SecurityEventStore()
        evidence = {
            "data_source_labels": ["autonomous_task"],
            "trifecta_flags_count": flags_count,
            "task_class": task_class,
            "effective_class": effective_class,
            "upgraded": effective_class != task_class,
        }
        return store.record(
            violation="LETHAL_TRIFECTA_UPGRADE",
            pid=0,
            process_name="trifecta_guard",
            cmdline=(description or "")[:500],
            contract_id="TASK-AGENTIC-SEC-1",
            evidence=evidence,
            handled="PENDING" if effective_class == "PROPOSE" else "AUTO_HANDLED",
            action_taken=f"UPGRADED_{task_class}_TO_{effective_class}",
        )
    except Exception as exc:  # fail-open
        log.warning("record_trifecta_event failed: %s", exc)
        return None
