# CHERRY_COGNITIVE_ERROR_DATABASE — thiết kế + dữ liệu seed
**Trạng thái:** PROPOSED — Phase D. File schema chi tiết nằm trong `CHERRY_SELF_CORRECTION_FRAMEWORK.md` (§3).

## 1. Mục đích
Kho lỗi tập trung append-only, mỗi lỗi có regression test riêng — "không được coi việc thay đổi câu trả lời là đã khắc phục lỗi".

## 2. Seed dữ liệu (lỗi THẬT đã xác minh trong 2 phiên 11/11 — nhập ngay khi Phase D duyệt)

| ID đề xuất | Loại | Lỗi | Root cause | Bằng chứng | Tác động | Regression test đề xuất |
|---|---|---|---|---|---|---|
| ERR-20261101-001 | PERCEPTION + SOURCE | La La School / Ghiền Mì Gõ nhiễm memory | Vosk fuzzy ≤3 lỗi khớp TV noise; mọi âm qua wake mặc định là owner | 20 episodes + 20 memories nhiễm (đã xóa verified=0); 19/19 noise test sau siết | Memory sai trong context | test_adversarial_audio (34 câu + biến thể) — CÓ sẵn từ a760ff3 |
| ERR-20261111-002 | VERIFICATION | ConflictDetector dead-code trên schema V9 | V31 query schema cũ (id/content/lifecycle_status) ≠ knowledge_units V9 | Probe B2: "no such column: id" — chỉ tương thích bảng memories cũ | 0 mâu thuẫn được phát hiện trên production | test_conflict_detector_on_v9_schema (chưa có — Phase D) |
| ERR-20261111-003 | EXECUTION | Backup 2AM chết 2 đêm liên tiếp | LastTaskResult 2147946720 chưa chẩn đoán; không alert khi backup thiếu | File mới nhất 09/11 44h; test_backup_fresh FAIL | Lưới an toàn dữ liệu hở | test_backup_task_result_zero + alert kiểm file mới nhất (Phase D) |
| ERR-20261111-004 | MEMORY | Nạp lặp rác học (1.837 rows "Test suite:*") | Learning ingest không dedupe ở write path + dual daemon nhân đôi | Quarantine LIKE '%Test suite:%' 1.837 và đang tăng | Nhiễu ground truth cho benchmark + tốn disk | test_ingest_skip_duplicates (pattern skill 27/10 — cần verify) |
| ERR-20261111-005 | REASONING | Retrieval mù kho lớn | LogicalReasoningEngine chỉ đọc knowledge_units (148), không nối semantic (5.052) + chroma (4.790) | Probes C2/D1: evidence=0 trên câu hỏi có trong kho | Mọi câu hỏi thật trả "không đủ bằng chứng" | test_reasoning_retrieves_semantic_memory (Phase B) |
| ERR-20261111-006 | MEMORY | Semantic dup 88 nhóm | Consolidation không dedupe statement | SQL GROUP BY HAVING c>1 = 88 nhóm | Memory trùng chiếm context | test_semantic_dedup_archive (Phase D, backup-first) |

## 3. Quy trình nhập seed
Khi Phase D duyệt: nhập 6 lỗi trên (không tự fix — lỗi #5 đã nằm trong COG-2, #4 trong COG-0; DB chỉ GHI NHẬN trạng thái, hành động sửa thuộc sprint tương ứng). Lỗi nào đã có regression test → status VERIFIED_FIXED; chưa có → OPEN với test đề xuất.

## 4. Đo lường từ Error DB
- Repeat rate: % lỗi tái phạm cùng loại sau khi VERIFIED_FIXED (30 ngày) — target 0.
- Time-to-verify: trung bình thời gian OPEN→VERIFIED_FIXED.
- Coverage: % lỗi có regression test khi đóng — target 100%.

## 5. Ràng buộc
- Append-only (history table); CIIA đối chiếu hash; không sửa quá khứ.
- Lỗi từ CPSL hidden tests KHÔNG được quay lại knowledge base (tránh leak ngược).
