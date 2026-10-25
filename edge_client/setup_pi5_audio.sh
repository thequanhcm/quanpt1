#!/bin/bash
# ==============================================================================
# QUAN AI BRAIN — CẤU HÌNH & CHẨN ĐOÁN ÂM THANH VẬT LÝ CHO RASPBERRY PI 5
# Định tuyến tự động: Loa USB / Tai nghe USB & Microphone USB (PipeWire/WirePlumber)
# ==============================================================================
set -e

echo "========================================================================"
echo "    QUAN AI BRAIN — CẤU HÌNH THIẾT BỊ ÂM THANH VẬT LÝ TRÊN PI 5"
echo "           ĐỊNH TUYẾN LOA USB & MICROPHONE USB CHO TONY"
echo "========================================================================"

# 1. Kiểm tra PipeWire / WirePlumber
if ! command -v wpctl >/dev/null 2>&1; then
    echo "[!] Cảnh báo: wpctl không tìm thấy. Đang kiểm tra hệ thống ALSA cổ điển..."
else
    echo "[1/4] Dò tìm thiết bị âm thanh qua PipeWire / WirePlumber (wpctl)..."
    
    # Lấy thông tin sinks (loa)
    echo "--- DANH SÁCH THIẾT BỊ ÂM THANH HIỆN TẠI ---"
    wpctl status || true
    echo "--------------------------------------------"

    # Tìm ID của USB Audio Sink (Loa USB)
    USB_SINK_ID=$(wpctl status | awk '/Sinks:/,/Sources:/' | grep -iE 'usb|headset|speaker|dac|sound' | head -n 1 | grep -oE '[0-9]+' | head -n 1 || true)
    
    if [ -n "$USB_SINK_ID" ]; then
        echo "  ✅ Tìm thấy Loa/Ngõ ra USB Audio với ID: $USB_SINK_ID"
        echo "     -> Thiết lập làm Loa ngõ ra mặc định (Default Audio Sink)..."
        wpctl set-default "$USB_SINK_ID"
        wpctl set-volume @DEFAULT_AUDIO_SINK@ 90%
        wpctl set-mute @DEFAULT_AUDIO_SINK@ 0
        echo "  ✅ Đã đặt âm lượng loa ngõ ra lên 90% (Bật tiếng)."
    else
        echo "  ⚠️ Không tìm thấy thiết bị USB riêng biệt trong Sinks, đặt ngõ ra mặc định lên 90%..."
        wpctl set-volume @DEFAULT_AUDIO_SINK@ 90% 2>/dev/null || true
        wpctl set-mute @DEFAULT_AUDIO_SINK@ 0 2>/dev/null || true
    fi

    # Tìm ID của USB Audio Source (Micro USB)
    USB_SOURCE_ID=$(wpctl status | awk '/Sources:/,/Filters:/' | grep -iE 'usb|mic|headset|input' | head -n 1 | grep -oE '[0-9]+' | head -n 1 || true)
    
    if [ -n "$USB_SOURCE_ID" ]; then
        echo "  ✅ Tìm thấy Microphone USB với ID: $USB_SOURCE_ID"
        echo "     -> Thiết lập làm Microphone thu âm mặc định (Default Audio Source)..."
        wpctl set-default "$USB_SOURCE_ID"
        wpctl set-volume @DEFAULT_AUDIO_SOURCE@ 90%
        wpctl set-mute @DEFAULT_AUDIO_SOURCE@ 0
        echo "  ✅ Đã đặt độ nhạy Micro USB lên 90% (Bật mic)."
    else
        echo "  ⚠️ Không tìm thấy Micro USB riêng biệt trong Sources, đặt âm lượng nguồn thu mặc định lên 90%..."
        wpctl set-volume @DEFAULT_AUDIO_SOURCE@ 90% 2>/dev/null || true
        wpctl set-mute @DEFAULT_AUDIO_SOURCE@ 0 2>/dev/null || true
    fi
fi

# 2. Điều chỉnh mức âm lượng phần cứng ALSA (amixer)
echo "[2/4] Kiểm tra và mở khóa âm lượng phần cứng ALSA..."
amixer set Master 90% unmute 2>/dev/null || true
amixer set Speaker 90% unmute 2>/dev/null || true
amixer set PCM 90% unmute 2>/dev/null || true
amixer set Capture 90% cap 2>/dev/null || true
amixer set Mic 90% cap 2>/dev/null || true

# 3. Cài đặt các gói giải mã âm thanh nếu còn thiếu
echo "[3/4] Kiểm tra các công cụ giải mã âm thanh (mpg123, alsa-utils)..."
if ! command -v mpg123 >/dev/null 2>&1; then
    echo "  -> Đang cài đặt mpg123 và alsa-utils để phát âm thanh mượt mà..."
    sudo apt-get update -y && sudo apt-get install -y mpg123 alsa-utils mpv || true
else
    echo "  ✅ mpg123 đã sẵn sàng."
fi

# 4. Thử nghiệm phát âm thanh kiểm tra loa
echo "[4/4] Thử nghiệm phát âm thanh mẫu trên ngõ ra mặc định..."
if command -v pw-play >/dev/null 2>&1 && [ -f /usr/share/sounds/alsa/Front_Center.wav ]; then
    pw-play /usr/share/sounds/alsa/Front_Center.wav 2>/dev/null || true
elif command -v aplay >/dev/null 2>&1 && [ -f /usr/share/sounds/alsa/Front_Center.wav ]; then
    aplay -q /usr/share/sounds/alsa/Front_Center.wav 2>/dev/null || true
fi

echo "========================================================================"
echo "    HOÀN TẤT CẤU HÌNH ÂM THANH! PI 5 ĐÃ SẴN SÀNG LÀM HÌNH THỂ CHO TONY"
echo "========================================================================"
