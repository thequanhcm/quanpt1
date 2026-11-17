"""Create + approve + consume card TASK-V6-M5 (Tối ưu Pi5 PROFILE A + benchmark 60 phút).

Owner directive (desktop chat 16/11/2026): "em triển khai M5" — phase M5 trong lộ trình
CHERRY_V6_NATURAL_MOTION_AVATAR_PLAN.md §4: "Tối ưu Pi5 (PROFILE A): đo FPS thật,
giảm chi phí khi CPU cao; PROFILE B PC giữ full; benchmark 60min".

ĐIỀU KHOẢN CARD:
1. ĐO FPS THẬT (M5a): engine đo FPS + render-ms thật mỗi frame, kiosk.js báo về
   daemon (POST telemetry), Edge Agent lưu history — benchmark đọc được.
2. GIẢM CHI PHÍ KHI CPU CAO (M5b): Edge Agent (đã đo CPU mỗi 30s) phát hiện
   CPU cao 3 mẫu liên tiếp → perf_profile=LOW vào to_kiosk_dict → kiosk.js đặt
   engine.setPerfProfile("LOW") — FPS cap giảm (IDLE 8, SPEAKING 15), tắt
   micro-saccade, giảm particles. CPU về bình thường 3 mẫu → NORMAL.
3. PROFILE B (PC) giữ full — không đụng engine PC; Pi5 mặc định NORMAL.
4. BENCHMARK 60 phút (M5c): tools/v6_m5_benchmark_pi5.py — sample 30s/lần qua
   Edge Agent metrics + PC RTT, ngưỡng CPU/nhiệt/throttle, report JSON+MD.
5. Fail-honest: FPS đọc từ đo thật của engine (không mô phỏng); benchmark chỉ
   ghi số liệu có nguồn; chưa verify E2E ghi rõ "chờ nghiệm thu".
"""
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE / "src"))

from quan_ai_brain.governance.approval_cards import ApprovalCardStore  # noqa: E402

CARD_MD = """# TASK-V6-M5 — TỐI ƯU PI5 (PROFILE A) + BENCHMARK 60 PHÚT

**Risk**: R1 (chỉ đo + cap FPS khi CPU cao, không đổi kiến trúc)
**Nguồn**: CHERRY_V6_NATURAL_MOTION_AVATAR_PLAN.md §4 (M5, benchmark 60min)
**Chỉ thị owner**: "em triển khai M5" (desktop chat 16/11/2026)

## Mục tiêu
M5a FPS meter thật trong avatar_engine (render ms + fps trung bình 10s) — expose
window.__cherryPerf + kiosk.js đẩy lên daemon mỗi 30s; Edge Agent lưu history.
M5b auto-degrade: CPU cao 3 mẫu liên tiếp (>=60%) → perf_profile=LOW
(FPS IDLE 8/SPEAKING 15, tắt micro-saccade, giảm particles); hồi NORMAL khi
CPU <40% 3 mẫu. PROFILE B PC giữ full (không đụng).
M5c benchmark 60 phút: tools/v6_m5_benchmark_pi5.py (đã smoke PASS 0.5 phút).

## Phạm vi KHÔNG đụng
- Không đổi kiến trúc engine; không tạo engine thứ 2 (đọc state có sẵn).
- Không deploy kèm thay đổi chưa verify; node --check + harness + regression.

## Bằng chứng nghiệm thu
- node --check 3 file JS OK; harness M5 (fps meter + perf profile) PASS.
- Full regression ≥ baseline (4083/10 pre-existing).
- Benchmark 60 phút chạy xong → reports/V6_M5_BENCHMARK_*.md PASS/WARN.
"""

CARD = "TASK-V6-M5"


def main() -> int:
    store = ApprovalCardStore(WORKSPACE / "data" / "governance.db", workspace=str(WORKSPACE))
    if store.get_card(CARD) is None:
        card = store.create_card(
            CARD,
            title="V6 M5: Tối ưu Pi5 (PROFILE A) + benchmark 60 phút",
            card_markdown=CARD_MD,
            risk_level=1,
            goal="Đo FPS thật + auto-degrade khi CPU cao + benchmark 60 phút (không đổi kiến trúc)",
            params={"owner_directive": "em triển khai M5", "date": "2026-11-16"},
        )
        print(f"CREATED: {card.task_code} -> {card.status}")
    card = store.approve_card(
        CARD,
        approver="quanpt1",
        auth_method="owner_desktop_chat_directive",
        notes=(
            'Owner: "em triển khai M5" (16/11/2026 desktop chat) — phase M5 theo lộ trình '
            "CHERRY_V6_NATURAL_MOTION_AVATAR_PLAN.md §4: đo FPS thật, giảm chi phí khi CPU "
            "cao (PROFILE A), benchmark 60 phút. Không đổi kiến trúc."
        ),
    )
    print(f"APPROVED: {card.task_code} -> {card.status}")
    consumed = store.consume_if_execution_started(CARD)
    print(f"CONSUMED: {CARD} -> {consumed}")
    return 0


if __name__ == "__main__":
    main()
