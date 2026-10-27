"""Lập card TASK-V3-SPRINT16 — Memory Hygiene: Lọc system prompt khỏi chat episodes.

Nguồn phê duyệt: USER duyệt Sprint 16 (desktop chat, 27/10/2026 19:35 GMT+7).

Phạm vi:
- Sprint 15 smoke phát hiện: chat episodes chứa nguyên văn system prompt -> tạo noise contradictions.
- Increment: Lọc system prompt khỏi episodes khi lưu, chỉ giữ user/assistant messages.
- Không đụng cognitive_state, không đụng session song song.

Increment nhỏ, có test, fail-honest.
"""
import sys
sys.path.insert(0, 'src')

from pathlib import Path
from quan_ai_brain.governance.approval_cards import ApprovalCardStore, ApprovalStatus
from quan_ai_brain.governance.state_store import GovernanceStateStore

def main():
    workspace = Path(__file__).parent.parent
    gov_db = workspace / "data" / "governance.db"
    card_store = ApprovalCardStore(gov_db, workspace=workspace)

    card_code = "TASK-V3-SPRINT16"
    title = "Memory Hygiene — Lọc system prompt khỏi chat episodes"
    description = """
Sprint 15 smoke phát hiện: chat episodes chứa nguyên văn system prompt, tạo noise contradictions trong cognitive state.

Increment:
1. Lọc system prompt khỏi episodes khi lưu vào brain.db (chỉ giữ user/assistant messages).
2. Không đụng cognitive_state, không đụng session song song.
3. Test: đảm bảo episodes không chứa system prompt sau khi lưu.
4. Fail-honest: nếu không thể lọc, ghi UNVERIFIED.

Không tự động approve, không tự động deploy. Chờ owner duyệt.
    """.strip()

    owner = "quanpt1"
    risk_level = "R1"
    autonomy_level = "LEVEL_A"

    card = card_store.create_card(
        task_code=card_code,
        title=title,
        card_markdown=f"# {title}\n\n{description}",
        risk_level=2,  # R1
        goal="Memory Hygiene",
        ttl_days=3,
    )

    print(f"Card created: {card.request_id}")
    print(f"Code: {card.task_code}")
    print(f"Title: {card.title}")
    print(f"Status: {card.status}")
    print(f"\nOwner approval required: POST /api/approvals/decide with {{'card_id': '{card.request_id}', 'decision': 'APPROVE', 'owner_confirm': 'DUYET'}}")

if __name__ == "__main__":
    main()