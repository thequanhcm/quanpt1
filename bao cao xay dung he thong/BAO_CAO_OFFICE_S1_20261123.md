# BÁO CÁO SPRINT OFFICE-S1 — EMAIL-INTAKE-REAL (card TASK-OFFICE-S1)

**Ngày:** 23/11/2026
**Card:** TASK-OFFICE-S1 — APPROVED + consumed (owner chat directive "duyệt", 23/11/2026)
**Risk:** R1 (đọc email READONLY qua SOAP đã LIVE; không gửi, không xóa, không đổi kiến trúc)
**Nguồn:** master prompt CHERRY OFFICE INTELLIGENCE V1.0 §II + ARCHITECTURE_AUDIT.md gap #1

---

## 1. Mục tiêu
Wire nguồn mail THẬT (Zimbra SOAP) vào pipeline intake hiện có; mở rộng phân loại
5→10 nhóm master prompt §II.2 + Priority/Urgency score + deadline detect; lệnh DM
"email hôm nay" → tóm tắt A/B.

## 2. Phạm vi
- `src/quan_ai_brain/office/__init__.py` (MỚI) + `email_connector.py` (MỚI 383 dòng):
  EmailCategory10, EmailAnalysis (9 trường §II.2), analyze_email() deterministic,
  SOAPMailConnector (interface EmailConnector), sync_and_analyze() (fetch 1 lần),
  format_summary_ab().
- `tools/office_email_sync_runner.py` (MỚI): subprocess runner 110s timeout.
- `tools/netchat_command_center.py` (PATCH): intent `email_today` (COMMAND_PATTERNS
  đặt trước "approve" để không nuốt), handle_email_today(), HANDLERS entry, +import os.

## 3. Danh sách nhiệm vụ
(a) SOAPMailConnector + 10 nhóm phân loại — XONG
(b) Score + deadline explicit/suggested — XONG
(c) Lệnh DM + tóm tắt A/B — XONG
(d) Test mock 100% — XONG (24/24)
(e) Full regression — CHẠY NỀN (bổ sung kết quả sau khi xong)
(f) Live smoke — XONG (thấy dưới)

## 4. Thiết kế kỹ thuật
- Lớp mỏng trên nền Sprint 9: dùng lại EmailIntakeStore (SQLite data/email_intake.db,
  dedupe message_id) + classify_email 5 nhóm cũ cho cột category (tương thích DB);
  phân tích 10 nhóm CHỈ nằm ở lớp office, không đổi DB schema.
- Deadline: chỉ ghi khi pattern NGÀY/GIỜ explicit trúng; từ mờ ("sớm nhất"...) →
  deadline_is_suggested=True (master prompt: không suy diễn khi không nêu rõ).
- Subprocess runner: tránh treo responder khi SOAP chậm (bài học imaplib hang).
- R2 bất biến giữ nguyên: không đánh dấu đã đọc, không xóa, không gửi.

## 5. Kết quả triển khai
- Import + route OK; live smoke thật: "email hôm nay" → **10 email mới** (08:48
  vmail thật), phân loại ACTION_REQUIRED: 5 · MEETING: 3 · APPROVAL: 1 · INFORMATION: 1.
- Chạy lần 2 → dedupe đúng: 0 mới, 10 trùng (không xử lý 2 lần).
- Detect_intent: "email hôm nay"/"kiểm tra email"/"tóm tắt email" → email_today;
  "duyệt email" → approve (không nuốt lẫn — pattern email đặt trước approve).

## 6. Test Evidence
- tests/test_office_email_connector.py — **24/24 PASS** (mock 100%: phân loại 8 nhóm,
  deadline explicit/suggested/không-tự-bịa, score range, sync dedupe, fail-honest
  BLOCKED/exception, format A/B, SOAP connector status/fetch mapping/error).
- tests/test_netchat_command_center.py — **24/24 PASS** (không phá lệnh cũ).
- **Full regression: 15 failed / 4.208 passed / 36 skipped (14:42)** —
  `reports/TEST_RUN_OFFICE_S1.txt`. Baseline 13 failed PRE-EXISTING + 2 fail
  xác minh stash-proof (test_cpsl_runner 13==12, test_ok_confirmation_flow): fail
  KỂ CẢ khi stash patch S1 → do môi trường Pi5 OFFLINE + hardcode count, KHÔNG
  phải do sprint này. **0 fail mới từ Sprint S1.** +32 passed (24 test mới + tăng
  từ các run trước).
- Live smoke: subprocess runner exit 0, 10 mail thật vào store, format A/B đúng.

## 7. Known Issues (trung thực)
- Bảng C "Tổng hợp công việc → task" chưa có (thuộc Sprint 5 Task pipeline) —
  format hiện tại A+B; không fake bảng C.
- "MEETING: 3" là 3 mail [Hủy cuộc họp] cùng nội dung — chưa dedupe nội dung
  gần giống nhau (master prompt §II.2 mục "trùng lặp" — Sprint 1b).
- Urgency của mail RE tiến độ = 0 dù nội dung có bảng tiến độ — classifier
  từ khóa chưa hiểu ngữ cảnh bảng (LLM layer — Sprint 1c).
- KPI master prompt §XV (≥95%) CHƯA ĐO — cần bộ dữ liệu gán nhãn (Sprint 7).

## 8. Security Review
- R2 DRAFT-ONLY giữ nguyên: chỉ Search/GetMsg READONLY.
- Credentials đi vault loader hiện có; KHÔNG log/echo secret.
- Input Injection: DM đi qua input_shield như cũ (trước route); nội dung email
  được render vào DM là DỮ LIỆU KHÔNG TIN CẬY — bản thân nó không được thực thi.
- Audit: route qua _audit() mặc định của command center (netchat_command.*).

## 9. Rollback Plan
- Xóa 3 file mới (office/, office_email_sync_runner.py, test) + revert patch
  netchat_command_center.py (intent email_today + handler + import os) → hệ thống
  về trạng thái Sprint 9 nguyên vẹn. Không có thay đổi DB schema (chỉ thêm rows).

## 10. Đề xuất Sprint tiếp theo
- **Sprint 1b THREAD-ANALYZER**: ghép thread theo subject Zimbra, tổng hợp 10 mục
  §II.4; dedupe nội dung gần giống.
- **Sprint 1c SMART-REPLY-3P**: 3 phương án A/B/C trên email_draft DRAFT-ONLY.
- Sau đó Sprint 2 Document (cài openpyxl/pandas khi duyệt).

---
*Fail-honest: mọi số liệu trong báo cáo này từ output lệnh thật trên máy QUANPT
23/11/2026. Không có mục nào được tuyên bố VERIFIED khi chưa có bằng chứng.*
