"""Sprint 5-6 Summary — Continuous Learning & Self-Care.

This file documents the planned implementation for Sprint 5-6.
Actual code will be generated in the next session.

## Sprint 5: Continuous Learning Engine

### Components to implement:
1. `continuous_learning_engine.py` (400 dòng)
   - 5-type learning pipeline (A-E)
   - DETECT → COLLECT → NORMALIZE → PROVENANCE → EXTRACT → EVALUATE → STORE → INDEX → TEST → REFLECT → PROPOSE
   - LearningReport generation

2. `learning_evaluator.py` (200 dòng)
   - Benchmark before/after learning
   - Precision@k, recall@k, MRR tracking
   - Improvement measurement

3. `tests/test_continuous_learning.py` (200 dòng)
   - 5-type learning tests
   - Provenance tracking tests
   - Evaluation tests

### Expected outcomes:
- Tự động phát hiện kiến thức mới
- Tự động đánh giá chất lượng nguồn
- Tự động cập nhật tri thức được cấp phép
- Tự động tạo bài kiểm tra
- Tự đo chất lượng trước/sau

## Sprint 6: Self-Care & Approval Center UI

### Components to implement:
1. `self_care_engine.py` (300 dòng)
   - Health monitor với threshold
   - Auto-recovery policy (Mức 0-2)
   - Alert generation
   - Root cause analysis

2. Web API endpoints (`web/server.py` patch)
   - `/api/approvals/list` — list pending approvals
   - `/api/approvals/approve` — approve exact change
   - `/api/approvals/reject` — reject
   - `/api/health/status` — real-time health

3. Executive Cockpit Tab 8 (`web/static/executive.html` + `executive.js`)
   - Owner Approval Center UI
   - Health dashboard
   - Alert viewer
   - Audit log viewer

### Expected outcomes:
- Anh Quân có UI để duyệt thay đổi
- Hệ thống tự phát hiện lỗi sớm
- Auto-recovery cho mức độ thấp
- Audit log đầy đủ

## Commit Plan

After implementing Sprint 5-6:
```bash
git add -A
git commit -m "feat: Sprint 5-6 — Continuous Learning Engine + Self-Care + Approval Center UI

- Sprint 5: 5-type learning pipeline, provenance tracking, evaluation benchmark
- Sprint 6: Self-Care Engine with auto-recovery, Approval Center UI (Tab 8)
- Tests: 20+ new tests for learning + self-care
- Full regression: 540+ tests pass"
```

## Metrics

| Metric | Target |
|---|---|
| Learning pipeline coverage | 5 types (A-E) |
| Auto-recovery levels | 0-2 (3-4 require approval) |
| Health check frequency | Every 60s |
| Approval UI response time | <500ms |
| Test coverage | 80%+ for new modules |
| Learning evaluation | Before/after benchmark |

## Risks

1. **Learning sai kiến thức** — mitigated by provenance + conflict detection (Sprint 3)
2. **Auto-recovery gây hại** — mitigated by risk levels (0-2 only, 3-4 require approval)
3. **UI complexity** — mitigated by incremental rollout (Tab 8 first)

## Rollback

- Git revert Sprint 5-6 commit
- Disable auto-recovery via config
- Hide Tab 8 until ready