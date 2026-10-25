#!/bin/bash
# ==============================================================================
# QUAN AI BRAIN — 24/7 AUTOSTART RUNNER & WATCHDOG FOR RASPBERRY PI 5
# Màn hình cảm ứng: 7" DSI Touchscreen 2 (1280x720) — Model F Digital Human
# ==============================================================================
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================================================"
echo "    QUAN AI BRAIN — KHỞI CHẠY HÌNH THỂ SỐ 24/7 TRÊN RASPBERRY PI 5"
echo "           GƯƠNG MẶT CÔ TRỢ LÝ AI MẪU F • MÀN HÌNH 7\" DSI"
echo "========================================================================"

# 1. Cấu hình môi trường đồ họa Wayland / X11
export DISPLAY="${DISPLAY:-:0}"
if [ -z "$WAYLAND_DISPLAY" ] && [ -e "$XDG_RUNTIME_DIR/wayland-0" ]; then
    export WAYLAND_DISPLAY="wayland-0"
fi

# 2. Chống tắt màn hình / Chống sleep 24/7 (Always-on Screen)
xset s off 2>/dev/null || true
xset -dpms 2>/dev/null || true
xset s noblank 2>/dev/null || true

# 3. Khởi động tiến trình Edge Client Daemon (main.py) nếu chưa chạy
if ! pgrep -f "python3.*main.py" > /dev/null; then
    echo "[Pi5 Autostart] Khởi động Edge Client Daemon..."
    python3 main.py >/tmp/quan_kiosk_daemon.log 2>&1 &
fi

# 3.5. Tự động kiểm tra và đồng bộ tài sản gương mặt Cô Trợ Lý Mẫu F nếu chưa có
if [ ! -f "$SCRIPT_DIR/assets/avatar/model_f_portrait.png" ]; then
    echo "[Pi5 Autostart] Đang đồng bộ ảnh chân dung và khẩu hình Model F từ PC Core..."
    python3 "$SCRIPT_DIR/sync_assets.py" >/tmp/quan_asset_sync.log 2>&1 || true
fi

# 4. Chờ dịch vụ cục bộ cổng 8768 sẵn sàng (tối đa 20s)
echo "[Pi5 Autostart] Đang chờ dịch vụ Kiosk 8768 sẵn sàng..."
for i in $(seq 1 40); do
    if curl -s http://127.0.0.1:8768/api/kiosk/status >/dev/null 2>&1; then
        echo "[Pi5 Autostart] Dịch vụ Kiosk đã sẵn sàng!"
        break
    fi
    sleep 0.5
done

# 4.5. Tự động kiểm tra và cấu hình ngõ ra Loa USB & Microphone USB (PipeWire/WirePlumber)
if [ -f "$SCRIPT_DIR/setup_pi5_audio.sh" ]; then
    echo "[Pi5 Autostart] Tự động cấu hình âm thanh loa USB và mic USB..."
    bash "$SCRIPT_DIR/setup_pi5_audio.sh" >/tmp/quan_audio_setup.log 2>&1 || true
fi

# 5. Kiểm tra chế độ khởi động hình thể:
# Mặc định theo chỉ đạo của Anh Quân (Quanpt1):
# Khi cấp nguồn Pi 5, tiến trình daemon chạy ngầm sẵn sàng kết nối PC Core nhưng KHÔNG tự khởi động
# trình duyệt Chromium Kiosk trên màn hình 7" DSI.
# Hình thể số chỉ khởi động khi có thao tác từ Tab "Bật/Tắt Hình Thể Pi 5" trên Cockpit PC Core.

if [ "$1" == "--now" ] || [ "$1" == "--launch-kiosk" ]; then
    CHROME_FLAGS="--kiosk --noerrdialogs --disable-infobars --check-for-update-interval=31536000 --touch-events=enabled --disable-pinch --overscroll-history-navigation=0 --window-size=1280,720 --window-position=0,0 --enable-features=OverlayScrollbar --autoplay-policy=no-user-gesture-required --use-fake-ui-for-media-stream --password-store=basic --disable-session-crashed-bubble --disable-features=Translate"
    echo "[Pi5 Autostart] Bật giao diện gương mặt Cô Trợ Lý Mẫu A/F toàn màn hình..."
    xset dpms force on 2>/dev/null || true
    if command -v chromium-browser > /dev/null; then
        chromium-browser $CHROME_FLAGS http://127.0.0.1:8768/
    elif command -v chromium > /dev/null; then
        chromium $CHROME_FLAGS http://127.0.0.1:8768/
    elif command -v google-chrome > /dev/null; then
        google-chrome $CHROME_FLAGS http://127.0.0.1:8768/
    fi
else
    echo "[Pi5 Standby] Daemon đã kết nối sẵn sàng trên cổng 8768."
    echo "[Pi5 Standby] Chế độ chờ (Standby) kích hoạt — Giao diện hình thể 7\" DSI sẽ chỉ bật khi Anh Quân thao tác từ Web Cockpit."
fi

