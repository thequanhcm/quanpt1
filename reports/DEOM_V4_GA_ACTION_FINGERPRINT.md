# DEOM V4 — G-A: APPROVAL ACTION FINGERPRINT (§6.2)

**Ngày:** 02/11/2026 01:30 · **Cơ sở:** Master Continuation Prompt V4.0 §6.2 "Approval Binding" · **Trạng thái:** IMPLEMENTED + TESTED

## 1. Vấn đề (M0 gap #1)

Card M4 gắn `task_id` + `scope` nhưng **không có binding nội dung hành động**. Nếu sau khi
owner duyệt, TONY/agent đổi `action_summary`, `scope` hay tham số của bước R4, card cũ
vẫn consume được → phê duyệt cũ áp cho nội dung mới — vi phạm §6.2: "Nếu nội dung hành
động thay đổi sau phê duyệt, approval cũ không được tự động tái sử dụng."

## 2. Thiết kế

- `compute_action_fingerprint(action_summary, scope, params)` — SHA-256 canonical JSON
  (normalize whitespace, sort scope/keys; KHÔNG gồm id/thời gian → 2 lần tạo cùng nội dung cho cùng vân tay).
- `ApprovalCard` + bảng `approval_cards_v2` thêm cột nullable `action_fingerprint`
  (ADD COLUMN an toàn — không đụng dữ liệu cũ, cùng kiểu migration M2).
- `create_card()`: không truyền fingerprint → tự tính từ nội dung trình duyệt. Card luôn có binding.
- `consume(action_fingerprint=…)`:
  - khớp → consume như cũ;
  - lệch → `FINGERPRINT_MISMATCH` event + raise — **card còn nguyên** (không bị tiêu nhầm);
  - card NULL (legacy) + consume kèm fp → chặn fail-closed (`NO_BINDING`), phải xin card mới;
  - consume KHÔNG kèm fp → chạy như workflow cũ (backward compat, từng đó đường vẫn còn
    ConsultationStore/ApprovalGate check riêng).
- `PermissionResolver` (lớp 4): đối chiếu fingerprint TRƯỚC consume, trả vết
  `{"layer":"fingerprint","result":"MATCH|MISMATCH|NO_BINDING"}` trong ResolverDecision.
- `PlanOrchestrator.step_action_fingerprint(step, task_id)` — nguồn duy nhất tính vân tay
  bước R4; `_check_step_approval` consume kèm vân tay này.

## 3. Test (12 bài — 3.206 PASS / 0 FAIL toàn bộ regression)

| Nhóm | Case |
|---|---|
| compute | deterministic · đổi summary đổi fp · thứ tự scope/whitespace không đổi fp · đổi params đổi fp |
| lifecycle | create tự binding · consume khớp OK · consume lệch chặn + card nguyên vẹn · backward-compat consume · legacy NULL fail-closed |
| wire | card khớp fp mở khóa bước R4 · card lệch fp → bước giữ WAITING_APPROVAL, card không bị tiêu |
| resolver | fp khớp → ALLOW_WITH_NOTICE · fp lệch → BLOCKED, card chưa consume |

## 4. Rollback

Xoá `data/approval_cards_v2.db` (isolation như M4) + git revert 1 commit — không ảnh hưởng tasks.db/governance.db.
