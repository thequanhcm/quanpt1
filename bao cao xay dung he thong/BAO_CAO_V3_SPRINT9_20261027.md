# BÁO CÁO V3 SPRINT 9 — DIGITAL EMPLOYEE WORKBENCH & EXPERIENCE INTELLIGENCE

**Ngày:** 27/10/2026
**Card:** TASK-V3-SPRINT9 (PENDING_APPROVAL → APPROVED → consumed; duyệt bởi quanpt1 qua MASTER PROMPT V3 SPRINT 9 trên desktop)
**Commit:** `679b6e9`
**Trạng thái:** HOÀN TẤT theo phạm vi đã duyệt — full regression **817 passed / 1 skipped / 0 fail** (799 → +18)

## 1. Audit trước khi triển khai (Bước 1–3 của master prompt)

**Baseline chạy lại thực tế:** 799 passed / 1 skipped / 0 fail — khớp báo cáo Sprint 8.

**Ma trận năng lực (tóm tắt):**

| Năng lực | Trạng thái xác minh |
|---|---|
| CognitiveLoop, ReflectionLoop, InformationGapAnalyzer | Đã có và hoạt động (cognition/, test đủ vòng đời) |
| ApprovalGate / ApprovalCardStore / PolicyEngine R0–R5 | Đã có và hoạt động; R5 hard-block giữ nguyên, KHÔNG sửa |
| DurableTaskRegistry (tasks.db) | Đã có và hoạt động (lifecycle đầy đủ, recover_in_flight) |
| ConsultationStore, GovernanceStateStore | Đã có và hoạt động |
| Experience/Episodic Memory (MemoryStore) | Đã có (episodes + memories + lifecycle) — thêm retrieval ở (D) |
| To-do store + API (Sprint 8) | Đã có và hoạt động |
| Email draft .eml (Sprint 8) | Đã có — draft-only; bổ sung metadata ở (C) |
| Email connector THẬT (Vmail) | **Bị chặn** — mật khẩu SSO đã lộ; giữ BLOCKED (§IX) |
| Workbench UI tổng hợp | Chưa có → xây mới ở (A)+(B) |
| Web/internal connector | Chưa có — KHÔNG nằm trong scope Sprint 9 (để Sprint 12) |

Không viết lại module nào đã có; không tạo bộ nhớ/approval engine/cognitive loop trùng chức năng.

## 2. Những gì đã triển khai (đúng phạm vi card)

### (A) Overview API — `GET /api/workbench/overview`
Số liệu **thật** tổng hợp từ 4 DB hiện có + probe dịch vụ cục bộ (8765/8766/11434).
**Fail-honest:** mỗi khối độc lập; nguồn lỗi → `"CHƯA XÁC MINH"` kèm lỗi gốc — test chứng minh DB hỏng (bytes rác) KHÔNG bao giờ hiện số 0 giả.

### (B) Tab Workbench trong dashboard (`/executive`)
- 5 thẻ tổng quan (nhiệm vụ mở, chờ phê duyệt, to-do, thiếu thông tin, dịch vụ) — badge tab hiện số pending.
- **Nhiệm vụ:** list thật từ DurableTaskRegistry + lọc đúng enum `TaskStatus` (PENDING/IN_PROGRESS/WAITING_APPROVAL/APPROVED/...), không chế trạng thái UI.
- **Approval Center UI:** duyệt/từ chối qua `/api/approvals/decide` — consume-once, reject bắt buộc lý do (prompt), chống double-submit, hiển thị trung thực 409 (đã xử lý) / 404 (không tồn tại) / 403 (không phải localhost). KHÔNG coi bấm nút là thành công — chỉ tin HTTP status + body server xác nhận.
- **To-do UI:** list/add/done, nút disable khi đang gửi (chống trùng), lỗi hiện rõ.
- Ghi đúng giới hạn: phê duyệt qua dashboard **chỉ localhost** — không quảng bá thành xác thực danh tính mạnh; không mở API ra mạng ngoài.

### (C) Email intake + draft metadata
- `integration/email_intake.py`: `EmailConnector` Protocol (thay thế được) + `MockEmailConnector` (bắt buộc ghi `source="mock"` trên từng email) + `VmailConnector` (**BLOCKED** — trung thực, fetch trả rỗng, không đăng nhập).
- Phân loại 4 nhóm bằng luật rõ ràng (ACTION_REQUIRED / FYI / NEWSLETTER / UNCLEAR); email quảng cáo không tạo nhiệm vụ.
- **Dedupe chứng minh:** sync lần 1 = 3 new; sync lần 2 = 0 new / 3 duplicates; store không tăng.
- Connector DISCONNECTED → sync trả 0 fetched, không giả vờ đã đọc (test §X.10).
- API `/api/email/intake` (GET, đọc-only) + `/api/email/intake/sync` (POST, localhost-only).
- `create_draft()` bổ sung header truy vết `X-QAB-Task-Id` / `X-QAB-Source-Email-Id` / `X-QAB-Draft-Reason` — **backward compatible** (API cũ chạy nguyên, test chứng minh). Vẫn **draft-only tuyệt đối** — không có đường gửi.

### (D) Experience retrieval
`memory/experience_retrieval.py` — `find_similar_experiences()` trên MemoryStore **hiện có**:
- Tách **confirmed** (VERIFIED/OBSERVED/USER_PROVIDED) và **candidates** (CANDIDATE/UNVERIFIED — ghi rõ "ứng viên, chưa duyệt"); test chứng minh CANDIDATE không lẫn vào confirmed.
- Kinh nghiệm **superseded** bị loại (test chứng minh).
- Chỉ là **nguồn tham chiếu** cho suy luận/đề xuất — không có quyền thực thi (không nối vào executor).

## 3. Kiểm chứng thực tế (khác mock)

- Full regression **817/0/1** trên môi trường thật; 18 test mới đều mock/tmppath (không đụng DB thật, không mail thật, không credential).
- **Smoke thật trên server live** (dual server do watchdog tự respawn sau khi tôi kill để nạp code — đúng thiết kế Sprint 7, PID 13772):
  - `/api/workbench/overview` → tasks 50 (25 PENDING + 25 CANCELLED), approvals 8 (7 APPROVED, 0 pending sau khi card Sprint 9 consume), todos OK, gaps → CHƯA XÁC MINH đúng (bảng chưa có), services 3/3 CONNECTED.
  - `/api/workbench/tasks?limit=2` → trả nhiệm vụ thật.
  - `/api/email/intake/sync` → result mock, `vmail_status: BLOCKED`.
  - `/executive` serve tab Workbench đầy đủ element.
- Lỗi thật bắt được khi smoke: `/api/workbench/tasks` parse query string sai → sửa + test lại (đã đưa vào commit).

## 4. Giới hạn trung thực (chưa làm / chưa kiểm chứng)

1. **Email intake là MOCK** — dữ liệu 3 email giả lập ghi rõ `source="mock"`. Email thật phải đợi: (1) anh đổi mật khẩu SSO, (2) cấu hình an toàn, (3) phê duyệt riêng (Sprint 10 theo lộ trình).
2. **Experience retrieval là tra cứu từ khoá (LIKE)** — chưa semantic search; đánh giá độ phù hợp chi tiết để Sprint 11.
3. Chưa có luồng tự động "email → tạo nhiệm vụ" — phân loại chỉ lưu DB, chưa nối sinh task (cần thiết kế + duyệt riêng).
4. UI Workbench dùng trên desktop (localhost:8765/executive → tab 🧰).
5. Web/internal app connector (§V) chưa triển khai — đúng lộ trình đề xuất Sprint 12.
6. 1 skipped là test Pi 5 phần cứng thật (không liên quan Sprint 9).

## 5. Governance checklist (§VIII)

- [x] Không tự phê duyệt — card Sprint 9 duyệt bởi anh qua master prompt, consume-once.
- [x] R5 hard-block + PolicyEngine không bị sửa (chỉ đọc/laravel tham chiếu).
- [x] Không có đường gửi email; không bypass ApprovalGate; approval trùng → 409.
- [x] Không có secret trong code/log/test (chỉ dùng workspace DB mock).
- [x] Vmail giữ BLOCKED, hiển thị BLOCKED trên UI.
- [x] Timeout/im lặng không được hiểu là đồng ý (UI chỉ tin response server).
- [x] Restart không mất trạng thái chờ (tasks.db/governance.db/todos.db là durable; dual server đã sống qua 2 lần respawn trong session này).

## 6. Trạng thái Git & việc chờ anh

- Commit: `679b6e9` (code + tests + tool lập card). Git tree sạch sau commit.
- **Chờ anh:** (1) đổi mật khẩu SSO (ưu tiên — đã lộ, Vmail vẫn khoá vì điều này); (2) mở dashboard `http://127.0.0.1:8765/executive` → tab **🧰 Workbench** dùng thử; (3) quyết định Sprint 10 (Real Email Intelligence read-only) sau khi mật khẩu đã đổi — sẽ lập card riêng chờ duyệt, không tự triển khai.
