# TONY EMPLOYEE CHARTER AUDIT — Đối chiếu Master Prompt V1.0 với hệ thống thật (02/11/2026)

**Phương pháp:** đo trực tiếp source + test, không tin tài liệu cũ (AUDIT FIRST).

## 1. Nguyên tắc đã tích hợp (bảng đầy đủ trong docs/TONY_DIGITAL_EMPLOYEE_CHARTER.md §1)

7 nguyên tắc cốt lõi (Do the right work / Take responsibility / Know your limits / Ask when
owner decides / Proactive not reckless / Think independently report honestly / Owner first)
đều có component thật giữ vai trò + test bảo vệ. **Không tạo engine mới** — đúng mệnh lệnh §XI.

## 2. Module được kiểm tra/cập nhật

| Module | Vai trò Charter | Thay đổi lần này |
|---|---|---|
| `governance/policy.py` | Ma trận quyền §IV (R0–R5) | Không đổi — đã đúng |
| `governance/permission_resolver.py` | Single Source of Authority §11.1 | Không đổi (4 lớp từ M4) |
| `governance/approval_service.py` | §11.3 traceability + R4 dual-factor | Không đổi (G-A fingerprint) |
| `orchestration/task_registry.py` + `task_state_machine.py` | §11.2 Single Task Accountability | Không đổi (G-C) |
| `orchestration/agent_dispatcher.py` | §VI trách nhiệm điều phối | Không đổi — test mới T6/T9 phủ |
| `planning/goal_decomposer.py` | N.1/T1/T3 | Không đổi — test mới phủ |
| `orchestration/task_feedback.py` + `learning/learning_metrics.py` | §VII học có trách nhiệm | Không đổi (M6+P5) |
| `tests/advanced/test_charter_responsibility.py` | Phần X — 10 test nhận thức | **MỚI (11 tests)** |
| `docs/TONY_DIGITAL_EMPLOYEE_CHARTER.md` | Bản áp dụng | **MỚI** |

## 3. Quy tắc được bảo vệ bằng code (không phụ thuộc prompt)

1. R5 hard-block — `PolicyEngine.authorize` + orchestrator invariant.
2. R4 không tự quyết — APPROVAL_REQUIRED + ApprovalCard consume-once + fingerprint G-A.
3. Self-approval chặn — `ApprovalCardService` (owner cố định quanpt1).
4. Terminal không re-run — state machine G-C ở `update_task_status`.
5. Step FAILED không re-run ngầm — orchestrator (ADV-004).
6. STOP/FREEZE tức thời — supervisor + lifecycle (P9-MS3, T8).
7. Lesson không tự promote — TaskFeedbackRecorder thiếu đường promote (T10).
8. Agent không tự nâng quyền — dispatcher NEVER_AUTO_ASSIGN + RBAC P13 không-grant (T6).
9. Dispatch theo capability/risk — không default quyền agent = TONY (§VI).

## 4. Test inventory (chạy thật 02/11)

- Suite Charter mới: **11/11 PASS** (`test_charter_responsibility.py`)
- Suite Advanced tổng: 90 + 11 = **101 PASS** (registry/security/chaos/concurrency/state-machine/learning/business/master/charter)
- FULL regression: **3.311 PASS / 0 FAIL / 44 SKIP** (02/11, ~4 phút)

## 5. Lỗ hổng còn tồn tại (trung thực — Charter §IX mục 5)

1. Nhãn epistemic (FACT/INFERENCE/…) có ở `CognitiveState.BeliefKind` nhưng chưa ÉP ở tầng
   render báo cáo DM — hiện là quy ước (Q1 cho owner).
2. Confidence Boundary: `add_uncertainty` có sẵn nhưng chưa có ngưỡng tự động dừng.
3. R3 ALLOW_WITH_NOTICE: notice ghi log/consultation, chưa bắt buộc DM owner trước chạy (Q2).
4. AgentProfile capabilities khai tĩnh — chưa có bài kiểm tra năng lực định kỳ cho agent.

## 6. Thiết kế vs đã kiểm chứng

- Đã kiểm chứng code+test: §III cả 7 nguyên tắc, §IV ma trận, §V quy trình (8 câu kiểm tra
  nằm ở docstring + checkpoint fail-closed), §VI, §VII, §VIII (monitoring), §XI.1–11.4.
- Chỉ thiết kế/quy ước: cấu trúc báo cáo 7 mục §IX (TONY tuân thủ khi viết, không có validator).

## 7. Quyết định cần Quanpt1

- Q1: Ép nhãn epistemic ở mọi báo cáo DM? (cần sửa tầng render)
- Q2: R3 notice bắt buộc gửi owner?
- Q3: `docs/SPRINT6_DESIGN_SIGNOFF.md` vẫn PENDING_OWNER_SIGNOFF — không tự ký.

**Không tự ghi OWNER_ACCEPTED** — chờ anh nghiệm thu.
