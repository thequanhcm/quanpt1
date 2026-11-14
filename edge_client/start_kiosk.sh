#!/bin/bash
# QUAN AI BRAIN — Desktop autostart (31/10/2026, v2)
# Daemon TONY do systemd quan_ai_edge quản lý 24/7 (Restart=always) —
# script này KHÔNG khởi động daemon nữa (tránh 2 daemon giành port 8768).
# Chờ daemon sẵn sàng (tối đa ~2 phút — daemon có thể bật sau desktop session),
# rồi mở giao diện kiosk nếu chromium chưa chạy.
for i in $(seq 1 40); do
    if curl -s -m 3 -o /dev/null http://127.0.0.1:8768/api/kiosk/status; then
        break
    fi
    sleep 3
done
STATUS=$(curl -s -m 3 http://127.0.0.1:8768/api/kiosk/status 2>/dev/null)
if echo "$STATUS" | grep -q '"kiosk_running": *true'; then
    if ! pgrep -f chromium >/dev/null 2>&1; then
        export DISPLAY=:0
        export WAYLAND_DISPLAY=wayland-0
        export XDG_RUNTIME_DIR=/run/user/1000
        # (14/11/2026 v6pure) OWNER: "Pi5 hoạt động liên tục, hình thể hiển thị liên tục"
        # → tắt screen blanking + DPMS để màn DSI không tự tắt khi không có user input.
        xset s off 2>/dev/null || true
        xset -dpms 2>/dev/null || true
        xset s noblank 2>/dev/null || true
        CHROME_FLAGS="--password-store=basic --kiosk --noerrdialogs --disable-infobars --check-for-update-interval=31536000 --touch-events=enabled --disable-pinch --overscroll-history-navigation=0 --window-size=800,480 --window-position=0,0 --ozone-platform=x11 --disable-features=Translate,TranslateUI --lang=vi --enable-features=OverlayScrollbar --disable-background-timer-throttling --disable-renderer-backgrounding --disable-backgrounding-occluded --autoplay-policy=no-user-gesture-required"
        if which chromium-browser > /dev/null 2>&1; then
            chromium-browser $CHROME_FLAGS http://127.0.0.1:8768/ &
        elif which chromium > /dev/null 2>&1; then
            chromium $CHROME_FLAGS http://127.0.0.1:8768/ &
        fi
    fi
fi
