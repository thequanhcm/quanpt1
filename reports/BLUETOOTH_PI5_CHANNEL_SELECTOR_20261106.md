# BLUETOOTH PC↔Pi5 + CHANNEL SELECTOR TỰ ĐIỀU TIẾT (06/11/2026)

**Yêu cầu owner:** "có thể cài đặt kết nối bluetooth giữa máy tính này và pi5 không, nếu được hãy kết nối. sau đó xem cài đặt tín hiệu hoặc phương thức nào mạnh nhất thì TONY tự điều tiết để kết nối"

**Trả lời: CÓ — được.** Bluetooth PC (Intel Wireless BT, service Running) + Pi5 (BT 5.0/BLE onboard). Nhưng **Pi5 hiện OFFLINE** (chờ power-cycle sau sự cố test WiFi — xem báo cáo PI5_WIFI_PRIORITY_AND_WATCHDOG) → **phase pair/chạy thật thực hiện ngay khi Pi5 lên lại** (anh nhắn "pi5 ok"). Toàn bộ kịch bản + code đã chuẩn bị sẵn.

## 1. Kênh truyền PC↔Pi5 — băng thông/độ trễ thật

| # | Kênh | RTT | Băng thông | Phụ thuộc | Vai trò |
|---|---|---|---|---|---|
| 1 | **Tailscale mesh direct** | 2–4ms | 100+ MB/s | Internet (không phụ thuộc router) | **PRIMARY** |
| 2 | LAN WiFi cùng router | 1–3ms | 100+ MB/s | router + cùng WiFi | fallback 1 |
| 3 | Tailscale DERP (Internet) | 50–200ms | 5–20 MB/s | Internet | fallback 2 (khác mạng) |
| 4 | **Bluetooth PAN** | 20–50ms | ~200 KB/s | chỉ khoảng cách ≤10m | **fallback 3 — cứu hộ khi WiFi+mesh chết hoàn toàn** (đúng kịch bản hôm nay) |
| 5 | UART GPIO | — | ~11 KB/s | cần dây | ngoài phạm vi |

**Vì sao BT đáng cài dù chậm:** hôm nay Pi5 chết WiFi là mất COMPLETE (không còn lối vào nào ngoài power-cycle). Với BT-PAN, heartbeat + DM text khẩn **vẫn sống** → TONY biết Pi5 còn sống, cảnh báo owner, và không cần chạm tay vào Pi.

## 2. Đã chuẩn bị (file trong `pi5_deploy/` — chưa chạy vì Pi5 offline)

| File | Vai trò |
|---|---|
| `tony_bt_nap_setup.sh` | Cài NAP: bridge pan0 172.30.99.1/24 + dnsmasq DHCP 172.30.99.10–50 + bluetoothctl discoverable/trust PC |
| `bt_nap_server.py` | BlueZ 5.x D-Bus `Network1.RegisterServer(NAP)` — alias `TONY-PI5`, tự dựng lại bridge nếu chết (liveness 30s). Syntax OK |
| `tony_channel_selector.py` | **Tự điều tiết kênh**: probe RTT TCP thật mỗi 30s, chọn kênh mạnh nhất theo ưu tiên, ghi `config.json` + restart service. Hysteresis 50% chống dao động. Fail-honest: probe fail = không suy diễn. Syntax OK |
| `tony_channel_selector.{service,timer}` | systemd timer chạy mỗi 30s |
| `tony_wifi_watchdog.{sh,service,timer}` | (từ phiên trước) tự chữa WiFi ≤75s |

## 3. Logic tự điều tiết của TONY (đúng yêu cầu "mạnh nhất thì tự chuyển")

```
mỗi 30s: probe RTT thật MESH → LAN → BT-PAN
  ├─ kênh hiện tại sống: chỉ nâng cấp nếu kênh ưu tiên cao hơn khỏe hơn ≥50% (chống nhảy channel liên tục)
  ├─ kênh hiện tại chết: failover ngay xuống kênh khỏe nhất còn sống (theo thứ tự ưu tiên)
  └─ tất cả chết: giữ config, báo lỗi — không suy diễn
đổi kênh = ghi core_host + restart quan_ai_edge (kiosk nối lại trong ~3s)
```

Kịch bản đời thực: mesh khỏe (mặc định) → router chết mesh vẫn direct (mesh không phụ thuộc router nếu có Internet khác) → WiFi Pi5 chết → Tailscale DERP qua BT-PAN? Không — BT-PAN là interface riêng; **kênh BT sống độc lập WiFi** → heartbeat qua 172.30.99.1 → TONY vẫn thấy Pi5, PC vẫn điều khiển được (chậm nhưng sống).

## 4. Lắp đặt khi Pi5 online (anh "pi5 ok" → em chạy tự động)

**Phase 1 — Pair Bluetooth (1 lần, cần 1 bấm trên Windows):**
1. Em SSH vào Pi5 bật `discoverable on, pairable on`, alias `TONY-PI5`
2. Anh mở Windows: **Settings → Bluetooth & devices → Add device → Bluetooth** → chọn `TONY-PI5` (không cần PIN — NoInputNoOutput agent)
3. Em SSH Pi5: `bluetoothctl trust <MAC-PC>` + lưu MAC vào `~/.tony_bt_pc_mac`
4. Gõ **Bluetooth PAN**: Windows Settings → Bluetooth & devices → Devices → TONY-PI5 → **Join Personal Area Network** → Access Point → Connect → PC nhận IP 172.30.99.x

**Phase 2 — Cài BT-NAP + Channel Selector trên Pi5 (SSH tự động):**
```bash
# 1. BT NAP server (systemd, tự sống)
sudo cp pi5_deploy/bt_nap_server.py /home/quanpt1/Desktop/edge_client/
sudo bash pi5_deploy/tony_bt_nap_setup.sh
# 2. Channel selector timer 30s
sudo cp pi5_deploy/tony_channel_selector.py /home/quanpt1/Desktop/edge_client/
sudo cp pi5_deploy/tony_channel_selector.{service,timer} /etc/systemd/system/
sudo systemctl enable --now tony_channel_selector.timer
# 3. WiFi watchdog (từ phiên trước)
sudo bash -c 'cp pi5_deploy/tony_wifi_watchdog.sh /usr/local/bin/ && chmod +x /usr/local/bin/tony_wifi_watchdog.sh && cp pi5_deploy/tony_wifi_watchdog.{service,timer} /etc/systemd/system/ && systemctl enable --now tony_wifi_watchdog.timer'
```

**Phase 3 — Verify E2E:** heartbeat matrix 6 đường (mesh/LAN/BT-PAN × 2 chiều) + test failover: chặn mesh+LAN → TONY tự chuyển BT-PAN trong ≤30s → bỏ chặn → tự nâng cấp về mesh (hysteresis chứng minh).

## 5. Trạng thái an toàn

- Không đụng gì trên Pi5 (offline); mọi file chỉ nằm PC
- PC Bluetooth không đổi gì (không pair vội — pair cần Pi5 discoverable, tránh cài nửa vời)
- 8 relay GPIO OPEN (kế thừa G1); PC core 8766 HEALTHY; DM bot_tony LIVE

## Ghi chú trung thực

- BT PAN băng thông ~200KB/s là ước lượng từ BlueZ spec (EDR) — sẽ đo thật sau khi pair và ghi số liệu vào báo cáo verify
- Flow pair cần 1 thao tác tay của anh trên Windows (Windows không cho pair Bluetooth bằng lệnh không UI) — các bước còn lại em tự làm qua SSH
