#!/bin/bash
# ==============================================================================
# QUAN AI BRAIN — 1-CLICK PERMANENT 24/7 AUTOSTART INSTALLER FOR RASPBERRY PI 5
# ==============================================================================
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "========================================================================"
echo "    QUAN AI BRAIN — CÀI ĐẶT TỰ ĐỘNG KHỞI ĐỘNG 24/7 TRÊN RASPBERRY PI 5"
echo "  Hình Thể Số Cô Trợ Lý Mẫu F Tự Động Bật Cùng Nguồn Điện & Hoạt Động Liên Tục"
echo "========================================================================"
echo ""

# 1. Phân quyền thực thi cho toàn bộ script
chmod +x start_kiosk.sh main.py setup_pi5.py oneclick_run_pi5.sh 2>/dev/null || true

# 2. Tạo thư mục autostart của hệ điều hành Raspberry Pi OS
HOME_DIR="${HOME:-/home/$USER}"
AUTOSTART_DIR="$HOME_DIR/.config/autostart"
mkdir -p "$AUTOSTART_DIR"

# 3. Tạo Desktop Autostart Entry (~/.config/autostart/quan_kiosk.desktop)
DESKTOP_ENTRY="$AUTOSTART_DIR/quan_kiosk.desktop"
cat << EOF > "$DESKTOP_ENTRY"
[Desktop Entry]
Type=Application
Name=QUAN AI BRAIN Model F Kiosk
Comment=Tự động bật gương mặt Cô Trợ Lý Mẫu F khi Pi 5 khởi động
Exec=/bin/bash -c "sleep 3 && \"$SCRIPT_DIR/start_kiosk.sh\""
Terminal=false
X-GNOME-Autostart-enabled=true
EOF

chmod +x "$DESKTOP_ENTRY"

# 4. Tạo lối tắt trên màn hình chính (Desktop Shortcut)
if [ -d "$HOME_DIR/Desktop" ]; then
    DESKTOP_SHORTCUT="$HOME_DIR/Desktop/QUAN_AI_BRAIN_Kiosk.desktop"
    cp "$DESKTOP_ENTRY" "$DESKTOP_SHORTCUT"
    chmod +x "$DESKTOP_SHORTCUT"
    echo "  [OK] Đã tạo biểu tượng truy cập nhanh trên màn hình chính Pi 5."
fi

# 5. Cấu hình chống tắt màn hình (Disable Screen Blanking / Sleep)
if command -v xset &> /dev/null; then
    xset s off 2>/dev/null || true
    xset -dpms 2>/dev/null || true
    xset s noblank 2>/dev/null || true
fi

# Thêm cấu hình chống sleep vào .profile hoặc .bashrc
if ! grep -q "xset s off" "$HOME_DIR/.profile" 2>/dev/null; then
    echo "xset s off -dpms s noblank 2>/dev/null || true" >> "$HOME_DIR/.profile"
fi

echo ""
echo "========================================================================"
echo "  ✅ ĐÃ THIẾT LẬP TỰ ĐỘNG KHỞI ĐỘNG 24/7 THÀNH CÔNG DUY NHẤT 1 LẦN!"
echo "========================================================================"
echo "  • Vị trí tự khởi động: $DESKTOP_ENTRY"
echo "  • Kịch bản điều khiển:  $SCRIPT_DIR/start_kiosk.sh"
echo "  • Màn hình cảm ứng:    Tự động mở Kiosk Model F (1280x720) mỗi khi cấp nguồn."
echo "  • Hoạt động liên tục:  Không sleep, tự phục hồi nếu tắt trình duyệt."
echo "========================================================================"
echo ""
echo "👉 Đang kích hoạt giao diện Kiosk ngay bây giờ..."
nohup bash "$SCRIPT_DIR/start_kiosk.sh" >/dev/null 2>&1 &
echo "  [Hoàn tất] Màn hình 7\" DSI đang hiển thị Cô Trợ Lý AI Mẫu F!"
echo ""
