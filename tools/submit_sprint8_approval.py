"""Lập card TASK-V3-SPRINT8 — Bộ kỹ năng văn phòng + Approval Center.

Duyệt bởi: quanpt1 qua desktop chat 27/10 ("em triển khai tiếp Sprint 8")
— chỉ thị trực tiếp của owner đủ điều kiện duyệt scope R2 (đã nêu trong
báo cáo tổng thể 27/10: Sprint 8 gồm các hướng này).
"""
from __future__ import annotations

import sys
from pathlib import Path

WORKSPACE = Path(r"E:\AI\QUAN AI BRAIN")
sys.path.insert(0, str(WORKSPACE / "src"))

from quan_ai_brain.governance.approval_cards import ApprovalCardStore

CARD = """# TASK-V3-SPRINT8 — BỘ KỸ NĂNG VĂN PHÒNG + APPROVAL CENTER

**Nguồn:** Kế hoạch Sprint 8 trong BAO_CAO_TONG_THE_AUDIT_KE_HOACH_20261027.md
**Mức rủi ro:** R2 (không tự gửi mail ra ngoài — email chỉ NHÁP có duyệt;
không đụng secret; mọi API mới có test + fail-closed)
**Duyệt bởi:** quanpt1 qua desktop 27/10 ("em triển khai tiếp Sprint 8")

## Hạng mục

**(a) To-do / nhắc việc cá nhân [todo_store.py]**
- SQLite `data/todos.db`: tasks (id, title, due, priority, status, created, done).
- API dashboard: GET/POST /api/todos, POST /api/todos/done.
- Tích hợp responder: lệnh "việc cần làm" → liệt kê; "nhớ giúp tôi ..." → thêm.
- Reminder sáng 8AM gộp vào morning_report (todo quá hạn + hôm nay).

**(b) Nháp email có duyệt [email_draft.py — R2 cẩn trọng]**
- Chỉ TẠO NHÁP .eml trong data/email_drafts/ — KHÔNG gửi, KHÔNG SMTP, KHÔNG COM Outlook.
- Chủ động "soạn email ..." → nháp + card duyệt; owner duyệt mới mở file .eml để anh tự gửi.
- Guard: không đụng địa chỉ nội bộ hệ thống; chờ trống subject → fail-closed.

**(c) Approval Center UI [dashboard 8765]**
- GET /api/approvals → cards (PENDING/APPROVED/...) từ governance.db (đọc-only).
- POST /api/approvals/approve|reject — XÁC THỰC: chỉ chấp nhận khi request
  đi từ localhost + kèm owner_confirm đúng nội dung card (giống consume-once
  chuẩn hiện có; không thêm bypass).
- Tab "Duyệt việc" trên dashboard: danh sách card chờ, nút duyệt/từ chối.

## Ngoài scope (nói rõ)
- Vmail: chờ anh đổi pass SSO + đăng nhập lại (đã lộ pass trong chat).
- Voice 2 chiều: cần thiết kế riêng trên Pi 5, để sprint sau.
- Không cài đặt SMTP/credentials mới — R5 hard-block.

## Tiêu chí nghiệm thu
- +12 test mới (todo 5, email_draft 4, approvals API 3+), regression 780→792+.
- E2E: thêm việc qua NetChat → thấy trong dashboard + báo cáo sáng nhắc.
- E2E: soạn nháp email → file .eml xuất hiện, KHÔNG gửi đi đâu.
- E2E: duyệt card trên dashboard web → card APPROVED consume-once.
"""

store = ApprovalCardStore(WORKSPACE / "data" / "governance.db", workspace=str(WORKSPACE))
card = store.create_card(
    task_code="TASK-V3-SPRINT8",
    title="Sprint 8 — Bộ kỹ năng văn phòng (todo + email nháp) + Approval Center UI",
    card_markdown=CARD,
    risk_level=2,
    goal="Trợ lý quản lý việc cần làm, soạn nháp email có duyệt, duyệt card ngay trên dashboard.",
    params={"sprint": 8, "items": ["todo", "email_draft", "approvals_ui"]},
)
print(f"card_saved: {card.task_code} status={card.status}")
