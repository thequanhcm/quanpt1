# CHERRY_INTELLIGENCE_MATURITY_DASHBOARD_PHASE0_REPORT
**Ngày:** 11/11/2026 tối | **Executor:** TONY (netMind Desktop, profile tony)
**Phạm vi:** Phase 0 — System Discovery. **KHÔNG thay đổi production code / schema / không kích hoạt tự nâng cấp.**
**Ký hiệu:** [VERIFIED] đo bằng tool thật · [INFERRED] suy luận từ kiến trúc · [UNKNOWN] chưa xác định · [BLOCKED] chưa thể thực hiện · [RISK] rủi ro · [RECOMMENDATION] đề xuất.

---

## 1. Hiện trạng hai giao diện [VERIFIED]

| | 8765 (Hội thoại nhận thức) | 8766 (Phòng điều hành) |
|---|---|---|
| HTTP | 200, 19.3KB HTML | 200, 100KB HTML |
| Title | "QUAN AI BRAIN — Trợ Lý Điều Hành Số" | "QUAN AI BRAIN — Phòng Điều Hành & Tham Vấn Chủ Nhân" |
| Tabs | chat, memories, planning, learning (`tab-btn-*` / `panel-*`) | persona, consultation, learning, orchestration, dialogue, netchat, edge-sync, pi5-embodiment, workbench, deep-memory (`data-tab`) |
| JS | app.js (49KB v5.5) + avatar_engine | executive.js (218KB) + wake/avatar |
| CSS | style.css (31KB) | executive.css (68KB) |

Đối chiếu 2 ảnh owner (đã vision_analyze phiên trước): khớp — 8766 có sidebar "QUAN AI BRAIN", tab "Nhân Sự Số"/"Tham Vấn & Duyệt"; 8765 là trang "Hội Thoại Nhận Thức & Giọng Nói". [VERIFIED]

## 2. Backend & API hiện có [VERIFIED]

- **server.py duy nhất** serve cả 2 cổng: **152 API routes** đã đếm (`re` trên source).
- Nhóm API tái sử dụng được cho dashboard:
  - Khu vực A (Overview): `/api/health`, `/api/status`, `/api/self/model`, `/api/executive/overview`
  - Khu vực E (Self-Correction/Learning): `/api/improvement/report` (LIVE — trả tasks 579/approvals 25/experience 183/quarantine 11.006 với evidence đính kèm), `/api/executive/learning/reports`, `/api/memory/review/*`
  - Khu vực F (Governance/Audit): `/api/approvals` (25 cards, 24 approved), governance.db (approvals/approval_requests/governance_events), audit.db (audit_logs)
  - KPI nền: `/api/self/state`, `/api/executive/tasks/cognitive-state`, `/api/experience/lessons`
- Không có API benchmark/KPI nào — chưa tồn tại. [VERIFIED]

## 3. Database map (29 DB read-only đã kiểm) [VERIFIED]

Liên quan trực tiếp dashboard:
- `brain.db` (103MB): episodes 3.054 · candidate_knowledge (quarantined 6.267 / approved 1.491 / promoted 3.209) · semantic_memory 5.052 · knowledge_units 148 · **review_findings 114 / review_changes 3** / review_questions 52 · knowledge_conflicts · feedback 936
- `tasks.db` (11.9MB): durable_tasks — COMPLETED 5 / COMPLETED_VERIFIED 1 / CANCELLED 524 / archived 49 + task_transitions (audit lifecycle)
- `governance.db`: approvals + approval_requests + governance_events + approval_cards
- `learning_reports.db`, `learning_checkpoints.db`, `learning_sandbox.db`, `gov_sandbox.db`
- `audit.db` (0.6MB audit_logs), `health_history.db`, `consultations.db`, `evidence.db`

Không có bảng benchmark/KPI. [VERIFIED]

## 4. Evaluation Engine đã có — TÁI SỬ DỤNG được phần lớn [VERIFIED — quan trọng nhất]

`src/quan_ai_brain/learning/evaluation.py` (214 dòng, LIVE, có test `test_evaluation_harness.py` PASS trong full suite):
- `ContinuousEvaluationHarness(workspace, memory_store)` — 2 method:
  - `run_benchmark_suite()` — chạy bộ benchmark task, trả `BenchmarkTaskResult(task_name, category, passed, score, latency_ms, evidence, details)`
  - `measure_upgrade_progress()` — trả `EvaluationMetric(overall_score_before/after, latency before/after, improvement_pct, **regression_detected**, benchmark_results, confidence_score, recommendation)`
- `learning/periodic_reporter.py` (390 dòng): PeriodicLearningReport + DB history — nền có sẵn cho "lịch sử benchmark".
- `benchmark_v21_performance.py`: benchmark hiệu năng (latency/throughput/memory/cache, V11 vs V20 comparison) — kiểu khác (performance, không phải intelligence) nhưng pattern pytest-benchmark tái dùng được.
- Baseline probes của em (14 probes 8 nhóm A-H, `_probe_results_task2.json`) + framework thiết kế CIEE/CPSL/CISC đã có (reports/intelligence_maturity/).

**Kết luận kiến trúc:** Không tạo backend mới — mở rộng `learning/evaluation.py` + thêm `intelligence/` module mỏng bên cạnh, đúng hướng "không tạo hai nguồn sự thật". [INFERRED — sẽ chốt thiết kế ở Phase 1-2]

## 5. Dữ liệu nào ĐÃ tính được 6 KPI ngay hôm nay [VERIFIED]

| KPI | Nguồn có sẵn | Có thể tính? |
|---|---|---|
| KPI1 Problem Solving Accuracy | durable_tasks (5 COMPLETED/1 VERIFIED — quá ít), CPSL chưa có | **INSUFFICIENT DATA** (đúng luật — không hiện 0%) |
| KPI2 Evidence Coverage | ReasoningResult.evidence_refs (V9) + probes baseline | CÓ — đo được trên probe set (baseline V0: 2/4 câu evidence=0) |
| KPI3 Reasoning Accuracy | Chưa có rubric + bộ chấm độc lập | **CHƯA** (cần CPSL Phase B) |
| KPI4 Uncertainty Calibration | conclusion A/B/C + confidence_breakdown V9; chưa có calibrator | **CHƯA** (chỉ đo được abstention thô) |
| KPI5 Self-Correction | review_findings 114 / review_changes 3 + Error DB chưa có | CÓ thô — nhưng "sửa thành công" cần đủ tiêu chí → hiện **INSUFFICIENT** |
| KPI6 Verified Improvement | measure_upgrade_progress có sẵn nhưng chưa có bộ benchmark intelligence chuẩn | **CHƯA** (cần baseline chuẩn trước) |

## 6. Dữ liệu CHƯA có [VERIFIED]

1. Bảng benchmark_runs/evaluation_results/kpi_snapshots (chưa tồn tại — Phase 2 thiết kế).
2. CPSL dataset (100 case, hidden/adversarial/OOD split).
3. Rubric bộ chấm Reasoning + Independent Evaluator.
4. confidence_calibrator.
5. Hidden benchmark protection (hash manifest + tách khỏi ingest path).

## 7. Rủi ro tích hợp [RISK]

1. **R1 (cao):** dashboard "đẹp" nhưng dữ liệu INSUFFICIENT — chống bằng hiển thị N/A bắt buộc (đã thiết kế states).
2. **R2 (trung bình):** executive.js 218KB + executive.html 102KB — sửa cẩn thận, thêm tab mới bằng append section riêng + JS file riêng (`intelligence_tab.js`) tránh đụng code cũ; cache-bust version.
3. **R3 (trung bình):** 2 server process đang LIVE phục vụ owner — deploy phải restart đúng quy trình `_spawn_dual_servers` (đã làm nhiều lần, rollback = revert).
4. **R4 (trung bình):** benchmark chạy trên brain.db LIVE — phải đọc DB copy (snapshot) tránh lock với learning daemon đang ghi 5 phút/lần.
5. **R5 (thấp):** hidden test leak qua chroma ingest — chống bằng thư mục riêng `data/cognitive/cpsl/hidden/` ngoài ingest path + hash manifest.
6. **R6 (cao):** Goodhart — điểm đẹp che yếu; chống bằng không-điểm-tổng + NOT EVALUATED + audit độc lập.

## 8. Kiến trúc đề xuất (map thực tế) [INFERRED]

```
(đã có) server.py 8765/8766 ── 152 API ── static/ (index + executive)
(đã có) learning/evaluation.py  ──► mở rộng: benchmark_cases V2 (6 KPI-oriented categories)
(MỚI)   src/quan_ai_brain/intelligence/
          kpi_engine.py            # 6 KPI calculators — input từ benchmark_runs + evidence
          benchmark_runner.py      # wraps ContinuousEvaluationHarness + probes + CPSL
          kpi_store.py             # bảng mới trong brain.db ADD-ONLY: benchmark_runs,
                                   #   evaluation_results, kpi_snapshots, version_comparisons
(MỚI)   API (3 read-only): /api/intelligence/scorecard | /audit-status | /errors
(MỚI)   static/intelligence_tab.{js,css} + 1 section trong executive.html (Khu vực A-F)
          + index.html 8765: badge trạng thái nhỏ dẫn sang 8766 (không phá 4 tab cũ)
```

## 9. Lộ trình + file sẽ sửa/tạo [RECOMMENDATION]

| Phase | Tạo/Sửa | R |
|---|---|---|
| 1 Design | `reports/.../CHERRY_INTELLIGENCE_DASHBOARD_DESIGN.md` + mockup HTML tĩnh (không đụng server) | R1 |
| 2 Data | `intelligence/kpi_store.py` (schema ADD-ONLY migration có backup) + `kpi_engine.py` + tests | R2 |
| 3 Impl | `intelligence_tab.js/css` + executive.html (append) + 3 API + restart servers + verify browser 2 cổng | R2 |
| 4 Baseline | `benchmark_runner.py` + chạy CPSL mini (30 case) + `CHERRY_INTELLIGENCE_BASELINE_REPORT.md` | R2 |
| 5 Audit | Independent audit protocol (đã thiết kế) → `CHERRY_DASHBOARD_INDEPENDENT_AUDIT.md` | R2 |

Kiểm thử: pytest mỗi module + full regression + verify thật 2 URL bằng curl/browser; rollback = git revert + restore DB backup (backup ngay trước migration).

## 10. Trạng thái [BLOCKED / UNKNOWN]

- [BLOCKED] Đo KPI1/KPI3/KPI4/KPI6 đầy đủ — cần CPSL dataset + rubric + calibrator (Phase 2/4).
- [BLOCKED] Benchmark nhóm System Troubleshooting edge — Pi5 offline vật lý từ 10/11 13:31 (chờ owner).
- [UNKNOWN] Cấu hình nội bộ browser owner (dark/light mode) — sẽ dùng CSS vars của app, hỗ trợ cả hai.
- [UNKNOWN] Số liệu "BATTERY/UPS/PAC-CRAC" (nhóm Data Center trong master prompt §III.4) — hệ thống chưa có cảm biến nhóm này; cần owner xác nhận có nguồn data nào không, nếu không sẽ ghi BLOCKED thay vì bịa.

## 11. Đề xuất phê duyệt [RECOMMENDATION]

1. **Duyệt Phase 1** (Design + mockup tĩnh — không đụng server, rollback trivial).
2. Duyệt luôn Phase 2 schema ADD-ONLY (có backup) nếu muốn nhanh.
3. Xác nhận: nhóm bài toán "Battery & Power / Data Center" — có data thật không? (không có → ghi BLOCKED, không bịa).
4. Giữ nguyên tắc: KHÔNG hiện số khi INSUFFICIENT — chấp nhận dashboard đầu tiên nhiều N/A là TRUNG THỰC.

---
*Phase 0 xong — DỪNG. Chờ Owner Authority (Quanpt1) duyệt trước Phase 1.*
