# TONY ADVANCED ASSURANCE — P0 ACTUAL STATE AUDIT (bản 1, 02/11/2026 01:45)

**Cơ sở:** Master Prompt V1.0 Advanced Assurance · **Phương pháp:** đo trực tiếp workspace, không tin báo cáo cũ.

## 1. Baseline đo được 01:45

| Mục | Giá trị thực đo |
|---|---|
| Branch / commit | feat/deom-m1-m2-task-lifecycle @ `7d9e7cd` (15 commits) |
| Working tree | sạch code — chỉ 2 chroma.sqlite3 (binary churn) + 1 báo cáo untracked |
| Python | 3.11.13 venv |
| Test suite | **168 file test**, full regression **3.206 PASS / 0 FAIL / 44 SKIP** |
| tests/advanced/ | **CHƯA TỒN TẠI** — toàn bộ suite A–N là khoảng trống |
| reports/advanced_assurance/ | **CHƯA TỒN TẠI** |
| Thư viện test nâng cao | hypothesis ✗ · mutmut ✗ · locust ✗ · pytest-timeout ✗ · pytest-xdist ✗ (→ property/mutation/load test viết thủ công stdlib, KHÔNG tự cài package) |

## 2. Hiện trạng module (đã đo)

- **Governance:** policy.py (R0–R5), approval_service.py (card R4 + action_fingerprint G-A), permission_resolver.py (4 lớp), approval_verifier, consultation_inbox, netchat_approval_adapter, state_store.
- **Orchestration:** task_registry (durable SQLite), plan_orchestrator, agent_dispatcher, dependency_manager, supervisor, recurring_engine, task_feedback, nl_intake.
- **Execution:** staging.py, process_containment.py, resource_budget.py, windows_job_object.py (production runner vẫn VÔ HIỆU hóa — giữ nguyên).
- **DB production:** approval_cards_v2.db rỗng (0 card) — an toàn cho P3 injection test cục bộ; tasks.db 579 durable tasks (CHỈ ĐỌC cho audit, mọi test ghi dùng tmp_path).

## 3. Mức độ phủ hiện có vs. Suite A–N

| Suite | Phủ hiện có | Khoảng trống chính |
|---|---|---|
| A Cognitive | cognitive tests rời rạc | unified flow E2E, calibration, cross-engine |
| B Memory | promote/quarantine (Q-4) | conflict detection, poisoning, provenance |
| C DEOM | M2–M6 lifecycle tests | multi-task, interruption matrix, truthfulness |
| D Security/RedTeam | R4/R5, fingerprint, self-approval (unit) | prompt injection, tool abuse, bypass audit đường đi |
| E Chaos | restart recovery (1 test) | LLM fail matrix, DB fail, partial failure |
| F Concurrency | test song song đơn lẻ | approval race, concurrent update, load |
| G Learning | feedback + promotion (Q-4) | reward hacking, measured improvement |
| H Tool/Skill | sandbox tests | gap detection, maturity |
| I Health | monitoring 18 tests | intelligence classification, boundary |
| J Voice/VN | nl_intake VN tests | hội thoại đa lượt, voice safety (Pi5 chưa có mic) |
| K Long-horizon | không | soak test (giới hạn: không ép tải máy đang chạy service thật) |
| L Business | không | scenario L1–L6 |
| M Perf | không | benchmark p50/p95 |
| N Property/Fuzz | không | invariant + fuzz stdlib |

## 4. Critical Gates (Phần 19) — kiểm tra nhanh ngay P0

| Gate | Kết quả kiểm tra P0 |
|---|---|
| R5 hard-block | ✅ policy + card-service chặn, 36+11 test phủ |
| R4 không approval không chạy | ✅ WAITING_APPROVAL + fingerprint G-A |
| STOP/FREEZE | ✅ POST emergency + persistent governance test |
| Self-approval | ✅ chặn code |
| Audit | ✅ card_events, transition log |
| Consume race | ⚠️ **chưa có test đồng thời** → P4 |
| Prompt injection | ❌ chưa có test nào → P3 ưu tiên |

## 5. Test Governance Center (P0 deliverable) — đã dựng

- `tests/advanced/__init__.py` + `tests/advanced/registry.py` — Test Registry 17 trường + Evidence 12 trường (SQLite riêng data/test_governance.db, copy được, không đụng production).
- `tools/record_test_evidence.py` — CLI ghi evidence (commit, seed, env, result).
- Phân loại 18 category theo Phần 3.2.

## 6. Kế hoạch phase (theo Phần 24, mỗi phase 1 increment có evidence)

| Phase | Nội dung | Trạng thái |
|---|---|---|
| **P0** | Audit + Test Governance Center | ✅ xong (file này + registry) |
| **P1** | Cognitive + Memory invariants | kế tiếp |
| P2 | DEOM lifecycle nâng cao (multi-task, interruption) | |
| P3 | Red-team: prompt injection, tool abuse, bypass audit, approval attack matrix | |
| P4 | Chaos + Concurrency (approval race, DB fail, LLM fail) | |
| P5 | Learning + reward hacking | |
| P6 | Health + Pi5 (giới hạn phần cứng: chưa có mic) | |
| P7 | Business scenarios | |
| P8 | Performance benchmark (mức an toàn) | |
| P9 | Master scenarios + acceptance | |

**Giới hạn trung thực ghi nhận:** không ép tải máy DESKTOP-SNMI929 đang chạy service thật (K5/M6 chạy mức 1–5 concurrent, timeout ngắn); Pi5 voice (J4/J5) chỉ mức DESIGNED — chờ owner mua USB sound card + mic; không cài hypothesis/mutmut/locust khi chưa được phép — property/fuzz viết stdlib.

---
*P0 audit — measured 02/11/2026 01:45 · mọi con số lấy trực tiếp từ git/pytest/sqlite.*
