"""Create + approve + consume card TASK-F2-CLO-TIMEOUT (fix CLO session stalled).

Owner directive (desktop chat 22/11/2026): "em xử lý luôn F2 (patch self_study.py:
timeout 48h → tự COMPLETED, chuyển sang lessons queue)" — duyệt để làm ngay.

Nguồn: BAO_CAO_RA_SOAT_TONG_THE_CHERRY_20261122.md §5.1 F2 + ảnh Discord owner
gửi (bot spam cảnh báo "Buổi tự học liên tục #24 ĐANG CHẠY 75h/76h").

ĐIỀU KHOẢN CARD:
1. PATCH self_study.py: thêm hàm enforce_stall_timeout(workspace, max_hours=48)
   — CLO session RUNNING quá 48h → kết thúc qua ContinuousLearningEngine
   .end_session() CHUẨN (không sửa DB tay) + ghi 1 episode kind='experience_lesson'
   vào lessons queue (brain.db) để chu trình tự học kế tiếp scan thành knowledge
   gap → quarantined → chờ owner duyệt (giữ nguyên ranh giới §XI).
2. Watchdog tích hợp: check_clo_stall() trong tools/watchdog.py đổi sang gọi
   enforce_stall_timeout (48h) — watchdog hiện KHÔNG chạy nhưng giữ đúng hợp đồng.
3. Session #24 kẹt hiện tại (75h+): chạy enforce_stall_timeout 1 lần thật →
   session COMPLETED + lesson ghi queue + HealthMonitor thoát cảnh báo.
4. Fail-honest: mỗi bước ghi log rõ; không fake; test mock 100% tmp_path.
"""
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE / "src"))

from quan_ai_brain.governance.approval_cards import ApprovalCardStore  # noqa: E402

CARD_MD = """# TASK-F2-CLO-TIMEOUT — FIX CLO SESSION STALLED (timeout 48h → COMPLETED + lessons queue)

**Risk**: R1 (thin layer trên engine chuẩn end_session; không tự nạp memory — lesson vào QUARANTINE pipeline)
**Nguồn**: BAO_CAO_RA_SOAT_TONG_THE_CHERRY_20261122.md §5.1 F2
**Chỉ thị owner**: "em xử lý luôn F2 (patch self_study.py: timeout 48h → tự COMPLETED, chuyển sang lessons queue)" (desktop chat 22/11/2026)

## Mục tiêu
1. self_study.py: hàm enforce_stall_timeout(workspace, max_hours=48) — session
   RUNNING quá 48h → end_session qua ContinuousLearningEngine chuẩn + ghi episode
   kind='experience_lesson' (lessons queue) + trả report dict có bằng chứng.
2. tools/watchdog.py check_clo_stall(): gọi enforce_stall_timeout (48h) thay
   advance ngay 24h — giảm nhạy, đúng directive owner.
3. Chạy 1 lần thật cho session #24 (kẹt 75h+) → COMPLETED + lesson queue.
4. HealthMonitor không còn cảnh báo CLO (status hết RUNNING).

## Phạm vi KHÔNG đụng
- Không sửa DB tay — mọi transition qua LearningSessionManager.update_session chuẩn.
- Không tự promote lesson vào memory — chỉ queue (quarantined pipeline).
- Không bật daemon mới — vẫn manual-start.

## Bằng chứng nghiệm thu
- Test mock tmp_path: (a) session 49h → COMPLETED + lesson ghi; (b) session 30h → không đụng;
  (c) idempotent — chạy 2 lần không đẻ lesson trùng.
- Session #24 thật: status COMPLETED, ended_at đặt, health_monitor._evaluate_clo_stall → None.
- Full regression không tệ hơn baseline.
"""

CARD = "TASK-F2-CLO-TIMEOUT"


def main() -> int:
    store = ApprovalCardStore(WORKSPACE / "data" / "governance.db", workspace=str(WORKSPACE))
    if store.get_card(CARD) is None:
        card = store.create_card(
            CARD,
            title="F2: CLO session timeout 48h → COMPLETED + lessons queue",
            card_markdown=CARD_MD,
            risk_level=1,
            goal="Fix clo_session stalled — timeout 48h tự COMPLETED, bài học vào lessons queue",
            params={"owner_directive": "em xử lý luôn F2 (patch self_study.py: timeout 48h → tự COMPLETED, chuyển sang lessons queue)", "date": "2026-11-22"},
        )
        print(f"CREATED: {card.task_code} -> {card.status}")
    card = store.approve_card(
        CARD,
        approver="quanpt1",
        auth_method="owner_desktop_chat_directive",
        notes=(
            'Owner: "em xử lý luôn F2 (patch self_study.py: timeout 48h → tự COMPLETED, '
            'chuyển sang lessons queue)" (22/11/2026 desktop chat) — duyệt để làm ngay. '
            "Thin layer trên end_session chuẩn; lesson vào quarantine pipeline, không tự nạp memory."
        ),
    )
    print(f"APPROVED: {card.task_code} -> {card.status}")
    consumed = store.consume_if_execution_started(CARD)
    print(f"CONSUMED: {CARD} -> {consumed}")
    return 0


if __name__ == "__main__":
    main()
