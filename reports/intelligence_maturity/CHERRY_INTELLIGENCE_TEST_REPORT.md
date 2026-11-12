# CHERRY INTELLIGENCE TEST REPORT — BASELINE V0 (11/11/2026 tối)
**Bộ probe:** 14 probes trên 8 nhóm năng lực (A-H) — chạy bằng code thật trên production DB (read-only), evidence `_probe_results_task2.json`.
**Kết quả: 9 PASS / 3 FAIL / 2 PARTIAL — đây là BASELINE V0 chưa hiệu chỉnh, số tuyệt đối sẽ thay đổi khi dataset chuẩn ở Phase A.**

---

## Kết quả từng nhóm

### A. Problem Solving — 1/1 PASS
| Probe | Kết quả | Bằng chứng |
|---|---|---|
| A1 Outcome verifier có sẵn (PlanOrchestrator + Task Verifier DEOM M2) | PASS | import + module exists |

### B. Reasoning Accuracy — 1 PASS / 1 FAIL / 1 GAP
| Probe | Kết quả | Bằng chứng |
|---|---|---|
| B1 Chống vòng tròn (shared_origins) | PASS | code V9 có rule "nhiều KU cùng gốc 1 nguồn ≠ đa bằng chứng độc lập" |
| B2 ConflictDetector chạy trên DB thật | **FAIL** | query schema CŨ (`id, content, lifecycle_status`) ≠ knowledge_units V9 (`knowledge_id, statement, status`) → **dead code** trên production; chỉ tương thích bảng `memories` cũ |
| B3 Causal guard | GAP_KNOWN | chưa có module causal_reasoner (đã ghi gap Cognitive #7) |

### C. Epistemic Intelligence — 2/3 PASS
| Probe | Kết quả | Bằng chứng |
|---|---|---|
| C1 Abstention khi không đủ bằng chứng | PASS | "Giá cổ phiếu FPT?" → conclusion C "Không đủ bằng chứng để trả lời câu hỏi này" (0.01s) |
| C2 Trả lời CÓ bằng chứng từ kho | **FAIL** | "Quy tắc học của CHERRY?" → evidence=0 dù kho có 10.874 tri thức — **retrieval V9 chỉ thấy 148 knowledge_units** |
| C3 Stale detection | PASS | FRESH/STALE/EXPIRED/IMMUTABLE + freshness_policy per-claim; claim 1 tháng + policy daily → STALE đúng |

### D. Critical Thinking — PARTIAL
| Probe | Kết quả | Bằng chứng |
|---|---|---|
| D1 Sinh giả thuyết trên sự cố thật ("Vì sao Pi5 mất kết nối?") | PARTIAL | 0 hypotheses — cùng gốc rễ C2: không có evidence → không sinh được giả thuyết. Khung support/against CÓ trong code |

### E. Metacognition — 1/1 PASS
| Probe | Kết quả | Bằng chứng |
|---|---|---|
| E1 MetacognitiveEvaluation chạy được | PASS | CognitiveState(task_id, goal).evaluate_metacognition() → MetacognitiveEvaluation |

### F. Adaptive — 1/1 PASS
| Probe | Kết quả | Bằng chứng |
|---|---|---|
| F1 LLM fallback regression tồn tại | PASS | test_netmind_provider.py có chuỗi fallback 7 model (đã E2E thật 01/11) |

### G. Decision — 2/2 PASS
| Probe | Kết quả | Bằng chứng |
|---|---|---|
| G1 R0–R5 tồn tại | PASS | governance/policy.py RiskLevel 6 mức |
| G2 R4 fail-closed | PASS | verify("FAKE-CARD-XYZ") → **False** (contract bool, doc "Trả về True CHỈ khi toàn bộ chuỗi bằng chứng khớp") |

### H. Learning Effectiveness — 1/2 PASS
| Probe | Kết quả | Bằng chứng |
|---|---|---|
| H1 Quarantine gate (không tự promote) | PASS | promoted=3.209 (đều qua R4), quarantined=6.267 chờ owner |
| H2 Kiểm soát spam học | **FAIL** | 1.837 rows "Test suite:*" trong quarantine (tăng từ 1.494 lúc 22h — **còn nạp tiếp**) |

---

## TASK 3 — ĐIỂM YẾU THỰC SỰ (xếp hạng theo bằng chứng)

1. **[NGHIÊM TRỌNG] Retrieval mù kho lớn** (C2+D1): reasoning trả "không đủ bằng chứng" cho câu hỏi nằm trong kho. 2/2 probe FAIL cùng gốc. → Sửa đầu tiên ở Phase A/B (đã ghi gap #1 Cognitive).
2. **[NGHIÊM TRỌNG] ConflictDetector dead-code** (B2): không phát hiện được mâu thuẫn trên production DB — năng lực "có code nhưng KHÔNG hoạt động" đúng định nghĩa bug im lặng (pattern skill: bare-except làm feature chết từ đầu).
3. **[CAO] Spam học chưa chặn ở write path** (H2): 1.494 → 1.837 rows trong ~2 giờ phiên này (~170/giờ với dual daemon).
4. **[TRUNG BÌNH] Causal guard chưa có** (B3) — correlation ≠ causation chưa được kiểm soát tự động.
5. **[TRUNG BÌNH] Hypothesis generation phụ thuộc retrieval** (D1) — không sinh giả thuyết khi thiếu data: đúng về fail-honest, sai về usefulness → sau khi sửa retrieval cần re-probe.

## Điểm mạnh xác nhận (không tô hồng)
- Abstention chuẩn xác và NHANH (0.01s) — biết nói "chưa đủ dữ liệu".
- Governance R4 thật sự fail-closed — fake card bị từ chối.
- Anti-circular evidence rule có thật trong code V9.
- Stale detection theo policy từng claim (không ngưỡng chung — đúng yêu cầu §IV).

## Giới hạn của baseline này
- 14 probes là PHỎNG ĐỘNG đầu tay, chưa phải CPSL chuẩn (dataset 5 nhóm + hidden tests ở Phase B).
- Chưa đo False Confidence Rate / Calibration Error (cần confidence_calibrator — Phase C).
- Chưa đo trên LLM pipeline thật (chỉ đo lớp deterministic V9) — nhóm Probes LLM cần budget riêng.
- Pi5 offline → nhóm bài toán System Troubleshooting edge-case chỉ đo được phía PC.

---
*Evidence: _probe_results_task2.json (14 entries, chạy 11/11 ~22:40, tool output nguyên vẹn trong phiên).*
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

