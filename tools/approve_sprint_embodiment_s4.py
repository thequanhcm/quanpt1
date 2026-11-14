"""Create + approve + consume card TASK-EMBODIMENT-S4 (Sprint 4 Natural Voice & Lip-Sync).

Owner directive (desktop chat 14/11/2026): "em tiếp tục xây dựng để cherry trên
pi5 linh hoạt uyển chuyển tự nhiên như người thật" — phê duyệt Sprint 4 trong
lộ trình Embodiment Sprint 0-7 đã được owner duyệt.
"""
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE / "src"))

from quan_ai_brain.governance.approval_cards import ApprovalCardStore  # noqa: E402

CARD_MD = """# TASK-EMBODIMENT-S4 — Sprint 4: Natural Voice & Lip-Sync

**Risk**: R2 · **Nguồn**: CHERRY_EMBODIMENT_SPRINT_PLAN.md §6
**Chỉ thị owner**: "em tiếp tục xây dựng để cherry trên pi5 linh hoạt uyển chuyển tự nhiên như người thật" (desktop chat 14/11/2026)

## Mục tiêu
Đồng bộ giọng nói và hình thể (Gate 4): không có hiện tượng miệng nói khi không phát audio hoặc audio đã kết thúc mà miệng vẫn hoạt động.

## Phạm vi
1. NEW `edge_client/audio_mouth_driver.js` — Audio-driven mouth animation (RMS/envelope), interrupt handling, barge-in recovery.
2. NEW `edge_client/audio_mouth_driver.py` — Python mirror cho test pytest.
3. Wire vào 2 engine (PC + Pi5): thay timer fallback bằng live audio meter (analyser).
4. PC server: `/api/voice/tts` — first-chunk optimization, speaking state sync.
5. 3 HTML: `<script src=audio_mouth_driver.js?v=s4_1411>` trước avatar_engine.js.

## Không làm (trung thực)
- KHÔNG tạo asset mới (audio assets dùng TTS hiện có).
- KHÔNG sửa production DB.
- KHÔNG đụng motion scheduler (Sprint 2) hoặc emotion engine (Sprint 3).

## Test
- Unit: tests/test_audio_mouth_driver_sprint4.py (RMS/interrupt/barge-in/recovery)
- Regression: pytest focused + node --check 3 file JS
- E2E: PC→Pi5 speak → mouth mở/đóng theo audio thật, audio dừng → miệng đóng ngay

## Rollback
- Revert commit + cache bump về s3_1411 + redeploy Pi5 từ .bak_<tag>.
"""


def main() -> int:
    store = ApprovalCardStore(WORKSPACE / "data" / "governance.db", workspace=str(WORKSPACE))
    code = "TASK-EMBODIMENT-S4"
    if store.get_card(code) is None:
        card = store.create_card(
            code,
            title="Sprint 4: Natural Voice & Lip-Sync (audio-driven mouth + interrupt + barge-in)",
            card_markdown=CARD_MD,
            risk_level=2,
            goal="Miệng nói đúng lúc audio phát, đóng ngay khi audio dừng",
            params={"owner_directive": "xây dựng tiếp — linh hoạt uyển chuyển tự nhiên", "date": "2026-11-14"},
        )
        print(f"CREATED: {card.task_code} -> {card.status}")
    card = store.approve_card(
        code,
        approver="quanpt1",
        auth_method="owner_desktop_chat_directive",
        notes=(
            'Owner: "em tiếp tục xây dựng để cherry trên pi5 linh hoạt uyển chuyển tự nhiên '
            'như người thật" (14/11/2026 desktop chat) — duyệt Sprint 4 trong lộ trình '
            "Embodiment Sprint 0-7 đã được owner duyệt trước đó. Phạm vi = đúng card; "
            "fail-honest; test trước khi báo hoàn thành. Analyser đã có trên kiosk (06/11) "
            "— engine chỉ cần wire vào live audio meter."
        ),
    )
    print(f"APPROVED: {card.task_code} -> {card.status}")
    consumed = store.consume_if_execution_started(code)
    print(f"CONSUMED: {code} -> {consumed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())