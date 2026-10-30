"""Approve + consume card TASK-V9-DEEP-MEMORY.

Owner directive: MASTER PROMPT V9 (28/10/2026, desktop chat) — "hãy audit và
phát triển trực tiếp hệ trí nhớ chuyên sâu của QUAN AI BRAIN" — chỉ thị thực
thi trực tiếp từ chủ nhân quanpt1, precedented bởi TASK-V8-CONV-ENGINE.
"""
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE / "src"))

from quan_ai_brain.governance.approval_cards import ApprovalCardStore


def approve_card(code: str, approver: str, auth_method: str, notes: str):
    store = ApprovalCardStore(WORKSPACE / "data" / "governance.db", workspace=str(WORKSPACE))
    card = store.approve_card(code, approver=approver, auth_method=auth_method, notes=notes)
    print(f"APPROVED: {code} -> {card.status}")
    return card


def consume_if_execution_started(code: str):
    store = ApprovalCardStore(WORKSPACE / "data" / "governance.db", workspace=str(WORKSPACE))
    consumed = store.consume_if_execution_started(code)
    print(f"CONSUMED: {code} -> {consumed}")
    return consumed


def main() -> int:
    approve_card(
        "TASK-V9-DEEP-MEMORY",
        approver="quanpt1",
        auth_method="owner_desktop_chat_directive",
        notes=(
            "MASTER PROMPT V9 — Deep Cognitive Memory & Logical Knowledge Governance "
            "Engine, gửi trực tiếp trong desktop chat 28/10/2026 với mệnh lệnh 'audit "
            "và phát triển trực tiếp hệ trí nhớ chuyên sâu'. Phạm vi = đúng card; "
            "R0-R5 + approval production giữ nguyên; DB additive-only có backup."
        ),
    )
    consume_if_execution_started("TASK-V9-DEEP-MEMORY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
