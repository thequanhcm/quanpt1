#!/bin/bash
# ==============================================================================
# QUAN AI BRAIN — ONE-CLICK SETUP & RUNNER CHO RASPBERRY PI 5
# Màn hình cảm ứng: 7" DSI Touchscreen 2 (1280x720) — Model F Digital Human
# ==============================================================================
# Hướng dẫn: Chỉ cần chạy 1 lệnh duy nhất trên Raspberry Pi 5:
#   bash oneclick_run_pi5.sh
# ==============================================================================

set -e
cd "$(dirname "$0")"

echo ""
echo "========================================================================"
echo "    QUAN AI BRAIN — ONE-CLICK RASPBERRY PI 5 KIOSK (7\" DSI 1280x720)"
echo "            TRỢ LÝ SỐ MẪU F — KẾT NỐI & ĐỒNG BỘ HAI CHIỀU WI-FI"
echo "========================================================================"
echo ""

# 1. Kiểm tra quyền thực thi các file mã nguồn
chmod +x setup_pi5.sh setup_pi5.py start_kiosk.sh 2>/dev/null || true

# 2. Kiểm tra và tự động cập nhật thư viện / môi trường hệ thống trên Pi 5
MISSING_PKGS=""

if ! command -v python3 &> /dev/null; then
    MISSING_PKGS="$MISSING_PKGS python3"
fi

if ! command -v chromium-browser &> /dev/null && ! command -v chromium &> /dev/null; then
    MISSING_PKGS="$MISSING_PKGS chromium-browser"
fi

if ! command -v aplay &> /dev/null; then
    MISSING_PKGS="$MISSING_PKGS alsa-utils"
fi

if [ -n "$MISSING_PKGS" ]; then
    echo "📦 Đang tự động cài đặt các gói cần thiết trên Pi 5:$MISSING_PKGS ..."
    if command -v sudo &> /dev/null; then
        sudo apt-get update -y
        sudo apt-get install -y $MISSING_PKGS
    else
        echo "⚠️ Không có quyền sudo. Vui lòng cài thủ công: apt-get install -y $MISSING_PKGS"
    fi
else
    echo "✅ Toàn bộ gói hệ thống (Python 3, Chromium Kiosk, ALSA Audio) đã sẵn sàng."
fi

# 3. Tối ưu cấu hình âm thanh cho 7" DSI Touchscreen (nếu có loa HDMI/Audio Hat)
if command -v amixer &> /dev/null; then
    amixer set Master 85% 2>/dev/null || true
fi

# 4. Thực thi quy trình ghép cặp tự động qua Wi-Fi và tạo Autostart
echo ""
echo "🚀 Đang khởi động quy trình ghép cặp Wi-Fi và tối ưu 1280x720..."
if [ $# -eq 0 ]; then
    python3 setup_pi5.py --auto
else
    python3 setup_pi5.py "$@"
fi

echo ""
echo "========================================================================"
echo "  ✅ HOÀN TẤT CÀI ĐẶT ONE-CLICK CHO RASPBERRY PI 5!"
echo "  Màn hình 7\" DSI Touchscreen 2 đang hiển thị hình thể số Cô Trợ Lý Mẫu F."
echo "========================================================================"
