# BÁO CÁO KỸ THUẬT — self_study_v2_chu_trinh_tu_hoc_that

> Sinh tự động 03/11/2026 07:54:40 (giờ VN) theo chỉ thị owner 02/11/2026:
> báo cáo chi tiết sau MỖI tác vụ — có phân tích, đánh giá, định hướng, đề xuất.

## 1. TÓM TẮT ĐIỀU HÀNH
Xử lý tồn tại tự học (từ netChat 07:49): Tự học V1 chỉ hardcoded 3 kịch bản cogitate — không học được gì. Xây Self-Study Engine V2 (cognition/self_study.py): SCAN gaps từ 113 experience_lessons thật → STUDY web_search thật → SYNTHESIZE có provenance → DEDUP word-set chống dupes 44% → QUARANTINE vào candidate_knowledge (KHÔNG tự nạp semantic_memory — test chốt) → REPORT trung thực. Đấu nối pipeline candidate_knowledge CÓ SẴN (7.950 rows) thay vì tạo mới. 7/7 test PASS trên copy brain.db production. Demo: web_search thật quarantine 2 knowledge conf=0.7. Capability self_learning_v1 nâng IMPLEMENTED_UNTESTED → VERIFIED_ACTIVE.

## 2. PHÂN TÍCH
- Tồn tại 1: cogitate() hardcoded (camera/AEC/barge-in) — thought không phản ánh học tập thật.
- Tồn tại 2: TONY khai 'DB học tập gần trống' nhưng candidate_knowledge có 7.950 rows — khai sai vì không biết pipeline có sẵn; đã đấu nối thay vì tạo mới (§II kế thừa).
- Tồn tại 3: dupes 44% — dedup containment >0.75 với guard chống false-positive statement ngắn.
- Ranh giới §XI: engine chỉ chạy khi được gọi; quarantine KHÔNG BAO GIỜ ghi semantic_memory.

## 3. ĐÁNH GIÁ
- tests/test_self_study.py 7/7 PASS (copy brain.db thật).
- tests/test_capability_registry.py 5/5 PASS (sau khi cập nhật).
- Demo thật: SCAN 5 gaps → web_search thật → 2 knowledge quarantined conf=0.7.

## 4. ĐỊNH HƯỚNG
- Cho phép chạy chu kỳ định kỳ qua CSEF RC (chờ duyệt).
- Đấu thought tự học vào chat pipeline.
- Sprint 3 CAI V3: nghiên cứu tài liệu Pi5 thật khi có SSH.

## 5. ĐỀ XUẤT
- Owner duyệt: (1) sprint này; (2) RC chạy chu kỳ tự học định kỳ 1h/lần khi idle.

## 6. BẰNG CHỨNG & MINH CHỨNG SỐ
- reports/SELF_STUDY_V2_REPORT.md
- reports/TEST_RUN_SELF_STUDY.txt
- tests/test_self_study.py (7 PASS)
- src/quan_ai_brain/cognition/self_study.py

## 7. RỦI RO & TRUNG THỰC
- Gap hiện tại chủ yếu là lessons về 'task candidate' (metadata) — chưa nhiều gap tri thức sâu; sẽ giàu hơn khi episodes thực tế tăng.
- Researcher prod dùng web_search — phụ thuộc Internet (như audit UAME đã nêu).

## 8. VIỆC CHỜ OWNER QUYẾT ĐỊNH
- Duyệt sprint + RC chạy định kỳ.
- Bấm tạo PR (10 commits).

## PHỤ LỤC — FILE/SAN PHẨM LIÊN QUAN
- `src/quan_ai_brain/cognition/self_study.py`
- `tests/test_self_study.py`
- `src/quan_ai_brain/cognition/capability_registry.py`
- `reports/SELF_STUDY_V2_REPORT.md`
