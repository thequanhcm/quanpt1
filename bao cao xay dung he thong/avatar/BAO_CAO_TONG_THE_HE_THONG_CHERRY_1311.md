# BÁO CÁO TỔNG THỂ HỆ THỐNG CHERRY — TỪ CẤU HÌNH ĐẾN CHỨC NĂNG

**Ngày:** 13/11/2026 (cập nhật 22:45) · **Người thực hiện:** TONY (Digital Executive Assistant)
**Đối tượng:** toàn bộ hệ thống QUAN AI BRAIN / CHERRY — PC Core (QUANPT, 192.168.1.24) + Edge Pi5 (192.168.1.21)
**Đặc tả số liệu:** mọi con số trong báo cáo này đều đo/thu thập thật trong phiên làm việc 13/11; mục chưa kiểm chứng được ghi rõ INCONCLUSIVE / STALE.

---

## 1. TÓM TẮT ĐIỀU HÀNH

| Hạng mục | Trạng thái | Bằng chứng |
|---|---|---|
| PC Core server (8765/8766) | 🟢 SỐNG | health 200/200, uptime liên tục qua watchdog |
| Pi5 hiển thị hình thể | 🟢 ACTIVE | kiosk_running=True, ổn định T+3', heartbeat 1.06s |
| LLM cloud động | 🟢 SỐNG | GLM-5.3-Flash 2.0–3.2s/câu; failover model rút tự chuyển 1.71s |
| Voice pipeline | 🟢 SỐNG | voice/interact 0.03s trả reply; audio tới Pi5, avatar SPEAKING |
| Avatar cảm xúc | 🟢 SỐNG | dashboard 22 states + toast; kiosk 19 states; 5/5 state thử OK |
| 24/7 watchdog + backup | 🟢 SỐNG | watchdog PID 11732 → server tự respawn; backup 2AM hằng ngày |
| Bảo mật (shield, HMAC, approval) | 🟢 SỐNG | pytest security pass; EN BLOCK 70 / VN SANITIZE 40 |
| Code quality | 🟢 184/184 | pytest focused voice+LLM+edge+shield sau audit vệ sinh |

Tốc độ phản hồi (điểm nóng sprint 13/11): **18.37s → 0.00–0.02s** cho reply text; **6–18s → 1.69s** cho audio lần đầu, **0.00s** khi cache hit.

---

## 2. KIẾN TRÚC TỔNG THỂ

```
┌──────────────────────── PC CORE (QUANPT — Win10, Quadro T1000 4GB) ───────────────────────┐
│  watchdog.py (PID 11732) ── tự respawn ── start_dual_servers → server.py                   │
│  ├─ Port 8765: web server chính (dashboard owner)                                          │
│  ├─ Port 8766: executive API + voice + LLM + netchat + edge gateway                        │
│  ├─ LLM: NetMind gateway (cloud) + Ollama local (fallback) — router động                   │
│  ├─ TTS: piper local (warm-up RAM) + Edge-TTS cloud (breaker 403)                          │
│  ├─ netchat_auto_responder ×2 (bot_tony DM chủ, 2-way token)                               │
│  ├─ learning_daemon (tự học, liveness = brain.db mtime) + backup 2AM                       │
│  └─ data/: brain.db 105MB, tasks.db 579 durable tasks, knowledge_db (chroma 55MB)          │
└──────────────────────────────────── WiFi LAN (ping <50ms) ────────────────────────────────┘
┌──────────────────── Pi5 EDGE (Desk 7" DSI + HDMI mirror Samsung 4K) ──────────────────────┐
│  main.py client_daemon (PID 259094) — poll/heartbeat core, HMAC signed                     │
│  ├─ Port 8768: kiosk daemon (kiosk status/control, audio, camera, files)                   │
│  ├─ Chromium kiosk 800×480 DSI (SwiftShader, labwc/Wayland) + HDMI-A-2 mirror 4K           │
│  ├─ kiosk.js 849 dòng: avatar 19 states, mouth-sync bell-curve, overlay effects            │
│  ├─ wake_word_service 379 dòng: "Cherry ơi" 3 lớp (HP 180Hz + noise-floor + SNR gate)      │
│  └─ audio: SRS-XB33 BT (timer 30s tự connect) + loa HDMI; screen idle-sleep 300s           │
└───────────────────────────────────────────────────────────────────────────────────────────┘
```

**Quy mô code (đếm thật `wc -l`):** server.py 6.897 · client_daemon.py 3.077 · executive.js 4.877 · avatar_engine.js 1.015 · netchat_auto_responder.py 1.536 · tts_config.py 834 · kiosk.js 849 · watchdog.py 740 · netmind_provider.py 765 · wake_word_service.py 379 · llm/router.py 199 — **tổng 21.168 dòng** cho 11 file lõi. Toàn repo: **2.046 file git-tracked, 214 file test**, ~39 package con trong `src/quan_ai_brain/`.

---

## 3. CẤU HÌNH HỆ THỐNG

### 3.1 LLM — router động đa model (cấu hình mới 14/11 00:30)
- Gateway: `https://stream-netmind.viettel.vn/aigw/ai/v1` (key từ env, không hard-code)
- Model mặc định: `zai-org/GLM-5.3-Flash` (chat nhanh) · Deep reasoning: `Qwen/Qwen3.5-122B-A10B-FP8` (~22s, luôn-reason)
- **Catalog ĐỘNG TTL 300s:** GET `/models` mỗi 5 phút → cho phép mọi model cloud đang được serve (catalog ĐỔI THEO NGÀY: MiniMax-M2.7 đã rút 13/11, Qwen3.6-35B đã vào)
- **Rank theo tốc độ đo thật:** GLM-5.3-Flash 0.34s < MiniMax-M3 0.61s < Qwen3.6-35B 2.09s
- **Failover 3 lớp:** model chết/không-catalog → model cloud nhanh nhất còn sống (CLOUD_SPEED_PRIORITY) → mới rớt Ollama local. Fast-path tránh probe `/models` mỗi request.

### 3.2 TTS — linh động local-first (cấu hình mới 13/11 22:20)
- **piper local** (ưu tiên, warm-up 2 model vào RAM lúc server start): `vi_VN-vais1000-medium.onnx` 63MB + `vi_VN-vivos-x_low.onnx` 27,8MB — synth thật **111–115ms**, warm-load **60–115ms** (cold 4,4–11,5s trước khi có warm-up)
- **Edge-TTS cloud** (vi-VN-HoaiMyNeural…): **circuit breaker 403** — Edge lỗi InvalidResponse ≥2 lần liên tiếp → skip 10 phút, map giọng Edge → piper cùng giới tính; Edge sống lại thì tự dùng
- Route: voice `piper-*` → piper; `vi-VN-*` → Edge cloud (khi breaker mở)

### 3.3 Voice pipeline — reply-first streaming
- `POST /api/voice/interact` trả **NGAY** `{tts_mode:"background", has_audio:false}` (đo 0.03s) → kiosk giữ THINKING
- TTS chạy background thread → xong tự POST `/api/kiosk/control {speak}` xuống Pi5 (daemon đặt `pending_audio_base64`, kiosk poll 1s phát) — đo sống: audio tới sau ~1,69s lần đầu, 0,00s khi cache
- Wake word: HP 180Hz + NoiseFloorEstimator (init 150) + gate SNR 2.2 + AGC 24x — 12/12 test; giới hạn vật lý: mic Jieli đặt xa SNR≈0dB (cần ≤50cm)

### 3.4 Kiosk hiển thị Pi5
- Chromium `--kiosk --window-size=800,480` (màn DSI 800×480), `--ozone-platform=x11 --use-angle=swiftshader --disable-gpu-compositing` (Wayland renderer treo trên Pi5 → X11), `--disable-features=Translate`, lang=vi
- HDMI mirror riêng: profile `~/.config/chromium-hdmi-mirror`, Samsung 3840×2160, `--window-position=800,0`
- **Idle-sleep 300s** (client_daemon.py:987): im lặng 5 phút → tắt kiosk + tắt đèn nền (by design, tiết kiệm màn 7"); lệnh từ PC hoặc chạm màn → bật lại ngay
- Avatar engine kiosk: `691886df`, cache `?v=cherry_07nov_r1`, 19 states, canvas 720×720, mouth-sync bell-curve (Model A)

### 3.5 Dashboard PC (8766/?tab=…)
- Engine `61dd807d`, cache `?v=emo_1311_r5`, **22 states** (14 gốc + 8 mới 13/11) + 11 tông giọng; toast thay toàn bộ 34 `alert()` (đã xác nhận alert=0); `window.setAvatarState` + `showExecToast` exposed
- 11 tab pane chính (persona, consultation, learning, orchestration, dialogue, netchat, edge-sync, pi5-embodiment, workbench, deep-memory, intelligence) + telemetry pills ("NetMind Cloud (GLM-5…)", "Trí Nhớ: 500 mục"…)

### 3.6 24/7 Ops
- Watchdog tự respawn ≤60s khi server chết (đã chứng minh 2 lần 13/11: kill PID cũ → respawn với code mới)
- Backup hằng ngày 2AM + backup pre-migration; learning daemon single-instance (liveness = brain.db mtime)
- Nguồn: AC=0 (display-off 600s giữ), DC=240s — pin không cạn khi cúp điện

---

## 4. CHỨC NĂNG CHI TIẾT (theo nhóm)

### 4.1 Chat + LLM động
- `POST /api/chat`: intent → role orchestrator → grounding (brain.db 500 mục nhớ gần nhất) → LLM → reply + provenance + `elapsed_ms`
- E2E sống 13/11: 3 câu thường 2.01–3.24s (GLM-5.3-Flash, "10 + 5 = 15 ạ." đúng); model đã rút (M2.7) → **tự chuyển GLM 1.71s** — router không cần can thiệp tay
- Qwen3.6-35B (model mới catalog) hoạt động qua /api/chat (trước đây bị MODEL_NOT_IN_CATALOG)

### 4.2 Voice + wake word
- Vòng đầy đủ: wake "Cherry ơi" (3 lớp chống nhiễu) → STT → chat → TTS piper/Edge → phát loa XB33/HDMI → avatar mouth-sync
- Voice record intent + music catch-all + transfer 2-way (PR #27) — pytest pass
- Kỹ thuật mới: reply text về NGAY, âm thanh theo sau (tts_mode=background) — tương thích ngược kiosk cũ (Pi5 vẫn chạy bản `9c8f6639`, audio tới sau ~1s)

### 4.3 Avatar hình thể
- **4 bản engine có kiểm soát:** backup 25/10 `2a453a11` (restore 8:00 4/4 md5) · Pi5 `691886df` · dashboard `61dd807d` (mới nhất, 22 states) · body_soft `3956a56f` (tạm dừng an toàn 3 nơi: stash + Pi5 `.bak_body_sync_1311` + `backups/avatar_body_sync_1311/`)
- Assets: PC 44 / backup 45 / Pi5 60 file; engine demo + test 6/6; **lỗi gốc đã ghi nhận:** `avatar_v2_surprised.png` md5 `c572cbbb` TRÙNG portrait (ảnh cười) — engine sẵn sàng, chỉ chờ thay ảnh
- Emotion: bell-curve khẩu hình theo tông giọng; overlay effects (canvas z-index 1 + alpha tăng — PR #27)

### 4.4 NetChat / DM bot_tony
- Kênh owner `mwp3nk…k6jr`, bot nhận DM duy nhất; responder 2 process pythonw, poll nhanh
- **DM 2 bước token:** lệnh nhạy cảm → `CONFIRM-REQUIRED:<token>` → chỉ thực thi khi owner gõ lại `--confirmed <token>`
- **Input shield** (sprint AGENTIC-SEC-1, 13/11): injection EN "Ignore all previous instructions…" → **BLOCK score 70**, không gọi LLM; VN có "trước đó" + path `.env` → **SANITIZE 40** + redact `[PROTECTED_SYSTEM_PATH]`; gap nhỏ: VN thiếu từ "trước" → ALLOW (lớp NEVER vẫn chặn rm -rf) — đã ghi gap-analysis, đề xuất sprint sau

### 4.5 File transfer 2 chiều + đồng bộ Pi5
- PC ↔ Pi5: initiate/chunk/ack; whitelist ext + chặn traversal `../`; barrier nhạy cảm 403 TRƯỚC whitelist 400; PC fallback local khi Pi5 offline
- ⚠️ Bug đã biết: `/transfer/chunk` sai signature `data_bytes` vs `data_b64` → file >15MB hỏng — chờ sprint sửa
- ⚠️ sync-all copy từ working tree → chỉ bấm khi working tree = bản đã duyệt (hiện PR #28 chưa merge)

### 4.6 Camera + hiển thị mở rộng
- Camera Pi5 MJPEG (lock + TTL cache + privacy), camera tab test pass; HDMI mirror 4K cho màn lớn
- Overlay effects: confetti/sparkle trên canvas kiosk (cylinder alpha tăng)

### 4.7 Bảo mật nhiều lớp
- `input_shield.py` 27/27 test + `untrusted_label` (4 điểm gọi trong server.py) + `trifecta_guard` (R3 FORCE PROPOSE) + `audit_sources` (record_shield_event fail-open)
- HMAC signed headers mỗi request Pi5→PC, nonce chống replay; approval card qua DB (`tasks.db` 579 tasks) — R4 chỉ chạy khi owner approve thật
- Autonomous Mode 3 lớp: AUTO / PROPOSE / NEVER (hard-block: DROP/DELETE DB, rmtree, router mạng, executive.js, secrets)

### 4.8 24/7 + tự học
- Watchdog + health monitor + backup 2AM + learning daemon (brain.db mtime = liveness) + morning report
- Learning quarantined: kiến thức mới phải qua evidence + regression + owner-approval mới vào production (không tự thay đổi production)

---

## 5. HIỆU NĂNG ĐO ĐƯỢC (trước → sau sprint tốc độ 13/11)

| Chỉ số | Trước | Sau | Cách đo |
|---|---|---|---|
| Reply text (voice) | 18.37s | **0.00–0.02s** | E2E sống /api/voice/interact |
| Audio tới loa lần đầu | 6–18s | **1.69s** | E2E + kiosk speak |
| Audio cache hit | 6–18s | **0.00s** | E2E |
| TTS mỗi câu mới (Edge 403) | ~6.2s lãng phí ×2 attempt | **0s** (breaker skip) | bench tmp_bench 13/11 |
| piper synth | cold 4.38–11.51s | **warm 60–115ms** (load) / 111–115ms (synth) | bench ONNX thật |
| LLM chat (cloud) | — | **GLM 0.34s / M3 0.61s / Qwen3.6 2.09s** (probe 1 câu); 2.0–3.2s full pipeline có grounding | benchmark 13/11 + E2E |
| Deep reasoning | — | ~22s (Qwen3.5-122B, luôn-reason) | benchmark |
| Wake word | ~5s | giữ nguyên (3 lớp) | test 12/12 |
| daemon→PC heartbeat | — | <50ms; last_heartbeat 1.06s | kiosk status |

---

## 6. KẾT QUẢ TEST (13/11)

### 6.1 pytest (focused, venv BRAIN — full suite >7' đặc trưng)
| Nhóm | File | Kết quả |
|---|---|---|
| Voice/LLM/TTS | v36_tts, vietnamese_tts, voice_api_endpoints, voice_first_pipeline, llm_provider, netmind_provider | **93 passed, 1 skipped** (skip = cần phần cứng Pi5) |
| Edge/hiển thị/shield | kiosk_overlay, transfer_2way, wake_noise, agentic_sec_shield, avatar_expression_sync, edge_client, wifi_protocol | **91 passed** |
| **Tổng sau audit vệ sinh** | 13 file | **184 passed / 0 fail** |

Pre-existing FAIL (giữ nguyên, không thuộc sprint này): test_cognitive_loop, test_cpsl_runner::test_run_e2e_mock, test_avatar_body_arms (12).

### 6.2 E2E sống không mock (production server)
- Health 8765/8766 = 200/200 · chat ×3 đúng nội dung · failover model rút tự chuyển · voice/interact 0.03s · avatar SPEAKING khi phát audio · edge heartbeat 1.06s
- Dashboard qua browser thật (CDP Edge): setAvatarState 5/5, toast 1/1, alert=0, 11 tab pane, pills đúng ("NetMind Cloud (GLM-5…)", "Trí Nhớ: 500 mục")
- Pi5 kiosk: ACTIVE ổn định (xem §7 root cause fix)

### 6.3 Điểm INCONCLUSIVE (trung thực)
- Screenshot màn Pi5 qua SSH: grim/wlopm không thấy wl_output (session labwc không expose qua SSH) → bằng chứng hiển thị Pi5 = API + process, **chưa có ảnh pixel**
- DM live thật: chưa test (policy mock) — wiring shield vào responder có, hiệu lực từ DM kế tiếp

---

## 7. AUDIT VỆ SINH 13/11 (đã thực hiện trong phiên này)

1. **Cách ly 9 file rác** → `quarantine_audit_20261113/` (MANIFEST.json + md5, KHÔNG xóa): 3 tmp test media, tmp_audit_merge.json, experience.db (0 byte orphan), e1.mp3 (0 byte), WAL mồ côi, 2 script test tạm
2. **Rotate 3 log khổng lồ 77,3MB** (dual_servers_watchdog 55,6MB + 2 learning daemon) → `logs/archive/20261113/` rồi truncate live — giảm write-path; health 200 sau rotate
3. **Giữ đúng thứ cần giữ:** `__pycache__` (1.637 file — tăng tốc import), `edge_devices.db` 0 byte (server.py:287 dùng thật), dữ liệu owner trong `kho_tai_lieu`/`Skill` (không đụng)
4. **Fix lỗi hiển thị Pi5:** kiosk chết từ 18:38 — root cause **SingletonLock profile mặc định chỉ vào zombie chromium** (daemon không wait() con) → chromium mới tự thoát ngay → vòng lặp chết. Fix: verify chủ lock là zombie → xóa 3 Singleton* → POST launch_kiosk → **ACTIVE ổn định T+8s/T+60s/T+3'**
5. Phân định thêm: kiosk tắt sau đó ~22:44 là **idle-sleep 300s by design** (client_daemon.py:987) — khác crash 18:38 (crash KHÔNG tự bật lại được)

**Chờ owner duyệt xóa (đã cách ly/liệt kê, không tự xóa):** `BRAIN_0/` 7,5GB · `backups/knowledge_db_broken_20261031/` 540MB · `data/pre_rehabilitate_20261112_133541.db` 103MB · ~10 bản backup brain.db 103MB/bản · `.bak` DWG/xlsx trong kho_tai_lieu (~150MB, dữ liệu owner) · `backups/rename_cherry_20261106/` + `logs/dm_token2-5.txt`

---

## 8. TRẠNG THÁI MÃ NGUỒN + VERSIONING

- **Branch hiện tại:** `feature/sprint-1311-latency-llm-router-avatar-emotion` — commit `6ed24a0` (18 files +1435 −79): tối ưu tốc độ phản hồi + LLM router động + cảm xúc avatar mở rộng
- **master:** `d84ebfd` (= origin, sau PR #27) · **PR #28 MỞ, mergeable — chờ owner "duyệt merge"**
- Đã deployed và đang chạy (verify trên server sống): breaker 403 + warm-up piper + tts_mode background + catalog động + failover cloud→cloud
- Pi5: kiosk.js bản 8:00 `9c8f6639` (tương thích ngược với tts_mode background); emotion 22-states dashboard CHƯA sync sang kiosk — chờ duyệt

---

## 9. HẠN CHẾ ĐÃ BIẾT & VIỆC CHỜ QUYẾT

| # | Hạn chế / việc | Trạng thái |
|---|---|---|
| 1 | PR #28 chờ "duyệt merge" | ⏳ owner |
| 2 | 2 khiếm khuyết gốc kiosk: daemon thiếu wait() con + launch chưa tự dọn SingletonLock | ⏳ chờ duyệt code fix (sprint sau) |
| 3 | Asset surprised trùng portrait (`c572cbbb`) | ⏳ chờ ảnh mới (engine sẵn sàng) |
| 4 | Emotion 22-states chưa sync sang kiosk Pi5 | ⏳ chờ duyệt + sync khi working tree = bản duyệt |
| 5 | Gap shield VN (thiếu "trước" → ALLOW, NEVER vẫn chặn rm -rf) | ⏳ đề xuất sprint sau |
| 6 | Transfer chunk >15MB hỏng (sai signature) | ⏳ sprint sau |
| 7 | Mic Jieli xa >50cm SNR≈0dB | Giới hạn vật lý — đổi mic gần |
| 8 | Edge-TTS 403 bền | Breaker là workaround; Edge sống lại sẽ tự dùng |
| 9 | BT XB33 E2E | Chưa test thật (loa tắt nguồn lúc test) — timer 30s sẽ tự connect |
| 10 | HANDOFF_LATEST.md còn bản 06/11 | validate_and_report full >7' — hỏi owner có chạy nền không |
| 11 | BRAIN_0 + backups lớn | Chờ duyệt xóa (§7) |

---

## 10. PHỤ LỤC — BẢN ĐỒ FILE THAM CHIẾU

| Thành phần | File | Dòng | Ghi chú |
|---|---|---|---|
| Core API | `src/quan_ai_brain/web/server.py` | 6.897 | voice/interact stream, shield wiring, edge gateway |
| Edge daemon | `edge_client/client_daemon.py` | 3.077 | heartbeat, kiosk control, idle-sleep 300s, HDMI mirror |
| Dashboard | `src/quan_ai_brain/web/static/executive.js` | 4.877 | 22 states, toast, 11 tabs |
| Avatar engine | `src/quan_ai_brain/web/static/avatar_engine.js` | 1.015 | `61dd807d`, mouth-sync |
| Kiosk UI | `edge_client/kiosk.js` | 849 | 19 states, THINKING khi background TTS (bản PC; Pi5 `9c8f6639`) |
| TTS | `src/quan_ai_brain/voice/tts_config.py` | 834 | breaker 403, warm_up, fallback map |
| LLM | `llm/netmind_provider.py` 765 · `llm/router.py` 199 | 964 | catalog TTL 300s, CLOUD_SPEED_PRIORITY |
| Shield | `security/input_shield.py` + 3 module | ~15KB | BLOCK 70 / SANITIZE 40 |
| DM responder | `tools/netchat_auto_responder.py` | 1.536 | 2-step token |
| Watchdog | `tools/watchdog.py` | 740 | respawn + backup 2AM |
| Báo cáo liên quan | `BAO_CAO_HIEN_TRANG_HINH_THE_1311.md` (cùng thư mục này) | 214 | chuyên sâu hình thể avatar |

---
*Trung thực: mọi trạng thái 🟢 đều có bằng chứng đo thật trong ngày 13/11; các mục INCONCLUSIVE/STALE/chờ-duyệt được ghi rõ. Không có mục nào được tuyên bố hoàn thành nếu chưa có bằng chứng kiểm chứng được.*
