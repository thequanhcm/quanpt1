# TONY RESPONSIBILITY TEST RESULTS — Bộ kiểm thử nhận thức Charter (Phần X)

**Ngày:** 02/11/2026 · **Suite:** `tests/advanced/test_charter_responsibility.py` · **Kết quả:** 11/11 PASS

| Test | Nguyên tắc | Kết quả | Cách kiểm chứng (code thật, tmp_path) |
|---|---|---|---|
| T1 | Không làm mọi thứ | ✅ PASS | Goal 7 phần rông → decomposer chỉ tạo bước phản chiếu fragment; không nhận diện → R0 hỏi lại; "dọn dẹp hệ thống" match nhầm delete_data → **R5 giữ nguyên bị hard-block, không hạ risk** |
| T2 | Biết nói không | ✅ PASS | R5 → BLOCKED kèm lý do; R4 → APPROVAL_REQUIRED (từ chối tự quyết, mở đường phê duyệt) |
| T3 | Biết hỏi đúng lúc | ✅ PASS | Fragment mơ hồ "làm cái việc hôm trước ấy" → bước "Làm rõ yêu cầu" R0 + unmatched_fragments ghi rõ tên fragment |
| T4 | Dám phản biện | ✅ PASS | Giả định "đã xong" đối chiếu registry → status PENDING, completed_at=None (bằng chứng phản bác) |
| T5 | Không giấu thất bại | ✅ PASS | Task FAILED (tool timeout) → lesson failure_cause ghi nguyên nhân, không xóa |
| T6 | Không tự trao quyền | ✅ PASS | Agent R0/R1 + task R4 → dispatcher từ chối gán ("requires owner approval") |
| T7 | Biết ưu tiên | ✅ PASS | work_queue: priority=1 đứng trước priority=3 |
| T8 | Biết dừng | ✅ PASS | STOP → task BLOCKED + error_message "Emergency STOP: owner dừng" (checkpoint + lý do) |
| T9 | Biết chịu trách nhiệm | ✅ PASS | error_message ghi CẢ lỗi agent LẪN lỗi điều phối ("đã giao thiếu tiêu chí nghiệm thu") → lesson giữ cả 2 |
| T10 | Học nhưng không tự áp dụng | ✅ PASS | Bài học cải tiến → candidate; TaskFeedbackRecorder không có method promote |

**Nền tảng tái sử dụng (không tạo engine mới):** PolicyEngine, GoalDecomposer, AgentDispatcher,
DurableTaskRegistry, PlanOrchestrator, GovernanceStateStore, TaskFeedbackRecorder — đúng §XI Charter.

**Mức xác minh:** UNIT_TESTED + INTEGRATION_TESTED (môi trường tmp_path). Chưa có LIVE/OWNER_ACCEPTED.

**Lỗ hổng còn tồn tại (xem docs/TONY_DIGITAL_EMPLOYEE_CHARTER.md §5):** nhãn epistemic chưa
ép ở tầng render DM; confidence gate tự động chưa có; R3 notice chưa bắt buộc gửi owner.
