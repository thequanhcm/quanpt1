# VMAIL EXISTING SYSTEM AUDIT — Sprint 0 (CHERRY VMAIL INTELLIGENCE V1.0)

**Ngày:** 23/11/2026 · **Auditor:** TONY · **Card tiền điều kiện:** TASK-VMAIL-S1 (PENDING_APPROVAL)
**Chỉ thị owner:** "em cho thực hiện: # MASTER IMPLEMENTATION PROMPT CHERRY VMAIL INTELLIGENCE V1.0" (23/11/2026)
**Trạng thái:** AUDIT ONLY — không sửa production.

---

## 1. Cognitive Core (§3.1 master prompt)

| Yêu cầu audit | Kết quả | Bằng chứng |
|---|---|---|
| Core ở đâu | `src/quan_ai_brain/` — cognition + llm + web server 8765/8766 (watchdog respawn) | PROJECT_STATUS.md 13/11-18/11; live E2E các sprint trước |
| API gọi core | `POST /api/chat` (`_handle_api_chat` web/server.py) + `/api/chat/history` | Sprint 1 Core E2E (HANDOFF_LATEST §2) |
| Context + tool | `PromptContextBuilder` + `ChatToolBridge` (QPIG §IV) + Self-RAG lite (18/11) | PROJECT_STATUS 18/11; chat_bridge.py 11,901B |
| Session + lịch sử | `SessionMemoryManager` → SQLite WAL `data/brain.db` (episodes/memories) | HANDOFF_LATEST §2 |
| Phân quyền | ApprovalCardStore (R0-R5) + PolicyEngine + Autonomy LEVEL_A-D; approver duy nhất quanpt1 | governance/ hiện hành |

**Kết luận:** KHÔNG tạo core mới — Cherry Vmail Agent là lớp nghiệp vụ gọi `/api/chat` + ChatToolBridge.

## 2. Deep Memory (§3.2)

| Thành phần | Hiện trạng | Nơi có |
|---|---|---|
| Memory service | 3 tầng: session_memory (episodes/memories) + semantic_memory (ONNX MiniLM 6.578 chunks, recall@3 1.0) + workflow/task journal | cognition/, memory/, data/brain.db |
| Memory retrieval | hybrid keyword + semantic search `/api/memory/semantic/search`; Self-RAG grader kiểm căn cứ | 18/11 sprint |
| Epistemic status | VERIFIED/USER_PROVIDED/CANDIDATE(UNVERIFIED) — bắt buộc source_ref | self_check.py |
| Chống trùng | ingest idempotent theo `original_id` metadata | semantic_memory.py |
| KPI master prompt "Memory Context Relevance ≥90%" | recall@3 đã đo **1.0** trên 8 câu thật (memory_eval CSV) | data/memory_eval_report.md |

**Kết luận:** Đáp ứng §6 "không tạo memory riêng"; Memory Candidate cho email đi qua
cơ chế episodes/experience_lesson hiện có (candidate PENDING + LEVEL_A — không tự promote).

## 3. Agent Router / MCP / Governance (§3.3)

- Tool Registry: 25 tools từ QPIG/UAG (19 directive §2 + 6 alias); ToolSelector score
  `kw*0.4 + name*0.3 + op*0.1 - risk*0.2`, MIN_CONFIDENCE 0.25 (CAI V3.0 §III).
- Governance Gateway: ApprovalCard (consume-once) + ConsultationStore + NetChatApprovalAdapter.
- SENTINEL: agent_identity + threat_levels L0-L4 + containment 3 cấp (38 test).
- Input Injection Shield 12+ pattern EN+VN wired `/api/chat` + DM responder (27/27).
- MCP: chưa có MCP server thật — Vmail đi qua connector nội bộ + QPIG directive (không blockers).

## 4. Hệ thống email hiện có (§3.4)

| Thành phần | Trạng thái | Nơi có |
|---|---|---|
| Vmail read (SOAP) | **LIVE_VERIFIED 23/11** | `tools/mail_reader.py` (268 dòng): AuthRequest→SearchRequest/GetMsgRequest; latest/today/unread/from:/kw: |
| IMAP | **BỊ TỪ CHỐI** — mail.viettel.com.vn:993 mở nhưng LOGIN/AUTH PLAIN NO dù pwd đúng | audit 23/11 — KHÔNG retry |
| Intake pipeline | Sprint 9 `email_intake.py` (Mock + Vmail BLOCKED) + Sprint 1a `office/email_connector.py` (SOAPMailConnector + 10 nhóm + score) — LIVE smoke 10 mail | integration/ + office/ |
| Draft tool | `tools/email_draft.py` R2 DRAFT-ONLY (.eml, không SMTP/COM) | Sprint 8 |
| Email Intelligence | deterministic proposals (không LLM) | integration/email_intelligence.py |
| Browser automation | Playwright runtime + browser-use skill — dự phòng phương án C, KHÔNG cần khi SOAP đủ | env |
| Secret Manager | vault `E:/BRAIN/user, pass, token/` loader (vmail_username/vmail_password) | secrets-vault.md |
| Audit Logger | core/audit.AuditLogger.record | live |

## 5. Kết nối Vmail thực tế (§4.1-4.2) — PROBE THẬT 23/11

Chạy `tools/office_vmail_probe_sprint0.py` (READ-ONLY, 2.3s):

| Phương thức | Kết quả probe | Ghi chú |
|---|---|---|
| SOAP AuthRequest | **OK** (authToken) | pwd hợp lệ |
| GetFolderRequest | **OK — 13 folder**: Inbox, Sent, Drafts, Junk, Archive, Calendar, Tasks, Contacts, Briefcase, Chats... | đủ cho list_folders |
| GetInfoRequest | **FAIL HTTP 500** | sections="ident" không nhận — dùng fallback từ AuthResponse/lifetime |
| SearchRequest types=conversation | **OK — 3+ conversation** (id dạng `-39012`/`38481`) | get_thread khả thi |
| SearchRequest subject: | **OK — 5 hit** | search_messages khả thi |
| IMAP/SMTP | KHÔNG dùng (login bị từ chối) | §4.2 phương án B loại |
| Browser Automation | KHÔNG cần (SOAP đủ) | §4.2 phương án C dự phòng |
| Gửi qua SOAP (SendMsgRequest) | **KHÔNG probe** — R2 DRAFT-ONLY; chỉ khi owner phê duyệt riêng | §7.4 |

## 6. Gap analysis & lộ trình (tổng hợp 6 tài liệu §3.5 vào 1 file ngắn gọn)

**Đã có (tái sử dụng):** connector đọc SOAP (A-C phạm vi đọc), intake 10 nhóm, sprint S1
DM tóm tắt, memory 3 tầng + semantic, governance + shield + audit.

**Gap phải làm:**
1. **VMAIL-CONNECTOR-CLASS** (Sprint 1): bọc mail_reader thành class `VmailConnector`
   với interface đầy đủ §4.3 — implement CHỈ các operation đã probe OK (list_folders,
   list_messages, get_message, search_messages, get_thread, get_connection_health,
   authenticate, validate_session); các operation ghi (create_draft/send/mark_read/move)
   → khai báo `unsupported_by_policy` (fail-honest, không fake).
2. **THREAD-ANALYZER** (Sprint 2): dùng SearchRequest types=conversation (đã probe OK)
   ghép thread; mâu thuẫn → trình bày cả hai + nguồn.
3. **MEMORY-ADAPTER** (Sprint 3): retrieve_context qua memory hiện có; Memory Candidate
   qua experience_lesson (PENDING, owner duyệt mới promote).
4. **REPLY-DRAFT-3P** (Sprint 4): email_draft mở rộng 11 style §7.2 + quality check §7.3;
   SEND vẫn R3 phê duyệt riêng.
5. **WORKFLOW + BRIEFING** (Sprint 5-6): Daily Briefing §16; follow-up cần folder Sent
   (probe OK) — nhưng "chưa được phản hồi" chỉ kết luận khi check thread mới nhất (§9D).
6. **DASHBOARD** (§10): panel trên dashboard 8765 hiện có.
7. **DB**: tái sử dụng `data/email_intake.db` (đã có) — thêm cột thread_id/classification
   khi duyệt; KHÔNG tạo memory db riêng (§12).

**Security gaps:** gửi email chưa có đường verify Sent-folder qua SOAP (chỉ làm khi
owner duyệt SEND); prompt injection từ attachment chưa scan (input_shield hiện bọc
DM + chat text, cần wire vào email body trước LLM).

## 7. Kết luận Sprint 0

- Nền QUAN AI BRAIN đáp ứng ~70% yêu cầu §1-3 master prompt (connector đọc + intake +
  memory + governance) — phần còn lại là lớp mỏng, không core thứ hai.
- SOAP là phương thức kết nối ĐÃ KIỂM CHỨNG (không giả định — §4.1); IMAP loại.
- Đề xuất card kế: **TASK-VMAIL-S1** = Sprint 1 connector class + tests (R1, chỉ đọc).

---
*Fail-honest: mọi trạng thái từ probe thật 23/11 trên máy QUANPT + source hiện hành;
GetInfoRequest FAIL được ghi nguyên trạng, không giấu.*
