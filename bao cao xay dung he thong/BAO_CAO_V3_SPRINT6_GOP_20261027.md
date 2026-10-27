# BÁO CÁO V3 SPRINT 6-GOP — GỘP 4 HƯỚNG NÂNG CẤP

**Ngày:** 27/10/2026
**Task:** TASK-V3-SPRINT6-GOP — owner duyệt "DUYỆT TASK-V3-SPRINT6-GOP" qua desktop (consume-once, approver quanpt1)
**Thứ tự thực hiện:** (2) → (3) → (4) → (1) đúng card

---

## (2) 24/7 HARDENING — HOÀN TẤT (5 tests)

| Việc | Kết quả thật |
|---|---|
| Backup 2AM | Scheduled task `QUAN_AI_BRAIN_BACKUP_2AM` **đăng ký lại SUCCESS, Ready, lần chạy tới 28/10 02:00**; chạy thử ngay → `brain_20261027_024356.db` tạo thành công |
| Ollama startup | `KHOI_DONG_24_7.bat` thêm khối **[0/5]**: check port 11434 trước khi start (idempotent, không chạy 2 instance), fail-safe khi thiếu binary |
| Tên task nhất quán | Sửa KHOI_DONG dùng đúng tên `QUAN_AI_BRAIN_BACKUP_2AM` (trước đây lệch tên `QUAN_AIBRAIN_Backup_2AM`) |

## (3) BÁO CÁO SÁNG 8H QUA NETCHAT — HOÀN TẤT (7 tests)

- `tools/morning_report.py`: probe thật 8765/8766 + edge status + Ollama + backup age + card chờ duyệt + task chờ info-gap → 1 tin gọn kênh.
- **Nguyên tắc trung thực:** probe lỗi → "chưa xác minh được X", KHÔNG bịa số (test riêng cover).
- **Chạy thử thật:** báo cáo gửi kênh thành công (netchat_sent: True).
- Task Scheduler `QUAN_AI_BRAIN_MORNING_REPORT_8AM` — **Ready, lần chạy tới 28/10 08:00**.

## (4) TRA CỨU TTNS/LỊCH HỌP VÀO CHAT — HOÀN TẤT (9 tests)

- `src/quan_ai_brain/tools/ttns_lookup.py`: bọc skill ttns-meeting-lookup (read-only); fail-closed (rỗng/thiếu script/timeout/JSON lỗi → None).
- E2E THẬT: "Lịch họp của quanpt1 hôm nay?" → trả đúng 3 lịch (Đào tạo Kỹ sư AI 2026, 8:00-12:00, Hội trường tầng G TCT VTNet).
- Tích hợp `server.py` mục 2.7: `looks_like_ttns_query()` routing → evidence block vào system_instructions; KHÔNG cache DB; KHÔNG gửi dữ liệu nhân sự ra ngoài.

## (1) DOCUMENT RAG — HOÀN TẤT (10 tests + benchmark 10/10)

- `src/quan_ai_brain/cognition/document_rag.py`: Ingestion → Chunking (paragraph-first, size 700, overlap 120, heading=section) → Index SQLite riêng `data/document_index.db` → Hybrid retrieval (keyword 0.4 + dense 0.6; synonym map tiếng Việt; threshold 0.45).
- **Chống ingest nhạy cảm:** .env/credentials/token BỊ TỪ CHỐI (test cover); chỉ .txt/.md.
- Fail-closed: Ollama chết → keyword-only; index rỗng → không evidence; không đủ căn cứ → "Em chưa tìm thấy căn cứ trong kho tài liệu nội bộ…".
- **Benchmark 10 câu (đúng cấu trúc Lab Mini RAG): 10/10 PASSED (100%)**, no-answer honesty 2/2 — Q1-Q3 direct, Q4-Q5 multi-chunk, Q6-Q7 paraphrase (synonym), Q8-Q9 no-answer, Q10 version-citation. Kết quả lưu `reports/sprint6_rag_benchmark.json`.
- Tích hợp `server.py` mục 2.8: evidence block có citation `[tài liệu §mục | version]` + luật "chỉ trả lời từ context, thiếu thì nói thiếu".

## KIỂM THỬ TỔNG

| Suite | Kết quả |
|---|---|
| Sprint 6 (5+7+9+10) | **31 passed** |
| **Full regression** | **767 passed, 1 skipped (TTS hardware), 0 fail** (từ 736 → +31) |

## GIỚI HẠN TRUNG THỰC

1. Benchmark đo tầng RETRIEVAL với mock embedding — chưa đo LLM faithfulness thật (cần chat thật: hỏi "SLA alarm critical là bao lâu?" và xem citation).
2. Benchmark chạy trên kho mẫu 3 tài liệu tự viết — khi anh có kho thật (sổ tay vận hành thật), cần re-index + chạy lại benchmark để số đo phản ánh đúng kho thật.
3. Reboot thật PC CHƯA test (hạng mục 2c cần anh nhấn restart; checklist sẵn trong card).
4. Báo cáo sáng chạy lần đầu thật vào 28/10 08:00 — nếu task scheduler không fire (Interactive only), cần chuyển sang logon-trigger.

## THAY ĐỔI FILE

| File | Loại |
|---|---|
| `src/quan_ai_brain/cognition/document_rag.py` | MỚI |
| `src/quan_ai_brain/tools/ttns_lookup.py` | MỚI |
| `tools/morning_report.py` + `tools/run_morning_report.bat` | MỚI |
| `tools/rag_benchmark.py` + `reports/sprint6_rag_benchmark.json` | MỚI |
| `KHOI_DONG_24_7.bat` | PATCH (khối Ollama [0/5] + tên task chuẩn) |
| `src/quan_ai_brain/web/server.py` | PATCH (2.7 TTNS + 2.8 RAG) |
| `tests/test_v3_sprint6_*.py` ×4 | MỚI (31 tests) |
| `kho_tai_lieu/` | MỚI (3 tài liệu mẫu benchmark) |
| Task Scheduler | +2 task (backup 2AM, report 8AM) |
