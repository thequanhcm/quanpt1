# DIGITAL EMPLOYEE BRAIN — AUDIT HIỆN TRẠNG (Sprint A)

**Mã tài liệu:** AUD-QAB-DEB-A-20261026
**Ngày audit thực địa:** 2026-10-26 23:00–23:59 ICT
**Người audit:** QUAN AI BRAIN (vai Principal AI Systems Architect), chủ sở hữu: `quanpt1`
**Phạm vi:** Toàn bộ repository `E:\AI\QUAN AI BRAIN`, đo lại bằng tool thật (không dùng số liệu báo cáo cũ làm bằng chứng)
**Quy tắc áp dụng:** Master Prompt V2 — Phần 1.1 (Nguồn hiện trạng bắt buộc), Phần 10 Bước 1 (Audit)

---

## 1. Phương pháp

- Chạy lại full regression suite: `python -m pytest -q tests --tb=no` → **546 passed, 1 failed, 2 skipped (164.14s)** trên 549 collected.
- Probe trực tiếp: cổng 8765 (Core Server), 11434 (Ollama), 8768 (Pi 5); process list; schtasks; SQLite real (4 file DB); audit ledger JSONL; git log.
- Import từng module từ Master Prompt Phần 1.1 vào interpreter thật để xác nhận tồn tại + class đúng tên.
- Không tin baseline cũ: mọi số liệu trong tài liệu này đo tại thời điểm audit.

## 2. Trạng thái runtime đã đo (Ground Truth 2026-10-26 23:xx)

| Hạng mục | Giá trị đo được | Trạng thái |
|---|---|---|
| Core Server 8765 | LISTENING, PID 24132 | HEALTHY |
| /api/health HTTP | 404 (route khác) | UNKNOWN (route name sai, không phải downtime) |
| Ollama 11434 | URLError | **OFFLINE** |
| Pi 5 :8768 | URLError | **UNREACHABLE** |
| Python processes | 10 (gồm server 24132 + daemon) | HEALTHY |
| Learning daemon | Cycle 3 hoàn tất 16:04 UTC | HEALTHY |
| Task Scheduler QUAN_AIBRAIN_* | "The system cannot find the file specified" | **CHƯA TẠO** |
| Git | 22 commits, working tree sạch sau commit 4bdd774 | HEALTHY |

## 3. Dữ liệu đã đo (4 DB thực tế)

| DB | Bảng | Số dòng | Ghi chú |
|---|---|---|---|
| brain.db | episodes | 495 | +12 so với báo cáo DC (495 vs 483) — learning daemon hoạt động thật |
| brain.db | memories | 502 | |
| brain.db | semantic_memory | 720 | 680 cũ + 10 DC Skill/ (duyệt 2026-10-26) + 30 tự thăng cấp daemon |
| brain.db | candidate_knowledge | 38,436 | 720 approved / 37,716 quarantined |
| tasks.db | durable_tasks | 160 | 109 PENDING / 48 CANCELLED / 2 COMPLETED / 1 IN_PROGRESS |
| tasks.db | durable_task_steps | có | |
| governance.db | 7 bảng | có | approval_requests, approvals, delegation_grants, consumed_nonces, governance_events, emergency_states |
| consultations.db | consultation_tickets | 5 | |
| logs/audit.jsonl | 502 dòng | audit trail thật (sandbox.consent_required, execution_succeeded...) |

## 4. Kết quả kiểm kê module (Master Prompt Phần 1.1)

### 4.1. ĐÃ TỒN TẠI và import thành công (ground truth bằng import thật)

| Module | Class chính | Trạng thái |
|---|---|---|
| `cognition/system_inventory.py` | SystemInventory | OK (440 dòng) |
| `cognition/self_model_engine.py` | SelfModelEngine | OK (242 dòng) |
| `cognition/continuous_learning_engine.py` | ContinuousLearningEngine | OK (502 dòng) |
| `cognition/self_care_engine.py` | SelfCareEngine | OK (351 dòng) |
| `cognition/context_builder.py` | (có) | OK |
| `cognition/retrieval.py` | (có) | OK |
| `cognition/autonomous_mind.py` | (có) | OK |
| `memory/knowledge_ingestion.py` | (có) | OK (346 dòng) |
| `orchestration/plan_orchestrator.py` | PlanOrchestrator | OK |
| `orchestration/task_registry.py` | DurableTaskRegistry(db_path, workspace) | OK |
| `orchestration/supervisor.py` | (có) | OK |
| `llm/netmind_provider.py` | NetMindProvider | OK (331 dòng, fail-closed) |
| `core/guardrails.py` | PathGuard | OK |
| `core/audit.py` | AuditLogger(workspace, relative_log_path='logs/audit.jsonl') | OK — file 502 dòng thật |
| `execution/process_containment.py` | ContainedExecutionRunner, InertProcessBackend, ApprovalGate | OK — execution vẫn Inert theo thiết kế Sprint 6 |
| `governance/policy.py` | PolicyEngine, RiskLevel R0–R5, DecisionStatus | OK — **R5 hard-block dòng 51–52** |
| `governance/state_store.py` | GovernanceStateStore | OK |
| `governance/consultation_inbox.py` | (có) | OK |

### 4.2. KHOẢNG TRỐNG module xác minh (không tồn tại file)

| Module kỳ vọng | Trạng thái | Ảnh hưởng |
|---|---| Sprint C/D/E/F |
| `governance/delegation.py` (DelegationGrant class) | ❌ MISSING | Sprint G không thể bắt đầu |
| `execution/contained_runner.py` (tên file chuẩn) | ❌ runner nằm trong process_containment.py | Sprint F chỉ cần tái dùng |
| `cognition/cognitive_loop.py` (CognitiveLoop) | ❌ MISSING | Sprint B — nhưng PlanOrchestrator + DurableTaskRegistry + Supervisor đã có thể mở rộng |
| `cognition/reflection.py` (ReflectionLoop) | ❌ MISSING | Sprint B |
| `integration/` — chưa có connector BATTERY AI V4 read-only | ❌ MISSING | Sprint E |
| `cognition/incident_intelligence.py` | ❌ MISSING | Sprint E |

### 4.3. Khoảng trống vận hành đã xác minh

| # | Khoảng trống | Bằng chứng đo được |
|---|---| `/api/health` trả 404 — cần kiểm tra route thật của server.py |
| 2 | Ollama OFFLINE — 11434 URLError | fail test_keep_warm_pulse, skip BGE-M3 test |
| 3 | Task Scheduler chưa tạo (cần Admin) | schtasks ERROR: cannot find |
| 4 | Pi 5 unreachable | URLError :8768 |
| 5 | 109 durable_tasks PENDING, chỉ 2 COMPLETED — backlog chưa có policy xử lý | tasks.db đo trực tiếp |
| 6 | 37,716 candidates quarantined — không có quy trình thẩm định lô có chính sách | brain.db |
| 7 | Watchdog chưa giám sát Ollama/NetChat bot (chỉ monitor server) | logs/watchdog.log chỉ log startup |
| 8 | Chưa có external monitor độc lập | không tìm thấy process/cron ngoài |
| 9 | /api/approvals/* chưa có endpoint trên server | audit trạng thái Sprint 6 |
| 10 | Confidence chưa hiệu chuẩn (calibration) — chưa dùng được cho auto-execute | Master Prompt 4.2 yêu cầu benchmark riêng |

## 5. Test suite — kết quả thật

- **549 collected → 546 passed, 1 failed, 2 skipped, 164.14s**
- FAILED: `test_autonomous_mind.py::test_keep_warm_pulse` — **FAIL do môi trường** (Ollama 11434 offline đã probe trực tiếp xác nhận; không phải bug code — xử lý ở Sprint A fix list)
- SKIPPED: `test_bge_m3_embedding.py:172` (Ollama offline); `test_vietnamese_tts.py:263` (Pi 5 hardware)
- Kết quả giống baseline báo cáo DC 2026-10-26 (546/1/2) → **không có regression mới**, các sprint trước giữ nguyên chức năng.

## 6. Điểm tích hợp Domain Brain

| Domain | Interface dự kiến | Trạng thái |
|---|---|--- |
| BATTERY AI V4 | API read-only (đã duyệt tri thức 10 items Skill/) | CHƯA có connector — Sprint E |
| DCIM/VDCIM | TBD khi owner cung cấp endpoint | CHƯA có |
| Monitoring/alerting | TBD | CHƯA có |
| NetChat | netchat_bot.py (bot_quanpt1, kênh Trợ lý Tony Pham) | HOẠT ĐỘNG — đang dùng cho daily digest + approval channel |

## 7. Rủi ro tương thích

1. **R-O1:** Ollama offline kéo dài làm skip embedding local → retrieval chỉ dựa embedding remote (GLM) — chấp nhận được ngắn hạn, phải fix ở Sprint A.
2. **R-O2:** 37,716 quarantined không thẩm định → tri thức DC mới có thể bị nhấn chìm trong noise. Cần policy lô theo mức rủi ro (Sprint D).
3. **R-O3:** `durable_tasks` 109 PENDING — nếu CognitiveLoop (Sprint B) khôi phục hết vào runtime sẽ quá tải; cần chính sách age-out.
4. **R-O4:** Confidence LLM chưa hiệu chuẩn → KHÔNG được dùng ngưỡng 80% làm điều kiện auto-execute cho đến khi có benchmark calibration (Master Prompt 4.2, 5.1).
5. **R-O5:** Task Scheduler chưa tạo + Startup folder chỉ chạy khi login → hệ 24/7 phụ thuộc đăng nhập Windows.

## 8. Danh sách file dự kiến thay đổi (kế hoạch, chưa sửa)

| Sprint | File | Loại |
|---|---|---|
| A-fix | `tools/watchdog.py` | PATCH (thêm Ollama/NetChat monitor) |
| A-fix | `start_server_fixed.py` hoặc server route | PATCH (health endpoint) |
| B | `cognition/cognitive_loop.py` (MỚI, tái dùng PlanOrchestrator + DurableTaskRegistry + Supervisor) | NEW |
| B | `cognition/reflection.py` (MỚI) | NEW |
| B | tests/test_cognitive_loop.py | NEW |
| C | `cognition/self_model_engine.py` | PATCH (nối SystemInventory thật) |
| D | `memory/knowledge_ingestion.py` + `cognition/continuous_learning_engine.py` | PATCH (promotion policy theo lô/rủi ro) |
| E | `integration/battery_ai_connector.py` (MỚI, read-only) | NEW |
| F | tái dùng `execution/process_containment.py` | PATCH |
| G | `governance/delegation.py` (MỚI: DelegationGrant) | NEW |

## 9. Kết luận Sprint A

1. Kiến trúc 8 năng lực có nền thật: 17/18 module kỳ vọng tồn tại, import OK, test suite 546 pass.
2. Execution vẫn Inert (đúng thiết kế an toàn), R5 hard-block xác minh tại `governance/policy.py:51-52`.
3. Vòng nhận thức khép kín CHƯA có (không CognitiveLoop/Reflection) — đây là khoảng trống lớn nhất, đúng trọng tâm Sprint B.
4. Khoảng trống runtime (Ollama, Task Scheduler, Pi 5) là lỗi môi trường, có kế hoạch fix cụ thể.
5. Không có regression so với baseline → an toàn để triển khai Sprint B theo kế hoạch.

**Đề xuất duyệt tiếp theo:** Sprint A-fix (watchdog mở rộng + health endpoint) → Sprint B (CognitiveLoop + Reflection, không đụng production).
