# BÁO CÁO V6 M1+M2 — FACIAL ENGINE 12-PARAM + LIP-SYNC & ĐẦU VỮNG (v6m12_1611)

**Ngày:** 16/11/2026 · **Task:** TASK-V6-M12 (card APPROVED + CONSUMED, auth `owner_desktop_chat_directive`)
**Chỉ thị owner:** "duyệt hướng này (duyệt để làm) em triển khai M1 + M2 ngay trong sprint này"
**Nguồn thiết kế:** `docs/CHERRY_V6_NATURAL_MOTION_AVATAR_PLAN.md` (audit 2 video mẫu `E:/BRAIN/Pi5/hình thể.mp4` + `hình thể1.mp4`, optical flow + frame analysis → `data/v6_body_ref_audit.json`)

## 1. Delivered

### M1 — Facial Engine 12-param (§5 brief)
| Hạng mục | Nội dung | Bằng chứng |
|---|---|---|
| M1a | `_facialParams()`: bảng 12+ tham số biểu cảm chuẩn hoá (eyeBlink L/R, eyeLookX/Y, browRaise/Lower, smile, mouthOpen, jawOpen, lipPucker, cheekRaise, headTilt/Yaw/Pitch) — **accessor ĐỌC state có sẵn**, không tạo engine thứ 2, không phá render P1/P2 | harness M1a.1-10 |
| M1a | `_browAmtFor(st)` tách preset mày thành 1 nguồn sự thật (render + 12-param cùng đọc) | harness M1a.9 |
| M1b | LISTENING gật nhẹ xác nhận: 6-14s/lần, biên độ 1.2°, 40% gật đôi (sin 0.75/1.5 chu kỳ, 620ms/1 gật), cộng vào pitch nền không đè | harness M1b.1-4 |
| M1c | THINKING/RESEARCHING chớp chậm 900ms (nhắm 450 + mở 450) thay blink 150ms — "chìm vào suy nghĩ" §4C | harness M1c.1-3 |
| M1d | IDLE mỉm cười thi thoảng 12-20s/lần, giữ 2.5-4s, ease sin biên độ 0.55 (không bật/tắt đột ngột §5), vẽ 2 nét khóe đi cùng head warp | harness M1d.1-6 + live smoke |

### M2 — Lip-sync & Đầu vững (đo từ video mẫu)
| Hạng mục | Nội dung | Bằng chứng |
|---|---|---|
| M2a | **"Đầu vững khi mở miệng lớn"**: steady factor `1 − openRatio×0.55` (mở 100% → state yaw/pitch/roll còn 45%, drift giữ 100% vì thở không phụ thuộc nói). Số liệu đo: ca sĩ mở 50-60% thì đầu frontal yaw chỉ 5-10° | harness M2a.1-4 |
| M2b | **Viseme tiếng Việt chuẩn hoá**: bảng `VISEME_VI` 12 nguyên âm (a/ă/â/e/ê/i/y/o/ô/ơ/u/ư) → 5 shape engine (A/O/E/I/U) với open/round; runtime vẫn chạy ngưỡng RMS đồng bộ tiếng loa (không phá wire), bảng là chuẩn tham chiếu + debug/tune | harness M2b.1-5 |
| M2b | **Răng dưới khi mở rất lớn** (>0.8 openRatio, fade 0.8→1.0, mờ hơn + hẹp hơn răng trên — đo frame mở tối đa video mẫu) | harness M2b.6-8 |

## 2. Kiểm chứng
- **Harness riêng** `data/wire_v6m12_test.js`: **39/39 PASS** (M1a 10 + M1b 4 + M1c 3 + M1d 6 + M2a 4 + M2b 8 + hooks 4)
- **P1 regression** `wire_v6rig_test.js`: **24/24 PASS** · **P2 regression** `wire_v6pose_test.js`: **25/25 PASS** (T5 cập nhật expectation cho steady — clamp vẫn ±6/±4/±2)
- **node --check** engine + driver: OK · mirror PC static md5 `9dd0ff59` khớp edge_client
- **Live smoke PC :8765**: engine serve md5 khớp, code M12 trong payload, cache-buster `v6m12_1611` ăn; headless Chrome console SẠCH; vision screenshot: avatar đầy đủ, mặt tự nhiên, **nụ cười nhẹ IDLE hiển thị đúng**, layout nguyên
- **Deploy Pi5** `quanpt1@192.168.1.21`: backup `.bak_pre_m12` → scp engine + driver + kiosk.html → md5 KHỚP cả 3 (`9dd0ff59` / `f86559dd` / `e90aad4c`) → reload_ui OK → kiosk_running=True, avatar_state=IDLE, embodiment=ACTIVE, core_connected=True; headless chromium trên Pi5: không lỗi JS (trang kiosk render, avatar qua file:// bị broken-image là hạn chế headless đã biết — kiosk thật chạy server assets)
- **Full regression pytest** nền `proc_ef5b5be698ab`: **4082 passed / 11 failed / 28 skipped (762.73s)** — đúng baseline. 11 fail đều pre-existing: 10 tên khớp baseline P2 (`8885ad6`, socket TimeoutError Pi5 LAN + cognitive/cpsl/identity/media/edge_known); riêng `test_avatar_emotion_sync_1314.py::test_html_cache_version_bumped` đã chứng minh A/B **pre-existing trên HEAD sạch** (stash M12 → vẫn fail: test chốt danh sách version `v6pure_1411/v6emo_1411/cherry_sync1314`, không nhận version mới hơn — fail này tồn tại từ sprint cảm xúc 14/11, KHÔNG phải fail mới của M12; 0 file Python sửa trong M12)

## 3. Không làm (trung thực — fail-honest)
- KHÔNG tạo engine thứ 2; KHÔNG chuyển 3D/VRM (verbatim owner: giữ Model A + asset hiện có)
- KHÔNG wire cử chỉ tay (M4 — phải PoC duyệt riêng, bài học arms-1311); KHÔNG bật tóc động (owner tắt 14/11)
- E2E động (nhìn thấy gật/smile/nhắm-chậm chuyển động thật bằng mắt) chưa chốt — headless đóng băng thời gian ảo; cần owner nhìn kiosk 15-30s: (1) IDLE thấy nụ cười thi thoảng, (2) LISTENING thấy gật nhẹ, (3) SPEAKING thấy đầu vững hơn khi mở miệng lớn

## 4. Files
- `edge_client/avatar_engine.js` + mirror static (md5 `9dd0ff59`): M1a-d + M2a + răng dưới
- `edge_client/audio_mouth_driver.js` + mirror (md5 `f86559dd`): VISEME_VI + export
- `edge_client/kiosk.html` / `static/executive.html` / `static/index.html`: cache-buster `v6m12_1611`
- `data/wire_v6m12_test.js` (39 checks) · `data/wire_v6pose_test.js` (T5 steady)
- `tools/submit_v6_m12_approval.py` (card TASK-V6-M12)
- Backup Pi5: `avatar_engine.js.bak_pre_m12`

## 5. Next (sau nghiệm thu owner)
- P3 blend cảm xúc liên tục (hết hard-cut crossfade) + HAPPY Duchenne đầy đủ
- M4 cử chỉ tay + GREETING/GOODBYE — cần PoC duyệt riêng
- M5-M6 tối ưu Pi5 + benchmark 60 phút 10 TEST chuẩn brief
