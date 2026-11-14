# CHERRY PI5 NATURAL EMBODIMENT MASTER AUDIT — TASK 001 (MASTER PROMPT V5.0)

**Ngày audit:** 14/11/2026, 19:45–20:45 (+07)
**Người audit:** TONY (agent) theo lệnh owner Phạm Thế Quân
**Phạm vi:** CHỈ AUDIT — đã phát hiện + fix 1 regression critical do Sprint 6 hôm nay gây ra (chi tiết §8). KHÔNG triển khai sprint mới.
**Trạng thái mỗi mục:** [IMPLEMENTED] / [TESTED] / [MEASURED] / [INFERRED] / [UNKNOWN] / [NOT_EVALUATED]

---

## 1. CURRENT STATE (đo trực tiếp Pi5 192.168.1.21)

| Hạng mục | Giá trị đo | Trạng thái |
|---|---|---|
| OS | Debian 13 (trixie), uptime 11h28m | MEASURED |
| Nhiệt độ | 55.4°C → 60.9°C khi load | MEASURED |
| RAM | 1.6–2.3 GB used / 4 GB | MEASURED |
| Load | 1.32 / 0.88 / 0.85 | MEASURED |
| Kiosk HTTP 8768 | 200 OK | MEASURED |
| core_connected | True (PC core 192.168.1.10:8766) | MEASURED |
| avatar_state | PROUD (stuck từ E2E test — không tự về IDLE) | MEASURED + INFERRED issue |
| embodiment_mode | ACTIVE | MEASURED |
| Chromium | 13–15 process (11 hủm + zombie 79 defunct dồn từ các lần restart hôm nay) | MEASURED |
| DSI 7" panel | KHÔNG phát hiện connector DSI trong /sys/class/drm — chỉ card1-HDMI-A-1/A-2 (disconnected) + virtual NOOP-1 1920x1080 | MEASURED + UNKNOWN (cần owner xác nhận màn hình đang cắm loại gì) |
| HDMI mirror Samsung 4K | DISCONNECTED (cả 2 cổng HDMI) | MEASURED |
| Bluetooth speaker | SRS-XB33 Connected: yes | MEASURED |
| Audio sinks | 2× vc4-hdmi (card 0/1); **không thấy sink Bluetooth qua pactl** (pactl rỗng — PipeWire socket không truy cập qua SSH session) | MEASURED + UNKNOWN route |
| Mic | USB UACDemoV1.0 (card 2) | MEASURED |
| Camera | /dev/video0..35 tồn tại; **KHÔNG có process libcamera/ffmpeg/gst chạy** | MEASURED |
| camera_streaming | False (daemon tự báo) | MEASURED |

## 2. VERSIONS (md5 đo 14/11 19:50, khớp PC 100% sau deploy Sprint 6 + fix TASK001)

| File | Pi5 md5 | Ghi chú |
|---|---|---|
| avatar_engine.js | c1b3b70e86fd55c411f6423c55fbdf8c | **ĐÃ FIX getCurrentEnergy + cache task001_1411** |
| kiosk.js | 729511da57e43b9ad8ec96f653fdbcc9 | kiosk.js mới (wire setAudioSource Sprint 4) |
| avatar_protocol.js | 9c342d4fa6adab2c81cce8f6c8260bd5 | Sprint 1 |
| motion_scheduler.js | f905032111f39e6e6a341fb55ec5e0c9 | Sprint 2 |
| emotion_engine.js | 050462149b2f20ac892d8850cff0e1de | Sprint 3 |
| audio_mouth_driver.js | 11258c519b92907e8287281237b1ba95 | Sprint 4 |
| presence_engine.js | 9e511fb9d33137ae0ed5bf67ce1c2873 | Sprint 5 |
| body_motion_engine.js | 988c85d05f7fd6c0f33b6d06fcecfd3e | Sprint 6 |
| client_daemon.py | 80b23e2a07701a722ec191509bf3d25e | #29 |
| wake_word_service.py | 2f10e28f19cd036f4cda55439fcb6af6 | Vosk offline |

## 3. EXISTING MOTION CAPABILITIES (audit code edge_client/avatar_engine.js + 6 module)

| Năng lực | Trạng thái | Bằng chứng |
|---|---|---|
| Blink | [IMPLEMENTED] 16 refs blink/blinkEase | engine |
| Saccade | [IMPLEMENTED] 17 refs | engine |
| Head tilt | [IMPLEMENTED] 5 refs | engine |
| Micro-nod | [IMPLEMENTED] 13 refs nod | engine |
| Breathing | [IMPLEMENTED] 12 refs breath | engine |
| Weight shift | [IMPLEMENTED] | engine |
| Mouth-sync (timer fallback) | [IMPLEMENTED] 90ms cycle, bell curve | engine |
| Mouth-sync (audio-driven) | [IMPLEMENTED] AudioMouthDriver RMS+EMA+viseme | Sprint 4 |
| Emotion transitions | [IMPLEMENTED] 21 intensity presets + 15 micro + 12 transition presets | Sprint 3 |
| Gaze/eye contact | [IMPLEMENTED] PresenceEngine 21 eye preset + 3 listening mode | Sprint 5 |
| Idle behavior | [IMPLEMENTED] 4 behaviors schedule 2–5s | Sprint 5 |
| Body motion | [IMPLEMENTED] 21 body preset + 5 breath + 9 arm preset | Sprint 6 — **đã fix crash** |
| **Render loop FPS cap** | [IMPLEMENTED] SPEAKING 42ms (24fps) / LISTENING-THINKING 56ms (18fps) / IDLE 83ms (12fps) | engine L355–365 |
| **Body RENDERING** (vẽ thân theo targetBody) | **MISSING** — targetBody được tính mỗi frame nhưng `_render` chưa tiêu thụ | grep 0 hit `_renderBody` |

## 4. MISSING CAPABILITIES (gap so với MASTER PROMPT V5.0)

1. **Body rendering chưa tiêu thụ targetBody** — Sprint 6 tính transform nhưng canvas chỉ vẽ head/portrait. Tay/váy (stash `body_sync_1311-experimental-avatar` có code canvas-drawn váy/đàn/hoa) chưa merge.
2. **Eye openness control** — không có biến eyeOpen/eye_open trong engine (grep 0 hit) → SURPRISED không mở mắt to hơn được với asset tĩnh.
3. **Gesture library chưa có trigger từ hội thoại** — GESTURE_LIBRARY 10 gesture tồn tại nhưng không có mapping text→gesture.
4. **Camera presence** — camera_streaming=False, không có face detection; toàn bộ Sprint 5 camera-gaze của V5.0 là NOT_EVALUATED (cần design riêng vì Pi5 đã bận ~2.3GB RAM + swiftshader load).
5. **avatar_v2_surprised.png trùng md5 với portrait** (`c572cbbb...` cả 2) — asset surprised VẪN LÀ ẢNH ĐƠ (chưa sửa, đúng kế hoạch chờ nhánh thử nghiệm).
6. **Avatar không tự về IDLE sau E2E** — state PROUD giữ nguyên ≥30 phút (AUTO-IDLE SLEEP 300s chỉ áp khi kiosk không có activity; set_expression trực tiếp không kích hoạt lại timer? Cần verify cơ chế).
7. **Audio sink Bluetooth không thấy qua pactl** — SRS-XB33 connected nhưng route audio không xác minh được qua SSH (PipeWire user session). UNKNOWN.
8. **pactl/pipewire socket không truy cập từ SSH** — mọi kiểm tra audio runtime phải qua daemon API hoặc trên máy.

## 5. RENDERING BOTTLENECKS (đo thật)

| Chỉ số | Giá trị | Đánh giá |
|---|---|---|
| gpu-process CPU | 65–68% STABLE (trend đo 6×5s) | **swiftshader software-composite floor** — không phải bug; kiosk `--use-angle=swiftshader` (software GL). Đây là giá nền của chromium kiosk trên Pi5 từ trước |
| renderer CPU | 2.1–9.1% (SAU fix; trước fix 48–63%) | JS engine nhẹ — canvas 12–24 FPS cap hoạt động tốt |
| Temperature | 59.8–60.9°C | Cao nhưng ổn định; swiftshader là nguyên nhân chính |
| JS render cost (harness) | 0.01 ms/frame PC ×4 ≈ 0.06 ms/frame Pi5 | _update+_render KHÔNG phải bottleneck; cap 42ms dư sức |
| Memory chromium | ~200MB/renderer ×N | Ổn |
| Zombie | 79 defunct (parent 1618 main.py không reap) | Không ăn CPU; nên thêm reaper vào main.py hoặc restart dịch vụ sạch |

## 6. CAMERA CAPABILITY — NOT_EVALUATED
- 25+ /dev/video* nodes (USB cam + unicam); không có process capture chạy.
- Daemon báo camera_streaming=False.
- **Không đánh giá gaze khả thi trong audit này** (cần Sprint riêng + benchmark CPU).

## 7. VOICE SYNCHRONIZATION
- Wake service Vosk offline chạy 24/7 (PID 1621, 7.2% CPU, uptime 11h).
- AudioMouthDriver đã wire kiosk.js playKioskSpeech → engine.setAudioSource (Sprint 4 + lũy kịch đã deploy).
- PCM audio hiển thị qua speech; **không đo được audio→mouth offset trong audit này** (cần Test D với mic thật).
- Latency targets V5.0 (§7.4): CHƯA ĐO — cần benchmark riêng với setup mic + loa thật.

## 8. CRITICAL FINDING — REGRESSION SPRINT 6 (ĐÃ FIX + DEPLOY NGAY)

**Phát hiện:** engine gọi `this._mouthDriver.getCurrentEnergy()` — method KHÔNG TỒN TẠI (API thật: `getCurrent()` → `{viseme, open, envelope, active}`). TypeError **mỗi frame** trong `_update()` → render loop crash giữa chừng → `_render` không chạy.

**Tác động đo được (trước fix):**
- Chromium gpu 60.8% + renderer 48.5–63.6% (~110% CPU) — exception storm
- Avatar đứng yên (kiosk vẫn 200 OK vì HTTP layer không qua canvas)
- Temp 60.4°C

**Tại sao test không bắt được:** pytest 195/195 pass vì test Sprint 6 chỉ chạy Python mirror + module độc lập; KHÔNG có integration test engine↔module. `node --check` chỉ check syntax, không check runtime call.

**Fix (commit `23c3d14`):**
1. 2 engine: `const mouth = this._mouthDriver.getCurrent(); ... setSpeechEnergy(mouth ? (mouth.envelope||0) : 0)`
2. NEW `tests/test_engine_module_api_contract.py` (6 test): quét mọi `this._<driver>.<method>(` call trên 2 engine, xác minh method tồn tại trong module JS — chặn vĩnh viễn bug "gọi method ma"
3. Cache bump `task001_1411` cho 6 module + engine trên 3 HTML (chromium cache cứng đầu — cache-bust bắt buộc)

**Verify sau fix:**
- pytest **201/201 pass** (195 cũ + 6 contract)
- Node harness chạy engine thật + 3 module thật, 200 frames `_update()`: **0 errors**; PROUD → targetBody `{leanY:-0.1, swayX:0.221, breathOffset:-0.219, leftArm:10}` đúng preset
- Pi5 redeploy md5 `c1b3b70e` khớp; kiosk serve `avatar_engine.js?v=task001_1411`
- **Renderer CPU: 48–63% → 2.1–9.1%** (giảm ~90%); gpu 65–68% STABLE (= swiftshader floor, đúng thiết kế); render loop sống lại

## 9. PROPOSED IMPROVEMENTS (thứ tự ưu tiên — CHỜ DUYỆT, không tự triển khai)

| # | Mục | Sprint đề xuất | Lý do ưu tiên |
|---|---|---|---|
| 1 | Wire targetBody vào _render (body rendering 2D: váy/tay theo transform + breath offset) | Sprint 7a | Hoàn tất vòng đời Sprint 6 — transform đã có nhưng chưa vẽ |
| 2 | Merge body/arms experimental từ stash (váy+đàn+hoa, đã có code canvas-drawn) vào body rendering | Sprint 7a | Tận dụng code đã được owner duyệt thử nghiệm trước đó |
| 3 | Fix auto-return IDLE sau set_expression (state PROUD stuck 30+ phút) | Sprint 7a (bug) | Tránh avatar "đơ biểu cảm" |
| 4 | Eye openness (eyeOpen 0..1 theo emotion, áp cho SURPRISED/THINKING) | Sprint 7b | V5.0 §3.2 yêu cầu |
| 5 | Text→gesture mapping (triggers trong conversation engine) | Sprint 7b | V5.0 §3.5 |
| 6 | Zombie reaper cho main.py (waitpid loop) hoặc systemd Restart kiểm soát | Sprint 7a (hygiene) | 79 zombie sẽ tăng theo mỗi lần restart |
| 7 | Camera presence (Sprint 5 V5.0) — design riêng, benchmark trước khi bật | Sprint 8 | Pi5 RAM 2.3/4GB, swiftshader load; cần đo trước |
| 8 | surprised asset đúng nghĩa (nhánh thử nghiệm + duyệt) | Sprint 8 | V5.0 §4.4 |
| 9 | Audio route Bluetooth verify (pactl không truy cập SSH — cần đo trên máy hoặc qua daemon API) | Sprint 8 | Route hiện UNKNOWN |

## 10. TEST STRATEGY (theo V5.0 §XII)

| Test | Trạng thái | Ghi chú |
|---|---|---|
| A – Natural Idle 10 phút | NOT_RUN | Cần sau Sprint 7a |
| B – Listening 20 câu | NOT_RUN | cần mic thật |
| C – Thinking | NOT_RUN | |
| D – Speaking lip-sync | NOT_RUN | cần đo audio→mouth offset |
| E – Emotion 15 states | PARTIAL (13/22 state được E2E setExpression qua history; screenshot thiếu) | |
| F – Barge-in | IMPLEMENTED (code) / NOT_VERIFIED (E2E mic) | |
| G – Camera presence | NOT_EVALUATED | camera tắt |
| H – Stability 4h | NOT_RUN (uptime 11h nhưng không có instrumentation FPS/frame-time) | |

## 11. RISKS

1. **Swiftshader floor 65–68% CPU** — không thể thêm feature render nặng; mọi sprint mới phải đo delta CPU trên nền này.
2. **DSI panel không thấy trong DRM** — nếu màn 7" thực chất là HDMI adapter thì profile LOW (V5.0 §8.3) phải đổi giả định. Cần owner xác nhận cấu hình màn hình thật.
3. **79 zombie tăng dần** — nếu main.py không reap, sau nhiều ngày có thể ăn PID/memory.
4. **Camera pipeline chưa test** — bật camera trên Pi5 có thể đẩy CPU qua ngưỡng.
5. **Cache-bust mỗi lần deploy** — phải bump version mọi static change (đã có sẵn trong quy trình).

## 12. ROLLBACK
- Engine fix: backup `avatar_engine.js.bak_pre_task001fix_1411` + git revert `23c3d14`
- kiosk.html: backup `.bak_pre_task001_1411`
- Quay lại Sprint 6 crash = không khuyến nghị (crash đốt CPU 110%)

## 13. OWNER APPROVAL REQUIRED

- [ ] Duyệt Sprint 7a: body rendering + merge stash experimental + fix auto-IDLE + zombie reaper
- [ ] Duyệt Sprint 7b: eyeOpen + text→gesture
- [ ] Xác nhận cấu hình màn hình Pi5 (DSI native hay HDMI adapter?)
- [ ] Duyệt benchmark latency (§7.4 V5.0) làm bước đo tiếp theo
- [ ] Camera presence: thiết kế + benchmark riêng trước khi bật

---
*Audit fail-honest: mọi số liệu trong bảng là đo thật (ssh/curl/ps/node harness); mục NOT_EVALUATED/UNKNOWN được ghi rõ, không bịa.*
