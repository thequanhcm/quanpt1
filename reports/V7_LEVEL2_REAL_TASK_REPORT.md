# V7 LEVEL 2 REAL TASK REPORT — 27/10/2026

**Phạm vi:** Cấp 2 (EXECUTION — Làm được việc) trên bài toán "email yêu cầu kiểm tra tiến độ"
**Kết luận hiện tại:** `LEVEL_2_PARTIAL` — pipeline đầu-cuối đã chạy được trên dữ liệu thật của hệ thống (58 bản ghi từ tasks.db + todos.db), nhưng **chưa có bài nghiệm thu với email thật do Quanpt1 cung cấp**.

## 1. Bằng chứng đã có (rehearsal trên dữ liệu thật được cấp quyền)

- **Live qua `/api/chat`** (không phải unit test): query "Kiểm tra tiến độ các công việc hiện tại giúp tôi" → chain 4 skill chạy thật trên server production:
  - `sources_accessed`: `data/tasks.db (read-only)`, `data/todos.db (read-only)`
  - `records_matched`: 58 bản ghi công việc thật
  - `conclusion`: RECONCILED_WITH_LIMITS
  - `risk_summary`: 0 risks (không có deadline trong DB để xếp), **116 unknowns** (owner/deadline/progress thiếu — ghi trung thực KHÔNG đoán)
  - `report_md`: báo cáo tư vấn 12 mục đầy đủ (1798 chars), mỗi kết luận có nguồn, mục 11 liệt kê nguồn chưa truy cập, mục 12 ghi giới hạn tin cậy.
- **Read-only chứng minh**: các skill chỉ SELECT; không có ghi/sửa/gửi nào.

## 2. Thực hiện theo 5 bước §4.2 (A→E)

| Bước | Trạng thái | Ghi chú |
|------|-----------|---------|
| A — Phân tích yêu cầu | ✅ (rehearsal) | 8 trường trích từ chat query; email thật chờ chủ cung cấp |
| B — Xác định nguồn | ✅ (rehearsal) | 2 nguồn DB truy cập; Vmail/Outlook BLOCKED ghi rõ; không giả định nguồn đã kết nối |
| C — Hợp nhất dữ liệu | ✅ (rehearsal) | unified_records với UNKNOWN/NOT_VERIFIED đúng chỗ; không tự tạo % tiến độ |
| D — Đối chiếu chéo | ⚠️ một phần | Cơ chế mâu thuẫn có (test thật: email vs DB), nhưng rehearsal chưa có email claim nào để đối chiếu |
| E — Phân tích & tư vấn | ✅ (rehearsal) | 12 mục đầy đủ; KHÔNG tự gửi email/sửa task (report_only) |

## 3. Bài toán nghiệm thu thật — chờ Quanpt1 (KHÔNG tự nâng trạng thái)

Để chuyển `LEVEL_2_PARTIAL` → `LEVEL_2_PASSED`, cần chủ cung cấp **một email yêu cầu kiểm tra tiến độ thực tế** (dán nguyên văn vào chat hoặc lưu file vào workspace — không cần quyền Vmail):

Chủ chỉ cần gửi: *"Kiểm tra tiến độ theo email này: [dán email]"* — hệ thống sẽ:
1. Phân tích email (8 trường + cam kết + câu hỏi).
2. Đối chiếu với tasks.db/consultations.db/todos.db/reports/.
3. Phát hiện mâu thuẫn email-vs-DB, quá hạn, thiếu trách nhiệm.
4. Trả báo cáo tư vấn 12 mục có truy vết nguồn.

## 4. Điều kiện nghiệm thu Cấp 2 — đối chiếu trung thực

| # | Điều kiện | Trạng thái |
|---|-----------|-----------|
| 1 | Bài toán thực tế được cấp quyền | ⏳ chờ email thật từ chủ |
| 2 | Dữ liệu thật trong phạm vi phép | ✅ (rehearsal 58 records) |
| 3 | Kết quả truy vết nguồn | ✅ evidence_refs từng bản ghi |
| 4 | Mâu thuẫn phát hiện/giới hạn ghi rõ | ✅ cơ chế + unknowns trung thực |
| 5 | Không trình bày suy đoán như sự thật | ✅ UNKNOWN/NOT_VERIFIED |
| 6 | Báo cáo trả lời mục tiêu ban đầu | ✅ 12 mục |
| 7 | Tiêu chí chất lượng + đánh giá | ⏳ cần bài nghiệm thu thật |
| 8 | Không hành động ngoài phê duyệt | ✅ report_only |

## 5. Khác biệt so với plan

- Plan đề xuất chạy bài toán 1 trước Cấp 3 — **đúng lộ trình, chưa hoàn thành phần "email thật"** vì nguồn email thật bị chặn và chủ chưa cung cấp email thay thế.
- Đã tự động dừng ở `PARTIAL` đúng §4.3 — không tự phong PASSED.

---
*Cập nhật: khi chủ cung cấp email thật, chạy lại chain + lưu bằng chứng vào reports/V7_LEVEL2_REAL_TASK_REPORT.md (phần Bài toán 1).*
