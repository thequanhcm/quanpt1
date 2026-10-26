# DIGITAL EMPLOYEE BRAIN — GAP REGISTER (Sổ khoảng trống)

**Mã tài liệu:** GAP-QAB-DEB-20261026
**Cách dùng:** mỗi gap có ID cố định, trạng thái, chủ xử lý, sprint. Cập nhật sau mỗi sprint — không xóa dòng, chỉ đổi trạng thái (giữ lịch sử).
**Trạng thái:** OPEN / IN_PROGRESS / RESOLVED / ACCEPTED_RISK / WON'T_FIX

---

## Nhóm 1 — Runtime & Reliability (Sprint A-fix)

| ID | Khoảng trống | Bằng chứng đo | Mức chặn | Chủ | Sprint | Trạng thái |
|---|---|---|---|---|---|---|
| GAP-R1 | Ollama daemon OFFLINE (11434 URLError) | probe 2026-10-26 23:xx; fail test_keep_warm_pulse; skip BGE-M3 | CAO (embedding local + keep-warm chết) | quanpt1 bật + autostart; QAB viết hướng dẫn | A3 | OPEN |
| GAP-R2 | Task Scheduler QUAN_AIBRAIN_* chưa tạo | schtasks → "cannot find the file specified" | TRUNG (24/7 phụ thuộc login) | quanpt1 (cần Admin 1 lần) | A5 | OPEN |
| GAP-R3 | Watchdog chưa giám sát Ollama/NetChat/disk | logs/watchdog.log chỉ có startup | TRUNG | QAB | A1 | OPEN |
| GAP-R4 | Không có `/api/health` chuẩn (404) | probe /api/health → HTTPError 404 | TRUNG | QAB | A2 | OPEN |
| GAP-R5 | Không external monitor độc lập | không tìm thấy process ngoài | TRUNG | QAB+owner | A6 | OPEN |
| GAP-R6 | Pi 5 unreachable :8768 | probe URLError | THẤP (edge tạm dừng) | owner (mạng) | — | OPEN |
| GAP-R7 | 109 durable_tasks PENDING không có age-out policy | tasks.db đo | TRUNG | QAB | A4 | OPEN |

## Nhóm 2 — Cognitive (Sprint B/C)

| ID | Khoảng trống | Bằng chứng | Mức chặn | Sprint | Trạng thái |
|---|---|---|---|---|---|
| GAP-C1 | Không có CognitiveLoop (state machine 11 trạng thái) | import check — module missing | CAO (não điều phối chưa khép kín) | B1 | **RESOLVED 2026-10-26** — `cognition/cognitive_loop.py` + `reflection.py`, 17 tests, commit 9fbbf48 |
| GAP-C2 | Không có ReflectionLoop 12 câu hỏi | import check — module missing | CAO (học từ sai lầm chưa cơ chế) | B2 | **RESOLVED 2026-10-26** — `cognition/reflection.py`, 17 tests, commit 9fbbf48 |
| GAP-C3 | Self-model trả lời 12 câu hỏi 2.2 chưa nối probe thật | self_model_engine 242 dòng, cần verify evidence | CAO | C1 | **RESOLVED 2026-10-26** — `answer_state_questions()` probe thật (TCP + SQL + audit line count) + snapshot diff; 2 tests |
| GAP-C4 | Chưa có test khôi phục sau process restart giữa nhiệm vụ | test suite không có scenario | CAO | B1 | **RESOLVED 2026-10-26** — `test_recovery_after_restart_marks_unknown_not_rerun` PASS |
| GAP-C2 | Chưa phát hiện tri thức mâu thuẫn/lỗi thời trong 720 semantic | không có module/benchmark | TRUNG | C2 | **RESOLVED 2026-10-26** — `memory/knowledge_quality.py` + 5 tests; scan thật: 780 semantic (673 exact dups!), 41,790 candidates (40,304 internal dups, 533 unique), 21 conflict suspects |
| GAP-C6 | Confidence chưa hiệu chuẩn (calibration) | không có benchmark nào đo | CAO (cấm auto-execute cho tới khi có) | E5 | OPEN |

## Nhóm 3 — Memory & Learning (Sprint C/D)

| ID | Khoảng trống | Bằng chứng | Mức chặn | Sprint | Trạng thái |
|---|---|---|---|---|---|
| GAP-M1 | 37,716 candidates quarantined không có thẩm định theo lô | brain.db đo | TRUNG (noise chèn ép tri thức DC) | C3 | **IN_PROGRESS 2026-10-26** — PromotionPolicy dry-run 2,000 items: 1,430 NEEDS_OWNER (lớp L1/L2/L3), 505 low-confidence, 41 dup, 24 conflict; phát hiện 99% trùng lặp (40,304 internal dups) — chờ owner duyệt chiến lược dedup |
| GAP-M2 | Promotion policy chưa phân lớp tri thức | continuous_learning_engine tự thăng cấp theo ngưỡng duy nhất | CAO | D2 | **RESOLVED 2026-10-26** — `memory/promotion_policy.py` lớp L0-L3: chỉ L0 (confidence ≥0.8, không dup/conflict) tự thăng cấp; L1/L2/L3 luôn NEEDS_OWNER; 8 tests |
| GAP-M3 | Chưa đo learning effectiveness (tỷ lệ false promotion) | không có report | TRUNG | D3 | OPEN |
| GAP-M4 | Memory benchmark chỉ precision@k/MRR cơ bản | memory/benchmark.py 349 dòng | TRUNG | C4 | OPEN |

## Nhóm 4 — DC Domain (Sprint E)

| ID | Khoảng trống | Bằng chứng | Mức chặn | Sprint | Trạng thái |
|---|---|---|---|---|---|
| GAP-D1 | Không connector BATTERY AI V4 | integration/ không có module | CAO cho DC-1 | E1 | OPEN (chờ endpoint+auth từ owner) |
| GAP-D2 | Không connector DCIM/VDCIM/Monitoring/Network | integration/ trống | CAO cho DC-1 | E1+ | OPEN |
| GAP-D3 | Incident intelligence (triage/correlate/RCA) chưa có module | import check missing | CAO | E3 | OPEN |
| GAP-D4 | Chưa có daily digest qua NetChat | bot chỉ responder, chưa digest định kỳ | TRUNG | E4 | OPEN |
| GAP-D5 | DC benchmark độc lập chưa xây | không có | CAO (điều kiện tin triage ≥90%) | E5 | OPEN |

## Nhóm 5 — Execution & Governance (Sprint F/G)

| ID | Khoảng trống | Bằng chứng | Mức chặn | Sprint | Trạng thái |
|---|---|---|---|---|---|
| GAP-X1 | Approval Card 13 trường qua NetChat chưa có | server chưa có /api/approvals/* | CAO | F2 | OPEN |
| GAP-X2 | Kill-switch chưa drill thật | emergency_states bảng có, chưa test E2E | CAO | F3 | OPEN |
| GAP-X3 | DelegationGrant engine chưa có (bảng DB đã có sẵn) | governance/delegation.py missing | CAO cho Sprint G | G1 | OPEN |
| GAP-X4 | Chưa có test: LLM đề xuất hành động trái policy bị chặn độc lập | test suite thiếu scenario | CAO | B/F | OPEN |
| GAP-X5 | Chưa có test: approval hết hạn/replay bị từ chối | test suite thiếu scenario | CAO | F | OPEN |
| GAP-X6 | Sandbox dry-run ≥10 lần/hành động mới chưa là quy trình đo được | thiết kế Sprint 6 có, chưa bộ đếm | TRUNG | F3 | OPEN |

## Nhóm 6 — Đã RESOLVED (lịch sử)

| ID | Khoảng trống | Ngày giải | Bằng chứng |
|---|---|---|---|
| GAP-00 | Tri thức DC Skill/ 10 items quarantined chờ duyệt | 2026-10-26 | owner duyệt; 10/10 → semantic_memory với approved_by=quanpt1; commit 4bdd774 |
| GAP-00b | Báo cáo DC chưa phản ánh batch duyệt | 2026-10-26 | báo cáo cập nhật 4 mục; commit 4bdd774 |
| GAP-00c | 24/7 không có launcher sau reboot | 2026-10-26 | KHOI_DONG_24_7.bat trong Startup folder; 4 thành phần chạy thật |

## Quy tắc cập nhật

1. Sau mỗi sprint: đổi trạng thái + thêm bằng chứng (số đo, commit SHA, test result).
2. Không bao giờ chuyển OPEN → RESOLVED nếu chỉ có code, chưa có test + evidence thật.
3. Gap chặn an toàn (GAP-C6, GAP-X2, GAP-X4) KHÔNG được bỏ qua để tăng tốc sprint sau.
