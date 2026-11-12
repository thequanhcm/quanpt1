#!/bin/bash
# Pi5 WiFi auto-reconnect + health watchdog (12/11/2026)
# Deploy tại /home/quanpt1/edge_client/pi5_stability/wifi_watchdog.sh
# Chạy bằng systemd timer mỗi 30s (KHÔNG dùng cron — systemd reliable hơn)
#
# Logic:
# - Ping gateway 192.168.1.1 — nếu fail → WiFi mất
# - Nếu WiFi mất > 60s → restart NetworkManager
# - Nếu vẫn mất sau restart → reboot (hw watchdog sẽ giám sát)
# - Ghi log vào /home/quanpt1/edge_client/pi5_stability/wifi_watchdog.log
# - Ghi boot reason + uptime vào /home/quanpt1/edge_client/pi5_stability/boot_status.json
#   (PC monitor đọc file này khi SSH được để biết Pi5 có reboot tự nhiên không)

set -u
LOG="/home/quanpt1/Desktop/edge_client/pi5_stability/wifi_watchdog.log"
STATUS="/home/quanpt1/Desktop/edge_client/pi5_stability/boot_status.json"
GATEWAY="192.168.1.1"
WIFI_IF="wlan0"
NM_RESTART_MARK="/tmp/wifi_nm_restart_pending"
mkdir -p "$(dirname "$LOG")"

ts() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }
log() { echo "$(ts) | $1" >> "$LOG"; }

# Ghi boot status (gọi 1 lần lúc boot + mỗi lần probe)
write_status() {
  local uptime_s boot_reason
  uptime_s=$(cut -d. -f1 /proc/uptime)
  boot_reason=$(journalctl --no-pager -n 50 | grep -i "systemd-shutdown\|reboot\|watchdog" | tail -1 | sed 's/"/\\"/g' || echo "unknown")
  cat > "$STATUS" <<EOF
{
  "ts_utc": "$(ts)",
  "uptime_sec": ${uptime_s},
  "boot_reason": "${boot_reason}",
  "wifi_if": "${WIFI_IF}",
  "gateway": "${GATEWAY}"
}
EOF
}

# Probe WiFi
if ping -c 1 -W 3 "$GATEWAY" >/dev/null 2>&1; then
  # OK
  rm -f "$NM_RESTART_MARK"
  write_status
  exit 0
fi

# WiFi mất — đánh dấu
if [ ! -f "$NM_RESTART_MARK" ]; then
  touch "$NM_RESTART_MARK"
  log "WARN: gateway $GATEWAY unreachable — marking"
  write_status
  exit 0
fi

# Đã mất > 60s (2 probe liên tiếp) → restart NetworkManager
mark_age=$(( $(date +%s) - $(stat -c %Y "$NM_RESTART_MARK") ))
if [ "$mark_age" -lt 60 ]; then
  log "WARN: still down (${mark_age}s) — waiting 60s before NM restart"
  write_status
  exit 0
fi

log "ACTION: restarting NetworkManager (WiFi down ${mark_age}s)"
sudo systemctl restart NetworkManager 2>>"$LOG" || true
sleep 10

if ping -c 1 -W 3 "$GATEWAY" >/dev/null 2>&1; then
  log "OK: WiFi recovered after NM restart"
  rm -f "$NM_RESTART_MARK"
  write_status
  exit 0
fi

# Vẫn mất → reboot (hw watchdog sẽ giám sát)
log "ACTION: WiFi still down after NM restart — rebooting"
sudo systemctl reboot 2>>"$LOG" || true
