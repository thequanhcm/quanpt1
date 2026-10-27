# V10 — SAMPLE REVIEW RESULTS (LIVE SMOKE)
**Ngày:** 28/10/2026 · Đợt sàng lọc mẫu chạy THẬT trên `data/brain.db` (sau backup `backups/brain_pre_v10_live_20261028.db`, 89.710.592 bytes)
**Server test riêng:** port 8799 (không đụng server production PID 8216 — đang chạy code cũ, 404 trên API V10 là đúng)

## 1. Đợt sàng lọc 1 — `rev_51dee1568d8a` (khảo sát ban đầu)
- Lệnh: POST `/api/chat` `{"query":"SÀNG LỌC"}` → **336 ms**, `model: deterministic-review` (KHÔNG gọi LLM)
- Trạng thái: `REVIEW_READY`
- Phạm vi mẫu: **20 tri thức** (scope_limit=20, tiêu chí minh bạch: RULE trước → nhiều quan hệ → trùng lặp; có `selection_reason` từng bản ghi)
- Phát hiện: **38** (DUPLICATE jaccard, MISSING_RELATION, CONTRADICTION…) — ví dụ `DUPLICATE k_45d6541a0245 ↔ k_e76f38c9e25f jaccard=1.00`
- Suy luận: **3** (`UNVERIFIED_INFERENCE`, kèm evidence_refs + assumptions — trung thực về mức chắc chắn)
- Câu hỏi: **32** → **điều chỉnh về cap 10** (PHẦN IV: "không tạo câu hỏi chỉ để tăng số lượng")
- Chống lặp: gọi `SÀNG LỌC` lần 2 → `already_open: True`, cùng `session_id` ✅
- Chỉ-đọc: knowledge_units + knowledge_relations KHÔNG đổi sau phân tích ✅

## 2. Đợt sàng lọc 2 — `rev_e2991750498b` (cap 10 câu hỏi, phản hồi đầy đủ)
- Questions: **10** (cap hoạt động; ưu tiên CONTRADICTION → MISSING_RELATION → DUPLICATE, theo confidence)
- Luồng phản hồi thật:
  1. `respond` q_2ae60852cfa3 (CLARIFY) → change `chg_17f7a8a22571` PENDING target `k_45d6541a0245` ✅ ghép đúng question_id
  2. `preview` → before/after + `requires_second_confirm: True` ✅
  3. `confirm=True` → **APPLIED, supersede**: v1 `k_45d6541a0245` → SUPERSEDED; KU kế nhiệm v2 `k_6fb0b4832e89` (derived_from=[old]) ✅
  4. `undo` → **restored_as `k_e2636cae13cc` v3** (EXTRACTED, derived_from=[v2]) — chuỗi v1→v2→v3 giữ đủ lịch sử, không mất dữ liệu ✅
  5. change đánh dấu `UNDONE` sau khi sửa code (trước đó chạy thật khi code còn ghi APPLIED — đã đồng bộ trạng thái DB minh bạch, ghi nhận ở §5)

## 3. Bảo toàn dữ liệu
- `PRAGMA integrity_check` = **ok** trước và sau toàn bộ luồng
- Episodes nguồn: 1.659 — không đụng ngoài phạm vi mẫu; không sàng lọc toàn bộ DB
- Sau smoke: cả 2 session smoke **đã đóng** → `/api/memory/review/current` = `IDLE` — UI sẵn sàng cho lệnh `SÀNG LỌC` thật đầu tiên của Quanpt1

## 4. Hiệu chỉnh giữa 2 đợt (học từ live)
1. Handler `current` query bảng V10 trước khi schema tồn tại → chuyển qua `MemoryReviewSession` (constructor tự `_create_schema` idempotent)
2. Sai tên cột `started_at_utc` → schema thật dùng `created_at_utc` — đã đồng bộ
3. Cap câu hỏi 10 + thứ tự ưu tiên — tránh hỏi dồn dập

## 5. Trung thực về dấu vết smoke trên DB thật
- 2 session review (đã COMPLETED), ~40 findings, 10 questions, 1 change UNDONE, chuỗi supersede v1→v2→v3 của 1 KU nội dung "Anh Quân — Quanpt1, chủ sở hữu của em." — đây là DẤU VẾT THỬ NGHIỆM, nội dung tri thức không thay đổi nghĩa (restore đúng nội dung gốc)
- 5 bảng V10 nằm additive trong brain.db; nếu muốn xoá sạch dấu vết: restore từ `backups/brain_pre_v10_live_20261028.db` + drop 5 bảng V10 (đề xuất, chờ Quanpt1 quyết)
