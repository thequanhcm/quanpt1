# BÁO CÁO: Nạp Gemini API key — lớp tra cứu thông tin ngoài hệ thống

**Mã báo cáo:** RPT-QAB-EXTERNAL-LOOKUP-20261027
**Thời điểm:** 27/10/2026 ~02:00 ICT
**Yêu cầu chủ sở hữu:** "Hãy nạp thông tin này vào cho hệ thống để sau anh hỏi các thông tin liên quan tra cứu ngoài hệ thống, tin tức thì tự truy xuất, tìm kiếm và phản hồi." (kèm Gemini API key)

## 1. Đã làm gì

1. **Lưu key an toàn** (không vào code, không vào git, không log):
   - `tools/persist_gemini_env.ps1` — lưu `GEMINI_API_KEY` + `GEMINI_MODEL` vào HKCU user-level registry (persist qua reboot). Key không in/log/truyền qua command line; file tạm chứa key đã xoá ngay sau nạp.
2. **Module mới `src/quan_ai_brain/tools/external_lookup.py`** (~14KB) — tra cứu ngoài 2 tầng:
   - **Tầng 1 — Gemini + Google Search grounding**: chỉ nhận khi response có nguồn (groundingMetadata). Cooldown 6h khi quota chặn (không đốt quota vô ích).
   - **Tầng 2 — Google News RSS (không cần key) + Gemini tổng hợp**: query rút gọn thành cụm tìm tin (`_clean_rss_query` — bỏ "hôm nay/bao nhiêu/ạ" vì Google News ranking tệ với câu dài), chuỗi fallback model khi 1 model hết quota/503.
   - An toàn: query redact trước khi rời máy; fail-closed (lỗi → chat vẫn chạy bình thường không evidence); key chỉ đọc env, env thiếu → tự đọc registry (không log).
3. **Tích hợp vào cả 2 đường chat** của server 8765 (`/api/chat` + `/api/chat/stream`, bước 2.6 sau grounding facts): chỉ câu hỏi thời sự (`should_lookup_external`) mới tra — câu nội bộ/điều khiển không tốn quota. Response có field `external_lookup` (audit minh bạch: layer, số nguồn).
4. **KHOI_DONG_24_7.bat**: `:LoadUserEnv` nạp thêm GEMINI_API_KEY/GEMINI_MODEL từ registry cho process con sau reboot.
5. **Tests mới `tests/test_external_lookup.py`** (20 test, mock HTTP, không gọi mạng thật, không đọc key thật): phân loại câu hỏi, render evidence, cache RSS, cooldown tầng 1, fallback tầng 2.

## 2. Kiểm chứng E2E thật (server 8765 chạy code mới)

| Câu hỏi | Kết quả |
|---|---|
| "tin thời tiết hôm nay" | 5.8s — trả tin 26/10 thật: không khí lạnh tràn miền Bắc, mưa lớn miền Trung >250mm, nguồn Laodong.vn + Tin tức 24h; trung thực nói chưa có số nhiệt độ chi tiết |
| "giá vàng SJC hôm nay bao nhiêu ạ?" | Tra được tin giá vàng 26/10 (SJC/DOJI/PNJ, vàng thế giới 4.000 USD/ounce); **TRUNG THỰC**: không bịa số, nói rõ nguồn không nêu giá SJC cụ thể trong tiêu đề, dẫn sjc.com.vn |
| "trạng thái hệ thống" / "ok" | KHÔNG tra ngoài (đúng thiết kế — không tốn quota) |

**Kênh nào được phủ:** dashboard 8765 + dashboard 8766 + kênh NetChat "Trợ lý Tony Pham" (responder đi qua `/api/chat` 8765).

## 3. Hạn chế trung thực (owner cần biết)

1. **Search grounding của Gemini KHÔNG dùng được trên free tier hiện nay**: Google đã đóng đường free-grounding cho project mới (429 triền miên trên mọi model; `gemini-2.5-flash`/`flash-lite` — 2 model duy nhất còn free grounding — đã bị retire với project mới). Tầng 1 sẵn sàng trong code — tự kích hoạt khi Google mở lại/quyến trả phí.
2. **Free chat quota thấp** (gemini-3-flash-preview ~20 request/ngày): tổng hợp Gemini là tăng cường — khi hết quota, bot vẫn trả nguồn RSS thô (không chết).
3. RSS Google News đôi khi trả tiêu đề không đủ chi tiết (như giá vàng) — bot được quy tắc KHÔNG bịa, sẽ nói rõ và dẫn nguồn để anh tự xem.

## 4. Test & Trạng thái

- Focused: **20/20 passed** (`test_external_lookup.py`).
- Full regression: 673 passed + 20 mới (2 skipped là Pi-hardware), 1 fail cũ đã biết (`test_keep_warm_pulse` — Ollama OFFLINE).
- Stack đã restart với code mới; watchdog đã reset lại phiên giám sát.

## 5. Việc tiếp theo đề xuất

- Muốn search-grounding thật (bot tự search web như Google): cần bật billing cho Gemini API (Tier 1) — tốn phí theo dụng; hoặc chờ Google mở lại free grounding.
- Có thể thêm nguồn RSS chuyên biệt (giá vàng sjc.com.vn, thời tiết nchmf...) khi anh cần độ chính xác số liệu cao hơn.
