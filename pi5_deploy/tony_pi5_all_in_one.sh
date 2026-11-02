#!/bin/bash
# =====================================================================
# TONY PI5 SELF-SETUP 24/7 — GỘP 1 FILE DUY NHẤT (script + SSH key)
# Owner copy 1 file này vào Pi rồi chạy:  sudo bash tony_pi5_all_in_one.sh
# Script tự: cài SSH key TONY, tắt kiosk cũ, sửa IP mới, service 24/7
# =====================================================================
set -e
echo "=== TONY SETUP PI5 24/7 — $(date) ==="

# 1) Cài SSH public key của TONY (nhúng sẵn bên dưới)
mkdir -p /home/quanpt1/.ssh
chmod 700 /home/quanpt1/.ssh
TONY_KEY='ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIDjGIBk7jGbrLk8U44bDCXMsStV7WipDKAzjYOipnsCy tony-desktop-snmi929'
if ! grep -qF "$TONY_KEY" /home/quanpt1/.ssh/authorized_keys 2>/dev/null; then
  echo "$TONY_KEY" >> /home/quanpt1/.ssh/authorized_keys
fi
chmod 600 /home/quanpt1/.ssh/authorized_keys
chown -R quanpt1:quanpt1 /home/quanpt1/.ssh
echo "[OK] SSH key TONY đã cài — em tự đăng nhập được từ lần sau"

# 2) Tắt kiosk cũ (chiếm cổng 8768, nhớ IP cũ)
pkill -f "edge_client" 2>/dev/null || true
pkill -f "main.py" 2>/dev/null || true
sleep 2
echo "[OK] Đã tắt kiosk cũ (nếu có)"

# 3) Cập nhật core_host trong config.json → IP Tailscale PC
CFG=/home/quanpt1/Desktop/edge_client/config.json
CORE_HOST="${CORE_HOST:-192.168.1.9}"   # PC lõi mới (02/11/2026, LAN QUANPT); nếu có Tailscale: CORE_HOST=100.x.x.x bash script
if [ -f "$CFG" ]; then
  python3 - "$CORE_HOST" <<'PYEOF'
import json, sys
p = "/home/quanpt1/Desktop/edge_client/config.json"
cfg = json.load(open(p))
cfg["core_host"] = sys.argv[1]
cfg["core_port"] = 8766
json.dump(cfg, open(p, "w"), indent=2)
print(f"[OK] core_host = {sys.argv[1]}:8766")
PYEOF
else
  echo "[CẢNH BÁO] Không tìm thấy $CFG — bỏ qua bước sửa IP"
fi

# 4) systemd service chạy 24/7 tự hồi sau reboot
cat > /tmp/quan_ai_edge.service <<'EOF'
[Unit]
Description=QUAN AI BRAIN Edge Kiosk (TONY 24/7)
After=network-online.target tailscaled.service
Wants=network-online.target

[Service]
Type=simple
User=quanpt1
WorkingDirectory=/home/quanpt1/Desktop/edge_client
ExecStart=/usr/bin/python3 /home/quanpt1/Desktop/edge_client/main.py
Restart=always
RestartSec=5
Environment=DISPLAY=:0

[Install]
WantedBy=multi-user.target
EOF
sudo cp /tmp/quan_ai_edge.service /etc/systemd/system/quan_ai_edge.service
sudo systemctl daemon-reload
sudo systemctl enable quan_ai_edge
sudo systemctl restart quan_ai_edge
sleep 5
echo "[OK] Service quan_ai_edge đã bật (24/7, tự hồi)"
sudo systemctl status quan_ai_edge --no-pager -l | head -12

echo ""
echo "=== HOÀN TẤT — TONY sẽ kiểm tra kết nối từ PC ngay bây giờ ==="
