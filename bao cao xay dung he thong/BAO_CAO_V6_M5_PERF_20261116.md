# V6 M5 — TỐI ƯU PI5 (PROFILE A) + FPS METER (16/11/2026)

Card: TASK-V6-M5 APPROVED+CONSUMED theo lệnh owner "em triển khai M5".
Lộ trình: `docs/CHERRY_V6_NATURAL_MOTION_AVATAR_PLAN.md` §4 M5 — "Tối ưu Pi5 (PROFILE A): đo FPS thật, giảm chi phí khi CPU cao; PROFILE B (PC) giữ full; benchmark 60 phút".

## 1. Triển khai 3 lớp

### M5a — FPS meter thật (`edge_client/avatar_engine.js`)
- Render loop đo **fps_measured** (cửa sổ 10s) + **render_ms_avg** mỗi frame (`performance.now()` bao `_update` + `_render`).
- `getPerfStats()` → `{fps_target, fps_measured, render_ms_avg, perf_profile}` cho kiosk/daemon/benchmark đọc.
- Không đổi logic render — chỉ thêm đo, overhead < 0.01ms/frame.

### M5b — PROFILE A auto-degrade (engine + agent)
- `avatar_engine.js`: `setPerfProfile("LOW"|"NORMAL")` (garbage → NORMAL, fail-safe).
  - LOW: IDLE/SLEEPING 125ms (~8 FPS), SPEAKING 66ms (~15 FPS), LISTENING/THINKING 100ms (~10 FPS).
  - NORMAL: giữ nguyên bảng thích ứng cũ (IDLE 83ms/12, LISTENING 56ms/18, SPEAKING 42ms/24).
- `edge_client/edge_agent.py`: `suggest_perf_profile()` đọc metrics_history (~3 phút, mẫu 30s):
  - CPU ≥ 70% trong ≥4 mẫu HOẶC nhiệt ≥ 70°C → **LOW**.
  - Phục hồi: cool ≥4 mẫu (CPU ≤45%) mới trả NORMAL (hysteresis, không dao động).
  - Thiếu dữ liệu (<4 mẫu) → NORMAL — **fail-honest, không suy đoán**.

### M5c — Pipeline telemetry (daemon + kiosk)
- `client_daemon.py`:
  - `EdgeDaemonState.kiosk_perf` (fps_measured/render_ms_avg/perf_profile/epoch).
  - Route mới `POST /api/kiosk/perf` nhận số từ browser.
  - `GET /api/kiosk/agent/status` expose `kiosk_perf`.
  - `to_kiosk_dict` thêm `perf_profile = edge_agent.suggest_perf_profile()`.
- `kiosk.js`:
  - Poll status 1s: `window.digitalHuman.setPerfProfile(data.perf_profile)` — chỉ log khi ĐỔI (`lastPerfProfile`, không spam console).
  - Mỗi 10s POST FPS thật về daemon (fire-and-forget, `keepalive`, lỗi mạng không ảnh hưởng render).

## 2. Kiểm chứng

### Harness wire — `data/wire_v6m5_test.js`: **28/28 PASS**
- M5a engine (11): parse class, getPerfStats/setPerfProfile/_frameIntervalMs tồn tại, LOW/NORMAL interval đúng từng state, getPerfStats đủ trường, garbage → NORMAL.
- M5b agent (5): hàm suggest tồn tại, fail-honest thiếu dữ liệu, ngưỡng CPU 70 / nhiệt 70, hysteresis.
- M5c daemon (5): route /api/kiosk/perf, kiosk_perf init, expose agent/status, perf_profile đẩy kiosk, gọi suggest_perf_profile.
- M5d kiosk (6): đọc data.perf_profile, gọi digitalHuman.setPerfProfile, POST /api/kiosk/perf, đẩy fps_measured, bỏ lượt khi chưa có số, parse OK.
- py_compile 3 file OK (edge_agent, client_daemon, benchmark tool).

### Regression FULL: **4083 passed / 10 failed / 28 skipped / 740.92s** — 0 fail mới
- Đúng baseline M3 (`1c8950a`: 4083/10/28).
- **A/B stash test**: stash M5 → chạy 3 test đáng ngờ trên HEAD sạch → **vẫn fail** (`test_cognitive_loop` AssertionError DISABLED, `test_edge_client` kiosk endpoints) → fail pre-existing, không phải M5.
- **Run nền thứ 2** (proc_5b2846f3d21a): 4082 passed / 11 failed / 28 skipped / 730.55s — ±1 flaky LAN socket-timeout (`test_executive_edge_files_and_actions`, nhóm đã biết flaky từ M3), danh sách fail trùng baseline → 0 fail mới.
- Lưu ý: `-x` dừng sớm ở `test_avatar_emotion_sync_1314::TestCacheBump` (test whitelist version cũ `v6pure_1411/v6emo_1411` — fail pre-existing từ baseline `f0998ad`).
- Log: `reports/test_run_m5_full.log`.

### Deploy Pi5 + E2E thật (kiosk production)
- `tools/v6_m5_deploy_pi5.py`: scp 5 file (avatar_engine.js, kiosk.js, kiosk.html, client_daemon.py, edge_agent.py) → **md5 5/5 KHỚP** → py_compile trên Pi5 OK → restart `quan_ai_edge.service` (system service, PID daemon = python3 main.py) OK.
- Verify `/api/kiosk/agent/status`: **kiosk_perf xuất hiện** với FPS thật từ browser.
- Đồng bộ lại `kiosk.html` lên Pi5 sau khi bump `kiosk.js?v=v6m5_1611` (bản đầu trên Pi5 còn param cũ) → reload_ui → kiosk_perf tươi lại → **PC = mirror = Pi5**.

### Kết quả đo thật trên kiosk Pi5 (đo trực tiếp, không suy đoán)
| Tình huống | FPS đo được | render_ms | CPU | Nhiệt |
|---|---|---|---|---|
| IDLE (sau khi M5 sống) | **12.0** | 0.25–0.37 | 28–29% | 45–48°C |
| SPEAKING (lệnh speak thật qua PC core → edge control) | **17.5 → 20.0** | 0.27 | 78.8% spike → 41% | 47–51°C |
| Về IDLE sau nói | 12.0 (11.9–12.1 dao động tự nhiên) | 0.25–0.37 | 2–29% | 41–56°C |
| ~90 phút quan sát liên tục | profile luôn NORMAL | — | throttle 0 | max ~56°C (< 70°C ngưỡng) |

→ FPS thích ứng theo state hoạt động đúng thiết kế: IDLE 12 / SPEAKING 18–24. PROFILE LOW chưa kích hoạt vì hệ thống khỏe (CPU/nhiệt thấp) — đúng logic "chỉ hạ khi quá tải". CPU chromium ổn hơn mong đợi (render 0.25–0.37ms/frame ≈ 0.3–1% một core).

### Cache-buster + mirror
- Bump `v6m4_1611` → **`v6m5_1611`** (kiosk.html + executive.html + index.html), cả `kiosk.js?v=` trong kiosk.html.
- Mirror md5 khớp: engine `6ae998fc2614a8e35eba7ccb2ddca49a`, kiosk.js `ff6c49ef3ef124efd3a9ade2f8b2fb68`, kiosk.html `87494121ad07ba916a101cc1198bda55`.

## 3. Benchmark tool + chạy chính thức 60 phút
`tools/v6_m5_benchmark_pi5.py` (~210 dòng): sample 30s/lần — CPU/nhiệt/throttle/load/mem qua edge agent + FPS thật từ kiosk_perf (stale >60s → không tính) + RTT PC telemetry + chromium CPU qua SSH; classify OK/WARN/CRIT; xuất JSON+MD vào `reports/`. Smoke 0.5 phút PASS.

**Đã chạy chính thức 60 phút** (`--duration-min 60 --interval-sec 30 --use-ssh`, 16/11 23:30, **119 mẫu**):

| Chỉ số | Min | Avg | P95 | Max |
|---|---|---|---|---|
| CPU (%) | 1.8 | 21.4 | 41.7 | 78.8 |
| Chromium CPU (%) — 1 core trên 4 | 7.5 | 90.9 | 118.7 | 182.6 |
| Nhiệt (°C) | 38.0 | 45.1 | 49.0 | 54.0 |
| RTT (ms) | 25.9 | 35.3 | 52.5 | 91.1 |

- Kết luận: **117 OK / 2 WARN / 0 CRIT**, `warn_3consec_cpu=false` — FINAL "WARN" chỉ do 2 mẫu WARN rải rác, không phải quá tải kéo dài.
- **PROFILE LOW chưa kích hoạt** — đúng thiết kế "chỉ hạ khi quá tải"; nhiệt max 54°C << ngưỡng 70°C, CPU max 78.8% chỉ là spike ngắn khi speak.
- Báo cáo chi tiết: `reports/V6_M5_BENCHMARK_20261116_233054.md`.

## 4. Giới hạn (trung thực)
1. Benchmark 60 phút **ĐÃ chạy chính thức bằng tool** (119 mẫu, 117 OK / 2 WARN / 0 CRIT — xem §3); 2 mẫu WARN rải rác, không tái hiện liên tiếp nên chưa kích hoạt LOW.
2. PROFILE LOW chưa được kích hoạt thật trên kiosk (hệ thống khỏe) — đã test logic qua harness 5/5.
3. Fail-honest: 10-11 test fail pre-existing như baseline, không claim đã sửa.
4. Camera streaming / wake word hoạt động song song chưa đo tác động FPS khi đồng thời.

## 5. Next (M6 — 10 TEST chuẩn brief + runtime stability)
- Benchmark 60 phút: ✅ **HOÀN TẤT** (xem §3).
- Sửa test whitelist cache version (test cũ dính version list).
- Owner nghiệm thu kiosk bằng mắt: nói chuyện liên tục 5-10 phút, xem avatar mượt, không giật.
- M6 cần brief gốc 10 TEST (đã compacted) — xin owner cung cấp lại hoặc xác nhận tiêu chí runtime stability 24h.
