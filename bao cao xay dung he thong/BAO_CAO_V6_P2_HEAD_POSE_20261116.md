# BÁO CÁO SPRINT — V6-001 P2: HEAD POSE 3D GIẢ + MẮT SỐNG (v6pose_1611)

**Ngày:** 16/11/2026 · **Card:** TASK-V6-P2 (APPROVED + CONSUMED, auth `owner_desktop_chat_directive`)
**Chỉ thị owner (verbatim):** *"em cần xây dựng hình thể tương tác như nhân vật thực"* (desktop chat 16/11)
**Nguồn thiết kế:** `docs/CHERRY_V6_LIVE_PORTRAIT_DESIGN.md` §4 Giai đoạn P2 (owner duyệt 15/11)

---

## 1. SCOPE ĐÃ LÀM

| # | Hạng mục | File | Chi tiết |
|---|---|---|---|
| 1 | Head pose state | `edge_client/avatar_engine.js` | `headYaw ±6° / headPitch ±4° / headRoll ±2°` (clamp `_clamp`), khởi tạo 0 trong constructor |
| 2 | Update loop 4b | `avatar_engine.js` | drift sinh học (3 sóng lệch pha) + state mapping (SPEAKING gật 0.64Hz/nghiêng theo câu, LISTENING nghiêng lắng nghe −2.2°/−1.4°, THINKING hướng lên-trái +2.6°, SLEEPING/OFFLINE đầu gục +2.6°, SURPRISED ngửa −1.6°, APOLOGETIC/ERROR cúi +1.8°) + gaze-lead (đầu theo mắt ~35-40%) + lerp quán tính cổ (0.035-0.05) |
| 3 | `_renderHeadPose` | `avatar_engine.js` | warp 16 dải ngang quanh trục cổ (896-space y=802), ease `pow(1.25)` 0 tại cổ → 1 tại đỉnh (y=76); dx = yaw·0.95·kx·ease, dy = pitch·0.95·ky·ease; roll = ctx.rotate trong crop; bandH +0.7px chống khe sáng; skip khi |pose| < 0.05° (tiết kiệm CPU idle); xuất `_poseAt` offset cho eye/brow/mouth |
| 4 | Render wire | `avatar_engine.js` | portrait + crossfade vẽ qua `_renderHeadPose` (thay drawImage trực tiếp); `_renderEyes` nhận `poseOff` (tham số mới); `_renderRigMouth/_renderRigSmile` dịch `poseDx` + breathOffset = dy; `_renderRigBrows` dịch `poseDx` |
| 5 | Mắt sống | `avatar_engine.js` | saccade branch mới SPEAKING/HAPPY/PROUD/SUCCESS (±1.6px quét + 30% micro-fixation nhìn thẳng chủ nhân) |
| 6 | Cache-buster | `kiosk.html`, `executive.html`, `index.html` | `v6rig_1611`/`v6noarms_1611`/`v6ges_1511` → `v6pose_1611` |
| 7 | Card | `tools/submit_v6_p2_approval.py` | NEW — tạo + duyệt + consume TASK-V6-P2 |
| 8 | Harness | `data/wire_v6pose_test.js` | NEW — 25 test (pattern wire_v6rig_test.js) |

**Không làm (giữ nguyên):** body_motion_engine.js, audio_mouth_driver, presence_engine, asset portrait, DB, secret, root transform (cấm xoay cả khung của owner 15/11 vẫn được tôn trọng — rotate chỉ nằm trong crop dải đầu).

## 2. TEST — SỐ LIỆU THẬT

| Bài test | Kết quả |
|---|---|
| `node data/wire_v6pose_test.js` (harness P2) | **25/25 PASS** — pose clamp, 16 dải, dải đáy dx≈0 (thân nguyên), ease brow>eye>mouth, state mapping, eyes overlay +poseOff, rig +poseDx, root không xoay, crossfade qua warp, P1 sprite vẫn tắt, arms vẫn tắt, vi-mô skip |
| `node data/wire_v6rig_test.js` (harness P1 regression) | **24/24 PASS** |
| `node --check avatar_engine.js` | PASS (PC) |
| Full regression `pytest tests/ -q` | **4082 passed / 11 failed / 28 skipped** (12:35) — 11 fail **pre-existing** (cùng cụm `test_web_executive_endpoints` + `edge_control_*`, lỗi socket TimeoutError trỏ Pi5 192.168.1.10:8766 — số đúng bằng baseline A/B stash đã chứng minh trên HEAD sạch f0998ad trong bf6616c; P2 chỉ sửa JS/HTML, 0 file Python route) |
| Live smoke PC :8765 | curl: engine served có `_renderHeadPose` + refs `v6pose_1611`; Chrome headless screenshot: avatar nguyên vẹn, không xé/khe/méo |
| E2E Pi5 (192.168.1.21) | deploy root+assets md5 khớp (`a4406b23`/`811f9bb2`); **phát hiện + fix serve-stale kiosk.js trên Pi5** (`9c8f6639` lỗi SyntaxError:605 "Unexpected token 'catch'" → sync PC `bfd8f172`, node --check OK) — sau fix JS console **SẠCH**, avatar render đầy đủ (vision xác nhận: đầu thẳng, cười nhẹ, không artifact warp) |

## 3. E2E VISUAL — TRUNG THỰC VỀ GIỚI HẠN

- **Đã xác nhận:** engine P2 nạp + chạy trên cả PC (:8765) lẫn Pi5 (:8768 kiosk), JS không lỗi, avatar hiển thị bình thường, không artifact (khe sáng/đầu tách/méo mặt) — vision check 2 nguồn.
- **Chưa chốt bằng ảnh tĩnh:** chuyển động yaw/pitch/roll NHANH NHƯ THẾ NÀO chưa đo được qua chuỗi screenshot (headless Chrome `--virtual-time-budget` đóng băng thời gian ảo; 2 frame thực cách 8s có diff đầu 0.94-2.36 vs thân 0.08 — có sự khác biệt vùng đầu nhưng chưa tách bạch blink/saccade khỏi warp).
- **Hạn chế phần cứng:** HDMI Pi5 vẫn mất vật lý (output = NOOP-1 headless 1536x672) — không chụp được màn hình thật đang chạy; đánh giá qua headless + diff số liệu.
- **Đề xuất nghiệm thu owner:** nhìn trực tiếp màn kiosk 15-30s — gật/nghiêng khi nói, đầu theo mắt, nghiêng lắng nghe khi LISTENING.

## 4. HONEST LIMITATIONS

1. Warp dải ngang 16 băng = xấp xỉ quay 2D quanh cổ, KHÔNG phải mesh 3D thật (yaw ±6° mô phỏng bằng shear theo chiều cao — đủ tự nhiên ở biên độ nhỏ, không quay quá 6°).
2. `_poseAt` chỉ offset eye/brow/mouth — tóc mái/kiểu tóc đi cùng dải warp tự nhiên (drawImage cùng ảnh), không cần rig riêng.
3. Chi phí render: 16 drawImage dải 1080-buffer — đo P1 mesh ~2ms; chưa đo FPS trên Pi5 thật (đề xuất đo ở sprint dọn dẹp với đầy đủ kiosk).
4. kiosk.js Pi5 stale `9c8f6639` là bug deploy CŨ lộ ra trong sprint này (không do P2 gây) — đã fix trong sprint, cần rà quy trình deploy (bước 6 kỷ luật md5 cả JS phụ thuộc).

## 5. NEXT STEPS

- (a) Owner nghiệm thu P2 bằng mắt trên kiosk thật → duyệt P3 (CẢM XÚC LIÊN TỤC: blend mesh 2 portrait, hết hard-cut).
- (b) Sprint dọn dẹp: fix is_kiosk_running stale + watchdog relaunch --kiosk + HDMI vật lý + đo FPS Pi5.
- (c) Commit + PR theo workflow TASK001 (chờ "duyệt merge").

---
*Fail-honest: mọi số liệu trên từ tool thật (node harness, pytest, curl md5, grim screenshot, vision check); phần chưa chứng minh được đã ghi rõ ở §3-4.*
