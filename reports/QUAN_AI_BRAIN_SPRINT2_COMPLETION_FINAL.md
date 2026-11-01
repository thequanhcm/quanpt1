# SPRINT 2 — HOÀN THÀNH & NGHIỆM THU

**Ngày hoàn thành:** 25/10/2026  
**Commit:** `b91512e` (Sprint 2) + `0356ccb` (docs update)  
**Chủ sở hữu phê duyệt:** Anh Quân — `Quanpt1`  
**Test suite:** 512 passed, 1 skipped, 0 failed (74.69s)

---

## I. TỔNG QUAN

Sprint 2 đã hoàn thành 4 hạng mục chính:
1. **Streaming GLM-5.3-Flash** — SSE live delta, first-delta 1.5–1.8s
2. **Deep reasoning tier** — Qwen3.5-122B với 2500 tokens
3. **Barge-in trên Pi 5** — Dừng TTS khi nghe giọng người
4. **Avatar V3 Giai đoạn B** — Loại bỏ random-viseme, bell-curve mượt, MP3 duration alignment

Tất cả đã được **deploy lên Pi 5 thật** (192.168.1.21:8768), test PASS, chờ nghiệm thu live từ anh Quân.

---

## II. CHI TIẾT HẠNG MỤC

### 1. Streaming GLM-5.3-Flash

**Backend:**
- `netmind_provider.py::stream_chat()` — Generator SSE thật, yield meta/delta/final/error
- `_iter_chat_stream_events()` — Parse SSE live, không buffer toàn bộ
- Delta không bao giờ bị replay khi lỗi transport
- Cache catalog NetMind 60s → first-delta từ 7.4s → **1.5–1.8s**

**Frontend:**
- `executive.js` — ReadableStream đọc SSE, render live vào bubble
- TTS chỉ phát sau khi nhận `final` event
- Fallback tự động sang `/api/chat` non-streaming khi SSE lỗi

**Bằng chứng:**
- `tools/sprint2_e2e_streaming_check.py` — E2E PC streaming qua gateway thật: 21–28 deltas live, persist đúng
- `tools/tmp_ttft_probe.py` — TTFT gateway trực tiếp: 0.49–0.94s
- Test suite: 4 test streaming + 2 test router = 6/6 PASS

### 2. Deep Reasoning Tier

**Cấu hình:**
- `Qwen/Qwen3.5-122B-A10B-FP8` vào allowlist
- `max_tokens=2500` mặc định (đủ cho 2255 reasoning + 72 content)
- Router nhận diện: "phân tích chuyên sâu/nghiên cứu sâu/deep dive…" + query >1200 ký tự → tier deep

**Probe kết quả:**
- `tools/sprint2_qwen_reasoning_probe.py` — 22.01s total, 2255 reasoning tokens, 72 content tokens, finish=stop
- Phù hợp cho phân tích tài liệu, không dùng cho hội thoại tương tác

### 3. Barge-in trên Pi 5

**Thay đổi:**
- `kiosk.js` — `window.bargeInStopSpeaking()`: pause audio + cancel utterance + avatar→LISTENING + thông báo "Dạ, em dừng lại nghe Anh ạ."
- `wake_engine.js` — Khi đang SPEAKING mà mic bắt giọng → gọi barge-in

**Deploy:**
- `tools/sprint2_push_bargein_js.py` — Upload 2 file qua `/api/kiosk/files/upload`
- Reload UI thành công
- **Kiểm tra:** kiosk.js 21,401 bytes, wake_engine.js 12,376 bytes — MATCH trên Pi
- kiosk_running=True, avatar=IDLE sau reload

**Chờ nghiệm thu:** Anh test nói "dừng đọc" khi TTS đang phát

### 4. Avatar V3 Giai đoạn B — Mouth Sync Timeline-Only + Exact Duration

**Vấn đề cũ:**
- `startSpeaking()` fallback dùng `Math.random() * 0.55` mỗi 90ms → "miệng nhai" giả tạo

**Giải pháp:**
- Loại bỏ random-viseme → dùng bell-curve `0.35 * sin(π*phase)`
- Thêm `MouthSyncEngine.measure_mp3_duration_ms()` — Parse ID3v2 + MPEG frame headers
- Timeline scaling theo `target_duration_ms` từ MP3 thật

**Test:**
- `tools/avatar_v3_giai_doan_b_tests.py` — 6/6 PASS:
  - Random-viseme removed ✓
  - MP3 duration measurement ✓
  - Timeline scaling ✓
  - Vietnamese viseme mapping ✓
  - Bell-curve envelope ✓
  - Punctuation pauses ✓

**Deploy:**
- `avatar_engine.js` 42,005 bytes — MATCH trên Pi
- Reload UI thành công

**Chờ nghiệm thu:** Anh chat thử, quan sát miệng mượt, không "nhai"

---

## III. TEST RESULTS

| Test suite | Kết quả | Thời gian |
|---|---|---|
| **Full regression** | 512 passed, 1 skipped, 0 failed | 74.69s |
| **Sprint 2 streaming** | 28 passed | 8.04s |
| **Avatar V3 Phase B** | 6 passed | <1s |
| **NetMind provider** | 18 passed | 7.17s |

**Zero regressions** so với Sprint 1 (502 tests).

**Skip duy nhất:** `tests/test_vietnamese_tts.py:266` — BLOCKED: Voice E2E trên Pi 5 chưa chạy trong phiên tự động (trung thực).

---

## IV. FILE CHANGED

| File | Thay đổi chính |
|---|---|
| `llm/netmind_provider.py` | +stream_chat() +_iter_chat_stream_events +deep model +budget 2500 |
| `llm/provider.py` | +stream() facade +export NETMIND_DEEP_REASONING_MODEL |
| `llm/router.py` | GLM defaults +tier deep +LOCAL_REASONING_FALLBACK_MODEL |
| `web/server.py` | /api/chat/stream +_build_llm_provider +cache 60s |
| `web/static/executive.js` | SSE reader +live render +fallback +TTS-after-final |
| `edge_client/kiosk.js` | window.bargeInStopSpeaking() |
| `edge_client/wake_engine.js` | barge-in hook +lệnh dừng đọc |
| `edge_client/avatar_engine.js` | **Phase B:** loại bỏ random-viseme, bell-curve envelope |
| `src/quan_ai_brain/voice/mouth_sync.py` | +measure_mp3_duration_ms() +docstring Phase B |
| `tests/test_netmind_provider.py` | catalog 2 model |
| `tests/test_sprint2_streaming.py` | 10 test mới (stream gates/happy/deep/router) |
| `tools/avatar_v3_giai_doan_b_tests.py` | MỚI — 6 tests Phase B |
| `tools/sprint2_push_bargein_js.py` | MỚI — push JS lên Pi |

**Diff tổng:** +1,857 insertions, −37 deletions (19 files)

---

## V. DEPLOYMENT STATUS

| Thành phần | Pi 5 IP | Local size | Pi size | Trạng thái |
|---|---|---|---|---|
| kiosk.js (barge-in) | 192.168.1.21:8768 | 21,401 bytes | 21,401 bytes | ✅ MATCH |
| wake_engine.js (barge-in) | 192.168.1.21:8768 | 12,376 bytes | 12,376 bytes | ✅ MATCH |
| avatar_engine.js (Phase B) | 192.168.1.21:8768 | 42,005 bytes | 42,005 bytes | ✅ MATCH |

**Reload UI:** Thành công — kiosk_running=True, avatar=IDLE

---

## VI. CHỜ NGHIỆM THU LIVE (Anh Quân)

### 1. Barge-in
- **Bước:** Mở `http://127.0.0.1:8765/` → Chat để TTS phát → Nói "dừng đọc" khi đang phát
- **Kỳ vọng:** Audio dừng ngay, avatar về LISTENING, có thông báo
- **Trạng thái:** ⏳ Chờ anh test

### 2. Avatar V3 Phase B
- **Bước:** Chat bình thường, quan sát miệng
- **Kỳ vọng:** Không còn "nhai", chuyển động mượt theo bell-curve
- **Trạng thái:** ⏳ Chờ anh test

### 3. Voice E2E (Sprint 3 prep)
- **Bước:** "Hi Tony" → nói câu tiếng Việt → nghe phản hồi
- **Kỳ vọng:** Wake word → ASR → LLM → TTS → loa Pi → avatar đồng bộ
- **Trạng thái:** ⏳ BLOCKED — cần test giọng thật

---

## VII. LỘ TRÌNH TIẾP THEO

### Sprint 3 — Deep Knowledge & Memory (chờ anh duyệt)
1. Audit module hiện có: `SessionMemoryManager`, `SQLiteStore`, `CognitiveRetriever`, BGE-M3
2. Knowledge ingestion với provenance (source, version, timestamp, verification state)
3. Benchmark retrieval: cold/warm, batch, incremental indexing
4. Deep memory cho nhân sự số: facts, evidence, inferences, decisions, procedures
5. Test: ghi/đọc, truy xuất ngữ cảnh, mâu thuẫn, khôi phục sau restart

### Avatar V3 Giai đoạn C (sau Phase B ổn định)
1. Polish gaze transition + eyebrow phối hợp ngữ cảnh
2. Head motion vi mô tự nhiên
3. Biểu cảm đồng bộ trạng thái (THINKING, EMPATHIC, WARNING)
4. Đo sai lệch audio/animation

### Voice E2E hoàn chỉnh
1. Wake word "Hi Tony" thật trên Pi
2. Mic → ASR → Core → TTS → loa (đo end-to-end latency)
3. Barge-in nghiệm thu
4. Mất kết nối + khôi phục

---

## VIII. ROLLBACK PLAN

Nếu nghiệm thu thất bại:
1. **Barge-in:** Upload lại bản cũ qua `/api/kiosk/files/upload` + reload_ui
2. **Avatar Phase B:** Upload lại `avatar_engine.js` bản trước (đã backup trong `assets/avatar/`)
3. **Streaming:** Fallback tự động sang `/api/chat` non-streaming khi lỗi
4. **Git:** Commit Sprint 2 đã neo — rollback = checkout commit `b91512e^`

---

## IX. BẰNG CHỨNG

- `reports/SPRINT2_COMPLETION_SUMMARY.md` — Tóm tắt Sprint 2
- `bao cao xay dung he thong/BAO_CAO_HE_THONG_TONG_HOP_20261025.md` — Báo cáo hệ thống chi tiết
- `tools/sprint2_e2e_streaming_check.py` — E2E streaming script
- `tools/sprint2_pi5_speak_e2e.py` — E2E Pi 5 speak script
- `tools/avatar_v3_giai_doan_b_tests.py` — 6 tests Phase B
- `tests/test_sprint2_streaming.py` — 10 test streaming/router
- `reports/SPRINT0_NETMIND_CATALOG.json` — Catalog NetMind
- `reports/SPRINT1_VIETNAMESE_BENCHMARK.json` — Benchmark tiếng Việt

---

## X. KẾT LUẬN

Sprint 2 đã hoàn thành với:
- ✅ 4 hạng mục chính triển khai
- ✅ 512 tests PASS, zero regressions
- ✅ Deploy lên Pi 5 thật, kiosk_running=True
- ✅ Chờ nghiệm thu live từ anh Quân

**Bước tiếp theo:** Anh test barge-in + Avatar Phase B → báo kết quả → Sprint 3 Deep Knowledge & Memory.

---
*Hết báo cáo Sprint 2.*