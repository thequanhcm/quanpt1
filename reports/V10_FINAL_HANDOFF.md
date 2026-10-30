# V10 — FINAL HANDOFF
**Ngày:** 28/10/2026 · Owner-Gated Memory Review & Knowledge Validation (lệnh `SÀNG LỌC`)

## Trả lời 10 câu hỏi bắt buộc (PHẦN XI)

1. **Lệnh `SÀNG LỌC` đã kết nối backend thật?** ✅ LIVE_VERIFIED — POST `/api/chat` `{"query":"SÀNG LỌC"}` chặn ở đầu `_handle_api_chat` (server.py, trước router LLM), xử lý deterministic 336ms qua `MemoryReviewSession` trên `data/brain.db` thật; KHÔNG gọi LLM, KHÔNG đụng responder/watchdog.
2. **Đợt mẫu xử lý những bản ghi nào?** 20 tri thức (`scope_limit=20`, tiêu chí minh bạch: RULE trước → nhiều quan hệ → trùng lặp; `selection_reason` ghi cho từng bản ghi — PHẦN 3.2). KHÔNG sàng lọc toàn bộ DB.
3. **Bốn nhóm hiển thị đầy đủ?** ✅ GET `/api/memory/review/session` trả units / findings / inferences / questions + changes; UI render 4 khu + khu thay đổi.
4. **Quanpt1 xem nguồn/bằng chứng trực tiếp?** ✅ Mỗi unit có source_refs; finding có evidence + confidence + đề xuất; inference có evidence_refs + assumptions + certainty (INSUFFICIENT_EVIDENCE khi thiếu); question có evidence + phương án.
5. **Phản hồi ghép đúng câu hỏi?** ✅ respond lưu `review_session_id` + `target_id` (question/finding/unit) + kind + text + thời điểm; không đoán từ văn bản tự do.
6. **Cập nhật đúng phạm vi?** ✅ Chỉ change PENDING trong session được confirm; target ngoài session bị từ chối (Test 6); không đụng ngoài 20 KU mẫu (Test 11 live).
7. **Lịch sử trước–sau?** ✅ `review_changes.before_json/after_json`; supersede giữ KU cũ; undo tạo KU v3 RESTORED_BY_UNDO — chuỗi v1→v2→v3 live thật.
8. **Test chạy thế nào?** V10 suite **16/16**; regression full **1169 passed, 1 skipped** (85.32s); live E2E qua 6 API + lệnh chat (chi tiết `V10_OWNER_FEEDBACK_TESTS.md`).
9. **Thay đổi chưa xác minh?** UI mức bấm-nút (IMPLEMENTED — chờ Quanpt1 mở dashboard xác nhận); dấu vết smoke trên brain.db (2 session COMPLETED + 1 change UNDONE) — muốn sạch: restore backup + drop 5 bảng V10, chờ anh quyết, mặc định GIỮ.
10. **Phạm vi được phép sàng lọc?** Mẫu ≤ 200 KU (mặc định 20), CHỈ ĐỌC tới khi anh xác nhận từng change; KHÔNG tự merge/xoá/nâng VERIFIED; mở rộng chỉ khi anh xác nhận quy trình mẫu đạt (PHẦN 8.1 — 9 tiêu chí chưa trình).

## Deliverables
- **Module:** `src/quan_ai_brain/cognition/memory_review_session.py` (877 lines — state machine IDLE→REVIEW_READY→WAITING_OWNER→APPLYING→COMPLETED/FAILED, scope selection có lý do, findings, inferences tái dùng LogicalReasoningEngine, questions A–G có cap 10, respond→preview→confirm→apply→undo, checkpoint stats)
- **API (6 route mới, localhost-only):** GET `/api/memory/review/{current,session}` · POST `/api/memory/review/{respond,confirm,undo,close}`
- **Lệnh chat:** `SÀNG LỌC` (nhận cả "SANG LOC", strip punctuation)
- **UI:** nút `+ Sàng Lọc Trí Nhớ` + panel 4 khu trong tab 🧠 (executive.html/js v4.3)
- **Tests:** `tests/test_v10_memory_review.py` (16 tests map §IX)
- **Reports:** audit · plan · sample results · feedback tests · change audit · test results · handoff (7 file `reports/V10_*.md`)
- **Approval:** card `TASK-V10-OWNER-REVIEW` APPROVED + CONSUMED (governance.db)

## An toàn & rollback
- Backup trước live: `backups/brain_pre_v10_live_20261028.db` (89.710.592 bytes)
- Schema V10: 5 bảng additive (memory_review_sessions, review_findings, review_inferences, review_questions, review_changes) — không ALTER bảng cũ
- R0–R5 giữ nguyên; R5 vẫn chặn; không tự phê duyệt (card do chủ duyệt qua luồng approval hiện có)

## Chờ Quanpt1
1. Mở dashboard → tab 🧠 → bấm **`+ Sàng Lọc Trí Nhớ`** (hoặc nhắn `SÀNG LỌC` trong chat) → xem 4 nhóm → trả lời câu hỏi → preview → xác nhận thay đổi đầu tiên của anh
2. Quyết định dấu vết smoke trên brain.db (giữ = mặc định / làm sạch bằng backup)
3. Sau khi quy trình mẫu được anh xác nhận đạt → em trình kế hoạch mở rộng phạm vi (PHẦN 8.1) — chưa tự làm
4. Duyệt commit `feat(v10)` khi anh sẵn sàng (V9 + V10 cùng working tree, chưa commit)
