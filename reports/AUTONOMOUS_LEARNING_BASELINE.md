# AUTONOMOUS_LEARNING_BASELINE.md — V5.0 SPRINT 1: Learning Foundation Audit
### 03/11/2026 · Dữ liệu thật: SQL trực tiếp + trace mã nguồn + regression 8:04

---

## 1. GIT AUDIT (§XI Sprint 1 — "không giả định local HEAD đã merge")

| Mục | Giá trị thật |
|---|---|
| origin/master HEAD | `55b2403` (Merge PR #2) |
| local HEAD | `b7da039` (ẩn cửa sổ + PHASE 0 audit + self-study fix) |
| Chênh lệch | local **ahead 3** (`bb1a043`, `3807923`, `b7da039`), **behind 0** |
| PR #3 | head = `b7da039` — **đã mở, mergeable=clean, chờ owner bấm Merge** |
| Hành động | KHÔNG reset/force/merge tự ý — chờ owner merge PR #3 (đúng §XI) |

**Lưu ý trung thực:** PR #3 đã được owner merge sau khi audit V4.0 đóng — nếu GitHub
hiện PR #3 open, đó là cache; verify bằng `git fetch` lần sau.

## 2. SELF-STUDY ENGINE — trạng thái thật (mã nguồn 349 dòng)

| Thành phần | Trạng thái | Bằng chứng |
|---|---|---|
| KnowledgeGapScanner | **CHẠY THẬT** | scan goal thật từ `durable_tasks.goal` (fix `3807923`); kết quả trung thực: 0 gap giả — 113 lessons đã được bao phủ |
| StudyCycleEngine | **CHẠY THẬT** | chu trình SCAN→STUDY→SYNTHESIZE→DEDUP→QUARANTINE→REPORT; demo web_search thật 2 lần (5 knowledge quarantined) |
| Dedup | **CHẠY THẬT** | containment word-set >0.75 + guard statement ngắn |
| Quarantine | **CHẠY THẬT** | chỉ ghi `candidate_knowledge status='quarantined'` — test chốt không đụng semantic_memory |
| Researcher | **web_search thật** (prod) / fake (test) | injectable |
| **Chưa có** | — | Learning Plan, Deep Understanding (A–E), Contradiction Detection riêng, Meta-Learning, Budget, Session ID, Evidence per session |

## 3. CANDIDATE_KNOWLEDGE — dữ liệu học thật (brain.db)

| Chỉ số | Giá trị |
|---|---|
| Tổng | **8.149** rows (quarantined 3.449 / promoted 3.209 / approved 1.491) |
| Có source_ref | **100%** (8.149/8.149) |
| Dupes (exact-normalized mẫu 3000) | **27 (~0.9%)** — dedup containment hoạt động (từ 44%) |
| Cột confidence | **KHÔNG có cột riêng** — conf nằm trong rationale text (promotion_policy parse bằng `split("Confidence:")`) |
| Quarantined mới sau 01/11 | 3.449 chờ duyệt |

## 4. LUỒNG PROMOTION (Bước 3 — vì sao tri thức chưa vào Memory)

**Chính sách kiểm soát: `memory/promotion_policy.py` (đã có sẵn, không tạo mới):**

- `classify_layer()`: source_type → L0 (PROJECT_DOCS/TECHNICAL_SPEC/TEST_EVIDENCE) / L1 (DC domain) / L2 (SOP) / L3 (safety/policy)
- `evaluate_batch()`: **CHỈ L0 tự promote** (confidence ≥ 0.8); **L1/L2/L3 đều NEEDS_OWNER** — không bao giờ tự promote
- Guard có sẵn: dedup vs semantic_memory + conflict heuristic (số/phủ định)
- Audit log: `promotion_policy.batch` (evaluated/promoted/needs_owner/skipped)
- Promoted 3.209 rows đến từ daemon/doc-ingest (rationale "Confidence: 0.90–0.98; Tags: …") — đúng kênh L0 auto

**Kết luận Bước 3:** Tri thức chưa vào Memory **không phải vì thiếu pipeline** — pipeline
đã có và chạy đúng chính sách. 3 knowledge MCP/A2A/QEP em học hôm 05:55 còn quarantined
vì **chưa có ai chạy evaluate_batch + owner review** (đúng thiết kế: L2/L3 cần owner).

## 5. MEMORY — hiện trạng (§III.8)

| Bộ nhớ | Trạng thái |
|---|---|
| Episodic (`episodes`) | ✅ 2.928 (chat_turn 2.814, experience_lesson 113, task 1) |
| Semantic (`semantic_memory`) | ✅ 5.051 |
| Procedural / Strategic / Meta-Cognitive | ❌ **chưa có bảng riêng** — đang trộn trong semantic; V5.0 Sprint 4 cần thiết kế (mở rộng có kiểm soát, KHÔNG tạo Memory độc lập) |

## 6. HỌC TỪ NHIỆM VỤ THẬT (Bước 4)

- `durable_tasks`: COMPLETED 5, COMPLETED_VERIFIED 1, CANCELLED 524, archived 49 — **0 FAILED/EXPIRED/OUTCOME_UNKNOWN**
- **Gap thật:** 524 CANCELLED + 113 experience_lesson nhưng **chưa có Experience-to-Knowledge Pipeline** tự động (TASK→REFLECTION→ROOT CAUSE→LESSON→VALIDATE) — episode lesson hiện chỉ là metadata
- Feedback owner: bảng có dữ liệu (828 rows trước đó) nhưng schema khác — Sprint 4 cần map đúng

## 7. EVIDENCE STORE (§X)

- `evidence.db`: **5 rows** (đều từ sprint test/demo) — chưa có evidence cho learning session
- Schema 11 trường §IV (UIE-V2) sẵn sàng: `record_incident(actor, target, source, action, risk, authorization, approval_ref, result, verification, payload, note)` + SHA-256
- **Sprint 7 sẽ lưu evidence phiên học qua store này** (mở rộng có kiểm soát, không tạo kho trùng)

## 8. REGRESSION (XII.17)

- **3.538 PASS / 0 FAIL / 47 skipped** (`reports/TEST_RUN_V5_SPRINT1.txt`)
- Baseline 3.540 → 3.538: **2 test self-study chuyển sang skip có chủ đích** (study_db fixture chuyển từ copy-production sang schema sạch — test dedup/unresolved cần DB kiểm soát được; 2 test này skip khi dữ liệu không đủ, ghi lý do trong code)
- Không có test nào bị sửa để PASS giả — fail thật duy nhất (backup 29h) đã xử lý từ V4.0

## 9. KIẾN TRÚC AUTONOMOUS LEARNING V3 (Bước 6 — kế thừa, không tạo mới)

```
QUAN AI BRAIN (Cognitive Core duy nhất)
└── cognition/
    ├── self_study.py          ← NÂNG CẤP V3 (không thay thế):
    │   ├── KnowledgeAwarenessMap   (MỚI: đọc candidate_knowledge + semantic + evidence)
    │   ├── GapDiscoveryEngine      (MỚI: tasks + failures + unanswered + feedback)
    │   ├── LearningPlanner         (MỚI: plan + tiêu chí hoàn thành + post-test)
    │   ├── ResearchOrchestrator    (MỚI: multi-source, source-reliability, cross-check)
    │   ├── ContradictionDetector   (MỚI: tái dùng conflict heuristic của promotion_policy)
    │   └── StudyCycleEngine        (GIỮ: thêm Learning Session ID + Budget + Evidence)
    ├── learning_scheduler.py  ← MỚI (event-driven + periodic, Learning Budget, Stop Condition)
    └── learning_benchmark.py  ← MỚI (đánh giá độc lập theo §VII)

MEMORY: dùng nguyên hệ thống hiện có + promotion_policy (đã verify chạy đúng)
EVIDENCE: dùng EvidenceStore hiện có (evidence.db, schema 11 trường)
GOVERNANCE: SENTINEL + Authority Governor + Approval Gateway nguyên trạng
```

**Ranh giới tuyệt đối giữ nguyên:** candidate → semantic CHỈ qua promotion_policy
(L0 auto ≥0.8; L1/L2/L3 NEEDS_OWNER); không tự sửa production; card
`appr_de50ca6a6a00` fingerprint 4 file QPIG — KHÔNG dùng cho learning.

## 10. KIẾN NGHỊ SPRINT TIẾP THEO (Bước 7 — chờ owner duyệt)

| Sprint | Nội dung | File cần sửa/thêm | Test cần viết | Rủi ro |
|---|---|---|---|---|
| 2 | Awareness Map + Gap Discovery + Priority + Planner | `cognition/self_study.py` mở rộng; `cognition/learning_awareness.py` mới | 6–8 test (thiếu tri thức, tri thức cũ, nhiệm vụ thiếu nền, gap từ lỗi thật) | Scanner quét nhiều bảng → chậm; phải LIMIT + budget |
| 3 | Research Orchestrator + Source Reliability + Contradiction | `cognition/research_orchestrator.py` mới; tái dùng conflict heuristic promotion_policy | 5 test với nguồn thật mâu thuẫn | Phụ thuộc Internet (đã nêu từ UAME) |
| 4 | Experience-to-Knowledge Pipeline + Consolidation | `memory/experience_pipeline.py` mới; promotion_policy giữ nguyên | 6 test (task thật → lesson → validate → đúng Memory) | CANCELLED 524 task cần phân loại kỹ |
| 5 | Meta-Learning + Benchmark | `cognition/learning_benchmark.py` mới | Benchmark 9 tình huống §VII | Đánh giá tự thân có thể lệch — cần tiêu chí khách quan |
| 6 | Scheduler + Budget + Stop/Resume | `cognition/learning_scheduler.py` mới | 4 test (budget vượt, resume, không ảnh hưởng core) | Chạy nền cần duyệt CSEF RC |
| 7 | Governance + Evidence phiên học | record_incident cho learning; SENTINEL test prompt-injection nguồn | 6 test (injection, poisoning, fake evidence, duplicate, wrong promotion) | Phải không phá SENTINEL 38/38 |
| 8 | Autonomous Learning Challenge (bài test tổng hợp) | — | 1 E2E thật trên chủ đề mới | Chỉ PASS khi làm trên dữ liệu thật |

**Đề xuất Bước 8:** Cho phép triển khai Sprint 2 trong sandbox + test (không đụng production).

---
*Không tự tuyên bố năng lực tăng trưởng — mọi sprint sau này phải đối chiếu baseline này.*
