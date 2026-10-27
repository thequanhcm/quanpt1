# KẾT QUẢ AUDIT GIAO THỨC TRUYỀN TIN PI 5 (27/10/2026 ~08:00 ICT) — ĐÃ SỬA XONG

## CHẨN ĐOÁN: ANH NÓI ĐÚNG — PI 5 ONLINE. PC BÁO SAI VÌ PI GÕ SAI ĐỊA CHỈ PC

### Bằng chứng thu được (probe thật, không suy đoán)
1. **Pi 5 sống và mạng tốt**: ping 192.168.1.21 → 4/4 packets, 5-7ms TTL=64; TCP 8768 (kiosk) OPEN; TCP 22 (ssh) OPEN; MAC `2c-cf-67-8e-c6-5a` (Raspberry Pi) có trong ARP.
2. **Kênh PC 8766 KHÔNG chết**: lắng nghe `0.0.0.0:8766`; gọi từ LAN `192.168.1.10:8766` với HMAC đúng → supervisor 200 READY, heartbeat POST 200.
3. **Root cause**: Pi gõ `core_host: 192.168.1.17:8766` — **IP CŨ của PC** (DHCP đổi PC sang 192.168.1.10 khi reboot đêm qua). Heartbeat 1s/lần của Pi bay tới .17 = không tồn tại.
4. **Nguồn sai**: `edge_client/config.json` (dòng 4) + systemd unit `quan_ai_edge.service` (ExecStart --core-host 192.168.1.17) — **IP hard-code 2 chỗ**.

## ĐÃ THỰC HIỆN (SSH vào Pi với user quanpt1 — key có sẵn)
1. `sed` sửa `config.json` trên Pi: core_host 192.168.1.17 → **192.168.1.10** ✅
2. `sudo sed` sửa `/etc/systemd/system/quan_ai_edge.service` ExecStart → 192.168.1.10 ✅
3. `systemctl daemon-reload + restart quan_ai_edge` → **active** ✅
4. **Kết quả ngay**: Pi kiosk `core_connected: True`, PC edge `state: READY`,
   heartbeat fresh liên tục (0.3–0.9s, RTT 11–16ms), đo 3 lần cách nhau ổn định ✅
5. **Bật kiosk ACTIVE** (không standby): `start_kiosk` → kiosk_running True,
   mode ACTIVE, avatar hiển thị trên màn 7" ✅
6. **E2E chu trình đầy đủ**: chat "pi5 đã online lại rồi em kiểm tra đi" qua
   dashboard → bot probe → **avatar Pi chuyển SPEAKING với transcript thật**
   ("Pi 5: ONLINE — RTT 11ms, heartbeat mới nhất...") trên màn hình ✅

## 24/7 + KHÔNG CHẾ ĐỘ NGHỈ (đã cấu hình và verify)
- `quan_ai_edge.service`: **enabled** (tự bật khi Pi khởi động/cấp điện lại),
  **Restart=always, RestartSec=3** (chết 3 giây là tự sống lại) — test restart
  thực tế: active lại và heartbeat về PC trong ~8 giây ✅
- Daemon chạy nền liên tục, heartbeat mỗi 1 giây, poll_interval 1s — không có
  cơ chế sleep trong giao thức. Kiosk hiển thị ACTIVE theo yêu cầu.
- Chỉ khi ANH TẮT CHỦ ĐỘNG (`poweroff_pi` / rút nguồn) hệ thống mới dừng.

## KHUYẾN NGHỊ CHỐNG LẶP LẠI (khi PC đổi IP lần nữa)
1. **DHCP reservation trong router** cho PC (MAC của PC → luôn 192.168.1.10) —
   anh làm trong trang quản trị router (192.168.1.1), 1 phút. Em đã đổi mọi
   chỗ hard-code về 192.168.1.10, nhưng nếu router cấp IP khác lần nữa sẽ
   lệch tiếp → reservation là cách chấm dứt vĩnh viễn.
2. (Tùy chọn sprint sau) Pi daemon hỗ trợ mDNS `quan-brain.local` thay IP cứng.

