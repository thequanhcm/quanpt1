# DEOM M0 — AS-BUILT PRECHECK (01/11/2026, ~19:55)

> Master Prompt V3.0 — TONY DIGITAL EMPLOYEE OPERATING MODEL (DEOM)
> Kiểm toán hiện trạng THẬT trên workspace `D:\AI\AI Quanpt1 2026\BRAIN` — mọi số liệu lấy từ kiểm tra trực tiếp (DB schema, file, tests), không suy đoán.

---

## 1. Kết quả tổng kiểm toán gần nhất (đầu vào)

- **Audit V2**: 22/22 báo cáo ✅ (16:45 hôm nay) — scorecard Governance C3.
- **Regression FULL mới nhất**: **3.034 PASS / 44 skipped / 0 FAIL** (19:44, HANDOFF_LATEST.md).
- **Dịch vụ đang sống**: servers 8765+8766 (pair 18292+18936), watchdog 20424→5172, responder 16804+18524, learning daemon 12144/20184.
- **CLO session #8** RUNNING (từ 01/11 12:00 UTC) sau khi mở kẹt #7.
- Quyet định Q-1..Q-5: **giữ nguyên trạng thái chờ** (đúng yêu cầu DEOM §5.4).

## 2. Cognitive Core hiện có (kiểm tra thật)

| Thành phần DEOM cần | Hiện trạng | Đánh giá |
|---|---|---|
| Cognitive Core | `src/quan_ai_brain/` 30+ package, cognition/ 41 module | ✅ Có, một nguồn duy nhất |
| Unified Memory | `memory/` 39 module + `unified_memory.py` MemoryFacade 5 lớp (M3 ✅) + brain.db 95MB (2.748 episodes) | ✅ Tái sử dụng |
| Reasoning Engine | `llm/` GLM-5.3-Flash live + planning/causal/decision | ✅ Tái sử dụng |
| Self Model | `cognition/self_model_engine.py`, `self_qa.py`, `system_inventory.py` (M4 ✅) | ✅ Tái sử dụng |
| Learning Engine | `continuous_learning_engine.py` + CLO #8 + Q-4 verifier (3.209 promoted) | ✅ Tái sử dụng |
| Tool Registry | `tools/registry.py` + `integration/registry.py` (IntegrationRegistry, 218 dòng) | ✅ Tái sử dụng |
| Skill Registry | Skill/ folder + capability_registry | ⚠️ Có nhưng chưa gắn vào task flow |
| Agent Registry | `ai/multi_agent.py` (BDIAgent) + `orchestration/` | ⚠️ Có nguyên liệu, chưa có Dispatcher hoàn chỉnh |
| Governance Gateway | `governance/policy.py` R0–R5 gate **đã đọc xác nhận** (R5 hard-block, R4 approval_required, R2 path-guard) + `approval_verifier.py` fail-closed + `approval_cards.py` | ✅ Mạnh, tái sử dụng |
| Audit Trail | `core/audit.py` + audit.db 456KB | ✅ Tái sử dụng |
| System Health | `monitoring/` 11 module (health_monitor, pi5_collector, rca_engine...) + health_alerts.db | ✅ Tái sử dụng |

## 3. Task Management hiện có (DEOM trọng tâm)

- **`orchestration/task_registry.py`** (438 dòng): `DurableTaskRegistry` — durable_tasks trong tasks.db (11,6MB, 578 records), idempotency, checkpoint, recovery (`recover_in_flight_tasks`), steps. **62/62 test backbone PASS.**
- **Schema thật**: task_id, correlation_id, idempotency_key, goal, risk_level, autonomy_level, status, acceptance_criteria_json, approved_scope_json, resource_budget_json, retry/max_retries, evidence_refs_json, result_payload_json, checkpoint_data_json.
- **`orchestration/plan_orchestrator.py`**: PlanOrchestrator — submit_plan, execute_lifecycle, recover_tasks, _verify_step_result.
- **`orchestration/supervisor.py`** (352 dòng): ContinuousAutonomySupervisor — states STARTING→READY→SELECTING_TASK→PLANNING→WAITING_FOR_APPROVAL→RUNNING_AUTHORIZED_TASK...
- **`planning/task_planner.py`** (502 dòng): TaskStatus, Priority, Task, Resource, Plan, TaskPlanner.
- **API server đã có**: `/api/executive/tasks` (+create/detail/cancel/execute/duplicates/cognitive-state), `/api/workbench/tasks`.
- **TaskStatus hiện tại**: PENDING, IN_PROGRESS, WAITING_APPROVAL, APPROVED, COMPLETED, FAILED, CANCELLED, OUTCOME_UNKNOWN, BLOCKED.

### GAP của Task Registry so với DEOM §4.3
| DEOM field | Hiện trạng |
|---|---|
| priority, deadline, parent_task_id, dependencies, required_tools, assigned_agents, permission_scope | **THIẾU** trong durable_tasks schema (priority có ở task_planner.Task nhưng chưa nối vào registry) |
| Trạng thái lifecycle | Có bộ gần đúng; **thiếu** RECEIVED/UNDERSTANDING/ANALYZING/PLANNING/READY/VERIFYING/NEEDS_INFORMATION/PAUSED/EXPIRED/REJECTED; COMPLETED chưa tách COMPLETED_VERIFIED/PARTIALLY/UNVERIFIED |
| State transition control | Có update_task_status nhưng **chưa có transition log (actor/timestamp/reason/evidence)** bắt buộc DEOM §4.4 |

## 4. Workforce / Proactive / Reporting

- `integration/proactive.py` (173 dòng): ProactiveOperationsLoop — phát hiện finding (health/latency) + proposed_solution + risk_level. **Là nền của Proactive Work Engine (DEOM §7.1) nhưng mới dừng ở finding, chưa sinh task.**
- Work Queue: `gateway/message_queue.py` (cho edge); **chưa có Work Queue ưu tiên 4 bậc (Critical/High/Normal/Low) cho task**.
- Reporting: `learning/periodic_reporter.py` (CLO reports) + `tools/morning_report.py` (cron 8h) + analytics/report_generator. **Chưa có Daily/Weekly/Monthly Executive Report theo format DEOM §9.**
- Dashboard: `web/static/executive.html` (97KB, 61 APIs) — Phòng Điều Hành đã rất đầy đủ (approvals, edge, camera, chat, tasks badge). **Chưa có tab riêng TONY Digital Employee Command Center / Scorecard / Workforce.**

## 5. Governance — kiểm tra thật

- `governance/policy.py` (67 dòng, ĐÃ ĐỌC TOÀN BỘ): RiskLevel R0–R5; R5→BLOCKED; R4→APPROVAL_REQUIRED; R3→ALLOW_WITH_NOTICE; R2→path-guard workspace-only; R0/R1→ALLOW. ✅ đúng chuẩn DEOM §15.
- `governance/approval_verifier.py`: fail-closed (Q-4, 3.209 promoted qua nó).
- approval_cards: 20 APPROVED / 1 CANCELLED — không PENDING tồn.
- RBAC: `security/rbac.py` (Permission/Role/RBACEngine/ABACEngine) — **chưa nối vào task flow**.
- ⚠️ **GAP DEOM §5.1**: Permission Matrix 13 quyền (READ...APPROVE) chưa tồn tại như một bảng tập trung; hiện phân tán: risk_level (task) + RBAC (security, chưa dùng) + policy.py (action gate).

## 6. Digital Employee Identity

- `cognition/executive_persona.py` + `self_model_engine.py` + `capability_registry` — có persona + năng lực.
- **Chưa có** hồ sơ nhân sự số chính thức theo DEOM §3.3 (Employee ID, Responsibilities, Active Tasks, Performance, Reliability... cập nhật từ dữ liệu thật).

## 7. Đánh giá khả năng tái sử dụng (kết luận M0)

**TÁI SỬ DỤNG (không xây mới):** Cognitive Core, Unified Memory, policy.py R0–R5, approval_verifier + approval_cards, audit, health monitoring, DurableTaskRegistry + PlanOrchestrator + Supervisor, task APIs server, executive dashboard, proactive findings, morning report cron.

**CẦN XÂY MỚI / MỞ RỘNG (theo M1→M7):**
1. M1: 4 tài liệu thiết kế (operating model, permission matrix, task lifecycle, approval design).
2. M2: **mở rộng schema durable_tasks** (priority, deadline, parent_task_id, dependencies, required_tools, assigned_agents, permission_scope) + **thêm transition log + lifecycle states DEOM** + Natural Language Task Intake (dựa trên command center intent engine hiện có) + Task Verifier (COMPLETED_VERIFIED/PARTIALLY/UNVERIFIED).
3. M3: Agent Dispatcher (dựa trên IntegrationRegistry + BDIAgent) + Work Queue 4 bậc ưu tiên + Dependency Manager + capability matching.
4. M4: Permission Resolver (nối RBAC + policy.py + risk_level) + Approval Workflow hoàn chỉnh (approval separation, approval_id/task_id) + Human Override (STOP/PAUSE/RESUME có sẵn ở supervisor — expose qua API/DM).
5. M5: TONY Daily/Weekly/Monthly Executive Report + tab "TONY DEOM" trong executive.html (Scorecard, Workforce, Approval Center — tái dùng 61 APIs).
6. M6: Proactive Work Engine (nâng proactive.py: finding → task proposal có duyệt) + resource budget (execution/resource_budget.py đã có) + notification policy.
7. M7: 7 tình huống nghiệp vụ CASE 1–7 + acceptance test trên dữ liệu thật.

## 8. Rủi ro & hạn chế ghi nhận

1. **Schema migration tasks.db** (M2) ảnh hưởng 578 records — phải ADD COLUMN an toàn + backup trước + không mất dữ liệu. (R4 — cần duyệt trước khi chạy migration thật).
2. durable_tasks đang có 524 CANCELLED — cần chính sách archive khi mở rộng.
3. Dashboard executive.html 97KB đã lớn — thêm tab phải tối giản, không viết dashboard rời.
4. Không tự thay đổi R0–R5, không tự promotion, không tự deploy (DEOM §15 + charter).
5. Pi5 kiosk đang tắt — PI5 integration test (M7 CASE) cần bật kiosk khi test.

## 9. Đối chiếu tiêu chí hoàn thành DEOM (Phần XIX) — trạng thái đầu M0

19 tiêu chí: ĐÃ CÓ (tái sử dụng được) ≈ 7/19 (core, memory, governance, audit, health, task registry nền, STOP/PAUSE). Còn ≈ 12 tiêu chí phải xây/kiểm chứng qua M1–M7. Sẽ cập nhật từng milestone với bằng chứng.

---
*Generated by TONY — DEOM M0 AS-BUILT PRECHECK. Toàn bộ số liệu từ kiểm tra trực tiếp ngày 01/11/2026.*
