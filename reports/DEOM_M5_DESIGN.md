# DEOM M5 — KẾ HOẠCH THIẾT KẾ: GOAL DECOMPOSITION (phân rã mục tiêu)

**Ngày:** 02/11/2026 · **Cơ sở:** DEOM §6 (Task Decomposition) + GAP #10 (M0) + `ExecutiveCoordinator` (LLM) + `nl_intake` (M2) · **Trạng thái:** THIẾT KẾ — đã nêu trước khi code

---

## 1. Vấn đề

Goal tiếng Việt của owner ("kiểm tra log server rồi tạo báo cáo, gửi cho anh") cần biến thành
TaskPlan nhiều bước **có risk đúng, có phụ thuộc, có policy gate** — trước khi vào supervisor/dispatcher (M3).

`ExecutiveCoordinator.plan()` đã làm điều này **qua LLM** — mạnh nhưng không deterministic, phụ thuộc
model/mạng. M5 bổ sung **đường nền deterministic** luôn khả dụng, không LLM, dễ kiểm thử.

## 2. GoalDecomposer (`planning/goal_decomposer.py` — MỚI)

### 2.1. Nguyên tắc
- **KHÔNG LLM ở đường chính**: luật + pattern tiếng Việt (động từ → step template).
- **KHÔNG THỰC THI gì** — chỉ lập kế hoạch (policy-only, đúng ranh giới PolicyEngine).
- **KHÔNG BAO GIỜ hạ risk**: template risk là sàn; `_evaluate_inherent_risk` (coordinator) là lưới nâng.
- Phần không nhận diện được → **R0 an toàn + warning** (fail-honest, không đoán bừa).

### 2.2. Cơ chế
1. **Split**: từ nối (`rồi / sau đó / tiếp theo / cuối cùng / then`), `;`, xuống dòng, đánh số `1.` `2)`.
2. **Match động từ → template** (6 nhóm): đọc R0 → phân tích R1 → ghi R2 → gửi R3 → cài/đổi hệ thống R4 → xóa R5.
3. **Bổ ngữ**: text sau động từ → mô tả step (giới hạn 120 ký tự).
4. **Phụ thuộc chuỗi**: bước N phụ thuộc `step-(N-1)` (chuỗi tuyến tính đúng thứ tự owner nói).
5. **Policy gate từng bước** — như coordinator: R5 BLOCKED, R4 PENDING_APPROVAL, R2 có target path mới ALLOW.
6. Output `TaskPlan` chuẩn (planning.models) — `validate()` pass, wire được thẳng vào M2/M3.

## 3. Tích hợp

- `nl_intake` (M2) vẫn là cửa nhận goal — decomposer gọi được từ intake hoặc thủ công.
- Plan sinh ra → `PlanOrchestrator` (M2) → supervisor SELECTING_TASK (M3) không đổi.
- `ExecutiveCoordinator` (LLM) giữ vai trò đường nâng cao: goal phức tạp mô tả tự nhiên
  sâu hơn 6 nhóm động từ sẽ do LLM; decomposer là fallback deterministic + đường test.

## 4. Nghiệm thu (tests `test_deom_m5_goal_decomposer.py` — 15 test)

1. 1 goal 1 hành động → 1 step risk đúng nhóm.
2. Chuỗi "A rồi B" → 2 step, step 2 dep step 1; đánh số 3 dòng → 3 step đúng risk [0,1,3].
3. R5 delete → BLOCKED (policy); R4 install → PENDING_APPROVAL + plan.requires_approval=True.
4. Động từ lạ → R0 + warning fail-honest; goal rỗng → ValueError.
5. redact_text chạy trên goal (Bearer → [REDACTED]); source="vn_goal" (không phải LLM).
6. TaskPlan validate() pass; không có validation_errors.

## 5. Biên an toàn

- Không đụng coordinator/LLM hiện có; decomposer là module MỚI độc lập.
- Hoàn tác = xoá module + revert commit; không schema DB mới (plan sinh là in-memory).
