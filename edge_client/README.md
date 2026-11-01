# QUAN AI BRAIN — RASPBERRY PI 5 EDGE CLIENT
## Hướng Dẫn Cài Đặt One-Click, Màn Hình Cảm Ứng 7" DSI Touchscreen 2 (1280x720) & Trợ Lý Số Mẫu F

Tài liệu này cung cấp hướng dẫn toàn diện từ A-Z để triển khai **QUAN AI BRAIN Edge Client** lên bo mạch **Raspberry Pi 5 (4GB/8GB RAM)** kết hợp **Màn hình cảm ứng 7" DSI Touchscreen 2 (1280x720)** và bộ hình thể số **Cô Trợ Lý AI Mẫu F** kết nối hai chiều với PC Core qua Wi-Fi nội bộ.

---

### 1. NGUYÊN TẮC BẢO MẬT & KIẾN TRÚC PHÂN TÁCH HAI HỆ THỐNG

Hệ thống được thiết kế theo mô hình **Central Brain Core (PC) & Physical Embodiment (Raspberry Pi 5)**:

```
+-------------------------------------------------------+
|  MÁY TÍNH TRUNG TÂM (PC CORE - Windows 11)           |
|  - Mô hình AI: Ollama qwen2.5:7b (Local Port 11434)   |
|  - Bộ nhớ dài hạn & Tri thức: SQLite (brain.db)       |
|  - Ràng buộc an toàn: R5 Hard-Blocked, R4 Owner-Gated |
|  - Executive Desk Server: Cổng 8766 (Lắng nghe LAN)   |
+---------------------------+---------------------------+
                            |  Ký số hai chiều HMAC-SHA256
      Cùng Mạng Wi-Fi LAN   |  Chống phát lại Nonce + Timestamp
                            |  Bảo vệ trôi đồng hồ <= 10s
+---------------------------+---------------------------+
|  RASPBERRY PI 5 (4GB RAM) — EDGE PHYSICAL INTERFACE   |
|  - Màn hình hiển thị: 7" DSI Touchscreen 2 (1280x720) |
|  - Trợ lý số Mẫu F: Canvas 2.5D 60 FPS siêu nhẹ       |
|  - Micro-Expressions: Lông mày, nụ cười mắt, ngữ cảnh|
|  - Khẩu hình tiếng Việt thời gian thực (MouthSync)    |
|  - Bộ điều khiển 8 kênh Rơ-le (Relay Board)           |
|  - Bộ điều khiển chuyển động Tay Chân & Khớp Cổ       |
|  - Nút bấm vật lý & cảm ứng ngắt khẩn cấp Fail-safe   |
+-------------------------------------------------------+
```

1. **Zero Core Database On Edge:** Toàn bộ cơ sở dữ liệu (`brain.db`, `tasks.db`, `governance.db`), chìa khóa bảo mật và LLM chỉ nằm trên PC của anh. Không bao giờ lưu trữ cơ sở dữ liệu hay token quản trị trên thẻ nhớ Pi 5.
2. **Ghép cặp 1 lần duy nhất (One-Time Pairing):** Khi chạy lần đầu, Pi 5 tự động quét Wi-Fi tìm IP PC Core, xác thực mã PIN (`888666`) một lần duy nhất, nhận mã khóa chia sẻ `shared_secret` lưu an toàn vào `config.json`. Mọi lần khởi động lại sau đó hệ thống **hoàn toàn tự động đồng bộ**, không cần hỏi lại.
3. **Fail-Safe Disconnect:** Khi mất sóng Wi-Fi hoặc PC tắt, Pi 5 lập tức chuyển sang chế độ `OFFLINE`, cô trợ lý Mẫu F nhắm mắt nghỉ ngơi thanh thản, khóa mọi rơ-le và đưa cánh tay về vị trí an toàn, ngắt micro thu âm.

---

### 2. YÊU CẦU THIẾT BỊ VẬT LÝ

| Thành phần | Thông số khuyến nghị | Ghi chú |
| :--- | :--- | :--- |
| **Bo mạch chính** | Raspberry Pi 5 (4GB RAM hoặc 8GB RAM) | Hệ điều hành Raspberry Pi OS 64-bit (Debian Bookworm) |
| **Màn hình hiển thị** | **7" DSI Touchscreen 2 (1280x720)** | Màn hình cảm ứng điện dung chính hãng Raspberry Pi |
| **Nguồn điện** | Nguồn USB Type-C 27W (5.1V / 5A) | Đảm bảo đủ dòng khi kéo cùng lúc màn hình và rơ-le |
| **Mạch Rơ-le** | Mạch 8-Channel Relay Module 5V (Optocoupler) | Điều khiển đóng cắt nguồn điện thiết bị ngoại vi |
| **Động cơ Servo** | 6-DOF Servos (MG996R / PCA9685 I2C Board) | Điều khiển cổ gật/xoay và cánh tay, bàn tay |
| **Âm thanh** | USB Conference Speakerphone hoặc ReSpeaker Array | Đánh thức giọng nói ("Hi TONY") & Đàm thoại rảnh tay |

---

### 3. CÀI ĐẶT TỰ ĐỘNG BẬT GƯƠNG MẶT MẪU F VÀ CHẠY NGẦM 24/7 TRÊN PI 5

Hệ thống hỗ trợ cơ chế chạy ngầm liên tục 24/7. Mỗi khi anh cấp nguồn hoặc khởi động lại Pi 5, màn hình cảm ứng 7" DSI lập tức tự động bật toàn màn hình gương mặt **Cô Trợ Lý AI Mẫu F** với đôi mắt chớp tự nhiên, nhịp thở vi mô và sẵn sàng nhận diện lệnh từ PC qua Wi-Fi.

#### Lệnh kích hoạt 1 lần duy nhất trên Raspberry Pi 5:
Mở Terminal trên Pi 5 (hoặc qua SSH) và chạy:
```bash
cd ~/Desktop/edge_client && bash install_autostart_247.sh
```
*(Hoặc nếu thư mục đặt tại `~/quan_ai_edge`, chạy `cd ~/quan_ai_edge && bash install_autostart_247.sh`)*

#### Cơ chế hoạt động 24/7 thông minh:
1. **Tự khởi động cùng nguồn điện:** Script tự động đăng ký `~/.config/autostart/quan_kiosk.desktop`. Cứ có nguồn điện là gương mặt cô trợ lý hiện lên ngay lập tức.
2. **Chống tắt màn hình (Anti-Blanking):** Tự động vô hiệu hóa chế độ ngủ màn hình (`xset s off -dpms s noblank`), giúp màn hình 7" luôn sáng rõ 24/7.
3. **Tự phục hồi (Self-Healing Loop):** Nếu trình duyệt bị tắt bất ngờ, watchdog tự động mở lại sau 2 giây.
4. **Trực chiến Standby & Tạm Dừng:**
   - Khi Pi 5 bật: Cô trợ lý luôn ở trạng thái Standby tỉnh táo, mắt chớp tự nhiên chờ kết nối.
   - Khi anh bấm **"⏸️ Tạm Dừng Trợ Lý"** trên PC: Cô trợ lý nhắm mắt nghỉ ngơi thanh thản.
   - Khi anh bấm **"▶️ Kích Hoạt Hoạt Động"**: Cô trợ lý lập tức mở mắt, mỉm cười và chào anh!

---

### 4. ĐIỀU KHIỂN & TRUYỀN DỮ LIỆU TỪ MÁY TÍNH QUA BÀN ĐIỀU HÀNH (http://127.0.0.1:8766/)

Chỉ cần Pi 5 và PC kết nối cùng mạng Wi-Fi, anh có thể kiểm soát toàn diện Pi 5 từ trình duyệt trên máy tính mà không cần cắm chuột/phím vào Pi 5:
- **Tab "Đồng Bộ Edge Pi 5" trên Web UI:**
  - **Sơ đồ luồng Wi-Fi Realtime:** Hiển thị IP PC (`192.168.1.11`), IP Pi 5 (`192.168.1.21`), RTT độ trễ (~11ms) và biểu đồ sóng Ping thời gian thực.
  - **Màn hình ảo (Virtual Screen Mirror):** Xem trước chính xác những gì đang hiển thị trên màn hình Pi 5.
  - **9 nút đổi biểu cảm tức thì:** Sẵn sàng, Mỉm cười, Suy nghĩ, Lắng nghe, Trả lời, Nghiên cứu, v.v.
  - **Thử nghiệm khẩu hình tiếng Việt (Mouth-Sync):** Nhập câu nói, cả PC và Pi 5 cùng phát âm thanh và mấp máy môi đồng bộ.
  - **Tải lên & Quản lý tệp tin từ xa (Remote File Manager):**
    + Bảng danh sách hiển thị tức thì toàn bộ 20 tài sản (ảnh chân dung Mẫu F, khẩu hình Viseme, âm thanh, biểu cảm).
    + Nút **"📡 Đồng bộ"** trên từng dòng: Cho phép đồng bộ ngay từng tệp sang Pi 5.
    + Nút **"🔄 Đồng Bộ Toàn Bộ Sang Pi 5"**: Tự động chuyển toàn bộ ảnh Model F sang Pi 5 và ra lệnh cho Pi 5 tải lại giao diện chỉ trong 1 giây.
    + Nút **"📤 Tải Lên Tệp Mới"**: Tải ảnh chân dung mới, âm thanh, tệp cấu hình trực tiếp từ PC sang thẻ nhớ Pi 5.
    + Nút **"🔄 Tải Lại Kiosk Pi 5"**: Làm mới màn hình Pi 5 từ xa.
    + Điều chỉnh âm lượng loa Pi 5 trực tiếp bằng thanh trượt (0% - 100%).

> **Mẹo đồng bộ nhanh từ Terminal Pi 5:** Nếu anh muốn tải hoặc đồng bộ ngay toàn bộ 20 ảnh chân dung Model F từ Terminal Pi 5, chỉ cần dán 1 dòng lệnh sau:
> ```bash
> curl -s http://192.168.1.11:8766/edge_client/sync_assets.py | python3
> ```

---

### 5. SƠ ĐỒ ĐẤU DÂY ĐIỀU KHIỂN RƠ-LE VÀ KHỚP TAY CHÂN

Tệp `edge_client/actuators.py` đã định sẵn sơ đồ chân GPIO BCM chuẩn công nghiệp:

#### 4.1. Bảng phân bổ 8 kênh Rơ-le (8-Channel Relay Module)
| Kênh Relay | Tên Chức Năng | Chân GPIO (BCM) | Chân vật lý Pin Header | Trạng thái ban đầu |
| :---: | :--- | :---: | :---: | :---: |
| **Relay 1** | Nguồn Cánh Tay Trái | GPIO 17 | Pin 11 | Hở mạch (OFF/OPEN) |
| **Relay 2** | Nguồn Cánh Tay Phải | GPIO 27 | Pin 13 | Hở mạch (OFF/OPEN) |
| **Relay 3** | Khóa Điện Cơ Chân Trái | GPIO 22 | Pin 15 | Hở mạch (OFF/OPEN) |
| **Relay 4** | Khóa Điện Cơ Chân Phải | GPIO 23 | Pin 16 | Hở mạch (OFF/OPEN) |
| **Relay 5** | Đèn Báo Khẩn Cấp LED | GPIO 24 | Pin 18 | Hở mạch (OFF/OPEN) |
| **Relay 6** | Hệ Thống Làm Mát Quạt | GPIO 25 | Pin 22 | Hở mạch (OFF/OPEN) |
| **Relay 7** | Rơ-le Dự Phòng Kênh 7 | GPIO 5 | Pin 29 | Hở mạch (OFF/OPEN) |
| **Relay 8** | Rơ-le Dự Phòng Kênh 8 | GPIO 6 | Pin 31 | Hở mạch (OFF/OPEN) |

> **Cơ chế An Toàn Relay:** Các mạch rơ-le thông dụng sử dụng mức kích dẫn thấp (Active-Low). `actuators.py` tự động kích hoạt ở mức HIGH khi khởi động để đảm bảo khi cấp nguồn, toàn bộ thiết bị ngoại vi đều ở trạng thái ngắt điện an toàn cho đến khi nhận lệnh có xác thực từ hệ thống.

#### 4.2. Bảng phân bổ 6 khớp cử động tay chân & cổ (6-DOF Servo Joints)
| Khớp Cử Động | Kênh PWM / Driver | Góc tối thiểu | Góc tối đa | Vị trí an toàn (Home) | Chức năng |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **head_yaw** | Kênh 0 (PCA9685) | 0° (Trái) | 180° (Phải) | **90°** (Nhìn thẳng) | Khớp cổ xoay ngang nhìn theo người dùng |
| **head_pitch** | Kênh 1 (PCA9685) | 45° (Ngửa) | 135° (Cúi) | **90°** (Ngang) | Khớp cổ gật lên xuống theo nhịp đàm thoại |
| **arm_left_shoulder** | Kênh 2 (PCA9685) | 0° (Thu) | 180° (Vươn) | **90°** (Thả lỏng) | Khớp vai nâng/hạ cánh tay trái |
| **hand_left_grip** | Kênh 3 (PCA9685) | 0° (Mở) | 90° (Kẹp) | **0°** (Mở tự do) | Bàn tay trái kẹp mở đồ vật |
| **arm_right_shoulder** | Kênh 4 (PCA9685) | 0° (Thu) | 180° (Vươn) | **90°** (Thả lỏng) | Khớp vai nâng/hạ cánh tay phải |
| **hand_right_grip** | Kênh 5 (PCA9685) | 0° (Mở) | 90° (Kẹp) | **0°** (Mở tự do) | Bàn tay phải kẹp mở đồ vật |

---

### 5. LỆNH ĐIỀU KHIỂN & KIỂM TRA THỬ NGHIỆM

Anh có thể mở Terminal trên Raspberry Pi 5 để kiểm tra từng bộ phận:

#### 5.1. Kiểm tra trạng thái toàn bộ phần cứng:
```bash
python3 -c "from edge_client.actuators import ActuatorController; import json; print(json.dumps(ActuatorController().get_status(), indent=2))"
```

#### 5.2. Đóng / Ngắt thử rơ-le (Ví dụ: Bật quạt tản nhiệt kênh 6):
```bash
python3 -c "from edge_client.actuators import ActuatorController; c = ActuatorController(); c.set_relay('relay_6', 'CLOSED'); print('Đã bật quạt làm mát')"
```

#### 5.3. Xoay góc cổ hoặc giơ tay chào:
```bash
python3 -c "from edge_client.actuators import ActuatorController; c = ActuatorController(); c.set_joint_angle('head_yaw', 110.0); print('Đã xoay đầu sang phải 20 độ')"
```

#### 5.4. LỆNH DỪNG KHẨN CẤP PHẦN CỨNG (EMERGENCY CUTOFF):
```bash
python3 -c "from edge_client.actuators import ActuatorController; c = ActuatorController(); print(c.emergency_all_stop())"
```
Lệnh này lập tức:
- Ngắt điện toàn bộ 8 rơ-le ngay lập tức (`state = OPEN`).
- Khóa toàn bộ các khớp servo về vị trí nghỉ an toàn (`90°`), nhả các kẹp tay (`0°`).

---

### 6. CÁC TÍNH NĂNG TRÊN MÀN HÌNH CẢM ỨNG KIOSK CỦA PI 5

Giao diện Kiosk (`kiosk.html`, `kiosk.css`, `kiosk.js`) chạy tại `http://127.0.0.1:8768`:
1. **Digital Avatar TONY Biểu Cảm:**
   - Đôi mắt Cybernetic có mí mắt chuyển động, đồng tử co giãn.
   - Tự động thay đổi diện mạo theo 11 trạng thái: `IDLE` (nghỉ ngơi), `LISTENING` (lắng nghe giọng anh), `THINKING` (suy nghĩ tính toán), `SPEAKING` (phát âm), `WAITING_FOR_OWNER` (chờ anh phê duyệt), `SAFE_MODE` (chế độ bảo vệ), `OFFLINE` (mất mạng).
2. **Dynamic Audio Waveform:** Hiển thị dạng sóng âm thanh trực tiếp khi anh nói chuyện hoặc khi TONY trả lời.
3. **Nút Bấm Cảm Ứng Lớn Dành Cho Ngón Tay:**
   - **`[🎤 TONY ƠI...]`**: Nhấn một chạm để nói chuyện ngay lập tức nếu không muốn gọi to từ đánh thức.
   - **`[🛑 DỪNG KHẨN CẤP]`**: Nút bấm to màu đỏ với khung cảnh báo viền đỏ. Chạm vào nút này sẽ gửi lệnh dừng có chữ ký số HMAC ngắt cả PC lẫn bo mạch rơ-le chỉ trong **0.05 giây**.
4. **Băng Báo Phê Duyệt (Consultation Alert):** Khi có tác vụ rủi ro cao (R4) cần anh duyệt, trên màn hình Pi 5 sẽ nhấp nháy dải đèn cam và thông báo để anh đưa ra quyết định trực tiếp.
