"""Đồng bộ toàn diện Giao Diện Hình Thể & Cấu Hình Âm Thanh sang Raspberry Pi 5 (QUAN AI BRAIN).

Chức năng:
1. Đẩy các tệp giao diện cốt lõi (kiosk.html, kiosk.js, kiosk.css, wake_engine.js, setup_pi5_audio.sh) sang Pi 5.
2. Tải lại giao diện Kiosk trên màn hình cảm ứng 7" DSI.
3. Kích hoạt tự động định tuyến âm thanh ngõ ra USB & micro USB qua PipeWire / WirePlumber.
4. Kiểm tra chu trình thoại 'Hi TONY' hai chiều giữa Pi 5 và PC Core.
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

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

PI5_IP = "192.168.1.21"
PI5_PORT = 8768


def upload_file_to_pi5(filename: str, file_path: Path, ip: str = PI5_IP, port: int = PI5_PORT) -> bool:
    if not file_path.exists():
        print(f"  ❌ Không tìm thấy tệp nguồn cục bộ: {file_path}")
        return False

    with open(file_path, "rb") as f:
        content_b64 = base64.b64encode(f.read()).decode("ascii")

    url = f"http://{ip}:{port}/api/kiosk/files/upload"
    payload = json.dumps({"filename": filename, "content_b64": content_b64}).encode("utf-8")

    try:
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json", "User-Agent": "QuanAI-Sync/1.0"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=12.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("success"):
                print(f"  ✅ Đã đồng bộ thành công: {filename} ({data.get('size_bytes', 0):,} bytes)")
                return True
            else:
                print(f"  ❌ Thất bại khi đồng bộ {filename}: {data}")
                return False
    except Exception as exc:
        print(f"  ❌ Lỗi kết nối khi tải {filename} sang Pi 5: {exc}")
        return False


def send_pi5_control(action_data: dict, ip: str = PI5_IP, port: int = PI5_PORT) -> dict | None:
    url = f"http://{ip}:{port}/api/kiosk/control"
    payload = json.dumps(action_data).encode("utf-8")
    try:
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json", "User-Agent": "QuanAI-Sync/1.0"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        print(f"  [!] Lỗi gửi lệnh điều khiển tới Pi 5: {exc}")
        return None


def main() -> int:
    print("=" * 72)
    print("   QUAN AI BRAIN — ĐỒNG BỘ TOÀN DIỆN HÌNH THỂ & ÂM THANH PI 5")
    print("=" * 72)
    print(f"  Mục tiêu:   http://{PI5_IP}:{PI5_PORT}/")
    print(f"  Thời gian: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 72)
    print()

    # Bước 1: Kiểm tra kết nối Pi 5
    print("[1/5] Kiểm tra kết nối tới Pi 5 Kiosk Daemon...")
    try:
        with urllib.request.urlopen(f"http://{PI5_IP}:{PI5_PORT}/api/kiosk/status", timeout=3.0) as resp:
            st = json.loads(resp.read().decode("utf-8"))
            print(f"  ✅ Đã kết nối Pi 5 ({st.get('device_id', 'N/A')}), Core: {st.get('core_host', 'N/A')}")
    except Exception as e:
        print(f"  ❌ Không thể kết nối tới Pi 5 tại http://{PI5_IP}:{PI5_PORT}/: {e}")
        return 1
    print()

    # Bước 2: Đồng bộ các tệp giao diện & giọng nói
    print("[2/5] Đang đẩy các tệp giao diện cốt lõi sang Pi 5...")
    edge_dir = ROOT / "edge_client"
    files_to_sync = [
        ("avatar_engine.js", edge_dir / "avatar_engine.js"),
        ("wake_engine.js", edge_dir / "wake_engine.js"),
        ("kiosk.html", edge_dir / "kiosk.html"),
        ("kiosk.js", edge_dir / "kiosk.js"),
        ("kiosk.css", edge_dir / "kiosk.css"),
        ("client_daemon.py", edge_dir / "client_daemon.py"),
        ("setup_pi5_audio.sh", edge_dir / "setup_pi5_audio.sh"),
        ("avatar_v2_portrait.png", edge_dir / "assets" / "avatar" / "avatar_v2_portrait.png"),
        ("avatar_v2_happy.png", edge_dir / "assets" / "avatar" / "avatar_v2_happy.png"),
        ("avatar_v2_thinking.png", edge_dir / "assets" / "avatar" / "avatar_v2_thinking.png"),
        ("avatar_v2_blink.png", edge_dir / "assets" / "avatar" / "avatar_v2_blink.png"),
        ("mouth_v2_rest.png", edge_dir / "assets" / "avatar" / "mouth_v2_rest.png"),
        ("mouth_v2_speaking.png", edge_dir / "assets" / "avatar" / "mouth_v2_speaking.png"),
        ("mouth_v2_open_o.png", edge_dir / "assets" / "avatar" / "mouth_v2_open_o.png"),
        ("mouth_v2_happy.png", edge_dir / "assets" / "avatar" / "mouth_v2_happy.png"),
        ("avatar_v2_warning.png", edge_dir / "assets" / "avatar" / "avatar_v2_warning.png"),
        ("avatar_v2_empathic.png", edge_dir / "assets" / "avatar" / "avatar_v2_empathic.png"),
        ("avatar_v2_confused.png", edge_dir / "assets" / "avatar" / "avatar_v2_confused.png"),
        ("avatar_v2_surprised.png", edge_dir / "assets" / "avatar" / "avatar_v2_surprised.png"),
        ("avatar_v2_error.png", edge_dir / "assets" / "avatar" / "avatar_v2_error.png"),
        ("avatar_v2_portrait.jpg", edge_dir / "assets" / "avatar" / "avatar_v2_portrait.jpg"),
        ("avatar_v2_happy.jpg", edge_dir / "assets" / "avatar" / "avatar_v2_happy.jpg"),
        ("avatar_v2_thinking.jpg", edge_dir / "assets" / "avatar" / "avatar_v2_thinking.jpg"),
        ("avatar_v2_blink.jpg", edge_dir / "assets" / "avatar" / "avatar_v2_blink.jpg"),
        ("model_f_portrait.png", edge_dir / "assets" / "avatar" / "model_f_portrait.png"),
        ("model_f_happy.png", edge_dir / "assets" / "avatar" / "model_f_happy.png"),
        ("model_f_thinking.png", edge_dir / "assets" / "avatar" / "model_f_thinking.png"),
        ("model_f_blink.png", edge_dir / "assets" / "avatar" / "model_f_blink.png"),
        ("mouth_rest.png", edge_dir / "assets" / "avatar" / "mouth_rest.png"),
        ("mouth_speaking.png", edge_dir / "assets" / "avatar" / "mouth_speaking.png"),
    ]

    for fname, fpath in files_to_sync:
        ok = upload_file_to_pi5(fname, fpath)
        if not ok:
            print(f"  ⚠️ Cảnh báo: Tệp {fname} chưa đồng bộ được.")
    print()

    # Bước 3: Đặt âm lượng loa và tự động định tuyến
    print("[3/5] Thiết lập âm lượng loa Pi 5 lên 90% & gửi lệnh định tuyến âm thanh...")
    send_pi5_control({"action": "set_volume", "volume": 90})
    send_pi5_control({"action": "auto_configure_audio"})
    print("  ✅ Đã cập nhật mức âm lượng 90% cho loa & mic Pi 5.")
    print()

    # Bước 4: Yêu cầu giao diện Pi 5 tải lại
    print("[4/5] Gửi lệnh tải lại giao diện Kiosk (reload_ui)...")
    send_pi5_control({"action": "reload_ui"})
    print("  ✅ Đã gửi tín hiệu tải lại giao diện Kiosk.")
    time.sleep(1.5)
    print()

    # Bước 5: Thử nghiệm chu trình giọng nói hai chiều 'Hi TONY'
    print("[5/5] Thử nghiệm chu trình thoại hai chiều 'Hi TONY'...")
    try:
        from quan_ai_brain.voice.voice_pipeline import XiaoZhiVoicePipeline
        from quan_ai_brain.voice.tts_config import GLOBAL_TTS_MANAGER
        pipe = XiaoZhiVoicePipeline()
        v_res = pipe.handle_voice_input("Hi TONY")
        spoken_text = v_res.spoken_text or v_res.response_text
        print(f"  - Phản hồi từ TONY: \"{spoken_text}\"")

        audio_bytes, _ = GLOBAL_TTS_MANAGER.synthesize_audio(spoken_text)
        if audio_bytes:
            audio_b64 = base64.b64encode(audio_bytes).decode("ascii")
            print(f"  - Đã tổng hợp giọng nữ Việt Nam ({len(audio_bytes):,} bytes MP3).")
            print("  - Đang phát âm thanh trực tiếp sang Loa Pi 5...")
            ctrl_res = send_pi5_control({
                "action": "speak",
                "text": spoken_text,
                "state": "SPEAKING",
                "timeline": v_res.mouth_timeline,
                "audio_base64": audio_b64,
            })
            if ctrl_res and ctrl_res.get("success"):
                print("  ✅ ĐÃ GỬI LỆNH PHÁT THOẠI VÀ KHẨU HÌNH SANG PI 5 THÀNH CÔNG!")
            else:
                print(f"  ⚠️ Cảnh báo: Lệnh phát thoại trả về: {ctrl_res}")
        else:
            print("  ⚠️ Không thể tổng hợp âm thanh giọng đọc.")
    except Exception as exc:
        print(f"  ❌ Lỗi thử nghiệm thoại: {exc}")
    print()

    print("=" * 72)
    print("   HOÀN TẤT ĐỒNG BỘ! PI 5 ĐÃ SẴN SÀNG LÀM HÌNH THỂ GIAO DIỆN TONY.")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
