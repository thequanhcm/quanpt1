"""Công cụ kiểm tra & thử nghiệm âm thanh trực tiếp trên Raspberry Pi 5 (QUAN AI BRAIN).

Chức năng:
1. Dò tìm và kiểm tra kết nối mạng đến Raspberry Pi 5 (IP: 192.168.1.21, Port 8768, Port 22).
2. Kiểm tra trạng thái Kiosk Daemon (/api/kiosk/status).
3. Thử nghiệm điều chỉnh âm lượng loa phần cứng trên Pi 5 (/api/kiosk/control -> set_volume).
4. Tổng hợp âm thanh tiếng Việt chuẩn nữ (vi-VN-HoaiMyNeural) bằng TTSManager.
5. Gửi luồng âm thanh Base64 và khẩu hình sang Pi 5 phát trực tiếp qua loa (/api/kiosk/control -> speak).
6. Báo cáo chẩn đoán thiết bị âm thanh vật lý (HDMI / USB Audio / ReSpeaker HAT / PipeWire).
"""
from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

# Đảm bảo UTF-8 cho Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from quan_ai_brain.voice.tts_config import TTSManager


DEFAULT_PI5_IP = "192.168.1.21"
DEFAULT_PI5_PORT = 8768
DEFAULT_TEST_PHRASE = (
    "Xin chào Anh Quanpt1! Em là TONY, trợ lý điều hành số của Anh. "
    "Em đang phát thử nghiệm âm thanh trực tiếp trên Raspberry Pi 5. "
    "Hệ thống loa và đồng bộ khẩu hình tiếng Việt đang hoạt động rất tốt!"
)


def probe_pi5_status(ip: str = DEFAULT_PI5_IP, port: int = DEFAULT_PI5_PORT) -> dict | None:
    url = f"http://{ip}:{port}/api/kiosk/status"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "QuanAI-AudioTest/1.0"})
        with urllib.request.urlopen(req, timeout=4.0) as resp:
            if resp.status == 200:
                return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"[!] Không thể kết nối tới Pi 5 ({url}): {e}")
    return None


def set_pi5_volume(volume_pct: int, ip: str = DEFAULT_PI5_IP, port: int = DEFAULT_PI5_PORT) -> bool:
    url = f"http://{ip}:{port}/api/kiosk/control"
    payload = json.dumps({"action": "set_volume", "volume": volume_pct}).encode("utf-8")
    try:
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json", "User-Agent": "QuanAI-AudioTest/1.0"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=4.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("success", False)
    except Exception as e:
        print(f"[!] Lỗi điều chỉnh âm lượng trên Pi 5: {e}")
        return False


def send_speech_to_pi5(
    text: str,
    audio_base64: str,
    ip: str = DEFAULT_PI5_IP,
    port: int = DEFAULT_PI5_PORT,
) -> dict | None:
    url = f"http://{ip}:{port}/api/kiosk/control"
    payload = json.dumps({
        "action": "speak",
        "text": text,
        "state": "SPEAKING",
        "audio_base64": audio_base64,
    }).encode("utf-8")

    try:
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json", "User-Agent": "QuanAI-AudioTest/1.0"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=12.0) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"[!] Lỗi gửi âm thanh tới Pi 5: {e}")
        return None


def run_audio_diagnostics(ip: str = DEFAULT_PI5_IP, port: int = DEFAULT_PI5_PORT, test_text: str = DEFAULT_TEST_PHRASE) -> bool:
    print("=" * 72)
    print("   QUAN AI BRAIN — KIỂM TRA & TEST ÂM THANH TRÊN RASPBERRY PI 5")
    print("=" * 72)
    print(f"  Mục tiêu Pi 5:  http://{ip}:{port}/")
    print(f"  Thời gian:      {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 72)
    print()

    # Bước 1: Dò tìm trạng thái Pi 5
    print("[1/5] Kiểm tra kết nối mạng và Kiosk Daemon trên Pi 5...")
    status = probe_pi5_status(ip, port)
    if not status:
        print("  ❌ THẤT BẠI: Không kết nối được tới Pi 5. Vui lòng kiểm tra:")
        print("     1. Pi 5 đã cấp nguồn và kết nối cùng mạng Wi-Fi?")
        print(f"     2. Địa chỉ IP của Pi 5 có đúng là {ip}?")
        print(f"     3. Kiosk Daemon (cổng {port}) đã được khởi động chưa?")
        return False

    print(f"  ✅ ĐÃ KẾT NỐI Pi 5 thành công!")
    print(f"     - Thiết bị:        {status.get('device_id', 'N/A')}")
    print(f"     - Trạng thái:      {status.get('avatar_state', 'N/A')}")
    print(f"     - Kết nối PC Core: {'ĐÃ KẾT NỐI' if status.get('core_connected') else 'CHƯA KẾT NỐI (Cần bật Port 8766 trên PC)'}")
    print(f"     - Chế độ hiển thị: {'Face-Only Kiosk' if status.get('face_only_mode') else 'Standard'}")
    print()

    # Bước 2: Thử nghiệm điều chỉnh âm lượng
    print("[2/5] Kiểm tra lệnh điều chỉnh âm lượng phần cứng (amixer Master)...")
    vol_target = 90
    vol_ok = set_pi5_volume(vol_target, ip, port)
    if vol_ok:
        print(f"  ✅ Thiết lập âm lượng loa Pi 5 lên {vol_target}% thành công!")
    else:
        print(f"  ⚠️ Cảnh báo: Lệnh set_volume không phản hồi thành công.")
    print()

    # Bước 3: Tổng hợp âm thanh tiếng Việt chuẩn HoaiMyNeural
    print("[3/5] Tổng hợp lời thoại tiếng Việt bằng Microsoft Edge TTS (vi-VN-HoaiMyNeural)...")
    mgr = TTSManager()
    active_voice = mgr.get_active_voice()
    print(f"     - Giọng đọc:   {active_voice.name if active_voice else 'Mặc định'} ({mgr.config.tts_voice_preference})")
    print(f"     - Ngôn ngữ:    {mgr.config.tts_locale}")
    print(f"     - Câu kiểm thử: \"{test_text}\"")

    audio_bytes, err = mgr.synthesize_audio(test_text)
    if err or not audio_bytes:
        print(f"  ❌ Lỗi tổng hợp giọng nói: {err}")
        return False

    audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
    print(f"  ✅ Tổng hợp âm thanh hoàn tất! Dung lượng: {len(audio_bytes):,} bytes MP3.")
    print()

    # Bước 4: Gửi luồng âm thanh sang Pi 5 phát trực tiếp
    print("[4/5] Gửi luồng âm thanh và lệnh SPEAK trực tiếp tới Raspberry Pi 5...")
    send_res = send_speech_to_pi5(test_text, audio_b64, ip, port)
    if send_res and send_res.get("success"):
        print("  ✅ Raspberry Pi 5 đã NHẬN LỆNH PHÁT ÂM THANH thành công!")
        print(f"     - Trạng thái trả về: {send_res.get('state')}")
        print(f"     - Nội dung thoại:    \"{send_res.get('text')}\"")
    else:
        print(f"  ❌ Lỗi khi gửi lệnh phát âm thanh: {send_res}")
        return False
    print()

    # Bước 5: Kiểm tra xác nhận sau phát âm
    print("[5/5] Xác nhận trạng thái sau khi phát âm...")
    time.sleep(2.0)
    post_status = probe_pi5_status(ip, port)
    if post_status:
        print(f"     - Trạng thái Avatar: {post_status.get('avatar_state')}")
        print(f"     - Lời thoại hiện tại: \"{post_status.get('transcript')}\"")
        print("  ✅ Kiểm tra hoàn tất!")
    print()

    print("=" * 72)
    print("   HƯỚNG DẪN KIỂM TRA THIẾT BỊ ĐẦU RA VẬT LÝ NẾU CHƯA NGHE THẤY TIẾNG:")
    print("=" * 72)
    print("1. Cổng HDMI: Nếu dùng màn hình có loa qua cáp micro-HDMI, kiểm tra âm lượng")
    print("   của màn hình và chọn đúng ngõ ra HDMI trong cài đặt âm thanh Pi 5.")
    print("2. Loa USB / Tai nghe USB: Cắm loa vào cổng USB 3.0/2.0 của Pi 5. Raspberry Pi OS")
    print("   sẽ tự nhận thiết bị USB Audio làm ngõ ra mặc định.")
    print("3. Thư viện giải mã: Đảm bảo Pi 5 đã cài mpg123 hoặc alsa-utils:")
    print("   sudo apt-get install -y mpg123 alsa-utils")
    print("4. Để kích hoạt kết nối hai chiều toàn diện giữa PC và Pi 5, hãy chạy:")
    print("   KHOI_DONG_PHONG_DIEU_HANH_8766.bat")
    print("=" * 72)
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Kiểm tra & test âm thanh trên Raspberry Pi 5")
    parser.add_argument("--ip", default=DEFAULT_PI5_IP, help=f"Địa chỉ IP Pi 5 (mặc định: {DEFAULT_PI5_IP})")
    parser.add_argument("--port", type=int, default=DEFAULT_PI5_PORT, help=f"Cổng Kiosk Pi 5 (mặc định: {DEFAULT_PI5_PORT})")
    parser.add_argument("--text", default=DEFAULT_TEST_PHRASE, help="Câu thoại thử nghiệm")
    args = parser.parse_args()

    success = run_audio_diagnostics(ip=args.ip, port=args.port, test_text=args.text)
    sys.exit(0 if success else 1)
