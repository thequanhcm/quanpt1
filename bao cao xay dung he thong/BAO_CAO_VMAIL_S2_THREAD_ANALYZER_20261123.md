# BÁO CÁO SPRINT 2 — VMAIL THREAD-ANALYZER (card TASK-VMAIL-S2)

**Ngày:** 23/11/2026 · **Executor:** TONY · **Branch:** `feat/v6-m6-memory-truth`
**Chỉ thị owner:** "duyệt, em làm các việc tiếp theo: Roadmap mục 6 — Sprint 2 VMAIL Thread Analyzer (Sprint 1 VmailConnector đã LIVE)"

---

## 1. Mục tiêu sprint

Master prompt VMAIL §5.3-5.4: Cherry hiểu TOÀN BỘ luồng trao đổi (không coi mỗi
email độc lập), tổng hợp 10 mục §5.3 + summary 8 mục §5.4 **bắt buộc dẫn nguồn**;
email mới nhất KHÔNG mặc định đúng; mâu thuẫn → trình bày CẢ HAI + nguồn.

## 2. Thiết kế (lớp mỏng — không core thứ 2)

```
VmailConnector (S1, SOAP READONLY)
        │ list_messages("inbox", 20)
        ▼
thread_analyzer.build_threads()      ← subject-normalize + tag hủy/hoãn/dời
        │ group theo key
        ▼
thread_analyzer.analyze_thread()     ← 10 mục §5.3, deterministic, KHÔNG LLM
        ▼
format_thread_summary() / format_10_items()   ← 8 mục §5.4, mỗi mục dẫn nguồn
        ▼
office_thread_summary_runner.py  ←  netchat_command_center "tóm tắt luồng email"
```

- `normalize_subject()`: strip RE/FW/FWD/TRL prefix; **tách tag "[Hủy cuộc họp]"/
  "Hoãn"/"Dời lịch" khỏi key** nhưng giữ lại thành tín hiệu thay đổi → mail hủy
  GHÉP ĐÚNG luồng gốc (tiêu chí nghiệm thu P1-3).
- Mọi item (yêu cầu/câu hỏi/cam kết/quyết định/thay đổi) kèm `(mail #id ngày)`.
- Mâu thuẫn: mail gốc mời họp + mail sau tag HỦY → báo CẢ HAI + nguồn 2 mail,
  ghi rõ "không tự kết luận bên nào đúng".

## 3. Files changed

| File | Loại | Nội dung |
|---|---|---|
| `src/quan_ai_brain/office/thread_analyzer.py` | MỚI (361 lines) | ThreadAnalyzer: normalize/build/analyze/format |
| `tools/office_thread_summary_runner.py` | MỚI (97 lines) | CLI runner (subprocess 110s — bài học imaplib hang) |
| `tools/netchat_command_center.py` | PATCH | intent `thread_summary` + handler + truyền `text` |
| `tests/test_office_thread_analyzer.py` | MỚI (19 test) | mock 100%, không SOAP thật |
| `docs/PROJECT_STATUS.md` | PATCH | mục Sprint 2 |

## 4. Bằng chứng nghiệm thu

| Tiêu chí | Kết quả |
|---|---|
| `tests/test_office_thread_analyzer.py` | **19/19 PASS** |
| "[Hủy cuộc họp]" ghép ĐÚNG gốc (P1-3) | ✅ test test_cancel_mail_groups_with_original |
| DM trả đủ 10 mục §5.3 (P1-3) | ✅ test_all_10_sections_present |
| Focused regression (thread+vmail+command_center+email) | **109/109 PASS** |
| Live smoke SOAP thật (READONLY) | ✅ luồng "Khói…CHÁY!!!" 7 mail → đủ 8 mục + nguồn; từ khóa "khói" → đúng luồng |
| R2 READONLY | ✅ không gọi mark_read/send; runner chỉ Search/GetMsg |
| Fail-honest | ✅ SOAP lỗi → `⚠️ + lỗi thật`, không fake luồng |

## 5. Known issues (trung thực)

- Tổng hợp tự nhiên bằng GLM (viết lời văn mượt) **chưa có** — sprint này deterministic
  trích xuất; belongs to sprint sau (nối /api/chat).
- Chưa ghi thread_id/classification vào `data/email_intake.db` — thuộc Sprint 3
  MEMORY-ADAPTER (master prompt §6.4, cần owner duyệt thêm cột).
- KPI §14 (Thread Understanding ≥95%) chưa đo — cần bộ dữ liệu gán nhãn (Sprint 7).
- Confidence hiện là tỉ lệ mục có dữ liệu (proxy), không phải accuracy đo được.

## 6. Bước kế tiếp (theo roadmap owner duyệt)

- **Sprint 3 — Shared Memory/MEMORY-ADAPTER**: retrieve_context + Memory Candidate
  qua cơ chế episodes/experience_lesson hiện có (không tự promote).
- Sprint 4 — Reply Draft 3P (DRAFT-ONLY); Sprint 5 — Workflow + Briefing;
  Sprint 6 — Dashboard; kèm mục 7 (4 module backlog), mục 8 (ChatToolBridge MAIL_READ),
  mục 9 (BGE — KHÔNG bật lại: owner tắt Ollama 18/11, ONNX MiniLM đang chủ lực).

---
*Fail-honest: mọi số liệu từ pytest thật + live SOAP thật 23/11 trên máy QUANPT.*
