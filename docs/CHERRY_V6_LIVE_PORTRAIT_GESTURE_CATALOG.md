# CHERRY V6-001 — PHỤ LỤC A: CATALOGUE CỬ CHỈ TỪ TOÀN BỘ VIDEO MẪU (E:\BRAIN\Pi5)
**Ngày:** 15/11/2026 · **Tình trạng:** DỰ THẢO — phục vụ thiết kế Face/Gesture Rig
**Chỉ đạo owner:** *"tham khảo lại các cử chỉ toàn bộ trong các video ở E:\BRAIN\Pi5 để xây dựng kỹ, hoàn hảo"*

## 0. TỔNG QUAN NGUỒN TƯ LIỆU (7 video — 1 trùng lặp đã loại)

| Video | Thời lượng | Loại | Trạng thái phân tích |
|---|---|---|---|
| **6.mp4** | 99 phút | **Người nói trực tiếp camera** (English with CTM) | ✅ Đo đủ 3 đoạn + 8 frame + vision (đã wire v6mot/v6ges) |
| **4.mp4 = mẫu.mp4** | 40.5 phút | Ca sĩ (nữ, keyboard) | ✅ md5 `c324f832` TRÙNG NHAU — 1 nguồn, đã đo (v6mot) |
| **3.mp4** | 5.4 phút | Ca sĩ | ✅ Đo motion_345 (flow 37.4px, chu kỳ 9–12.9s) |
| **5.mp4** | 5.1 phút | Ban nhạc (trống/sax/piano/ca sĩ) | ✅ MỚI: 6 frame + vision catalogue + flow |
| **vi 1.mp4** | 5.0 phút | Người mẫu cinematic (2 chương: trắng/đỏ) | ✅ MỚI: 6 frame + vision catalogue + flow |
| **vi 2.mp4** | 6.0 phút | Người mẫu cinematic (áo dài, 6 shot ~29s) | ✅ MỚI: 6 frame + vision catalogue + flow |
| **Kết luận nguồn** | | | **2 chế độ cử chỉ đối lập: "người nói camera" (6) vs "biểu diễn/cinematic" (3,4,5,vi1,vi2)** |

**Số liệu đo thật (optical flow):**
- vi1: flow 0.0–1.22px, đầu V/H 0.87–1.18 (gật ≳ nghiêng), nhịp ~1 cử chỉ/5–10s
- vi2: flow 0.16–0.87px, V/H 0.87–1.08, shot-hold ~29s (chân dung động), mật độ tay ≈ 0
- v5: flow 0.41–1.57px, V/H 0.41–1.26 (nghiêng > gật khi chơi nhạc cụ), nhịp nhanh/không hold ở trống

## 1. CATALOGUE CỬ CHỈ TỔNG HỢP (18 mục — gộp trùng, xếp theo giá trị cho CHERRY)

### NHÓM A — NGƯỜI NÓI CAMERA (CHUẨN CHÍNH CHO CHERRY — từ 6.mp4)
| # | Cử chỉ | Tham số đo/tham chiếu | Áp dụng cho rig |
|---|---|---|---|
| A1 | **Gật đầu theo câu nói** (vertical dominant) | V/H 1.11–1.55; chu kỳ 1.4–4s | head pitch nod theo cadence câu + openRatio pulse (đã wire v6mot, giữ) |
| A2 | **Đứng im vi-chuyển động 87–98%** | micro_still 0.87–0.98 | micro-rest ×0.4–0.5 (đã wire) |
| A3 | **Đan/ấp 2 tay trước bụng khi giải thích** | vision 8 frame 6.mp4 | gesture tay — CHỈ làm khi portrait có vùng tay (hiện crop ngực — khoanh dựng P3 nếu mở rộng khung) |
| A4 | **Trọng tâm chuyển ngang nhẹ nhịp 2.8/3.9s** | v6ges beat | giữ (đã wire) |
| A5 | **Cười nhẹ khép môi khi nói**, khóe má nhích | vision 6.mp4 | face rig: smile preset theo tone (P1) |
| A6 | **Gật nhấn khi kết câu/khoanh tay khoe ý** | chu kỳ 1.03–1.67s đoạn giữa | nod pulse ×1.3 ở token cuối câu (P2) |

### NHÓM B — BIỂU CẢM MẶT SỐNG (tổng hợp 6 + vi2 + 5 + mẫu)
| # | Cử chỉ | Nguồn | Áp dụng |
|---|---|---|---|
| B1 | **Chớp mắt tự nhiên** | 6.mp4, vi2 (F1 nhắm) | blink curve 4–7s ngẫu nhiên + đôi blink kép (P2) |
| B2 | **Mắt nhắm đắm mình khi cảm xúc cao** | 5.mp4 (ca sĩ/sax), vi1 (F2) | preset THINKING/EMPATHETIC: mắt thu hẹp 30–50% (P2 saccade+lid) |
| B3 | **Nụ cười môi khép cường độ thấp** (không răng trừ khi nói) | vi2 signature | smile base 0.2–0.35, mở răng CHỈ khi openRatio>0.3 (P1) |
| B4 | **Lông mày nhíu khi tập trung/chìm vào nốt** | 5.mp4 sax, vi1 (F4 cúi+hạ mắt) | brow warp −0.3..−0.7 theo THINKING/WARNING (P1) |
| B5 | **Mắt hạ/nghiêng khi e ấp, ngẩng khi tự tin** | vi1 (F4 hạ mắt), vi2 (F3 eye-contact) | gaze preset theo state (P2) |
| B6 | **"Khoảnh khắc kết nối camera"** — đổi từ nhìn xa sang nhìn thẳng | vi2 F3 duy nhất | eye-contact chủ động khi xưng hô với owner (P2) |

### NHÓM C — CINEMATIC/MUSIC (MƯỢN KHI TONE VUI/Biểu DIỄN — đã một phần wire)
| # | Cử chỉ | Nguồn | Áp dụng |
|---|---|---|---|
| C1 | Sway thân nhịp chậm 9–12.9s + 50s | 3.mp4, 4.mp4 | giữ v6mot tầng 0.08Hz+0.02Hz |
| C2 | Nghiêng đầu vai khi đắm mình (V/H 0.41–0.75) | 4.mp4, v5 | tilt khi tone vui ×1.2 (v6ges phraseSway) |
| C3 | "Ngắm lên cao" — đầu ngửa nhẹ nhìn lên | vi1 F5/F6 | preset SUCCESS: cằm nâng 3–5° + mắt nhìn lên nhẹ (P2) |
| C4 | Vải/tóc bay khi thân tĩnh | vi1/vi2 toàn bộ | hair strand 1-2 sợi hiệu ứng nhẹ bằng warp (P3, cẩn trọng "không vẽ thêm") |
| C5 | Giữ pose dài (hold 5–15s) giữa các cử chỉ | vi1/vi2 | dải nghỉ giữa các gesture ≥4s (đã có micro-rest) |
| C6 | Quay đầu nhìn sang "đồng đội" rồi trở lại | 5.mp4 piano | glance ngang 20–30° khi nhắc hệ thống khác (P2/P3) |

## 2. NHỊP TỔNG THỂ KHUYẾN NGHỊ (hợp nhất số đo)

- **Chu kỳ nền:** vi-beat 1.2–4s (6.mp4) chồng lên sway chậm 9–12.9s + 50s (3/4/5) — đúng kiến trúc 2 tầng v6mot hiện tại, thêm tầng micro mặt
- **Tỷ lệ nghỉ:** tổng thời gian "đứng im" mục tiêu 70–85% (dải 6.mp4 87–98% vs cinematic thấp hơn) — Cherry nói nhiều sẽ về phía 75%
- **Đổi pose lớn:** mỗi 8–15s một thay đổi tư thế (cân bằng giữa 6.mp4 ~1/1.4–4s ở đầu và cinematic hold 5–15s)

## 3. GẮN VÀO KẾ HOẠCH P1/P2/P3 (báo cáo chính)

- **P1 (face rig cơ bản):** B3, B4, A5 + miệng theo audio (A1-hỗ trợ)
- **P2 (head pose + mắt sống):** A1, A6, B1, B2, B5, B6, C3, C6
- **P3 (cảm xúc liên tục + mở rộng):** A3 (nếu mở khung nhân vật), B6 mở rộng, C4, C6

## 4. TỆP ĐÍNH KÈM
- `data/gesture_catalog_vi_videos.json` (thời lượng + flow 3 video mới)
- `data/frames_vi_sheets/sheet_{vi1,vi2,v5}.jpg` (contact sheet 6 frame/video)
- `data/frames_vi/*.jpg` (42 frame gốc)
- Số liệu cũ: `motion_345_*.json`, `motion_6_*.json` (vẫn hiệu lực)
