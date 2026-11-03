#!/bin/bash
# ==============================================================================
# QUAN AI BRAIN — ĐỒNG BỘ & KÍCH HOẠT AUDIO TRÊN PI5 QUA DASHBOARD
# ==============================================================================

PI5_IP="192.168.1.10"
DASHBOARD_URL="http://127.0.0.1:8766"
EDGE_CLIENT_DIR="edge_client"

echo "=========================================="
echo "QUAN AI BRAIN — PI5 AUDIO SYNC & ACTIVATE"
echo "=========================================="
echo ""

# 1. Kiểm tra dashboard đang chạy
echo "[1/5] Kiểm tra Dashboard đang chạy..."
if ! curl -s "$DASHBOARD_URL" > /dev/null 2>&1; then
    echo "❌ Dashboard không chạy tại $DASHBOARD_URL"
    echo "   Vui lòng khởi động dashboard trước khi chạy script này."
    exit 1
fi
echo "✅ Dashboard đang chạy"

# 2. Kiểm tra Pi5 reachable
echo ""
echo "[2/5] Kiểm tra kết nối đến Pi5 ($PI5_IP)..."
if ! ping -c 2 -W 2 "$PI5_IP" > /dev/null 2>&1; then
    echo "❌ Không thể ping Pi5 tại $PI5_IP"
    echo "   Vui lòng kiểm tra kết nối mạng."
    exit 1
fi
echo "✅ Pi5 reachable"

# 3. Kiểm tra SSH
echo ""
echo "[3/5] Kiểm tra SSH trên Pi5..."
if ! ssh -o ConnectTimeout=3 -o StrictHostKeyChecking=no quanpt1@"$PI5_IP" "echo 'SSH OK'" 2>&1 | grep -q "SSH OK"; then
    echo "⚠️ SSH chưa chạy trên Pi5"
    echo ""
    echo "📋 HƯỚNG DẪN KÍCH HOẠT SSH TRÊN PI5:"
    echo "   1. Mở Terminal trên Pi5 (hoặc SSH nếu đã enable)"
    echo "   2. Chạy: sudo systemctl start sshd"
    echo "   3. Chạy: sudo systemctl enable sshd"
    echo "   4. Thử lại script này"
    echo ""
    echo "🔄 HOẶC sử dụng Dashboard Web:"
    echo "   - Mở: $DASHBOARD_URL"
    echo "   - Vào tab 'Remote File Manager'"
    echo "   - Click 'Đồng Bộ Toàn Bộ Sang Pi 5'"
    echo "   - Chạy lệnh trên Pi5 console:"
    echo "     curl -s http://$PI5_IP:8766/edge_client/sync_assets.py | python3 && bash edge_client/setup_pi5_audio.sh"
    exit 1
fi
echo "✅ SSH đang chạy"

# 4. Đồng bộ files
echo ""
echo "[4/5] Đồng bộ files sang Pi5..."
rsync -avz --delete "$EDGE_CLIENT_DIR/" quanpt1@"$PI5_IP:~/edge_client/" 2>&1 | head -20
if [ $? -eq 0 ]; then
    echo "✅ Đồng bộ thành công"
else
    echo "❌ Đồng bộ thất bại"
    exit 1
fi

# 5. Chạy setup script
echo ""
echo "[5/5] Kích hoạt audio trên Pi5..."
ssh quanpt1@"$PI5_IP" "cd edge_client && bash setup_pi5_audio.sh" 2>&1 | head -50

echo ""
echo "=========================================="
echo "✅ HOÀN THÀNH"
echo "=========================================="
echo ""
echo "Tiếp theo:"
echo "1. Kiểm tra loa/mic USB được nhận diện"
echo "2. Test âm thanh: speaker-test -t wav"
echo "3. Test mic: arecord -d 5 test.wav && aplay test.wav"
echo "4. Khởi động kiosk: cd edge_client && python3 main.py"
echo ""