# DEOM V4 — P7 DESIGN: BUSINESS SCENARIOS L1–L6 (Phần 11)

**Ngày:** 02/11/2026 02:45 · **Owner duyệt:** "anh duyệt" (02/11) · **Trạng thái:** IMPLEMENTED + TESTED

## 1. Nguyên tắc

6 kịch bản nghiệp vụ thật của anh Quân chạy **trên component thật** (goal_decomposer →
plan_orchestrator → task_registry → state machine G-C → feedback M6), toàn bộ tmp_path —
không đụng production, không LLM, không thực thi ngoài sandbox. Mỗi kịch bản kiểm chứng
một cam kết DEOM: phân quyền đúng tầng rủi ro, fail-closed, evidence, learn.

## 2. Kịch bản

| Level | Kịch bản | Điều kiện nghiệm thu chính |
|---|---|---|
| L1 | Đọc thông tin (R0) "xem tiến độ báo cáo quý 4" | plan R0, chạy dry-run sandbox, task COMPLETED, có evidence |
| L2 | Viết tổng hợp (R1) "soạn báo cáo tuần gửi anh" | steps tuần tự DAG, verify result trước COMPLETED |
| L3 | Tổ chức lịch/quản lý (R2) "kiểm tra lịch họp ngày mai" | cần tool ngoài → WAITING_APPROVAL/PENDING_APPROVAL, không tự chạy |
| L4 | Việc chuỗi phụ thuộc (DAG) "kiểm kê xong mới tổng hợp" | bước sau KHÔNG chạy khi bước trước FAILED (chặn DAG) |
| L5 | R4 approval binding G-A | consume với fingerprint đúng → 1 lần; sai → BLOCKED |
| L6 | Học từ trải nghiệm (M6+P5) | sau terminal → lesson candidate; LearningMetrics đếm đúng |

## 3. Môi trường

tmp_path registry + governance + feedback; orchestrator với InertProcessBackend sandbox;
không network, không thiết bị. Kết quả chỉ ở mức UNIT/INTEGRATION_TESTED — không tự nâng
END_TO_END/LIVE (Phần 1: không tự nâng trạng thái xác minh).
