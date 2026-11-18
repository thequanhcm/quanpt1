# CHERRY V7 — NATURAL HUMAN MOTION ENGINE
**Ngày**: 2026-11-18 · **Người lập**: TONY · **Trạng thái**: TRIỂN KHAI (theo lệnh owner 18/11)
**Nguồn yêu cầu**: 10 hạng mục nâng cấp motion toàn diện + video tham chiếu `E:/BRAIN/Pi5/Cherry final.mp4` (2h44m MC talking-head)
**Tiền đề**: V6 motion engine đã ổn (P1-M6 DONE 16/11 commit `1c8950a`), giờ áp profile thực đo từ video và mở rộng 10 hạng mục.

---

## 0. TUYÊN NGÔN (fail-honest)
- **CHERRY MUST NOT CLAIM INTELLIGENCE. CHERRY MUST DEMONSTRATE INTELLIGENCE.**
- **NATURAL MOTION. INTELLIGENT EXPRESSION. HUMAN-CENTERED INTERACTION.**
- Giữ chuyển động như một **THỂ THỐNG NHẤT** — KHÔNG phải các bộ phận chạy độc lập.
- Giữ nguyên asset Model A (portrait 896×896, 11 portrait variants) — không tạo asset mới.
- 2.5D warp-mesh tiếp tục (không chuyển Three.js/VRM).
- Tất cả thay đổi phải có **evidence** từ video profile + đo runtime (FPS, latency).

## 1. MOTION PROFILE ĐO ĐƯỢC (evidence — `data/avatar/cherry_final_motion_profile_20261118.json`)

| Chỉ số | Giá trị | Ý nghĩa |
|---|---|---|
| **speaking_motion_mean** | 0.18 | Khi MC nói: 18% pixel khung thay đổi liên tục |
| **face_motion_mean** | 0.20-0.24 | Đầu + mắt + miệng hoạt động LIÊN TỤC |
| **body_motion_mean** | 0.15-0.21 | Gesture tay + sway ngực (~75% face motion) |
| **mouth_peak_intensity** | 0.71-0.87 | Nguyên âm mạnh, mở ~50-60% hàm |
| **mouth_active_ratio_when_speaking** | 99% | Khi nói, miệng gần như KHÔNG lúc nào still |
| **approx_blink_rate_per_min** | 17 | Chuẩn sinh lý (15-20/min) |
| **approx_syllable_peaks_per_sec** | 4.5 | MC nói tiếng Anh chuẩn 4-6 syllable/s |
| **speaking_duration_ratio** | 60% | 60% thời gian MC nói, 40% B-roll |
| **b_roll_still_ratio** | 89% | B-roll gần như tĩnh hoàn toàn |

## 2. KIẾN TRÚC "THỂ THỐNG NHẤT" — 1 SÓNG LAN, NHIỀU BỘ PHẬN

Thay vì 5 engine chạy độc lập → xây **1 MOTION HEARTBEAT** điều khiển tất cả bộ phận qua **motion frames** đồng bộ.

```
┌─────────────────────────────────────────────────────────────────┐
│   AUDIO RMS  →  PHONEME BUFFER  →  MOTION HEARTBEAT (60Hz)     │
│                                                  ↓              │
│         ┌──── Motion Frame (state vector @ t) ────┐             │
│         │  yaw/pitch/roll, browL/R, eyeL/R, mouth, │             │
│         │  smile, breath, blink, saccade, gesture │             │
│         └─────┬────────┬─────────┬────────┬───────┘             │
│               ↓        ↓         ↓        ↓                     │
│        avatar_engine  emotion  presence  body  →  Canvas       │
│        (mesh warp)   (blend)  (gaze/idle) (sway)               │
└─────────────────────────────────────────────────────────────────┘
```

**Đặc điểm**:
- Mỗi frame @60Hz: tính 1 motion frame duy nhất (state vector), 5 engine chỉ ĐỌC, không có logic riêng.
- **Physics damping** (velocity + acceleration) áp dụng cho TOÀN BỘ tham số → không bao giờ giật.
- **Micro-expression loop** chạy nền 4-7s/lần kể cả khi IDLE/SLEEPING → khuôn mặt LUÔN CÓ SỨC SỐNG.

## 3. 10 HẠNG MỤC → 10 MODULE (1-1)

| # | Hạng mục | Module | Owner file |
|---|---|---|---|
| 1 | FACIAL ANIMATION | muscle_controllers.js | src/quan_ai_brain/web/static/ |
| 2 | NATURAL LIP SYNC | phoneme_buffer.js + audio_mouth_driver.js | src/quan_ai_brain/web/static/ |
| 3 | EYE MOVEMENT | saccade_engine.js (random + smooth pursuit + blink) | src/quan_ai_brain/web/static/ |
| 4 | HEAD & NECK | head_dynamics.js (yaw/pitch/roll + quán tính) | src/quan_ai_brain/web/static/ |
| 5 | BODY LANGUAGE | body_motion_engine.js (mở rộng) | src/quan_ai_brain/web/static/ |
| 6 | MOTION BLENDING | motion_blender.js (state transitions 200-900ms) | src/quan_ai_brain/web/static/ |
| 7 | MICRO-EXPRESSIONS | micro_expression_loop.js (4-7s/lần, luôn chạy) | src/quan_ai_brain/web/static/ |
| 8 | PHYSICS & SMOOTHING | physics.js (damping + spring + smoothing) | src/quan_ai_brain/web/static/ |
| 9 | AUDIO-VISUAL SYNC | audio_mouth_driver.js (RMS + viseme + 4.5 peaks/s) | src/quan_ai_brain/web/static/ |
| 10 | PERFORMANCE OPT | motion_profiler.js (FPS monitor + adaptive LOD) | src/quan_ai_brain/web/static/ |

**Nguyên tắc KHÔNG VI PHẠM**:
- KHÔNG tạo avatar_engine mới — chỉ mở rộng file hiện tại.
- Mọi module mới = **fail-open**: import try/except, fallback về hành vi cũ nếu lỗi.
- KHÔNG đổi protocol_version của các file sync Pi5 (kiosk → commit trước khi SCP).

## 4. MỤC TIÊU NGHIỆM THU (acceptance criteria)

| Tiêu chí | Trước | Sau | Đo |
|---|---|---|---|
| FPS Pi5 (kiosk) | ~30-40 | ≥50 | runtime FPS monitor |
| Giật hình | có | 0 | physics smoothing pass rate |
| Miệng idle still | 0% (99% active) | ≤60% | mouth_active_ratio_when_speaking → khi idle ≤30% |
| Blink cố định | 2.8-3.4s ±0.3 | 2.5-6.0s ±2.5 | log blink interval |
| Head pose vững khi mở lớn | chưa | ≥80% | steady-factor test |
| Nhịp nói | linear | matched 4.5 peaks/s | audio-viseme sync test |
| Quán tính đầu | cứng | có inertia | angular velocity test |

## 5. RÀNG BUỘC KHÔNG THỂ THIẾU (fail-honest)

1. **Mọi sửa phải có unit test** (harness wire_v7m1 / v7m2 / ...). Test fail = không merge.
2. **Bất kỳ thay đổi nào trên avatar_engine.js** phải đi qua regression: 4082 passed/11 fail pre-existing — không tăng fail.
3. **Mirror Pi5** qua Task PI5_FILE_SYNC_15MIN md5 check, KHÔNG tự SCP.
4. **Không đổi asset** (portrait, mouth, brow PNG) — chỉ chỉnh mesh/deformation.
5. **E2E trên Pi5 thật** trước khi coi là xong (kiosk_running=True + owner nhìn live).

## 6. LỘ TRÌNH (KHÔNG SỚM, KHÔNG MUỘN)

| Sprint | Module | Card | Bằng chứng |
|---|---|---|---|
| **M0 (18/11, hôm nay)** | motion_profiler.js + micro_expression_loop.js | V7-M0 | FPS log + idle micro blink |
| **M1 (18/11)** | physics.js + head_dynamics.js | V7-M1 | damping test + inertia test |
| **M2 (19/11)** | phoneme_buffer.js + audio_mouth_driver.js (mở rộng viseme) | V7-M2 | 12 viseme VN + matched 4.5 peaks/s |
| **M3 (19/11)** | saccade_engine.js + micro-expression | V7-M3 | blink 2.5-6s variance + saccade smooth |
| **M4 (20/11)** | body_motion_engine.js + muscle_controllers.js | V7-M4 | chest sway 0.18 + cheek/forehead micro |
| **M5 (20/11)** | motion_blender.js (state transitions 200-900ms) | V7-M5 | transition smoothness test |
| **M6 (21/11)** | E2E trên Pi5 + benchmark 60min | V7-M6 | FPS ≥50, no-jerk |
| **M7 (21/11)** | Báo cáo + commit + SCP Pi + chờ owner duyệt | V7-M7 | reports/CHERRY_V7_REPORT_20261118.md |

## 7. RỦI RO & GIẢM THIỂU

| Rủi ro | Giảm thiểu |
|---|---|
| Pi5 CPU cao khi chạy đồng thời 5 module | motion_profiler adaptive LOD: giảm saccade frequency khi FPS < 45 |
| Quán tính quá mạnh gây trễ cảm xúc | Damping factor configurable, mặc định 0.15 (chuẩn sinh học) |
| Module mới gây giật khi load | fail-open + lazy load (chỉ khởi tạo khi avatar khởi động) |
| Sync Pi5 sai MD5 | Task PI5_FILE_SYNC_15MIN auto-revert |
| M2 thiếu viseme VN chuẩn | Dùng bảng VISEME_VI 12 nguyên âm đã có trong M1 commit `b5e62df` |

## 8. KHÔNG LÀM (out of scope)

- ❌ Tạo asset 3D (VRM) — owner đã VERBATIM từ chối V6.0
- ❌ Crossfade ảnh + sprite đè — fail-honest cũ
- ❌ Đổi khuôn mặt Model A — owner VERBATIM "giữ nguyên, chỉ xây chuyển động"
- ❌ Tóc animate (đã tắt 14/11 theo owner)
- ❌ Tay animate (đã xoá 16/11 theo owner) — M4 chỉ chest sway + vai, KHÔNG tay
- ❌ Eye contact thật (không có camera tracking user)

---

*Trạng thái V7-M0: triển khai ngay 18/11 — wire profiler + micro-expression trước khi ghép engine cũ.*
