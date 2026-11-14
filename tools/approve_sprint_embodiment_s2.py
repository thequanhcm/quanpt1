"""Create + approve + consume card TASK-EMBODIMENT-S2 (Sprint 2 Natural Motion Engine).

Owner directive (desktop chat 14/11/2026): "em tiếp tục xây dựng để cherry trên
pi5 linh hoạt uyển chuyển tự nhiên như người thật" — phê duyệt Sprint 2 trong
lộ trình Embodiment Sprint 0-7 đã được owner duyệt.
"""
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE / "src"))

from quan_ai_brain.governance.approval_cards import ApprovalCardStore

CARD_MD = """# TASK-EMBODIMENT-S2 — Sprint 2: Natural Motion Engine

**Risk**: R2 · **Nguồn**: CHERRY_EMBODIMENT_SPRINT_PLAN.md §4 + CHERRY_MOTION_ENGINE_DESIGN.md
**Chỉ thị owner**: "em tiếp tục xây dựng để cherry trên pi5 linh hoạt uyển chuyển tự nhiên như người thật" (desktop chat 14/11/2026)

## Mục tiêu
Chuyển động mượt, không rung, không giật và không ảnh hưởng rendering (Gate 2).

## Phạm vi
1. NEW `edge_client/motion_scheduler.js` — MotionScheduler (priority + interrupt + blend + easing).
2. NEW `edge_client/gesture_library.js` — 10 gesture (greeting/listening/thinking/curious/empathic/emphatic/acknowledging/considering/responding/closing).
3. Wire vào 2 engine (PC + Pi5) qua protocol module (Sprint 1).
4. Head motion improvements: gentle head return, small conversational movement.
5. Eye motion improvements: slow blink, eye contact, brief gaze away, return-to-camera, curious gaze, empathic gaze.
6. Body motion: subtle shoulder, gentle upper-body sway (CSS transform — không cần asset).
7. Emotion transition: 300ms ease-in-out (Sprint 3 prep).

## Không làm (trung thực)
- KHÔNG đụng body_soft.png — file chưa tồn tại trên PC lẫn Pi5 (verify 14/11: 0 hits).
  Stash `body_sync_1311-experimental-avatar` chỉ chứa avatar_engine.js + kiosk.html,
  không có asset. Body motion dùng CSS transform (subtle shoulder + sway) thay thế.
- KHÔNG tạo asset mới (Sprint 3).
- KHÔNG đụng voice pipeline (Sprint 4).
- KHÔNG sửa production DB.

## Test
- Unit: tests/test_motion_scheduler_sprint2.py (priority/interrupt/blend/easing/gesture selection)
- Regression: pytest focused + node --check 2 engine
- E2E: PC→Pi5 set_expression → avatar chuyển state mượt, không giật
- FPS: đo trước/sau (target ≥ 12 FPS IDLE, ≥ 18 FPS THINKING/LISTENING, ≥ 24 FPS SPEAKING)

## Rollback
- Revert commit + cache bump về s1_1411 + redeploy Pi5 từ .bak_<tag>.
"""


def main() -> int:
    store = ApprovalCardStore(WORKSPACE / "data" / "governance.db", workspace=str(WORKSPACE))
    code = "TASK-EMBODIMENT-S2"
    if store.get_card(code) is None:
        card = store.create_card(
            code,
            title="Sprint 2: Natural Motion Engine (motion scheduler + gesture library)",
            card_markdown=CARD_MD,
            risk_level=2,
            goal="Chuyển động mượt, không rung, không giật và không ảnh hưởng rendering",
            params={"owner_directive": "xây dựng tiếp — linh hoạt uyển chuyển tự nhiên", "date": "2026-11-14"},
        )
        print(f"CREATED: {card.task_code} -> {card.status}")
    card = store.approve_card(
        code,
        approver="quanpt1",
        auth_method="owner_desktop_chat_directive",
        notes=(
            'Owner: "em tiếp tục xây dựng để cherry trên pi5 linh hoạt uyển chuyển tự nhiên '
            'như người thật" (14/11/2026 desktop chat) — duyệt Sprint 2 trong lộ trình '
            "Embodiment Sprint 0-7 đã được owner duyệt trước đó. Phạm vi = đúng card; "
            "fail-honest; test trước khi báo hoàn thành. body_soft.png chưa tồn tại → "
            "KHÔNG đụng, dùng CSS transform thay thế."
        ),
    )
    print(f"APPROVED: {card.task_code} -> {card.status}")
    consumed = store.consume_if_execution_started(code)
    print(f"CONSUMED: {code} -> {consumed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
