
---

## Baseline V1 — CIEE Runner chuẩn hóa (11/11/2026 22:37)

**Bộ probe:** 14 probes chuẩn hóa vào `tools/ciee/` (probe class có probe_id / group A-H / setup / run / assert / evidence). **Run:** `20261111T153748Z` — evidence đầy đủ tại `reports/intelligence_maturity/ciee/runs/20261111T153748Z/` (results.json + REPORT.md + manifest.txt).

**Kết quả: 10 PASS / 2 FAIL / 1 PARTIAL / 1 GAP_KNOWN / 1 NOT_RUN / 0 ERROR — trên 15 probes, 8 nhóm A-H.**

| Probe | V0 | V1 |
|---|---|---|
| A1_outcome_verifier_available | PASS | PASS |
| B1_anti_circular_rule | PASS | PASS |
| B2_conflict_scan_runs | FAIL | FAIL |
| B3_causal_guard_exists | GAP_KNOWN | GAP_KNOWN |
| C1_abstain_no_evidence | PASS | PASS |
| C2_known_evidence_answer | FAIL | PASS ← khác V0 |
| C3_stale_detection | PASS | PASS |
| D1_hypotheses_on_real_incident | PARTIAL | PARTIAL |
| E1_metacognition_evaluable | PASS | PASS |
| F1_llm_fallback_regression | PASS | PASS |
| G1_risk_levels_exist | PASS | PASS |
| G2_r4_fail_closed | PASS | PASS |
| H1_quarantine_gate | PASS | PASS |
| H2_learning_spam_control | FAIL | FAIL |
| C4_chroma_vector_store | ? | NOT_RUN ← khác V0 |

**Khác biệt với V0 (nguyên nhân):**

- `C2_known_evidence_answer`: FAIL → PASS — Động: 8/8 KU thật được trả lời có evidence (100%); câu hỏi V0 'Quy tắc học của CHERRY là gì?' → type=C, evidence=0. GAP COVERAGE: retrieval chỉ thấy 148 KU / 16236 tri thức tổng (semantic 5052 + candidate 11036) — gap 16
- `C4_chroma_vector_store`: UNKNOWN → NOT_RUN — Bỏ qua theo mặc định: chroma startup tải embedding stack nặng (~RAM), không thuộc 14 probes chuẩn của baseline. Chạy lại với --chroma để bật.

**Chuẩn hóa so với V0:** V0 là script ad-hoc 1 lần; V1 là runner tái lập (`python E:/BRAIN/tools/ciee/ciee_runner.py`), mọi DB production chỉ đọc qua URI `mode=ro&immutable=0` + snapshot copy cho module tự CREATE TABLE; probe đo động trên KU thật (C2, seed=42) để giảm nhiễu mẫu cố định; Chroma probe ghi NOT RUN có lý do.

