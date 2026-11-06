#!/bin/bash
# WIFI WATCHDOG PI5 — Tự đảm bảo wlan0 luôn nối WiFi ưu tiên (priority cao nhất khả dụng)
# Chạy mỗi 60s qua systemd timer. Fail-safe: chỉ reconnect, không bao giờ down interface.
LOG_TAG="tony_wifi_watchdog"

# 1. wlan0 có IP không?
if ip -4 addr show wlan0 | grep -q "inet "; then
    # có mạng — thoát im lặng
    exit 0
fi

logger -t $LOG_TAG "wlan0 không có IP — thử autoconnect lại theo priority"

# 2. Thử bật lại connection active (NetworkManager autoconnect theo priority đã cấu hình)
nmcli networking connectivity check >/dev/null 2>&1
nmcli device wifi rescan >/dev/null 2>&1 || true

# 3. Force autoconnect: activate connection có priority cao nhất trong các mạng đang thấy
# NetworkManager tự chọn theo priority khi gọi:
nmcli device connect wlan0 >/dev/null 2>&1 || true

# 4. Sau 15s vẫn chưa có IP → restart NetworkManager (cấp cuối)
sleep 15
if ! ip -4 addr show wlan0 | grep -q "inet "; then
    logger -t $LOG_TAG "vẫn không có IP — restart NetworkManager"
    systemctl restart NetworkManager
fi
