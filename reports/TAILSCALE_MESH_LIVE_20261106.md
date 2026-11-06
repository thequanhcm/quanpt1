# TAILSCLANE MESH PC↔Pi5 — LIVE 06/11/2026 (owner duyệt cài + cấu hình)

## Hành động đã thực hiện
1. `winget install Tailscale.Tailscale` — **cài xong v1.104.5** (35s, service Tailscale Running)
2. Máy PC **tự động nhận node cũ `quanpt` (100.92.219.98)** trong mesh thequan.hcm@ — không cần login lại
   (node key vẫn còn trong tài khoản; trước đó node này offline 55 ngày)
3. Verify mesh: `tailscale ping 100.100.83.59` → **pong via 192.168.1.21:41641 in 2-4ms (direct, không DERP relay)**
4. Cấu hình Pi5: backup config.json.bak_20261106 → `core_host: 192.168.1.9 → 100.92.219.98` (mesh IP PC)
5. `systemctl restart quan_ai_edge` → active

## TOÀN BỘ TEST HEARTBEAT SAU KHI XONG (owner yêu cầu)
| # | Test | Kết quả |
|---|---|---|
| 1 | Kiosk Pi5 → PC core qua mesh | core_connected: **True** \| core_host: 100.92.219.98:8766 \| avatar: IDLE |
| 2 | PC nhận heartbeat Pi5 | state=**READY** paired=**True** heartbeat 0.07s trước |
| 3 | tailscale ping mesh | pong direct 2-4ms (10/10 lần) |
| 4 | PC → Pi5 control qua mesh (set_expression) | 200 "Tailscale mesh LIVE 06/11" |
| 5 | Heartbeat stability 10 lần liên tục | **10/10 READY (<5s)** |
| 6 | tailscale ping lặp 10 lần | **10/10 pong** |
| 7 | Kiosk API qua mesh (status/agent/audio) | **3/3 = 200** |
| 8 | Pi5 → PC core API qua mesh | **200** (health) |

## Kiến trúc kênh sau khi xong
- **PRIMARY: Tailscale mesh** — PC `100.92.219.98` ↔ Pi5 `100.100.83.59` (direct LAN path, tự fallback DERP khi ra ngoài mạng nhà)
- **Fallback: LAN Wi-Fi** 192.168.1.9 ↔ 192.168.1.21 (config cũ .bak_20261106 lưu sẵn, rollback 1 lệnh)
- Mesh ổn định khi: đổi Wi-Fi, ra ngoài mạng nhà (iPhone bắt tin qua iPhone node khi anh bật lại), PC đổi IP router

## Tài sản dữ liệu máy cũ (BRAIN_0) — đã audit từ trưa
- config mẫu: `BRAIN_0/edge_client/config.json` (core_host cũ 192.168.10.199 — đã thay bằng mesh)
- SSH key cũ `tony-desktop-snmi929` trong `BRAIN_0/pi5_deploy/tony_pc.pub` — private key KHÔNG có trên máy này (Pi5 dùng key dell@QUANPT)
- Script deploy cũ `BRAIN_0/pi5_deploy/*` — dùng bản mới hơn ở `E:\BRAIN\pi5_deploy` khi owner chạy script Pi5

## Việc còn lại (chờ owner)
- Chạy `sudo bash tony_pi5_all_in_one.sh` (zip 11 file DM TONY) để sync 9 module edge_client (UDR-1/UDC-1) → "pi5 ok" → G1 LIVE VALIDATION 16 mục
