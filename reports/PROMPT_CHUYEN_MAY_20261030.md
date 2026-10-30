# PROMPT CHUYỂN MÁY — HOÀN THIỆN CÔNG VIỆC DANG DỞ (30/10/2026)

> **Cách dùng:** Dán toàn bộ nội dung dưới đây vào trợ lý (netMind Desktop) trên máy mới.
> Trước khi dán: copy thư mục dự án `E:\AI\QUAN AI BRAIN` (hoặc ít nhất các mục ở "BƯỚC 0") từ máy cũ sang máy mới.

---

Dưới đây là bàn giao công việc từ máy cũ. Em đọc kỹ, kiểm chứng bằng code/data thật trước khi làm anything (audit first, change second).

## BỐI CẢNH

Anh là Phạm Thế Quân (quanpt1@viettel.com.vn), AI specialist tại Viettel Networks. Dự án: **QUAN AI BRAIN** (trợ lý ảo TONY) tại workspace `E:\AI\QUAN AI BRAIN`, nhánh `feature/cognitive-state-integration`. Repo GitHub: `https://github.com/thequanhcm/quanpt1.git` (không có branch `main`; PR duy nhất là **PR #1** base `master`, cập nhật bằng **PATCH /pulls/1**). Đọc `AGENTS.md`, `docs/PROJECT_STATUS.md`, `reports/HANDOFF_LATEST.md` trước khi làm.

## QUY TẮC BẤT DI BIẾN (đọc trước khi làm bất cứ việc gì)

1. Audit trước sửa sau; đọc code thật trước khi tin tài liệu; bằng chứng trước khi tuyên bố.
2. Commit/push CHỈ khi anh duyệt; conventional-commit bắt buộc; PR cập nhật bằng PATCH.
3. Không đọc/in/log secret; credential chỉ qua `git credential fill` (không in ra log).
4. Không xóa/ghi đè dữ liệu gốc khi chưa có phương án backup + rollback; giữ nguyên working tree đang dở.
5. Không tự cấp quyền, không tự duyệt, không bật production execution; R4 cần phê duyệt riêng, R5 hard-block.
6. Test thật trên phần cứng thật trước khi báo hoàn thành; pytest không import hàm `test_*` vào namespace; chromadb teardown cần `clear_system_cache()`.
7. TONY_STOP/START chỉ kill process có executable/command-line chứa `*QUAN AI BRAIN*` — tuyệt đối không blanket-kill python.exe.
8. Mọi daemon windowless phải mang env `PYTHONUTF8=1` + `PYTHONIOENCODING=utf-8` (commit `ffdfc24`).

## TRẠNG THÁI REPO (tại máy cũ)

- **Đã commit + push (PR #1, head `693cc3a`, 100 commits):** V40 ingestion kho_tai_lieu; fix UTF-8 daemon `ffdfc24`; full suite 2,846/2,846 GREEN `f1b1782`; reports `5ea08e9`; V41 Edge Agent 5 năng lực + Phase 0 QEP audit `693cc3a` (suite 2,884/2,884).
- **CHƯA commit (working tree máy cũ — KHÔNG được mất):**
  - `src/quan_ai_brain/knowledge/knowledge_ingestion.py` — PDF theo từng trang (marker `<<<PAGE N>>>`), DOCX đọc thêm tables (fix mất 544k ký tự bảng — Sổ tay VT-CNTT tăng 47x nội dung), XLSX marker `<<<SHEET name>>>`, **OCR ảnh** (`_parse_image` pytesseract vie+eng), FileScanner thêm `.png/.jpg/.jpeg/.bmp`, fix bug `_create_chunk` dùng chung reference metadata (page bị đè).
  - `src/quan_ai_brain/knowledge/knowledge_query.py` — `SearchResult` thêm `page_label` + `citation()` ("file (trang N)" / "file (sheet 'X')"), `render_evidence_block()` (bắt buộc LLM dẫn nguồn), `answer_question` hiện citation.
  - `src/quan_ai_brain/web/server.py` — **bước 2.9 KB RAG** trong chat handler (sau 2.8 DocumentRAG): retrieve KnowledgeQueryEngine top-5 min_score 0.55 → render_evidence_block vào system_instructions, fail-closed.
  - Tests MỚI: `tests/test_v41_knowledge_citation.py` (18 tests), `tests/test_v41_image_ocr.py` (7 tests) — 36/36 PASS tại máy cũ (kèm 18 tests knowledge cũ).
  - Tools: `tools/v41_verify_retrieval.py`, `tools/v41_chroma_diag.py`, `tools/v41_reingest_priority.py`, `tools/v41_embed_queue.py`.
- **BƯỚC 0 — copy từ máy cũ sang máy mới (bắt buộc):** toàn bộ thư mục repo (nhanh nhất: copy cả `E:\AI\QUAN AI BRAIN` trừ `.venv`), đặc biệt: `data/knowledge_db/` (ChromaDB 35,700 chunks), `data/document_index.db`, `brain.db`, `logs/v41_reingest_queue.json` (1,094 chunks đã parse chờ embed), `logs/v41_ocr_queue.json` (17 chunks OCR từ 22 ảnh), các file uncommitted liệt kê trên. Nếu lỡ bỏ máy cũ rồi: pull repo từ GitHub (phần committed) và em phải báo anh để lấy các file uncommitted + data từ ổ E máy cũ.

## MÔI TRƯỜNG MÁY MỚI CẦN SETUP

1. Python 3.11 + venv tại `.venv`; `pip install chromadb==1.5.9 pypdf python-docx pandas openpyxl xlrd nbformat pytesseract Pillow` (project gốc stdlib-only trừ knowledge pipeline).
2. **Tesseract OCR 5.4** (`winget install UB-Mannheim.TesseractOCR`, nếu bị chặn UAC thì tải installer UB-Mannheim về chạy với `-ArgumentList '/S'`) + copy `vie.traineddata` (từ tessdata_fast GitHub) vào `tessdata\` (cần admin PowerShell RunAs).
3. **Ollama** + model `bge-m3:latest` (embedding 1024 dims, ~0.78s/chunk trên GPU). Ollama phải chạy trước khi embed.
4. NetChat bot credentials đã có trong hệ thống máy cũ (brain.db/config) — KHÔNG log giá trị.
5. Task Scheduler trên máy mới: chỉ setup SAU khi anh duyệt (đây là máy production mới).

## VIỆC DANG DỞ — LÀM THEO THỨ TỰ, MỖI MỤC CÓ TIÊU CHÍ NGHIỆM THU

### 1. Hoàn tất ingestion kho_tai_lieu: 35,700 → 81,287 chunks
- Chạy lại `tools/v40_resume_ingest.py` (idempotent V40.1 — bỏ qua chunk đã lưu).
- **LƯU Ý ChromaDB 1.5.9:** KHÔNG chạy 2 process ghi cùng lúc (HNSW lock → InternalError "Error loading hnsw index"); KHÔNG gọi `col.count()` khi process khác đang ghi (segfault) — giám sát bằng sqlite read-only: `SELECT count(*) FROM embeddings` trên `data/knowledge_db/chroma.sqlite3`.
- **LƯU Ý OOM (sự cố thật trên máy cũ 21:24–21:53):** một process python commit tới 57GB → Windows kill loạt → lỗi Dell TechHub 0xe0434352 chỉ là nạn nhân. Chạy ingestion 1 process duy nhất, không mở thêm việc nặng song song.
- Nghiệm thu: sqlite count ≥ 81,287 hoặc bằng tổng chunks khả dụng; log không còn "embedding failed".

### 2. Embed 2 queue còn lại
- `logs/v41_reingest_queue.json` (Sổ tay VT-CNTT 991 chunks + 4 bài giảng M3 có page + 3 md) và `logs/v41_ocr_queue.json` (17 chunks OCR) bằng `tools/v41_embed_queue.py` — sửa hằng số QUEUE để chạy từng file (tool hiện trỏ tới reingest queue).
- Nghiệm thu: metadata có key `v41_reingest=1` đếm được ≥1,111 chunks; query thử "Cước trung bình theo hợp đồng" phải ra chunk có `source_ocr=1`.

### 3. Verify truy xuất CÓ DẪN CHỨNG (yêu cầu gốc của anh)
- Chạy `tools/v41_verify_retrieval.py`: 4 câu hỏi (RLS, churn, PM counter RAN 5G, Transformer) — mỗi kết quả PHẢI hiện `filename | page=N`.
- Smoke test chat flow qua `/api/chat` (guard 5000 ký tự KHÔNG nới): hỏi "churn là gì theo tài liệu" → câu trả lời phải dẫn `[tên file, trang N]`; nếu không đủ căn cứ phải nói rõ "chưa tìm thấy căn cứ" (fail-closed chuẩn bước 2.8/2.9).

### 4. Chạy full test suite + commit (XIN DUYỆT trước khi commit)
- `pytest tests -q` — mục tiêu ≥ 2,902 passed (2,884 + 18 citation + 7 OCR... tính lại theo thực tế), 0 failed.
- Commit message gợi ý: `feat(knowledge): page-level citation + docx tables + image OCR + KB RAG in chat (bước 2.9)`.
- Sau khi push: PATCH PR #1 (urllib + token qua `git credential fill`, không in log).

### 5. Viết master plan: BRAIN = TRUNG TÂM ĐIỀU HÀNH THIẾT BỊ (BACnet, SNMP, I2C, Modbus, MQTT...)
Yêu cầu gốc của anh: trợ lý nắm/điều khiển thiết bị ngoại vi qua mọi giao thức, mã nguồn mở, có phê duyệt quyền. **Đã audit xong khả năng tái sử dụng (đừng audit lại):**
- `gateway/connectors.py`: `Connector` ABC (fetch/send/health_check) + `CircuitBreaker` + mock connectors.
- `integration/`: `BaseConnectorAdapter`, `ConnectorManifest` + `ConnectorOperation` (đã có `risk_level` R0–R5, `autonomy_level` A0_OBSERVE→A3_OWNER_APPROVAL, `supports_dry_run`, `requires_approval`), `IntegrationPolicy` (block R5, sanitize output, detect prompt injection), `IntegrationRegistry.execute_and_verify` (policy pre-flight + verification dossier).
- `governance/policy.py`: `PolicyEngine` R0–R5 (R4=approval_required, R5 hard-block).
- Khoảng trống: `ConnectorType` enum chưa có loại field-bus/protocol (BACnet/SNMP/I2C/Modbus) — đề xuất thêm `FIELD_BUS`/`PROTOCOL_DEVICE` hoặc dùng metadata.
- Kiến trúc đề xuất: mỗi giao thức = 1 adapter dưới `integration/connectors/` khai báo manifest (operation READ = R0/A0, operation WRITE = R3/R4 requires_approval + dry_run bắt buộc); vòng điều khiển thời gian thực (I2C timing, PWM) nằm ở **Local Safety Runtime phía thiết bị**, Brain chỉ gửi intent cấp skill — tuyệt đối không cho LLM đụng GPIO/PWM trực tiếp; thư viện mã nguồn mở: bacpypes3 (BACnet), pysnmp (SNMP), python-periphery/smbus2 (I2C), pymodbus, paho-mqtt.
- Deliverable: báo cáo `reports/PHASE0_DEVICE_CONTROL_PLAN.md` (không code điều khiển thật) — kiến trúc, bảng giao thức/risk mapping, roadmap stage-gate, decisions cần anh duyệt. STOP chờ duyệt.

### 6. Các việc chờ khác (làm sau mục 1–5, theo thứ tự anh duyệt)
- PHASE 0 P1 Multi-Embodiment: tạo `src/quan_ai_brain/embodiment/` (EmbodimentAdapter ABC + CapabilityRegistry + KioskBodyAdapter) — đã có audit `reports/PHASE0_MULTI_EMBODIMENT_AUDIT.md`.
- Deploy Edge Agent V41 lên Pi5 (Pi5 `quanpt1@192.168.1.21` — kiểm tra IP mới của máy; khi PC đổi IP phải sửa `edge_client/config.json` core_host + config phía Pi rồi restart daemon).
- Lớp 2: refine system prompt + retrieval threshold theo bài giảng M3 (Bai3 Prompt Engineering, Bai4/5 RAG — 1,620 chunks đã có page).

## BÁO CÁO
Sau mỗi mục: báo cáo kết quả THẬT (kèm số liệu đo được), mục nào không xong phải nói rõ nguyên nhân. Cuối phiên: chạy `python tools/validate_and_report.py`, đảm bảo `reports/HANDOFF_LATEST.md` phản ánh đúng trạng thái.
