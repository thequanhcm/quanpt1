# KẾT NỐI PC↔Pi5 — LIVE 06/11/2026 14:25
## Bằng chứng kết nối thành công (sau khi lấy thông tin từ BRAIN_0)

### Thông tin lấy từ BRAIN_0 (workspace cũ)
- `BRAIN_0/edge_client/config.json`: core_host=192.168.10.199 (IP cũ, sai)
- `BRAIN_0/pi5_deploy/tony_pc.pub`: SSH key cũ `tony-desktop-snmi929` (sinh trên máy cũ C:\\Users\\quocd, KHÔNG có private key trên máy này)
- `BRAIN_0/pi5_deploy/tony_pi5_all_in_one.sh`: script cài đặt (đã có bản mới hơn ở E:\\BRAIN\\pi5_deploy)

### Thông tin thật trên Pi5 (lấy qua SSH)
- IP: 192.168.1.21 (MAC 2C:CF:67 = Raspberry Pi Ltd)
- core_host hiện tại: 100.102.120.6 (Tailscale cũ, sai)
- SSH key đã cài: `id_ed25519` (dell@QUANPT) — có sẵn trên máy này
- Service: quan_ai_edge active + enabled, uptime 1h32m
- Pi OS: Debian 13 (OpenSSH_10.0p2)

### Hành động đã làm (qua SSH key dell@QUANPT)
1. Backup config: `cp config.json config.json.bak_20261106`
2. Sửa core_host: 100.102.120.6 → **192.168.1.9** (IP PC Wi-Fi hiện tại)
3. Restart service: `systemctl restart quan_ai_edge`
4. Verify: kiosk status trả `core_connected: true, avatar_state: IDLE, core_host: 192.168.1.9:8766`

### Kênh 2 chiều đã verify
| Hướng | Endpoint | Kết quả |
|---|---|---|
| Pi5 → PC | POST /api/executive/edge/heartbeat | 200, PC nhận `state: READY, paired: true, seit: 0.03s` |
| PC → Pi5 | POST /api/kiosk/control (set_expression) | 200, Pi5 nhận `avatar_state: IDLE, transcript: "Kết nối PC↔Pi5 LIVE 06/11"` |
| Pi5 → PC | POST /api/executive/edge/events | 200 `accepted: 1` (alert channel) |
| Pi5 → PC | POST /api/executive/edge/converse (audio) | 200 (STT im lặng → text rỗng, đúng thiết kế) |

### Trạng thái hiện tại
- **Kênh điều khiển PC↔Pi5: LIVE** ✓
- Kiosk UI (chromium màn 7" DSI): chưa bật (Pi5 headless, DISPLAY rỗng — bình thường khi không gắn màn vật lý)
- UDR-1 device events (USB cắm/rút): chưa sync — cần chạy script zip 11 file để đồng bộ 9 module edge_client mới

### Việc còn lại (chờ owner duyệt)
- Chạy `sudo bash tony_pi5_all_in_one.sh` (zip 11 file trong DM TONY) để sync UDR-1/UDC-1 + cài key TONY mới
- Sau đó: G1 LIVE VALIDATION 16 mục (UDR device events, UDC điều khiển có phê duyệt, kênh NetChat)


=== KIỂM TRA TAILSCLANE (06/11 ~17:40, yêu cầu owner) ===
Mesh Tailscale (tài khoản thequan.hcm@gmail.com) hiện có 4 thiết bị:
- 100.100.83.59  quanpt1            (Pi5, linux)  — ONLINE
- 100.102.120.6  desktop-snmi929    (windows)     — OFFLINE 15h (máy CŨ — chính là core_host sai trong config Pi5)
- 100.122.235.105 iphone-15-pro-max (iOS)         — offline 56 ngày
- 100.92.219.98  quanpt             (windows)     — offline 55 ngày

KẾT LUẬN TAILSCLANE:
- Pi5 tailscaled ACTIVE, IP mesh 100.100.83.59, Tailscale v1.104.5 hoạt động chuẩn
- Máy PC CŨ (desktop-snmi929) = nguồn gốc core_host 100.102.120.6 trong config — đã tắt → kiosk OFFLINE trước đó
- PC MỚI (máy này) CHƯA cài Tailscale → chưa có IP trong mesh

HAI PHƯƠNG ÁN KÊNH PC↔Pi5:
(A) LAN Wi-Fi 192.168.1.9 ↔ 192.168.1.21 — ĐANG LIVE (đã verify heartbeat/paired/control) ✓
(B) Tailscale mesh — cần CÀI MỚI Tailscale trên PC (winget install Tailscale.Tailscale)
    + đăng nhập thequan.hcm@gmail.com → nhận IP mới → đổi core_host trên Pi5 sang IP đó
    → ƯU ĐIỂM: không phụ thuộc Wi-Fi/đổi IP router;NHƯNG = cài phần mềm mới → CẦN DUYỆT OWNER

KHUYẾN NGHỊ: giữ (A) làm kênh chính; nếu anh muốn kênh dự phòng mesh qua Internet
(khi ra ngoài mạng nhà), duyệt để em cài Tailscale trên PC (lệnh winget có sẵn, ~2 phút).
