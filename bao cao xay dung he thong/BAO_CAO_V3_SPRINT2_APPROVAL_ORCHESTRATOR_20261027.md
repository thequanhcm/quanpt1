# SPRINT 2 (MASTER PROMPT V3) — APPROVAL ORCHESTRATOR + NETCHAT APPROVAL ADAPTER

**Mã hồ sơ:** TASK-V3-SPRINT2
**Thời điểm:** 27/10/2026 (~00:00–00:30 UTC)
**Phê duyệt của chủ sở hữu:** anh Quân trả lời **"Duyệt"** trên kênh 2 lần (23:45, 23:46 — kèm quote card) và "duyệt" tại desktop → hồ sơ TASK-V3-SPRINT2 đã lưu trạng thái APPROVED trong governance.db (bảng `approval_cards` + `approvals`, approver=quanpt1).

---

## 1. VẤN ĐỀ ĐÃ PHÁT HIỆN (báo cáo trung thực theo yêu cầu chủ sở hữu)

Tin Approval Card đầu tiên (23:45) chỉ là **văn bản** — KHÔNG có hồ sơ nào được ghi vào approval_requests/approval_cards. Khi anh trả lời "Duyệt", command center tra `consultation_tickets` (rỗng PENDING) → trả lời sai: *"Hiện không có hồ sơ nào chờ phê duyệt. Mọi quyết định đã được xử lý."* — thông điệp này vừa sai sự thật vừa gây hiểu nhầm nghiêm trọng (2 lần).

## 2. ĐÃ XÂY DỰNG

### 2.1. `src/quan_ai_brain/governance/approval_cards.py` — ApprovalCardStore
- **Bảng additive** `approval_cards` trong `data/governance.db` (không đụng schema cũ).
- **Tạo card TRƯỚC khi post tin** → mọi card trên kênh luôn khớp hồ sơ thật.
- Gắn **formal request** qua ApprovalGate (request_id = task_code) → duyệt = `grant_approval(approver='quanpt1')` lưu bảng `approvals` chuẩn, consume-once, có `consume_if_execution_started()` để đánh dấu đã dùng khi bắt đầu thực hiện.
- State machine V3 mục 5.3 đầy đủ: PENDING_APPROVAL → APPROVED / REJECTED / EXPIRED (TTL 7 ngày, refresh_expiry) / CANCELLED; **amend → về PENDING với version+1** (bắt duyệt lại).
- **R5 không thể lập card** (chặn tại create — phòng thủ 2 lớp với PolicyEngine).
- Chỉ `quanpt1` trong trusted_approvers.

### 2.2. `src/quan_ai_brain/governance/netchat_approval_adapter.py` — NetChatApprovalAdapter
- Parse lệnh: `DUYỆT / TỪ CHỐI / SỬA / CHI TIẾT TASK-<mã>` + **lệnh trần "Duyệt"** (ánh xạ an toàn: đúng 1 hồ sơ PENDING → duyệt hồ sơ đó kèm giải thích vì sao ánh xạ an toàn; >1 → yêu cầu mã, liệt kê; =0 → trung thực liệt kê hồ sơ gần nhất + giải thích consume-once).
- **Xác minh danh tính**: chỉ user_id `3b1ughs36i8e9p46im8opnms8w` (quanpt1) được ra quyết định; sai → từ chối kèm lý do danh tính (V3 mục 5.2).
- **MỌI phản hồi giải thích cụ thể** (yêu cầu của anh): duyệt gì / ai duyệt / vì sao ánh xạ / cơ chế lưu / trạng thái / **hành động tiếp theo**. Cụ thể:
  - Duyệt lần 2 → "đã được anh duyệt lúc <thời điểm> — consume-once, gõ lại không thực thi lần hai."
  - Sai mã → "KHÔNG TÌM THẤY... Vì sao... Các hồ sơ đang có... Hành động tiếp theo..."
  - Sai người → "KHÔNG THỰC THI — Xác minh danh tính thất bại..."
  - Không còn câu "Mọi quyết định đã được xử lý" gây hiểu nhầm.
- Test T14: revoke approval → evaluate_approval chặn (thu hồi có hiệu lực).

### 2.3. Tích hợp
- `tools/netchat_command_center.py`: `route_message()` kiểm tra approval commands **trước tiên**, truyền `sender_user_id`; thất bại adapter không phá lệnh khác.
- `tools/netchat_auto_responder.py`: truyền `user_id` của người gửi vào router.

## 3. KIỂM CHỨNG

- **25/25 test mới** (`tests/test_sprint2_approval_orchestrator.py`):生命周期 đầy đủ, duyệt trùng bị chặn, reject→không duyệt được, amend→về PENDING v2, TTL hết hạn, sai người bị chặn, **Duyệt trần ánh xạ đúng + giải thích**, nhiều hồ sơ PENDING → yêu cầu mã, lặp lệnh được giải thích consume-once, non-command không đụng, R5 chặn 2 lớp, revoke chặn thực thi.
- **49/49** với test command center cũ (không hồi quy).
- E2E DB thật: TASK-V3-SPRINT2 → APPROVED, evidence [(CREATED), (APPROVED, quanpt1)], bảng approvals có dòng chuẩn.
- Full regression: chạy cuối phiên — kết quả ghi tại reports/DIGITAL_EMPLOYEE_BRAIN_TEST_REPORT.md.

## 4. GIỚ HẠN TRUNG THỰC
- Danh tính cấp-1 = tài khoản NetChat trên kênh riêng (không sinh-trắc-học). R4 đề nghị thêm chữ ký OwnerSignatureVerifier (VERIFIED module, chưa nối).
- `SỬA TASK-xxxx` hiện ghi nhận yêu cầu + nhắc trình lại; bước tự động amend nội dung card do AI soạn sẽ hoàn thiện ở Sprint 3 (cần LLM soạn phương án mới → lại phải duyệt).
- Card cũ của em (TASK-V3-SPRINT2) được lập SAU phê duyệt của anh để hoàn tất hồ sơ — đã ghi rõ trong notes; quy trình chuẩn từ giờ: card TRƯỚC → post SAU.

## 5. BƯỚC KẾ TIẾP (Sprint 3 — xin duyệt riêng khi trình)
TaskUnderstandingEngine + InitiativeEngine (mở rộng CognitiveLoop UNDERSTANDING + lớp quét công việc tồn); mọi đề xuất chủ động gom ≤5 mục, có mã task mới, KHÔNG tự thực hiện khi chưa duyệt.
