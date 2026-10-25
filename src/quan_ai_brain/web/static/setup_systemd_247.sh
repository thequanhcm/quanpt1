#!/bin/bash
# ==============================================================================
# QUAN AI BRAIN — 24/7 SYSTEMD AUTOSTART & RESILIENCE FOR RASPBERRY PI 5
# ==============================================================================
# Script cài đặt dịch vụ cấp OS chạy ngầm liên tục 24/7.
# Đảm bảo:
# 1. Tự động bật lại ngay lập tức khi mất điện đột ngột hoặc khởi động lại Pi 5.
# 2. Hoạt động liên tục 24/7, tự phục hồi (Restart=always, RestartSec=3).
# 3. Chạy ở chế độ Standby (màn hình 7" không tự bật Kiosk để tiết kiệm điện & màn hình).
# 4. Khi Anh Quân cần bật hình thể, Anh chỉ cần bấm nút trên Web Cockpit (Tab 7).
# 5. Cấu hình SSH Public Key để PC Core có thể điều khiển trực tiếp từ xa.
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REAL_USER="${SUDO_USER:-$USER}"
REAL_HOME=$(getent passwd "$REAL_USER" | cut -d: -f6)
REAL_HOME="${REAL_HOME:-$HOME}"

echo ""
echo "========================================================================"
echo "    QUAN AI BRAIN — CÀI ĐẶT DỊCH VỤ HỆ THỐNG 24/7 TRÊN RASPBERRY PI 5"
echo "  Tự Động Bật Khi Cấp Nguồn / Mất Điện Đột Ngột • Kết Nối Liên Tục 24/7"
echo "========================================================================"
echo "  • Người dùng vận hành:  $REAL_USER"
echo "  • Thư mục mã nguồn:    $SCRIPT_DIR"
echo "  • PC Core Brain:       http://192.168.1.17:8766/"
echo "========================================================================"
echo ""

# 1. Cấu hình SSH Public Key của PC Core để điều khiển tự động
echo "[1/4] Thiết lập xác thực SSH không mật khẩu từ PC Core..."
mkdir -p "$REAL_HOME/.ssh"
chmod 700 "$REAL_HOME/.ssh"
PUBKEY="ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIDcSxP8XdhmhkmL+u9qdDxomwhYvWWYSZvLvfesgSrmB dell@QUANPT"
if ! grep -q "dell@QUANPT" "$REAL_HOME/.ssh/authorized_keys" 2>/dev/null; then
    echo "$PUBKEY" >> "$REAL_HOME/.ssh/authorized_keys"
fi
chmod 600 "$REAL_HOME/.ssh/authorized_keys"
chown -R "$REAL_USER:$REAL_USER" "$REAL_HOME/.ssh" 2>/dev/null || true
echo "  ✅ Đã lưu SSH Key của PC Core vào $REAL_HOME/.ssh/authorized_keys."

# 2. Phân quyền thực thi mã nguồn
echo "[2/4] Phân quyền thực thi tệp tin..."
chmod +x "$SCRIPT_DIR"/*.sh "$SCRIPT_DIR"/*.py 2>/dev/null || true

# 3. Tạo dịch vụ systemd cấp hệ điều hành (Chạy ngầm vĩnh viễn, chống mất nguồn)
echo "[3/4] Cấu hình systemd service: /etc/systemd/system/quan_ai_edge.service..."
SERVICE_FILE="/etc/systemd/system/quan_ai_edge.service"

sudo bash -c "cat << 'EOF' > $SERVICE_FILE
[Unit]
Description=QUAN AI BRAIN — Raspberry Pi 5 Edge Client 24/7
After=network-online.target sound.target
Wants=network-online.target

[Service]
Type=simple
User=$REAL_USER
WorkingDirectory=$SCRIPT_DIR
Environment=PYTHONUNBUFFERED=1
Environment=DISPLAY=:0
Environment=WAYLAND_DISPLAY=wayland-0
ExecStart=/usr/bin/python3 $SCRIPT_DIR/main.py --core-host 192.168.1.17 --core-port 8766
Restart=always
RestartSec=3
StandardOutput=journal
StandardError=journal
LimitNOFILE=65535

[Install]
WantedBy=multi-user.target
EOF"

echo "  ✅ Đã tạo tệp dịch vụ systemd thành công."

# 4. Kích hoạt và khởi chạy dịch vụ
echo "[4/4] Đăng ký khởi động vĩnh viễn và chạy dịch vụ ngay bây giờ..."
# Dọn dẹp tiến trình chạy thủ công trước đó để giải phóng port 8768
sudo pkill -f "python3.*(main|client_daemon).py" 2>/dev/null || true
sleep 1

sudo systemctl daemon-reload
sudo systemctl enable quan_ai_edge.service
sudo systemctl restart quan_ai_edge.service

echo ""
echo "========================================================================"
echo "  🎉 HOÀN TẤT THIẾT LẬP 24/7 CHO RASPBERRY PI 5!"
echo "  • Trạng thái dịch vụ: quan_ai_edge.service [ACTIVE / RUNNING]"
echo "  • Chống mất nguồn:   Mất điện, reboot hay crash đều TỰ ĐỘNG BẬT LẠI sau 3s."
echo "  • Chế độ:            Standby (Giao diện 7\" DSI chỉ bật khi Anh chọn trên Web PC)."
echo "  • Kiểm tra dịch vụ:  systemctl status quan_ai_edge"
echo "========================================================================"
echo ""
