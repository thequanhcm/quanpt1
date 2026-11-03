# KẾT NỐI HÌNH THỂ Pi 5 — BẤT KỂ MẠNG NÀO (TAILSCALE)
# Cập nhật 31/10/2026 — Phương án "Pi 5 chỉ cần có mạng là kết nối được"

## Ý CHÍNH
Anh muốn: **Pi 5 chỉ cần kết nối mạng BẤT KỲ (Wi-Fi nhà, Wi-Fi khách, 4G hotspot,
điện thoại share mạng...) là PC kết nối thông — KHÔNG cần cùng mạng Wi-Fi.**

→ Giải pháp: **TAILSCALE** (mạng riêng ảo, miễn phí cho 3 thiết bị).
Tailscale tạo "mạng riêng" — mỗi thiết bị có 1 IP cố định **100.x.y.z**.
Dù Pi ở mạng nào (nhà, công ty, 4G), Pi và PC vẫn như ở cùng 1 LAN.

## TRẠNG THÁI HIỆN TẠI (đã kiểm tra thật từng bước)

| Hạng mục | Trạng thái |
|---|---|
| PC DESKTOP-SNMI929 | IP LAN: 192.168.10.199 (Ethernet, gateway 192.168.10.1) |
| PC ra internet | ✅ OK (Google DNS / Tailscale / Google web đều thông) |
| Tailscale trên PC | ✅ ĐÃ CÀI (v1.104.4, service Running) |
| Tailscale login PC | ⏳ **CHỜ ANH BẤM LINK** (xem BƯỚC 1 bên dưới) |
| Server 8766 nhận LAN | ✅ OK (bind 0.0.0.0, pythonw có rule firewall Allow) |
| Firewall profile | Public — nhưng pythonw đã có rule Allow nên không chặn |
| Pi 5 (192.168.1.21 cũ) | ❌ Không vào được (subnet khác) |
| HMAC secret 2 đầu | ✅ Khớp (config.json edge_client) |

## BƯỚC 1 (ANH LÀM — 30 GIÂY): ĐĂNG NHẬP TAILSCALE TRÊN PC
Mở trình duyệt, vào link này:
**https://login.tailscale.com/a/ac17fe901cc4a**

- Nếu anh có tài khoản Google/Microsoft/GitHub → đăng nhập bằng tài khoản đó.
- Nếu chưa có → chọn "Sign up with Google" (1 phút).
- Sau khi đăng nhập → nhấn **"Connect"** → PC vào mạng riêng Tailscale.

## BƯỚC 2 (ANH LÀM — 2 PHÚT): CÀI TAILSCALE TRÊN Pi 5
Cần 1 màn hình + bàn phím cắm vào Pi (hoặc SSH từ máy nào đó trong mạng của Pi):

```bash
# Trên Pi 5 (terminal)
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
# → In ra 1 link, mở link đó bằng trình duyệt ĐIỆN THOẠI/laptop
# → Đăng nhập BẰNG CÙNG TÀI KHOẢN với bước 1
# → Pi vào mạng, có IP 100.x.y.z cố định
```

Xem IP mới của Pi:
```bash
tailscale ip -4     # ví dụ: 100.101.102.103
```

## BƯỚC 3 (ANH LÀM — 1 PHÚT): CHỈ IP MỚI CHO Pi
```bash
# Trên Pi 5
sudo nano ~/edge_client/config.json
# Sửa:
#   "core_host": "192.168.10.199"  →  "core_host": "<IP 100.x.y.z CỦA PC>"
# (PC cũng có IP 100.x.y.z riêng — xem bằng lệnh `tailscale ip -4` trên PC)
# Lưu: Ctrl+O, Enter, Ctrl+X

# Restart daemon
sudo systemctl restart quan_ai_edge
```

## BƯỚC 4 (EM LÀM): XÁC MINH TỪ PC
Sau khi anh làm xong 3 bước, em chạy lệnh kiểm tra:
- `tailscale status` → thấy Pi trong danh sách (ID: EDGE-PI5-DESK-01)
- `curl http://<IP-Pi-100.x>:8768/` → kiosk của Pi trả lời
- Dashboard http://127.0.0.1:8766/ → Tab Edge → trạng thái **ONLINE/READY**
- Heartbeat mỗi 1 giây → xác nhận paired=true

## TÓM TẮT QUY TRÌNH SAU NÀY (24/7, KHÔNG CẦN CHẠM LẠI)
- Pi 5: `quan_ai_edge.service` systemd tự chạy khi boot (Restart=always, 3s).
- Pi mất Wi-Fi rồi có lại → tự kết nối lại Tailscale (đã login 1 lần, nhớ mãi).
- Pi đổi mạng (Wi-Fi nhà → 4G điện thoại → Wi-Fi công ty) → **KHÔNG cần làm gì**,
  IP Tailscale 100.x.y.z không đổi, heartbeat tự chảy lại trong ~10 giây.
- PC đổi mạng cũng vậy — không cần cấu hình lại.
- PC ↔ Pi mã hóa WireGuard đầu-cuối, không ai trên mạng công cộng nghe được.

## LƯU Ý BẢO MẬT
- Tailscale = VPN WireGuard chuẩn; Pi chỉ nói chuyện với thiết bị trong "tailnet" của anh.
- KHÔNG mở port router, KHÔNG DDNS, KHÔNG expose ra internet.
- HMAC secret giữa Pi↔PC vẫn chạy trên lớp Tailscale (2 lớp bảo mật).
- Nếu anh muốn chặt hơn: trên admin console Tailscale có thể hạn chế
  "chỉ thiết bị A với thiết bị B được nói chuyện" (ACL).

## KIỂM TRA PC PHÍA EM ĐÃ LÀM (evidence 31/10/2026)
1. ✅ Internet thông (Google DNS/Tailscale/Google web OK)
2. ✅ Tailscale 1.104.4 cài thành công qua winget, service Running
3. ✅ Server 8766 nhận kết nối từ IP LAN (socket test OK)
4. ✅ Firewall: pythonw.exe đã có Inbound Allow (không cần mở thêm)
5. ✅ edge_client/config.json trên PC đã trỏ core_host=192.168.10.199
   (chờ anh login Tailscale xong sẽ đổi sang IP 100.x.y.z của PC)
6. ✅ setup_systemd_247.sh trên Pi đã cấu hình sẵn SSH key + systemd 24/7
7. ⏳ Chờ: (a) anh bấm link login PC, (b) cài Tailscale trên Pi, (c) Pi rejoined

## NẾU KHÔNG MUỐN TAILSCALE (các phương án khác)
- **Cùng Wi-Fi**: đơn giản nhất, chỉ cần sửa core_host về IP LAN của PC
  (hướng dẫn cũ: docs/PI5_KET_NOI_LAI_HUONG_DAN.md).
- **Port forward + DDNS**: phải cấu hình router, không an toàn bằng, KHÔNG khuyên.
- **Relay tự viết**: qua gateway netMind — cần auth, phức tạp, không cần thiết.
