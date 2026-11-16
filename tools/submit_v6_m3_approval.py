"""Create + approve + consume card TASK-V6-M3 (P3 Emotion blend mesh + HAPPY Duchenne).

Owner directive (desktop chat 16/11/2026): "em triển khai M3" — phase P3 trong lộ trình
CHERRY_V6_NATURAL_MOTION_AVATAR_PLAN.md §4: "Emotion blend mesh giữa 2 portrait (hết
hard-cut) + HAPPY Duchenne (mắt cong khi cười)". TEST 07/08 brief.

Audit nền (16/11): crossfade 350ms linear HAI LỚP globalAlpha đã có (v6emo 14/11);
emotion_engine.js (s3_1411) có transition presets + intensity nhưng _emotionEngine.update()
CHƯA được tick trong update loop; micro lerp factor cứng 0.08 không theo easing/intensity.
"""
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE / "src"))

from quan_ai_brain.governance.approval_cards import ApprovalCardStore  # noqa: E402

CARD_MD = """# TASK-V6-M3 — P3 Emotion Blend Mesh + HAPPY Duchenne

**Risk**: R2 · **Nguồn**: CHERRY_V6_NATURAL_MOTION_AVATAR_PLAN.md §4 (P3, TEST 07/08 brief)
**Chỉ thị owner**: "em triển khai M3" (desktop chat 16/11/2026)
**Nền đã audit**: crossfade 2 lớp globalAlpha 350ms (v6emo); emotion_engine s3_1411 chưa
được tick; micro-lerp factor cứng 0.08.

## Mục tiêu
M3a BLEND THEO PROGRESS ENGINE: tick _emotionEngine.update() mỗi frame; khi transition
đang chạy → FADE_MS lấy durationMs của preset (mặc định giữ 350), easing ease-in-out
thay linear — vẫn vẽ 2 lớp portrait qua _renderHeadPose (kiến trúc giữ nguyên).
M3b MICRO LERP THEO EASING+INTENSITY: factor frame = easing(duration, elapsed) ×
intensity clamp — chuyển nhanh/slow theo TRANSITION_PRESETS (SERIOUS_ALERT 120ms nhanh,
SLEEPING 900ms chậm) thay 0.08 cố định.
M3c HAPPY DUCHENNE: khi tone tích cực (WARM_GREETING/CONFIDENT_SUCCESS/PROUD/HAPPY) —
rig smile tăng kéo khóe + cheekRaise (đã có 0.6×) + micro eyeSquint sync theo _rigSmile
(mắt cong khi cười §4F brief: "Mắt hơi cong khi cười", không cường điệu).

## Phạm vi
- `edge_client/avatar_engine.js` + mirror (md5 đồng bộ); `edge_client/emotion_engine.js`
  + mirror nếu cần expose easing helper. Cache-buster `v6m3_1611` 3 HTML.
- Harness `data/wire_v6m3_test.js` NEW.
- KHÔNG đụng: audio_mouth_driver, body_motion_engine, asset, DB, secret, kiến trúc 2 lớp
  crossfade (đã duyệt v6emo), P1 rig, P2 warp.

## Không làm (trung thực)
- KHÔNG tạo engine thứ 2; KHÔNG đụng lớp tay (M4 PoC riêng); KHÔNG bật tóc động.
- Blend vẫn trên 2 portrait asset có sẵn — KHÔNG tạo portrait mới (giữ nhận diện Model A).
- E2E động cần owner nhìn kiosk (headless đóng băng thời gian).

## Test
- Node harness wire_v6m3_test.js: tick engine, fade duration theo preset, easing monotonic,
  micro factor theo intensity, Duchenne sync, P1/P2/M12 hooks nguyên.
- Re-run wire_v6m12 (39) + wire_v6rig (24) + wire_v6pose (25).
- node --check; full regression (baseline 11 fail pre-existing); live smoke; deploy Pi5 md5.

## Rollback
- Revert commit + cache-buster về `v6m12_1611`; backup .bak_pre_m3 trên Pi5.
"""

CARD = "TASK-V6-M3"


def main() -> int:
    store = ApprovalCardStore(WORKSPACE / "data" / "governance.db", workspace=str(WORKSPACE))
    if store.get_card(CARD) is None:
        card = store.create_card(
            CARD,
            title="V6 P3: Emotion blend mesh + HAPPY Duchenne (mắt cong khi cười)",
            card_markdown=CARD_MD,
            risk_level=2,
            goal="Chuyển cảm xúc mượt theo easing engine, hết hard-cut; HAPPY mắt cong khi cười",
            params={"owner_directive": "em triển khai M3", "date": "2026-11-16"},
        )
        print(f"CREATED: {card.task_code} -> {card.status}")
    card = store.approve_card(
        CARD,
        approver="quanpt1",
        auth_method="owner_desktop_chat_directive",
        notes=(
            'Owner: "em triển khai M3" (16/11/2026 desktop chat) — phase P3 theo lộ trình '
            "CHERRY_V6_NATURAL_MOTION_AVATAR_PLAN.md đã trình và duyệt hướng (M1+M2 đã xong b5e62df). "
            "Bám rễ V6.0 Model A 2.5D, không tạo asset mới."
        ),
    )
    print(f"APPROVED: {card.task_code} -> {card.status}")
    consumed = store.consume_if_execution_started(CARD)
    print(f"CONSUMED: {CARD} -> {consumed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
