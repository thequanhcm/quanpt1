# CHERRY INTELLIGENCE MATURITY — MASTER PLAN V1.0
**Ngày:** 11/11/2026 | **Trạng thái:** PROPOSED — chờ owner duyệt trước khi triển khai production
**Nền tảng:** Task A→E Cognitive Core (reports/cognitive/, 11/11) + baseline measurement TASK 2/3 cùng phiên
**Nguyên tắc:** CHERRY MUST NOT CLAIM INTELLIGENCE — CHERRY MUST DEMONSTRATE INTELLIGENCE.

---

## 1. Mục đích
Chuyển trọng tâm từ "xây module nhận thức" (Cognitive Core) sang **chứng minh năng lực bằng đo lường độc lập**, theo 8 nhóm: Problem Solving · Reasoning Accuracy · Epistemic · Critical Thinking · Metacognition · Adaptive · Decision · Learning Effectiveness.

## 2. Phạm vi & mối quan hệ với Cognitive Core
- CIEE/CPSL/CISC/CIIA là **lớp đánh giá BÊN NGOÀI** — không đụng code nhận thức; chỉ ĐO và BÁO.
- Tái dùng tối đa: logical_reasoning V9, conflict_detector, CognitiveState, governance R0–R5, pytest harness hiện có (test_evaluation_harness, benchmark_v21).
- Tránh trùng lặp với CHERRY COGNITIVE BENCHMARK V1 (cognitive/): benchmark V1 đo năng lực nhận thức thành phần; CPSL đo **giải quyết vấn đề đầu-cuối** trên bài toán thật. Hai bộ chạy chung runner, giữ dataset tách biệt.

## 3. Kiến trúc 5 khối
```
┌────────────────────────────────────────────────────────────────┐
│ CIEE — Evaluation Engine (độc lập, không tin tự-chấm)          │
│  ┌──────────────┐ ┌───────────────┐ ┌───────────────────────┐  │
│  │ CPSL Lab     │ │ Uncertainty   │ │ Self-Correction       │  │
│  │ (5 nhóm bài  │ │ Framework     │ │ Engine (error DB +    │  │
│  │ toán thật)   │ │ (4 module)    │ │ regression per error) │  │
│  └──────┬───────┘ └───────┬───────┘ └───────────┬───────────┘  │
│         └────────────┬────┴─────────────────────┘              │
│                CISC Scorecard (12 KPI, không trộn điểm tổng)    │
│                        │                                        │
│                CIIA Independent Audit (PASS/PWL/FAIL/INCONCL)   │
└────────────────────────────────────────────────────────────────┘
```

## 4. Cách triển khai từng Phase (A→G)
| Phase | Nội dung | Sprint | R | Deliverable chính |
|---|---|---|---|---|
| A — Intelligence Baseline | Bộ probe 8 nhóm chạy thật + CIEE runner | INT-1 | R1 | test_report baseline + phiên bản BASELINE V1 |
| B — Problem Solving Lab | CPSL dataset 5 nhóm (trouble/infra/info/plan/novel) + train/val/hidden/adversarial/OOD split | INT-2 | R2 | cpsl dataset + runner + benchmark doc |
| C — Uncertainty & Evidence | uncertainty_estimator, confidence_calibrator, evidence_sufficiency_checker, abstention_policy | INT-3 | R2 | 4 module + 6 chỉ số đo được |
| D — Self-Correction | self_correction_engine + error database + regression-per-error | INT-4 | R2 | engine + error DB schema |
| E — Scorecard & Dashboard | CISC 12 KPI + dashboard spec + version comparison | INT-5 | R1 | scorecard + dashboard spec |
| F — Continuous Improvement | learning candidate eval + rollback + regression benchmark hằng tuần | INT-6 | R3 | pipeline học có kiểm soát |
| G — Independent Audit | CIIA protocol + lần audit đầu | INT-7 | R2 | audit report 4 trạng thái |

## 5. Tiêu chí nghiệm thu từng Phase (tóm tắt — chi tiết trong doc từng Phase)
- A: baseline chạy được, tái lập (2 lần chạy khớp ≥95%), mọi KPI có definition+dataset.
- B: ≥30 case/group nhóm 1-3; hidden test tách khỏi knowledge base (hash manifest); ground truth độc lập.
- C: 6 metrics đo được trên dataset thật; calibration error có con số; abstention có cả appropriate + unnecessary rate.
- D: ≥1 lỗi thật đi qua đủ chu trình 10 bước (baseline dùng lỗi backup 2AM + La La School); không xóa lịch sử lỗi.
- E: scorecard 12 KPI, nhóm thiếu data ghi NOT EVALUATED, không gán trọng số tự tiện.
- F: kiến thức mới đi OBSERVE→VALIDATE→EVALUATE→TEST→APPROVE→PROMOTE; rollback hoạt động.
- G: audit trả 1/4 trạng thái; INCONCLUSIVE KHÔNG tự chuyển PASS.

## 6. Rủi ro & chi phí tài nguyên
| Rủi ro | Mức | Giảm thiểu |
|---|---|---|
| CPSL dataset che định kiến code hiện có (hardcode theo code cũ) | Cao | ground truth xây từ INCIDENT THẬT (log 10-11/11) + biến thể sinh động; CIIA kiểm tra tính độc lập |
| Chạy benchmark đè production DB (102MB, đang LIVE) | Trung bình | benchmark đọc DB COPY mỗi lần chạy; không ghi vào brain.db; chạy ngoài giờ nhạy cảm |
| Chi phí LLM khi evaluating | Trung bình | deterministic-first: ~80% probe không cần LLM (đo bằng code/probe); LLM chỉ khi bắt buộc |
| Điểm đẹp giả (Goodhart) | Cao | không điểm tổng; report từng nhóm; CIIA có quyền FAIL; hidden test không cho Cherry thấy |
| Trùng lặp với Cognitive Core benchmark | Trung bình | phân vai rõ (§2); chung runner, dataset riêng |

Chi phí: ~0 module daemon mới; 1 runner script + dataset JSON; disk ~10MB; không tăng RAM thường trú (chạy theo yêu cầu).

## 7. Bằng chứng nền (đo thật 11/11 tối — TASK 2/3)
- 14 probes thật: **9 PASS / 3 FAIL / 2 PARTIAL** — chi tiết `CHERRY_INTELLIGENCE_TEST_REPORT.md`.
- 3 FAIL thật: (1) reasoning retrieval không thấy 10.874 tri thức (C2, D1) — gap lớn nhất; (2) ConflictDetector dead-code trên schema V9 (B2); (3) learning spam 1.837 rows (H2).
- Điểm mạnh có thật: abstention đúng lúc (C1), R0-R5 fail-closed (G1/G2), quarantine gate (H1), LLM fallback regression (F1), metacognition model (E1).

## 8. Trạng thái thực tế
- Đã xong: TASK 1-6 trong phiên này (inspect, measure, identify, design, plan, report).
- Chưa làm: mọi code/module CIEE-CPSL-CISC-CIIA — **chờ owner duyệt Phase A**.
- Pi5 offline: nhóm bài toán edge chạy BLOCKED, không giả kết quả.

---
*Fail-honest: mọi số "đo thật" đều có evidence probe JSON; mọi "PROPOSED" chưa có code.*
