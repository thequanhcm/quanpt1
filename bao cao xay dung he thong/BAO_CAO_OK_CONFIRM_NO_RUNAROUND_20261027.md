# BÁO CÁO: Quy tắc "ok" = Xác nhận + Không hỏi lòng vòng

**Mã báo cáo:** RPT-QAB-OK-CONFIRM-20261027
**Thời điểm:** 27/10/2026 ~00:50 ICT
**Yêu cầu chủ sở hữu:** "Thiết lập khi anh gõ ok, OK có nghĩa là anh đã xác nhận, còn không sẽ không phản hồi hoặc không có xác nhận; thiết lập để trợ lý không hỏi lòng vòng."

## 1. Chẩn đoán từ ảnh (kênh NetChat 00:27–00:31)

Hai lỗi thật, có bằng chứng trong ảnh:
1. **"ok" của anh bị bắt nhầm**: bot hỏi "Anh xác nhận cho em chạy lại probe nhé?" → anh gõ "ok" → regex lệnh duyệt hồ sơ (`_PLAIN_APPROVE` gồm cả "ok") bắt tin này thành lệnh "Duyệt" trần → bot trả lời dài dòng "KHÔNG CÓ HỒ SƠ NÀO ĐANG CHỜ DUYỆT..." — sai ý, lòng vòng.
2. **Xin phép việc mình tự làm được**: bot probe chỉ-đọc (an toàn tuyệt đối) mà vẫn hỏi xin phép + đẩy việc kiểm tra về phía anh ("Anh kiểm tra giúp đèn LAN...").

## 2. Giải pháp 4 lớp

### Lớp 1 — "ok" = xác nhận có thực thi (`netchat_command_center.py`)
- Khi bot hỏi xin phép/chờ lệnh → hành động được **stage** vào `_PENDING_ACTIONS` (TTL 15 phút, quá hạn tự huỷ — "ok" muộn không kích hoạt việc lỗi thời).
- Anh gõ `ok/OK/oke/ừ/uk/ok anh` → thực thi NGAY việc đang chờ, trả **kết quả thật** (VD: probe lại Pi 5 báo ONLINE/OFFLINE thật), consume-once.
- `ok` khi **không có việc chờ** → **im lặng hoàn toàn** (không phản hồi — đúng chữ yêu cầu anh).

### Lớp 2 — Respond tự chạy probe chỉ-đọc (`netchat_auto_responder.py`)
- Regex phát hiện câu trả lời AI đang **xin phép** làm việc probe/kiểm tra/trạng thái/xác minh → responder **tự chạy probe thật ngay** và trả KẾT QUẢ thay câu hỏi. Bot không bao giờ xin phép làm việc nó tự làm được.
- `ok_silent` → không gửi gì vào kênh (không spam).

### Lớp 3 — System prompt quy tắc 10–11 (`context_builder.py`)
- Quy tắc 10: việc chỉ-đọc an toàn → LÀM LUÔN không xin phép; "ok" sau lời đề nghị = xác nhận, không hỏi lại; **anh phủ nhận kết quả (VD "anh đã bật rồi") → probe lại bằng dữ liệu mới TRƯỚC khi kết luận** (probe cũ có thể lỗi thời).
- Quy tắc 11: trả lời ngắn, đi thẳng, không kết thúc bằng câu hỏi xin phép.

### Lớp 4 — Teach pipeline nhận diện rộng hơn
- Thêm prefix "thiết lập khi anh...", "quy tắc:", "khi anh gõ" → lời dạy cấu hình hành vi của anh được lưu tự động vào trí nhớ dài hạn (USER_PROVIDED).

## 3. Kiểm chứng E2E thật

- **10 tests mới** (`tests/test_ok_confirmation_flow.py`): ok→thực thi; ok không có việc → im lặng; TTL hết hạn chặn "ok" muộn; ok KHÔNG rơi vào adapter duyệt hồ sơ (regression từ ảnh); probe báo trung thực OFFLINE; lệnh thường không ảnh hưởng.
- **Full regression: 653 passed (+10), 1 failed (Ollama env cũ), 2 skipped — 0 regression.**
- **E2E dạy qua API**: "nhớ rằng khi anh gõ ok..." → lưu thành công (ID `c8711f2b`, SEMANTIC PREFERENCE USER_PROVIDED) + `teach_note` trong response JSON (đã fix field thiếu).
- **E2E đúng kịch bản ảnh**: hỏi "anh đã bật pi5 rồi, em kiểm tra và xác nhận" → bot probe lại, báo trung thực "Pi 5: OFFLINE (probe thật)", **KHÔNG hỏi xin phép** (verify tự động: không còn "cho phép/xác nhận cho em/chờ lệnh").
- **E2E trên kênh thật**: anh gõ "pi 5 đã online. em kiểm tra lại" → bot trả lời "Em đã probe lại ạ: [CÓ BẰNG CHỨNG — probe thật...] Pi 5: OFFLINE — không xác minh được..." — đúng hành vi mới, không hỏi lòng vòng.

## 4. Giới hạn trung thực

- "ok" hiện thực thi các hành động đã được stage (probe lại Pi 5, probe toàn hệ thống). Các hành động mới trong tương lai cần đăng ký runner — nếu quên, bot trả lời trung thực "chưa có runner tương ứng" thay vì bịa.
- Việc đổi trạng thái (duyệt hồ sơ, thực thi nhiệm vụ) vẫn PHẢI qua luồng approval V3 — "ok" không phê duyệt hộ hồ sơ (an toàn: tránh ánh xạ sai ý sang quyết định quan trọng). Nếu anh muốn "ok" cũng duyệt được hồ sơ đang chờ, cần duyệt thiết kế riêng.
- Responder đang chạy code mới; 2 lần deploy kênh NetChat bị 502/403 từ gateway — báo cáo này gửi qua file + đã thử kênh 1 lần.

## 5. Commit & files
- Commit: (chèn sau khi commit)
- Files: `tools/netchat_command_center.py` (+110 dòng), `tools/netchat_auto_responder.py`, `src/quan_ai_brain/cognition/context_builder.py` (quy tắc 10–11), `src/quan_ai_brain/cognition/teach_pipeline.py` (4 prefix), `src/quan_ai_brain/web/server.py` (teach_note field), `tests/test_ok_confirmation_flow.py` (mới 10 tests).
