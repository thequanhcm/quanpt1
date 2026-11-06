# KIỂM TRA TOÀN BỘ TONY + PI5 SAU KHI OWNER NỐI LẠI (06/11 18:45–18:57)

## Trigger
Owner DM: "Anh đã kết nối lại pi5. Em hãy kiểm tra mọi kết nối" (18:45:41) + 3 ảnh dashboard.

## Phát hiện từ 3 ảnh dashboard
1. **Ảnh Remote Camera (8766)**: lỗi COMMAND_NOT_DELIVERED: Pi 5 offline — ĐÚNG sự thật lúc 18:33 (Pi5 chưa power-cycle)
2. **Ảnh Phòng Điều Khiển (8766)**: EDGE-PI5-DESK-01 DISCONNECTED (heartbeat 4.2s > 4.0s); task_d4ab31100f95 DAG 0% treo
3. **Ảnh Hội Thoại (8765)**: Ollama local chưa kết nối (suy luận qua GLM-5.3-Flash cloud) — đúng thiết kế sau khi gỡ Ollama; tin "chào em" 18:33 đang THINKING

## Kết quả kiểm tra toàn bộ (bằng chứng thật)
| # | Thành phần | Kết quả | Bằng chứng |
|---|---|---|---|
| 1 | PC core 8765+8766 | HEALTHY (DEGRADED chỉ vì ollama OFFLINE — đã gỡ, không phải lỗi) | /api/health 200 |
| 2 | Pi5 kiosk LAN | core_connected=True avatar IDLE | GET /api/kiosk/status |
| 3 | Pi5 kiosk mesh | core_connected=True avatar IDLE | GET /api/kiosk/status |
| 4 | Tailscale mesh | DIRECT 192.168.1.21:41641 | tailscale status |
| 5 | DM bot_tony | LIVE (heartbeat 1s) | logs/netchat_responder_heartbeat.log |
| 6 | TONY chat E2E | Trả lời trong 2.0s qua GLM cloud | POST /api/chat → "OK" |
| 7 | Pi5 services | quan_ai_edge + bluetooth + selector timer + watchdog timer + BT-NAP: 5/5 active | systemctl is-active |
| 8 | BT discoverable | TONY-PI5, Discoverable=yes, Pairable=yes | bluetoothctl show |

## DEPLOY MỚI HOÀN TẤT (đã chờ từ trước, lắp được khi Pi5 online)
- **WiFi watchdog**: /usr/local/bin + systemd timer 60s — ACTIVE (fix thêm chmod +x bị thiếu → 203/EXEC)
- **Channel selector**: timer 30s — ACTIVE; state file đo RTT thật: MESH 23.4ms, LAN 55.1ms, BT-PAN chưa pair (null) → chọn MESH
- **BT-NAP server**: service active; bridge pan0 172.30.99.1/24 + dnsmasq DHCP; register BlueZ OK sau 2 fix (Network1→NetworkServer1; Register(uuid, bridge) đúng thứ tự tham số — docs org.bluez.NetworkServer.rst)

## Test fail-over thật (iptables chặn mesh+LAN 35s)
- Selector phát hiện "kênh MESH CHẾT — failover" (journal 18:56:24)
- TẤT CẢ kênh chết (BT-PAN null vì chưa pair) → giữ config, đợi chu kỳ sau = đúng thiết kế fail-honest
- Bỏ chặn → chu kỳ kế tự probe lại MESH 30.7ms → hoạt động bình thường. KHÔNG mất kết nối SSH.

## Việc còn lại — PHẦN CỦA OWNER (1 bấm duy nhất)
**Pair Bluetooth PC↔Pi5**: Windows Settings → Bluetooth & devices → Add device → chọn "TONY-PI5"
→ sau đó em chạy Join PAN từ PC + selector sẽ tự thấy kênh BT-PAN và đưa vào vòng tự điều tiết.

## Files mới/sửa
- pi5_deploy/bt_nap_server.py (fix interface + tham số Register)
- pi5_deploy/tony_bt_nap.service (mới)
- pi5_deploy/tony_channel_selector.py (fix import sys)
- pi5_deploy/bt_register_probe.py (probe debug)
