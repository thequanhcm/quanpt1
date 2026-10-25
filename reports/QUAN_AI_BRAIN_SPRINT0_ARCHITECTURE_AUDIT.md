# QUAN AI BRAIN — SPRINT 0: ARCHITECTURE AUDIT REPORT

**Mã tài liệu:** `RPT-QAB-SPRINT0-AUDIT-V1`
**Ngày lập:** 2026-10-25
**Người lập:** Agent Kiến trúc trưởng (Chief AI Systems Architect & Cognitive Engineering Lead)
**Chủ sở hữu phê duyệt:** Anh Quân — `Quanpt1`
**Workspace:** `E:\AI\QUAN AI BRAIN`
**Trạng thái:** ✅ HOÀN THÀNH — CHỜ PHÊ DUYỆT CHỦ SỞ HỮU (trước Sprint 1)

---

## 1. Baseline xác minh thực tế (không tin số liệu trong báo cáo cũ)

| Hạng mục | Giá trị xác minh trực tiếp | Nguồn bằng chứng |
|---|---|---|
| Git branch / commit | `master` @ `9243d12` | `git rev-parse` |
| Working tree | 17 modified, 324 untracked, 0 stash, `git diff --check` sạch (chỉ warning CRLF) | `git status --porcelain` |
| Python | 3.11.9 x64 (`.venv`) + pytest 9.1.1 | `.venv/Scripts/python.exe --version` |
| Baseline test | **484 passed, 1 skipped, 0 failed — 66.08s** | pytest độc lập (`tests/`) |
| Test bị skip duy nhất | TTS hardware probe — `pytest.skip()` trung thực vì Pi 5 offline, đúng thiết kế | `tests/test_vietnamese_tts.py:266` |
| Ollama daemon | **ONLINE** `127.0.0.1:11434`, 6 model; `bge-m3` (566.70M, F16, 1024-dim), `qwen2.5:7b` (7.6B Q4_K_M) | `/api/tags`, `/api/ps` |
| GPU | **Quadro T1000 — 4096 MiB**, dùng 2824 MiB | `nvidia-smi` |
| VRAM của 7B | Chỉ nạp **2.3 GB / 5.1 GB** model (partial offload) | `/api/ps` `size_vram` |
| Web server 8765/8766 | ĐANG TẮT tại thời điểm audit (không ảnh hưởng test) | TCP probe |
| DB thực | tasks.db: 76 tasks / 24 steps; brain.db: 316 episodes / 323 memories; governance.db: 147 emergency states / 291 events; consultations.db: 5 tickets | sqlite3 read-only |
| NetMind base URL | `https://stream-netmind.viettel.vn/aigw/ai/v1` | `NETMIND_DESKTOP_LLM_BASE_URL` (chỉ tên biến) |
| NetMind catalog | HTTP 200 — 6 model; **có `zai-org/GLM-5.3-Flash`**; **KHÔNG có `GLM-5.3` đầy đủ, KHÔNG có `GLM-5.3-FlashX`** | GET `/models` với key đọc trong bộ nhớ tiến trình, không in ra |
| GLM-5.3-Flash chat | HTTP 200, **0.52s**, tiếng Việt tự nhiên, 53 prompt + 80 completion tokens (63 reasoning tokens) | POST `/chat/completions` |
| Test output gốc (module test.json) | 17 passed (Sprint 1 walking skeleton) — KHÁC suite 485 bài hiện tại | `reports/test.json` |

> Kết luận baseline: báo cáo handoff 484/1/0 khớp bằng chứng thực tế. Commit message "17 passed tests" chỉ phản ánh
> snapshot Sprint 1 đầu tiên, không phải trạng thái hiện tại. Suite hiện tại là 485 bài test.

---

## 2. Giải quyết 5 mâu thuẫn bắt buộc (§3.2 Master Prompt)

### 2.1. LLM ✅ GIẢI QUYẾT
- `LLMRouter` (`src/quan_ai_brain/llm/router.py`) là **router cục bộ thuần heuristic** (fast/reasoning/fallback),
  KHÔNG có provider cloud nào. `OllamaClient` chặn mọi host ≠ localhost (giữ nguyên — đúng thiết kế).
- Ollama daemon **đang online** — báo cáo "daemon offline" đã lỗi thời.
- **Mâu thuẫn hiệu năng giải mã:** GPU chỉ 4 GB → 7B chỉ nạp 2.3/5.1GB → **6.0 tok/s thực tế, 35.6s cold** (báo cáo cũ ghi 20.6s).
  Các con số 0.5–0.79s trong báo cáo kiến trúc chỉ đúng cho 0.5B/1.5B **khi đã warm**.

### 2.2. Task orchestration ✅ GIẢI QUYẾT — BÁO CÁO KIẾN TRÚC ĐÚNG, HANDOFF CŨ LỖI THỜI
- `PlanOrchestrator.submit_plan()` (`src/quan_ai_brain/orchestration/plan_orchestrator.py:63`) ĐÃ nối TaskPlan →
  `DurableTaskRegistry` với DAG validation, risk assessment R0–R5, idempotency key, R5 hard-block, R4 gate, inert sandbox.
- Bằng chứng runtime: `data/tasks.db` có **76 durable_tasks / 24 durable_task_steps**.
- "Kết nối TaskPlan vào DurableTaskRegistry" trong handoff là **residual text lỗi thời**, không còn đúng hiện trạng.

### 2.3. Voice ✅ GIẢI QUYẾT — handoff cũ đang QUÁ LỖI THỜI
- Handoff cũ ghi "Voice Interface NOT_IMPLEMENTED" nhưng toàn bộ pipeline đã tồn tại và 56 module test đều pass:
  `voice/tts.py` (edge-tts `vi-VN-HoaiMyNeural`), `voice/mouth_sync.py`, `voice/wake_word.py`,
  endpoints `/api/voice/*`, edge_client daemon + kiosk + av engine.
- Skip duy nhất là **hardware Pi 5 probe**, đúng quy tắc "không giả thành công phần cứng".
- Trạng thái chuẩn: `IMPLEMENTED & TESTED (PC)`, `NOT_VERIFIED_ON_PI_HARDWARE (E2E)`. Đã sửa handoff template.

### 2.4. Embedding BGE-M3 "9.64s" ✅ GIẢI QUYẾT
- Đo độc lập: **cold 0.466s / warm 0.387s** (1024-dim, text ~60 ký tự) — model đã resident trong daemon từ trước.
- Con số 9.64s trong báo cáo kiến trúc = **cold-start gồm thời gian load model vào VRAM**, không phải warm inference
  và không phải pipeline. Ghi nhận trong báo cáo audit, chưa sửa báo cáo kiến trúc (chờ duyệt).

### 2.5. Hiệu năng LLM ✅ GIẢI QUYẾT — ĐÃ ĐO ĐỘC LẬP CÓ ĐỊNH NGHĨA RÕ
`reports/SPRINT0_RUNTIME_PROBE.json` (kèm số hiệu chỉnh 20s→35.6s/7B):
- `qwen2.5:0.5b`: cold 2.77s (load 2.35s), warm **0.68s**, 133–145 tok/s
- `qwen2.5:1.5b`: cold 2.60s (load 2.02s), warm 0.68–8.8s (dao động do prefill prompt dài), 77–79 tok/s
- `qwen2.5:7b`: cold **35.6s (load 17.1s)**, **6.0 tok/s** — không phù hợp dùng làm reasoning tier mặc định
  cho hội thoại tương tác; 2.3GB VRAM của GPU 4GB là nghẽn cổ chai.
- Định nghĩa phép đo: `wall_s` = tổng thời gian request (stream=False); `load_s` = model load trong request;
  `eval_count` = số token sinh ra; tok/s = `eval_count / eval_s`. N = 1–2 sample mỗi model (n=1 cho 7B) —
  nhỏ, đủ dùng cho audit, chưa đủ cho benchmark chính thức (Sprint 1 sẽ chạy benchmark chuẩn).

### 2.6. Working tree ✅ GIẢI QUYẾT
- 17 modified + 324 untracked đã liệt kê đầy đủ, KHÔNG có nội dung bị đè. Quá trình audit chỉ thêm file mới
  (báo cáo + 3 công cụ probe) trong `reports/` và `tools/`, không sửa file có sẵn nào.

---

## 3. Capability Matrix (trạng thái gắn với bằng chứng)

| Module | File | Trạng thái | Bằng chứng |
|---|---|---|---|
| LLM Router | `llm/router.py` | VERIFIED (local-only) | code + runtime probe |
| Ollama Client (local) | `llm/client.py` | VERIFIED_E2E | daemon online, embed/generate chạy thật |
| **NetMind Provider** | — | **MISSING** | không có adapter nào trong codebase |
| BGE-M3 Embedding | `cognition/embedding.py` | VERIFIED | 0.39–0.47s, 1024-dim |
| Hybrid Retrieval | `cognition/retrieval.py` | INTEGRATION_TESTED | code + test suite |
| Memory SQLite | `memory/sqlite_store.py`, `data/brain.db` | VERIFIED_E2E | 323 memories, 316 episodes |
| PlanOrchestrator↔Registry | `orchestration/plan_orchestrator.py` | VERIFIED_E2E | 76 tasks trong tasks.db |
| Governance R0–R5 | `governance/policy.py`, `state_store.py` | VERIFIED_E2E | 147 emergency states, 291 events |
| Approval/Delegation/Verifier | `tools/approval.py`, `delegation.py`, `signature.py` | INTEGRATION_TESTED | 49 tests pass, chưa dùng R4 thật |
| Sandbox/PathGuard/Redaction | `tools/sandbox.py`, `path_guard.py`, `core/redaction.py` | VERIFIED_E2E | test suite |
| Voice TTS vi-VN | `voice/tts.py` | UNIT_TESTED_ONLY (PC) | skip trung thực Pi 5 |
| Wake word/VAD/ASR/barge-in | `voice/wake_word.py` | IMPLEMENTED_NOT_VERIFIED | code có, không bằng chứng E2E |
| Pi 5 Edge Client | `edge_client/` | IMPLEMENTED_NOT_VERIFIED (lúc audit) | không ping được Pi (192.168.1.21 offline) |
| Daemon 24/7 | — | MISSING (đúng an toàn) | không có service chạy |
| **GLM-5.3-Flash qua NetMind** | — | **VERIFIED (probe) / MISSING (adapter)** | HTTP 200 + chat 0.52s |

---

## 4. Kết luận & quyết định cần anh Quân phê duyệt

### D1 — Cập nhật trạng thái thực tế vào báo cáo (rủi ro thấp)
Sửa các mốc sai trong `docs/PROJECT_STATUS.md` + `HANDOFF_LATEST.md`: "Voice NOT_IMPLEMENTED" → trạng thái đúng;
"daemon offline" → online; 7B 20.6s → 35.6s (VRAM 4GB); BGE-M3 9.64s → ghi chú cold-start vs warm 0.4s.

### D2 — Sprint 1: NetMind GLM-5.3-Flash provider (rủi ro thấp, không xóa local)
Xây `src/quan_ai_brain/llm/netmind_provider.py` theo hợp đồng `LLMProvider` hiện có:
- Model mapping thực tế: Tier 1 Fast = `zai-org/GLM-5.3-Flash`; Tier 2/3 = `zai-org/GLM-5.3-Flash`
  (vì catalog KHÔNG có GLM-5.3 đầy đủ). Qwen local giữ nguyên cho offline/private.
- Config: `NETMIND_BASE_URL`, `NETMIND_API_KEY` (chỉ env var, không hardcode), `NETMIND_TIMEOUT_SECONDS`,
  `NETMIND_MAX_RETRIES`, `NETMIND_EXTERNAL_DATA_ALLOWED` (default FALSE — fail-closed).
- **Điểm kỹ thuật bắt buộc:** `reasoning_tokens` chiếm 63/80 token ở probe → cần cơ chế tắt/giảm reasoning
  (kiểm tra tham số `reasoning_effort`/`thinking` trên gateway) hoặc ngân sách token riêng, nếu không sẽ chậm và tốn.
- Streaming: GET /models + non-stream chat đã xác minh; **streaming chưa được xác minh** (cần Sprint 1).
- Audit log định tuyến (provider/model/reason/latency/tokens), không log nội dung nhạy cảm.

### D3 — Benchmark so sánh Qwen vs GLM-5.3-Flash (sau D2)
Chạy cùng bộ câu hỏi tiếng Việt (16 nhóm theo §5.5), đo accuracy/naturalness/latency/fallback; so Qwen 0.5B/1.5B/7B
local vs GLM-5.3-Flash. Có bộ dữ liệu benchmark đầu tiên trước khi bật tier mới vào production path.

### D4 — Handoff template 3 trường trung thực (rủi ro thấp)
Thêm 3 trường vào template của `tools/validate_and_report.py`:
1. `test_suite_identity` (485 bài + tên các file test mới nhất)
2. `report_freshness` (cảnh báo "tuyên bố ở section X có thể lỗi thời, luôn đối chiếu code+test hiện tại")
3. `verification_status` 5 mức (CURRENT / AGING / STALE / CONTRADICTED / UNKNOWN) cho từng tuyên bố then chốt.
Mục đích: chấm dứt tình trạng báo cáo cũ mâu thuẫn với hiện trạng (bài học từ chính audit này).

### D5 — Sprint 2: GPU budget & keep-warm policy (trung bình)
Quadro T1000 4GB không đủ giữ 7B (5.1GB) + BGE-M3 (1.2GB) đồng thời. Đề xuất chính sách:
fast tier (0.5B/1.5B + BGE-M3) resident mặc định; 7B on-demand và **fallback lên GLM-5.3-Flash khi 7B cold > ngưỡng**;
đo keep-warm pulse hiện tại trước khi đổi.

### D6 — Đo E2E voice trên Pi 5 khi phần cứng online (BLOCKED hiện tại)
Giữ nguyên trạng thái BLOCKED trung thực cho đến khi Pi 5 kết nối mạng. Không fake kết quả.

### D7 — Commit Sprint 0 (rủi ro thấp)
Commit toàn bộ working tree hiện tại (17M + 324 untracked) làm 1 commit Sprint 0 audit để neo trạng thái,
trước khi bắt đầu diff Sprint 1.

---

## 5. Bằng chứng đính kèm
- `reports/SPRINT0_RUNTIME_PROBE.json` — đo cold/warm thực tế 4 model.
- `reports/SPRINT0_NETMIND_CATALOG.json` — danh mục model thật (không chứa key).
- `reports/SPRINT0_NETMIND_CHAT_SMOKE.json` — smoke test GLM-5.3-Flash (không chứa key).
- `tools/sprint0_probe.py`, `tools/sprint0_netmind_probe.py`, `tools/sprint0_netmind_chat_probe.py` — công cụ đo có thể tái lập.
- Baseline test: `484 passed, 1 skipped in 66.08s` — chạy lại bằng `.venv/Scripts/python.exe -m pytest -q tests`.

---

## 6. Rủi ro & biên giới
- Audit KHÔNG đọc giá trị secret nào; key NetMind chỉ được load vào bộ nhớ tiến trình probe, không in/log/lưu file.
- Audit KHÔNG sửa file mã nguồn/docs có sẵn; chỉ thêm 4 file mới (báo cáo + 3 probe tools).
- Mọi kết luận `VERIFIED_*` gắn với bằng chứng runtime trong phiên ngày 2026-10-25; tuyên bố trong tài liệu cũ
  không được dùng làm bằng chứng.

---

*Được lập bởi Agent Kiến trúc trưởng theo Master Prompt V1, mục §XV: dừng chờ phê duyệt của anh Quân
trước khi triển khai Sprint 1.*
