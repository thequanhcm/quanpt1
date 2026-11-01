# DEOM V4.0 — M0 ACTUAL STATE AUDIT (bản 2, 02/11/2026 01:15)

**Cơ sở:** Master Continuation Prompt V4.0 · **Phạm vi:** đối chiếu 12 điều kiện nghiệm thu + baseline handoff + 44 SKIP · **Phương pháp:** đo trực tiếp workspace (git/API/test), KHÔNG dựa handoff cũ.

---

## 1. Baseline đã xác minh lại (01:15 02/11/2026)

| Mục | Prompt V4 ghi | Thực tế đo được |
|---|---|---|
| Branch | feat/deom-m1-m2-task-lifecycle | ✅ đúng |
| Commit | `e0d6135` | ⚠️ **cũ** — đã tiến tới `eafdf36` (M6 docs) sau M4+M5+M6 |
| Working tree | có thay đổi | ✅ chỉ 2 file chroma.sqlite3 (binary churn) + báo cáo mới — bảo toàn, không đụng |
| Tests | 3.166 passed | ⚠️ **cũ** — hiện **3.194 PASS / 0 FAIL / 44 SKIP** (sau M6) |
| Sprint6 signoff | PENDING_OWNER_SIGNOFF | ✅ vẫn đúng — giữ nguyên, không tự ký |

## 2. Đối chiếu 12 điều kiện nghiệm thu DEOM → bằng chứng

| # | Điều kiện | Trạng thái | Bằng chứng (code + test có thật) |
|---|---|---|---|
| 1 | Giao việc (NL) | **TESTED** | nl_intake M2 + `test_deom_m2_nl_intake.py` |
| 2 | Tổ chức (plan) | **TESTED** | TaskPlan/TaskStep/DAG + `test_plan_orchestration_lifecycle.py` |
| 3 | Quản lý (lifecycle) | **TESTED** | DurableTaskRegistry 579+ tasks, transition log + `test_deom_m2_task_lifecycle.py` |
| 4 | Phân quyền (backend) | **TESTED** | PermissionResolver + `test_deom_m4_permissions.py` (36) |
| 5 | Điều phối agent | **TESTED** | AgentDispatcher R3/R4/R5 không tự gán + `test_deom_m3_dispatcher.py` (34) |
| 6 | Thực hiện | **TESTED** (inert sandbox) | PlanOrchestrator + SafeToolSandbox — production runner VẪN tắt (đúng §XVIII) |
| 7 | Kiểm chứng | **TESTED** | verifier fail-honest COMPLETED_VERIFIED/UNVERIFIED |
| 8 | Báo cáo | **LIVE_VERIFIED** (daily) | morning_report.py cron 8h chạy thật; weekly/monthly/scorecard **CHƯA CÓ** |
| 9 | Học tập | **TESTED** | TaskFeedbackRecorder (M6, lesson luôn candidate) + experience retrieval |
| 10 | Phục hồi | **TESTED** | `test_supervisor_recovers_in_flight_tasks_on_init` + recover_tasks |
| 11 | Giao tiếp PC+Pi5 | **LIVE_VERIFIED** | edge READY, heartbeat 2s, HMAC fail-closed |
| 12 | Quản trị | **TESTED** | STOP/FREEZE emergency POST + `test_persistent_governance.py` |

**API đo live 01:15 (8766, server thật PID 11112):** supervisor 200 (dữ liệu registry thật), tasks 200 (active_tasks từ DurableTaskRegistry), emergency → POST-only thiết kế (GET 404), POST hành động lạ bị từ chối đúng (`Invalid action; must be 'stop', 'freeze', or 'resume'`).

## 3. Phân loại 44 SKIP (đo bằng `pytest -rs`, đủ 44/44)

| Loại | Số | Chi tiết |
|---|---|---|
| Hardware unavailable (Pi5) | 1 | `test_vietnamese_tts.py:266` |
| Missing dependency | 7 | pytesseract/Pillow ×6, Azure Speech SDK ×1 |
| Covered elsewhere | 6 | v39 "tested in integration/unit tests" |
| Placeholder | 3 | v14 UI API pending |
| Known defect (fix pending) | 14 | v15 db-lock ×1; v17 ×4; v18 ×4; v39 ×5 |
| Manual verification | 13 | v21 ×7, v25 ×3, v15 ×2 … |

**Trung thực:** 14 "known defect" + 3 placeholder là nợ kỹ thuật sprint V14–V18 CŨ, ngoài lõi DEOM; không chặn DEOM nhưng cần backlog riêng.

## 4. Gap còn lại so với prompt V4 (sau M0–M6)

1. **§6.2 Approval binding fingerprint** — card M4 có task_id+scope nhưng KHÔNG có fingerprint nội dung hành động; hành động đổi sau duyệt chưa bị chặn code-level → **G-A (làm ngay)**.
2. **§X Weekly/Monthly + Scorecard** — chỉ có daily; cần scorecard từ task_feedback.db với chỉ số đo được.
3. **§5.1 TaskRecord thiếu `root_task_id`/`version`/`blocker`** — có parent_task_id + checkpoint; root/version/blocker dẫn xuất hoặc ADD COLUMN nullable kiểu M2.
4. **TEST 9 mâu thuẫn 2 agent** — cognitive có, dispatcher chưa có test đối chiếu.
5. **TEST 10 reuse E2E** — retrieval có, chưa có test 2 nhiệm vụ tương tự → tái sử dụng.
6. **Emergency API thiếu GET status** — chỉ POST side-effect action.

## 5. Increment G-A — Approval Action Fingerprint (§6.2)

- **Hiện trạng:** `create_card()` không nhận fingerprint; `consume()` không đối chiếu nội dung đã duyệt.
- **Tái sử dụng:** ApprovalCardService (M4), PermissionResolver (M4), plan_orchestrator wire (M4), DB riêng approval_cards_v2.db (isolation, hoàn tác = xoá file).
- **File đổi:** `approval_service.py` (schema +1 cột nullable, create_card +verify helper), `permission_resolver.py` (đối chiếu trước consume), `plan_orchestrator.py` (cung cấp fingerprint khi check), test mới.
- **Thiết kế:** `action_fingerprint = sha256(goal|action_summary|scope|params)`. create_card tính từ nội dung TRÌNH owner; consume(action_fingerprint=…) → lệch ≠ khớp → BLOCKED + event FINGERPRINT_MISMATCH, fail-closed. Card cũ fingerprint NULL → fail-closed (không bỏ qua).
- **Test:** ~8 case (khớp, đổi summary, đổi scope, đổi risk không thể, NULL fingerprint, consume sau mismatch, wire orchestrator, event log).
- **Rủi ro:** card cũ không fingerprint → bị chặn (mong muốn — fail-closed); migration ADD COLUMN nullable không đụng dữ liệu.
- **Rollback:** xoá `data/approval_cards_v2.db` + git revert 1 commit.

## 6. Điều KHÔNG làm (§XVIII)

Không production executor/daemon mới; không đổi R0–R5; không mở R4/R5; không promote; không đụng Sprint6 signoff; không push.

---
*DEOM V4.0 M0 audit — measured 02/11/2026 01:15 · mọi dòng TESTED có file test thật PASS trong regression 3.194/0/44.*
