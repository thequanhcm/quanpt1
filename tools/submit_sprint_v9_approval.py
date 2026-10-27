"""Submit approval card for V9 — Deep Cognitive Memory & Logical Knowledge Governance.

Owner directive: MASTER PROMPT V9 (28/10/2026, desktop chat) — nâng cấp kho hội
thoại thành hệ trí nhớ có cấu trúc, quan hệ, suy luận có bằng chứng, sàng lọc
theo chu kỳ, hỏi chủ nhân theo cấu trúc A–G, phản hồi có phiên bản.
"""
from __future__ import annotations

import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE / "src"))

from quan_ai_brain.governance.approval_cards import ApprovalCardStore

TASK_CODE = "TASK-V9-DEEP-MEMORY"
TITLE = "V9 — Deep Cognitive Memory & Logical Knowledge Governance Engine"

CARD_MARKDOWN = """[XIN PHÊ DUYỆT] — Mã nhiệm vụ: TASK-V9-DEEP-MEMORY

## 1. Mục tiêu
Chuyển kho lưu trữ hội thoại (brain.db: 1.506 chat_turn phẳng, 1.709 memories,
không có bảng quan hệ) thành hệ trí nhớ chuyên sâu: đơn vị tri thức chuẩn,
quan hệ có căn cứ, suy luận loại A/B/C chống vòng tròn, chu kỳ sàng lọc có
checkpoint, câu hỏi cho chủ theo cấu trúc A–G, phản hồi có phiên bản giữ lịch sử.

## 2. Phạm vi (5 slice theo ưu tiên V9 XV)
- (a) 3 báo cáo audit ĐÃ nộp: V9_DEEP_MEMORY_ACTUAL_STATE_AUDIT,
  V9_MEMORY_DATA_MODEL, V9_DEEP_MEMORY_IMPLEMENTATION_PLAN.
- (b) Slice 1 — deep_memory.py (memory/): 5 bảng mới ADDITIVE trên brain.db
  (knowledge_units, knowledge_relations, memory_exchange_log, memory_review_runs,
  owner_questions) + extractor deterministic từ chat_turns + liên kết có căn cứ
  + trace + API /api/memory/deep/* (localhost-only).
- (c) Slice 2 — logical_reasoning.py (cognition): quy trình 12 bước §V.1,
  kết luận A/B/C, chống vòng tròn suy luận, confidence breakdown 4 thành phần.
- (d) Slice 3 — memory_review_cycle.py: 10 stage COLLECT→REPORT có checkpoint,
  batch limit 50, mâu thuẫn không tự giải → CONFLICTED/NEEDS_OWNER_REVIEW,
  câu hỏi A–G + thông báo NetChat ≤1 tin/đợt.
- (e) Slice 4 — answer_owner_question: phiên bản + SUPERSEDES, trả lời làm rõ
  ≠ phê duyệt production (không đụng approval cards, không đổi R0–R5).
- (f) Slice 5 — UI card "🧠 Deep Memory" trên dashboard (overview/explorer/
  review center/timeline) + executive.js v4.2.

## 3. Tác động & rủi ro
- File mới: memory/deep_memory.py, cognition/logical_reasoning.py,
  cognition/memory_review_cycle.py, tests/test_v9_deep_memory.py, 8 báo cáo V9.
- PATCH: server.py (thêm route), executive.html/js (card mới), cache bump.
- DB: CREATE TABLE IF NOT EXISTS ×5 — KHÔNG ALTER/XOÁ bảng cũ; backup
  brain.db vào backups/ trước lần migrate đầu; rollback = drop 5 bảng mới
  + env kill-switch QUAN_AI_BRAIN_V9_OFF=1.
- Rủi ro: R2 (ghi DB dự án additive). Không đụng governance, không đổi
  quyền hạn, không chạy cycle liên tục (chỉ on-demand).

## 4. Tiêu chí nghiệm thu
- 12 test A–L theo §XIII (mock/tmppath 100%): trích xuất đúng loại, quan hệ
  có basis, mâu thuẫn không tự chọn, suy luận lưu nguồn, câu hỏi A–G, phản
  hồi giữ lịch sử, idempotent, checkpoint resume, không mất dữ liệu,
  truy xuất nhiệm vụ mới, truy vết về nguồn, trả lời ≠ phê duyệt.
- Regression full không suy giảm so với baseline (đang chạy, cập nhật khi xong).
- Live smoke: /api/memory/deep/stats + 1 đợt extract nhỏ trên brain.db thật
  (sau backup) — số liệu thật trong báo cáo, không số minh họa.
- Báo cáo phân biệt DESIGNED/IMPLEMENTED/TESTED/LIVE_VERIFIED/BLOCKED.
"""

def main() -> int:
    store = ApprovalCardStore(WORKSPACE / "data" / "governance.db", workspace=str(WORKSPACE))
    card = store.create_card(
        task_code=TASK_CODE,
        title=TITLE,
        card_markdown=CARD_MARKDOWN,
        risk_level=2,  # R2 — ghi dữ liệu additive vào DB dự án, có backup + rollback
        goal="Deep Cognitive Memory & Logical Knowledge Governance per MASTER PROMPT V9",
    )
    print(f"Card created: {card.request_id} | {card.task_code} | {card.status}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
