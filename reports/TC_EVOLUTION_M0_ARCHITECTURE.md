# TONY COGNITIVE EVOLUTION — M0 ARCHITECTURE (HIỆN TRẠNG KIẾN TRÚC THỰC)

**Thời điểm:** 01/11/2026 09:45. Tài liệu này mô tả kiến trúc **đang tồn tại thật** (đã audit code + chạy thử), tách bạch rõ phần nào đã wired, phần nào chỉ nằm rời.

---

## 1. Sơ đồ kiến trúc hiện hành (đã xác minh)

```text
                    QUANPT1
        (NetChat DM · Giọng nói qua Pi5 · Dashboard)
                       |
        ┌──────────────┴───────────────┐
        |       KÊNH GIAO TIẾP         |
        |  NetChat DM (responder 2s)    |
        |  Voice chain (wake→VAD→STT)   |
        └──────────────┬───────────────┘
                       |
   ┌───────────────────┴────────────────────┐
   |        PC — BỘ NÃO (D:\...\BRAIN)      |
   |  start_dual_servers.py                 |
   |  ├─ :8766 Executive Server             |
   |  │   ├─ /api/chat (Ollama qwen2.5:7b)  |
   |  │   ├─ /api/executive/* (edge ctl)    |
   |  │   ├─ /api/voice/tts-synthesize      |
   |  │   ├─ /api/health (4 components)     |
   |  │   └─ guardrails, redaction, audit   |
   |  └─ :8765 GLM Server                   |
   |      └─ /api/chat (GLM-5.3-Flash)      |
   |                                        |
   |  Responder NetChat (poll 2s, DM)       |
   |  Command Center (12+ intent)           |
   |  Learning daemon + Scheduled ×3        |
   |  Watchdog (stale 150s)                 |
   └───────────────────┬────────────────────┘
                       | Tailscale (rtt 30ms)
   ┌───────────────────┴────────────────────┐
   |      PI5 — HÌNH THỂ (EDGE-PI5-DESK-01) |
   |  quan_ai_edge daemon (8768):           |
   |   kiosk avatar, speak, photo, HDMI,    |
   |   voice VAD conversation, mic/speaker  |
   |  quan_ai_wake (Vosk BT-first, 4 cụm)   |
   |  quan_ai_kiosk_guard (60s, flag-aware) |
   └────────────────────────────────────────┘
```

## 2. Ma trận module ↔ trạng thái wired

### 2.1. Nhận thức (cognition/) — 39 file

| Module | Dòng | Đã wired vào server/runtime? | Bằng chứng |
|---|---|---|---|
| `context_builder.py` | — | **CÓ** — mọi /api/chat | Audit code + test suite |
| `executive_persona.py` | — | **CÓ** — prompt persona | Test + chat thật |
| `cognitive_loop.py` | 459 | **MỘT PHẦN** — Sprint B, chưa phải vòng duy nhất | Docstring; không thấy gọi từ /api/chat chính |
| `critical_thinker.py` | 575 | **MỘT PHẦN** | Tồn tại + test; chưa thấy trong luồng chat chính |
| `self_model_engine.py` | 507 | **MỘT PHẦN** (Sprint 4) | Có engine; chưa thấy API expose |
| `self_care_engine.py` | 351 | **MỘT PHẦN** (Sprint 6) | Tồn tại; chưa thấy scheduler |
| `continuous_learning_engine.py` | 655 | **MỘT PHẦN** (Sprint 5) | Có engine; learning daemon chạy riêng |
| `system_inventory.py` | 440 | **MỘT PHẦN** | Có engine |
| `capability_registry.py` | 181 | **CÓ** — /api/executive/capabilities | Endpoint thật |
| `skill_registry.py` | — | **CÓ** — /api/skills | Endpoint thật |
| `vietnamese_conversation.py` | — | CẦN KIỂM TRA wired | — |
| `role_orchestrator.py` | — | **CÓ** — `_GLOBAL_ROLE_ORCHESTRATOR` trong server | Audit code |

### 2.2. Trí nhớ (memory/) — 40 file

| Nhóm | File chính | DB | Trạng thái |
|---|---|---|---|
| Store lõi | `sqlite_store.py`, `session_manager.py` | brain.db | **LIVE** (2.004 memories, 2.548 episodes) |
| Deep memory | `deep_memory.py` (934 dòng), `knowledge_graph.py`, `causal_chains.py` | knowledge_units=150, relations=210 | **LIVE nhưng ít dữ liệu** |
| Conflict/dedupe | `conflict_detector.py` (687 dòng), `duplicate_detector.py` | — | **CÓ ENGINE** — chưa thấy chạy định kỳ |
| Quarantine | `quarantine_store.py` + `clae/quarantine.py` | candidate_knowledge=4.284 | **LIVE nhưng kẹt** (verifier None → không promote được) |
| Consolidation | `experience_consolidation.py`, `lesson_learner.py` | — | **CÓ ENGINE** — wiring chưa rõ |
| 5-layer memory (Episodic/Semantic/Procedural/Relational/Cognitive) | Phân tán: episodes, semantic_memory, best_practices, knowledge_relations, causal_reasoning | 5 bảng riêng biệt | **CÓ VẬT CHẤT nhưng CHƯA THỐNG NHẤT** thành một API |

### 2.3. Orchestration & governance

| Thành phần | File | Trạng thái |
|---|---|---|
| Task registry | `orchestration/task_registry.py` + tasks.db (578 tasks, 1.029 steps) | **LIVE** |
| Supervisor | `orchestration/supervisor.py` (352 dòng) | CÓ — chưa thấy chạy nền |
| Plan orchestrator | `plan_orchestrator.py` | CÓ — wired một phần (task_id/correlation_id trong kiosk status) |
| Approval cards | `governance/approval_cards.py` (346 dòng) + approval_cards table (0 rows) | **CÓ SẴN nhưng CHƯA DÙNG** |
| Consultation inbox | `consultation_inbox.py` + consultations.db | CÓ — wired (sprint trước) |
| Policy R0–R5 | `governance/policy.py`, `core/guardrails.py`, `core/redaction.py` | **LIVE** (test pass) |
| Audit | `core/audit.py` + audit.db (384 KB) | **LIVE** |

### 2.4. Learning (learning/)

| Thành phần | Trạng thái |
|---|---|
| `engine.py`, `evaluation.py`, `knowledge_refiner.py` | Wired qua learning_daemon (log 09:13) |
| `self_optimizer.py` (437 dòng) | CÓ ENGINE — phạm vi tuning param, chưa thấy chạy thật |
| `federated_learning.py`, `federated_orchestrator.py` | CÓ — cần audit phạm vi thật |
| Quarantine gate | **CHẶN bởi approval_verifier=None** — 4.284 candidates tồn đọng |

### 2.5. Voice (đã LIVE hoàn chỉnh 01/11)

| Chuỗi | Trạng thái |
|---|---|
| Wake word (Vosk, BT-first, 4 cụm, AGC+fuzzy) | **LIVE E2E** |
| Hội thoại liên tục: chào <0,5s → VAD 280 → converse → GLM → TTS → loa | **LIVE E2E 01/11** (giới hạn: loa BT mất nguồn lúc 09:04 — chờ owner bật) |
| STT faster-whisper small int8 (subprocess venv) | **LIVE** |
| TTS Edge-TTS + retry ×2 | **LIVE** (flaky 403 đã có fallback retry) |
| Barge-in / echo handling | **CHƯA CÓ** (đã xử lý echo bằng cách đóng mic khi phát) |

### 2.6. Health (hiện tại mỏng)

| Thành phần | Trạng thái |
|---|---|
| `/api/health` (4 components, health.py chỉ 30 dòng) | **CÓ — RẤT CƠ BẢN** |
| Edge telemetry (rtt, packets, avatar) | **LIVE** |
| PC CPU/RAM/disk monitor | **CHƯA CÓ** trong server |
| Pi5 temp/throttled/reboot history | **CHƯA CÓ** — em probe tay qua SSH |
| Alert engine / Health state machine | **CHƯA CÓ** |

## 3. Điểm mạnh kiến trúc (giữ lại, không xây lại)

1. Tách bộ não (PC) — hình thể (Pi5) đã rõ ràng qua HTTP + HMAC (đúng hướng MULTIPLE EMBODIMENTS).
2. Governance R0–R5 + guardrails + redaction + audit đã chạy thật và có test.
3. Responder NetChat có self-healing (watchdog, seen-after-send, catch-up 12h).
4. Voice chain E2E hoàn chỉnh ngày 01/11.
5. Test suite 2.958 tests — nền regression tốt.

## 4. Điểm yếu kiến trúc (đối chiếu kiến trúc mục tiêu)

1. **Chưa có ONE Cognitive Core thống nhất** — nhiều engine mạnh (cognitive_loop, critical_thinker, self_model, self_care, continuous_learning) tồn tại rời rạc, chưa có Event Bus nối chúng.
2. **Chưa có Cognitive Event Bus** — các thành phần giao tiếp qua gọi hàm trực tiếp + DB, không có event trung tâm.
3. **Chưa có Module Registry động** — capability_registry là static list, không phản ánh health/test/runtime theo thời gian thực.
4. **Memory 5 lớp tồn tại vật lý nhưng chưa có API thống nhất** — retrieval hiện đi qua CognitiveRetriever riêng.
5. **Health intelligence mỏng** — health.py 30 dòng; thiếu PC/Pi5 deep monitors + alert engine.
6. **Learning kẹt ở approval gate** — 4.284 candidates không thể promote (verifier chưa cấu hình — đúng theo AGENTS.md, chờ owner).
7. **Không có git** — 83k dòng code không có version control → rủi ro bảo toàn tri thức.
8. **journald Pi5 volatile** — mất khả năng điều tra sự cố quá khứ.

*Kế hoạch xử lý từng điểm: `TC_EVOLUTION_M0_GAP_ANALYSIS.md`.*
