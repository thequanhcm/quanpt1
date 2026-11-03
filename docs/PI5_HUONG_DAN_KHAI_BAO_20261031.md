# HƯỚNG DẪN KHAI BÁO PI 5 — PHIÊN BẢN TAILSCALE (31/10/2026)
# Toàn bộ file đã kiểm toán + gói ZIP sẵn sàng. Anh làm theo 6 bước.

═══════════════════════════════════════════════════════════════════
BƯỚC 0 — KIỂM TOÁN FILE (EM ĐÃ LÀM — KẾT QUẢ)
═══════════════════════════════════════════════════════════════════
✅ 22 file Python/shell/config cốt lõi: ĐỦ, syntax 0 lỗi
✅ 3 file có IP CŨ cần biết (KHÔNG ảnh hưởng — đã có route mới):
   • setup_systemd_247.sh:64 (ExecStart --core-host 192.168.1.17)
     → script deploy MỚI của em đã thay bằng main.py KHÔNG tham số
       (đọc core_host từ config.json) — KHÔNG dùng file cũ nữa
   • sync_assets.py:41,48 (fallback 192.168.1.11)
     → chỉ là fallback khi KHÔNG có config.json; Pi có config.json
       nên đọc đúng core_host mới — an toàn
   • README.md:80 (mô tả IP ví dụ) — chỉ là tài liệu
✅ Cơ chế ghép cặp: setup_pi5.py gửi POST /api/edge/pair với PIN 888666
   → server cấp shared_secret mới, lưu config.json Pi + bộ nhớ server
✅ HMAC heartbeat: client ký bằng shared_secret; server ghi nhận qua
   header X-QuanAI-Device — sẽ pair lại tự động khi heartbeat đầu tiên
✅ Gói ZIP tạo sẵn: backups/edge_client_pi5_deploy_20261031.zip (22,7 MB,
   72 file, có script deploy_pi5_tailscale_20261031.sh MỚI)

═══════════════════════════════════════════════════════════════════
BƯỚC 1 (PC — 30 giây) — ANH BẤM LINK ĐĂNG NHẬP TAILSCALE
═══════════════════════════════════════════════════════════════════
Mở trình duyệt: https://login.tailscale.com/a/ac17fe901cc4a
→ Đăng nhập Google → nhấn "Connect"
→ Xong: trên PC mở PowerShell gõ:  & "C:\Program Files\Tailscale\tailscale.exe" ip -4
   → ghi lại IP dạng 100.x.y.z — ĐÂY LÀ "ĐỊA CHỈ MỚI VĨNH VIỄN" CỦA PC

═══════════════════════════════════════════════════════════════════
BƯỚC 2 (PI 5 — 3 phút) — COPY GÓI VÀO PI
═══════════════════════════════════════════════════════════════════
Chọn 1 trong 3 cách:
• Cách A (USB): Copy ZIP vào USB → cắm vào Pi → giải nén vào ~/:
    unzip ~/edge_client_pi5_deploy_20261031.zip -d ~/
    → tạo ~/edge_client/
• Cách B (scp từ PC — nếu Pi cùng LAN tạm thời):
    scp "D:\AI\AI Quanpt1 2026\BRAIN\backups\edge_client_pi5_deploy_20261031.zip" pi@<IP_Pi>:~/
• Cách C (Pi còn bản cũ): chỉ thay 2 file config.json + deploy script

═══════════════════════════════════════════════════════════════════
BƯỚC 3 (PI 5 — 2 phút) — CÀI TAILSCALE TRÊN PI
═══════════════════════════════════════════════════════════════════
Trên Pi 5 (terminal trực tiếp hoặc SSH):
    cd ~/edge_client
    bash deploy_pi5_tailscale_20261031.sh --tailscale-only

Script sẽ:
• Cài Tailscale (curl -fsSL https://tailscale.com/install.sh | sh)
• In link đăng nhập → ANH MỞ LINK BẰNG ĐIỆN THOẠI → đăng nhập CÙNG
  tài khoản với Bước 1
• Sau khi đăng nhập xong, script tự nhận IP 100.x.y.z của Pi

═══════════════════════════════════════════════════════════════════
BƯỚC 4 (PI 5 — 1 phút) — DEPLOY ĐẦY ĐỦ
═══════════════════════════════════════════════════════════════════
    cd ~/edge_client
    bash deploy_pi5_tailscale_20261031.sh

Script tự động làm 5 việc:
[1/5] Cài python3 + chromium + alsa nếu thiếu
[2/5] Xác nhận Tailscale online (in ra IP Pi)
[3/5] Hỏi IP 100.x.y.z của PC (anh gõ 1 lần) → chạy setup_pi5.py
      --auto --host <IP-PC> --pin 888666 → ghép cặp + nhận shared_secret
[4/5] Tạo systemd quan_ai_edge.service (Restart=always, 3s)
[5/5] Health check — báo THÀNH CÔNG khi heartbeat tới PC

═══════════════════════════════════════════════════════════════════
BƯỚC 5 — XÁC MINH TỪ PC (EM LÀM KHI ANH BÁO XONG)
═══════════════════════════════════════════════════════════════════
Em sẽ chạy:
• & "C:\Program Files\Tailscale\tailscale.exe" status   → thấy Pi trong tailnet
• curl http://<IP-Pi-100.x>:8768/api/kiosk/status       → kiosk trả lời
• http://127.0.0.1:8766/ → Tab "Đồng Bộ Edge Pi 5"      → trạng thái ONLINE/READY
→ Báo anh kết quả qua DM NetChat

═══════════════════════════════════════════════════════════════════
BƯỚC 6 — BẢO TRÌ SAU NÀY (CHỈ KHI CẦN)
═══════════════════════════════════════════════════════════════════
• PC đổi IP LAN / đổi Wi-Fi / chuyển 4G: KHÔNG CẦN LÀM GÌ
  (IP 100.x.y.z không bao giờ đổi)
• Cần chỉ lại IP PC mới (ví dụ cài lại tailnet): trên Pi chạy
    bash deploy_pi5_tailscale_20261031.sh --repoint
• Xem log Pi:        journalctl -u quan_ai_edge -f
• Restart daemon:    sudo systemctl restart quan_ai_edge
• Đồng bộ assets:    python3 ~/edge_client/sync_assets.py
  (tự đọc core_host từ config.json — không cần sửa gì)

═══════════════════════════════════════════════════════════════════
THÔNG SỐ KHAI BÁO NHANH (khi anh cần gõ tay)
═══════════════════════════════════════════════════════════════════
File cấu hình trên Pi:  ~/edge_client/config.json
  device_id      : EDGE-PI5-DESK-01            (giữ nguyên)
  core_host      : <IP 100.x.y.z CỦA PC>       (SỐ DUY NHẤT ANH CẦN SỬA)
  core_port      : 8766                         (giữ nguyên)
  kiosk_host     : 0.0.0.0                      (giữ nguyên)
  kiosk_port     : 8768                         (giữ nguyên)
  shared_secret  : (tự sinh khi ghép cặp — không sửa tay)
  poll_interval  : 1.0 giây                     (giữ nguyên)

Lệnh kiểm tra nhanh trên Pi:
  python3 ~/edge_client/main.py --check-health
  → "[THÀNH CÔNG] Brain Core ONLINE!" = mọi thứ thông

═══════════════════════════════════════════════════════════════════
LƯU Ý AN TOÀN
═══════════════════════════════════════════════════════════════════
• PIN ghép cặp: 888666 (hiển thị trên Cockpit 8766)
• KHÔNG chia sẻ config.json cho ai (có shared_secret bên trong)
• Pi chỉ nói chuyện với thiết bị trong tailnet riêng của anh —
  không mở port router, không public internet
• Nếu kiosk trắng: ssh vào Pi chạy
  DISPLAY=:0 chromium --kiosk http://127.0.0.1:8768/ &
