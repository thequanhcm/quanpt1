"""Approve + consume V8 card — owner directive MASTER PROMPT V8 via desktop chat 27/10/2026.

Owner explicitly sent the full V8 master prompt instructing implementation
("Antigravity, hãy bắt đầu bằng audit thực tế... sau đó triển khai những cải
tiến mang lại hiệu quả cao nhất" + 10-item priority list + acceptance criteria).
This is the explicit chat directive required by the sprint lifecycle.
"""
from __future__ import annotations

import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE / "src"))

from quan_ai_brain.governance.approval_cards import ApprovalCardStore

TASK_CODE = "TASK-V8-CONV-ENGINE"

if __name__ == "__main__":
    store = ApprovalCardStore(WORKSPACE / "data" / "governance.db", workspace=str(WORKSPACE))
    card = store.approve_card(
        TASK_CODE,
        "quanpt1",
        auth_method="owner_desktop_chat_directive",
        notes=(
            "Owner gui MASTER PROMPT V8 (Vietnamese Conversational Intelligence "
            "Engine) day du qua desktop chat 27/10/2026 - chi thi trien khai "
            "audit + upgrade theo 10 muc uu tien va tieu chi nghiem thu §X."
        ),
    )
    print("status:", card.status)
    consumed = store.consume_if_execution_started(TASK_CODE)
    print("consumed:", consumed)
