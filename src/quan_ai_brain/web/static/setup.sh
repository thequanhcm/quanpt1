#!/bin/bash
# ==============================================================================
# QUAN AI BRAIN — TỰ ĐỘNG THIẾT LẬP & ĐỒNG BỘ 1-CLICK CHO RASPBERRY PI 5
# ==============================================================================
set -e

CORE_IP="192.168.1.17"
CORE_PORT="8766"

echo ""
echo "========================================================================"
echo "    QUAN AI BRAIN — CÀI ĐẶT & ĐỒNG BỘ TỰ ĐỘNG CHO RASPBERRY PI 5"
echo "           Đồng bộ từ PC Core: http://$CORE_IP:$CORE_PORT/"
echo "========================================================================"
echo ""

# 1. Cấu hình SSH Authorized Key để PC có thể điều khiển trực tiếp từ xa
echo "[1/5] Thiết lập SSH Authorized Key không cần mật khẩu..."
mkdir -p "$HOME/.ssh"
chmod 700 "$HOME/.ssh"
PUBKEY="ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIDcSxP8XdhmhkmL+u9qdDxomwhYvWWYSZvLvfesgSrmB dell@QUANPT"
if ! grep -q "dell@QUANPT" "$HOME/.ssh/authorized_keys" 2>/dev/null; then
    echo "$PUBKEY" >> "$HOME/.ssh/authorized_keys"
    echo "  ✅ Đã thêm SSH Public Key của PC Core vào authorized_keys."
fi
chmod 600 "$HOME/.ssh/authorized_keys"

# 2. Tải gói mã nguồn mới nhất từ PC Core
echo "[2/5] Đang tải gói edge_client mới nhất từ PC Core..."
TMP_TAR="/tmp/edge_client.tar.gz"
curl -sSL "http://$CORE_IP:$CORE_PORT/edge_client.tar.gz" -o "$TMP_TAR"
echo "  ✅ Đã tải gói mã nguồn ($(stat -c%s "$TMP_TAR" 2>/dev/null || stat -f%z "$TMP_TAR") bytes)."

# 3. Giải nén vào các thư mục quy chuẩn
echo "[3/5] Đang giải nén mã nguồn vào hệ thống..."
TARGET_DIR="$HOME/Desktop/edge_client"
LINK_DIR="$HOME/quan_ai_brain/edge_client"

mkdir -p "$TARGET_DIR"
tar -xzf "$TMP_TAR" -C "$TARGET_DIR"

mkdir -p "$HOME/quan_ai_brain"
rm -rf "$LINK_DIR"
ln -sf "$TARGET_DIR" "$LINK_DIR"

echo "  ✅ Đã cập nhật tệp tin tại $TARGET_DIR và liên kết $LINK_DIR"

# 4. Cài đặt dịch vụ systemd 24/7 (tự phục hồi, chống mất nguồn)
echo "[4/4] Cài đặt dịch vụ hệ thống systemd 24/7..."
cd "$TARGET_DIR"
chmod +x *.sh *.py 2>/dev/null || true
bash setup_systemd_247.sh

echo ""
echo "========================================================================"
echo "  🎉 THÀNH CÔNG RỰC RỠ! RASPBERRY PI 5 ĐÃ HOÀN TẤT ĐỒNG BỘ 100%!"
echo "  • Cổng 8768 đang chạy ở chế độ Standby."
echo "  • Từ bây giờ, Anh chỉ cần OneClick từ PC mà không cần chạm vào Pi 5."
echo "========================================================================"
echo ""
