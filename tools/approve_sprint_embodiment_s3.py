"""Create + approve + consume card TASK-EMBODIMENT-S3 (Sprint 3 Expressive Emotion Engine).

Owner directive (desktop chat 14/11/2026): "em tiếp tục xây dựng để cherry trên
pi5 linh hoạt uyển chuyển tự nhiên như người thật" — phê duyệt Sprint 3 trong
lộ trình Embodiment Sprint 0-7 đã được owner duyệt.
"""
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE / "src"))

from quan_ai_brain.governance.approval_cards import ApprovalCardStore  # noqa: E402

CARD_MD = """# TASK-EMBODIMENT-S3 — Sprint 3: Expressive Emotion Engine

**Risk**: R2 · **Nguồn**: CHERRY_EMBODIMENT_SPRINT_PLAN.md §5
**Chỉ thị owner**: "em tiếp tục xây dựng để cherry trên pi5 linh hoạt uyển chuyển tự nhiên như người thật" (desktop chat 14/11/2026)

## Mục tiêu
Tăng chiều sâu biểu cảm (Gate 3): cảm xúc hiển thị đúng ngữ cảnh, không chỉ đúng tên state.

## Phạm vi
1. NEW `edge_client/emotion_engine.js` — EmotionTransitionEngine (duration/easing/hold), EmotionIntensity 0.0-1.0, MicroEmotions, ContextAwareExtractor (negation + multi-emotion).
2. NEW `edge_client/emotion_engine.py` — Python mirror cho test pytest.
3. Wire vào 2 engine (PC + Pi5) — transition mượt thay thế set state trực tiếp.
4. 3 HTML: `<script src=emotion_engine.js?v=s3_1411>` trước avatar_engine.js.
5. Ảnh avatar_v2_surprised.png ĐÃ CÓ trên PC + Pi5 (verify 14/11) — dùng được.

## Không làm (trung thực)
- KHÔNG tạo asset mới (avatar_v2_surprised_v2.png) — ảnh hiện có đủ gate 3; asset v2 hoãn khi owner yêu cầu.
- KHÔNG đụng voice pipeline (Sprint 4).
- KHÔNG sửa production DB.

## Test
- Unit: tests/test_emotion_engine_sprint3.py (transition/intensity/micro/context/negation/multi)
- Regression: pytest focused + node --check 3 file JS
- E2E: PC→Pi5 set_expression PROUD mượt + telemetry không lỗi

## Rollback
- Revert commit + cache bump về s2_1411 + redeploy Pi5 từ .bak_<tag>.
"""


def main() -> int:
    store = ApprovalCardStore(WORKSPACE / "data" / "governance.db", workspace=str(WORKSPACE))
    code = "TASK-EMBODIMENT-S3"
    if store.get_card(code) is None:
        card = store.create_card(
            code,
            title="Sprint 3: Expressive Emotion Engine (transition + intensity + micro + context)",
            card_markdown=CARD_MD,
            risk_level=2,
            goal="Cảm xúc hiển thị đúng ngữ cảnh, không chỉ đúng tên state",
            params={"owner_directive": "xây dựng tiếp — linh hoạt uyển chuyển tự nhiên", "date": "2026-11-14"},
        )
        print(f"CREATED: {card.task_code} -> {card.status}")
    card = store.approve_card(
        code,
        approver="quanpt1",
        auth_method="owner_desktop_chat_directive",
        notes=(
            'Owner: "em tiếp tục xây dựng để cherry trên pi5 linh hoạt uyển chuyển tự nhiên '
            'như người thật" (14/11/2026 desktop chat) — duyệt Sprint 3 trong lộ trình '
            "Embodiment Sprint 0-7 đã được owner duyệt trước đó. Phạm vi = đúng card; "
            "fail-honest; test trước khi báo hoàn thành. avatar_v2_surprised.png ĐÃ CÓ "
            "PC+Pi5 (verify 14/11) — không cần tạo asset mới."
        ),
    )
    print(f"APPROVED: {card.task_code} -> {card.status}")
    consumed = store.consume_if_execution_started(code)
    print(f"CONSUMED: {code} -> {consumed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
