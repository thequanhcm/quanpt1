"""Create + approve + consume card TASK-EMBODIMENT-S6 (Sprint 6 Body Motion Engine).

Owner directive (desktop chat 14/11/2026): "em tiếp tục xây dựng để hình thể trên
pi5 linh hoạt uyển chuyển tự nhiên như người thật" — phê duyệt Sprint 6 Body
Motion Engine (thay Sprint 6 Performance trong lộ trình gốc).
"""
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE / "src"))

from quan_ai_brain.governance.approval_cards import ApprovalCardStore  # noqa: E402

CARD_MD = """# TASK-EMBODIMENT-S6 — Sprint 6: Body Motion Engine

**Risk**: R2 · **Nguồn**: CHERRY_EMBODIMENT_SPRINT_PLAN.md §8 (Performance) — **thay thế** bằng Body Motion Engine theo yêu cầu owner "hình thể linh hoạt uyển chuyển tự nhiên".
**Chỉ thị owner**: "em tiếp tục xây dựng để hình thể trên pi5 linh hoạt uyển chuyển tự nhiên như người thật" (desktop chat 14/11/2026)

## Mục tiêu
Body motion human-like (Gate 6): shoulder sway, body lean, breathing, arm reach theo emotion + speech — không còn sway cứng.

## Phạm vi
1. NEW `edge_client/body_motion_engine.js` — BodyMotionEngine: shoulder sway + body lean + breathing + arm reach + speech sync.
2. NEW `edge_client/body_motion_engine.py` — Python mirror cho test pytest.
3. Wire vào 2 engine (PC + Pi5): apply body transform vào render loop (thay sway cứng).
4. 3 HTML: `<script src=body_motion_engine.js?v=s6_1411>` trước avatar_engine.js.

## Không làm (trung thực)
- KHÔNG tạo asset body_soft.png (stash experimental chỉ có canvas-drawn body, không có motion).
- KHÔNG sửa production DB.
- KHÔNG đụng presence engine (Sprint 5) hoặc audio mouth driver (Sprint 4).

## Test
- Unit: tests/test_body_motion_engine_sprint6.py (sway/lean/breath/arm/speech)
- Regression: pytest focused + node --check 3 file JS
- E2E: PC→Pi5 speak → body sway/lean/breath theo speech + emotion.

## Rollback
- Revert commit + cache bump về s5_1411 + redeploy Pi5 từ .bak_<tag>.
"""


def main() -> int:
    store = ApprovalCardStore(WORKSPACE / "data" / "governance.db", workspace=str(WORKSPACE))
    code = "TASK-EMBODIMENT-S6"
    if store.get_card(code) is None:
        card = store.create_card(
            code,
            title="Sprint 6: Body Motion Engine (shoulder sway + body lean + breathing + arm reach)",
            card_markdown=CARD_MD,
            risk_level=2,
            goal="Body motion human-like, không còn sway cứng",
            params={"owner_directive": "hình thể linh hoạt uyển chuyển tự nhiên", "date": "2026-11-14"},
        )
        print(f"CREATED: {card.task_code} -> {card.status}")
    card = store.approve_card(
        code,
        approver="quanpt1",
        auth_method="owner_desktop_chat_directive",
        notes=(
            'Owner: "em tiếp tục xây dựng để hình thể trên pi5 linh hoạt uyển chuyển tự nhiên '
            'như người thật" (14/11/2026 desktop chat) — duyệt Sprint 6 Body Motion Engine '
            "(thay Sprint 6 Performance trong lộ trình gốc). Stash body_sync_1311-experimental "
            "chứa canvas-drawn body (váy/đàn/hồng) — KHÔNG phải motion engine. Body motion "
            "engine mới sẽ apply sway/lean/breath vào render loop."
        ),
    )
    print(f"APPROVED: {card.task_code} -> {card.status}")
    consumed = store.consume_if_execution_started(code)
    print(f"CONSUMED: {code} -> {consumed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())