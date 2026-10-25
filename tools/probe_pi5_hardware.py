"""Kiểm tra và chẩn đoán phần cứng Âm thanh (Micro, Loa) và Thị giác (Camera) trên Raspberry Pi 5.

Quy trình:
1. Soạn thảo kịch bản cấu hình & quét phần cứng AV toàn diện.
2. Tải lên Raspberry Pi 5 qua cổng Kiosk 8768.
3. Kích hoạt tự động quét và định tuyến.
4. Thu thập báo cáo JSON chi tiết về Micro, Camera, Loa.
"""
from __future__ import annotations

import base64
import json
from pathlib import Path
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PI5_IP = "192.168.1.21"
PI5_PORT = 8768

PROBE_SCRIPT = r"""#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_JSON="$SCRIPT_DIR/assets/avatar/hardware_scan.json"
SNAPSHOT_PATH="$SCRIPT_DIR/assets/avatar/camera_snapshot.jpg"

mkdir -p "$SCRIPT_DIR/assets/avatar"

echo "=== QUAN AI BRAIN — BẮT ĐẦU CHẨN ĐOÁN AV TRÊN PI 5 ==="

# 1. Thu thập thông tin USB
USB_LIST=$(lsusb 2>/dev/null || echo "lsusb không khả dụng")

# 2. Thu thập thông tin Âm thanh ALSA & PipeWire
ALSA_CARDS=$(cat /proc/asound/cards 2>/dev/null || echo "Không đọc được /proc/asound/cards")
ARECORD_LIST=$(arecord -l 2>/dev/null || echo "arecord không khả dụng")
APLAY_LIST=$(aplay -l 2>/dev/null || echo "aplay không khả dụng")

WPCTL_STATUS=""
if command -v wpctl >/dev/null 2>&1; then
    WPCTL_STATUS=$(wpctl status 2>/dev/null || true)
fi

# 3. Thu thập thông tin Video & Camera
VIDEO_DEVICES=$(ls -1 /dev/video* 2>/dev/null || echo "Không tìm thấy /dev/video*")
V4L2_DEVICES=""
if command -v v4l2-ctl >/dev/null 2>&1; then
    V4L2_DEVICES=$(v4l2-ctl --list-devices 2>/dev/null || true)
fi

RPICAM_STATUS=""
if command -v rpicam-hello >/dev/null 2>&1; then
    RPICAM_STATUS=$(rpicam-hello --list-cameras 2>/dev/null || true)
elif command -v libcamera-hello >/dev/null 2>&1; then
    RPICAM_STATUS=$(libcamera-hello --list-cameras 2>/dev/null || true)
fi

# 4. Định tuyến âm thanh Loa & Mic USB
if command -v wpctl >/dev/null 2>&1; then
    # Tìm USB Sink
    USB_SINK_ID=$(wpctl status | awk '/Sinks:/,/Sources:/' | grep -iE 'usb|headset|speaker|dac|sound' | head -n 1 | grep -oE '[0-9]+' | head -n 1 || true)
    if [ -n "$USB_SINK_ID" ]; then
        wpctl set-default "$USB_SINK_ID" 2>/dev/null || true
        wpctl set-volume @DEFAULT_AUDIO_SINK@ 90% 2>/dev/null || true
        wpctl set-mute @DEFAULT_AUDIO_SINK@ 0 2>/dev/null || true
    else
        wpctl set-volume @DEFAULT_AUDIO_SINK@ 90% 2>/dev/null || true
        wpctl set-mute @DEFAULT_AUDIO_SINK@ 0 2>/dev/null || true
    fi

    # Tìm USB Source (Mic)
    USB_SOURCE_ID=$(wpctl status | awk '/Sources:/,/Filters:/' | grep -iE 'usb|mic|headset|input' | head -n 1 | grep -oE '[0-9]+' | head -n 1 || true)
    if [ -n "$USB_SOURCE_ID" ]; then
        wpctl set-default "$USB_SOURCE_ID" 2>/dev/null || true
        wpctl set-volume @DEFAULT_AUDIO_SOURCE@ 90% 2>/dev/null || true
        wpctl set-mute @DEFAULT_AUDIO_SOURCE@ 0 2>/dev/null || true
    else
        wpctl set-volume @DEFAULT_AUDIO_SOURCE@ 90% 2>/dev/null || true
        wpctl set-mute @DEFAULT_AUDIO_SOURCE@ 0 2>/dev/null || true
    fi
fi

amixer set Master 90% unmute 2>/dev/null || true
amixer set Speaker 90% unmute 2>/dev/null || true
amixer set Capture 90% cap 2>/dev/null || true
amixer set Mic 90% cap 2>/dev/null || true

# 5. Kiểm tra ghi âm thử 1 giây (Mic check)
MIC_TEST_RESULT="CHƯA KIỂM TRA"
if command -v arecord >/dev/null 2>&1; then
    if arecord -d 1 -f cd /tmp/test_mic_probe.wav 2>/dev/null; then
        FILE_SIZE=$(stat -c%s /tmp/test_mic_probe.wav 2>/dev/null || echo 0)
        if [ "$FILE_SIZE" -gt 1000 ]; then
            MIC_TEST_RESULT="THÀNH CÔNG (Thu được $FILE_SIZE bytes âm thanh)"
        else
            MIC_TEST_RESULT="CẢNH BÁO: Tệp ghi âm rỗng ($FILE_SIZE bytes)"
        fi
        rm -f /tmp/test_mic_probe.wav
    else
        MIC_TEST_RESULT="KHÔNG GHI ĐƯỢC: arecord báo lỗi"
    fi
fi

# 6. Kiểm tra chụp ảnh thử (Camera check)
CAMERA_TEST_RESULT="CHƯA KIỂM TRA"
CAMERA_HAS_IMAGE=false

# Thử qua rpicam-still (CSI Camera)
if [ -n "$RPICAM_STATUS" ] && echo "$RPICAM_STATUS" | grep -qvE 'No cameras available|None'; then
    if command -v rpicam-still >/dev/null 2>&1; then
        if rpicam-still -t 800 -o "$SNAPSHOT_PATH" --width 640 --height 480 -n 2>/dev/null; then
            CAMERA_TEST_RESULT="THÀNH CÔNG (CSI Camera via rpicam-still)"
            CAMERA_HAS_IMAGE=true
        fi
    fi
fi

# Nếu chưa chụp được, thử qua USB V4L2 Webcam
if [ "$CAMERA_HAS_IMAGE" = false ] && ls /dev/video* >/dev/null 2>&1; then
    # Thử fswebcam
    if command -v fswebcam >/dev/null 2>&1; then
        if fswebcam -r 640x480 --no-banner "$SNAPSHOT_PATH" 2>/dev/null; then
            CAMERA_TEST_RESULT="THÀNH CÔNG (USB Webcam via fswebcam)"
            CAMERA_HAS_IMAGE=true
        fi
    fi
    # Thử ffmpeg v4l2
    if [ "$CAMERA_HAS_IMAGE" = false ] && command -v ffmpeg >/dev/null 2>&1; then
        FIRST_VIDEO=$(ls /dev/video* 2>/dev/null | head -n 1)
        if ffmpeg -y -f v4l2 -video_size 640x480 -i "$FIRST_VIDEO" -frames 1 "$SNAPSHOT_PATH" -loglevel quiet 2>/dev/null; then
            CAMERA_TEST_RESULT="THÀNH CÔNG (USB Webcam via ffmpeg v4l2: $FIRST_VIDEO)"
            CAMERA_HAS_IMAGE=true
        fi
    fi
fi

if [ "$CAMERA_HAS_IMAGE" = false ]; then
    if [ "$CAMERA_TEST_RESULT" = "CHƯA KIỂM TRA" ]; then
        CAMERA_TEST_RESULT="CHƯA PHÁT HIỆN THIẾT BỊ CAMERA VẬT LÝ"
    fi
fi

# 7. Xuất file kết quả JSON
python3 -c "
import json, time, os

data = {
    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
    'epoch': time.time(),
    'hostname': os.uname().nodename,
    'kernel': os.uname().release,
    'usb_devices': '''$USB_LIST'''.strip().split('\n'),
    'audio': {
        'alsa_cards': '''$ALSA_CARDS'''.strip(),
        'arecord_list': '''$ARECORD_LIST'''.strip(),
        'aplay_list': '''$APLAY_LIST'''.strip(),
        'wpctl_summary': '''$WPCTL_STATUS'''.strip(),
        'mic_test': '''$MIC_TEST_RESULT'''
    },
    'video': {
        'dev_video': '''$VIDEO_DEVICES'''.strip().split('\n'),
        'v4l2_devices': '''$V4L2_DEVICES'''.strip(),
        'rpicam_cameras': '''$RPICAM_STATUS'''.strip(),
        'camera_test': '''$CAMERA_TEST_RESULT''',
        'has_snapshot': os.path.exists('$SNAPSHOT_PATH')
    }
}

with open('$OUTPUT_JSON', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print('Đã ghi báo cáo phần cứng thành công!')
"

echo "=== HOÀN TẤT CHẨN ĐOÁN AV TRÊN PI 5 ==="
"""


def upload_file(filename: str, content_str: str) -> bool:
    content_b64 = base64.b64encode(content_str.encode("utf-8")).decode("ascii")
    url = f"http://{PI5_IP}:{PI5_PORT}/api/kiosk/files/upload"
    payload = json.dumps({"filename": filename, "content_b64": content_b64}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "QuanAI-HardwareProbe/1.0"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10.0) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        return res.get("success", False)


def trigger_scan() -> bool:
    url = f"http://{PI5_IP}:{PI5_PORT}/api/kiosk/control"
    payload = json.dumps({"action": "auto_configure_audio"}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "QuanAI-HardwareProbe/1.0"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15.0) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        return res.get("success", False)


def fetch_report() -> dict | None:
    url = f"http://{PI5_IP}:{PI5_PORT}/assets/avatar/hardware_scan.json?t={int(time.time())}"
    req = urllib.request.Request(url, headers={"User-Agent": "QuanAI-HardwareProbe/1.0"})
    with urllib.request.urlopen(req, timeout=10.0) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> int:
    print("=" * 72)
    print("   QUAN AI BRAIN — CHẨN ĐOÁN PHẦN CỨNG MICRO & CAMERA TRÊN RASPBERRY PI 5")
    print("=" * 72)
    print(f"  Mục tiêu: http://{PI5_IP}:{PI5_PORT}/")

    print("\n[1/4] Đang tải kịch bản quét AV lên Raspberry Pi 5...")
    if not upload_file("setup_pi5_audio.sh", PROBE_SCRIPT):
        print("❌ Lỗi khi tải kịch bản lên Pi 5!")
        return 1
    print("✅ Đã tải lên và cấp quyền thực thi cho setup_pi5_audio.sh thành công!")

    print("\n[2/4] Đang kích hoạt quét phần cứng và định tuyến trên Pi 5...")
    if not trigger_scan():
        print("❌ Lỗi khi kích hoạt lệnh quét trên Pi 5!")
        return 1
    print("✅ Đã phát lệnh kích hoạt quét thành công! Đang chờ Pi 5 thực thi...")

    # Chờ kịch bản hoàn tất
    for i in range(1, 8):
        time.sleep(1.0)
        sys.stdout.write(f"\r  Đang đợi kiểm tra phần cứng ({i}/7s)...")
        sys.stdout.flush()
    print("\n")

    print("[3/4] Đang thu thập báo cáo phần cứng chi tiết...")
    try:
        report = fetch_report()
    except Exception as exc:
        print(f"❌ Không thể đọc báo cáo từ Pi 5: {exc}")
        return 1

    if not report:
        print("❌ Báo cáo trả về rỗng!")
        return 1

    print("\n" + "=" * 72)
    print("              KẾT QUẢ QUÉT PHẦN CỨNG VẬT LÝ TRÊN PI 5")
    print("=" * 72)
    print(f"  Thời gian quét:   {report.get('timestamp')}")
    print(f"  Hệ điều hành:     {report.get('hostname')} (Kernel: {report.get('kernel')})")

    print("\n--- 1. DANH SÁCH THIẾT BỊ USB (lsusb) ---")
    for u in report.get("usb_devices", []):
        if u.strip():
            print(f"  • {u}")

    print("\n--- 2. HỆ THỐNG ÂM THANH & MICRO (Audio / Mic) ---")
    audio = report.get("audio", {})
    print(f"  • Card ALSA:     {audio.get('alsa_cards')}")
    print(f"  • Ngõ vào thu âm (arecord):\n    {audio.get('arecord_list')}")
    print(f"  • Ngõ ra phát loa (aplay):\n    {audio.get('aplay_list')}")
    print(f"  • Kết quả thử Mic: {audio.get('mic_test')}")

    print("\n--- 3. HỆ THỐNG THỊ GIÁC & CAMERA (Vision / Camera) ---")
    video = report.get("video", {})
    print(f"  • Thiết bị /dev/video: {video.get('dev_video')}")
    print(f"  • V4L2 Devices:        {video.get('v4l2_devices') or 'None'}")
    print(f"  • CSI/libcamera:       {video.get('rpicam_cameras') or 'None'}")
    print(f"  • Kết quả thử Camera:  {video.get('camera_test')}")
    print(f"  • Ảnh chụp thử:        {'ĐÃ CÓ (camera_snapshot.jpg)' if video.get('has_snapshot') else 'CHƯA CÓ'}")

    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
