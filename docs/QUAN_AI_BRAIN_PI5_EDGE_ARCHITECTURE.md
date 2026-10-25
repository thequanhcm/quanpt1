# QUAN AI BRAIN — THIẾT KẾ KIẾN TRÚC PC BRAIN CORE & RASPBERRY PI 5 EDGE
## HỆ THỐNG PHÂN TÁN AN TOÀN: TRUNG TÂM NÃO BỘ (PC) & GIAO DIỆN NGOẠI VI (EDGE CLIENT)

- **Dự án:** QUAN AI BRAIN — Digital Executive Assistant
- **Chủ nhân & Người phê chuẩn:** Quanpt1
- **Mô hình kiến trúc:** `CENTRAL BRAIN CORE (PC) <──[ Authenticated LAN ]──> EDGE INTERFACE (Raspberry Pi 5)`
- **Nguyên tắc quản trị cốt lõi:**
  1. Không nhân bản cơ sở dữ liệu chính hoặc trust anchors sang Raspberry Pi 5.
  2. Không chuyển logic quyết định quyền hạn cốt lõi ra Edge Client.
  3. Mất kết nối mạng được xem là lỗi truyền thông — tuyệt đối không coi là sự chấp thuận ngầm để thực thi.
  4. R5 bị chặn cứng, R4 cần chữ ký 2 lớp của Quanpt1.

---

## 1. PHÂN CHIA TRÁCH NHIỆM HỆ THỐNG (SYSTEM SEPARATION)

```
┌────────────────────────────────────────────────────────────────────────┐
│                        PC — CENTRAL BRAIN CORE                         │
│                                                                        │
│  • Brain Control Plane & Planning Engine                               │
│  • Local LLM Engine (Ollama: qwen2.5:7b, llama3.1)                     │
│  • Long-Term Memory Engine (SQLite: data/brain.db)                     │
│  • Self-Learning Engine & Periodic Reporter                            │
│  • Durable Task Registry (data/tasks.db)                               │
│  • Continuous Autonomy Supervisor (16 States)                          │
│  • Policy Engine & Governance State Store (data/governance.db)         │
│  • Owner Consultation Inbox (Port 8766 Cockpit)                        │
│  • High-Performance TTS/ASR Synthesis Backend                          │
│  • Edge Session & Device Pairing Manager                               │
└────────────────────────────────────────────────────────────────────────┘
                                    ▲
                                    │  Authenticated Mutual TLS /
                                    │  HMAC Signed Local WebSockets / REST
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                    RASPBERRY PI 5 — EDGE INTERFACE                     │
│                                                                        │
│  • 5" / 7" DSI/HDMI Touch Display (Kiosk Mode Fullscreen)              │
│  • Digital Avatar / Expressive Face (60fps Canvas/SVG)                 │
│  • Dual Microphone Array with Hardware Mute Switch                     │
│  • Speaker & DAC Audio Amplifier for Voice Feedback                    │
│  • Lightweight Wake Word Detection ("Tony ơi", "Hi TONY")             │
│  • Short Dialog History & Task Status Glance                           │
│  • Physical/Touch Emergency STOP Button                                │
│  • Zero Local Credentials or Core Database Duplication                │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. PC — CENTRAL BRAIN CORE (TRUNG TÂM NÃO BỘ)

Máy tính hiện tại của Quanpt1 (`E:\AI\QUAN AI BRAIN`) đóng vai trò là Trung tâm điều hành tối cao:

1. **Lưu trữ & Trí nhớ dài hạn:** Toàn bộ dữ liệu tri thức (`brain.db`), nhật ký công việc (`tasks.db`), vé tham vấn (`consultations.db`), và trạng thái an toàn (`governance.db`) được lưu trữ tại PC với cơ chế SQLite WAL an toàn.
2. **Năng lực suy luận LLM:** Tận dụng card đồ họa và CPU mạnh mẽ của PC để chạy các mô hình ngôn ngữ lớn (Ollama `qwen2.5:7b`, `llama3.1`). Raspberry Pi 5 hoàn toàn không phải gánh tải suy luận AI nặng nề này.
3. **Quản trị quyền hạn (Policy & Governance):** Toàn bộ việc thẩm định rủi ro R0-R5, kiểm tra chữ ký số của Quanpt1, xác thực OTP và áp dụng STOP/FREEZE diễn ra hoàn toàn trên PC.
4. **Session & Pairing Manager:** Quản lý danh sách các thiết bị Edge được phép kết nối; cấp phát token phiên có thời hạn; kiểm tra IP whitelist từ Windows Firewall.

---

## 3. RASPBERRY PI 5 — EDGE INTERFACE (GIAO DIỆN NGOẠI VI)

Raspberry Pi 5 là một thiết bị vật lý nhỏ gọn đặt tại bàn làm việc hoặc phòng họp của Quanpt1:

1. **Hiển thị biểu cảm (Expressive Face):** Màn hình hiển thị gương mặt số của trợ lý với chuyển động mắt, miệng và ánh sáng biểu đạt theo đúng trạng thái thời gian thực nhận từ PC (IDLE, LISTENING, THINKING, SPEAKING, WAITING_FOR_OWNER,...).
2. **Thu âm & Đánh thức bằng giọng nói:**
   - Microphone mảng (Mic Array) thu âm thanh xung quanh.
   - Chạy engine nhận dạng từ khóa đánh thức nhẹ (như Porcupine hoặc Vosk bản siêu nhẹ) bắt các cụm từ: *"Tony ơi"*, *"Hi TONY"*, *"Chào trợ lý"*.
   - Khi phát hiện từ đánh thức, phát chuông phản hồi nhẹ và truyền âm thanh giọng nói của Quanpt1 về PC qua luồng an toàn.
3. **Phát âm thanh phản hồi:** Nhận luồng âm thanh TTS đã được tổng hợp từ PC và phát qua loa ngoài với âm lượng rõ ràng, tự nhiên.
4. **Hiển thị tác vụ tóm tắt:** Hiển thị 1-2 dòng tóm tắt công việc Brain đang giải quyết hoặc hiển thị cảnh báo khi có một quyết định cần Quanpt1 bấm duyệt.
5. **Nút bảo vệ riêng tư phần cứng (Hardware Privacy):** Tích hợp công tắc ngắt nguồn micro vật lý, giúp Quanpt1 hoàn toàn an tâm khi cần không gian riêng tư.

---

## 4. LUỒNG TƯƠNG TÁC ĐẦU CUỐI (END-TO-END FLOW)

```
[Quanpt1 nói: "Tony ơi, kiểm tra tiến độ dự án"]
                    │
                    ▼
[Raspberry Pi 5: Nhận diện Wake-Word "Tony ơi"]
                    │
                    ▼ (Phát tiếng Bíp xác nhận & Bật viền sáng LISTENING)
[Raspberry Pi 5: Thu âm thanh & Gửi kèm Token HMAC lên PC]
                    │
                    ▼
[PC Brain Core: Session Manager xác thực Token & IP]
                    │
                    ▼
[PC: Speech-to-Text -> ExecutiveCoordinator -> TaskPlan -> PolicyEngine]
                    │
                    ▼ (Chuyển trạng thái THINKING -> Gửi tín hiệu về Pi 5)
[PC: Ollama LLM suy luận & CognitiveRetriever tra cứu trí nhớ]
                    │
                    ▼ (Chuyển trạng thái SPEAKING -> Gửi âm thanh TTS về Pi 5)
[Raspberry Pi 5: Expressive Face chuyển động miệng & Loa phát câu trả lời]
                    │
                    ▼
[Raspberry Pi 5: Mở cửa sổ chờ nghe nối tiếp 15 giây (Follow-up Window)]
```

---

## 5. THIẾT KẾ BẢO MẬT VÀ RANH GIỚI MẠNG (SECURITY BOUNDARY)

Để đảm bảo an toàn tuyệt đối khi kết nối thiết bị trong mạng LAN:

### 5.1. Quy trình Ghép Cặp 1 Lần (One-Time Pairing)
1. Khi cài đặt Raspberry Pi 5 lần đầu, màn hình Pi 5 hiển thị mã định danh thiết bị: `EDGE-PI5-XXXX`.
2. Quanpt1 mở Phòng Điều Hành trên PC (`http://127.0.0.1:8766/`), vào mục Quản lý Thiết bị Edge và nhập mã PIN xác thực (6 chữ số).
3. PC sinh một cặp khóa bí mật dùng riêng (`Edge Secret Token`) và lưu vào bảng `edge_devices` trong SQLite.
4. Pi 5 lưu token này trong bộ nhớ an toàn (Secure Keyring) và dùng nó để ký HMAC cho mọi gói tin gửi lên PC.

### 5.2. Chống Tấn Công Phát Lại & Nghe Lén (Anti-Replay & Encryption)
- Mỗi gói tin từ Pi 5 gửi lên PC đều chứa:
  - `timestamp_utc`: Thời điểm gửi (PC từ chối gói tin có độ lệch > 5 giây).
  - `nonce`: Chuỗi ngẫu nhiên 16 ký tự dùng 1 lần (PC kiểm tra bảng consumed nonces).
  - `hmac_signature`: Chữ ký HMAC-SHA256 trên nội dung gói tin.
- Giao tiếp qua giao thức HTTPS hoặc WebSocket bảo mật (WSS) nội bộ.

### 5.3. Ranh Giới Tường Lửa (Windows Firewall Confinement)
- Máy chủ PC hiện tại chỉ lắng nghe trên `127.0.0.1` (Localhost).
- Khi bật tính năng Edge Gateway (chỉ sau khi Quanpt1 duyệt):
  - PC mở một cổng chuyên biệt cho Edge (ví dụ TCP `:8767`).
  - Cấu hình Windows Firewall với quy tắc nghiêm ngặt: **CHỈ CHO PHÉP ĐÚNG ĐỊA CHỈ IP TĨNH CỦA RASPBERRY PI 5** kết nối vào cổng 8767. Mọi kết nối từ thiết bị lạ khác trong mạng LAN đều bị DROP ngay lập tức.

### 5.4. Hành Vi Khi Mất Kết Nối Mạng (Fail-Safe Disconnection)
- Nếu cáp mạng bị rút hoặc Wi-Fi mất kết nối:
  - Màn hình Raspberry Pi 5 lập tức chuyển sang trạng thái `OFFLINE` (Mặt xám, nhấp nháy đỏ nhẹ).
  - Hiển thị thông điệp: *"Mất kết nối với Brain Core trên PC. Đang thử kết nối lại..."*.
  - Micro tự động ngắt thu âm.
  - PC Brain Core tự động đánh dấu thiết bị Edge vào trạng thái `DISCONNECTED`.
  - Tuyệt đối không giả lập việc thực thi yêu cầu khi kết nối không thông suốt.

---

## 6. LỰA CHỌN PHẦN CỨNG GỢI Ý CHO RASPBERRY PI 5

1. **Bo mạch chính:** Raspberry Pi 5 (Bản 4GB hoặc 8GB RAM).
2. **Màn hình hiển thị:** Màn hình cảm ứng chính hãng Raspberry Pi Touch Display 2 (7 inch) hoặc Waveshare DSI LCD (5 inch).
3. **Microphone & Loa:** 
   - ReSpeaker USB Mic Array v2.0 (4 micro, có đèn LED vòng RGB tích hợp) hoặc USB Conference Speakerphone.
   - Hoặc HAT âm thanh WM8960 Audio HAT gắn trực tiếp lên chân GPIO của Pi 5.
4. **Vỏ hộp:** Vỏ in 3D để bàn nghiêng góc 15-20 độ, hướng thẳng lên mắt người dùng.
5. **Nguồn điện:** Bộ nguồn Type-C chính hãng Raspberry Pi 27W (5.1V / 5A).
