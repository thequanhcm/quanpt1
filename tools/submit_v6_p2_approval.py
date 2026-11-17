"""Create + approve + consume card TASK-V6-P2 (Head Pose 3D giả + Mắt sống).

Owner directive (desktop chat 16/11/2026): "em cần xây dựng hình thể tương tác
như nhân vật thực" — duyệt Giai đoạn P2 trong CHERRY_V6_LIVE_PORTRAIT_DESIGN.md
§4 (đã được owner duyệt 15/11): head pose warp quanh trục cổ + mắt liếc saccade
tự nhiên + blink bằng warp mí.
"""
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE / "src"))

from quan_ai_brain.governance.approval_cards import ApprovalCardStore  # noqa: E402

CARD_MD = """# TASK-V6-P2 — Head Pose 3D giả + Mắt sống (Giai đoạn P2, V6-001)

**Risk**: R2 · **Nguồn**: CHERRY_V6_LIVE_PORTRAIT_DESIGN.md §4 (owner duyệt 15/11/2026)
**Chỉ thị owner**: "em cần xây dựng hình thể tương tác như nhân vật thực" (desktop chat 16/11/2026)
**Tiêu chí nghiệm thu (DESIGN §4 P2)**: lắc đầu/rung đầu/nghiêng là CHUYỂN ĐỘNG CỦA
ĐẦU NHÂN VẬT (warp mesh quanh cổ, không còn "lắc cả tấm ảnh"); mắt liếc tự nhiên.

## Mục tiêu
1. `_renderHeadPose`: warp mesh vùng đầu (dải y từ đỉnh tóc tới đáy cằm) quanh trục cổ —
   yaw ±6°, pitch ±4°, roll ±2° theo state/emotion + speech; thân bên dưới GIỮ NGUYÊN →
   cổ là điểm bẻ, đúng giải phẫu người.
2. Mắt sống: saccade mở rộng theo state (IDLE/LISTENING/SPEAKING), head pose dẫn dắt gaze
   (đầu quay → mắt nhìn cùng hướng trước, bù saccade sau).
3. Bảo toàn thành quả đã duyệt: P1 face rig (mày/miệng/cười), crossfade v6emo,
   gesture v6ges, body motion v6mot, mặt sạch không vẽ đè (tắt arms 16/11).

## Phạm vi
- Sửa `edge_client/avatar_engine.js` + mirror `src/quan_ai_brain/web/static/avatar_engine.js`
  (cùng md5, như mọi sprint embodiment).
- Cache-buster `v6pose_1611` trong 2 HTML (kiosk + executive).
- KHÔNG đụng: body_motion_engine.js, audio_mouth_driver.js, asset portrait, DB, secret.

## Ràng buộc (DESIGN §5)
- Warp KHÔNG vượt viền bake (crop trong khung); vùng tóc/mép khóa biên độ.
- ~20 tam giác, offscreen feather — Pi5 4GB vẫn 30fps (đo trước khi nghiệm thu).
- Không vẽ đặc điểm mới (Model A) — chỉ di chuyển đặc điểm gốc.

## Test
- Node harness `data/wire_v6pose_test.js`: warp chạy đúng vùng, mắt sạch (EYES_BOX
  không bị đè), P1 rig vẫn render, không xoay root transform.
- `node --check` 2 engine JS; pytest focused (nếu có test JS-binding).
- Full regression pytest + live smoke Console :8765 + screenshot so sánh.

## Rollback
- Revert commit + cache-buster về `v6noarms_1611`; harness P1 (wire_v6rig_test) chạy lại PASS.
"""

CARD = "TASK-V6-P2"


def main() -> int:
    store = ApprovalCardStore(WORKSPACE / "data" / "governance.db", workspace=str(WORKSPACE))
    if store.get_card(CARD) is None:
        card = store.create_card(
            CARD,
            title="V6-001 P2: Head pose 3D giả + mắt sống (warp quanh trục cổ)",
            card_markdown=CARD_MD,
            risk_level=2,
            goal="Lắc/nghiêng đầu là chuyển động của đầu nhân vật; mắt liếc tự nhiên",
            params={"owner_directive": "hình thể tương tác như nhân vật thực", "date": "2026-11-16"},
        )
        print(f"CREATED: {card.task_code} -> {card.status}")
    card = store.approve_card(
        CARD,
        approver="quanpt1",
        auth_method="owner_desktop_chat_directive",
        notes=(
            'Owner: "em cần xây dựng hình thể tương tác như nhân vật thực" (16/11/2026 desktop '
            "chat) — duyệt P2 Head Pose + Mắt sống theo lộ trình DESIGN §4 đã chốt 15/11. "
            "P1 face rig đã nghiệm thu (PR #31). Bám rễ V6.0: giữ Model A + asset hiện có."
        ),
    )
    print(f"APPROVED: {card.task_code} -> {card.status}")
    consumed = store.consume_if_execution_started(CARD)
    print(f"CONSUMED: {CARD} -> {consumed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
