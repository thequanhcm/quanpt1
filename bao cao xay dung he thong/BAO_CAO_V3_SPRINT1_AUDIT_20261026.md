# SPRINT 1 (MASTER PROMPT V3) — AUDIT HIỆN TRẠNG & THIẾT KẾ LUỒNG CÔNG VIỆC/PHÊ DUYỆT

**Mã báo cáo:** RPT-QAB-V3-SPRINT1-AUDIT-20261026
**Thời điểm audit:** 26/10/2026 23:44 UTC (27/10 ~06:44 ICT)
**Cơ sở:** MASTER PROMPT — QUAN AI BRAIN DIGITAL EMPLOYEE V3 (nguyên văn của chủ sở hữu)
**Phạm vi:** Audit read-only. Không sửa code nghiệp vụ, không commit (Mục X.15, XV V3).

---

## 1. KẾT QUẢ AUDIT MODULE THEO TRẠNG THÁI TRUNG THỰC

### 1.1. VERIFIED_ACTIVE (đã xác minh bằng test chạy thật đêm 26/10)

| Thành phần | Bằng chứng |
|---|---|
| `ApprovalGate` (tools/approval.py, 278 dòng) | Fingerprint SHA-256 chống sửa tham số (dòng 33–49); evaluate_approval chặn revoked/consumed/expired/fingerprint-mismatch (192–226); consume một-lần (228–245). Test: test_approval_gate.py PASS |
| `GovernanceStateStore` (governance/state_store.py, 859 dòng) | SQLite bền vững `data/governance.db`: save/get request+approval+grant, consume, revoke, nonce, verify_integrity, PathGuard. Test: test_governance_state_store.py PASS |
| `PolicyEngine` R0–R5 (governance/policy.py) | R5 BLOCKED cứng dòng 51–52; R4 → APPROVAL_REQUIRED; R2 chỉ ghi trong workspace (PathGuard). Test PASS |
| `ConsultationStore` (governance/consultation_inbox.py) | Ticket DRAFT→PENDING_REVIEW→APPROVED/DIRECTED/REJECTED; DB thật 5 tickets (4 APPROVED) |
| `DurableTaskRegistry` (orchestration/task_registry.py) | 19 cột task: idempotency_key, acceptance_criteria_json, approved_scope_json, checkpoint, evidence_refs; recover_in_flight_tasks; DB thật 168 tasks. Test PASS |
| `CognitiveLoop` (cognition/cognitive_loop.py, 374 dòng) | 11 trạng thái lifecycle; fail-closed thiếu acceptance_criteria; approve(task_id, decision, guidance) duyệt ticket theo task rồi mới cho tick() chạy tiếp (dòng 220+); restart → OUTCOME_UNKNOWN. Test 17/17 PASS |
| `ReflectionLoop` (cognition/reflection.py, 271 dòng) | reflect_task + persist_lessons (lesson→episodic, hypothesis→quarantine). Test PASS |
| `DelegationRegistry` (tools/delegation.py) | GrantStatus, DelegationRegistry — test test_delegation.py PASS (chưa nối DB thật) |
| `OwnerSignatureVerifier` (tools/signature.py) | TrustAnchor, verify_signature, consume_signature_nonce — test PASS (chưa nối NetChat) |
| NetChat Command Center (tools/netchat_command_center.py, commit 842d30a) | 24/24 test; routing phê duyệt/trạng thái/báo cáo/nhiệm vụ/tri thức; chống câu hỏi giả lệnh |
| Auto-responder 2 chiều | Responder đọc đúng kênh 4phc9b1mx78qjq3grxcw89u94a, không re-spam, catch-up 60 phút |

**Focused regression đêm nay:** 81/81 PASS (approval_gate, governance_state_store, owner_signature, authenticated_verifier, delegation, consultation_inbox, durable_task_registry, cognitive_loop).

### 1.2. IMPLEMENTED_UNTESTED (có code, chưa xác minh E2E trong luồng V3)

- `AuthenticatedVerifier` (tools/verifier.py) — có test đơn vị, chưa chạy trong luồng phê duyệt NetChat thật.
- `LearningPromotionPolicy` (memory/promotion_policy.py) — dry-run đã chạy, chưa áp chính thức (chờ quyết định dedup của chủ sở hữu).
- Khoản phục hồi sau restart của CognitiveLoop — có test đơn vị, chưa drill với approval đang chờ thật.

### 1.3. PLANNED (thiết kế có, code chưa có)

- GAP-X1: Approval Card đầy đủ qua NetChat + `/api/approvals/*` (server chưa có route).
- GAP-X3: DelegationGrant engine nối DB (bảng `delegation_grants` đã có, 0 dòng).
- GAP-X5: Test phê duyệt hết hạn/replay bị từ chối (chưa có scenario riêng).
- EmailWorkAdapter / InternalWebWorkAdapter: chỉ có connectors mock + system_telemetry — chưa có adapter email/web thật (đúng nguyên tắc read-only/draft-only trước phê duyệt riêng).

### 1.4. UNVERIFIED / KHÔNG TỒN TẠI (trung thực: không tạo module giả)

Theo Mục XI V3, các trách nhiệm CHƯA có code, phải xây mới hoặc mở rộng:

| Trách nhiệm V3 | Hiện trạng thật | Phương án |
|---|---|---|
| TaskUnderstandingEngine | KHÔNG TỒN TẠI | Sprint 3: mở rộng CognitiveLoop giai đoạn UNDERSTANDING + context_builder |
| InitiativeEngine | KHÔNG TỒN TẠI | Sprint 3: lớp quét email/web/task treo, gom đề xuất, chống nhiễu |
| WorkContextBuilder | context_builder.py có sẵn (memory retrieval) | Mở rộng thêm nguồn email/web khi connector có |
| ApprovalOrchestrator | CÁC MẢNH ĐÃ CÓ: ApprovalGate + GovernanceStateStore + ConsultationStore + CognitiveLoop.approve | **Sprint 2: ghép thành orchestrator duy nhất, KHÔNG tạo vòng mới cạnh tranh** |
| NetChatApprovalAdapter | Chỉ có command center 1 chiều (duyệt ticket FIFO) | **Sprint 2: xây adapter gửi Approval Card + nhận DUYỆT/TỪ CHỐI theo mã task** |
| WorkExecutionCoordinator | PlanOrchestrator + InertExecution có sẵn | Mở rộng interface, không viết lại |
| OutcomeVerificationEngine | CognitiveLoop VERIFYING + acceptance_criteria có sẵn | Mở rộng kiểm chứng bằng bằng chứng ngoài (email/web) sau khi có connector |
| ExperienceMemoryEngine | KHÔNG TỒN TẠI | Sprint 5: bảng `experiences` mới (additive) + ReflectionLoop persist_lessons |
| TaskAccountabilityReporter | Có khuôn mẫu báo cáo 5 dòng trong quy trình làm việc hiện tại | Sprint 6: chuẩn hóa theo mẫu V3 Mục VII |
| EmailWorkAdapter / InternalWebWorkAdapter | KHÔNG TỒN TẠI | Sprint 4: read-only + draft-only trước, ghi phải có phê duyệt riêng |

### 1.5. Số liệu DB thật (đo lại 23:44 UTC 26/10)

- `data/tasks.db`: 168 durable_tasks (PENDING 113, CANCELLED 52, COMPLETED 2, IN_PROGRESS 1).
- `data/governance.db`: approval_requests **0**, approvals **0**, delegation_grants **0**, consumed_nonces **0**, governance_events 383, emergency_states 193. → *Cơ chế đã sẵn sàng nhưng chưa có phê duyệt thật nào đi qua.*
- `data/consultations.db`: 5 tickets (4 APPROVED, 1 APPROVED — không còn PENDING).
- `data/brain.db`: semantic 821 (mới ghi chỉ thị kênh 2 chiều #821), quarantined ~43,4xx, episodes 520.
- `logs/audit.jsonl`: >500 dòng, ghi liên tục.

---

## 2. THIẾT KẾ LUỒNG PHÊ DUYỆT (Sprint 2) — GHÉP, KHÔNG XÂY LẠI

### 2.1. State machine phê duyệt — ánh xạ sang hệ hiện hữu

Trạng thái V3 (Mục 5.3) → ánh xạ cụ thể:

| V3 | Dùng sẵn | Ghi chú |
|---|---|---|
| DRAFT | ConsultationStore.create_ticket (DRAFT) | |
| PENDING_APPROVAL | ApprovalRequest.status=PENDING_OWNER_APPROVAL + ticket PENDING_REVIEW + task WAITING_APPROVAL | 3 lớp cùng một mã `task_id` |
| APPROVED | ApprovalGate.grant_approval(approver='quanpt1') | Lưu governance.db, một-lần dùng |
| REJECTED | deny_approval + ticket REJECTED | Task bị BLOCK theo CognitiveLoop |
| EXPIRED | evaluate_approval hết hạn | Cần thêm expiration mặc định cho request (hiện chưa có TTL mặc định — thêm vào Sprint 2) |
| CANCELLED | revoke_approval + ticket CANCELLED | |
| EXECUTING / VERIFYING / COMPLETED / FAILED | TaskStatus IN_PROGRESS → CognitiveLoop tick() | |
| OUTCOME_UNKNOWN | recover_in_flight_tasks + CognitiveLoop recovery | Đã có, giữ nguyên |

### 2.2. NetChatApprovalAdapter — luồng đủ 11 bước V3 (Mục 5.1)

```
DETECT→UNDERSTAND→INVESTIGATE→PROPOSE (CognitiveLoop: RECEIVED..RISK_ASSESSMENT)
→ SEND_APPROVAL_REQUEST  [MỚI: adapter gửi Approval Card ≤5 mục theo Mẫu VI vào kênh
   4phc9b1mx78qjq3grxcw89u94a, kèm mã TASK-XXXX + fingerprint rút gọn]
→ WAIT_FOR_OWNER          [task WAITING_APPROVAL, KHÔNG timeout tự thực hiện]
→ VALIDATE_APPROVAL       [MỚI: nhận tin "DUYỆT TASK-XXXX" từ kênh →
   (a) xác minh user_id người gửi = chủ sở hữu (bảng 2.3)
   (b) đối chiếu mã task + fingerprint + trạng thái PENDING + chưa consumed/expired/revoked
   (c) ApprovalGate.grant_approval(approver='quanpt1') → consume một-lần]
→ EXECUTE_APPROVED_ACTION [CognitiveLoop.approve(task_id) → tick() chạy đúng approved_scope]
→ VERIFY_RESULT           [VERIFYING theo acceptance_criteria]
→ REPORT                  [báo cáo 5 mục Mẫu VII gửi NetChat]
→ LEARN_FROM_OUTCOME      [ReflectionLoop; kinh nghiệm vào đúng loại A–E Mục 8.2]
```

Chống giả mạo/replay (Mục X.11): phê duyệt phải khớp fingerprint; một-lần dùng (consume); nonce đã có bảng; tin nhắn lặp KHÔNG thực thi lần hai.

### 2.3. Mô hình danh tính chủ sở hữu (trung thực về mức bảo đảm)

- **Cấp 1 (mặc định Sprint 2):** kênh là private 2 thành viên (anh Quân `3b1ughs36i8e9p46im8opnms8w` + bot `edojmne9d7gcxx8axu1mzas3pr`); adapter chỉ chấp nhận phê duyệt từ `user_id` của chủ sở hữu qua bot gateway (token bot, không phải token người). = "danh tính tài khoản NetChat".
- **Cấp 2 (tùy chọn cho R4):** chữ ký OwnerSignatureVerifier (đã VERIFIED_ACTIVE) — chủ sở hữu ký lệnh bằng key; adapter xác minh trước khi grant.
- Giới hạn được ghi rõ: cấp 1 chứng minh tin đến từ tài khoản NetChat đó, không phải sinh-trắc-học. R4 khuyến nghị cấp 2; R5 không bao giờ.

### 2.4. Khuôn mẫu tin nhắn (đúng Mẫu VI, ≤5 đầu mục)

```
[XIN PHÊ DUYỆT] — Mã nhiệm vụ: TASK-xxxxxxxx
1. Mục đích: ...
2. Căn cứ/Hiện trạng: ... (bằng chứng)
3. Phương án đề xuất: ... (các bước, phạm vi)
4. Ưu/Nhược/Rủi ro: ... (+ rollback)
5. Xin ý kiến: DUYỆT/TỪ CHỐI/SỬA/CHI TIẾT TASK-xxxxxxxx
Trạng thái: ĐANG CHỜ ANH QUANPT1 PHÊ DUYỆT. CHƯA THỰC HIỆN.
```

Lệnh nhận: `DUYỆT TASK-<mã>` / `TỪ CHỐI TASK-<mã> [lý do]` / `SỬA TASK-<mã>: [nội dung]` / `CHI TIẾT TASK-<mã>` (4 cú pháp Mục VI). Lệnh cũ "phê duyệt" (FIFO) vẫn giữ cho ticket không gắn task.

### 2.5. Test bắt buộc Sprint 2 ( ánh xạ Mục XII)

Mới viết: T5 (phê duyệt không hợp lệ: sai user_id, sai mã, hết hạn), T8 (OUTCOME_UNKNOWN), T11 (restart khi chờ duyệt — không tự thực thi), T12 (kế hoạch nhiều bước — chỉ bước đã duyệt), T14 (thu hồi quyền chặn hành động mới + audit), T15 (R5 chặn không ngoại lệ), T10 (báo cáo 5 mục), T3 (sửa phương án → xin duyệt lại). Tái dùng: T15 đã có (policy), T4 (WAITING không timeout). T1/T2/T9/T13 chờ Sprint 3–4 khi có connector email/web.

---

## 3. DANH SÁCH GAP SAU AUDIT (bổ sung vào GAP Register)

| ID | Khoảng trống | Sprint V3 |
|---|---|---|
| GAP-V3-1 | NetChatApprovalAdapter + Approval Card + lệnh DUYỆT/TỪ CHỐI theo mã task | Sprint 2 |
| GAP-V3-2 | Approval request chưa có TTL mặc định (expiry) | Sprint 2 |
| GAP-V3-3 | Identity binding user_id chủ sở hữu → approver 'quanpt1' | Sprint 2 |
| GAP-V3-4 | TaskUnderstandingEngine + InitiativeEngine | Sprint 3 |
| GAP-V3-5 | EmailWorkAdapter + InternalWebWorkAdapter (read/draft-only) | Sprint 4 |
| GAP-V3-6 | ExperienceMemoryEngine (bảng experiences + provenance) | Sprint 5 |
| GAP-V3-7 | OutcomeVerificationEngine + TaskAccountabilityReporter chuẩn V3 | Sprint 6 |
| GAP-V3-8 | Integration E2E + drill restart/kill-switch | Sprint 7 |

(GAP-X1/X3/X5 cũ tương ứng GAP-V3-1/… được đánh dấuCLOSED-DUP khi Sprint 2 xong.)

## 4. RỦI RO & ROLLBACK

- Chỉ thêm module mới trong `tools/` + bảng additive; không sửa PolicyEngine/R5.
- Rollback: git revert từng commit sprint; bảng mới không xóa dữ liệu cũ.
- Không động: Skill/, bot-netchat skill, BATTERY AI V4, DC-COMMAND, os_kernel.

## 5. ĐỀ XUẤT TRÌNH CHỦ SỞ HỮU (sau Sprint 1)

Duyệt Sprint 2 — ApprovalOrchestrator + NetChatApprovalAdapter theo thiết kế mục 2 (không tự thực hiện cho tới khi có phê duyệt). Kèm 2 quyết định tồn: dedup 40k candidates; Sprint E connector BATTERY AI V4.
