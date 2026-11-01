"""Lập card TASK-V3-SPRINT10 — Email Intelligence Layer (mock-mode).

Duyệt bởi: quanpt1 qua desktop chat 27/10 ("duyệt card Sprint 10").
Điều kiện trung thực: Vmail thật vẫn BLOCKED (SSO pass chưa đổi) — sprint này
xây lớp thông minh trên connector mock; kích hoạt connector thật = card riêng.
"""
from __future__ import annotations

import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE / "src"))

from quan_ai_brain.governance.approval_cards import ApprovalCardStore

TASK_CODE = "TASK-V3-SPRINT10"
TITLE = "Sprint 10 — Email Intelligence Layer (mock-mode, real connector ready)"

CARD_MARKDOWN = """[XIN PHÊ DUYỆT] — Mã nhiệm vụ: TASK-V3-SPRINT10

## 1. Mục tiêu
Chuyển email tiếp nhận (Sprint 9, mock) thành luồng công việc: email ACTION_REQUIRED
→ đề xuất xử lý có căn cứ → nhiệm vụ ứng viên khi anh bấm duyệt — KHÔNG gửi mail,
KHÔNG chạm Vmail thật (vẫn BLOCKED vì mật khẩu SSO chưa đổi).

## 2. Phạm vi
- (a) Proposal builder (deterministic, không LLM): mỗi email ACTION_REQUIRED có đề xuất
  đủ §VI.3 (mục tiêu/căn cứ/kết luận/giả định/phương án/rủi ro/phạm vi/tiêu chí/rollback/
  quyết định cần anh) + kinh nghiệm liên quan (confirmed vs candidates, từ Sprint 9 D).
- (b) Tạo nhiệm vụ ỨNG VIÊNExplicit: POST /api/email/task/create — chỉ tạo khi anh bấm;
  task PENDING, LEVEL_A (read-only/candidate), idempotent theo message_id (không trùng),
  goal ghi rõ nguồn [EMAIL:mock-xxx]. Không có đường thực thi tự động.
- (c) API + Workbench UI: xem đề xuất, tạo nhiệm vụ ứng viên, hiển thị liên kết task.
- (d) Vmail giữ BLOCKED; hiển thị trung thực điều kiện mở Sprint 11 thật.

## 3. Tác động & rủi ro
- File mới: integration/email_intelligence.py; PATCH email_intake.py (bảng proposals +
  link_task), server.py (3 endpoint), executive.js (UI đề xuất + nút tạo task).
- Rủi ro thấp: ghi mức R2 trong workspace; task ứng viên PENDING không tự chạy
  (LEVEL_A + WAITING_APPROVAL gate giữ nguyên); không LLM (deterministic).
- Rollback: git revert; endpoint mới tách biệt, backward-compat.

## 4. Tiêu chí nghiệm thu
- Proposal đủ 11 trường §VI.3; mock source ghi rõ trong giả định.
- Sync/generate lặp lại không tạo trùng proposal; tạo task 2 lần cùng email → cùng task_id.
- Email FYI/NEWSLETTER không tạo đề xuất/nhiệm vụ.
- Kinh nghiệm chưa xác nhận xuất hiện ở mục "ứng viên, chưa duyệt", không đếm là căn cứ mạnh.
- Vmail vẫn BLOCKED; không có đường gửi; regression sạch.
"""

if __name__ == "__main__":
    store = ApprovalCardStore(WORKSPACE / "data" / "governance.db", workspace=str(WORKSPACE))
    card = store.create_card(TASK_CODE, TITLE, CARD_MARKDOWN)
    print(f"card_saved: {TASK_CODE} status={card.status}")
