# BÁO CÁO: Sửa lỗi bot báo sai "Pi 5 OFFLINE" + trả lời ngắn gọn đúng câu hỏi

**Mã báo cáo:** RPT-QAB-PI5-EDGE-TRUTH-20261027
**Thời điểm:** 27/10/2026 ~01:00 ICT
**Yêu cầu chủ sở hữu:** "pi5 đã online mà sao bot phản hồi không đúng, hãy kiểm tra lại hệ thống xử lý của trợ lý và khắc phục. Việc trả lời câu hỏi cần ngắn gọn, tránh dài dòng không đúng nội dung câu hỏi."

## 1. Root cause — LỖI SAI BẢN CHẤT của probe Pi 5 (tìm thấy bằng audit 2 ảnh + netstat)

**Mâu thuẫn trong ảnh của anh:** Bot probe báo "Pi 5: OFFLINE" nhưng **dashboard 8766 hiển thị "Pi 5: READY — ĐÃ KẾT NỐI, RTT 27ms"** — cùng một hệ thống, hai kết quả trái ngược.

**Audit toàn chuỗi xử lý tìm ra nguyên nhân tận gốc:**
- Pi 5 là thiết bị **riêng trong LAN** (IP 192.168.1.21), chạy kiosk port **8768 TRÊN PI**.
- Pi 5 gửi **heartbeat HMAC qua LAN** lên Executive server 8766 mỗi ~1 giây — đây là nguồn sự thật hợp lệ (dashboard đọc từ đây nên báo READY đúng).
- **3 module của em lại probe `TCP 127.0.0.1:8768`** — cổng 8768 **chạy trên Pi, KHÔNG BAO GIỜ lắng nghe trên PC** → probe luôn OFFLINE dù Pi 5 online. Bot lại gắn nhãn "[CÓ BẰNG CHỨNG — probe thật]" cho kết quả sai bản chất này → "honesty theater" nghiêm trọng: dùng format trung thực để báo dữ liệu sai.
- 3 module bị lỗi: `grounding_facts.py` (system prompt mỗi request), `self_model_engine.py` (lệnh "trạng thái"), `netchat_command_center.py` (handler "ok" → reprobe).

## 2. Khắc phục

1. **Nguồn sự thật duy nhất cho Pi 5** (`_pi5_edge_truth()`): đọc `/api/executive/edge/status` — heartbeat HMAC thật qua LAN, có RTT đo thật. Không probe TCP 127.0.0.1:8768 nữa (comment code giải thích rõ sai bản chất).
2. **`grounding_facts.py`**: mục 4 của Bộ Sự Thật Sống giờ báo "Pi 5: ONLINE (edge READY, RTT ~13ms, heartbeat 0s trước)" khi Pi kết nối — khớp dashboard.
3. **`self_model_engine.py`** ("trạng thái"): pi5_edge giờ vào danh sách ONLINE khi heartbeat sống.
4. **Quy tắc 7 mới trong Bộ Sự Thật Sống**: "Anh NÓI thành phần đã bật → tin Anh + kiểm tra lại mục 3-4; KHÔNG cãi lại bằng dữ liệu cũ."
5. **`_reprobe_pi5`** (handler "ok"): trả kết quả từ edge monitor.

## 3. Trả lời ngắn gọn — đúng câu hỏi

- **Quy tắc 11 nâng cấp**: "chỉ trả lời ĐÚNG nội dung câu hỏi, 2-5 câu; Anh hỏi Pi 5 → chỉ nói Pi 5; KHÔNG liệt kê thành phần không liên quan; 'kiểm tra lại' = probe + một dòng kết luận."
- **Lệnh "trạng thái" rút từ ~15 dòng còn 3-4 dòng**: `🟢 ONLINE: ... | 🔴 OFFLINE: ... | 📋 Nhiệm vụ: ...` (bỏ timestamp, bỏ phân mục dọc, bỏ "Thay đổi từ lần trước" nếu rối).

## 4. Kiểm chứng E2E

**Đúng kịch bản trong ảnh của anh** (hỏi qua API thật, server mới):
> Anh: "pi5 đã online. em kiểm tra lại"
> Bot: "**Pi 5: ONLINE** — heartbeat mới nhất cách đây ~1 giây, RTT ~18ms, edge READY. Kết quả khớp với những gì Anh nói — Pi 5 đang hoạt động bình thường."

**Trên kênh NetChat thật** (responder dùng server mới): bot trả lời "Em vừa probe lại Pi 5: **ONLINE** — RTT 19ms, heartbeat 1 giây trước" — hết mâu thuẫn với dashboard.

**Bộ Sự Thật Sống mới** (chèn vào system prompt mỗi request): mục 4 báo "ONLINE (edge READY, RTT 13ms, heartbeat 0s trước) — hình thể Pi 5 ĐANG hoạt động, xác nhận bằng heartbeat thật."

**Test**: 653 passed, 0 regression (1 failed cũ `test_keep_warm_pulse` — Ollama env, không liên quan; 2 tests fixture cập nhật theo format ngắn mới).

## 5. Giới hạn trung thực

- Edge monitor chỉ thấy Pi 5 **khi PC nhận được heartbeat** — nếu Executive server 8766 chết, trạng thái sẽ là "UNAVAILABLE" (không suy diễn ONLINE/OFFLINE).
- RTT hiển thị là giá trị đo gần nhất từ heartbeat, có thể chênh ±vài ms so với thực tế tức thời.
- 2 ảnh anh gửi: ảnh 1 (kênh NetChat) có đủ hội thoại; ảnh 2 là dashboard 8766 (không có hội thoại) — dùng để đối chiếu mâu thuẫn trạng thái.

## 6. Commit & files
- Files: `src/quan_ai_brain/cognition/grounding_facts.py`, `src/quan_ai_brain/cognition/self_model_engine.py`, `src/quan_ai_brain/cognition/context_builder.py` (quy tắc 11), `tools/netchat_command_center.py` (`_pi5_edge_truth`, `_reprobe_pi5`, `handle_status` rút gọn), tests cập nhật.
- Commit: (điền sau commit)
