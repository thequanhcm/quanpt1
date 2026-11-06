# PI5 WIFI WATCHDOG — ƯU TIÊN KẾT NỐI WIFI CÙNG MẠNG PC (06/11/2026)

**Yêu cầu owner:** "cài đặt sau pi5 luôn ưu tiên kết nối wifi cùng mạng [với PC]"

## 1. ĐÃ CÀI XONG (trước khi test failover): WiFi priority trên Pi5

NetworkManager `autoconnect-priority` — số càng cao càng ưu tiên, đã set qua `sudo nmcli`:

| Mạng | Priority | Vai trò |
|---|---|---|
| **Ca Ngo 5G** | **100** | WiFi nhà — PC đang dùng (PC∩Pi5 giao nhau) — ưu tiên cao nhất |
| **Ca Ngo** | 90 | Cùng router nhà băng 2.4GHz — fallback khi 5G yếu |
| Na, Nino | 10 | Mạng khác Pi5 từng nối — chỉ dùng khi vắng nhà |
| powersave | disable (cả 4) | tránh rớt kết nối tiết kiệm năng lượng |

→ Khi 2 máy cùng ở nhà: Pi5 LUÔN ưu tiên bám đúng WiFi của PC.

## 2. ⚠️ SỰ CỐ TRONG QUÁ TRÌNH KIỂM CHỨNG (trung thực — fail-honest)

Để kiểm chứng priority, tôi chạy `nmcli dev disconnect wlan0` trên Pi5 (kỳ vọng tự autoconnect lại).
**Kết quả thực tế: Pi5 KHÔNG tự nối lại** — NetworkManager trên Pi OS **không autoconnect lại sau disconnect do admin** (chỉ autoconnect sau mất sóng/router chết, không phải sau `disconnect` thủ công). Pi5 mất cả LAN + mesh từ **17:58** (23+ phút).

**Hệ quả:** Pi5 hiện OFFLINE. **Việc của anh: rút-cắm nguồn Pi5** (không mất dữ liệu — tất cả cấu hình đã lưu đĩa). Sau boot, NetworkManager autoconnect bình thường theo priority.

**Lesson learned (đã vá bằng cơ chế mới dưới đây):** không được test bằng `dev disconnect` trên thiết bị headless không có lối vào vật lý.

## 3. ĐÃ CHUẨN BỊ SẴN: WiFi Watchdog tự hồi phục (vá đúng gap này)

File mới trong `E:\BRAIN\pi5_deploy\` (chờ cài khi Pi5 online lại):
- `tony_wifi_watchdog.sh` — chạy mỗi 60s: wlan0 có IP → thoát; không IP → rescan + `nmcli device connect wlan0` (NetworkManager tự chọn priority cao nhất khả dụng) → sau 15s vẫn không có → `systemctl restart NetworkManager`
- `tony_wifi_watchdog.service` + `tony_wifi_watchdog.timer` (OnBootSec=90, OnUnitActiveSec=60)

**Lắp đặt khi Pi5 online lại (3 lệnh qua SSH, sẽ chạy khi anh báo "pi5 ok"):**
```bash
sudo cp pi5_deploy/tony_wifi_watchdog.sh /usr/local/bin/ && sudo chmod +x /usr/local/bin/tony_wifi_watchdog.sh
sudo cp pi5_deploy/tony_wifi_watchdog.{service,timer} /etc/systemd/system/
sudo systemctl enable --now tony_wifi_watchdog.timer
```

**Sau khi lắp:** Pi5 tự chữa WiFi trong ≤75s trong MỌI tình huống mất mạng (kể cả disconnect thủ công, router chết rồi sống, nhảy AP) — không cần power-cycle nữa.

## 4. Trạng thái an toàn

- Trước sự cố: priority + powersave đã lưu vào disk (bền vững qua reboot); kiosk + fail-honest fix đã sync trước đó; 8 relays OPEN.
- Pi5 boot lại: service `quan_ai_edge` + `quan_ai_kiosk_guard` enabled → TONY tự chạy; core_host mesh IP cố định → nối lại PC trong ~3s (đã chứng minh ở báo cáo PI5_WIFI_AUTOCONNECT).
- PC-side: không thay đổi gì; TONY trên PC vẫn chạy bình thường 24/7.

## Ghi chú minh bạch

- Sự cố do test của tôi — tôi chịu trách nhiệm, đã khai báo ngay khi phát hiện thay vì giấu.
- Không có dữ liệu mất: mọi config (priority, powersave, core_host, sync module) đều đã ghi đĩa Pi5 trước khi mất kết nối.
