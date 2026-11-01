# PR: DEOM M1+M2 — Task Lifecycle hoàn chỉnh cho mô hình nhân sự số

> **Nhánh:** `feat/deom-m1-m2-task-lifecycle` → **Base:** `main`
> **Chuỗi 2 commit conventional-commit** (đã rewrite sạch, cây nội dung giữ nguyên 100%):
> 1. `9386a9d` — **feat(orchestration): add DEOM M2 task lifecycle — schema, transitions, verifier, NL intake**
> 2. `02cfa0d` — **docs(status): record Q-1/Q-2/Q-5 fixes and DEOM M1+M2 in status, register, handoff**

## Nội dung thay đổi

### feat(orchestration) — M2 (R4, owner blanket approval 01/11/2026)
- **Schema `durable_tasks` +11 cột**: priority, deadline_utc, parent_task_id, dependencies, required_tools, assigned_agents, permission_scope, progress_weight, source, verified_at_utc, verification_note — ADD COLUMN idempotent, chạy sau backup `data/backups/tasks_backup_20261101_2300.db` (578 records nguyên vẹn).
- **Governance**: bảng `task_transitions` (actor / time / reason / evidence — DEOM §4.4).
- **Trạng thái**: `TaskStatus` +10 trạng thái DEOM (RECEIVED → UNDERSTANDING → ANALYZING → PLANNING → READY, VERIFYING, NEEDS_INFORMATION, PAUSED, EXPIRED, REJECTED, COMPLETED_VERIFIED / PARTIALLY / UNVERIFIED); 9 trạng thái cũ giữ nguyên (backward-compat).
- **Task Verifier fail-honest**: thiếu bằng chứng → `COMPLETED_UNVERIFIED`; không bao giờ tự phong VERIFIED; wire vào `PlanOrchestrator`.
- **Work Queue 4 bậc**: priority + deadline; task learning nhường việc của owner.
- **NL Intake tiếng Việt** (`orchestration/nl_intake.py`): deterministic, không LLM; deadline theo giờ VN (+07:00).
- **API**: `/api/executive/tasks/intake`, `/tasks/transitions`, `/work-queue`.
- **Watchdog**: `check_task_deadlines()` (rate-limit 10 phút) → EXPIRED có transition log.
- **M1 design docs**: `reports/DEOM_M1_{OPERATING_MODEL,PERMISSION_MATRIX,TASK_LIFECYCLE,APPROVAL_DESIGN}.md`.

### docs(status) — Q-1/Q-2/Q-5 + trạng thái dự án
- PROJECT_STATUS: ghi nhận git init (Q-1), journald persistent Pi5 với root cause vendor drop-in (Q-2), Bluetooth FastConnectable/AutoEnable (Q-5).
- REGISTER: +5 dòng quyết định có dấu thời gian + cách hoàn tác.
- HANDOFF_LATEST regen (validate exit 0) + bản lưu `HANDOFF_20261101_224214.md`.

## Kiểm định
- **Regression FULL: 3.071 PASS / 44 skipped / 0 FAIL** (baseline 3.034 + 37 test mới: `test_deom_m2_task_lifecycle.py`, `test_deom_m2_nl_intake.py`).
- `tools/validate_and_report.py` exit 0; Mirror F THÀNH CÔNG; secret scan sạch (3 file khớp regex đều là code pattern, không phải secret thật).
- Cây nội dung sau rewrite giống hệt cây trước rewrite (`git diff` = rỗng).

## Cách mở PR khi anh sẵn sàng
1. Tạo repo private mới (ví dụ `quan-ai-brain`) trên GitHub/GitLab → copy URL.
2. Chạy:
   ```
   cd "D:\AI\AI Quanpt1 2026\BRAIN"
   git remote add origin <URL>
   git push -u origin main
   git push -u origin feat/deom-m1-m2-task-lifecycle
   ```
3. Mở PR: nhánh `feat/deom-m1-m2-task-lifecycle` → `main`, tiêu đề **"feat(orchestration): DEOM M1+M2 — task lifecycle, verifier, NL intake"**, dán nội dung file này vào phần mô tả.
