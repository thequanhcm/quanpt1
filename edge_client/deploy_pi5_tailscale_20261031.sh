#!/bin/bash
# ==============================================================================
# QUAN AI BRAIN — DEPLOY MỚI CHO PI 5 (31/10/2026) — KẾT NỐI QUA TAILSCALE
# ==============================================================================
# Dành cho: Pi 5 cài LẠI từ đầu (hoặc cập nhật code mới) — PC đã cài Tailscale.
# Sau script này: Pi ở MẠNG NÀO CŨNG KẾT NỐI ĐƯỢC PC (không cần cùng Wi-Fi).
#
# CÁCH DÙNG (trên Pi 5, sau khi đã copy thư mục edge_client vào ~/):
#   1. Cài Tailscale:        bash deploy_pi5_tailscale_20261031.sh --tailscale-only
#   2. Deploy + ghép cặp:    bash deploy_pi5_tailscale_20261031.sh
#   3. Chạy lại mỗi lần đổi IP PC: bash deploy_pi5_tailscale_20261031.sh --repoint
# ==============================================================================
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
ok()   { echo -e "  ${GREEN}[OK]${NC} $1"; }
warn() { echo -e "  ${YELLOW}[!]${NC} $1"; }
fail() { echo -e "  ${RED}[LỖI]${NC} $1"; }

banner() {
echo ""
echo "========================================================================"
echo "   QUAN AI BRAIN — DEPLOY PI5 QUA TAILSCALE (31/10/2026)"
echo "   Hình thể TONY: màn 7\" DSI — kết nối PC BẤT KỂ MẠNG NÀO"
echo "========================================================================"
}

# ------------------------------------------------------------------------------
# BƯỚC T: CÀI TAILSCALE TRÊN PI (chạy 1 lần)
# ------------------------------------------------------------------------------
install_tailscale() {
    banner
    echo "[T/4] CÀI TAILSCALE TRÊN PI 5"
    if command -v tailscale &> /dev/null; then
        ok "Tailscale đã cài: $(tailscale version | head -1)"
    else
        echo "  Đang cài Tailscale (cần internet)..."
        curl -fsSL https://tailscale.com/install.sh | sh
        ok "Đã cài Tailscale"
    fi

    # Kiểm tra đã login chưa
    if sudo tailscale status &> /dev/null; then
        TS_IP=$(tailscale ip -4 2>/dev/null || echo "?")
        ok "Tailscale ĐÃ đăng nhập — IP của Pi: $TS_IP"
        echo "$TS_IP" > /tmp/ts_ip_pi.txt
    else
        warn "Chưa đăng nhập. Chạy lệnh sau và mở link bằng ĐIỆN THOẠI:"
        echo ""
        echo "        sudo tailscale up"
        echo ""
        echo "  → Đăng nhập bằng CÙNG tài khoản với máy PC."
        echo "  → Sau đó chạy lại script này."
        exit 2
    fi
}

# ------------------------------------------------------------------------------
# BƯỚC R: CHỈ LẠI IP PC TRONG config.json (chạy mỗi lần IP PC đổi)
# ------------------------------------------------------------------------------
repoint_core() {
    banner
    echo "[R] TRỎ config.json VỀ IP TAILSCALE MỚI CỦA PC"
    # PC phải đang online trong tailnet — thử IP lưu trong file ghi chú trước
    if [ -f "$SCRIPT_DIR/.pc_ts_ip" ]; then
        PC_IP=$(cat "$SCRIPT_DIR/.pc_ts_ip")
    else
        read -rp "  Nhập IP Tailscale của PC (dạng 100.x.y.z, xem bằng lệnh 'tailscale ip -4' trên PC): " PC_IP
    fi
    if [[ ! "$PC_IP" =~ ^100\. ]]; then
        fail "IP '$PC_IP' không đúng dạng Tailscale (100.x.y.z)"
        exit 1
    fi
    python3 - "$PC_IP" <<'PYEOF'
import json, sys
from pathlib import Path
cfg_file = Path(__file__).resolve().parent / "config.json" if False else Path("config.json")
data = json.loads(cfg_file.read_text(encoding="utf-8"))
data["core_host"] = sys.argv[1]
cfg_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"  [OK] core_host = {sys.argv[1]}")
PYEOF
    echo "$PC_IP" > "$SCRIPT_DIR/.pc_ts_ip"
    ok "Đã lưu .pc_ts_ip để lần sau tự điền"
}

# ------------------------------------------------------------------------------
# BƯỚC D: DEPLOY ĐẦY ĐỦ (dependencies + ghép cặp + systemd 24/7)
# ------------------------------------------------------------------------------
deploy_full() {
    banner
    echo "[D/5] DEPLOY TOÀN BỘ"

    # 1. Gói hệ thống
    echo ""
    echo "[1/5] Gói hệ thống (python3, chromium, alsa)..."
    MISSING=""
    command -v python3 >/dev/null || MISSING="$MISSING python3"
    command -v chromium >/dev/null || command -v chromium-browser >/dev/null || MISSING="$MISSING chromium-browser"
    command -v aplay >/dev/null || MISSING="$MISSING alsa-utils"
    if [ -n "$MISSING" ]; then
        sudo apt-get update -y && sudo apt-get install -y $MISSING
    fi
    ok "Gói hệ thống sẵn sàng"

    # 2. Tailscale
    echo ""
    echo "[2/5] Tailscale..."
    if ! sudo tailscale status &> /dev/null; then
        warn "Tailscale chưa chạy — chạy: bash $0 --tailscale-only rồi làm theo hướng dẫn"
        exit 2
    fi
    TS_IP=$(tailscale ip -4 2>/dev/null || echo "?")
    ok "Pi online trong tailnet — IP Pi: $TS_IP"

    # 3. Ghép cặp với PC (qua IP Tailscale của PC)
    echo ""
    echo "[3/5] Ghép cặp với PC Brain Core..."
    if [ -f "$SCRIPT_DIR/.pc_ts_ip" ]; then
        PC_IP=$(cat "$SCRIPT_DIR/.pc_ts_ip")
        warn "Dùng IP PC đã lưu: $PC_IP"
    else
        read -rp "  Nhập IP Tailscale của PC (xem trên PC bằng lệnh: tailscale ip -4): " PC_IP
    fi
    if [[ ! "$PC_IP" =~ ^100\. ]]; then
        fail "IP PC '$PC_IP' không đúng dạng 100.x.y.z"
        exit 1
    fi
    python3 setup_pi5.py --auto --host "$PC_IP" --port 8766 --pin 888666 --no-launch \
        && echo "$PC_IP" > "$SCRIPT_DIR/.pc_ts_ip" \
        || { fail "Ghép cặp thất bại — kiểm tra PC đã login Tailscale + server 8766 đang chạy"; exit 1; }
    ok "Đã ghép cặp, shared_secret lưu trong config.json"

    # 4. Systemd 24/7 (tự dậy khi boot, restart khi crash)
    echo ""
    echo "[4/5] Dịch vụ systemd 24/7..."
    sudo pkill -f "python3.*(main|client_daemon).py" 2>/dev/null || true
    sleep 1
    SERVICE_FILE=/etc/systemd/system/quan_ai_edge.service
    sudo bash -c "cat << 'EOF' > $SERVICE_FILE
[Unit]
Description=QUAN AI BRAIN — Raspberry Pi 5 Edge Client 24/7
After=network-online.target tailscaled.service
Wants=network-online.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$SCRIPT_DIR
Environment=PYTHONUNBUFFERED=1
ExecStart=/usr/bin/python3 $SCRIPT_DIR/main.py
Restart=always
RestartSec=3
StandardOutput=journal
StandardError=journal
LimitNOFILE=65535

[Install]
WantedBy=multi-user.target
EOF"
    sudo systemctl daemon-reload
    sudo systemctl enable quan_ai_edge.service
    sudo systemctl restart quan_ai_edge.service
    ok "quan_ai_edge.service ACTIVE — tự dậy khi boot, tự restart sau 3s"

    # 5. Health check
    echo ""
    echo "[5/5] Kiểm tra sức khỏe..."
    sleep 3
    systemctl is-active --quiet quan_ai_edge.service && ok "Dịch vụ đang chạy" || fail "Dịch vụ chưa chạy — xem: journalctl -u quan_ai_edge -n 20"
    if python3 main.py --check-health 2>/dev/null | grep -q "THÀNH CÔNG"; then
        ok "Kết nối PC Brain Core: THÀNH CÔNG"
    else
        warn "Chưa ping được PC — kiểm tra PC server 8766 + tailscale status"
    fi

    echo ""
    echo "========================================================================"
    echo "  ✅ HOÀN TẤT! Hình thể TONY trên Pi 5 đã LIVE"
    echo "  • Pi online ở mạng nào cũng tự nối PC (IP 100.x.y.z không đổi)"
    echo "  • Xem dashboard PC: http://127.0.0.1:8766/ → Tab Edge"
    echo "  • Xem log Pi:       journalctl -u quan_ai_edge -f"
    echo "========================================================================"
}

# ------------------------------------------------------------------------------
# MAIN — chọn chế độ theo tham số
# ------------------------------------------------------------------------------
case "${1:-}" in
    --tailscale-only) install_tailscale ;;
    --repoint)        repoint_core ;;
    *)                deploy_full ;;
esac
