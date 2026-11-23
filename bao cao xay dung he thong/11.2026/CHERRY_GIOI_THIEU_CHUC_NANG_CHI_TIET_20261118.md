# CHERRY — GIỚI THIỆU CHỨC NĂNG CHI TIẾT
**Phiên bản:** 18/11/2026 · **Soạn bởi:** TONY (netMind Desktop, profile tony)
**Phạm vi:** Toàn bộ chức năng của CHERRY (QUAN AI BRAIN) tính đến commit `304d6eb` trên master (PR #36 đã merge)
**Quy tắc:** Fail-honest — mọi con số lấy từ tool thật (probe API 18/11, sqlite brain.db, source code). Không tô hồng phần chưa verify.

---

## 1. CHERRY LÀ GÌ?

**CHERRY** là trợ lý điều hành ảo (Digital Executive Assistant) chạy 24/7 trên máy chủ PC QUANPT (Windows 10) và Raspberry Pi 5, với:

- **Giác quan thật:** tai (mic + wake word + STT), mắt (camera IMX708), miệng (TTS + loa Bluetooth + avatar miệng nhấp nháy)
- **Trí nhớ dài hạn:** 3.157 memories + 3.698 episodes + vector search ChromaDB
- **Tự học liên tục:** chu kỳ 5 phút/lần, không tắt
- **Tự chuẩn đoán:** watchdog phát hiện lỗi hệ thống, báo owner
- **Kỷ luật an toàn:** fail-honest, không tự hành động ghi/gửi ngoài nếu chưa có owner duyệt (R0–R5)

> **Tuyên ngôn:** CHERRY MUST NOT CLAIM INTELLIGENCE. CHERRY MUST DEMONSTRATE INTELLIGENCE.
> **NATURAL MOTION. INTELLIGENT EXPRESSION. HUMAN-CENTERED INTERACTION.**

---

## 2. KIẾN TRÚC 5 LỚP

```
┌────────────────────────────────────────────────────────────────┐
│  LỚP 1 — GIAO DIỆN (UI)                                        │
│  • PC: Dashboard "Phòng Điều Hành" port 8766 (executive.html)  │
│  • PC: Chat Web port 8765 (index.html + cherry_studio.js)      │
│  • Pi5: Kiosk Chrome fullscreen (kiosk.html + avatar)          │
├────────────────────────────────────────────────────────────────┤
│  LỚP 2 — API (Flask-style HTTP server)                         │
│  • 8765: chat, voice, memories, skills, health                 │
│  • 8766: executive, edge (HMAC-signed), NetChat                │
├────────────────────────────────────────────────────────────────┤
│  LỚP 3 — APPLICATION (điều phối)                               │
│  • Orchestrator + task engine + supervisor + consultations     │
├────────────────────────────────────────────────────────────────┤
│  LỚP 4 — COGNITION (nhận thức)                                 │
│  • LLM GLM-5.3-Flash (NetMind cloud, ~1.2s/response)           │
│  • RAG: ChromaDB semantic + keyword                            │
│  • V7 Skills (5 skill read-only, whitelist)                    │
│  • Speech utils + TTS (giọng Hoài My)                          │
├────────────────────────────────────────────────────────────────┤
│  LỚP 5 — INFRA (hạ tầng)                                       │
│  • brain.db (SQLite): memories/episodes/knowledge              │
│  • chroma knowledge_db: vector store                           │
│  • Pi5 edge_client: heartbeat + audio + camera + kiosk         │
│  • WiFi LAN-first, auto-discovery /24                          │
└────────────────────────────────────────────────────────────────┘
```

### Số liệu thật 18/11 (probe trực tiếp)

| Thành phần | Giá trị |
|---|---|
| Memories | **3.157** (EPISODIC 3.135, SEMANTIC 10, PREFERENCE 3, PROCEDURAL 2, CANDIDATE 7) |
| Episodes | **3.698** (bao gồm 113 experience_lesson) |
| Candidate knowledge (chờ duyệt) | 8.997 |
| ChromaDB embeddings | 4.790 |
| API endpoints | ~120+ (liệt kê trong `/api/health`, probe 194 path pattern) |
| V7 skills TESTED | 10/11 skill AVAILABLE/TESTED |

---

## 3. CHỨC NĂNG CHI TIẾT

### 3.1. Hội thoại văn bản + giọng nói (LIVE)

**Luồng E2E:** Owner nói → mic Pi5 → wake "Cherry ơi" (Vosk) → STT → POST `/api/voice/interact` (8766, HMAC) → LLM GLM-5.3-Flash suy luận → TTS piper in-process (681ms/150 ký tự) → audio_base64 + mouth_timeline (viseme frames) → loa SRS-XB33 → avatar miệng nhấp nháy → avatar_state=SPEAKING.

- **Độ trễ đo thật:** full pipeline 230ms text→audio; TTS 681ms cho câu 150 ký tự.
- **Giọng:** Thống nhất **1 giọng = Hoài My** (`vi-VN-HoaiMyNeural`, pref `data/tts_preference.json`); giọng Nam Minh có sẵn nhưng không dùng mặc định.
- **Chống nhiễu TV (fix La La School):** fuzzy match ≤2 lỗi, bỏ cụm TONY quá độ → test 34 câu: 19/19 TV noise bị từ chối, 9/9 giọng thật pass.
- **Barge-in:** endpoint `/api/voice/barge-in` cho phép cắt lời khi đang nói.

### 3.2. Wake word (LIVE, bộ từ owner chốt 11/11)

Bộ từ đánh thức: **"Cherry ơi" / "Cherry" / "Cherry à"** + biến thể Vosk (cheri/ché ri/che ri/chè ri × ơi/oi/à/a). Sprint 18/11 bổ sung 4 phrase vivi-port ("Hey/Hei/Hai/Hay Cherry") — **chưa SCP lên Pi5**.

### 3.3. Avatar 2.5D — Natural Motion (V7, module sẵn sàng — CHƯA wire runtime)

Avatar portrait Model A (896×896) với motion engine 9 module xây 18/11 (commit `149e475`), **fail-open, chưa wire vào avatar_engine runtime**:

| Module | Chức năng |
|---|---|
| `physics.js` | Nguồn sự thật smoothing: damp/spring/angularInertia/jitter — không giật |
| `micro_expression_loop.js` | 12 vi-biểu cảm nền 2.8–7s/lần, intensity theo emotion (SLEEPING 0.05 → SPEAKING 0.55) |
| `motion_profiler.js` | FPS EMA + P95 + 4 LOD adaptive cho Pi5 (mục tiêu ≥50 FPS) |
| `head_dynamics.js` | Quán tính đầu yaw ±8°/pitch ±6°/roll ±4° + thở |
| `audio_mouth_driver.js` | 12 viseme Preston Blair + phoneme tiếng Việt (text-driven + audio RMS) |
| `saccade_engine.js` | Saccade mắt 2–4Hz + blink 2,5–6s có TLB chống robot (17 lần/phút chuẩn sinh lý) |
| `motion_blender.js` | Chuyển state mượt 200–900ms ease-out (SPEAKING→IDLE 300ms, IDLE→SLEEPING 2s) |
| `muscle_controllers.js` | Cơ mặt: brow/cheek/jaw/squint/forehead/cornerPull |
| `motion_heartbeat.js` | Đầu não 60Hz điều phối — 1 state vector duy nhất mỗi frame |

**Profile chuyển động đo từ video tham chiếu "Cherry final.mp4"** (MC talking-head 2h44m): face motion 0,20–0,24; miệng active 99% khi nói; blink 17 lần/phút; head pose ±5°. Em đã calibrate toàn bộ hằng số theo profile này.

**Trạng thái chân thực:** 109 test PASS trên Node.js harness; **chưa test trên Pi5 thật**; chưa wire runtime — chờ owner duyệt.

### 3.4. Trí nhớ chuyên sâu (Deep Cognitive Memory V9)

- **EPISODIC:** tự ghi mỗi phiên chat ("Người dùng hỏi: ...") — 3.135 records
- **SEMANTIC:** tri thức trừu tượng qua ChromaDB vector search (4.790 embeddings)
- **PROCEDURAL:** quy trình từng học (2 records)
- **PREFERENCE:** sở thích owner (3 records)
- **Verification:** OBSERVED 2.952 / UNVERIFIED 113 / VERIFIED 72 / USER_PROVIDED 13 / CANDIDATE 7
- **API:** `/api/memory/semantic/search`, `/api/memory/deep/*` (7 endpoint), `/api/memory/review/*` (6 endpoint)
- **Memory review:** tự phát hiện DUPLICATE/SIMILAR (38 findings), `changes_applied: 0` — chưa tự gộp (chờ owner duyệt)

### 3.5. V7 Skills — Nghiệp vụ trợ lý điều hành

10 skill trong registry (file `data/skill_registry.json`), tất cả **TESTED** lifecycle, chạy qua endpoint `GET /api/v7/skill/<name>` **whitelist 5 skill read-only**:

| Skill (whitelist API) | Chức năng | Args |
|---|---|---|
| `memory_health_audit` | Audit sức khỏe memory (đếm/verif/segment) | — |
| `lesson_mining` | Khai thác bài học từ experience_lesson | `limit=N` |
| `system_status_summary` | Tổng hợp trạng thái hệ thống | — |
| `pipeline_audit` | Audit pipeline errors + governance events | `limit=N` |
| `voice_health_check` | Kiểm tra TTS/mic/loa/wake | — |

5 skill registry khác (TASK_STATUS_RECONCILIATION, EMAIL_ANALYSIS, CROSS_SOURCE_EVIDENCE_ANALYSIS, PROGRESS_RISK_DETECTION, OWNER_ADVISORY_REPORT, VERIFIED_WORKFLOW_REUSE) — TESTED nhưng **chưa mở qua HTTP** (không có trong whitelist), gọi nội bộ.

**Cách chạy nhanh:**
```
curl http://127.0.0.1:8765/api/v7/skill/memory_health_audit
curl http://127.0.0.1:8765/api/v7/skill/pipeline_audit?limit=10
```

Trong chat `/api/chat`: trigger words tự chạy skill + marker 🧠/🔊/📜 cuối reply (block V7 chạy ngoài `if create_task` — wire LIVE 18/11 commit `07da555`).

**Kỷ luật skill:** stdlib-only, read-only, `action_policy: report_only` — KHÔNG tự ghi/gửi ngoài. Lifecycle: PROPOSED → IMPLEMENTED_IN_SANDBOX → TESTED → APPROVED → AVAILABLE.

### 3.6. Tự học (learning_daemon) — LIVE

- Chu kỳ **5 phút/lần**, đọc docs/git/test → `candidate_knowledge` (8.997 records chờ duyệt)
- 169 facts/ngày (đo 11/11); log 180.718 dòng
- **Điểm yếu trung thực:** nạp lặp rác (fact "Test suite: 3648 passed" 160 lần/ngày) — chưa có auto-dedupe
- API: `/api/learning/status`, `/api/learning/pause`, `/api/learning/resume`, `/api/learning/trigger`

### 3.7. Tự chuẩn đoán (watchdog + memory_review) — LIVE

- **Watchdog** (cap 5 lần/giờ): phát hiện FED mất kết nối, CLO session stall >24h (tự advance #15→#16), NetChat responder stale, learning daemon chết
- **Giới hạn:** chỉ PHÁT HIỆN + log + báo owner — KHÔNG tự sửa (trừ `ensure_daemon_alive` whitelist)
- **Memory review:** session tự chạy, findings DUPLICATE/SIMILAR, chưa tự áp dụng
- API: `/api/health`, `/api/health/history`, `/api/health/rca`, `/api/health/machine`, `/api/autonomic/status`, `/api/autonomic/selftest`

### 3.8. Quản trị tác vụ + tham vấn (Executive Layer) — LIVE

Dashboard "Phòng Điều Hành" (port 8766) gồm 11 tab thật:

| Tab | Chức năng |
|---|---|
| Dialogue | Chat + hội thoại nhận thức với CHERRY |
| Deep Memory | Trí nhớ chuyên sâu V9 — search/timeline/units |
| Consultation | Hộp thư tham vấn & xin ý kiến owner |
| Orchestration | Điều hành kế hoạch đa lĩnh vực + giám sát ranh giới an toàn |
| Workbench | Quản lý work-queue + tasks |
| Learning | Báo cáo tự học + hồ sơ nâng cấp hệ thống |
| NetChat | Kênh "Trợ lý Tony Pham" 24/7 |
| Edge Sync | Đồng bộ PC↔Pi5 (heartbeat, alerts, transfers) |
| Pi5 Embodiment | Trạng thái cơ thể Pi5 (avatar, audio, camera) |
| Intelligence | Scorecard + audit trí tuệ |
| Persona | Hồ sơ bản sao số của Quanpt1 |

**API tái vụ đầy đủ:** `/api/executive/tasks/*` (7 endpoint), `/api/executive/consultations/*` (3), `/api/executive/edge/*` (25+), `/api/workbench/*`, `/api/todos/*`, `/api/plan`, `/api/supervisor/*`.

### 3.9. NetChat — Bot "Trợ lý Tony Pham" 24/7 (LIVE)

- Gửi/nhận tin nhắn NetChat như một nhân viên
- **2-step gate an toàn:** DM owner PHẢI preview trước + hỏi xác nhận rồi mới `--confirmed <token>` — KHÔNG tự gửi
- API: `/api/executive/netchat/status|messages|send|command`

### 3.10. Camera + File transfer (LIVE trên Pi5)

- **Mắt:** IMX708 Module 3, chụp 47KB, `camera_on` → READY, snapshot + library + stream (10 endpoint camera)
- **File:** upload/download/sync-all/delete + transfer initiate/chunk/ack/status/history (HMAC-signed)

### 3.11. Kết nối Pi5↔PC — Ưu tiên số 1 (LIVE)

- **WiFi LAN-first:** discovery /24, DHCP reservation khuyến nghị, `core_host` tự tìm lại
- **Auto-discovery (PR #18):** PC đổi IP → Pi5 DISCONNECTED 20s → **45s sau tự tìm lại**, RTT 3–32ms, config sống qua restart
- **Channel selector:** chọn LAN/MESH, cấm ghi MESH vào core_host (tránh đấm ngược discovery)
- **Bảo mật:** mọi POST từ Pi5 HMAC-sign, sai key → 401 + record_auth_failure
- **Tailscale:** đã bỏ (NoState vĩnh viễn) — LAN-only

### 3.12. LLM Router

- **Mặc định:** `zai-org/GLM-5.3-Flash` qua NetMind cloud (Viettel AI Gateway) — ~1.2s/response
- **Ollama qwen2.5:7b:** DISABLED theo owner (chỉ dùng BGE-M3 embedding, bước 0/5 của launcher)
- **Fail-honest:** thiếu API key → trả lỗi rõ, không suy diễn

### 3.13. Vận hành 24/7 (LIVE)

| Thành phần | Chi tiết |
|---|---|
| Launcher | `KHOI_DONG_24_7.bat` — 7 bước (0/5→6/6) |
| Dual servers | 8765 (chat/voice) + 8766 (executive/edge), watchdog restart |
| Learning | 5 phút/chu kỳ, pause/resume được |
| Watchdog | Tự restart cap 5/giờ |
| **Cherry Autonomous Mode** | **MỚI 18/11** (`76f69e1`) — tự vận hành chủ động 24/7 (`tools/cherry_autonomous.py`) |
| Backup | 2AM hằng ngày (Task Scheduler) |
| Report | 8AM hằng ngày (Task Scheduler) |
| Power | AC=0, display-off 600 GIỮ, DC=240s (powercfg never-sleep) |
| VBS wrapper | Set CurrentDirectory=E:\BRAIN trước khi Run (fix Task Scheduler cwd bug 18/11) |

### 3.14. Governance & An toàn (R0–R5)

1. **Không đọc secret** — không mở .env/credentials/keys, redact mọi log
2. **R5 hard-block** — không có hard-coded credentials hay override secret
3. **R4 approval** — hành động nhạy cảm cần owner duyệt qua `approval_cards` (2 bảng v1+v2)
4. **Quarantine** — tri thức lạ vào candidate, không tự promote
5. **Fail-honest** — thiếu dữ liệu → UNKNOWN/NOT_VERIFIED, không suy diễn
6. **Learning ≠ deployment** — tri thức mới quarantine đến khi có evidence + test + duyệt

---

## 4. TRẠNG THÁI SỐC — GIỚI HẠN TRUNG THỰC

| Hạn chế | Chi tiết |
|---|---|
| MiniLM yếu câu meta | Semantic search kém với câu hỏi meta ("em là ai") |
| Distance threshold 0.85 | Heuristic, chưa tune |
| Tư duy phản biện 3/10 | Có nguồn, chưa đánh giá nguồn (source-trust scoring chưa làm) |
| Watchdog chỉ phát hiện | Chưa tự sửa (trừ whitelist service) |
| Memory review chưa khép vòng | changes_applied = 0 |
| Auto-dedupe chưa có | 160 fact rác/ngày |
| Quarantine tắc | 8.997 candidate chờ duyệt |
| V7 motion | Chưa wire runtime, chưa SCP Pi5, chưa test Pi5 thật |
| 9 test pre-existing | TimeoutError/HTML cache/edge kiosk — không liên quan chức năng chính |
| Pi5 wake mở rộng | 4 phrase "Hey Cherry" chưa SCP lên Pi5 |

---

## 5. LỘ TRÌNH SẮP TỚI (theo sprint đã chốt)

1. **Wire motion heartbeat vào avatar_engine** — bật chuyển động mượt thật (chờ owner duyệt)
2. **SCP 9 file JS + wake mở rộng lên Pi5** — test Pi5 thật ≥50 FPS
3. **BM25 lexical thật + synonyms YAML** — cải thiện recall 0.625 → 1.0 (hybrid semantic)
4. **Source-trust scoring + auto-dedupe** — chặn nhiễm TV từ gốc (Hướng A trong báo cáo 11/11)
5. **Watchdog có action an toàn** — tự restart whitelist service
6. **Quarantine batch review UI** — giải tỏa 8.997 candidate
7. **Nâng 5 skill lên APPROVED/AVAILABLE** — sau khi chạy ổn định

---

*Tài liệu kết thúc. Mọi số liệu lấy từ probe thật 18/11/2026 (API /api/health, sqlite brain.db, source code commits 304d6eb). Fail-honest: không mục nào ghi LIVE nếu chưa có bằng chứng.*
