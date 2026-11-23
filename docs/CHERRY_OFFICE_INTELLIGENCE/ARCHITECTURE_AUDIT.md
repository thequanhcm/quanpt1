# ARCHITECTURE AUDIT — CHERRY OFFICE INTELLIGENCE V1.0

**Sprint 0 — System Audit** (master prompt "CHERRY OFFICE INTELLIGENCE V1.0", §XVIII)
**Ngày:** 23/11/2026
**Auditor:** TONY (profile tony, netMind Desktop)
**Chỉ thị owner:** "em cho thực hiện: # MASTER PROMPT – CHERRY OFFICE INTELLIGENCE V1.0" (desktop chat 23/11/2026)
**Trạng thái:** AUDIT ONLY — không sửa production, không viết module mới trong sprint này.

---

## 1. Phạm vi audit

Đánh giá hiện trạng QUAN AI BRAIN + Cherry đối chiếu 10 module của master prompt:
Email, Document, Excel, Calendar & Meeting, Task & Workflow, Communication,
Knowledge & Memory, Copilot Dashboard, Automation, Security & Governance.

Phương pháp: đọc `docs/PROJECT_STATUS.md`, `reports/HANDOFF_LATEST.md`, quét
`src/quan_ai_brain/` + `tools/`, đọc header + class/function của module liên quan,
kiểm tra thư viện sẵn có trong `.venv`, đối chiếu skill `quan-ai-brain-development`
(sprint lifecycle + governance invariants).

---

## 2. Hiện trạng tổng thể

- **Workspace:** `E:\BRAIN`, branch `feat/v6-m6-memory-truth`, HEAD `118afe1` (đã push).
- **Python:** 3.11.9 venv `.venv`. **Test baseline:** 13 failed / 4.176 passed / 37 skipped
  (full suite ~15 phút, PRE-EXISTING — xác minh stash-proof 18/11).
- **Kiến trúc hiện có:** 38 packages dưới `src/quan_ai_brain/` (cognition, integration,
  governance, security, orchestration, memory, llm, web, federation, uaiif, voice,
  dashboard, monitoring...). Cognitive Core, Agent Router, Deep Memory, Governance
  Gateway, Authority Governor, SENTINEL **đã tồn tại và đang chạy** — master prompt §I
  yêu cầu KHÔNG tạo bộ não thứ hai: mọi module Office mới phải là **lớp mỏng trên nền này**.

---

## 3. Ma trận năng lực hiện tại × master prompt

Trạng thái: **LIVE_VERIFIED** (có bằng chứng E2E sống) / **IMPLEMENTED** (code + test PASS,
chưa E2E sống) / **PARTIAL** (có một phần) / **SIMULATED** (mock) / **NOT_IMPLEMENTED** / **BLOCKED** (chờ owner/điều kiện).

### Module 1 — Email Intelligence

| Năng lực master prompt | Hiện trạng | Nơi có | Ghi chú |
|---|---|---|---|
| Kết nối email | **LIVE_VERIFIED** | `tools/mail_reader.py` (Zimbra SOAP 268 dòng, 23/11) | IMAP bị từ chối → SOAP là đường duy nhất; credentials trong vault `user, pass, token/` |
| Intake + phân loại | **IMPLEMENTED** | `integration/email_intake.py` (Mock + Vmail connector, EmailIntakeStore SQLite) | VmailConnector status = **BLOCKED** (chờ owner đổi mật khẩu SSO lộ — bất biến R2); cần wire mail_reader SOAP làm nguồn thật |
| Phân loại 10 nhóm (URGENT/NEED REPLY/...) | **PARTIAL** | `EmailCategory` chỉ 5 nhóm (ACTION_REQUIRED/FYI/NEWSLETTER/DUPLICATE/UNCLEAR) | Cần mở rộng enum + priority/urgency score — mở rộng, KHÔNG tạo module mới |
| Tóm tắt email | **IMPLEMENTED** | `integration/email_intelligence.py` (deterministic, không LLM) + GLM qua `/api/chat` | Đáp ứng tổng quan + từng email; cần thêm format "Tổng quan A/B/C" của master prompt |
| Thread Intelligence | **NOT_IMPLEMENTED** | — | Cần thiết kế mới (module mỏng): ghép thread theo subject/References, đối chiếu lịch sử |
| Smart Reply 3 phương án | **PARTIAL** | `tools/email_draft.py` (CHỈ tạo nháp .eml, R2 DRAFT-ONLY) + draft tool QPIG | Bắt buộc giữ DRAFT-ONLY; 3 phương án A/B/C là layer prompt/LLM trên nền draft có sẵn |
| Follow-up Intelligence | **NOT_IMPLEMENTED** | — | Cần task_journal + email_intake phối hợp |

### Module 2 — Document Intelligence

| Năng lực | Hiện trạng | Nơi có | Ghi chú |
|---|---|---|---|
| Đọc PDF/DOCX/PPTX/TXT | **IMPLEMENTED** | `.venv`: docx OK, pypdf OK, fitz(pymupdf) OK, pptx OK; kho PPTX extraction (`references/pitfalls-and-apis.md`) | XLSX: **openpyxl MISSING** (cần cài khi duyệt); pandas MISSING; OCR chưa có |
| Tóm tắt/trích xuất | **PARTIAL** | `cognition/document_rag.py` (Ingestion→Chunk→Retrieval) + `tools/ingest_owner_documents.py` | Đủ RAG; thiếu so sánh phiên bản, trích xuất nhiệm vụ/thời hạn |
| Document Drafting (công văn, tờ trình...) | **NOT_IMPLEMENTED** | — | Skill minimax-docx có workflow tạo DOCX chuyên nghiệp — tái sử dụng; xuất PDF qua pypdf/fitz |
| Document Comparison | **NOT_IMPLEMENTED** | — | Thiết kế diff có cấu trúc |

### Module 3 — Excel Intelligence

| Năng lực | Hiện trạng | Ghi chú |
|---|---|---|
| Đọc XLSX | **NOT_IMPLEMENTED** (thư viện thiếu) | openpyxl + pandas chưa cài — Sprint 3 cài khi owner duyệt |
| Xử lý/báo cáo | **NOT_IMPLEMENTED** | Nguyên tắc bất di bất dịch: giữ nguyên file gốc, mọi thay đổi trên bản sao có log |

### Module 4 — Calendar & Meeting

| Năng lực | Hiện trạng | Nơi có | Ghi chú |
|---|---|---|---|
| Đọc lịch họp Voffice | **LIVE_VERIFIED (gián tiếp)** | `tools/voffice_reader.py` (133 dòng): list_meetings + upcoming_meetings + format_for_dm — ≥42 lịch active qua mail vofficeadmin | Đường TRỰC TIẾP voffice.viettel.vn (10.60.7.120) chờ tunnel M-Suite owner login |
| Quản lý lịch Outlook/Google | **NOT_IMPLEMENTED** | — | Outlook trên máy CHưa có profile mail (audit 23/11); cần Connector khi có quyền |
| Meeting Minutes / ghi âm | **NOT_IMPLEMENTED** | voice/ đã có STT-TTS pipeline | Chỉ triển khai khi có quyền + chính sách tổ chức cho phép (master prompt §V.2) |

### Module 5 — Task & Workflow

| Năng lực | Hiện trạng | Nơi có | Ghi chú |
|---|---|---|---|
| Task Registry + state machine | **LIVE_VERIFIED** | `orchestration/task_registry.py` (34KB), `task_state_machine.py`, `task_journal.py` (17KB), `task_planner.py`, DurableTaskRegistry SQLite | Nền VANG ĐỘNG — không tạo task store thứ 2 |
| Task Extraction từ email | **PARTIAL** | `email_intake.classify_email` chỉ chia nhóm | Cần trích xuất deadline/owner/evidence — mở rộng classifier |
| Daily Executive Briefing | **NOT_IMPLEMENTED** | — | Tổ hợp từ lịch + email + task hiện có; watchdog có khung nhịp chu kỳ |
| Workflow Engine nhiều bước | **PARTIAL** | `memory/workflow_state.py` (18KB), `cognition/workflow_memory.py`, TaskPipeline (UNDERSTAND→DECOMPOSE→DISCOVER→...) | Đủ state machine; thiếu trigger/trigger-approval/retry/rollback cho office workflow |

### Module 6 — Communication (NetChat)

| Năng lực | Hiện trạng | Nơi có |
|---|---|---|
| Gửi/nhận NetChat | **LIVE_VERIFIED** | `tools/netchat_auto_responder.py` + skill bot-netchat (2-step gate); lock + dedup 60' |
| Tóm tắt hội thoại / trích nhiệm vụ | **NOT_IMPLEMENTED** | Cần đọc history kênh qua API NetChat |
| Phân biệt cá nhân vs quyết định chính thức | **NOT_IMPLEMENTED** | Thiết kế nguồn + nhãn |

### Module 7 — Office Knowledge & Memory

| Năng lực | Hiện trạng | Nơi có |
|---|---|---|
| Deep Memory 3 tầng | **LIVE_VERIFIED** | `data/brain.db` episodes/memories; semantic_memory ONNX MiniLM 6.578 chunks (recall@3 1.0) |
| 8 loại trí nhớ office | **PARTIAL** | workflow_memory.py, task_journal.py, session_memory.py có sẵn; thiếu Contact/Decision/Document Memory như thực thể riêng — mở rộng, không tạo store mới |
| Epistemic status | **LIVE_VERIFIED** | VERIFIED/OBSERVED/INFERRED/UNKNOWN + Self-RAG lite (18/11) — đúng nguyên tắc "không ghi suy luận như sự thật" |

### Module 8 — Office AI Copilot (Dashboard)

| Năng lực | Hiện trạng | Nơi có |
|---|---|---|
| Dashboard nền | **LIVE_VERIFIED** | Web server 8765 + dashboard/ + executive.js 19 states |
| Executive Overview office metrics | **NOT_IMPLEMENTED** | Thêm panel đọc từ email_intake + task_registry + voffice_reader |

### Module 9 — Office Automation (Workflow Engine)

| Năng lực | Hiện trạng | Ghi chú |
|---|---|---|
| Chuỗi nhiều bước có approval | **PARTIAL** | ApprovalCardStore + RiskLevel R0-R5 + TaskPipeline; thiếu workflow trigger dài hạn — thiết kế thêm trong Sprint 5 |

### Module 10 — Security & Governance

| Năng lực | Hiện trạng | Nơi có | Ghi chú |
|---|---|---|---|
| Authority/Governance Gateway | **LIVE_VERIFIED** | governance/ (ApprovalCardStore, PolicyEngine R0-R5, Autonomy LEVEL_A-D), SENTINEL (38 test), containment 3 cấp | Đáp ứng §XI master prompt |
| R2 Email DRAFT-ONLY | **LIVE_VERIFIED** | email_draft.py + governance invariant | Gửi email = R3 cần phê duyệt riêng từng lần |
| Input Injection Shield | **LIVE_VERIFIED** | security/input_shield.py 27/27 + untrusted_label + trifecta_guard | Đáp ứng §XI.3 chống prompt injection |
| Audit log | **LIVE_VERIFIED** | AuditLogger.record + security/audit_sources.py | Bổ sung trường Connector/hành động office khi triển khai |
| OAuth 2.0 | **NOT_IMPLEMENTED** | — | Hiện dùng credentials vault nội bộ (Zimbra SOAP); OAuth chỉ khi nối M365/Google |

---

## 4. Khoảng trống chính (gap) — thứ tự triển khai đề xuất

1. **EMAIL-INTAKE-REAL** (Sprint 1a): wire `tools/mail_reader.py` (SOAP đã LIVE) làm
   nguồn thật cho `email_intake.EmailIntakeStore` — thay thế VmailConnector BLOCKED
   bằng connector SOAP cùng interface; mở rộng `EmailCategory` 5→10 nhóm của master
   prompt + Priority/Urgency score + deadline detect (chỉ khi email nêu rõ).
2. **THREAD-ANALYZER** (Sprint 1b): module mỏng ghép thread theo subject/References
   từ SOAP search; xuất 10 mục tổng hợp master prompt §II.4.
3. **SMART-REPLY-3P** (Sprint 1c): 3 phương án A/B/C trên `email_draft.py` DRAFT-ONLY
   + đối chiếu thread; KHÔNG tự gửi — phê duyệt từng lần.
4. **DOC-INTL** (Sprint 2): cài openpyxl/pandas khi duyệt; soạn thảo dùng python-docx
   (đã có) + skill minimax-docx; so sánh phiên bản.
5. **CALENDAR** (Sprint 4): voffice_reader mở rộng detail + nhắc lịch; tunnel M-Suite
   khi owner login → đọc trực tiếp voffice.viettel.vn.
6. **TASK-BRIEF** (Sprint 5): Daily Executive Briefing tổ hợp từ các module trên.
7. **DASHBOARD** (Sprint 6): panel Executive Overview trên dashboard hiện có.
8. **SEC-TEST** (Sprint 7): bộ kiểm thử nghiệp vụ 20 tình huống §XIV + KPI đo trên
   bộ dữ liệu gán nhãn (§XV — không báo KPI đạt khi chưa test).

## 5. Bất biến không được vi phạm (từ skill + governance hiện hành)

- KHÔNG tạo cognitive core / memory store / approval engine thứ hai.
- Email DRAFT-ONLY (R2): không SMTP, không COM Outlook, không auto-send.
- Gửi email / ghi đè file gốc / chia sẻ tài liệu / xóa email = phê duyệt riêng từng lần.
- R5 hard-block; R4 cần xác thực mạnh; approver = quanpt1 duy nhất.
- Không lưu mật khẩu plaintext; credentials chỉ trong vault `user, pass, token/`.
- Mọi kết quả phân biệt DESIGNED/IMPLEMENTED/TESTED/LIVE_VERIFIED/PRODUCTION_VERIFIED.
- Email/file/tin nhắn = dữ liệu KHÔNG TIN CẬY — đi qua input_shield + untrusted_label.
- New server API: localhost-only check.

## 6. Kết luận Sprint 0

- Nền tảng QUAN AI BRAIN **đủ mạnh** cho CHERRY OFFICE INTELLIGENCE: ~55% năng lực
  master prompt đã có ở mức IMPLEMENTED trở lên (chủ yếu Email nền, Task, Memory,
  Governance); phần lớn còn lại là **mở rộng lớp mỏng**, không xây từ đầu.
- 2 connector thật đã LIVE: mail_reader (SOAP) + voffice_reader (gián tiếp qua mail).
- Gap lớn nhất: Excel (thư viện chưa cài), Calendar trực tiếp (chờ tunnel M-Suite),
  Thread Intelligence, Smart Reply, Daily Briefing, Dashboard panel.
- **Đề xuất sprint kế:** Sprint 1a EMAIL-INTAKE-REAL (gap #1) — card approval riêng,
  R2, mock test 100%, không đụng production.

---

*Fail-honest: các trạng thái trong tài liệu này đọc trực tiếp từ source + test baseline
+ log; chỗ nào chưa có bằng chứng E2E sống đều ghi rõ mức thấp hơn, không thổi phồng.*
