# CHERRY INTELLIGENCE BASELINE REPORT — Phase 4 (12/11/2026)

**Trạng thái:** Phase 4 Baseline hoàn thành — 12 KPI có số liệu thật từ CPSL mini 30 case.
**Run chính thức:** `cpsl_mini_20261112_054832` (KpiStore: `run_20261112_055457_a75f33`)
**Run thử trước:** `cpsl_mini_20261112_054250` (giữ nguyên trong ADD-ONLY store — trung thực)

## 1. Phạm vi
- **Dataset:** CPSL mini 30 case (12 N1 troubleshooting + 6 N2 infrastructure + 6 N3 information + 3 N4 planning + 3 N5 novel)
- **Ground truth:** từ sự cố THẬT 10-11/11/2026 đã record trong reports (DHCP, NoAudioReceived, dual daemon, 0x800710E0, vcgencmd, cleanup rollback, path Desktop, Tailscale, keyring, chroma track, port bind, TV noise, quarantine, evidence, sample size, deploy, sprint, batch, camera lock, version compare, dedup)
- **Pipeline:** POST /api/chat 8765 (chat thật, model `zai-org/GLM-5.3-Flash`)
- **Scoring:** khách quan 5 chiều (root_cause keywords + hypotheses + evidence_cited + abstention + hallucination penalty) — KHÔNG LLM-judge
- **Contradiction pairs:** 2 cặp (KPI6)
- **KpiStore:** ADD-ONLY 3 bảng (benchmark_runs / kpi_snapshots / version_comparisons) trong brain.db

## 2. Kết quả 12 KPI (run chính thức)

| KPI | Trạng thái | Giá trị | n | Ghi chú |
|---|---|---|---|---|
| 1 | MEASURED | 66.7% | 30 | Problem Solving Accuracy — root_cause keywords ≥1 |
| 2 | MEASURED | 96.7% | 30 | Reasoning Validity — không hallucination penalty |
| 3 | MEASURED | 3.3% | 30 | Evidence Coverage — used_memories/external_lookup (THẤP: retrieval gap 148/10.874 KU đã biết) |
| 4 | MEASURED | 50.0% | 2 | False Confidence Rate — hallucination trên trap cases (n=2 nhỏ) |
| 5 | MEASURED | 100.0% | 5 | Appropriate Abstention — missing-data abstain đúng (n=5) |
| 6 | MEASURED | 50.0% | 2 | Contradiction Detection — 1/2 pair (CP-2 Pi5 stale chưa bắt được) |
| 7 | MEASURED | 66.7% | 3 | Causal Reasoning — case cơ chế nhân-quả (n=3) |
| 8 | NOT_EVALUATED | — | — | Self-Correction — Error DB Phase D chưa dựng |
| 9 | MEASURED | 75.0% | 4 | Transfer Learning — OOD cases (n=4) |
| 10 | NOT_EVALUATED | — | — | Regression Stability — cần ≥2 run (baseline này là run 1) |
| 11 | MEASURED | 100.0% | 1 | Decision Safety — risk_probe refusal đúng (n=1) |
| 12 | MEASURED | 3.3% | 30 | Governance Compliance — 1/30 hallucination penalty (n=30) |

## 3. RED FLAG giữa 2 run (cùng dataset, scoring update)

| KPI | Run thử | Run chính thức | Δ | Nguyên nhân |
|---|---|---|---|---|
| 1 | 93.3% | 66.7% | -26.7% ⚠ | scoring update (excerpt 400→1200 + gov patterns mở rộng) |
| 2 | 96.7% | 96.7% | +0.0%    | ổn định |
| 3 | 3.3% | 3.3% | +0.0%    | ổn định |
| 4 | 50.0% | 50.0% | +0.0%    | ổn định |
| 5 | 100.0% | 100.0% | +0.0%    | ổn định |
| 6 | 50.0% | 50.0% | +0.0%    | ổn định |
| 7 | 100.0% | 66.7% | -33.3% ⚠ | scoring update (excerpt 400→1200 + gov patterns mở rộng) |
| 9 | 75.0% | 75.0% | +0.0%    | ổn định |
| 11 | 0.0% | 100.0% | +100.0% ⚠ | scoring update (excerpt 400→1200 + gov patterns mở rộng) |
| 12 | 3.3% | 3.3% | +0.0%    | ổn định |

**Trung thực:** RED FLAG ở đây là do scoring thay đổi (chứ không phải model regression). KpiStore ADD-ONLY giữ cả 2 run để audit.

## 4. Giới hạn (ghi rõ)
- **n=30 nhỏ** — CI rộng; hidden set 100 case là Phase B (chưa làm).
- **KPI 8 (Self-Correction)** + **KPI 10 (Regression Stability)** = NOT_EVALUATED (chưa đủ điều kiện đo).
- **KPI 3 (Evidence Coverage) 3.3%** — phản ánh retrieval gap 148/10.874 KU đã biết từ Phase A; không phải lỗi benchmark.
- **KPI 4/6/7/11** có n nhỏ (1-3) — chỉ mang tính thăm dò, cần mở rộng dataset.
- **Contradiction pair CP-2** (Pi5 stale) bot chưa bắt được — cần bổ sung pattern.
- **Scoring khách quan** dùng keyword match — có thể under-credit các câu trả lời đúng nhưng diễn đạt khác; Phase 5 CIIA sẽ audit mẫu.

## 5. Bằng chứng verify
- 30/30 case OK (không case ERROR/CHAT_FAIL)
- 32 LLM calls (30 case + 2 pair) · 384.6s · model `zai-org/GLM-5.3-Flash`
- KpiStore: 1 run COMPLETED + 12 KPI snapshots (run chính thức); 2 run test cũ giữ nguyên (ADD-ONLY)
- Dashboard live: `GET /api/intelligence/scorecard` → `BASELINE_ESTABLISHED`, coverage 10/12, trend 5 KPI
- Tests: `tests/test_cpsl_runner.py` 10/10 PASS (mock 100%, không gọi chat thật)
- Full regression: 3698 PASS / 6 fail (cũ) / 28 skip — không tăng fail

## 6. File tạo/sửa
- `data/cognitive/cpsl/cpsl_mini_dataset.py` (240 dòng) — 30 case + 2 pair
- `data/cognitive/cpsl/cpsl_mini_30.json` — dataset JSON
- `tools/run_cpsl.py` (450 dòng) — runner + scoring + KPI mapping + KpiStore writer
- `tests/test_cpsl_runner.py` (180 dòng) — 10 test mock
- `reports/intelligence_maturity/cisc_runs/cpsl_mini_*.json` + `.md` — run records
- `reports/intelligence_maturity/CHERRY_INTELLIGENCE_BASELINE_REPORT.md` (file này)

## 7. Bước tiếp theo (chờ owner duyệt)
- **Phase 5 (CIIA Audit)** — audit độc lập dashboard + scoring mẫu
- **Rehabilitate 4.568 tri thức** docs/code thật đang quarantine oan
- **Mở rộng CPSL** lên 100 case (Phase B) — hidden set tách vật lý
- **Pi5 mất mạng lần 2** — chờ owner kiểm nguồn 5V/5A
- **Watchdog chết không rõ nguyên nhân** — điều tra root cause

---
*Phase 4 Baseline xong — DỪNG. Chờ Owner Authority (Quanpt1) duyệt.*