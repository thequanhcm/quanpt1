#!/bin/bash
# TONY tự cấu hình Pi5 — 24/7 ổn định (script owner chạy 1 lần)
# Owner chạy: sudo bash tony_setup_247.sh
set -e
echo "=== TONY SETUP PI5 24/7 — $(date) ==="

# 1) Nhận SSH public key của TONY vào authorized_keys (nếu file đi kèm)
if [ -f "$(dirname "$0")/tony_pc.pub" ]; then
  mkdir -p /home/quanpt1/.ssh
  chmod 700 /home/quanpt1/.ssh
  cat "$(dirname "$0")/tony_pc.pub" >> /home/quanpt1/.ssh/authorized_keys
  chmod 600 /home/quanpt1/.ssh/authorized_keys
  chown -R quanpt1:quanpt1 /home/quanpt1/.ssh
  echo "[OK] SSH key TONY đã cài — em tự đăng nhập được từ lần sau"
fi

# 2) Kill kiosk cũ (chiếm cổng 8768, nhớ IP cũ)
pkill -f "edge_client" 2>/dev/null || true
sleep 2

# 3) Cập nhật core_host trong config.json → IP Tailscale PC
CFG=/home/quanpt1/Desktop/edge_client/config.json
if [ -f "$CFG" ]; then
  python3 - <<'EOF'
import json
p = "/home/quanpt1/Desktop/edge_client/config.json"
cfg = json.load(open(p))
cfg["core_host"] = "100.102.120.6"
cfg["core_port"] = 8766
json.dump(cfg, open(p, "w"), indent=2)
print("[OK] core_host = 100.102.120.6:8766")
EOF
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
sudo systemctl status quan_ai_edge --no-pager -l | head -15

echo "=== HOÀN TẤT — TONY kiểm tra từ PC ==="
