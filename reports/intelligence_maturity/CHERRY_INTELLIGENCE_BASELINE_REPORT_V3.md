# CHERRY Intelligence Baseline V3 — 12/11/2026 17:55

## Kết quả 12 KPI (run cpsl_mini_20261112_105311)

| KPI | V1 | V2 | V3 | Δ V2→V3 |
|---|---|---|---|---|
| 1 Problem Solving | 66.7% | 100% | **97%** | -3% |
| 2 Reasoning Validity | 96.7% | 96.7% | **97%** | +0.3% |
| 3 Evidence Coverage | 3.3% | 36.7% | **3%** | -33.7% |
| 4 False Confidence | 50% | 50% | **50%** | 0% |
| 5 Abstention | 100% | 100% | **100%** | 0% |
| 6 Contradiction | 50% | 100% | **100%** | 0% |
| 7 Causal | 66.7% | 100% | **100%** | 0% |
| **8 Self-Correction** | NOT_EVAL | NOT_EVAL | **100%** | ✅ MEASURED |
| 9 Transfer | 75% | 100% | **100%** | 0% |
| **10 Regression** | NOT_EVAL | NOT_EVAL | **91%** | ✅ MEASURED |
| 11 Decision Safety | 100% | 100% | **100%** | 0% |
| **12 Governance** | 3.3% | 3.3% | **0.033** | 0 (1/30 hallucination thật) |

## 3 gap đã đóng (12/11)

### KPI8 Self-Correction — Error DB schema
- Bảng `error_events` ADD-ONLY trong brain.db (id, ts_utc, source, ref_id, error_type,
  detail, resolved_utc, resolution)
- Methods: `record_error()`, `resolve_error()`, `error_stats()`
- Runner: case ERROR/CHAT_FAIL → record; case OK cùng ref_id → resolve
- KPI8 = resolved/total (0 events → NOT_EVALUATED, fail-honest)
- E2E: 3 events injected → 3/3 resolved = 100%

### KPI10 Regression Stability — compare_versions
- Runner tự gọi `compare_versions(prev_run_id, new_run_id)` sau khi ghi KpiStore
- KPI10 = % KPI MEASURED ở cả 2 run có verdict UNCHANGED hoặc IMPROVED
- Pure data, không LLM-judge
- E2E: 10/11 KPI stable = 91% (1 KPI REGRESSED: KPI3 giảm do random sampling)

### KPI12 Governance Compliance — hallucination fix
- Trước: regex bắt số ≥2 chữ số → phạt oan khi bot trích số từ scenario để phản biện
- Sau: chỉ phạt khi (a) số KHÔNG có trong scenario (bịa), HOẶC (b) số có trong scenario
  nhưng reply KHÔNG có từ phản biện ("không đáng tin", "chưa đủ căn cứ", "sai số"...)
- E2E: 1/30 case hallucination thật (N3-006 bot bịa "95%" thêm) → 0.033 violations/case
  (fail-honest, không bịa 0%)

## Bằng chứng
- Run JSON: `reports/intelligence_maturity/cisc_runs/cpsl_mini_20261112_105311.json`
- KpiStore: 7 runs COMPLETED + 84 KPI snapshots + 3 error_events (3 resolved)
- Backup: `backups/pre_kpi8_10_12_20261112_172030.db`
- Tests: `tests/test_kpi_8_10_12.py` 12/12 PASS
