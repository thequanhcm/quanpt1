# BÁO CÁO HỆ THỐNG QUAN AI BRAIN — TỔNG HỢP ĐẾN 25/10/2026

**Mã tài liệu:** `RPT-QAB-SYS-SUMMARY-V1-20261025`
**Ngày phát hành:** 25/10/2026
**Chủ sở hữu hệ thống:** Anh Quân — `Quanpt1`
**Người lập báo cáo:** TONY PHAM / QUAN AI BRAIN — Agent Kỹ sư kiến trúc trưởng
**Phạm vi:** Toàn bộ hệ thống từ Sprint 0 → Sprint 2 + Audit Avatar Model A (Digital Human V3, Giai đoạn A)

---

## 1. TÓM TẮT ĐIỀU HÀNH

QUAN AI BRAIN đã hoàn thành và xác minh 3 sprint liên tiếp:

| Sprint | Nội dung | Trạng thái |
|---|---|---|
| **Sprint 0** | Architecture Audit — giải quyết 5 mâu thuẫn lớn giữa các báo cáo | ✅ Hoàn thành, commit neo `4d90465` |
| **Sprint 1** | Tích hợp GLM-5.3-Flash qua NetMind (đã duyệt D1–D7) | ✅ Hoàn thành, commit `d7be168`, 502 tests pass |
| **Sprint 2** | Streaming SSE + Deep Reasoning Qwen3.5-122B + Policy vĩnh viễn + Barge-in Pi 5 | ✅ Hoàn thành trên PC + E2E thật trên Pi 5 — **chưa commit** (chờ nghiệm thu) |
| **Avatar V3 Giai đoạn A** | Audit engine hình thể số Model A | ✅ Audit xong — **diff chưa trình/duyệt**, chưa sửa mã |

**Test suite hiện tại: 512 passed, 1 skipped, 0 failed (73.9s).** Kết quả E2E thật: streaming GLM first-delta 1.5–1.8s; Pi 5 phát tiếng Việt HoaiMyNeural và avatar chuyển SPEAKING→IDLE được xác minh qua API kiosk.

Hai quyết định đang chờ anh Quân: (1) duyệt đẩy `kiosk.js`/`wake_engine.js` bản barge-in vào thư mục gốc daemon Pi 5, (2) duyệt diff Giai đoạn B của Avatar V3 (đồng bộ miệng theo timeline-only + duration chính xác).

---

## 2. BASELINE HẠ TẦNG (đo thật 25/10/2026)

### 2.1. Phần cứng & môi trường
- **PC Core:** Windows 10 x64, Python 3.11 (venv `.venv`), GPU NVIDIA Quadro T1000 **4GB VRAM**.
- **Pi 5 (EDGE-PI5-DESK-01):** IP `192.168.1.21`, kiosk daemon port **8768**, cùng Wi-Fi với PC. Trạng thái lúc báo cáo: `kiosk_running=true`, `core_connected=true`, `embodiment_mode=ACTIVE`, `emergency_state=normal`.
- **Ollama daemon:** `127.0.0.1:11434` — ONLINE, 6 model local (qwen2.5:0.5b/1.5b/7b, bge-m3, …).
- **NetMind Gateway:** `https://stream-netmind.viettel.vn/aigw/ai/v1` — xác minh HTTP 200 cho GET /models và POST /chat/completions (cả stream & non-stream).

### 2.2. Cổng dịch vụ tại thời điểm báo cáo
| Cổng | Dịch vụ | Trạng thái |
|---|---|---|
| 8765 | Web UI hội thoại (run_web_server) | **200 OK** — đang chạy nền |
| 8766 | Executive Desk / Cockpit (run_executive_server) | **200 OK** — đang chạy nền |
| 8768 | Pi 5 Kiosk Daemon | **200 OK** |
| 11434 | Ollama | **OPEN** |

### 2.3. Git
- Commit mới nhất: **`d7be168`** (feat: Sprint 1 — GLM-5.3-Flash NetMind provider integration, approved D1-D7).
- Working tree: **8 file modified + nhiều tool/test mới** của Sprint 2 — tổng diff **+678/−35 dòng**, chưa commit (chi tiết mục 5.5).

---

## 3. KIẾN TRÚC HIỆN TẠI

```
┌─────────────────────────── PC CORE (Windows) ────────────────────────────┐
│  Web UI 8765 ── /api/chat/stream (SSE) ──┐                               │
│  Executive Desk 8766 ────────────────────┤                               │
│                                          ▼                               │
│  LLMProvider facade (provider.py)                                        │
│   ├─ NetMindProvider (cloud, fail-closed) ──► Viettel AI Gateway          │
│   │    ├─ GLM-5.3-Flash (fast + reasoning, streaming)                    │
│   │    └─ Qwen3.5-122B-A10B (deep reasoning, always-reasons)             │
│   ├─ OllamaClient (local: qwen 0.5b/1.5b/7b + bge-m3)                    │
│   └─ MockLLMProvider (chỉ khi caller bật fallback, có nhãn is_mock)      │
│  LLMRouter: fast/reasoning→GLM │ deep→Qwen3.5-122B │ offline→Qwen local  │
│  MouthSyncEngine (timeline 50ms) + TTSManager (edge-tts vi-VN-HoaiMy)    │
└──────────────────────────────┬───────────────────────────────────────────┘
                               │ Wi-Fi LAN (HTTP + HMAC)
┌──────────────────────────────▼───────────────────────────────────────────┐
│  RASPBERRY PI 5 (EDGE-PI5-DESK-01, port 8768)                            │
│  Kiosk Chromium: avatar_engine.js (Canvas 2.5D Model A) + kiosk.js        │
│  wake_engine.js (wake word "Hi Tony" + BARGE-IN Sprint 2)                 │
│  client_daemon.py: poll Core, nhận lệnh speak (audio+timeline),           │
│  mic/camera control, heartbeat, emergency stop                            │
└───────────────────────────────────────────────────────────────────────────┘
```

**Luồng hội thoại streaming (mới — Sprint 2):**
`User → /api/chat/stream → LLMRouter (cache NetMind 60s) → NetMindProvider.stream_chat (SSE) → delta forwards live → OutputGuardrails.sanitize → persist_chat_turn (SAU khi hoàn tất) → final event`
UI: `executive.js` render từng delta vào bubble, TTS chỉ phát sau khi nhận `final`. Fallback tự động về `/api/chat` non-streaming nếu SSE lỗi.

---

## 4. NETMIND GATEWAY — SỰ THẬC ĐÃ XÁC MINH

### 4.1. Danh mục model thực tế (GET /models, HTTP 200)
1. `zai-org/GLM-5.3-Flash` — **model chủ lực**, streaming OK, tiếng Việt tự nhiên
2. `Qwen/Qwen3.5-122B-A10B-FP8` — **deep reasoning**, luôn suy luận
3. `MiniMax/MiniMax-M3`, `MiniMax/MiniMax-M3-VIP`, `MiniMax/MiniMax-M2.7`, `Qwen/Qwen3.6-35B-A3B-FP8`

`zai-org/GLM-5.3` và `zai-org/GLM-5.3-FlashX` **KHÔNG có** trong catalog tài khoản → không cấu hình (từ chối ở tầng allowlist).

### 4.2. Số liệu đo được (25/10/2026, từ các probe trong `tools/`)
| Phép đo | Kết quả | Ghi chú |
|---|---|---|
| GLM non-stream wall time | **0.92–0.99s** (3 lần, ~80 completion tokens) | reasoning_effort="low" |
| GLM streaming TTFT (trực tiếp gateway) | **0.49–0.94s** | 23–39 deltas |
| GLM streaming TTFT (qua API server đầy đủ) | **1.53–1.78s** | đã tối ưu từ 7.42s nhờ cache catalog 60s |
| GLM reasoning mặc định (không param) | đốt **60/60 token reasoning, trả về RỖNG** | bắt buộc set `reasoning_effort:"low"` |
| Qwen3.5-122B với max_tokens=200/900 | **RỖNG** (toàn bộ budget bị reasoning nuốt) | param reasoning_effort không tác dụng |
| Qwen3.5-122B với max_tokens=2500 | **22.01s**, 2255 reasoning + 72 content, finish=stop | mặc định budget 2500 đã set trong provider |
| Gateway hiccup quan sát | 1 lần đo được 41.9s (dạng "sụt"}, các probe trước/sau đều ~1s | giới hạn bên ngoài, hệ thống chịu được nhờ streaming + timeout |

### 4.3. Bảo mật đã xác minh
- API key **chỉ đọc từ env** (`HERMES_CUSTOM_NETMIND_API_KEY`/`NETMIND_API_KEY`) tại thời điểm gọi; không lưu instance, không in/log/ghi file (assert trong 28 test).
- `NETMIND_EXTERNAL_DATA_ALLOWED` đã bật **vĩnh viễn** theo duyệt của anh: registry `HKCU\Environment` = `true` (xác minh bằng reg query). Provider vẫn fail-closed nếu flag false.
- Allowlist model nghiêm ngặt: chỉ nhận exact catalog ID; lỗi trả về có cấu trúc (`NETMIND_DISABLED`, `NO_API_KEY`, `MODEL_NOT_IN_NETMIND_CATALOG`, `TIMEOUT`, `HTTP_xxx`…).
- **Lưu ý cấu hình:** biến `NETMIND_DESKTOP_LLM_BASE_URL` trên máy trỏ tới endpoint LiteLLM khác trả về 404 cho GLM-5.3-Flash → provider cố chủ ý dùng default gateway; chỉ `NETMIND_BASE_URL` được phép override (comment chứng minh trong code).
- Audit log chỉ metadata (provider/model/latency/tokens), không bao giờ ghi prompt.

---

## 5. CHI TIẾT TỪNG SPRINT

### 5.1. Sprint 0 — Architecture Audit (commit `4d90465`)
Giải quyết 5 mâu thuẫn trong báo cáo cũ bằng đo thật:
1. **LLM hiệu năng:** Qwen2.5:7B thực tế cold 35.6s, 6 tok/s (GPU 4GB chỉ chứa 2.3/5.1GB → partial offload) — không phải 20.6s như báo cáo.
2. **Orchestration:** `PlanOrchestrator` ĐÃ nối `DurableTaskRegistry` (bằng chứng: 76 tasks thật trong `data/tasks.db`, cùng 316 episodes, 323 memories).
3. **Voice:** pipeline TTS/mouth-sync/wake-word có code + test đầy đủ trên PC; chỉ thiếu E2E phần cứng Pi (giữ BLOCKED trung thực).
4. **BGE-M3 9.64s** là cold-start; warm inference thực đo **0.39–0.47s**.
5. **Số test:** 484 PASS là đúng; "17 passed" chỉ là message cũ.

Báo cáo: `reports/QUAN_AI_BRAIN_SPRINT0_ARCHITECTURE_AUDIT.md` (+ 3 file JSON bằng chứng probe).

### 5.2. Sprint 1 — GLM-5.3-Flash Provider (commit `d7be168`, đã duyệt D1–D7)
- `NetMindProvider` fail-closed (cổng: policy → key → allowlist), retry có trần + backoff, TIMEOUT tách riêng CONNECTION_ERROR.
- D3 benchmark tiếng Việt (28 prompts/14 nhóm): **GLM 88.5% keyword accuracy / 1.33s avg / 1.99s p95** vs Qwen1.5b 69.2% / 1.76s / 3.48s → GLM làm model chính, Qwen local giữ cho offline/riêng tư.
- D5 GPU budget: keep-warm vật lý chỉ giữ `qwen2.5:0.5b` + bge-m3 trong VRAM 4GB (không ghim 7B).
- D4: handoff template thêm 3 trường trung thực (`test_suite_identity`, `report_freshness`, `verification_status`).
- D1: đính chính mốc sai trong báo cáo kiến trúc (chú thích §8.2 — bảo toàn nội dung gốc).
- Kết quả cuối: **502 passed, 1 skipped**; báo cáo `reports/QUAN_AI_BRAIN_GLM53_SPRINT1_COMPLETION.md`.

### 5.3. Sprint 2 — Streaming + Deep Reasoning + Barge-in (chưa commit)
**Phạm vi đã duyệt (3 mục anh trả lời "thực hiện cả 3"):** policy vĩnh viễn; Sprint 2 streaming/barge-in/persona; thêm tier reasoning Qwen3.5-122B.

**Backend:**
- `netmind_provider.py`: +`NETMIND_DEEP_REASONING_MODEL`, +`DEEP_REASONING_DEFAULT_MAX_TOKENS=2500`, skip `reasoning_effort` cho deep model, **`stream_chat()`** là generator sự kiện thật (meta/delta/final/error), `_iter_chat_stream_events()` parse SSE live, delta không bao giờ bị replay khi lỗi transport.
- `provider.py`: facade thêm `stream()`; local model re-emitted 1 delta + final (kể cả mock có nhãn warning rõ ràng).
- `router.py`: fast/reasoning → GLM; **tier mới `deep`** (patterns "phân tích chuyên sâu/nghiên cứu sâu/deep dive…", query >1200 ký tự, task_hint `deep_research`/`document_analysis`); offline → giữ tier, đổi sang `qwen2.5:7b` (`is_fallback=true`).
- `web/server.py`: **endpoint `/api/chat/stream` SSE** (route + handler 149 dòng); mock fallback chỉ khi caller bật `fallback=true` và luôn gắn `is_mock/warning`; persist sau khi stream xong; helper `_build_llm_provider()` + **cache catalog NetMind 60s** (giảm first-delta 7.4s → 1.5–1.8s); handler `/api/chat` cũng dùng chung router mới.

**Frontend & Edge:**
- `executive.js`: đọc SSE bằng ReadableStream, render delta live vào bubble, avatar SPEAKING khi delta đầu, **TTS chỉ phát sau final**, fallback tự động sang `/api/chat` khi stream lỗi.
- `kiosk.js`: hàm global `window.bargeInStopSpeaking()` — pause audio kiosk + cancel utterance + avatar về LISTENING + thông báo "Dạ, em dừng lại nghe Anh ạ."
- `wake_engine.js`: khi đang SPEAKING mà mic bắt được giọng → gọi barge-in thay vì bỏ qua; lệnh "dừng đọc/dừng nói" cũng qua cùng cơ chế.

**E2E đã chạy thật:**
- PC streaming (server thật 127.0.0.1, qua gateway): PASS — meta GLM → 21–28 deltas → final persist OK.
- **Pi 5 speak E2E (phần cứng thật): PASS** — TTS 41,040 bytes vi-VN-HoaiMyNeural → timeline 104 frames/4,735ms → đẩy sang kiosk 8768 → `avatar_state` chuyển SPEAKING rồi về IDLE (poll xác minh), transcript hiển thị đúng trên Pi.
- Sync asset: **53 file** đã đẩy sang `assets/avatar` của Pi (bao gồm mirror kiosk.js/wake_engine.js mới).

**Test:** 18 test NetMind (cập nhật catalog) + 10 test mới (`tests/test_sprint2_streaming.py`: 4 cổng stream + happy path + non-SSE + 4 test router) → **full suite 512 passed / 1 skipped / 73.9s, zero regression**.

### 5.4. Audit Avatar Model A — Digital Human V3 Giai đoạn A (CHƯA sửa mã)
**Hiện trạng kiểm kê (đọc code + asset, chưa diff):**
- Engine `avatar_engine.js` 1,011 dòng, Canvas 2.5D, render loop với 9 layer: portrait selection (9 ảnh master) → tóc bezier động → mắt (blink/gaze/squint/glint) → lông mày 4 tham số → miệng feathered ellipse → cyber lighting.
- **16 trạng thái** đầy đủ (IDLE→OFFLINE…) với aura color + tốc độ halo riêng — đúng đặc tả Master Prompt §VI.
- Chớp mắt: interval ngẫu nhiên 3.2–6.0s + 28% double-blink, easing sin — đạt yêu cầu §IV.1.
- Gaze: micro-saccade mỗi 2.2–5.2s; THINKING nhìn lên-trái; lerp 0.08/mũi — đạt khung §IV.2, chưa nối ngữ cảnh hội thoại thật.
- **Asset:** 44 file (PC web) / 47 (Pi); **8 hình miệng** (mouth_v2_rest/speaking/happy/open_o + bộ cũ) nhưng render chỉ dùng 3; 5 ảnh mắt; 9 portrait cảm xúc.
- **Lip-sync hiện tại = `APPROXIMATE_LIP_SYNC`**: `MouthSyncEngine` (Python, 199 dòng) sinh timeline 50ms từ văn bản — map nguyên âm tiếng Việt có dấu (o/ô/ơ→O, u/ư→U, e/ê→E, i/y→I, còn lại A) với bell-curve sin; ước lượng 140–300ms/từ + pause 250/450ms.
- **Gap chính tìm thấy:** `startSpeaking()` fallback trong avatar_engine dùng viseme NGẪU NHIÊN mỗi 90ms khi thiếu timeline → nguồn "miệng nhai giả"; duration timeline ước lượng từ số ký tự (±20% so với MP3 thật vì edge-tts không trả alignment).

**Phương án đề xuất (đang chờ duyệt, chưa làm):**
- **Giai đoạn B (đề xuất duyệt đầu tiên):** loại bỏ random-viseme fallback; mọi lời nói bắt buộc đi qua timeline; đo duration MP3 thật (decode header) và scale timeline theo; bổ sung mapping 2-3 hình miệng chưa dùng (open_o đã có, thêm nếu cần). Kết quả kỳ vọng: chuyển từ APPROXIMATE sang APPROXIMATE+ duration-aligned (đánh dấu trung thực, KHÔNG claim PHONEME_ALIGNED).
- **Giai đoạn C:** nối gaze/eyebrow với ngữ cảnh chat thật (THINKING khi router chọn deep, v.v.).
- **Không** chuyển 3D/blendshape — bằng chứng: engine hiện đạt thẩm mỹ Model A, Pi render mượt, đổi kiến trúc = rủi ro mất nhận diện + hiệu năng.

### 5.5. Thay đổi chưa commit (Sprint 2) — 8 file + tools
**Modified:** `edge_client/kiosk.js`, `edge_client/wake_engine.js`, `src/quan_ai_brain/llm/netmind_provider.py`, `src/quan_ai_brain/llm/provider.py`, `src/quan_ai_brain/llm/router.py`, `src/quan_ai_brain/web/server.py`, `src/quan_ai_brain/web/static/executive.js`, `tests/test_netmind_provider.py` (+678/−35).
**Mới:** `tests/test_sprint2_streaming.py` (10 test), `tools/sprint2_e2e_streaming_check.py`, `tools/sprint2_pi5_speak_e2e.py`, `tools/sprint2_qwen_reasoning_probe.py`, `tools/sprint2_streaming_probe.py`, `tools/tmp_debug_stream.py` + `tools/tmp_ttft_probe.py` (tạm, có thể xóa), `tools/sprint2_push_bargein_js.py` (chờ duyệt chạy).
**Quy trình đề xuất:** anh nghiệm thu → chạy `tools/sprint2_push_bargein_js.py` (sau duyệt) → commit Sprint 2 → xóa 2 tool tạm.

---

## 6. TRẠNG THÁI NĂNG LỰC (ma trận rút gọn)

| Năng lực | Trạng thái | Bằng chứng |
|---|---|---|
| Chat streaming GLM (PC, E2E thật) | **VERIFIED_E2E** | curl 8765 SSE + E2E script PASS |
| Deep reasoning Qwen3.5-122B | INTEGRATION_TESTED | probe 22s thành công; chưa qua UI thật |
| Router 3 tầng + fallback local | VERIFIED_E2E | 10 test + E2E meta tier |
| Policy fail-closed NetMind | VERIFIED_E2E | 18 test + E2E DISABLED_BY_POLICY |
| TTS tiếng Việt PC (HoaiMy) | VERIFIED_E2E | 41KB audio sinh thật |
| Speak → Pi 5 kiosk audio + avatar | **VERIFIED_E2E (phần cứng thật)** | sprint2_pi5_speak_e2e.py PASS |
| Barge-in trên Pi | UNIT_TESTED_ONLY (JS mới đã sync mirror, chưa load ở root) | node --check + sync 53 file |
| Wake word "Hi Tony" trên Pi | IMPLEMENTED_NOT_VERIFIED (phiên này) | đã có test PC; cần thử giọng thật |
| Lip-sync | **APPROXIMATE_LIP_SYNC** (trung thực) | timeline từ văn bản, không alignment |
| Voice pipeline E2E mic→ASR→LLM→TTS→loa Pi | NOT_RUN | cần phiên thử giọng thật |
| Camera/snapshot Pi | NOT_RUN (phiên này) | daemon có endpoint, chưa test |
| Deep memory/RAG | SPRINT 3 (chưa bắt đầu) | — |
| Orchestration E2E mới | UNIT_TESTED_ONLY | 76 tasks cũ trong DB, flow đã nối từ trước |

---

## 7. RỦI RO & VẬN ĐỀ MỞ

1. **Gateway hiccup:** quan sát 1 lần 41.9s (không repro được; các probe khác ~1s). Streaming + timeout + retry hiện có giúp chịu đựng, nhưng nên theo dõi; nếu tái diễn nhiều → cân nhắc circuit breaker (Sprint 6).
2. **JS barge-in chưa active trên kiosk:** trang kiosk đang load `kiosk.js` gốc (19,112 bytes) từ thư mục root daemon, bản mới (21,401 bytes) mới chỉ nằm ở `assets/avatar/` (mirror). Cần 1 lệnh upload duyệt trước (mục 9.1).
3. **Deep tier 22s** là chậm cho hội thoại tương tác — đúng thiết kế (chỉ dùng cho phân tích chuyên sâu), UI nên hiển thị trạng thái THINKING rõ trong lúc chờ.
4. **Cache catalog 60s:** nếu gateway đổi catalog trong 60s, routing có thể chọn model cũ — chấp nhận được vì generate() vẫn fail-closed có cấu trúc nếu model 404.
5. **2 tool tạm** (`tmp_debug_stream.py`, `tmp_ttft_probe.py`) cần xóa trước commit.
6. Server 8765/8766 đang chạy nền từ phiên làm việc — cần khởi động lại bằng tiến trình mới (đọc registry) để nhận policy vĩnh viễn trong production thực tế.

---

## 8. ROLLBACK

- Toàn bộ Sprint 2 nằm trong working tree **chưa commit** → rollback = `git checkout -- <file>` (hoặc `git stash`) — không ảnh hưởng commit `d7be168`.
- Pi 5: bản JS trên root chưa bị ghi đè (lệnh upload bị chặn) → kiosk hiện trạng "trước Sprint 2" nguyên vẹn; mirror ở assets/avatar có thể xóa qua `/api/kiosk/files/delete` nếu muốn.
- Policy registry: `setx NETMIND_EXTERNAL_DATA_ALLOWED false` để quay lại fail-closed mặc định.
- Không có migration DB trong Sprint 2 → không cần rollback dữ liệu.

---

## 9. QUYẾT ĐỊNH CẦN ANH QUÂN PHÊ DUYỆT

### 9.1. Đẩy 2 file JS vào root daemon Pi (bước chót Sprint 2)
Chạy `tools/sprint2_push_bargein_js.py` (đã viết sẵn, gửi base64 qua `/api/kiosk/files/upload` — đúng endpoint daemon tự dùng) → rồi reload UI kiosk. Sau đó: nói "dừng đọc" hoặc lên tiếng khi TTS đang phát để nghiệm thu barge-in thật.
- [ ] DUYỆT / [ ] KHÔNG

### 9.2. Duyệt diff Avatar V3 Giai đoạn B (mouth sync)
Nội dung: bỏ random-viseme fallback; timeline-only; đo duration MP3 thật để scale timeline; mở rộng mapping hình miệng; thêm test pytest cho duration alignment. Chỉ đụng `avatar_engine.js`, `mouth_sync.py`, và test liên quan — không đổi nhận diện Model A.
- [ ] DUYỆT / [ ] KHÔNG

### 9.3. (Tùy chọn) Commit Sprint 2
Sau khi 9.1 xong: commit với message "feat: Sprint 2 — GLM streaming + deep reasoning tier + Pi barge-in (owner-approved)".
- [ ] DUYỆT / [ ] CHƯA

---

## 10. LỘ TRÌNH TIẾP THEO

1. **Avatar V3 Giai đoạn B→G** (nếu 9.2 duyệt): mouth sync → eyes/expression polish → head motion → PC/Pi performance → clip kiểm thử + đo sai lệch audio/animation.
2. **Sprint 3 — Deep Knowledge & Memory:** tối ưu retrieval BGE-M3 (warm đã 0.4s), knowledge ingestion có provenance, trí nhớ nhiệm vụ, phát hiện mâu thuẫn.
3. **Sprint 4 — Digital Employee Orchestration:** vòng đời nhiệm vụ E2E với governance giữ nguyên an toàn.
4. **Voice E2E trên Pi:** wake word thật + mic→ASR→GLM streaming→TTS→loa, đo end-to-end latency từng chặng.
5. **Sprint 6 — Stability:** circuit breaker cho gateway, recovery, benchmark tái lập.

---

## PHỤ LỤC A — FILE BY-FILE CỦA SPRINT 2

| File | Thay đổi chính |
|---|---|
| `llm/netmind_provider.py` | deep model + budget 2500 + stream_chat generator + _iter_chat_stream_events + base_url note |
| `llm/provider.py` | stream() facade + export NETMIND_DEEP_REASONING_MODEL |
| `llm/router.py` | GLM defaults + tier deep + LOCAL_REASONING_FALLBACK_MODEL |
| `web/server.py` | /api/chat/stream + _build_llm_provider + cache 60s + router mới ở cả 2 handler |
| `web/static/executive.js` | SSE reader + live render + fallback + TTS-after-final |
| `edge_client/kiosk.js` | window.bargeInStopSpeaking() |
| `edge_client/wake_engine.js` | barge-in hook + lệnh dừng đọc qua global |
| `tests/test_netmind_provider.py` | catalog 2 model |
| `tests/test_sprint2_streaming.py` | 10 test mới (stream gates/happy/deep/router) |

## PHỤ LỤC B — LỆNH NGHIỆM THU NHANH (copy-paste)

```bash
# 1. Full test suite
./.venv/Scripts/python.exe -m pytest -q tests

# 2. Streaming E2E qua server thật
NETMIND_EXTERNAL_DATA_ALLOWED=true ./.venv/Scripts/python.exe tools/sprint2_e2e_streaming_check.py

# 3. Pi 5 speak E2E (phần cứng thật)
./.venv/Scripts/python.exe tools/sprint2_pi5_speak_e2e.py

# 4. Stream thủ công qua UI server đang chạy
curl -N -X POST http://127.0.0.1:8765/api/chat/stream -H "Content-Type: application/json" \
  -d '{"query":"Cho biet ban la ai","session_id":"manual_test"}'
```

---
*Hết báo cáo. Mọi số liệu trong tài liệu này là kết quả đo thật trong phiên làm việc 25/10/2026; các phần chưa xác minh được ghi rõ trạng thái, không có mục nào bị tô mới.*
