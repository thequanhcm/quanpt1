# CHERRY Intelligence Baseline V2 — 12/11/2026 (sau rehabilitate)

**Run:** cpsl_mini_20261112_090345
**Duration:** 505s (8.4 phút)
**Cases:** 30 (CPSL mini)
**Model:** zai-org/GLM-5.3-Flash

## So sánh V1 → V2 (sau rehabilitate 3951 tri thức docs/code thật)

| KPI | V1 | V2 | Δ | Ghi chú |
|---|---|---|---|---|
| 1 Problem Solving | 66.7% | **100%** | +33.3% | Tất cả case đúng root_cause |
| 2 Reasoning Validity | 96.7% | 96.7% | 0% | Đã cao sẵn |
| 3 Evidence Coverage | 3.3% | **36.7%** | +33.3% | Retrieval gap giảm 10x (148→~1600 KU usable) |
| 4 False Confidence | 50% | 50% | 0% | n=2, cần thêm case |
| 5 Abstention | 100% | 100% | 0% | Đã đạt |
| 6 Contradiction | 50% | **100%** | +50% | Cả 2 pair đều detect được |
| 7 Causal | 66.7% | **100%** | +33.3% | Tất cả 3 case đúng |
| 8 Self-Correction | NOT_EVALUATED | NOT_EVALUATED | — | Cần Error DB |
| 9 Transfer | 75% | **100%** | +25% | Tất cả 4 OOD case đúng |
| 10 Regression | NOT_EVALUATED | NOT_EVALUATED | — | Runner chưa so sánh 2 run |
| 11 Decision Safety | 100% | 100% | 0% | Đã đạt |
| 12 Governance | 3.3% | 3.3% | 0% | Cần thêm governance pattern |

## Kết luận

**Rehabilitate 3951 tri thức docs/code thật** đã cải thiện mạnh:
- 5/10 KPI MEASURED tăng (KPI1, 3, 6, 7, 9)
- 0 KPI giảm
- KPI3 (Evidence Coverage) tăng 10x — retrieval gap giảm từ 148/10.874 lên ~1600/10.874

**Gap còn lại:**
- KPI8: cần Error DB schema (sprint riêng)
- KPI10: runner cần thêm logic so sánh 2 run
- KPI12: governance pattern cần mở rộng

## Bằng chứng

- Run JSON: `reports/intelligence_maturity/cisc_runs/cpsl_mini_20261112_090345.json`
- KpiStore: 2 runs COMPLETED + 24 KPI snapshots
- Backup trước rehabilitate: `data/pre_rehabilitate_20261112_133541.db`
