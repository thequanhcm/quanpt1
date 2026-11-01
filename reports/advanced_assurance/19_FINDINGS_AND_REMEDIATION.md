# ADVANCED ASSURANCE — P1..P4 CHỮA LỖI PHÁT HIỆN (Findings & Remediation), 02/11/2026 01:55

**Quy trình đúng Phần 21:** TEST → OBSERVE → IDENTIFY → ROOT CAUSE → FIX (sandbox scope) → REGRESSION → so sánh trước/sau.

## Findings bảng

| Finding ID | Suite phát hiện | Severity | Mô tả | Root cause | Fix đã áp dụng | Regression test |
|---|---|---|---|---|---|---|
| ADV-001 | F3 Approval Race | **P1** | 10 thread consume đồng thời 1 card → **10 consume đều thành công** (double-consume thật) | `consume()` đọc state rồi UPDATE không có điều kiện — cửa sổ đua check-then-act | `UPDATE … WHERE consumed_at_utc IS NULL` + rowcount=1 mới claim thành công (atomic) | `test_n_threads_consume_exactly_once` (trước fix FAIL — bằng chứng phát hiện) |
| ADV-002 | E5 Restart Recovery | P2 | `recover_in_flight_tasks` trả list TaskRecord nhưng test đếm theo string — API không rõ | API trả object list | test dùng `[t.task_id for t in …]` (test-side, không đổi code) | `test_recover_in_progress_not_reexecuted` |
| ADV-003 | E2 Atomicity | P3 | transition PENDING→VERIFYING không bị registry chặn ở tầng update (chỉ verify_task có guard) | registry tin tưởng caller truyền đúng trạng thái | GHI NHẬN, không sửa code lõi trong P1 (rủi ro ảnh hưởng supervisor đang chạy) — nâng thành P2 backlog cần owner duyệt thiết kế state-machine chặt hơn | `test_transaction_atomicity_on_bad_transition` |
| ADV-004 | P0 Audit | P3 | Emergency API không có GET status an toàn (chỉ POST side-effect) | thiết kế Sprint 9 | backlog (đã ghi ở DEOM V4 M0) | — |

**Không có BLOCKER theo Phần 19.1** — R5/R4/STOP/self-approval/audit đều giữ vững qua mọi test P1–P4.

## So sánh trước/sau

| Chỉ số | Trước (handoff 7d9e7cd) | Sau (P1–P4) |
|---|---|---|
| FULL regression | 3.206 PASS / 0 FAIL / 44 SKIP | **3.257 PASS / 0 FAIL / 44 SKIP** (+51 test mới) |
| Suite advanced | không tồn tại | **51 test** (registry 14 + security 23 + chaos 9 + concurrency 5) |
| Approval consume race | LỖI (double-consume) | ĐÃ SỬA + test chứng minh 1/10 thắng |
| IN_PROGRESS recovery | có code, chưa test restart thật | test E5 chứng minh OUTCOME_UNKNOWN, không re-execute |

## Trạng thái theo thang Phần 1 (không tự nâng Level 5)

- Governance core: **ADVERSARIAL_TESTED** (D1/D3/D6 matrix) — không phải LIVE.
- Task registry: **CHAOS_TESTED** (E2/E5/E6) + CONCURRENCY_TESTED (F1/F2/F3).
- LLM provider: **INTEGRATION_TESTED** (E1 offline matrix; LIVE ở health check 00:38 riêng).
- Test Governance Center: **UNIT_TESTED** (14 test).
- Pi5 voice: **DESIGNED** — chờ phần cứng (giữ trung thực).
