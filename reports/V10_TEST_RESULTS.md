# V10 — TEST RESULTS
**Ngày:** 28/10/2026

## Tổng hợp
| Hạng mục | Kết quả | Bằng chứng |
|---|---|---|
| V10 test suite (13 test §IX + 3 bổ sung) | **16/16 PASS** | `tests/test_v10_memory_review.py` |
| Regression toàn bộ sau V10 | **1169 passed, 1 skipped** (85.32s) | = 1153 (V9) + 16 (V10), 0 vỡ |
| Live E2E lệnh `SÀNG LỌC` | **LIVE_VERIFIED** | `rev_51dee1568d8a` (336ms) + `rev_e2991750498b` trên brain.db thật, port 8799, sau backup 89.7MB |
| Supersede + Undo giữ lịch sử | **LIVE_VERIFIED** | chuỗi v1 `k_45d6541a0245` → v2 `k_6fb0b4832e89` → v3 `k_e2636cae13cc` (RESTORED_BY_UNDO) |
| DB integrity | ok trước = sau | PRAGMA integrity_check |
| UI (nút + panel 4 khu + phản hồi + preview/confirm/undo) | IMPLEMENTED (JS node --check OK) | chờ Quanpt1 bấm xác nhận → LIVE |
| Chống lặp live | LIVE_VERIFIED | lần 2 `already_open: True` cùng session_id |
| Chỉ-đọc trước xác nhận | LIVE_VERIFIED | KU/relations nguyên vẹn sau phân tích |

## Hiệu chỉnh giữa chặng (học từ live, đã fix + test lại)
1. Handler query bảng V10 khi schema chưa có → `MemoryReviewSession.__init__` tự `_create_schema()` idempotent
2. `started_at_utc` → `created_at_utc` (đồng bộ schema thật)
3. Cap câu hỏi 32 → 10 (PHẦN IV) + ưu tiên CONTRADICTION trước
4. `undo_change` giờ đánh dấu `confirm_state='UNDONE'` (trước chỉ ghi result)

## Trạng thái trung thực
- TESTED + LIVE (backend): khởi tạo, 4 nhóm, phản hồi, phạm vi, lịch sử, chống lặp, phục hồi, integrity, undo
- IMPLEMENTED chờ LIVE: UI mức bấm-nút-thật của Quanpt1
- KHÔNG ĐỤNG: server production PID 8216 (code cũ — 404 trên API V10 là đúng), episodes, bảng V9
