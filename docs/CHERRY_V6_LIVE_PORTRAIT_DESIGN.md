# CHERRY V6-001 — BÁO CÁO THIẾT KẾ NHÂN VẬT CHUYỂN ĐỘNG (LIVE PORTRAIT)
**Ngày:** 15/11/2026 · **Người lập:** TONY · **Trạng thái:** DỰ THẢO — CHỜ OWNER DUYỆT
**Chỉ đạo owner (verbatim):** *"anh muốn là một nhân vật chuyển động chứ không phải là một hình ảnh tĩnh và nháy, muốn sẽ là một nhân vật chuyển động, cử chỉ, nét mặt, miệng.... theo biểu thị cảm xúc chân thực"*

---

## 1. VẤN ĐỀ HIỆN TRẠNG (AUDIT TRUNG THỰC)

Hệ thống hiện tại = **1 ảnh portrait tĩnh 896×896** (avatar_v3, SDXL semi-realistic) + các lớp
hiệu ứng đè **2D**:

| Lớp hiện có | Bản chất | Giới hạn |
|---|---|---|
| Portrait v3 × 11 cảm xúc | Ảnh TĨNH đổi theo state | Chuyển cảm xúc = **hard-cut** giữa 2 ảnh (crossfade 350ms) |
| Miệng nói (mouth_v2) | 1 sprite miệng đè lên | Mấp máy giả — portrait miệng **khép cười**, đè miệng mở lộ 2 lớp |
| Lông mày SVG (kiosk.js) | Đường vẽ đè lên mặt | Phong cách lệch art gốc, trông "phụ kiện" |
| Gesture layer (v6ges) | translate+scale **toàn khung ảnh** | Nhân vật không tự cử chỉ — khung ảnh được di chuyển |
| Sway/nod/thở (v6mot) | Toàn khung + micro | Cả người di chuyển cùng 1 khối như **lắc tấm ảnh** |

**Kết luận:** đúng như cảm nhận của owner — "ảnh tĩnh và nháy". Muốn nhân vật TỰ cử chỉ,
nét mặt, miệng theo cảm xúc chân thực → cần **deform mesh trên chính khuôn mặt ảnh**
(live-portrait), không phải đè hiệu ứng.

## 2. PHÂN TÍCH ASSET (đo thật, không phán đoán)

- `avatar_v3_*.png` 896×896, mặt chiếm ~60% chiều cao khung; mắt ~100px, miệng ~130px
- Frontal, đối xứng, da mịn gradient → **thuận warp mesh**, ít lộ artifact
- vision_analyze chấm khả năng sống hóa: **7.5–8/10**; yếu nhất = nói (miệng khép, không có
  khoang miệng sẵn → cần khoét vùng miệng vẽ răng/âm tối khi mở)
- Hạn chế: sợi tóc mảnh trước mặt + viền khung bake sẵn → biên độ warp phải nhỏ hoặc
  crop trong viền

## 3. KIẾN TRÚC ĐỀ XUẤT — "LIVE PORTRAIT 2.5D" (bám rễ V6.0: Model A, asset hiện có)

```
┌──────────────────────────────────────────────────────┐
│ Lớp 4: GESTURE THÂN (hiện tại) — giữ nguyên v6ges    │
│   tiến người/sway/trọng tâm quanh tâm đáy            │
├──────────────────────────────────────────────────────┤
│ Lớp 3: HEAD POSE 3D giả — MỚI                        │
│   warp mesh vùng đầu: yaw ±6°, pitch ±4°, roll ±2°   │
│   quanh trục cổ → lắc đầu/rung đầu/nghiêng THẬT      │
│   (không còn "lắc cả tấm ảnh")                       │
├──────────────────────────────────────────────────────┤
│ Lớp 2: FACE RIG — MỚI (trái tim của sprint này)      │
│   • Mắt: mí trên warp theo blink curve (đã có)       │
│   • Lông mày: warp vùng chân mày lên/xuống/đan xen   │
│     theo cảm xúc (thay SVG đè)                       │
│   • Miệng: warp vùng môi + khoét khoang miệng tối    │
│     + răng khi mở (viseme A/E/O/đóng) theo audio     │
│   • Má/cười: warp khóe miệng + má theo tone          │
├──────────────────────────────────────────────────────┤
│ Lớp 1: PORTRAIT GỐC (giữ nguyên nhận diện Model A)   │
└──────────────────────────────────────────────────────┘
```

**Face rig = triangulated mesh** (build 1 lần lúc load từ landmark cứng khai báo theo ảnh
v3 — mắt/mày/miệng/má/cằm), mỗi frame vẽ theo tam giác với offset điều khiển bởi:
- state cảm xúc (22 state hiện có) → preset biên độ mày/miệng/mắt/cười
- audio envelope (audio_mouth_driver hiện có) → openRatio miệng realtime
- nhịp sinh học: blink 4–7s, micro-saccade, nhịp thở, vi-beat 1.2–4s (chuẩn 6.mp4 đã đo)

## 4. TRÌNH TỰ THỰC HIỆN ĐỀ XUẤT (3 giai đoạn, mỗi giai đoạn nghiệm thu riêng)

| Giai đoạn | Nội dung | Tiêu chí nghiệm thu owner |
|---|---|---|
| **P1 — FACE RIG CƠ BẢN** | mesh warp mày + miệng (mở/đóng theo audio) + cười; bỏ SVG mày đè | Cherry **tự nói bằng miệng của chính ảnh**, mày nhíu/duỗi theo cảm xúc; không còn lớp vẽ đè |
| **P2 — HEAD POSE + MẮT SỐNG** | yaw/pitch/roll đầu quanh cổ; saccade mắt nhìn quanh; blink bằng warp mí | Lắc đầu/rung đầu/nghiêng là **chuyển động của đầu nhân vật**; mắt liếc tự nhiên |
| **P3 — CẢM XÚC LIÊN TỤC** | blend 2 portrait cảm xúc bằng mesh giữa các keylandmark (không hard-cut); vi-beat theo 6.mp4 | Chuyển cảm xúc **mượt như người**, không còn "nháy ảnh" |

## 5. RỦI RO + BIỆN PHÁP

| Rủi ro | Biện pháp |
|---|---|
| Warp lộ méo ở tóc/viền | crop trong viền bake + biên độ khóa theo vùng (mặt thoải, tóc khóa) |
| Miệng mở thiếu răng tối tự nhiên | vẽ khoang miệng gradient tối + răng mờ theo openRatio |
| Pi5 CPU (4 GB RAM) | mesh chỉ vùng mặt (~20 tam giác), 30fps, đo FPS thật trên Pi5 trước khi duyệt P2 |
| Lệch nhận diện Model A | mọi preset chỉ **di chuyển đặc điểm gốc**, không vẽ thêm đặc điểm mới |

## 6. ĐỀ NGHỊ PHÂN BỔ CÔNG VIỆC

1. Owner xem **PoC demo HTML** (đính kèm widget `cherry_live_poc.html`) — kéo slider
   openRatio/yaw/blink thấy ngay khác biệt so với đè sprite.
2. Nếu owner ưng hướng → duyệt **P1** (chỉ face rig cơ bản) — làm trên nhánh riêng, không
   đụng production kiosk cho tới khi E2E đạt.
3. P2/P3 duyệt lần lượt sau khi P1 nghiệm thu.

---
*Fail-honest: báo cáo dựa trên đo asset thật + audit code thật; PoC dùng đúng asset v3
của Cherry; chưa wire production, chờ duyệt.*
