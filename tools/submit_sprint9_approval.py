"""Lập card TASK-V3-SPRINT9 — Digital Employee Workbench & Experience Intelligence.

Duyệt bởi: quanpt1 qua MASTER PROMPT V3 SPRINT 9 (desktop chat 27/10) — phạm vi
§III (Workbench), §IV (Email workflow draft-only + intake adapter), §VI (Intelligence
context/retrieval), §VII (Experience memory tái sử dụng), §VIII (Governance giữ nguyên).

Scope ĐÃ DUYỆT (rút từ master prompt, phần khả thi + an toàn):
  (A) Overview API /api/workbench/overview — tổng hợp THẬT từ task registry,
      consultation, todos, approvals, service health; lỗi → CHƯA XÁC MINH.
  (B) Workbench UI trong executive dashboard: tab Workbench (overview + nhiệm vụ
      + Approval Center hoàn chỉnh + to-do) dùng API hiện có, đúng trạng thái DB.
  (C) Email intake adapter: interface + MOCK connector (Vmail giữ BLOCKED — master
      prompt §IX), phân loại + chống trùng; email_draft thêm liên kết task/nguồn.
  (D) Experience retrieval: find_similar_experiences từ memory store HIỆN CÓ,
      tích hợp context builder làm nguồn tham chiếu — KHÔNG tạo quyền thực thi.

KHÔNG nằm trong scope: gửi email thật, web connector thật thao tác ngoài, sprint 10-13,
sửa ApprovalGate/PolicyEngine/R5, tự duyệt tri thức quarantine.
"""
from __future__ import annotations

import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE / "src"))

from quan_ai_brain.governance.approval_cards import ApprovalCardStore

TASK_CODE = "TASK-V3-SPRINT9"
TITLE = "Sprint 9 — Digital Employee Workbench & Experience Intelligence"

CARD_MARKDOWN = """[XIN PHÊ DUYỆT] — Mã nhiệm vụ: TASK-V3-SPRINT9

## 1. Mục tiêu
Hoàn thiện môi trường làm việc thống nhất (Workbench) cho nhân sự số trên dashboard
hiện có, kết nối kỹ năng văn phòng với nhận thức/phê duyệt/kinh nghiệm — theo
MASTER PROMPT V3 SPRINT 9 của quanpt1 (27/10).

## 2. Phạm vi được đề xuất
- (A) GET /api/workbench/overview: số liệu THẬT từ data/tasks.db + consultations.db
  + todos.db + governance.db + service probe. DB/API lỗi → "CHƯA XÁC MINH", không điền 0.
- (B) Tab Workbench trong static/executive.html: tổng quan + danh sách nhiệm vụ
  (đúng trạng thái DB: NEEDS_OWNER_INPUT / WAITING_FOR_OWNER_APPROVAL / IN_PROGRESS /
  WAITING_FOR_VERIFICATION / DONE...), Approval Center UI (duyệt/từ chối consume-once,
  reject bắt buộc lý do, chống double-submit, hiển thị 409/404 trung thực),
  to-do UI (list/add/done, chống trùng). Localhost-only — nói đúng giới hạn.
- (C) Email intake adapter: interface + MockEmailConnector (read-only, dedupe theo
  message_id, phân loại 4 nhóm) + draft .eml gắn metadata task_id/nguồn/lý do.
  Vmail thật: GIỮ BLOCKED (§IX — mật khẩu SSO đã lộ, chờ owner đổi).
- (D) find_similar_experiences(task_context) trên memory store hiện có (episodic
  lessons đã xác nhận) — nguồn tham chiếu cho đề xuất, KHÔNG phải quyền thực thi;
  chưa xác nhận → đánh dấu "ứng viên, chưa duyệt".

## 3. Tác động & rủi ro
- Thay đổi: web/server.py (+2 API), static/executive.html (+1 tab), cognition/context_builder.py
  (mở rộng, không thay đổi hành vi cũ), tools/email_draft.py (+metadata), module mới
  integration/email_intake.py + memory experience retrieval helper.
- Rủi ro thấp: chỉ đọc + ghi mức R2 trong workspace; UI dùng API có sẵn; không đụng
  ApprovalGate/PolicyEngine/R5; không gửi mail; không ra ngoài localhost.
- Rollback: git revert từng commit; API mới tách biệt, không phá API cũ (backward-compat).

## 4. Tiêu chí nghiệm thu
- Dashboard đọc số liệu thật từ API (không số giả); DB lỗi → CHƯA XÁC MINH.
- Duyệt trùng → 409 không kích hoạt lần 2; reject không đổi sang APPROVED; card không
  tồn tại → 404 hiển thị trung thực.
- To-do lưu/khôi phục đúng; không tạo trùng khi bấm 2 lần.
- Email mock connector không xử lý trùng; draft KHÔNG gửi; Vmail vẫn BLOCKED.
- Kinh nghiệm chưa xác nhận không được coi là quy tắc đã duyệt.
- R5 hard-block + consume-once giữ nguyên; regression sạch, test mới có mock rõ ràng.
"""
CARD_VERSION = 1

if __name__ == "__main__":
    store = ApprovalCardStore(
        WORKSPACE / "data" / "governance.db", workspace=str(WORKSPACE)
    )
    card = store.create_card(TASK_CODE, TITLE, CARD_MARKDOWN)
    print(f"card_saved: {TASK_CODE} status={card.status}")
