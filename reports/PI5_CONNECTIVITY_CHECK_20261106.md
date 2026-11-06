
=== KẾT QUẢ KIỂM TRA KẾT NỐI PI5 (06/11 ~14:12) ===
1. PC Wi-Fi: 192.168.1.9 (Wireless adapter) ✓
2. 192.168.1.2 = ZTE device (MAC 34:24:3E = ZTE Corp) — KHÔNG phải Pi5 (ping OK nhưng mọi port đóng)
3. Pi5 THẬT = 192.168.1.21 (MAC 2C:CF:67 = Raspberry Pi Ltd) ✓
   - Ping: OK (5-71ms)
   - SSH port 22: MỞ — OpenSSH_10.0p2 Debian 13 (Pi OS mới)
   - Kiosk port 8768: MỞ — "QUAN AI BRAIN — Raspberry Pi 5 Edge Kiosk" đang chạy
   - SSH key TONY: Permission denied (publickey) — key chưa được cài vào Pi
4. Kiosk /api/kiosk/status: kiosk_running=true nhưng core_host=100.102.120.6:8766 (IP CŨ, sai)
   → core_connected=false, avatar OFFLINE
5. PC core 8766: /edge/status 200 (paired=false, DISCONNECTED — chưa nhận heartbeat từ Pi5)
   POST heartbeat 200 OK — API nhận edge bình thường
6. /edge/devices: ĐÃ XỬ LÝ — DeviceStore init độc lập tạo 3 bảng chuẩn (events/current/
   sqlite_sequence); route giờ trả success:true current:[] (đúng thiết kế UDR-1: rỗng vì
   Pi5 chưa gửi events). Nghi vấn: server 12:43 chưa init store trước lần gọi đầu 14:10.

=== KẾT LUẬN & VIỆC CẦN LÀM ===
Kết nối vật lý PC↔Pi5: OK (cùng Wi-Fi, ping 5-38ms).
Kênh điều khiển: CHƯA SỐNG vì 2 việc owner phải làm trên Pi5:
  (1) Chạy script zip 11 file trong DM TONY: sudo bash tony_pi5_all_in_one.sh
      → script tự: bật sshd (đã bật sẵn), cài SSH key TONY (hiện THIẾU),
        sửa core_host 100.102.120.6 → 192.168.1.9, sync 9 module edge_client,
        cài service quan_ai_edge 24/7.
  (2) Sau khi chạy xong, báo lại 'pi5 ok' → em chạy G1 LIVE VALIDATION 16 mục.
KHÔNG cài key/sửa config Pi5 từ xa được vì: SSH key chưa cài (permission denied),
đăng nhập password cần tương tác bàn phím Pi5 (an toàn — không tự nhập password).
