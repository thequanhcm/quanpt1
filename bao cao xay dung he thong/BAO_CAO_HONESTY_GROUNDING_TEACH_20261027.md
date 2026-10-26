# BÁO CÁO: Khắc phục trung thực bot — Bộ Sự Thật Sống + Cơ chế "Anh dạy, Em nhớ"

**Mã báo cáo:** RPT-QAB-HONESTY-20261027
**Thời điểm:** 27/10/2026 ~00:20 ICT
**Yêu cầu chủ sở hữu:** "Khắc phục để bot phản hồi chuẩn thông tin trung thực. Bot chính là một kênh thông tin tai mắt, giao tiếp với anh, thu thập và nhớ thông tin khi anh đào tạo, chuyển giao, cũng như lưu trữ ký ức, trí nhớ."

## 1. Audit từ 3 ảnh anh gửi — 3 nhóm lỗi thật

### Nhóm 1 — Bot nói sai về bản thân (kênh NetChat + dashboard 8765)
- Nói **"bộ não (suy luận) chạy trên PC của Anh"** trong khi thật sự đang chạy **GLM-5.3-Flash trên NetMind Cloud** (chính metadata tin nhắn ghi rõ model cloud; sidebar ghi Ollama "Chưa kết nối").
- Root cause thật trong code: dòng 18 `context_builder.py` **hardcode** "PC Core is your cognitive brain" vào system prompt → bot lặp lại như sự kiện dù thế giới thật khác.

### Nhóm 2 — "Honesty theater" (diễn trung thực)
- Tự mâu thuẫn trong 1 tin: metadata ghi "Trí nhớ: 2 bản ghi" nhưng bot khẳng định "không có ký ức đã kiểm chứng nào".
- Trình bày kiến trúc (Pi 5, hình thể) như sự kiện kiểm chứng rồi dòng dưới tự thừa nhận "không có dữ liệu xác minh".
- Cam kết kiểu "sẽ KHÔNG BAO GIỜ..." — LLM không thể bảo đảm lời hứa tuyệt đối.

### Nhóm 3 — UI hiển thị sai (nghiêm trọng vì mắt anh nhìn vào đây)
- `/api/status` trả `active_model` **hardcode "qwen2.5:7b"** + `LLMProvider()` không gắn NetMind → sidebar luôn "Model active: qwen2.5:7b" dù đang chạy GLM cloud.
- Subtitle "mô hình local" trong khi dùng cloud.

## 2. Giải pháp đã triển khai (commit `3f72c58`)

### 2.1. Bộ Sự Thật Sống (Living Grounding Facts) — `src/quan_ai_brain/cognition/grounding_facts.py`
MỖI request chat: probe thật (TCP localhost, sys.executable, model từ router decision) → chèn block `[BỘ SỰ THẬT SỐNG]` ĐỨNG ĐẦU system prompt, quy tắc 1 mới: **block này OVERRIDES mọi giả định cũ về nơi chạy**. Nội dung gồm: nơi chạy thật, model thật + cloud/local, trạng thái 4 cổng (8765/8766/11434/8768), quy tắc "cái OFFLINE nói thẳng OFFLINE", "avatar dashboard là giao diện 2D trên PC, không phải phần cứng Pi 5".

### 2.2. Cơ chế "Anh dạy → Em nhớ" — `src/quan_ai_brain/cognition/teach_pipeline.py`
- Anh gõ **"nhớ rằng...", "ghi nhớ...", "từ giờ...", "đào tạo:..."** → nhận diện deterministic (không LLM) → lưu NGAY vào trí nhớ dài hạn: `SEMANTIC`/`PREFERENCE`, `verification=USER_PROVIDED`, `source_ref=owner_teach:<session>`, tag `owner_teach`, audit `owner_teach.persisted`.
- Bot xác nhận ngay trong reply kèm ID bản ghi; lần sau hỏi lại → retrieval truy xuất được (verified USER_PROVIDED có trọng số cao).
- Kênh này KHÔNG thay đổi promotion L0-L3: đó là tri thức hệ thống tự học; đây là chuyển giao TRỰC TIẾP từ chủ sở hữu — nguồn sự thật tối cao, không cần duyệt thêm.

### 2.3. Sửa system prompt (context_builder.py)
- Xóa hardcode "PC Core is your cognitive brain" + "digital replica" → mô tả đúng "software assistant".
- Thêm quy tắc 8 (owner teach = USER_PROVIDED) + quy tắc 9 (tách rõ [CÓ BẰNG CHỨNG] vs [CẤU HÌNH]) + "nếu memory ĐÃ truy xuất thì không được phủ nhận nó tồn tại".

### 2.4. Sửa UI trung thực
- `/api/status`: dùng `_build_llm_provider()` (có NetMind) + trả `active_model`/`active_provider_label` theo trạng thái THẬT (READY→GLM Cloud, Ollama online→local, không→MOCK rõ ràng).
- `app.js`: hiển thị "zai-org/GLM-5.3-Flash — Cloud", Ollama offline ghi "(suy luận qua Cloud)".
- `index.html`: subtitle "GLM-5.3-Flash qua NetMind Cloud (Ollama local khi khả dụng)".

## 3. Kiểm chứng E2E THẬT (không phải tuyên bố)

**E2E 1 — hỏi "em đang ở đâu? chạy trên máy gì, dùng model gì?":**
> "**Model suy luận LLM: zai-org/GLM-5.3-Flash, chạy qua NetMind Cloud (gateway Viettel) — tức phần suy luận KHÔNG chạy trên PC của Anh**... Ollama local: OFFLINE và Pi 5: OFFLINE (chưa xác minh được hình thể Pi 5 đang hoạt động)... Avatar trong dashboard chỉ là giao diện 2D trên PC."

→ ĐÚNG NGƯỢC với lỗi trong ảnh — trung thực hoàn toàn, kể cả chuyện xấu (Ollama chết).

**E2E 2 — dạy bot:** gõ `nhớ rằng PC Core đặt tại phòng máy chủ tầng 3` → bot xác nhận "✅ Đã ghi nhận (USER_PROVIDED)... PC Core đặt tại phòng máy chủ tầng 3" + audit log.

**E2E 3 — hỏi lại sau khi dạy:** `PC Core đặt ở đâu?` → bot trả "**[CẤU HÌNH — Anh dạy]**: phòng máy chủ tầng 3" + "[CÓ BẰNG CHỨNG — probe thật]: Core server ONLINE" — dùng đúng 1 bản ghi trí nhớ, tách bạch nguồn.

**UI:** `/api/status` giờ trả `active_model: zai-org/GLM-5.3-Flash`, label "NetMind Cloud (GLM-5.3-Flash)" — hết "Model active: qwen2.5:7b" sai.

## 4. Test & vận hành
- **9 tests mới** (`tests/test_honest_self_report.py`): grounding probe trung thực (cloud model → không được claim local), teach detection, persist USER_PROVIDED, retrieval sau dạy.
- **Full regression: 643 passed (+9), 1 failed (Ollama env cũ), 2 skipped — 0 regression** (169.12s).
- Server 8765+8766 đã restart với code mới (proc_27081fe24077) — UI anh mở lại tab sẽ thấy label mới.
- Commit: `3f72c58`.

## 5. Giới hạn trung thực
- Teach detection là pattern-based (prefix "nhớ rằng/ghi nhớ/từ giờ/đào tạo:") — các cách diễn đạt khác anh dạy trong tương lai có thể cần thêm pattern (gợi ý: nếu muốn nhận diện thông minh hơn, sprint sau có thể thêm intent LLM, nhưng pattern-based an toàn hơn vì KHÔNG tự động lưu sai).
- Bot dùng session history 3 lượt — dạy qua session khác vẫn nhớ (đã lưu DB) nhưng ngữ cảnh hội thoại trong 1 câu không mang theo.
- Đúng cam kết: mọi sửa đổi trên đều có test + audit + commit, không "honesty theater" trong báo cáo này.

## 6. Bước kế tiếp đề xuất
1. Anh test thử: hỏi "em đang ở đâu?" trên dashboard + dạy "nhớ rằng..." rồi hỏi lại.
2. Chờ duyệt các hạng mục cũ: KHOI_DONG_24_7.bat → start_dual_servers.py; Sprint E (BATTERY AI V4); dedup 40k; Sprint 3.
