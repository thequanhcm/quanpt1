# BÁO CÁO 4 MỤC ROADMAP (owner duyệt 23/11) — 24/11/2026

**Phạm vi:** mục 6 (Sprint 2 Thread Analyzer), 7 (4 module backlog), 8 (MAIL_READ wire), 9 (BGE).

## ✅ Mục 6 — Sprint 2 VMAIL THREAD-ANALYZER (HOÀN THÀNH, commit `22938f6`)
- `src/quan_ai_brain/office/thread_analyzer.py` (361 lines): 10 mục §5.3 + 8 mục §5.4, dẫn nguồn mail #id, mâu thuẫn hủy/hoãn trình bày CẢ HAI.
- `tools/office_thread_summary_runner.py` + DM "tóm tắt luồng email <kw>".
- Test 19/19; focused bộ 109/109; live SOAP thật: luồng "Khói CHÁY" 7 mail ghép đúng.
- Chi tiết: `bao cao xay dung he thong/BAO_CAO_VMAIL_S2_THREAD_ANALYZER_20261123.md`.

## ✅ Mục 8 — MAIL_READ wire ChatToolBridge/QPIG (HOÀN THÀNH, commit `50cab29`)
- `src/quan_ai_brain/tools/vmail_tool.py`: tool `vmail_mail_read` R1 READONLY.
- Wire đúng kiến trúc: DIRECTIVE_NAMES + INTENT_KEYWORDS + AUTO_DIRECTIVES + ToolRegistryLoader (2 registry) + QPIG.call fallback handler + strong-phrase floor 0.35.
- Test 13/13 mới + UAIIF 34/34 không phá = 47/47; Live E2E SOAP: QPIG.call → 3 mail + threads mode luồng Khói 7 mail.

## ✅ Mục 9 — BGE embedding offline (XÁC MINH ĐÚNG THIẾT KẾ, không thay đổi)
- BGE = Ollama — owner tắt hoàn toàn 18/11 → is_available()=False là CHỦ Ý, không phải lỗi.
- Đường chính ONNX MiniLM (SemanticMemoryEngine): **6.578 chunks LIVE** tại data/vector_db_semantic; benchmark 4 câu thật: 248-431ms/câu, hits đúng ngữ cảnh → đủ nhanh, không cần BGE.
- Trung thực: "mirror ổ D" 0 hits vì chưa ingest (sprint memory riêng, không thuộc mục 9).

## ✅ Mục 7 — 4 module backlog (AUDIT: KHÔNG xây mới — đúng §2.1)
- Tên `cognitive_core`/`shared_memory`/`approval_engine`/`voip_connector` KHÔNG tồn tại, NHƯNG chức năng tương đương đã có: cognition/ (suy luận + self_check + semantic), governance/ (R0-R5 + ApprovalCard + ConsultationStore), memory/ 3 tầng + semantic 6578 chunks, voffice_reader + integration/ (VoIP gián tiếp).
- Master prompt §2.1 cấm tạo core thứ 2 → 4 module chỉ xây khi sprint nghiệp vụ cần interface riêng (vd voip_connector khi tunnel M-Suite lên — Sprint Calendar).

## Giới hạn trung thực
- LLM tổng hợp tự nhiên (GLM) chưa nối vào Thread Analyzer — deterministic hiện tại; nối /api/chat thuộc sprint sau.
- KPI §14 (≥95%) chưa đo — cần bộ dữ liệu gán nhãn (Sprint 7).
- Thread chưa ghi vào email_intake.db (Sprint 3 MEMORY-ADAPTER chờ duyệt thêm cột).
- MAIL_READ dùng được khi Cherry bật (manual-start); pipeline 8765 hiện OFF.

## Trạng thái roadmap VMAIL sau phiên
S0 ✅ → S1 ✅ → **S2 ✅ (mới)** → S3 MEMORY-ADAPTER (kế tiếp) → S4 Reply Draft → S5 Workflow → S6 Dashboard.

---
*Fail-honest: mọi số liệu từ pytest thật + live SOAP/ONNX thật trên máy QUANPT 24/11.*
