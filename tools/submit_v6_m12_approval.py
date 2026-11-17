"""Create + approve + consume card TASK-V6-M12 (M1 Facial Engine + M2 Lip-sync).

Owner directive (desktop chat 16/11/2026): "duyệt hướng này (duyệt để làm) em triển
khai M1 + M2 ngay trong sprint này" — duyệt 2 phase đầu của lộ trình
CHERRY_V6_NATURAL_MOTION_AVATAR_PLAN.md (thiết kế dựa trên 2 video mẫu đo thật).
"""
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE / "src"))

from quan_ai_brain.governance.approval_cards import ApprovalCardStore  # noqa: E402

CARD_MD = """# TASK-V6-M12 — M1 Facial Engine hoàn thiện + M2 Lip-sync & Đầu vững

**Risk**: R2 · **Nguồn**: CHERRY_V6_NATURAL_MOTION_AVATAR_PLAN.md §4 (owner duyệt 16/11)
**Chỉ thị owner**: "duyệt để làm" M1+M2 (desktop chat 16/11/2026)
**Nguồn đo**: E:/BRAIN/Pi5/hình thể.mp4 + hình thể1.mp4 (optical flow + frame analysis,
data/v6_body_ref_audit.json)

## Mục tiêu
M1: (a) bảng 12 tham số biểu cảm chuẩn hoá `_facialParams()` (§5 brief) — read-only
introspection + helper _browAmtFor, không phá render P1/P2; (b) LISTENING gật nhẹ xác
nhận thi thoảng; (c) THINKING chớp mắt chậm; (d) IDLE mỉm cười thi thoảng (12-20s/lần).
M2: (a) "đầu vững khi mở miệng lớn" — steady factor theo openRatio (đo: mở 50-60% =
đầu frontal); (b) viseme tiếng Việt chuẩn hoá (bảng 11 nguyên âm + suy từ dải mở);
(c) răng dưới khi mở rất lớn (>0.8) — đo từ video mở tối đa.

## Phạm vi
- `edge_client/avatar_engine.js` + mirror static (md5 đồng bộ, như mọi sprint).
- Cache-buster `v6m12_1611` trong kiosk.html + executive.html + index.html.
- Harness `data/wire_v6m12_test.js` NEW.
- KHÔNG đụng: audio_mouth_driver, body_motion_engine, presence_engine, asset, DB, secret.

## Không làm (trung thực)
- KHÔNG tạo engine thứ 2 (anti-pattern) — 12-param là accessor đọc state có sẵn.
- KHÔNG chuyển 3D/VRM (VERBATIM owner: giữ Model A + asset hiện có).
- KHÔNG wire lớp tay/cử chỉ (M4 — phải PoC duyệt riêng, bài học arms-1311).
- KHÔNG bật tóc động (owner tắt 14/11).

## Test
- Node harness wire_v6m12_test.js: 12-param đủ key, LISTENING nod, THINKING slow-blink,
  IDLE smile gate, steady factor, viseme shape dải, răng dưới, P1/P2 hooks nguyên.
- Re-run wire_v6rig_test (24) + wire_v6pose_test (25) — không hồi quy.
- node --check; full regression pytest (baseline 11 fail pre-existing).
- Live smoke PC :8765 + deploy Pi5 md5 + reload_ui + JS console sạch.

## Rollback
- Revert commit + cache-buster về `v6pose_1611`; backup .bak_pre_m12 trên Pi5.
"""

CARD = "TASK-V6-M12"


def main() -> int:
    store = ApprovalCardStore(WORKSPACE / "data" / "governance.db", workspace=str(WORKSPACE))
    if store.get_card(CARD) is None:
        card = store.create_card(
            CARD,
            title="V6 M1+M2: Facial Engine 12-param hoàn thiện + Lip-sync & đầu vững",
            card_markdown=CARD_MD,
            risk_level=2,
            goal="8 nhóm chuyển động chuẩn brief: hoàn thiện facial params + lip-sync tiếng Việt",
            params={"owner_directive": "duyệt để làm M1+M2", "date": "2026-11-16"},
        )
        print(f"CREATED: {card.task_code} -> {card.status}")
    card = store.approve_card(
        CARD,
        approver="quanpt1",
        auth_method="owner_desktop_chat_directive",
        notes=(
            'Owner: "duyệt hướng này (duyệt để làm) em triển khai M1 + M2 ngay trong sprint này" '
            "(16/11/2026 desktop chat) — duyệt 2 phase đầu theo CHERRY_V6_NATURAL_MOTION_AVATAR_PLAN.md "
            "đã trình (audit 2 video mẫu + kiến trúc 10 module). Bám rễ V6.0 Model A 2.5D."
        ),
    )
    print(f"APPROVED: {card.task_code} -> {card.status}")
    consumed = store.consume_if_execution_started(CARD)
    print(f"CONSUMED: {CARD} -> {consumed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
