# BÁO CÁO KỸ THUẬT — v5_sprint1_learning_foundation_audit

> Sinh tự động 03/11/2026 13:03:52 (giờ VN) theo chỉ thị owner 02/11/2026:
> báo cáo chi tiết sau MỖI tác vụ — có phân tích, đánh giá, định hướng, đề xuất.

## 1. TÓM TẮT ĐIỀU HÀNH
V5.0 SPRINT 1 — Learning Foundation Audit (baseline trước khi xây Autonomous Learning V3). Audit thật bằng SQL trực tiếp + trace mã nguồn + regression 8:04. Kết quả: Self-Study Engine V2 đã chạy thật (scanner đọc goal thật, dedup containment, quarantine-only, web_search thật); candidate_knowledge 8.149 rows 100% source_ref, dupes giảm 44%→0.9%; promotion_policy đã có và chạy đúng (L0 auto ≥0.8, L1/L2/L3 NEEDS_OWNER) — tri thức còn quarantined là do CHÍNH SÁCH không phải thiếu pipeline. Thiếu: Learning Planner, Deep Understanding A-E, Contradiction Detection, Meta-Learning, Budget, Session Evidence, Experience-to-Knowledge Pipeline (113 lesson chỉ metadata, 524 task CANCELLED chưa khai thác). Regression 3.538/0/47 vs baseline 3.540 (2 skip có chủ đích, đã ghi lý do). Đã đề xuất kiến trúc V3 kế thừa 100% + kế hoạch Sprint 2-8 kèm file/test/rủi ro, CHỜ OWNER DUYỆT trước khi triển khai sandbox.

## 2. PHÂN TÍCH
- Git: local b7da039 ahead-3 so với master 55b2403 qua PR #3 — không reset/force, chờ merge.
- Tri thức chưa vào Memory: promotion_policy L1/L2/L3 = NEEDS_OWNER (đúng thiết kế bảo mật), không phải lỗi pipeline.
- Knowledge đã học (MCP/A2A/QEP conf 0.85) rơi vào L2/L3 → cần owner review để promote.
- Experience pipeline: 113 experience_lesson chỉ là metadata; 524 CANCELLED task chưa được phân tích root-cause — nguồn học lớn nhất chưa khai thác.
- Confidence không có cột riêng — parse từ rationale text (mong manh, Sprint 2 nên chuẩn hóa).

## 3. ĐÁNH GIÁ
- Regression full: 3.538 PASS / 0 FAIL / 47 skipped (8:04) — baseline giữ vững.
- 8.149 candidate_knowledge: 100% provenance, dupes 0.9%.
- Promotion policy verify qua mã nguồn + dữ liệu promoted 3.209 rows đúng kênh L0.

## 4. ĐỊNH HƯỚNG
- Sprint 2 (chờ duyệt): Awareness Map + Gap Discovery + Priority + Planner.
- Sprint 3: Research Orchestrator + Source Reliability + Contradiction.
- Sprint 4: Experience-to-Knowledge Pipeline (học từ 524 CANCELLED task).
- Sprint 5-8: Meta-Learning, Scheduler+Budget, Governance+Evidence, Challenge E2E.

## 5. ĐỀ XUẤT
- Owner duyệt Sprint 2 triển khai trong sandbox (không đụng production).

## 6. BẰNG CHỨNG & MINH CHỨNG SỐ
- reports/AUTONOMOUS_LEARNING_BASELINE.md
- reports/TEST_RUN_V5_SPRINT1.txt
- commit 72b79b7

## 7. RỦI RO & TRUNG THỰC
- Nghiên cứu phụ thuộc Internet (đã nêu UAME).
- Scanner đa bảng có thể chậm — bắt buộc LIMIT + budget Sprint 2.
- Meta-learning tự đánh giá có thể lệch — cần benchmark tiêu chí khách quan.

## 8. VIỆC CHỜ OWNER QUYẾT ĐỊNH
- Duyệt Sprint 2 sandbox.
- Merge PR #3 nếu chưa (commit b7da039).

## PHỤ LỤC — FILE/SAN PHẨM LIÊN QUAN
- `reports/AUTONOMOUS_LEARNING_BASELINE.md`
- `src/quan_ai_brain/cognition/self_study.py`
- `src/quan_ai_brain/memory/promotion_policy.py`
