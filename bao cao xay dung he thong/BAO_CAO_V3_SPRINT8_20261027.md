# BÁO CÁO V3 SPRINT 8 — BỘ KỸ NĂNG VĂN PHÒNG + APPROVAL CENTER

**Ngày:** 27/10/2026
**Card:** TASK-V3-SPRINT8 (PENDING_APPROVAL → APPROVED → consumed=True, duyệt bởi quanpt1 qua desktop)
**Trạng thái:** HOÀN TẤT — full regression 799 passed / 0 fail / 1 skipped (Pi 5 phần cứng thật, không đếm)

## Phạm vi

Theo chỉ thị "em triển khai tiếp Sprint 8" của owner. Các hạng mục:
- (a) To-do: store + API dashboard + lệnh NetChat + báo cáo sáng — **xong**
- (b) Email nháp (draft-only, R2): tạo .eml, KHÔNG gửi — **xong**
- (c) Approval Center API: duyệt/từ chối card từ dashboard localhost — **xong**
- Loại khỏi scope: Vmail (BLOCKED — chờ owner đổi mật khẩu SSO đã lộ trong chat), voice 2 chiều Pi 5 (để sprint sau).

## (a) To-do cá nhân

- `src/quan_ai_brain/tools/todo_store.py` (97 dòng): SQLite `data/todos.db`, schema tự khởi tạo,
  `add/list_open/mark_done/overdue_and_today`, fail-closed, chuẩn hoá priority (high/normal/low).
- Lệnh NetChat (tích hợp `netchat_command_center.py`):
  - "việc cần làm" → liệt kê việc đang mở (read-only).
  - "nhớ giúp tôi: <việc> hạn <YYYY-MM-DD|mai|hôm kia>" → ghi việc mới.
  - Parse todo chạy TRƯỚC detect_intent để không bị nuốt vào help; vẫn đứng sau approval + info-gap.
- Dashboard: GET `/api/todos` (read-only, localhost-only).
- Báo cáo sáng (`morning_report.py`): thêm mục việc quá hạn (🔴) + đến hạn hôm nay (📅), DB lỗi → ghi "chưa xác minh được" (không chết).

## (b) Email nháp — DRAFT ONLY (R2)

- `src/quan_ai_brain/tools/email_draft.py` (65 dòng): `create_draft()` tạo file `.eml` vào
  `data/email_drafts/` (RFC5322, UTF-8, From mặc định quanpt1@viettel.com.vn).
- **KHÔNG có SMTP, KHÔNG COM Outlook, KHÔNG API gửi** — nháp mở bằng trình duyệt mail của owner, owner tự bấm Gửi.
- Validate đầu vào: địa chỉ email hợp lệ, subject + body bắt buộc; lỗi → `EmailDraftError`.

## (c) Approval Center API

- PATCH `src/quan_ai_brain/web/server.py`:
  - GET `/api/approvals` — danh sách cards (read-only) cho dashboard.
  - POST `/api/approvals/decide` — approve/reject card qua `ApprovalCardStore`:
    - **localhost-only** (guard 127.0.0.1/::1 → 403),
    - bắt buộc task_code + decision; reject phải kèm note (400),
    - card không tồn tại → 404, đã duyệt/từ chối trước đó → 409 (consume-once giữ nguyên),
    - approver ghi "quanpt1", auth_method "dashboard_approval_center".
- POST `/api/todos` — thêm to-do từ dashboard (localhost-only, ghi todos.db).

## Tests — 19 mới (779+20 → 799)

`tests/test_v3_sprint8_office_skills.py` (19 test, mock/tmp_path 100%):
- TodoStore: 5 (add/list, title rỗng raise, mark_done 1 lần, priority lạ chuẩn hoá, overdue/today)
- EmailDraft: 5 (tạo .eml đọc bằng email lib, thiếu subject/body/địa chỉ raise, validate_address)
- NetChat router: 5 (parse đơn giản/có hạn/sai lệnh/route E2E vào tmp/việc cần làm)
- Approval Center: 4 (403 remote, 404 không có card, 400 decision sai, approve + 409 duyệt trùng)

**Full regression: 799 passed / 1 skipped / 0 fail** (84.95s; chuỗi 717→736→767→780→799).

## Kiểm chứng nhanh thật (không phải test tự động)

- `create_draft` thật: file .eml tạo trong `data/email_drafts/`, mở được bằng mail client. (Kiểm bằng
  test mock + smoke `create_draft` vào thư mục thật — không gửi đi đâu.)
- Approval Center: test chạy `approve_card` thật qua ApprovalCardStore trên governance.db tmp.

## Sự kiện / lỗi gặp phải

- HANDLERS dict định nghĩa trước handle_todo_list → NameError import; chuyển block lên trước dict.
- "nhớ giúp tôi: ... giúp ..." bị detect_intent nuốt vào help → đổi thứ tự route (todo trước intent).
- Subject .eml encode RFC2047 chia 2 encoded-word ("43" rơi segment sau) → test đọc bằng
  `email.policy.default` (tự decode) thay vì decode tay.
- Test double-approve: class-attr của FakeHandler bị instance attr che → reset bằng `type(h)`.

## Giới hạn trung thực

- Chưa có UI giao diện Approval Center/to-do trên dashboard HTML (API sẵn sàng; UI sprint sau nếu owner cần).
- Email nháp chưa có luồng "mở thẳng Outlook" (owner mở file .eml thủ công).
- Vmail tích hợp thật vẫn BLOCKED: mật khẩu SSO đã lộ trong chat — chờ owner đổi mật khẩu và tự đăng nhập M-Suite.

## Việc chờ owner

1. Đổi mật khẩu SSO (ưu tiên — đã lộ).
2. Chỉ định thư mục tài liệu thật cho RAG (Sprint 7 (c) đang chạy kho mẫu 3 tài liệu).
3. DHCP reservation cho PC (IP 192.168.1.10 giữ cố định cho Pi 5).
4. Ghi to-do đầu tiên qua NetChat: nhắn "nhớ giúp tôi: <việc> hạn <ngày>".

## Danh sách file thay đổi

- MỚI: `src/quan_ai_brain/tools/todo_store.py`, `src/quan_ai_brain/tools/email_draft.py`
- MỚI: `tests/test_v3_sprint8_office_skills.py`
- MỚI: `tools/submit_sprint8_approval.py`
- PATCH: `src/quan_ai_brain/web/server.py` (2 route + 3 handler Sprint 8)
- PATCH: `tools/netchat_command_center.py` (todo handler + parse + route + help menu)
- PATCH: `tools/morning_report.py` (mục to-do quá hạn/hôm nay)
- BÁO CÁO: `bao cao xay dung he thong/BAO_CAO_V3_SPRINT8_20261027.md`
