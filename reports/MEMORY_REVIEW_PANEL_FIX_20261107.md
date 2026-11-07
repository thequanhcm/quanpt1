# FIX: Sàng Lọc Trí Nhớ (Owner-Gated) — 07/11/2026

## Lỗi owner báo (ảnh dashboard 8766)
Panel "🔎 Sàng Lọc Trí Nhớ (Owner-Gated)" hiển thị chữ đỏ:
`Lỗi tải: Unexpected token '<', "<!DOCTYPE"... is not valid JSON`

## Root cause (2 tầng)

**Tầng 1 — 5 route API thiếu hoàn toàn trong server.py:**
Frontend V10 (`executive.js`) gọi:
- `GET  /api/memory/review/current`
- `GET  /api/memory/review/session?session_id=…`
- `POST /api/memory/review/respond`
- `POST /api/memory/review/confirm` (preview + apply)
- `POST /api/memory/review/undo`

Backend `MemoryReviewSession` (cognition/memory_review_session.py) đã HOÀN CHỈNH
và đã có 16 test pass từ V10 Sprint — nhưng **không ai viết cầu nối route** trong
server.py. Request rơi vào 404 HTML mặc định của http.server → `res.json()`
thất bại → đúng thông báo `<!DOCTYPE... is not valid JSON`.

**Tầng 2 — nút "+ Sàng Lọc Trí Nhớ" gọi sai endpoint:**
`startReview()` POST `/api/chat` với query "SÀNG LỌC" → LLM trả lời tự do,
**không tạo session review**. Đổi sang POST `/api/memory/review/start`
(lệnh máy, không phụ thuộc LLM).

**Tầng phụ — server 8765/8766 chạy code cũ (PID 20796 pythonw từ start_dual_servers.py)
không bị restart bởi filter python.exe** → phải kill đúng PID + spawn lại venv python.

## Fix
1. `web/server.py`: import MemoryReviewSession + 6 route (thêm `/start`) + 6 handler:
   - start: tạo đợt (chỉ đọc) — scope_limit 1–200, mặc định 20
   - current: find_open_session
   - session: payload 4 nhóm (units/findings/inferences/questions + changes)
   - respond: ghi phản hồi owner + build change PENDING
   - confirm: preview_only=true → trước/sau; confirm=true → áp dụng (bước 2)
   - undo: APPLIED → undo_change; PENDING/PREVIEWED → cancel_change (nút "✖ Bỏ")
2. `web/static/executive.js`: nút gọi `/api/memory/review/start` trực tiếp.
3. Restart đúng quy trình server dual 8765+8766.

## Bảo đảm owner-gated (không đổi so với thiết kế V10)
- Phân tích CHỈ ĐỌC: không ghi knowledge_units khi start/respond
- Thay đổi chỉ ghi sau: respond → change PENDING → preview (trước/sau) → confirm lần 2
- Lịch sử before/after trong review_changes + undo không phá dữ liệu

## E2E thật (server 8766, DB brain.db)
1. `POST /api/memory/review/start` → `rev_77e4b6aa98f9` REVIEW_READY ✓
2. `GET current` → trả session đang mở ✓
3. `GET session` → 20 units / 38 findings / 3 inferences / 10 questions ✓
4. respond CLARIFY → change `chg_…` PENDING ✓
5. preview → before/after + requires_second_confirm=True ✓
6. abandon PENDING → CANCELLED (không ghi tri thức) ✓
7. close → COMPLETED; current → null (IDLE) ✓
8. Tests: test_v10_memory_review + test_v9_memory_review_cycle → **24/24 PASS**
9. node --check executive.js OK; py_compile server.py OK

## Kết quả cho owner
Panel "Sàng Lọc Trí Nhớ" trên dashboard 8766 hoạt động lại: bấm
"+ Sàng Lọc Trí Nhớ" tạo đợt mẫu thật (chỉ đọc), 4 nhóm hiển thị, phản hồi từng
mục, preview trước/sau, xác nhận lần 2 mới ghi, hoàn tác được.
