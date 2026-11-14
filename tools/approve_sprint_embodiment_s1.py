"""Create + approve + consume card TASK-EMBODIMENT-S1 (Sprint 1 Unified Emotion Protocol).

Owner directive (desktop chat 14/11/2026): "xây dựng tiếp" — phê duyệt sprint
tiếp theo trong lộ trình Sprint 0-7 (CHERRY_EMBODIMENT_SPRINT_PLAN.md) đã được
owner duyệt. Sprint 0 DONE; Sprint 1 là sprint kế tiếp.
"""
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE / "src"))

from quan_ai_brain.governance.approval_cards import ApprovalCardStore

CARD_MD = """# TASK-EMBODIMENT-S1 — Sprint 1: Unified Emotion Protocol

**Risk**: R2 · **Nguồn**: CHERRY_EMBODIMENT_SPRINT_PLAN.md §3 + CHERRY_EMBODIMENT_BASELINE.md §12-13
**Chỉ thị owner**: "xây dựng tiếp" (desktop chat 14/11/2026)

## Mục tiêu
PC và Pi5 hiểu CÙNG một sự kiện theo CÙNG một quy tắc (Gate 1).

## Phạm vi
1. NEW `shared/avatar_protocol.js` — 1 nguồn sự thật: 22 STATE_CONFIGS, EMOTION_TONES,
   extractVietnameseEmotion, normalizeState, IPC envelope 17 field + validator
   (timestamp/sequence/duplicate/stale/expiry/reconciliation).
2. 2 engine (PC + Pi5) đọc protocol từ shared module — xóa bản local trùng lặp.
3. server.py `_handle_api_edge_control`: bọc envelope (event_id, sequence, platform...)
4. client_daemon.py `/api/kiosk/control`: validate envelope trước khi xử lý.
5. kiosk.html + executive.html thêm script tag + cache bump.

## Test
- Unit: tests/test_avatar_protocol_sprint1.py (registry + validator 8 ca Sprint plan §3.4)
- Regression: pytest focused + node --check 2 engine
- E2E: PC→Pi5 set_expression sync; telemetry mirror Pi5→PC

## Không làm
- Không đụng body_soft/stash (Sprint 2), không tạo asset mới (Sprint 3),
  không đụng voice pipeline (Sprint 4), không sửa production DB.

## Rollback
- Revert commit + cache bump về cherry_sync1314 + redeploy Pi5 từ .bak_<tag>.
"""

def main() -> int:
    store = ApprovalCardStore(WORKSPACE / "data" / "governance.db", workspace=str(WORKSPACE))
    code = "TASK-EMBODIMENT-S1"
    if store.get_card(code) is None:
        card = store.create_card(
            code,
            title="Sprint 1: Unified Emotion Protocol (PC↔Pi5)",
            card_markdown=CARD_MD,
            risk_level=2,
            goal="PC và Pi5 hiểu cùng một sự kiện theo cùng một quy tắc",
            params={"owner_directive": "xây dựng tiếp", "date": "2026-11-14"},
        )
        print(f"CREATED: {card.task_code} -> {card.status}")
    card = store.approve_card(
        code,
        approver="quanpt1",
        auth_method="owner_desktop_chat_directive",
        notes=(
            'Owner: "xây dựng tiếp" (14/11/2026 desktop chat) — duyệt sprint tiếp theo '
            "trong lộ trình Embodiment Sprint 0-7 đã được owner duyệt trước đó. "
            "Phạm vi = đúng card; fail-honest; test trước khi báo hoàn thành."
        ),
    )
    print(f"APPROVED: {card.task_code} -> {card.status}")
    consumed = store.consume_if_execution_started(code)
    print(f"CONSUMED: {code} -> {consumed}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
