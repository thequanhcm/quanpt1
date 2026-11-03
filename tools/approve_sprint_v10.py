"""Approve + consume card TASK-V10-OWNER-REVIEW.

Owner directive: MASTER PROMPT V10 (28/10/2026, desktop chat) — "Antigravity,
hãy bắt đầu bằng audit hiện trạng và triển khai quy trình sàng lọc mẫu cho hệ
trí nhớ của QUAN AI BRAIN" — chỉ thị thực thi trực tiếp từ chủ nhân quanpt1.
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
        "TASK-V10-OWNER-REVIEW",
        approver="quanpt1",
        auth_method="owner_desktop_chat_directive",
        notes=(
            "MASTER PROMPT V10 — Owner-Gated Memory Review, gửi trực tiếp desktop "
            "chat 28/10/2026 với mệnh lệnh 'triển khai quy trình sàng lọc mẫu'. "
            "Phạm vi = đúng card; phân tích chỉ-đọc đến khi chủ xác nhận từng "
            "thay đổi; không tự mở rộng; R0-R5 giữ nguyên."
        ),
    )
    consume_if_execution_started("TASK-V10-OWNER-REVIEW")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
