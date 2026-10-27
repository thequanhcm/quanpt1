"""Submit approval card for V10 — Owner-Gated Memory Review & Knowledge Validation.

Owner directive: MASTER PROMPT V10 (28/10/2026, desktop chat) — "hãy phát triển
trực tiếp trên hệ thống QUAN AI BRAIN hiện có": lệnh SÀNG LỌC tạo đợt review
mẫu có ID, phân tích CHỈ ĐỌC, hiển thị 4 nhóm kết quả trên giao diện, chờ phản
hồi chủ nhân, cập nhật đúng phạm vi xác nhận, lưu lịch sử trước–sau.
"""
from __future__ import annotations

import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE / "src"))

from quan_ai_brain.governance.approval_cards import ApprovalCardStore

TASK_CODE = "TASK-V10-OWNER-REVIEW"
TITLE = "V10 — Owner-Gated Memory Review & Knowledge Validation"

CARD_MARKDOWN = """[XIN PHÊ DUYỆT] — Mã nhiệm vụ: TASK-V10-OWNER-REVIEW

## 1. Mục tiêu
Lệnh `SÀNG LỌC` (chat + nút UI "+ SÀNG LỌC TRÍ NHỚ") tạo một đợt sàng lọc mẫu
có review_session_id duy nhất: phân tích CHỈ ĐỌC một tập dữ liệu giới hạn
(≤20 tri thức, tiêu chí chọn minh bạch ghi lại từng lý do), hiển thị 4 nhóm
bắt buộc (tri thức đang lưu / quan hệ & mâu thuẫn / suy luận & bằng chứng /
câu hỏi cho chủ), chờ phản hồi Quanpt1, chỉ cập nhật đúng phạm vi được xác
nhận, lưu lịch sử trước–sau và có khả năng hoàn tác. KHÔNG tự động sửa toàn
bộ trí nhớ; KHÔNG mở rộng phạm vi khi chưa có xác nhận của chủ.

## 2. Phạm vi
- (a) 2 báo cáo audit/plan: V10_MEMORY_REVIEW_AUDIT, V10_MEMORY_REVIEW_IMPLEMENTATION_PLAN.
- (b) Module mới cognition/memory_review_session.py: 5 bảng ADDITIVE
  (memory_review_sessions, review_findings, review_inferences,
  review_questions, review_changes) + selection minh bạch + phân tích
  chỉ-đọc + response handler 9 loại + apply có confirm + before/after.
- (c) server.py: +5 API /api/memory/review/* (start/session/respond/apply/
  close) + route lệnh SÀNG LỌC ở đầu /api/chat (exact match).
- (d) executive.html/js: panel Sàng Lọc trong tab 🧠 V9 (trạng thái 8 giá trị,
  4 khu nội dung, phản hồi từng mục, preview before/after trước khi áp).
- (e) tests/test_v10_memory_review.py: 13 test §IX.
- (f) 5 báo cáo kết quả + handoff.
- Tái sử dụng: LogicalReasoningEngine (nhóm suy luận), supersede_unit V9
  (version+1 SUPERSEDES giữ lịch sử), _tokens/_jaccard (so trùng).

## 3. Tác động & rủi ro
- File mới: cognition/memory_review_session.py, tests/test_v10_memory_review.py,
  7 báo cáo V10. PATCH: server.py, executive.html/js.
- DB: CREATE TABLE IF NOT EXISTS ×5 — additive, không ALTER bảng nào,
  không đụng dữ liệu V9/legacy; backup brain.db trước live sample review.
- Phân tích CHỈ ĐỌC cho đến khi chủ xác nhận từng thay đổi; thay đổi quan
  trọng cần preview before/after rồi confirm lần 2 mới áp.
- Rủi ro: R2 (ghi DB additive + ghi tri thức có xác nhận hai bước).
- KHÔNG: tự duyệt, tự mở rộng phạm vi, tự hợp nhất/xoá, đụng R0–R5,
  restart server production 8216.

## 4. Tiêu chí nghiệm thu (13 test §IX)
1 session_id duy nhất + phạm vi rõ · 2 đủ 4 nhóm từ dữ liệu thật · 3 truy
được nguồn · 4 không sửa DB trước xác nhận (trừ bảng vận hành review) ·
5 phản hồi ghép đúng question_id · 6 cập nhật đúng phạm vi · 7 before/after
truy được · 8 NO_DECISION giữ trạng thái chờ · 9 lệnh 2 lần không tạo đợt
trùng · 10 phục hồi sau gián đoạn · 11 không vượt cap mẫu · 12 integrity
trước=sau · 13 số liệu UI khớp backend. Regression không suy giảm.
"""

def main() -> int:
    store = ApprovalCardStore(WORKSPACE / "data" / "governance.db", workspace=str(WORKSPACE))
    card = store.create_card(
        task_code=TASK_CODE,
        title=TITLE,
        card_markdown=CARD_MARKDOWN,
        risk_level=2,
        goal="Owner-gated sample memory review per MASTER PROMPT V10",
    )
    print(f"Card created: {card.request_id} | {card.task_code} | {card.status}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
