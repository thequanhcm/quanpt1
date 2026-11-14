"""Create + approve + consume card TASK-EMBODIMENT-S5 (Sprint 5 Human-Like Interaction).

Owner directive (desktop chat 14/11/2026): "em tiếp tục xây dựng để cherry trên
pi5 linh hoạt uyển chuyển tự nhiên như người thật" — phê duyệt Sprint 5 trong
lộ trình Embodiment Sprint 0-7 đã được owner duyệt.
"""
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE / "src"))

from quan_ai_brain.governance.approval_cards import ApprovalCardStore  # noqa: E402

CARD_MD = """# TASK-EMBODIMENT-S5 — Sprint 5: Human-Like Interaction

**Risk**: R2 · **Nguồn**: CHERRY_EMBODIMENT_SPRINT_PLAN.md §7
**Chỉ thị owner**: "em tiếp tục xây dựng để cherry trên pi5 linh hoạt uyển chuyển tự nhiên như người thật" (desktop chat 14/11/2026)

## Mục tiêu
Tăng tính hiện diện (Gate 5): người dùng giao tiếp tự nhiên mà không cảm nhận được các trạng thái máy móc.

## Phạm vi
1. NEW `edge_client/presence_engine.js` — PresenceEngine: eye contact + listening behavior + conversation continuity + natural idle + user interruption + return-to-idle.
2. NEW `edge_client/presence_engine.py` — Python mirror cho test pytest.
3. Wire vào 2 engine (PC + Pi5): idle behavior + listening gaze + eye contact qua render loop.
4. 3 HTML: `<script src=presence_engine.js?v=s5_1411>` trước avatar_engine.js.

## Không làm (trung thực)
- KHÔNG đụng wake response latency (wake_engine.js đã tối ưu 150ms trong sprint trước — xác nhận lại bằng đo, không sửa).
- KHÔNG sửa production DB.
- KHÔNG đụng audio mouth driver (Sprint 4) hoặc emotion engine (Sprint 3).

## Test
- Unit: tests/test_presence_engine_sprint5.py (eye contact/listening/continuity/idle/interruption/return-to-idle)
- Regression: pytest focused + node --check 3 file JS
- E2E: PC→Pi5 speak → глаз contact... [đã bỏ] E2E live set_expression + kiosk 200.

## Rollback
- Revert commit + cache bump về s4_1411 + redeploy Pi5 từ .bak_<tag>.
"""


def main() -> int:
    store = ApprovalCardStore(WORKSPACE / "data" / "governance.db", workspace=str(WORKSPACE))
    code = "TASK-EMBODIMENT-S5"
    if store.get_card(code) is None:
        card = store.create_card(
            code,
            title="Sprint 5: Human-Like Interaction (presence engine)",
            card_markdown=CARD_MD,
            risk_level=2,
            goal="Giao tiếp tự nhiên không cảm nhận trạng thái máy móc",
            params={"owner_directive": "xây dựng tiếp — linh hoạt uyển chuyển tự nhiên", "date": "2026-11-14"},
        )
        print(f"CREATED: {card.task_code} -> {card.status}")
    card = store.approve_card(
        code,
        approver="quanpt1",
        auth_method="owner_desktop_chat_directive",
        notes=(
            'Owner: "em tiếp tục xây dựng để cherry trên pi5 linh hoạt uyển chuyển tự nhiên '
            'như người thật" (14/11/2026 desktop chat) — duyệt Sprint 5 trong lộ trình '
            "Embodiment Sprint 0-7 đã được owner duyệt trước đó. Phạm vi = đúng card; "
            "fail-honest; test trước khi báo hoàn thành. Wake latency đã tối ưu từ trước "
            "(reply 18.37s→0.02s lịch sử sprint) — chỉ xác nhận lại, không sửa."
        ),
    )
    print(f"APPROVED: {card.task_code} -> {card.status}")
    consumed = store.consume_if_execution_started(code)
    print(f"CONSUMED: {code} -> {consumed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())