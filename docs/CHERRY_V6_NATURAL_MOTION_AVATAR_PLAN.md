# CHERRY V6 — NATURAL MOTION AVATAR: THIẾT KẾ & LỘ TRÌNH 7 PHASE
**Ngày:** 16/11/2026 · **Người lập:** TONY · **Trạng thái:** DỰ THẢO — CHỜ OWNER DUYỆT
**Nguồn yêu cầu:** Project brief "CHERRY AI DIGITAL HUMAN – NATURAL MOTION AVATAR" (16/11)
**Nguồn tham chiếu:** `E:\BRAIN\Pi5\hình thể.mp4` (4K50, 352s) + `E:\BRAIN\Pi5\hình thể1.mp4` (1080p30, 314s) — đo thật trong `data/v6_body_ref_audit.json`

---

## 0. TỔNG QUAN — XÂY TRÊN GÌ, KHÔNG XÂY LẠI GÌ

Owner yêu cầu kiến trúc 10 module. **Audit trung thực hệ thống hiện có** (đã chạy production 24/7):

| Module trong brief | Trạng thái hiện tại | Hành động |
|---|---|---|
| 1. Avatar Renderer | ✅ Canvas 2D full-viewport kiosk (v6full, 1080² buffer) | Giữ — bổ sung nhẹ |
| 2. Facial Animation Engine | ✅ P1 face rig (mày/miệng/cười mesh) + blink/saccade/gaze | Mở rộng: 12 tham số chuẩn hoá (§5 brief) |
| 3. Body Motion Engine | ✅ v6mot (sway/lean/breath/arm-reach) + P2 head pose (yaw/pitch/roll quanh cổ) | Mở rộng theo video mẫu |
| 4. Lip Sync Engine | ✅ audio_mouth_driver + viseme A/E/I/O/U + dải mở 0.42-0.78 đo từ 6.mp4 | Chuẩn hoá viseme tiếng Việt |
| 5. Emotion Engine | ⚠️ Có 11 portrait + tone map; chuyển cảm xúc = crossfade 350ms (P3 thiết kế đã duyệt: blend mesh) | P3 — phase riêng |
| 6. Audio Processing | ✅ WebAudio live meter (PC) | Giữ |
| 7. Speech Recognition | ✅ mic pipeline kiosk (bấm mic) | Ngoài phạm vi phase này |
| 8. TTS Integration | ✅ Hoài My vi-VN qua Pi5 | Giữ |
| 9. AI Conversation Interface | ✅ Dashboard 8766 + Console 8765 | Giữ |
| 10. State Management | ✅ 22-state machine + presence_engine + motion_scheduler | Chuẩn hoá 8 nhóm brief |

**Quyết định kiến trúc:** KHÔNG chuyển sang Three.js/VRM 3D. Bám VERBATIM owner (V6.0): *"Không cần chuyển ngay sang 3D hoàn toàn. Ưu tiên giữ nhận diện Model A và tận dụng asset hiện có"* + *"khuôn mặt hình thể giao diện của anh giữ nguyên, chỉ xây dựng chuyển động"*. Con đường 2.5D warp-mesh trên chính portrait (đã chứng minh ở P1/P2) tiếp tục mở rộng. §8 brief cho phép: *"Có thể sử dụng mô hình 2.5D hoặc 3D tùy năng lực phần cứng"*.

## 1. KẾT QUẢ ĐO 2 VIDEO MẪU (điều kiện đầu vào của owner)

| Chỉ số | hình thể.mp4 (4K50) | hình thể1.mp4 (1080p30) | Ý nghĩa thiết kế |
|---|---|---|---|
| still_ratio | 44% | 40% | 40-44% thời gian near-still — micro-rest là CHUẨN, không chuyển động liên tục |
| cx_std (trọng tâm ngang) | 0.119 | 0.149 | Đổi trọng tâm người ±12-15% khung — thân thật lệch người, không chỉ lắc đầu |
| cy_std (trọng tâm dọc) | 0.169 | 0.191 | Gật/cúi/ngửa theo nhịp RÕ hơn ngang |
| Head pose khi hát | yaw 5-10°, roll 5-8° | yaw 30-40° (3/4), pitch cúi 5-15° | Người hát: yaw chủ đạo, pitch khi cảm xúc; **đầu VỮNG khi mở miệng lớn** |
| Khẩu hình mở vừa | oval dọc, lộ 6-8 răng trên, hàm hạ, khoang tối | môi hé rất nhỏ (legato) | Dải mở rộng 0→0.6+; khoang+răng phải có chiều sâu (P1 đã làm đúng hướng) |

⚠️ **Danh tính:** 2 video là ca sĩ người thật (Mỹ Duyên / Cẩm Tú) — KHÔNG sao chép khuôn mặt/trang phục (đúng ràng buộc owner §2B). Chỉ ánh xạ đặc tính chuyển động.

## 2. 8 NHÓM CHUYỂN ĐỘNG (§4 brief) — TRẠNG THÁI HIỆN TẠI & KẾ HOẠCH

| Nhóm | Hiện tại | Còn thiếu | Phase |
|---|---|---|---|
| A. IDLE | thở + sway + blink + vi-mô đầu ✅ | mỉm cười thi thoảng khi idle; tóc nhẹ (tắt theo owner 14/11 — đề nghị duyệt lại riêng) | M1 |
| B. LISTENING | yaw+roll nghiêng lắng nghe ✅ | gật nhẹ xác nhận thi thoảng (chưa có) | M1 |
| C. THINKING | yaw lệch + mắt chuyển hướng ✅ | chớp mắt CHẬM khi suy nghĩ (chưa có) | M1 |
| D. SPEAKING | viseme dải đo được + đầu vững? | **đầu vững khi mở miệng lớn** (giảm pitch khi openRatio cao — đo từ video: mở lớn = đầu đứng); gật nhấn nhá có sẵn | M2 |
| E. EXPLAINING | gesture layer có | cử chỉ tay minh hoạ — CẦN LỚP TAY MỚI (canvas-drawn, tiến hoá từ bài học arms-1311, DUYỆT RIÊNG) | M4 |
| F. HAPPY | tone map có | mắt cong khi cười (Duchenne — có squint sẵn) + gật vui | M3 |
| G. GREETING | WARM_GREETING có | đưa tay chào — thuộc lớp tay M4 | M4 |
| H. GOODBYE | chưa có | gật + cử chỉ chào + về Idle | M4 |

## 3. FACIAL ANIMATION ENGINE (§5 brief) — 12 THAM SỐ

Chuẩn hoá thành bảng blend-state duy nhất (single source of truth, thay preset rải rác):

```
PARAMS = { blinkL/R, gazeX/Y, browRaise, browLower, smile,
           mouthOpen, jawOpen, lipPucker, cheekRaise,
           headTilt(roll), headYaw, headPitch }  // neck = pivot cổ 896:802
```
Mọi tham số: nội suy easing (lerp có quán tính — đã có ở P2), blending theo priority, không hard-cut. Bảng này nằm trong `avatar_engine.js` (THEO 1 FILE, không tạo engine thứ 2 — anti-pattern bảo vệ kiến trúc).

## 4. LỘ TRÌNH 7 PHASE (§11 brief) — MẪU PHỤC VỤ NGHIỆM THU

| Phase | Nội dung | Bằng chứng nghiệm thu |
|---|---|---|
| **P1 ✅ ĐÃ LÀM** | Hình thể + khuôn mặt (portrait 896 + rig 4 lớp) | harness 24/24, PR #31 |
| **P2 ✅ ĐÃ LÀM** | Chuyển động đầu/mắt/miệng (head pose + mắt sống) | harness 25/25, 8885ad6 |
| **M1 (sprint tiếp)** | Hoàn thiện Facial Engine 12-param + Listening-gật + Thinking-chớp-chậm + Idle-smile | harness mở rộng + kiosk thật |
| **M2** | Lip-sync chuẩn hoá viseme tiếng Việt + "đầu vững khi mở lớn" (đo video) | TEST 05/06 brief |
| **P3** | Emotion blend mesh giữa 2 portrait (hết hard-cut) + HAPPY Duchenne | TEST 07/08 |
| **M4** | Body gesture: lớp tay procedural (nhẹ, đúng tỷ lệ, duyệt PoC riêng trước khi wire) + GOODBYE | TEST 06/07 + PoC |
| **M5** | Tối ưu Pi5 (PROFILE A): đo FPS thật, giảm chi phí khi CPU cao; PROFILE B PC giữ full | benchmark 60min |
| **M6** | Kiểm thử 10 TEST chuẩn brief + runtime stability | bảng nghiệm thu |

## 5. RÀNG BUỘC KHÔNG THỂ THIẾT (fail-honest)

1. **Không có asset 3D của Cherry** — con đường 3D thật (VRM) cần tạo model mới; ngoài phạm vi 2.5D đã duyệt. Nếu owner muốn 3D thật → sprint tạo model riêng (chi phí + risk nhận diện cao, cần quyết riêng).
2. **Tóc động (§3)**: tắt theo owner 14/11 ("bỏ các đường trên hình thể, giữ hình nguyên gốc"). Cần owner duyệt lại nếu muốn bật — tóc bake trong ảnh tĩnh, chỉ làm được wind-sway giả.
3. **Cử chỉ tay (E/G/H)**: bài học arms-1311 (2 cánh tay bị owner yêu cầu xoá 16/11) — M4 PHẢI có PoC duyệt riêng trước khi wire, không lặp sai lầm.
4. **Mắt nhìn "người đối diện"**: camera không tracking mắt user thật (không có eye-contact thật) — mô phỏng bằng hướng nhìn về giữa màn hình + saccade.

## 6. ĐỀ NGHỊ PHÂN BỔ

1. Owner đọc §4 lộ trình + §5 ràng buộc → duyệt M1-M2 (chỉ engine hiện có, không tạo asset mới, không đụng production cho tới E2E).
2. M4 (lớp tay) cần PoC riêng + duyệt.
3. M6 benchmark 60 phút cần Pi5 rảnh 1 giờ.

---
*Fail-honest: số liệu video đo bằng optical flow + frame thật; trạng thái hệ thống audit từ code chạy production; phần chưa làm ghi rõ.*
