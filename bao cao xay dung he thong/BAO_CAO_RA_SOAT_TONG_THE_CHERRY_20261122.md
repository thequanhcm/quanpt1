# BÁO CÁO RÀ SOÁT TỔNG THỂ CHERRY — KẾ HOẠCH PHÂN TÍCH / NÂNG CAO / KHẮC PHỤC

| Trường | Giá trị |
|---|---|
| Ngày | 21/11/2026 12:34 ICT (session 22/11 sau midnight) |
| Loại | Audit-first baseline + roadmap (theo pattern V31 §A) |
| Workspace | `E:\BRAIN` (máy QUANPT) |
| Head commit | `084d218` trên nhánh `feat/v6-m6-memory-truth` |
| Tác giả | TONY (sau khi rà soát runtime + đọc PROJECT_STATUS.md) |
| Phương pháp | Read-only — KHÔNG đụng code; chỉ quan sát + probe endpoint thật |
| Báo cáo gần nhất | `BAO_CAO_V6_M6_MEMORY_TRUTH_20261118.md` (3 ngày trước) |

---

## PHẦN I — HIỆN TRẠNG CHERRY (bức chân dung 1 lần nhìn)

### 1.1. Quy mô codebase (đo trực tiếp)

| Hạng mục | Số |
|---|---|
| Python modules trong `src/quan_ai_brain/` | **167 file .py** (≈ 60K LOC) |
| Packages | 26 (`cognition/`, `memory/`, `voice/`, `orchestration/`, `ai/`, `analytics/`, ...) |
| Cộng sinh thái | `os_kernel`, `SKILL_BAT_AI`, `BATTERY_AI_V4`, `DC-COMMAND`, BOT projects (preserve read-only) |
| Test suite | `tests/` — pytest đang chạy nền (PID 20256/19176, ~5–8 phút) — báo cáo số pass/fail sẽ cập nhật |
| DB hiện hành | brain.db 19.4 MB · tasks.db 11.9 MB · governance.db 660 KB · learning_checkpoints.db 41 KB · vector_db_semantic 0 B ⚠️ |
| Audit log | `logs/audit.jsonl` — **12.304 events** |

### 1.2. Pipeline phản hồi chính (đo thật qua HTTP probe 12:33)

```
[User] → POST /api/chat → 7 bước trong server.py:
  1. Session lookup (session_memory.py)
  2. Memory recall (memory_recall.py: keyword LIKE search)
  3. Self-RAG grader P1 (cognition/self_check.py — chấm ý căn cứ)
  4. Context builder (cognition/context_builder.py: system_prompt)
  5. LLM call (llm/router.py → NetMind GLM-5.3-Flash, fallback Ollama local)
  6. Response shaping + autoload memories
  7. Mouth timeline (voice/mouth_sync.py: 85 frames @50ms = 3.81s)
[Kiosk] ← HTTP /api/kiosk/control ← Cherry avatar + mouth-timeline render
```

| Probe | Response | Trạng thái |
|---|---|---|
| `POST /api/chat` greeting | 6.3s, dùng 3 memories | ✅ LIVE |
| `POST /api/chat` suy luận 1+1 | 4.4s, 4 memories | ✅ LIVE |
| `POST /api/chat` "Cherry nhớ tên anh?" | 7.5s, fail-honest "không có thông tin" | ✅ P1 Self-RAG hoạt động đúng (không bịa) |
| `POST /api/voice/interact` | mouth_timeline 85 frames, audio null | ⚠️ TTS background mode (không có audio_base64) |
| `POST /api/memory/semantic/search` (q="trí nhớ ngữ nghĩa") | 0 hits | ❌ **BUG** — query parse trống |
| `GET /api/autonomic/status` | health 35/100, overall_pain CRITICAL | ⚠️ 5 pains đang mở |
| `GET /api/executive/supervisor` | edge DISCONNECTED, alert ALERT_A_PI5_NOT_CONNECTED | ⚠️ Pi5 chưa pair |

### 1.3. 12 Capability × 4 trạng thái (nó là gì, thực tế ra sao)

| # | Capability | Trạng thái công bố | Bằng chứng runtime | Đánh giá thật |
|---|---|---|---|---|
| 1 | `long_term_memory` | VERIFIED_ACTIVE | brain.db 2.594 approved + 357 quarantined | ✅ THẬT |
| 2 | `local_llm_inference` | VERIFIED_ACTIVE | GLM-5.3-Flash OK, Ollama OFF | ✅ THẬT (NetMind), Ollama chỉ bật offline |
| 3 | `safe_task_planning` | VERIFIED_ACTIVE | supervisor current_task COMPLETED_VERIFIED | ✅ THẬT (DAG + R0-R5) |
| 4 | `tool_sandbox` | VERIFIED_ACTIVE | chưa probe trực tiếp | ✅ CODE |
| 5 | `self_learning_v1` | VERIFIED_ACTIVE | clo_sessions 24, last RUNNING 75h | ⚠️ **KẸT** (stalled do Q-4 chưa duyệt) |
| 6 | `web_ui_voice` | VERIFIED_ACTIVE | 8765/8766 OK | ✅ THẬT |
| 7 | `os_job_containment` | INERT_STAGING | chờ SPRINT6_DESIGN_SIGNOFF.md | ❌ STAGED |
| 8 | `ecosystem_adapters` | EXTERNAL_PLANNED | DC-COMMAND/Kernel L3/Battery AI preserve | ❌ PLANNED |
| 9 | `universal_software_integration` | VERIFIED_ACTIVE | bounded A0-A3, 20 acceptance tests | ✅ THẬT |
| 10 | `edge_embodiment_pi5` | VERIFIED_ACTIVE | edge DISCONNECTED, 1 alert mở | ⚠️ **CODE sẵn, hardware OFFLINE** |
| 11 | `netchat_dm_channel` | VERIFIED_ACTIVE | 2 pythonw đang chạy là AGENT_X_PRO, không phải Cherry | ⚠️ KHÔNG xác minh được |
| 12 | `speech_learning_quarantine` | IMPLEMENTED_UNTESTED | 516 quarantined, chưa wire | ❌ QUARANTINED |

### 1.4. Cơ sở dữ liệu & dữ liệu người dùng

- **2.594** knowledge approved + **357** quarantined = 2.951 record tổng; được viết bởi 12K+ chat episodes (audit log ghi sống)
- **150** Knowledge Units (deep memory) + 210 relations (REFINES, RELATED_TO, SUPERSEDES) — schema đẹp nhưng `last_review_run` 27/10/2026 (đã 25 ngày không review — flag mục 5.2)
- **50** durable tasks: 1 VERIFIED + 2 COMPLETED + **47 CANCELLED** (tỉ lệ hủy cao — phân tích mục 5.3)
- **0** pending owner decisions, **0** pending approval cards

### 1.5. Avatar + Pi5 (state of embodiment)

- **Avatar v3** (portrait Cherry) chạy ổn định trên PC harness v9.3 (head 8 hướng + smooth miệng + seam clean). Engine `7dd792fb` nguyên vẹn. **Tạm bỏ v4 (owner từ chối 20/11)**
- **Motion library**: V8→V9.2 sprint soft-smooth (jerk 0.83→0.82, autocorr 0.30→0.32, dark-ratio miệng 0.02→0.033), V9.3 head 8 hướng (biên ±5.2°/±3.2°/±1.6° cosine ease)
- **Pi5**: ping OK, kiosk offline, chưa pair với supervisor. Lip-sync frames engine chưa được port vào Pi5 (chỉ chạy trên PC harness)
- **Wake word "Cherry ơi"**: config registered, `enabled=False` (cần owner bật thật trên Pi5)

---

## PHẦN II — PHÂN TÍCH HỆ THỐNG (read-only, không sửa)

### 2.1. Phân loại module theo mức độ "sống thật"

**Tier S (chạy thật, đo được)**: cognition/ → memory_recall.py, context_builder.py, self_check.py, capability_registry.py | memory/ → memory_service.py, deep_memory.py, semantic_memory.py | llm/ → router.py, netmind_provider.py | voice/ → mouth_sync.py, tts_interface.py | web/server.py (route 150+ endpoints)

**Tier A (code sẵn, kích hoạt được nhưng chưa wire đầy đủ)**: cognition/ → autonomous_mind.py, executive_persona.py, cognitive_loop.py, self_study.py | orchestration/ → supervisor.py, plan_orchestrator.py | ai/ → 7 module (common_sense, neural_symbolic, explainable_ai...)

**Tier B (đã code, nhưng gated chờ sign-off / phụ thuộc)**: execution/ → windows_job_object.py, process_containment.py | ai/transfer_learning.py | scaling/, business_intelligence.py

**Tier C (file tồn tại nhưng không có tín hiệu chạy trong 30 ngày)**: analytics/ (8 module — chưa thấy ingest metrics vào report), creativity/ (idea_generator, innovation_engine — không có trigger), decision/ (decision_engine — chỉ chạy qua plan_orchestrator), intelligence/ (chỉ 1 file kpi_store)

### 2.2. Ba "nút thắt cổ chai" hiện tại (analysis-by-evidence)

#### Nút 1 — `vector_db_semantic/` size = 0 byte
- **Triệu chứng**: `/api/memory/semantic/stats` trả `n_count` nhưng ls filesystem thấy dir rỗng
- **Nguyên nhân có thể**: ChromaDB persist ngoài workspace (vd `~/AppData`) nhưng config path trỏ `E:\BRAIN\data\vector_db_semantic`; hoặc layer bị evict
- **Hệ quả**: semantic search fail → fallback hybrid keyword LIKE → recall@3 có thể tụt
- **Cách xác minh**: probe `/api/memory/semantic/stats` đã thấy `n_count` = ?, filesystem `ls -la data/vector_db_semantic` cần chạy

#### Nút 2 — `clo_last_session` RUNNING 75h (stalled)
- **Triệu chứng**: learning_checkpoints.db ghi session #24 status RUNNING, started_at 19/11 12:51, hiện đã 75 giờ (3 ngày)
- **Health monitor** đã cảnh báo WARNING "tự chủ học kẹt do Q-4 chưa duyệt"
- **Nguyên nhân**: tự học chờ approval queue (bài học M6 self-study quarantine) — không có chủ nhân → session treo
- **Hệ quả**: 357 quarantined lessons không được xét → cơ chế tự cải thiện đứng

#### Nút 3 — `tasks.db` 47/50 CANCELLED (94% cancelled)
- **Triệu chứng**: work-queue 0, current_task VERIFIED xong; 47 record bị hủy
- **Nguyên nhân có thể**: (a) chủ nhân hủy khi nhận ra quá nhiều auto-task; (b) plan_orchestrator tạo task con nhưng agent_dispatcher không có consumer
- **Cần điều tra thêm**: lấy mẫu 5 record CANCELLED xem lý do hủy (reason field)

### 2.3. Mapping "công bố" ↔ "chạy thật"

| Capability công bố | Bằng chứng runtime | Khoảng cách |
|---|---|---|
| edge_embodiment_pi5 "verified" | Pi5 chưa pair, alert mở | ❌ "verified" chỉ là CODE verified, hardware chưa |
| netchat_dm_channel "verified 476 tin" | không tìm thấy process cherry_netchat; 2 pythonw là AGENT_X_PRO | ⚠️ khó xác minh từ máy local |
| web_ui_voice "served locally" | 8765/8766 OK, giao diện tải được | ✅ đúng |
| self_learning_v1 "24 sessions" | 24 sessions nhưng 1 bị stalled 75h | ⚠️ đếm thật nhưng không đảm bảo health |

### 2.4. Failure mode catalog

| Mã lỗi / triệu chứng | Khi nào xuất hiện | Đã có mitigation chưa |
|---|---|---|
| LLM NetMind timeout (timeout 30s) | câu dài >1000 token | retry 1 lần + fallback Ollama (OFF) |
| Memory search miss | semantic dir rỗng | fallback LIKE keyword |
| Self-RAG grader fail | grader GLM trả JSON invalid | fail-open (giữ nguyên câu gốc) |
| Audio capture fail Pi5 | DRM all-disconnected | log-only, không retry |
| Approval queue dài | owner không duyệt | warn sau 24h, stall sau 72h |

---

## PHẦN III — KẾ HOẠCH PHÂN TÍCH HỆ THỐNG (Analysis Roadmap)

### 3.1. Sprint A7: AUDIT V31-EXTENDED (1 tuần)
**Mục tiêu**: 3 audit độc lập thay vì 1 audit-first; tạo `AUDIT_V31_BASELINE.json` + `AUDIT_EXECUTIVE_SUMMARY.md`

| Item | Output | Effort |
|---|---|---|
| A7.1 | Audit DB sâu: schema validation + index health + orphaned rows | 0.5d |
| A7.2 | Audit test pass-rate thật (đợi pytest nền xong) + gap matrix | 0.5d |
| A7.3 | Audit module Tier B/C: mỗi module có __call__? Có trigger? Có consumer? | 1d |
| A7.4 | Audit pipeline end-to-end: 20 câu hỏi mẫu đi qua toàn bộ 7 bước chat | 0.5d |
| A7.5 | Audit security: vault `E:\BRAIN\user, pass, token` × audit_secrets.py | 0.5d |
| A7.6 | Audit pi5-edge readiness: ping + SSH + kiosk + wake word config | 0.5d |

**Card**: `TASK-AUDIT-V31-EXTENDED`, approval trước khi chạy.

### 3.2. Sprint A8: OBSERVABILITY (2 tuần)
**Mục tiêu**: nhìn thấy Cherry đang làm gì trong production, không chỉ trong test

| Item | Output |
|---|---|
| A8.1 | Metrics dashboard (`/api/metrics/overview`) — p95 latency, success rate, queue depth |
| A8.2 | Trace ID xuyên suốt: 1 request chat → memory → LLM → kiosk, ghép lại trong 1 ID |
| A8.3 | Memory write log: ai viết gì vào brain.db lúc nào (table `memory_writes` + writer agent) |
| A8.4 | Task lifecycle audit: tại sao 47/50 bị cancel (dashboard query) |
| A8.5 | Owner-visible health report cuối ngày (`/api/health/daily?date=...`) |

### 3.3. Sprint A9: DEPENDENCY HEALTH (1 tuần)
| Item | Output |
|---|---|
| A9.1 | ChromaDB persist health probe (giải quyết nút 1) |
| A9.2 | Ollama fallback test (giả lập NetMind offline, verify chain) |
| A9.3 | Pi5 connection state machine: DISCONNECTED → PAIRING → CONNECTED → DEGRADED → LOST |
| A9.4 | Memory review cycle tự chạy (25 ngày chưa review) |

---

## PHẦN IV — KẾ HOẠCH NÂNG CAO HỆ THỐNG (Enhancement Roadmap)

### 4.1. Tầng nhận thức (Cognition) — Sprint C-serie

| Sprint | Cải tiến | Bằng chứng cần đạt |
|---|---|---|
| **C1** | Self-RAG grader nâng cấp: hỗ trợ tiếng Việt + repair không chỉ xóa mà có thể paraphrase dựa trên evidence | recall@3 ≥0.95, latency ≤500ms |
| **C2** | Causal engine thật (hiện đang là lookup table): tích hợp vào `/api/chat` để trả lời câu nhân quả | 8/8 câu causal test PASS |
| **C3** | Executive_persona nhớ phong cách viết: học từ chính 12K episodes (few-shot in-context) | conversation BLEU ≥0.7 vs corpus owner |
| **C4** | Mind/cogitate kết nối `thinking`: hiện `total_thoughts=0` chưa chạy | 50+ thoughts/day, quality ≥0.6 |

### 4.2. Tầng trí nhớ (Memory) — Sprint M-serie

| Sprint | Cải tiến | Bằng chứng |
|---|---|---|
| **M1** | ChromaDB persist đúng chỗ + auto-recovery (nút 1) | dir size > 0, search hit ≥1 |
| **M2** | Memory consolidation thật: lessons quarantined → approved tự động nếu rule owner đặt | 100 lessons/cycle, false-positive ≤5% |
| **M3** | Memory timeline visual: timeline của 1 owner (ngày nào hỏi gì, học gì) | dashboard route `/api/memory/timeline` |
| **M4** | Deep memory đào sâu: chuyển 2.594 flat knowledge → ontology (concept graph) | 500 concepts + 2K edges |

### 4.3. Tầng hành động (Execution) — Sprint E-serie

| Sprint | Cải tiến | Bằng chứng |
|---|---|---|
| **E1** | Universal Software Integration wire thật: PowerShell automation cho Word/Excel (hiện 20 test PASS, nhưng chưa chạy trên máy owner) | 5 task thực tế qua PSI |
| **E2** | Tool sandbox có rate-limit + audit (mỗi tool call ghi log) | audit_events += tool_call records |
| **E3** | Email intake tự động + proposal (hiện có code, chưa thấy intake thật) | 1 email intake/ngày thật |

### 4.4. Tầng hình thể (Embodiment) — Sprint H-serie

| Sprint | Cải tiến | Bằng chứng |
|---|---|---|
| **H1** | Port V9.3 motion config lên Pi5 kiosk (engine vẫn 7dd792fb, harness Pi5 sync) | 5 motion delta trên Pi5, FPS ≥18 |
| **H2** | Camera IMX708 + face-recognition: "Cherry chào anh khi anh vào phòng" | 5 lần detect đúng owner/ngày |
| **H3** | Wake word "Cherry ơi" chạy thật trên Pi5 (Vosk matcher) | false-positive ≤1/giờ |
| **H4** | 2 chiều lip-sync thật: Pi5 send mouth timeline, PC nhận via `/api/executive/edge/mouth-sync` | RTT <300ms |

### 4.5. Tầng tự học (Self-learning) — Sprint L-serie

| Sprint | Cải tiến | Bằng chứng |
|---|---|---|
| **L1** | Fix clo_session stalled 75h (nút 2) | session chuyển COMPLETED trong 1h sau fix |
| **L2** | Auto-promote quarantined → approved nếu ≥3 lần owner không reject | false-positive ≤2% |
| **L3** | A/B testing cho knowledge mới: 50/50 random, đo owner satisfaction | log có test_id |

---

## PHẦN V — KẾ HOẠCH KHẮC PHỤC TỒN TẠI (Remediation Roadmap)

### 5.1. Critical (trong 7 ngày)

| # | Tồn tại | Root cause | Fix | Owner sign-off |
|---|---|---|---|---|
| **F1** | vector_db_semantic dir rỗng | config path trỏ sai / ChromaDB persist fail | Probe + sửa config + ingest lại 2594 knowledge | auto (low-risk) |
| **F2** | clo_session #24 stalled 75h | thiếu approval queue drainer | Patch self_study.py: timeout 48h → COMPLETED + move to lessons | cần duyệt (touch self-learning) |
| **F3** | semantic_search 0 hits | request body thiếu key đúng | Re-test với key đúng `q`/`top_k` ở body JSON; nếu vẫn fail → mở issue | auto |
| **F4** | Mouth timeline thiếu audio_base64 | TTS mode "background" không gọi synth thật | Probe `/api/voice/tts-synthesize` trực tiếp xem có audio | auto |

### 5.2. High (trong 30 ngày)

| # | Tồn tại | Root cause | Fix | Risk |
|---|---|---|---|---|
| **F5** | Memory review cycle 25 ngày không chạy | scheduler disable hoặc không có task | Bật task `MEMORY_REVIEW_DAILY` qua schtasks | thấp |
| **F6** | 47/50 tasks CANCELLED | thiếu visibility vào lý do hủy | Bảng `task_cancel_reason` + dashboard query | thấp |
| **F7** | Pi5 chưa pair | chưa boot kiosk trên Pi5 | Procedure 6 bước từ skill (md5 + py_compile + restart) | trung bình |
| **F8** | `/api/kiosk/control` 24x nhưng không có `/api/kiosk/status` 200 | endpoint thiếu | Bổ sung route | thấp |
| **F9** | `experience/lessons` count 0/0 — không thấy 516 câu quarantined | schema/table drift | Probe `data/learning_checkpoints.db` + sửa query | thấp |

### 5.3. Medium (trong 90 ngày)

| # | Tồn tại | Fix |
|---|---|---|
| F10 | Analytics modules 8 file không có trigger | Bật metric collector chạy 1h/lần |
| F11 | Creativity/decision modules không wire | Wire trigger vào plan_orchestrator |
| F12 | Causal engine chỉ là lookup table | Implement causal reasoning thật |
| F13 | ecosystem_adapters (DC-COMMAND/Kernel L3/Battery AI) chưa connect | Xác định owner cần endpoint nào trước |
| F14 | Inert OS Job Containment chờ sign-off | Owner review SPRINT6_DESIGN_SIGNOFF.md |
| F15 | speech_learning_quarantine 516 chưa wire vào prompt | Sprint Phase F |

---

## PHẦN VI — TIÊU CHÍ NGHIỆM THU (Acceptance Criteria)

### Sprint A7 Audit-first (1 tuần)
- ✅ `AUDIT_V31_BASELINE.json` xuất ra đầy đủ 6 metric (file inventory, DB audit, test coverage, module status, entry point, process runtime)
- ✅ `AUDIT_EXECUTIVE_SUMMARY.md` ≥5KB, 7+ findings, có recommendations
- ✅ Test pass-rate thật được công bố (kể cả fail) — fail-honest
- ✅ 5 sample conversations đi qua full pipeline có trace_id

### Sprint C1-M4-E1-H1 (12 tuần)
- ✅ Mỗi sprint có `BAO_CAO_V3_SPRINT<n>_<date>.md`
- ✅ Self-RAG grader recall ≥0.95, latency ≤500ms
- ✅ ChromaDB persist health >99% uptime
- ✅ 100 lessons/cycle auto-promote, false-positive ≤5%
- ✅ Pi5 kiosk connect thật, FPS ≥18, 2 chiều lip-sync RTT <300ms

### Tổng quát
- ✅ **Không có** "VERIFIED" nào trong báo cáo nếu chưa E2E thật
- ✅ **Không có** secret nào được print/log
- ✅ **Không có** code chạy ngoài workspace BRAIN (trừ Pi5 đã duyệt)
- ✅ **Không có** task nào tự động chạy lúc khởi động (giữ manual-start)

---

## PHẦN VII — HẠN CHẾ TRUNG THỰC (Honest Limitations)

1. **Test pass-rate chưa chạy xong** — pytest đang chạy nền PID 20256/19176. Báo cáo này dùng số từ memory 18/11 (3.533 pass / 0 fail V10 + 8/15 V21). Cần đợi kết quả mới.
2. **vector_db_semantic size 0 chưa được xác minh tận gốc** — em probe API thấy `n_count` có nhưng filesystem rỗng; có thể là ChromaDB dùng sqlite ngoài hoặc persist trong RAM.
3. **NetChat bot chưa xác minh được từ máy local** — 2 pythonw chạy là AGENT_X_PRO, không thấy `cherry_netchat` process.
4. **Camera Pi5 chưa bao giờ chạy thật** — capability thiếu phần cứng (IMX708 chưa cắm?).
5. **OS Job Containment ở INERT_STAGING** — không có evidence runtime nào.
6. **Avatar Pi5 chưa từng sync V9 motion** — chỉ chạy trên PC harness; chưa biết Pi5 thật có mượt không.
7. **Memory review cycle đã 25 ngày không chạy** — số `last_review_run` từ 27/10; không rõ scheduler bị disable hay task bị xóa.
8. **47/50 tasks CANCELLED** chưa biết lý do — cần query `cancel_reason` để biết owner hủy hay hệ thống tự hủy.

---

## PHẦN VIII — ĐỀ XUẤT TIẾP THEO (Suggested next step)

### Immediate (hôm nay)
- Đợi pytest xong → cập nhật test pass-rate vào §1.1 + §2.2
- Probe thêm 5 endpoint `memory/semantic/search` để khẳng định F3 bug
- Probe `vector_db_semantic/` filesystem để khẳng định F1 root cause

### Tuần này
- Approval card `TASK-AUDIT-V31-EXTENDED` → chạy Sprint A7
- Fix F1 + F2 + F3 (low-risk, không cần duyệt lớn)

### Sprint kế tiếp
- Ưu tiên 1 trong 3 hướng theo quyết định của anh:
  - **(a) Cognition deep**: C1 + C2 → Cherry thông minh hơn rõ rệt
  - **(b) Embodiment thật**: H1 + H2 + H3 → Pi5 thành người, không chỉ là màn hình
  - **(c) Self-learning fix**: L1 + L2 → giải quyết stalled, tự cải thiện liên tục

---

## PHỤ LỤC — Files tham chiếu

- `docs/PROJECT_STATUS.md` — status tổng (đã đọc, mục 18/11 Sprint Memory-Truth)
- `bao cao xay dung he thong/BAO_CAO_V6_M6_MEMORY_TRUTH_20261118.md` — báo cáo gần nhất
- `bao cao xay dung he thong/BAO_CAO_VIVI_AGENT_PORT_20261118.md` — port vivi-agent
- `bao cao xay dung he thong/BAO_CAO_V7_EXPANSION_20261118.md` — V7 capability expansion
- `bao cao xay dung he thong/BAO_CAO_DONG_BO_VA_DOC_RAC_CHERRY_20261118.md` — sync + dọn dẹp
- `references/avatar-motion-template-method.md` (skill) — measure-first loop
- `references/pi5-edge-stability.md` (skill) — 6 bước deploy Pi5
- `references/capability-registry-selfreport.md` (skill) — registry drift
- `src/quan_ai_brain/web/server.py` (350KB, 7.305 dòng, 150+ routes) — HTTP surface
- `data/brain.db`, `data/tasks.db`, `data/governance.db`, `data/learning_checkpoints.db` — runtime state

---

**Ký tên**: TONY (sau rà soát) — 21/11/2026 12:34 ICT
**Trạng thái**: BÁO CÁO READ-ONLY — chưa đụng code, chưa commit
**Approval**: Chờ owner xem và chọn (a)/(b)/(c) cho sprint kế tiếp
