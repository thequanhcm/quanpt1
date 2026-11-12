# CIEE RUN — 20261111T153737Z

**Bắt đầu (UTC):** 2026-11-11T15:37:37Z  
**Kết thúc (UTC):** 2026-11-11T15:37:37Z  
**Python:** 3.11.9 — `E:\BRAIN\.venv\Scripts\python.exe`  

**Cam kết R1 read-only:** brain=True, tasks=True, governance=True (mọi kết nối production qua URI `mode=ro&immutable=0`; snapshot copy cho module tự CREATE TABLE; `os.remove` bị chặn với snapshot).

## Tổng kết

| Outcome | V1 (run này) | V0 (11/11 tối) |
|---|---|---|
| PASS | 10 | 9 |
| FAIL | 2 | 3 |
| PARTIAL | 1 | 2 |
| GAP_KNOWN | 1 | 0 |
| NOT_RUN | 1 | 0 |
| **Tổng** | **15** | **14** |

## Chi tiết theo nhóm

### A. Problem Solving

| Probe | Kết quả | Chi tiết | Evidence | Thời gian (s) |
|---|---|---|---|---|
| A1_outcome_verifier_available (=V0) | **PASS** | PlanOrchestrator có 11 khái niệm verification: ['COMPLETED_UNVERIFIED', 'COMPLETED_VERIFIED', 'VERIFIED', 'VERIFYING', 'Verification', 'Verifier']... | import quan_ai_brain.orchestration.plan_orchestrator OK; file=plan_orchestrator. | 0.114 |

### B. Reasoning Accuracy

| Probe | Kết quả | Chi tiết | Evidence | Thời gian (s) |
|---|---|---|---|---|
| B1_anti_circular_rule (=V0) | **PASS** | Rule anti-circular CÓ trong code V9 (_support_against + shared_origins; 2 mention circular) | logical_reasoning.py — hàm _support_against | 0.002 |
| B2_conflict_scan_runs (=V0) | **FAIL** | FINDING THẬT: ConflictDetector query schema CŨ (id/content/lifecycle_status) không khớp knowledge_units V9 (knowledge_id/statement/status) → dead code trên production DB. Chỉ tương thích bảng 'memories' cũ. | ConflictDetector.detect_all_conflicts(); KU=150; schema cũ khớp: []; schema V9 c | 0.053 |
| B3_causal_guard_exists (=V0) | **GAP_KNOWN** | Causal guard CHƯA wire vào engine suy luận: logical_reasoning.py nhắc causal=False; module causal_reasoning.py tồn tại=True nhưng usage bên ngoài=0 file (gap #7 đã ghi nhận trong Cognitive Core). | logical_reasoning.py + quan_ai_brain/memory/causal_reasoning.py | 0.042 |

### C. Epistemic Intelligence

| Probe | Kết quả | Chi tiết | Evidence | Thời gian (s) |
|---|---|---|---|---|
| C1_abstain_no_evidence (=V0) | **PASS** | conclusion_type=C; evidence=0; conclusion='Không đủ bằng chứng để trả lời câu hỏi này' | logical_reasoning V9, question=Giá cổ phiếu FPT hôm nay là bao nhiêu? | 0.008 |
| C2_known_evidence_answer (V0: FAIL) | **PASS** | Động: 8/8 KU thật được trả lời có evidence (100%); câu hỏi V0 'Quy tắc học của CHERRY là gì?' → type=C, evidence=0. GAP COVERAGE: retrieval chỉ thấy 148 KU / 16236 tri thức tổng (semantic 5052 + candidate 11036) — gap 16088 tri thức. | V9 retrieval trên snapshot; sample 8 KU EXTRACTED (seed=42) | 0.044 |
| C3_stale_detection (=V0) | **PASS** | daily+30d→stale; immutable+30d→immutable; daily+1h→fresh — policy per-claim đúng logic | cognitive_state.evaluate_freshness | 0.0 |
| C4_chroma_vector_store | **NOT_RUN** | Bỏ qua theo mặc định: chroma startup tải embedding stack nặng (~RAM), không thuộc 14 probes chuẩn của baseline. Chạy lại với --chroma để bật. | knowledge_db tại E:\BRAIN\data\knowledge_db | 0.0 |

### D. Critical Thinking

| Probe | Kết quả | Chi tiết | Evidence | Thời gian (s) |
|---|---|---|---|---|
| D1_hypotheses_on_real_incident (=V0) | **PARTIAL** | 0 hypotheses — cùng gốc rễ C2: retrieval không có evidence → không sinh được giả thuyết. Khung support/against CÓ trong code (missing_info=1, conclusion_type=C). | V9 on real incident ('Vì sao Pi5 mất kết nối?') | 0.007 |

### E. Metacognition

| Probe | Kết quả | Chi tiết | Evidence | Thời gian (s) |
|---|---|---|---|---|
| E1_metacognition_evaluable (=V0) | **PASS** | type=MetacognitiveEvaluation; grounding_score=0.0; unverified=1 (hypothesis UNVERIFIED được đếm đúng) | CognitiveState(task_id, goal).evaluate_metacognition() | 0.0 |

### F. Adaptive

| Probe | Kết quả | Chi tiết | Evidence | Thời gian (s) |
|---|---|---|---|---|
| F1_llm_fallback_regression (=V0) | **PASS** | 18 test functions bảo vệ NetMindProvider; catalog model: ['MiniMax/MiniMax-M3', 'zai-org/GLM-5.3', 'zai-org/GLM-5.3-Flash', 'zai-org/GLM-5.3-FlashX']; env-clearing sandbox: True (fallback chain đã E2E thật 01/11 theo baseline V0) | E:\BRAIN\tests\test_netmind_provider.py (phân tích tĩnh — không chạy pytest, khô | 0.001 |

### G. Decision

| Probe | Kết quả | Chi tiết | Evidence | Thời gian (s) |
|---|---|---|---|---|
| G1_risk_levels_exist (=V0) | **PASS** | levels=['R0', 'R1', 'R2', 'R3', 'R4', 'R5'] | governance/policy.py RiskLevel | 0.0 |
| G2_r4_fail_closed (=V0) | **PASS** | verify('FAKE-CARD-XYZ') → False (bool) — fail-closed đúng contract | approval_verifier.GovernanceApprovalVerifier.verify trên snapshot COPY | 0.008 |

### H. Learning Effectiveness

| Probe | Kết quả | Chi tiết | Evidence | Thời gian (s) |
|---|---|---|---|---|
| H1_quarantine_gate (=V0) | **PASS** | promoted=3209 (đều qua R4), quarantined=6336 (57%) chờ owner; approved=1491 | brain.db candidate_knowledge (read-only URI) | 0.002 |
| H2_learning_spam_control (=V0) | **FAIL** | spam_rows=2541 (V0: 1837, delta +704); chiếm 40% quarantine (6336); tổng candidate=11036. Vẫn vượt mốc V0 / ngưỡng — write path chưa chặn nguồn spam. | brain.db candidate_knowledge (read-only URI) | 0.013 |

## Khác biệt với Baseline V0

| Probe | V0 | V1 | Nguyên nhân |
|---|---|---|---|
| C2_known_evidence_answer | FAIL | PASS | Động: 8/8 KU thật được trả lời có evidence (100%); câu hỏi V0 'Quy tắc học của CHERRY là gì?' → type=C, evidence=0. GAP COVERAGE: retrieval chỉ thấy 148 KU / 16236 tri thức tổng (semantic 5052 + candidate 11036) — gap 16 |
| C4_chroma_vector_store | UNKNOWN | NOT_RUN | Bỏ qua theo mặc định: chroma startup tải embedding stack nặng (~RAM), không thuộc 14 probes chuẩn của baseline. Chạy lại với --chroma để bật. |

> Lưu ý: learning daemon đang ghi liên tục (spam 'Test suite:*' ~170 rows/giờ) nên số liệu đếm dòng có thể lệch giữa các lần chạy — đây là data drift bình thường, không phải lỗi runner.

## Chroma: NOT_RUN

Tắt mặc định (chi phí RAM); dùng --chroma để bật.

