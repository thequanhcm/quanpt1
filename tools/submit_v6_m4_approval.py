"""Create + approve + consume card TASK-V6-M4 (Body gesture: PoC tay procedural + GOODBYE).

Owner directive (desktop chat 16/11/2026): "em triển khai M4" — phase M4 trong lộ trình
CHERRY_V6_NATURAL_MOTION_AVATAR_PLAN.md §4: "lớp tay procedural (nhẹ, đúng tỷ lệ,
DUYỆT PoC RIÊNG trước khi wire) + GOODBYE (gật + cử chỉ chào + về Idle)".

ĐIỀU KHOẢN CARD — bài học arms-1311 (16/11 owner yêu cầu xoá 2 cánh tay chibi bake +
tắt _renderArmsOverPortrait):
1. TAY: chỉ làm PoC HTML (cherry_poc_arms.html) — KHÔNG wire vào kiosk production
   cho tới khi owner duyệt PoC riêng ("duyệt PoC" / "duyệt để làm").
2. GOODBYE (không tay): wire được ngay — gật chào + lean-back nhẹ + về IDLE, thời
   lượng ~2.5s, một lần khi kết thúc hội thoại.
"""
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE / "src"))

from quan_ai_brain.governance.approval_cards import ApprovalCardStore  # noqa: E402

CARD_MD = """# TASK-V6-M4 — Body Gesture: PoC Tay Procedural + GOODBYE

**Risk**: R2 · **Nguồn**: CHERRY_V6_NATURAL_MOTION_AVATAR_PLAN.md §4 (M4, TEST 06/07)
**Chỉ thị owner**: "em triển khai M4" (desktop chat 16/11/2026)
**Điều khoản lộ trình**: tay PHẢI PoC duyệt riêng trước khi wire (arms-1311).

## Mục tiêu
M4a GOODBYE STATE (wire ngay): state GOODBYE — gật chào 2 nhịp + lean-back nhẹ + mặt
trả về IDLE sau ~2.5s; phun từ sự kiện kết thúc phát thoại (stopSpeaking / utterance
end) khi tone tích cực; portrait mặc định (không asset mới).
M4b POC TAY PROCEDURAL (KHÔNG wire): file PoC HTML riêng `data/cherry_poc_arms.html`
— canvas 2.5D vẽ tay chính ảnh warp (không sprite chibi như arms-1311): cẳng tay +
bàn tay warp từ mép ảnh theo gesture (wave-chào, explain-palm), đúng tỷ lệ Model A,
tắt/bật bằng toggle, 3 tốc độ. Owner xem PoC rồi quyết: duyệt wire / chỉnh / bỏ.

## Phạm vi
- M4a: `edge_client/avatar_engine.js` + mirror (state GOODBYE + harness) + kiosk.js
  trigger + cache-buster `v6m4_1611`.
- M4b: CHỈ `data/cherry_poc_arms.html` (standalone, không import vào kiosk).
- KHÔNG đụng: audio driver, asset, DB, secret, P1/P2/M12/M3 render paths.

## Không làm (trung thực)
- KHÔNG vẽ tay vào kiosk/production trước PoC duyệt riêng (nghiêm cấm lặp arms-1311).
- KHÔNG tạo asset tay mới; PoC dùng warp trên chính ảnh.
- E2E động cần owner nhìn kiosk.

## Test
- Harness `data/wire_v6m4_test.js`: GOODBYE phun đúng lúc + tự về IDLE 2.5s + gật 2
  nhịp + lean-back + không đụng nhánh tay production (arms vẫn tắt) + hooks nguyên.
- Re-run m3/m12/rig/pose. node --check. Regression. Live smoke. Deploy Pi5 md5.
- PoC tay: mở file trực tiếp (standalone HTML) — owner duyệt bằng mắt.

## Rollback
- Revert commit + cache-buster về `v6m3_1611`; backup .bak_pre_m4 trên Pi5; PoC là
  file độc lập — xoá không ảnh hưởng production.
"""

CARD = "TASK-V6-M4"


def main() -> int:
    store = ApprovalCardStore(WORKSPACE / "data" / "governance.db", workspace=str(WORKSPACE))
    if store.get_card(CARD) is None:
        card = store.create_card(
            CARD,
            title="V6 M4: GOODBYE (wire) + PoC tay procedural (duyệt riêng)",
            card_markdown=CARD_MD,
            risk_level=2,
            goal="Nhóm G/H brief: GOODBYE gật chào + về IDLE; PoC tay warp 2.5D chờ duyệt",
            params={"owner_directive": "em triển khai M4", "date": "2026-11-16",
                    "poc_gate": "arms cần duyệt PoC riêng trước wire"},
        )
        print(f"CREATED: {card.task_code} -> {card.status}")
    card = store.approve_card(
        CARD,
        approver="quanpt1",
        auth_method="owner_desktop_chat_directive",
        notes=(
            'Owner: "em triển khai M4" (16/11/2026 desktop chat) — M4 theo lộ trình đã duyệt. '
            "Card tự ràng buộc: tay chỉ PoC, wire tay cần owner duyệt PoC riêng (arms-1311). "
            "GOODBYE wire được ngay trong card này."
        ),
    )
    print(f"APPROVED: {card.task_code} -> {card.status}")
    consumed = store.consume_if_execution_started(CARD)
    print(f"CONSUMED: {CARD} -> {consumed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
