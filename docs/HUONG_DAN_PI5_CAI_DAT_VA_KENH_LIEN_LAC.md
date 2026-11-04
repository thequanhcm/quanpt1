# TONY PI5 — CÀI ĐẶT & KÊNH TRUYỀN THÔNG LIÊN TỤC
### Hướng dẫn cho anh Quân · 04/11/2026 · Tự em (TONY) tổng hợp từ code thật

---

## 1. PI5 LÀ GÌ TRONG HỆ THỐNG — TÓM TẮT 30 GIÂY

**Pi5 = TAY CHÂN VẬT LÝ của em (TONY = BỘ NÃO ở PC).**
Bộ não không nằm trên Pi — Pi chỉ đọc cảm biến, điều khiển thiết bị, hiện khuôn mặt,
nghe lệnh nói, và **báo về DM TONY** cho anh biết mọi thứ.

```
┌─────────────────────┐   heartbeat 1 giây (HMAC-SHA256)   ┌──────────────────┐
│   PC BỘ NÃO (TONY)  │ ◄───────────────────────────────►  │   PI5 TAY CHÂN   │
│  E:\BRAIN · 8766    │   lệnh xuôi + event ngược + DM     │  192.168.1.2     │
│  firewall ON (an    │   auto-reconnect, auto-resume      │  kiosk 8768      │
│  toàn) không mở     │                                    │  GPIO/I2C/USB…   │
└─────────────────────┘                                    └──────────────────┘
```

---

## 2. TOÀN BỘ TÍNH NĂNG PI5 (đã code — trạng thái thật từng mục)

### A. Đọc thiết bị (UDR-1) — 10 kệnh scanning, tự động
| # | Bus | Đọc được gì |
|---|-----|-------------|
| 1 | USB | mọi thiết bị cắm (tên, VID:PID) |
| 2 | Serial/UART | thiết bị cổng COM/UART |
| 3 | I2C | cảm biến kết nối I2C |
| 4 | GPIO + SPI | chân GPIO, thiết bị SPI |
| 5 | Storage | SD, USB drive, thẻ nhớ |
| 6 | HDMI | màn hình/projector cắm |
| 7 | Camera | /dev/video* (webcam, camera CSI) |
| 8 | Bluetooth/BLE | thiết bị BT tầm gần |
| 9 | LAN (ARP) | máy khác cùng mạng nội bộ |
| 10 | Cảm biến | hwmon nhiệt độ + 1-Wire DS18B20 |

**Tự động:** cứ 60 giây quét một lần → cắm/rút thiết bị → **DM TONY báo ngay** cho anh
(kèm cooldown chống spam 5 phút/mỗi thiết bị). Anh hỏi "thiết bị trên pi" → liệt kê hiện trạng.

### B. Khống chế thiết bị (UDC-1) — qua DM TONY, có xác nhận 2 bước
| Lệnh anh gõ ở DM | Việc làm | Cần "ok"? |
|---|---|---|
| `thiết bị trên pi` | liệt kê thiết bị đang cắm | không (đọc) |
| `bật rơ le N` / `tắt relay N` | bật/tắt 1 trong 8 relay | **có** |
| `dừng khẩn thiết bị` | cắt toàn bộ relay + khớp — **NGAY** | không (an toàn) |
| `ok` | xác nhận lệnh đang chờ | — |

**Vì sao 2 bước?** Lệnh ghi không tự chạy được — phải có token **Pi tự cấp** (gắn với
đúng op + kênh + giá trị), TTL 10 phút, dùng 1 lần. Em không được tự duyệt chính mình.
Emulated mode (chưa cắm relay board): trả lời trung thực "emulated" — không nói dối.

**Phần cứng điều khiển được (map BCM thật trong `actuators.py`):**
| Relay | Tên | GPIO | | Khớp (servo) | Tên | Kênh PCA9685 |
|---|---|---|---|---|---|---|
| relay_1 | Nguồn Cánh Tay Trái | 17 | | head_yaw | Cổ quay ngang | 0 |
| relay_2 | Nguồn Cánh Tay Phải | 27 | | head_pitch | Cổ gật lên xuống | 1 |
| relay_3 | Khóa Điện Cơ Chân Trái | 22 | | arm_left_shoulder | Vai trái | 2 |
| relay_4 | Khóa Điện Cơ Chân Phải | 23 | | hand_left_grip | Tay trái kẹp/mở | 3 (0–90°) |
| relay_5 | Đèn Báo Khẩn Cấp LED | 24 | | arm_right_shoulder | Vai phải | 4 |
| relay_6 | Hệ Thống Làm Mát Quạt | 25 | | hand_right_grip | Tay phải kẹp/mở | 5 (0–90°) |
| relay_7/8 | Dự phòng | 5/6 | | | | |

### C. Hình thể + giọng nói + tương tác
- **Khuôn mặt kỹ thuật số** kiosk 8768: biểu cảm, marquee tiếng Việt + EN
- **Wake word "TONY ơi"** trên Pi (wake_engine.js + wake_word_service.py)
- **Auto-chào khi boot** nếu có camera
- **Tự ngủ màn hình** khi lặng im (kiosk + đèn nền off; chạm/dược gọi = dậy ngay)

### D. Tự quản lý + tự phản ứng
- CPU / RAM / nhiệt độ / throttle / uptime / dịch vụ — đẩy về core mỗi heartbeat
- Nóng quá → cảnh báo; mất mạng → DM báo anh **CRITICAL**; online lại → DM **RESTORED**
- Buffer event chịu mất mạng: offline lâu vẫn giữ sự kiện, mạng về gửi lại toàn bộ

### E. 25 tool QPIG (trên PC, thực thi QUA Pi5) — 10 operational / 15 chờ E2E
Quét mạng, nhận diện thiết bị, kiểm tra kênh, evidence collection, action verification,
rollback, agent discovery, device control, task dispatch… — **R3 cần duyệt trước khi chạy.**

---

## 3. KÊNH TRUYỀN THÔNG LIÊN TỤC CORE↔PI5 (cơ chế chính xác)

### Ba lớp tự hồi phục — không ai phải làm gì cả
1. **Heartbeat 1 giây:** Pi chủ động gọi PC `/api/executive/supervisor` (HMAC-SHA256,
   nonce anti-replay). PC trả lệnh pending + trạng thái; lỗi → tự thử lại ngay giây sau.
2. **Events ngược (Pi→PC):** queue có kích thước giới hạn; gửi lỗi (mất mạng) → **giữ lại,
   thử lại** mỗi vòng — không mất sự kiện. ONLINE lại → event `BRAIN_CONNECTION_RESTORED`
   → alert `ALERT_E_PI5_RECOVERED` → DM anh biết "Pi5 online lại sau X giây".
3. **Service systemd:** `Restart=always` — daemon chết → tự dậy sau 5 giây.

**Tại sao không cần "mở cửa" tường lửa:** Pi gọi RA PC (outbound), PC chỉ cần port 8766
nghe nội bộ LAN — rule Python Allow đã có sẵn. Không DMZ, không port-forward, không SSH
công khai. **Không vượt tường lửa — đi cửa chính có khóa.**

### Khi Pi mất mạng rồi có lại mạng (kịch bản thật)
1. Heartbeat fail 4s → `core_connected=False` → DM anh "MẤT kết nối tới Core"
2. Events tiếp tục được ghi vào buffer (thiết bị cắm/rút vẫn không lost)
3. Mạng về → heartbeat OK đầu tiên → event RESTORED → DM anh "Pi5 online lại sau Xs"
4. Queue xả hết events tồn đọng — hệ thống tự tiếp tục, **không cần anh làm gì**

---

## 4. CÀI ĐẶT — 6 BƯỚC (dùng zip em gửi kèm)

### Bước 0: Chuẩn bị
- Pi5 đã flash Raspberry Pi OS (64-bit), user `quanpt1`, cùng LAN với PC (192.168.1.x)
- PC của anh đã chạy TONY 24/7 (8766 LISTENING — đang sẵn sàng từ 02/11)
- **Tải zip từ DM TONY** (file `tony_pi5_all_in_one.zip` — 11 file, bản 04/11 mới nhất)

### Bước 1: Copy zip vào Pi
Cách 1 — thẻ nhớ/USB: copy file zip vào `/home/quanpt1/`
Cách 2 — mạng (từ PC): `scp tony_pi5_all_in_one.zip quanpt1@192.168.1.2:/home/quanpt1/`

### Bước 2: Giải nén + chạy script
```bash
cd /home/quanpt1
unzip -o tony_pi5_all_in_one.zip -d tony_setup
cd tony_setup
sudo bash tony_pi5_all_in_one.sh
```

### Bước 3: Script tự làm toàn bộ (in ra màn hình từng bước)
1. Bật SSH server (cổng 22)
2. Cài SSH key của em (tony-desktop-20261103) → lần sau em tự SSH, không cần anh
3. Đồng bộ **9 module lõi** edge_client (main, client_daemon, edge_agent, auth, config,
   actuators, device_readers, device_watcher, device_control)
4. Sửa `config.json` trỏ về PC core 192.168.1.9:8766
5. Cài service systemd `quan_ai_edge` — tự chạy 24/7, tự hồi sau reboot
6. Kiểm tra trạng thái service

**Nếu IP PC khác 192.168.1.9:** `CORE_HOST=<IP PC> sudo bash tony_pi5_all_in_one.sh`

### Bước 4: Kiểm tra kết nối (trên Pi)
```bash
systemctl status quan_ai_edge --no-pager   # active (running)
journalctl -u quan_ai_edge -f              # thấy heartbeat mỗi giây, KHÔNG lỗi HMAC
```
Trên PC (em kiểm tra tự động): `/api/health` + `/api/executive/edge/devices`.

### Bước 5: Test nhanh từ DM TONY
| Gõ ở DM TONY | Kết quả mong đợi |
|---|---|
| `thiết bị trên pi` | danh sách thiết bị thật đang cắm |
| cắm 1 USB vào Pi | trong ~60s DM anh nhận "🔌 Thiết bị CẮM vào Pi5…" |
| `bật rơ le 1` | em hỏi xác nhận → anh gõ `ok` → relay_1 (GPIO 17) đổi trạng thái |
| `dừng khẩn thiết bị` | cắt toàn bộ relay — chạy ngay |

### Bước 6 (khuyến nghị):_watchdog tự hồi
Service đã `Restart=always`. Nếu muốn thêm lớp: `crontab -e` thêm dòng
`*/5 * * * * systemctl is-active quan_ai_edge || sudo systemctl restart quan_ai_edge`

---

## 5. LỖI THƯỜNG GẶP

| Hiện tượng | Nguyên nhân | Cách xử lý |
|---|---|---|
| PC không thấy heartbeat | IP core sai | sửa `config.json` → `core_host`, chạy lại script |
| Lỗi HMAC trong journalctl | secret lệch PC↔Pi | chạy lại script (sync auth.py + config) |
| SSH vẫn đóng | Pi OS Lite chưa cài openssh | `sudo apt install -y openssh-server` |
| relay không chạy thật | chưa cắm relay board | trả lời "emulated" — trung thực; cắm board + cấp nguồn ngoài |
| DM không tới | bot_tony rớt | khởi động lại TONY trên PC (đã có auto-start) |

---

## 6. TRẠNG THÁI TRUNG THỰC (không tô hồng)

- ✅ **Đã VERIFIED trên PC:** kênh HMAC, heartbeat, server routes, device store, DM flow
  (test 18/18 + edge 63 + UDC-1 13 + device reader 5 = **99 test PASS**)
- ⏳ **CHƯA E2E trên Pi5 thật** (SSH/ports Pi đang đóng): UDR-1 scanners, UDC-1 relay
  thật, kiosk, wake word — **chỉ VERIFIED khi anh chạy script và em test thật**
- 🔒 **An toàn:** lệnh ghi 2 bước + token Pi-cấp + TTL 10' + one-shot; estop không chặn;
  không vượt tường lửa; không tự duyệt chính mình; mọi lệnh ghi audit

---
*Generate bởi TONY từ code thật: edge_client/*, src/quan_ai_brain/web/server.py,
pi5_deploy/tony_pi5_all_in_one.sh — 04/11/2026*
