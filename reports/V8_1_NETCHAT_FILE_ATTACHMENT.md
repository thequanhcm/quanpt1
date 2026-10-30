# V8.1 — NETCHAT FILE ATTACHMENT (đọc file đính kèm trong kênh chat)
**Ngày:** 28/10/2026 · Yêu cầu chủ: ảnh image_5eff09 — gửi PDF "KV1 Ke hoach dao tao lan toa AI thuc 1382026.pdf" kèm lệnh "đọc và tóm tắt" → bot trả lời "Anh chưa đính kèm file nào" (bug).

## Root cause (audit)
1. `tools/netchat_auto_responder.py` chỉ đọc `msg["message"]` (text) — bỏ qua `file_ids` hoàn toàn.
2. Khi vá xong phát hiện lỗi lớp 2: server guard `/api/chat` chặn query > 5000 ký tự → prompt chứa nội dung PDF 18K ký tự bị từ chối (HTTP 500) dù file đã vào prompt.

## Triển khai (chỉ sửa trong workspace, stdlib)
| Thành phần | Chi tiết |
|---|---|
| `extract_message_files()` | file_info → download (≤20MB) → trích xuất; PDF/DOCX chạy qua subprocess venv agent (có sẵn pypdf/python-docx — KHÔNG thêm dependency vào pyproject); text thuần đọc trực tiếp. Lỗi từng file → ghi chú inline (fail-honest). |
| Lưu file | `data/netchat_files/<file_id>.<ext>` (thư mục đã gitignore), tái sử dụng khi file đã tải. |
| `_summarize_via_map_reduce()` | Tài liệu >5000 ký tự: chia phần ≤4300 (dòng đơn cắt cứng), tóm tắt dồn tuần tự (budget động ≤4800/prompt), reduce cuối kẹp ≤3800 tóm tắt + trả lời câu hỏi thật. |
| Router bypass | Tin có tài liệu → bỏ qua command router (lệnh hệ thống không đi kèm file). |
| Chống trùng sau restart | `data/netchat_responder_state.json` lưu message_id đã trả lời (≤2000); restart nạp lại → KHÔNG trả lời lại tin cũ (trước đây catchup 60' gây spam trùng). Cửa sổ catchup 60'→45'. |
| Timeout | `/api/chat` call 60s→120s (prompt dài). |

## Bằng chứng LIVE (file thật của chủ)
- Extract: `KV1 Ke hoach dao tao lan toa AI thuc 1382026.pdf` — 8 trang → 18.037 ký tự tiếng Việt.
- Map-reduce: 5 phần × ≤4300 → 5/5 map OK → tổng hợp.
- Bot trả lời đúng nội dung: 345 học viên / 10 lớp / 11/8–20/9/2026 / LXP 15-30/8 / taskforce AI 2 nhóm.
- Restart sau khi gieo state 50 ID: `[STARTUP] Không có tin mới nào cần trả lời (đã trả lời hết ở lần chạy trước)` — không spam.

## Bug trung gian đã sửa trong chính bản vá
- `file_info` trả JSON đa dòng kèm header → parser line-by-line fail → meta rỗng → đọc nhầm PDF nhị phân. Sửa bằng `_parse_json_loose` (raw_decode từ `{` đầu tiên).
- Block tài liệu đứng sau 2 xuống dòng → `startswith()` không khớp → đổi `in`.
- Comment lẫn từ Trung Quốc ("声称") — đã sửa.
- Kill-loop restart responder khớp sai regex → 2 responder song song ~1 phút → kill PID trực tiếp, giờ còn đúng 1 cặp.

## Trạng thái
- Responder LIVE: PID 16580 (proc_f96f3e82eefc), heartbeat xanh, chạy code đầy đủ.
- CHƯA commit — chờ chủ duyệt (cùng lượt với các thay đổi khác nếu có).
- Giới hạn đã biết: PDF scan ảnh (không có lớp chữ) → báo lỗi rõ cho chủ; file >20MB bị chặn; các định dạng khác (xlsx/pptx) chưa hỗ trợ (báo rõ, không im lặng).
