# DEOM M0 — GAP ANALYSIS (01/11/2026, ~19:58)

> Phân tích khoảng trống giữa hiện trạng (DEOM_M0_ACTUAL_STATE.md) và mục tiêu Master Prompt V3.0.
> Nguyên tắc §2.1: ONE BRAIN — KHÔNG tạo bộ não mới; mọi gap giải quyết bằng MỞ RỘNG thành phần hiện có.

---

## GAP MATRIX — 16 thành phần logic (DEOM §16)

| # | Thành phần | Hiện trạng | Gap | Mức | Milestone |
|---|---|---|---|---|---|
| 1 | Digital Employee Identity | persona + self_model + capability_registry | Hồ sơ nhân sự số có cấu trúc (DEOM §3.3) cập nhật từ dữ liệu thật (active tasks, performance, reliability) | Vừa | M1 |
| 2 | Task Intake | Command center intent engine (DM) + server APIs | Natural-language intake cho câu giao việc dài ("em theo dõi việc này đến khi hoàn thành") → cấu trúc task; intake qua Pi5 voice đã có voice pipeline | Vừa | M2 |
| 3 | Task Registry | DurableTaskRegistry 578 tasks, idempotency, checkpoint, recovery 62 tests | **Thiếu fields**: priority, deadline, parent_task_id, dependencies, required_tools, required_skills, assigned_agents, permission_scope. Thiếu transition log (actor/time/reason/evidence) | **Lớn** | M2 |
| 4 | Task Planner | TaskPlanner (502 dòng) + PlanOrchestrator | Task Decomposition tự động (DEOM §6.2) — planner hiện cần plan được submit; chưa tự phân rã từ goal tự nhiên | Vừa | M2/M3 |
| 5 | Task Scheduler | cron morning report + watchdog loop | Recurring task engine trong registry (định kỳ, deadline-driven) | Vừa | M6 |
| 6 | Work Queue | gateway/message_queue (edge) — không phải task queue | Queue 4 bậc (Critical/High/Normal/Low/Background) + 6 quy tắc ưu tiên DEOM §7.2 + chống learning chiếm tài nguyên | Vừa | M3 |
| 7 | Agent Dispatcher | IntegrationRegistry + BDIAgent (459 dòng) | Dispatcher chọn agent theo năng lực kiểm chứng + workload + quyền; chống lệnh trái ngược; correlation ID | Vừa | M3 |
| 8 | Permission Resolver | policy.py R0–R5 (đã đọc toàn bộ) + security/rbac.py (chưa nối) | Bảng Permission Matrix tập trung 13 quyền × actor/resource/scope/env/risk/expiration; resolver hợp nhất risk_level + RBAC + policy | **Lớn** | M4 |
| 9 | Approval Workflow | approval_cards + approval_verifier fail-closed (20 APPROVED) | Hiển thị đủ 12 trường DEOM §5.3 (rollback plan, alternatives...); approval separation backend-enforced; chống "phê duyệt lại bằng chính agent yêu cầu" | Nhỏ–Vừa | M4 |
| 10 | Progress Tracker | update_task_status + steps trong registry | Weighted progress (không đếm bước); blocker tracking | Nhỏ | M2 |
| 11 | Task Verifier | _verify_step_result (PlanOrchestrator) | Task-level verifier → COMPLETED_VERIFIED / COMPLETED_PARTIALLY / COMPLETED_UNVERIFIED với bằng chứng | Vừa | M2 |
| 12 | Reporting Engine | morning_report (8h cron) + periodic_reporter (CLO) | TONY Daily/Weekly/Monthly Executive Report đúng format DEOM §9; liên kết Task ID + evidence | Vừa | M5 |
| 13 | Performance Evaluator | learning/performance_monitor (CLO) | Digital Employee Scorecard 10 nhóm (DEOM §10.1) + 3 cấp năng lực có bằng chứng | Vừa | M5 |
| 14 | Learning Feedback | CLO + experience_consolidation + unified_memory promotion | Bản ghi kinh nghiệm sau mỗi task (Task ID → Lessons → Reusable Procedure) đúng DEOM §11 | Vừa | M6 |
| 15 | Executive Dashboard | executive.html 97KB + 61 APIs (Approvals, Edge, Tasks badge) | Tab "TONY Digital Employee" trong dashboard hiện có: Executive Overview, Workforce, Scorecard, Activity Timeline. KHÔNG tạo dashboard rời | Vừa | M5 |
| 16 | Notification Manager | alert_engine (health) + NetChat DM | Chính sách notify theo priority/kênh; không tự gửi ra ngoài (R3+) | Nhỏ | M6 |

## GAP NGHIỆP VỤ — 7 CASE (DEOM §13)

| Case | Khả năng hiện tại | Còn thiếu |
|---|---|---|
| CASE 1 Kiểm tra tiến độ email | email_intake + email_intelligence + tasks APIs | Tự phân rã 12 bước + đối chiếu + soạn báo cáo một lệnh |
| CASE 2 Công việc quá hạn | tasks.db có dữ liệu; health alerts | Deadline hiện chưa lưu trong registry → không phát hiện quá hạn được. **Phụ thuộc M2 schema** |
| CASE 3 Hệ thống bất thường | pi5_collector + rca_engine + alert_engine (CLO alert sent=1 là bằng chứng sống) | Quy trình khuyến nghị không tự đổi cấu hình (đã đúng charter) — chỉ cần nối vào task |
| CASE 4 Thiếu tool | sandbox + candidate knowledge + Q-4 promotion | Quy trình thiết kế tool mới → candidate → sandbox → trình duyệt (có sẵn nền) |
| CASE 5 Nhiệm vụ dài hạn | CLO sessions + checkpoint + recovery | Project/task group + milestones trong registry |
| CASE 6 Owner vắng mặt | watchdog tự hồi + proactive findings | Giới hạn rõ việc nào tự làm / việc nào chờ (Group A/B/C/D) |
| CASE 7 Xung đột quyền agent | BDIAgent + decision_engine | Quy trình thu thập bằng chứng + nêu quan điểm + tách phần cần owner quyết |

## GAP KIỂM THỨ (DEOM §18)

- Functional: registry tests tốt (62) — thiếu tests cho intake NL, decomposition, weighted progress, recovery E2E qua API.
- Governance: đã có test_approval_gate + Q-4 — **thiếu**: self-approval blocked, agent escalation blocked, unauthorized send/deploy blocked trong ngữ cảnh task mới.
- Reliability: đã có recover_in_flight_tasks tests — thiếu test restart service giữa task, duplicate event, concurrent task cùng ghi.
- Performance: resource_budget.py có — thiếu benchmark concurrent tasks + queue latency.
- Acceptance: chưa có bộ 7 CASE E2E.

## RỦI RO TRIỂN KHAI

1. **M2 migration tasks.db** — phải ADD COLUMN + backup + kiểm 578 records nguyên vẹn (R4 — xin duyệt).
2. **Không phá nền tảng 3.034 tests** — mọi module mới phải có tests + chạy regression FULL.
3. **Không vi phạm charter** — mọi thay đổi quyền/policy/promotion dừng lại xin duyệt; Q-1..Q-5 giữ nguyên.
4. **Dashboard** — chỉ thêm tab vào executive.html hiện có, không tạo dashboard rời.

## THỨ TỰ TRIỂN KHAI ĐỀ XUẤT (M1→M7)

```
M1 (design docs, 0 code) → M2 (schema mở rộng + intake + verifier + transition log)
→ M3 (queue + dispatcher) → M4 (permission resolver + approval hoàn chỉnh)
→ M5 (reports + tab dashboard) → M6 (proactive work + recurring + learning feedback)
→ M7 (7 CASE + acceptance)
```

Mỗi milestone: code + tests + E2E + regression 3.034+ + HANDOFF + xin duyệt phần thuộc R4.

---
*Generated by TONY — DEOM M0 GAP ANALYSIS.*
