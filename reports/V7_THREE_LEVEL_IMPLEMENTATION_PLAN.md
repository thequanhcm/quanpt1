# V7 THREE-LEVEL IMPLEMENTATION PLAN — 27/10/2026

**Nguyên tắc:** lát cắt dọc (§11), reuse-first, bằng chứng quyết định cấp độ. Không big-bang.

## Giai đoạn 2 — CẤP 1 (IN_PROGRESS)

| # | Việc | Cách làm | Tiêu chí nghiệm thu |
|---|------|----------|---------------------|
| 1.1 | Nâng **SkillRegistry schema** lên chuẩn V7 §3.2 | Bổ sung trường vào `SkillRecord` (back-compat `from_dict` default): `input_schema`, `output_schema`, `permissions_required`, `data_sources`, `timeout_policy`, `error_policy`, `risk_level`, `test_suite_ref`, `last_verified_at`; giữ lifecycle fail-closed V6 | Unit test round-trip + lifecycle; registry hiện có load OK không mất dữ liệu |
| 1.2 | **Tool Registry** cho tool cấp thấp | Mở rộng `CapabilityRegistry` bằng lớp `ToolRecord` riêng (không đụng 9 caps system): tool_id, version, schema, permissions, timeout/error policy, risk, test refs, last_verified_at, known_limitations | API/unit; trạng thái phân biệt PROPOSED→...→AVAILABLE |
| 1.3 | Seed 6 skill mục tiêu §3.3 (đối chiếu hiện trạng — không trùng) | `TASK_STATUS_RECONCILIATION` = nâng cấp metadata của skill AVAILABLE hiện có (đổi name, thêm schema); 5 skill còn lại đăng ký mới trạng thái PROPOSED/IMPLEMENTED_IN_SANDBOX theo đúng thực tế | Mỗi skill có đủ trường V7; trạng thái phản ánh thật (không AVAILABLE khi chưa test) |
| 1.4 | Test bắt buộc §3.5 | Mỗi skill test case: input hợp lệ/không hợp lệ/thiếu/mâu thuẫn/nguồn unavailable/timeout/quyền thiếu/độc hại/schema sai/từ chối | Suite pass; fail-honest mọi nhánh |
| 1.5 | Báo cáo `V7_LEVEL1_CAPABILITY_REPORT.md` | Đánh giá đủ 8 điều kiện nghiệm thu Cấp 1 | `LEVEL_1_PASSED` chỉ khi đủ; ngược lại ghi đúng phần thiếu |

## Giai đoạn 3 — CẤP 2 (IN_PROGRESS sau Cấp 1)

| # | Việc | Ghi chú |
|---|------|---------|
| 2.1 | Bài toán 1: email kiểm tra tiến độ do chủ cung cấp trực tiếp | Nguồn thật được cấp quyền: email (dán chat/file), `data/tasks.db`, `data/consultations.db`, `data/todos.db`, `reports/`; Vmail/Outlook ghi BLOCKED |
| 2.2 | Chạy qua pipeline: A→E (phân tích email → nguồn → hợp nhất → đối chiếu chéo → tư vấn) | Dùng TaskPipeline 11-stage + skills Cấp 1; UNKNOWN/NOT_VERIFIED trung thực; mỗi kết luận truy vết được nguồn |
| 2.3 | Báo cáo `V7_LEVEL2_REAL_TASK_REPORT.md` + lưu bằng chứng §4.3 | `LEVEL_2_PASSED` chỉ khi đủ 8 điều kiện; thiếu quyền → `LEVEL_2_PARTIAL` |

## Giai đoạn 4 — CẤP 3 (sau khi có bài toán 1 thật)

- Task Retrospective (tái dùng `improvement_report.py` + log thật) → Capability Gap Registry (tái dùng `info_gap_tasks` S14) → Verified Workflow Memory (mở rộng SkillRegistry: workflow_id, step_sequence, verified_runs, last_verified_at) → candidate cải tiến (giữ version cũ, test so sánh, rollback).
- Bài toán 2 (đợt tiến độ khác — chủ cung cấp) → tái sử dụng workflow đã lưu; đo đối chiếu (thời gian, số bước làm lại, chất lượng bằng chứng).
- Báo cáo `V7_LEVEL3_CONTINUOUS_IMPROVEMENT_REPORT.md` — `LEVEL_3_PASSED` chỉ khi có lần tái sử dụng thành công có đo; ngược lại `LEVEL_3_IN_PROGRESS`.

## Giai đoạn 5-6 — TÁI SỬ DỤNG + NỘP ĐỘNG (chưa kích hoạt nếu bạn muốn) — NGHIỆM THU

- Bảng chấm §7: mỗi cấp trạng thái NOT_STARTED/IN_PROGRESS/BLOCKED/PASSED/REGRESSION_DETECTED — trạng thái tổng = cấp cao nhất ĐẠT.
- Regression §9: suite liên quan + full suite; phân biệt lỗi có trước (0 hiện tại) vs mới.
- `V7_TEST_RESULTS.md` + `V7_FINAL_HANDOFF.md`.

## Phạm vi & an toàn (lặp lại cho chắc)

- R5 chặn cứng; R4 theo cơ chế hiện hành; SPRINT6 sign-off còn PENDING → production runner/Job Object live/subprocess spawner giữ nguyên INERT_STAGING.
- Không tự commit/push — mỗi giai đoạn xong: trình diff + kết quả test, chờ chủ duyệt rồi mới commit (khác quy tắc V6).
- Không tự cài package mới; chỉ stdlib + dependency hiện có.
- Nguồn chưa có quyền (Vmail/Outlook) = BLOCKED, không suy diễn.

## Trạng thái ban đầu (§7)

| Cấp | Trạng thái |
|-----|-----------|
| Cấp 1 | IN_PROGRESS (có sẵn: TaskPipeline, SkillRegistry V6, CapabilityRegistry; thiếu: schema V7, 5 skill, test §3.5) |
| Cấp 2 | NOT_STARTED |
| Cấp 3 | NOT_STARTED |
| **Tổng thể** | **Cấp 1 IN_PROGRESS** |

---
*Kế hoạch bởi QUAN AI BRAIN Agent · V7 · chờ chủ duyệt hoặc chỉnh sửa trước khi triển khai Giai đoạn 2.*
