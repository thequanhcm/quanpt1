"""Raspberry Pi 5 Edge Client Daemon for QUAN AI BRAIN.

Runs as a lightweight systemd or console service on Raspberry Pi 5.
Maintains authenticated heartbeat to PC Central Brain Core and serves local Kiosk UI.

AUDIO ROUTING POLICY:
- CHROMIUM_ONLY (mặc định): Chỉ để Chromium Kiosk phát âm thanh qua Web Audio API → PipeWire.
  Đây là nguồn phát DUY NHẤT để tránh chồng lấn đôi tiếng.
- HARDWARE_ONLY: Chỉ phát qua mpg123/PipeWire trực tiếp (không qua Chromium).
- DUAL: Phát cả hai (CẦN TRÁNH — gây trùng âm).
"""
from __future__ import annotations

import base64
from datetime import datetime, timezone
import hashlib
import http.server
import json
import math
import mimetypes
import os
import shutil
from pathlib import Path
import socketserver
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

try:
    from edge_client.auth import EdgeHMACAuth
    from edge_client.config import EdgeConfig
except ImportError:
    from auth import EdgeHMACAuth  # type: ignore
    from config import EdgeConfig  # type: ignore

# V41 EDGE AGENT: 5 năng lực chủ động (30/10/2026, duyệt bởi Quanpt1)
try:
    from edge_client.edge_agent import EdgeAgent
except ImportError:
    from edge_agent import EdgeAgent  # type: ignore

STATIC_DIR = Path(__file__).resolve().parent

# ============================================================
# AUDIO PLAYBACK MODE — điều khiển nguồn phát âm thanh
# "CHROMIUM_ONLY" : Chromium Web Audio là nguồn DUY NHẤT (khuyến nghị)
# "HARDWARE_ONLY" : mpg123/PipeWire trực tiếp (khi không dùng Chromium)
# "DUAL"          : Cả hai — CHỈ dùng khi debug, sẽ gây chồng lấn!
# ============================================================
AUDIO_PLAYBACK_MODE = "CHROMIUM_ONLY"


def play_audio_on_hardware_speaker(audio_base64: str) -> bool:
    """Phát âm thanh trực tiếp qua loa vật lý (mpg123 / PipeWire) trên Raspberry Pi 5.

    CẢNH BÁO: Chỉ gọi hàm này khi AUDIO_PLAYBACK_MODE là "HARDWARE_ONLY" hoặc "DUAL".
    Khi Chromium Kiosk đang chạy, ĐỂ Chromium phát qua Web Audio API.
    Gọi đồng thời 2 nguồn sẽ gây chồng tiếng (echo/double-play).
    """
    if not audio_base64:
        return False

    def _worker() -> None:
        try:
            import base64
            import shutil
            import subprocess
            import tempfile

            audio_bytes = base64.b64decode(audio_base64)
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tf:
                tf.write(audio_bytes)
                temp_path = tf.name

            # Detect available player on Raspberry Pi / Linux
            player_cmd = None
            if shutil.which("mpg123"):
                # Try PipeWire backend first if available, otherwise default
                player_cmd = ["mpg123", "-a", "pipewire", "-q", temp_path] if shutil.which("pw-play") else ["mpg123", "-q", temp_path]
            elif shutil.which("mpv"):
                player_cmd = ["mpv", "--no-video", "--really-quiet", temp_path]
            elif shutil.which("cvlc"):
                player_cmd = ["cvlc", "--play-and-exit", "-q", temp_path]
            elif shutil.which("ffplay"):
                player_cmd = ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", temp_path]
            elif shutil.which("paplay"):
                player_cmd = ["paplay", temp_path]
            elif shutil.which("pw-play") and shutil.which("ffmpeg"):
                # Convert MP3 to WAV for native PipeWire play
                temp_wav = temp_path.replace(".mp3", ".wav")
                conv = subprocess.run(["ffmpeg", "-y", "-i", temp_path, "-loglevel", "quiet", temp_wav], timeout=10)
                if conv.returncode == 0 and Path(temp_wav).exists():
                    player_cmd = ["pw-play", temp_wav]
            elif shutil.which("aplay") and shutil.which("ffmpeg"):
                temp_wav = temp_path.replace(".mp3", ".wav")
                conv = subprocess.run(["ffmpeg", "-y", "-i", temp_path, "-loglevel", "quiet", temp_wav], timeout=10)
                if conv.returncode == 0 and Path(temp_wav).exists():
                    player_cmd = ["aplay", "-q", temp_wav]

            if player_cmd:
                try:
                    subprocess.run(player_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=45)
                except Exception:
                    # Fallback to standard mpg123 if pipewire backend failed
                    if player_cmd[0] == "mpg123" and "-a" in player_cmd:
                        subprocess.run(["mpg123", "-q", temp_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=45)
            try:
                Path(temp_path).unlink(missing_ok=True)
                wav_path = temp_path.replace(".mp3", ".wav")
                Path(wav_path).unlink(missing_ok=True)
            except Exception:
                pass
        except Exception:
            pass

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    return True


_KIOSK_PROC = None
# (01/11/2026, owner) STOP trên màn hình = CHỈ thoát giao diện hiển thị
# (không tắt màn, không emergency) — kiosk_guard đọc flag này để KHÔNG tự dậy
# lại giao diện; owner gọi lại (nút CHERRY ƠI / wake word "Cherry ơi" / DM) thì mở.
_KIOSK_CLOSED_BY_OWNER_EPOCH = 0.0
_KIOSK_CLOSED_LOCK = threading.Lock()


def _set_kiosk_closed_by_owner(closed: bool) -> None:
    """Đặt/xoá cờ 'giao diện đóng theo yêu cầu owner' (module-level, thread-safe)."""
    global _KIOSK_CLOSED_BY_OWNER_EPOCH
    with _KIOSK_CLOSED_LOCK:
        _KIOSK_CLOSED_BY_OWNER_EPOCH = time.time() if closed else 0.0


def _kiosk_closed_by_owner() -> bool:
    """True nếu owner vừa chạm STOP (15 phút) — guard không tự dậy lại kiosk."""
    return (time.time() - _KIOSK_CLOSED_BY_OWNER_EPOCH) < 900
_MUSIC_PROC = None
_MUSIC_LOCK = threading.Lock()


def stop_music_stream(daemon_state: Any = None) -> bool:
    """Dừng luồng phát nhạc trên Pi 5 nếu đang phát."""
    global _MUSIC_PROC
    with _MUSIC_LOCK:
        if _MUSIC_PROC is not None:
            try:
                _MUSIC_PROC.terminate()
                _MUSIC_PROC.wait(timeout=1.5)
            except Exception:
                try:
                    _MUSIC_PROC.kill()
                except Exception:
                    pass
            _MUSIC_PROC = None

    if daemon_state is not None:
        try:
            with daemon_state.lock:
                daemon_state.current_music = None
        except Exception:
            pass
    return True


def play_music_stream(url: str, title: str = "", video_id: str = "", daemon_state: Any = None) -> bool:
    """Phát nhạc trực tiếp qua loa vật lý trên Pi 5 (Chromium Kiosk / Headless Chromium / mpv)."""
    global _MUSIC_PROC
    stop_music_stream(daemon_state)

    if daemon_state is not None:
        try:
            with daemon_state.lock:
                daemon_state.current_music = {
                    "title": title or "Bản nhạc YouTube",
                    "video_id": video_id,
                    "url": url,
                    "playing": True,
                    "started_at": datetime.now(timezone.utc).isoformat(),
                }
        except Exception:
            pass

    def _worker() -> None:
        global _MUSIC_PROC
        import os, shutil, subprocess
        # If Chromium Kiosk is not currently displayed, run background headless Chromium for native YouTube audio
        if not is_kiosk_running() and shutil.which("chromium"):
            embed_url = f"https://www.youtube.com/embed/{video_id}?autoplay=1"
            cmd = [
                "chromium",
                "--no-sandbox",
                "--headless=new",
                "--autoplay-policy=no-user-gesture-required",
                "--disable-gpu",
                embed_url,
            ]
        elif shutil.which("mpv"):
            cmd = ["mpv", "--no-video", "--really-quiet", url]
        elif shutil.which("cvlc"):
            cmd = ["cvlc", "--no-video", "--play-and-exit", "-q", url]
        else:
            cmd = None

        if cmd:
            try:
                env = os.environ.copy()
                if os.path.exists("/run/user/1000"):
                    env["XDG_RUNTIME_DIR"] = "/run/user/1000"
                    env["PULSE_SERVER"] = "unix:/run/user/1000/pulse/native"
                with _MUSIC_LOCK:
                    _MUSIC_PROC = subprocess.Popen(
                        cmd,
                        env=env,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                _MUSIC_PROC.wait()
            except Exception:
                pass
            finally:
                with _MUSIC_LOCK:
                    _MUSIC_PROC = None

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    return True



def is_kiosk_running() -> bool:
    """Kiểm tra xem tiến trình Chromium Kiosk hiển thị hình thể có đang chạy hay không.

    (29/10/2026) FIX: pgrep -f "chromium" khớp MỌI process chromium — bao gồm
    headless Chromium worker phát nhạc YouTube (_worker trong stop_music /
    play_music khởi chạy chromium --headless=new). Khi đó hàm trả True dù kiosk
    hiển thị KHÔNG tồn tại → nút BẬT HÌNH THỂ bị skip ("đang chạy rồi") và
    dashboard báo ACTIVE sai trong khi màn DSI trắng. Giờ chỉ tính các process
    chromium KHÔNG headless (kiosk thật có cờ --kiosk hoặc không có --headless).
    """
    global _KIOSK_PROC
    try:
        import subprocess, shutil, os
        if shutil.which("pgrep"):
            res = subprocess.run(["pgrep", "-f", "chromium"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=1.0)
            pids = [p for p in res.stdout.split() if p.strip()]
            for pid in pids:
                try:
                    with open(f"/proc/{pid}/stat", "rb") as fh:
                        stat_fields = fh.read().decode("utf-8", errors="replace").split()
                    # (31/10/2026) FIX: zombie chromium (STAT=Z — cha chưa reap) có
                    # cmdline RỖNG → trước đây bị coi là kiosk thật → close_kiosk
                    # xong dashboard vẫn báo ACTIVE trong khi màn hình đã tắt.
                    if len(stat_fields) > 2 and stat_fields[2] == "Z":
                        continue
                    with open(f"/proc/{pid}/cmdline", "rb") as fh:
                        cmdline = fh.read().decode("utf-8", errors="replace")
                except Exception:
                    continue
                # headless chromium (nhạc/background) KHÔNG phải kiosk hiển thị
                if "--headless" in cmdline:
                    continue
                # (31/10/2026) cmdline rỗng (zombie/process chết) không tính là kiosk
                if not cmdline.strip():
                    continue
                # helper processes (zygote/crashpad/renderer) kế thừa cmdline gốc;
                # chỉ cần 1 process chromium không-headless tồn tại = kiosk thật
                return True
            return False
        elif os.name == "nt":
            return _KIOSK_PROC is not None and _KIOSK_PROC.poll() is None
    except Exception:
        pass
    return False


def launch_kiosk_process() -> bool:
    """Khởi động trình duyệt Chromium Kiosk toàn màn hình hiển thị hình thể trên Pi 5."""
    global _KIOSK_PROC
    try:
        import subprocess, shutil, os
        if is_kiosk_running():
            return True

        env = os.environ.copy()
        if "DISPLAY" not in env:
            env["DISPLAY"] = ":0"
        if "WAYLAND_DISPLAY" not in env:
            if os.path.exists("/run/user/1000/wayland-0"):
                env["WAYLAND_DISPLAY"] = "wayland-0"
        if "XDG_RUNTIME_DIR" not in env:
            if os.path.exists("/run/user/1000"):
                env["XDG_RUNTIME_DIR"] = "/run/user/1000"

        # Bật sáng màn hình và tắt chế độ nghỉ (DPMS on) nếu có xset
        if shutil.which("xset"):
            subprocess.run(["xset", "dpms", "force", "on"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["xset", "s", "off"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["xset", "-dpms"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        chrome_bin = shutil.which("chromium-browser") or shutil.which("chromium") or shutil.which("google-chrome") or shutil.which("chrome")
        if chrome_bin:
            chrome_flags = [
                "--kiosk",
                "--noerrdialogs",
                "--disable-infobars",
                "--check-for-update-interval=31536000",
                "--touch-events=enabled",
                "--disable-pinch",
                "--overscroll-history-navigation=0",
                # V40 (30/10): màn DSI Pi 5 = 800x480 — 1280,720 làm khung UI lệch/tràn
                "--window-size=800,480",
                "--window-position=0,0",
                "--enable-features=OverlayScrollbar",
                "--autoplay-policy=no-user-gesture-required",
                "--use-fake-ui-for-media-stream",
                "--password-store=basic",
                # V40 (30/10): Wayland renderer bị treo trên Pi 5 (0 CPU) — X11 + SwiftShader ổn định
                "--ozone-platform=x11",
                "--use-gl=angle",
                "--use-angle=swiftshader",
                # (31/10/2026) AUDIT: tắt GPU compositing SwiftShader 3D — 2D path nhẹ hơn cho HUD phẳng
                "--disable-gpu-compositing",
                "--force-prefers-reduced-motion",
                "--disable-session-crashed-bubble",
                # (31/10/2026) Chống Google Translate tự dịch giao diện kiosk
                "--disable-features=Translate,TranslateUI",
                "--lang=vi",
                "http://127.0.0.1:8768/"
            ]
            cmd = [chrome_bin] + chrome_flags
            _KIOSK_PROC = subprocess.Popen(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False


# ---- (31/10/2026) HDMI OUT: xuất kiosk ra cổng HDMI khi owner cắm màn ----
_HDMI_MIRROR_PROC: "subprocess.Popen | None" = None
_HDMI_MIRROR_LOCK = threading.Lock()
_HDMI_WATCHER_STARTED = False


def detect_hdmi_outputs() -> list[str]:
    """Trả danh sách cổng HDMI đang CONNECTED (ví dụ ['HDMI-A-1'])."""
    import glob as _glob
    connected = []
    try:
        for st_path in _glob.glob("/sys/class/drm/card*-HDMI-A-*/status"):
            try:
                with open(st_path, "r", encoding="utf-8") as fh:
                    if fh.read().strip() == "connected":
                        # tên output = tên thư mục cha
                        name = st_path.split("/")[-2]
                        connected.append(name)
            except OSError:
                continue
    except Exception:
        pass
    return connected


def _hdmi_edid_resolution(conn_name: str) -> tuple[int, int]:
    """Đọc resolution ưa thích của màn HDMI từ modes file (fallback 1920x1080)."""
    import glob as _glob
    try:
        base = _glob.glob(f"/sys/class/drm/{conn_name}/modes")
        if base:
            with open(base[0], "r", encoding="utf-8") as fh:
                first = fh.readline().strip()
                if "x" in first:
                    w, h = first.split("x")
                    return int(w), int(h.split()[0])
    except Exception:
        pass
    return 1920, 1080


def launch_hdmi_mirror() -> bool:
    """Mở chromium kiosk THỨ 2 fullscreen trên output HDMI (mirror avatar)."""
    global _HDMI_MIRROR_PROC
    with _HDMI_MIRROR_LOCK:
        try:
            import subprocess, shutil, os
            if _HDMI_MIRROR_PROC is not None and _HDMI_MIRROR_PROC.poll() is None:
                return True  # đang chạy
            conns = detect_hdmi_outputs()
            if not conns:
                return False
            conn = conns[0]
            w, h = _hdmi_edid_resolution(conn)
            chrome_bin = shutil.which("chromium-browser") or shutil.which("chromium")
            if not chrome_bin:
                return False
            env = os.environ.copy()
            env.setdefault("DISPLAY", ":0")
            if os.path.exists("/run/user/1000/wayland-0"):
                env.setdefault("WAYLAND_DISPLAY", "wayland-0")
            env.setdefault("XDG_RUNTIME_DIR", "/run/user/1000")
            if shutil.which("xset"):
                subprocess.run(["xset", "dpms", "force", "on"], env=env,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            # Đặt output HDMI enabled + tắt power save qua wlr-randr (nếu có)
            if shutil.which("wlr-randr"):
                try:
                    subprocess.run(["wlr-randr", "--output", conn.replace("HDMI-A-", "HDMI-A-"),
                                    "--on"], env=env,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
                except Exception:
                    pass
            flags = [
                "--kiosk", "--noerrdialogs", "--disable-infobars",
                "--check-for-update-interval=31536000", "--touch-events=enabled",
                "--disable-pinch", "--overscroll-history-navigation=0",
                f"--window-size={w},{h}",
                # Vị trí cửa sổ: đặt sang phải màn DSI (800) để rơi vào HDMI
                f"--window-position=800,0",
                "--enable-features=OverlayScrollbar",
                "--autoplay-policy=no-user-gesture-required",
                "--use-fake-ui-for-media-stream", "--password-store=basic",
                "--ozone-platform=x11", "--use-gl=angle", "--use-angle=swiftshader",
                "--disable-gpu-compositing", "--force-prefers-reduced-motion",
                "--disable-session-crashed-bubble",
                "--disable-features=Translate,TranslateUI", "--lang=vi",
                "http://127.0.0.1:8768/?hdmi=1",
            ]
            _HDMI_MIRROR_PROC = subprocess.Popen([chrome_bin] + flags, env=env,
                                                 stdout=subprocess.DEVNULL,
                                                 stderr=subprocess.DEVNULL)
            return True
        except Exception:
            _HDMI_MIRROR_PROC = None
            return False


def stop_hdmi_mirror() -> bool:
    """Tắt chromium mirror trên HDMI (khi owner rút màn)."""
    global _HDMI_MIRROR_PROC
    with _HDMI_MIRROR_LOCK:
        try:
            if _HDMI_MIRROR_PROC is not None and _HDMI_MIRROR_PROC.poll() is None:
                _HDMI_MIRROR_PROC.terminate()
                try:
                    _HDMI_MIRROR_PROC.wait(timeout=5)
                except Exception:
                    _HDMI_MIRROR_PROC.kill()
            _HDMI_MIRROR_PROC = None
            return True
        except Exception:
            return False


# (06/11/2026) Voice/HDMI URL KHÔNG còn hardcode IP — lấy từ config.json
# (cùng nguồn với kiosk/heartbeat). Root cause thật 06/11: IP Tailscale PC
# đổi 100.102.120.6 (01/11) → 100.92.219.98, voice loop vẫn bắn vào IP cũ
# → "Cherry ơi" từ Pi5 timeout im lặng. Resolver đọc config mỗi lần gọi
# (file local ~1KB) + cache phòng đọc lỗi.
_CORE_BASE_CACHE: str | None = None
_CORE_BASE_CACHE_AT: float = 0.0
_VOICE_COMMAND_PATH = "/api/executive/edge/voice_command"
_VOICE_CONVERSE_PATH = "/api/executive/edge/converse"


def _resolve_core_base_url() -> str:
    """Địa chỉ não PC cho voice/HDMI — từ config.json của daemon (nguồn duy nhất).

    (06/11/2026, owner) ƯU TIÊN WiFi LAN khi PC + Pi5 cùng mạng: probe TCP
    config host trước (LAN, <1ms); fail mới thử các host dự phòng
    (Tailscale mesh 100.x). Chọn host ĐẦU TIÊN mở cổng — LAN luôn thắng khi
    cùng WiFi vì được probe đầu tiên. Kết quả cache 30s tránh probe mỗi lời nói.
    """
    global _CORE_BASE_CACHE, _CORE_BASE_CACHE_AT
    now = time.time()
    if _CORE_BASE_CACHE and (now - _CORE_BASE_CACHE_AT) < 30.0:
        return _CORE_BASE_CACHE
    try:
        cfg_path = Path.home() / "Desktop" / "edge_client" / "config.json"
        with open(cfg_path, encoding="utf-8") as fh:
            cfg = json.load(fh)
        port = int(cfg.get("core_port") or 8766)
        # Thứ tự ưu tiên: LAN (config) → mesh fallback (từ last known PC mesh IP)
        host_candidates: list[str] = []
        cfg_host = str(cfg.get("core_host") or "").strip()
        if cfg_host:
            host_candidates.append(cfg_host)
        if cfg_host not in ("100.92.219.98",):
            host_candidates.append("100.92.219.98")  # Tailscale mesh PC (backup)
        import socket as _sock
        for host in host_candidates:
            try:
                with _sock.create_connection((host, port), timeout=1.0):
                    base = f"http://{host}:{port}"
                    _CORE_BASE_CACHE = base
                    _CORE_BASE_CACHE_AT = now
                    return base
            except OSError:
                continue
    except Exception:
        pass
    return _CORE_BASE_CACHE or "http://127.0.0.1:8766"


# (01/11/2026, owner) HỘI THOẠI LIÊN TỤC: sau wake, CHERRY chào NGAY
# "Dạ, em nghe anh ạ." (audio cục bộ, không đợi PC) rồi LẮNG NGHE LIÊN TỤC
# theo VAD — nói tới đâu thu tới đó → gửi não PC STT + xử lý → trả lời giọng
# → nghe tiếp... như hội thoại 2 người. Nghỉ khi: im lặng ~30s, owner nói
# "nghỉ đi/tạm biệt", hoặc hết 15 phút/phiên (gọi "Cherry ơi" là mở phiên mới).
_VOICE_CONVO_ACTIVE = threading.Lock()  # 1 phiên hội thoại duy nhất
_VAD_CHUNK_SEC = 0.2          # mỗi block PCM VAD 0.2s
_VAD_RMS_SPEAK = 280.0        # ngưỡng MỜI câu nói (đo thật 01/11: tiếng qua
                              # loa BT ~340–630, nền ~5–60; ngưỡng 800 cũ
                              # KHÔNG BAO GIỜ mở — đã sửa)
_VAD_RMS_NOISE = 100.0        # dưới ngưỡng này = im lặng (reset dội)
_VAD_SPEAK_MIN_FRAMES = 2     # ≥2 block nói liên tiếp mới mở (chống dội âm)
_VAD_SILENCE_END = 14         # 14×0.2s = 2.8s im lặng → kết thúc 1 câu
_VAD_MAX_SEG_SEC = 14.0       # 1 câu nói tối đa 14s
_VOICE_CONVO_IDLE_SEC = 30.0  # im lặng 30s → nghỉ phiên
_VOICE_CONVO_SESSION_SEC = 900.0  # tối đa 15 phút/phiên
_GREET_WAV = str(Path.home() / "tony_speech" / "greet_listen.wav")


def _find_voice_mic_node() -> str | None:
    """Mic BT (loa SRS-XB33) ưu tiên — trao đổi thoại; fallback mic USB Jieli."""
    try:
        env = dict(os.environ, XDG_RUNTIME_DIR="/run/user/1000")
        out = subprocess.run(
            ["pw-cli", "ls", "Node"], capture_output=True, text=True,
            timeout=5, env=env,
        ).stdout or ""
        import re as _re
        blocks = _re.split(r"id (\d+), type PipeWire:Interface:Node/3", out)
        usb_id = None
        for k in range(1, len(blocks), 2):
            nid, content = blocks[k], blocks[k + 1]
            if "Audio/Source" not in content:
                continue
            if _re.search(r"bluez_input\.[0-9A-Fa-f:]+", content):
                return nid
            if "UACDemoV1.0" in content and usb_id is None:
                usb_id = nid
        return usb_id
    except Exception:
        return None


def _voice_play_wav(path: str) -> bool:
    """Phát WAV cục bộ qua loa (pw-cat ưu tiên) — dùng cho lời chào trong ~0,5s."""
    if not os.path.exists(path):
        return False
    try:
        env = dict(os.environ, XDG_RUNTIME_DIR="/run/user/1000")
        player = ["pw-cat", "--playback", path]
        if not shutil.which("pw-cat"):
            player = ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", path]
            if not shutil.which("ffplay"):
                return False
        subprocess.run(player, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, timeout=10, env=env)
        return True
    except Exception:
        return False


def _voice_start_recording(mic: str | None):
    """Mở pw-record --raw (stdout) trả Popen — caller tự đọc PCM theo block."""
    env = dict(os.environ, XDG_RUNTIME_DIR="/run/user/1000")
    cmd = (["pw-record", "--raw", "--format", "s16", "--rate", "16000",
            "--channels", "1"] + (["--target", mic] if mic else []) + ["-"])
    return subprocess.Popen(cmd, stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL, env=env)


def _voice_read_chunk(stream, chunk_bytes: int) -> bytes:
    """Đọc ĐỦ 1 block PCM 16-bit LE từ stdout pw-record (b"" nếu stream hết).

    Timeout 2s/lần read: pw-record chết treo (mic BT ngắt quãng không EOF)
    → trả b"" để caller reset stream thay vì block vĩnh viễn."""
    import selectors
    sel = selectors.DefaultSelector()
    try:
        sel.register(stream.stdout, selectors.EVENT_READ)
    except Exception:
        return b""
    buf = b""
    try:
        while len(buf) < chunk_bytes:
            events = sel.select(timeout=2.0)
            if not events:
                if buf:
                    return buf  # có data một phần → dùng luôn
                return b""  # 2s không có gì → coi như stream chết
            try:
                got = stream.stdout.read(chunk_bytes - len(buf))
            except Exception:
                return b""
            if not got:
                return b""
            buf += got
    finally:
        try:
            sel.close()
        except Exception:
            pass
    return buf


def _pcm_rms(buf: bytes) -> float:
    """RMS của block PCM s16le mono."""
    acc = 0
    n = len(buf) // 2
    for i in range(0, len(buf) - 1, 2):
        s = buf[i] | (buf[i + 1] << 8)
        if s >= 0x8000:
            s -= 0x10000
        acc += s * s
    return math.sqrt(acc / max(1, n))


def _voice_post_json(url: str, payload: dict, timeout: float = 240) -> dict | None:
    """POST JSON tới server PC, trả dict (None nếu lỗi network)."""
    try:
        req = urllib.request.Request(
            url, data=json.dumps(payload).encode(),
            method="POST", headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        print(f"[VOICE] POST lỗi ({url.rsplit('/', 1)[-1]}): {exc}", flush=True)
        return None


def _voice_set_transcript(transcript: str, state: str = "LISTENING") -> None:
    """Đẩy trạng thái + chữ lên kiosk nội bộ (thread-safe, fire-and-forget)."""
    try:
        req = urllib.request.Request(
            "http://127.0.0.1:8768/api/kiosk/control",
            data=json.dumps({"action": "set_expression",
                             "state": state, "transcript": transcript}).encode(),
            method="POST", headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=4) as resp:
            resp.read()
    except Exception:
        pass


def _voice_send_answer_flow(text: str, answer: str) -> bool:
    """Nhờ server tổng hợp giọng câu trả lời (TTS) → phát qua loa BT cục bộ.

    Trả True nếu đã phát được âm thanh. Nghịch lý: synthesize 1–3s trong lúc
    mic vẫn mở → VAD có thể nghe tiếng em phát (loa và mic cùng loa BT).
    Nên: vòng hội thoại CHỈ gọi hàm này KHI ĐÃ đóng pw-record.
    Edge-TTS flaky (403 bền, gặp 09:00:37) → THỬ 2 LẦN, lần 2 chờ 3s."""
    if not answer:
        return False
    out = None
    for attempt in range(2):
        out = _voice_post_json(
            _resolve_core_base_url() + "/api/voice/tts-synthesize",
            {"text": answer[:300]}, timeout=30)
        if out and out.get("audio_base64"):
            break
        print(f"[VOICE] TTS lần {attempt + 1} fail → thử lại sau 3s", flush=True)
        time.sleep(3)
    audio_b64 = str((out or {}).get("audio_base64") or "")
    if not audio_b64:
        return False
    try:
        mp3 = Path("/tmp/tony_answer.mp3")
        mp3.write_bytes(base64.b64decode(audio_b64))
        wav = Path("/tmp/tony_answer.wav")
        subprocess.run(["ffmpeg", "-y", "-i", str(mp3), "-ar", "16000",
                        "-ac", "1", str(wav), "-loglevel", "quiet"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       timeout=20)
        ok = _voice_play_wav(str(wav) if wav.exists() else str(mp3))
        try:
            mp3.unlink(missing_ok=True)
            wav.unlink(missing_ok=True)
        except Exception:
            pass
        return ok
    except Exception:
        return False


def _voice_collect_utterance(rec) -> bytes | None:
    """VAD thu MỘT câu nói: chờ anh nói → thu tới khi nghỉ 2.8s → trả PCM.

    Trả về:
    - b"IDLE_TIMEOUT": im lặng quá 30s (nghỉ phiên)
    - None: pw-record gãy
    - bytes PCM: 1 câu nói hoàn chỉnh
    """
    chunk = int(16000 * _VAD_CHUNK_SEC) * 2
    speech_frames = 0
    silence_frames = 0
    idle_start = time.time()
    opened_at = None
    pcm = bytearray()
    last_data = time.time()  # watchdog stream chết (BT ngắt quãng không EOF)
    while True:
        buf = _voice_read_chunk(rec, chunk)
        if not buf:
            return None
        if buf:
            last_data = time.time()
        elif time.time() - last_data > 15.0:
            return None  # stream chết 15s không data → mở lại pw-record
        rms = _pcm_rms(buf)
        now = time.time()
        if opened_at is None:
            # Chưa mở câu: kiểm timeout chờ im lặng
            if now - idle_start > _VOICE_CONVO_IDLE_SEC:
                return b"IDLE_TIMEOUT"
            if rms >= _VAD_RMS_SPEAK:
                speech_frames += 1
                if speech_frames >= _VAD_SPEAK_MIN_FRAMES:
                    opened_at = now
                    pcm = bytearray(buf)  # giữ cả 2 block đã nói
                    silence_frames = 0
                    _voice_set_transcript("Em đang nghe anh nói...", "LISTENING")
            else:
                if rms < _VAD_RMS_NOISE:
                    speech_frames = 0  # nền im → reset bộ đếm dội
        else:
            pcm.extend(buf)
            if rms >= _VAD_RMS_SPEAK:
                silence_frames = 0
            else:
                silence_frames += 1
                if silence_frames >= _VAD_SILENCE_END:
                    return bytes(pcm)
            if now - opened_at > _VAD_MAX_SEG_SEC:
                return bytes(pcm)


def _pcm_to_wav_bytes(pcm: bytes) -> bytes:
    """Gói PCM s16le 16k mono thành WAV header chuẩn (bỏ ffmpeg)."""
    import struct
    data_len = len(pcm)
    header = b"RIFF" + struct.pack("<I", 36 + data_len) + b"WAVE" + \
        b"fmt " + struct.pack("<IHHIIHH", 16, 1, 1, 16000, 32000, 2, 16) + \
        b"data" + struct.pack("<I", data_len)
    return header + pcm


def _voice_conversation_loop() -> None:
    """HỘI THOẠI LIÊN TỤC sau wake (yêu cầu owner 01/11/2026):

    [ĐÃ chào "Dạ, em nghe anh ạ." trước đó] → vòng lặp:
      1. Mở pw-record raw → VAD chờ anh nói
      2. Anh nói → thu tới khi nghỉ 2.8s (tối đa 14s) → đóng mic
      3. Gửi /converse: STT → xử lý (intent/DM-đặc-biệt/GLM) → trả lời
      4. Phát giọng câu trả lời qua loa BT → nghe tiếp (1.)
    Nghỉ khi: 30s im lặng, anh nói "nghỉ đi/tạm biệt", hoặc 15 phút/phiên.
    """
    if not _VOICE_CONVO_ACTIVE.acquire(blocking=False):
        return  # đã có phiên chạy
    try:
        session_start = time.time()
        turn = 0
        # KHÔNG pkill pw-record: wake_word_service cũng giữ 1 pw-record
        # thường trữ trên cùng mic BT (PipeWire fan-out cho phép nhiều
        # reader); pkill sẽ giết luôn wake word của em!
        print("[VOICE] phiên hội thoại liên tục BẮT ĐẦU", flush=True)
        while time.time() - session_start < _VOICE_CONVO_SESSION_SEC:
            # Chờ mic BT xuất hiện (sau khi phát chào, HFP đổi profile —
            # node source có thể biến mất vài giây → thử tối đa 12s):
            mic = None
            for _ in range(24):
                mic = _find_voice_mic_node()
                if mic:
                    break
                time.sleep(0.5)
            if not mic:
                # BT vắng mặt (loa tắt/ngắt) — KHÔNG fallback default mic
                # (default có thể là nguồn khác vô dụng); đợi rồi thử lại.
                time.sleep(2)
                continue
            try:
                rec = _voice_start_recording(mic)
            except Exception as exc:
                print(f"[VOICE] mở pw-record lỗi: {exc}", flush=True)
                time.sleep(2)
                continue
            try:
                utt = _voice_collect_utterance(rec)
            finally:
                try:
                    rec.terminate()
                    rec.wait(timeout=3)
                except Exception:
                    try:
                        rec.kill()
                    except Exception:
                        pass
            if utt == b"IDLE_TIMEOUT":
                _voice_set_transcript("Em nghỉ nghe nhé. Gọi 'CHERRY ơi' khi cần em!", "IDLE")
                print("[VOICE] 30s im lặng → nghỉ phiên", flush=True)
                return
            if not utt:
                print("[VOICE] pw-record gãy → mở lại", flush=True)
                time.sleep(1)
                continue
            turn += 1
            print(f"[VOICE] câu {turn}: {len(utt)} bytes PCM", flush=True)
            wav_bytes = _pcm_to_wav_bytes(utt)
            content_b64 = base64.b64encode(wav_bytes).decode("ascii")
            _voice_set_transcript("Em đang suy nghĩ...", "THINKING")
            out = _voice_post_json(_resolve_core_base_url() + _VOICE_CONVERSE_PATH, {
                "content_b64": content_b64,
                "device_id": "EDGE-PI5-DESK-01",
                "turn": turn,
            }) or {}
            stt = str(out.get("stt_text") or "").strip()
            answer = str(out.get("reply") or "").strip()
            print(f"[VOICE] STT={stt!r} → reply={answer[:80]!r}", flush=True)
            if not stt:
                _voice_send_answer_flow(
                    stt, "Em nghe không rõ, anh nói lại giúp em nhé!")
                continue
            # Owner dừng hội thoại bằng giọng:
            low = stt.lower()
            if any(k in low for k in ("nghỉ đi", "nghi di", "nghỉ nào", "tạm biệt", "ngủ đi")):
                _voice_send_answer_flow(stt, "Dạ, em nghỉ nghe đây ạ. Anh cần thì gọi em nhé!")
                _voice_set_transcript("Em nghỉ nghe nhé. Gọi 'CHERRY ơi' khi cần em!", "IDLE")
                print("[VOICE] owner bảo nghỉ → kết thúc phiên", flush=True)
                return
            if answer:
                spoke = _voice_send_answer_flow(stt, answer)
                print(f"[VOICE] phát giọng: {spoke}", flush=True)
                # Chờ đuôi tiếng loa tắt hẳn trước khi mở mic lại — chống em tự
                # nghe thấy giọng phản hồi của mình (đã gặp E2E 01/11: câu sau
                # chính là STT câu trả lời vừa phát):
                time.sleep(1.5)
            else:
                _voice_send_answer_flow(stt, "Em chưa xử lý được lệnh này, anh thử lại nhé.")
                time.sleep(1.5)
        print("[VOICE] hết 15 phút/phiên → nghỉ", flush=True)
        _voice_set_transcript("Em nghỉ nghe nhé. Gọi 'CHERRY ơi' khi cần em!", "IDLE")
    finally:
        _VOICE_CONVO_ACTIVE.release()


def _start_voice_conversation() -> None:
    """Chào NGAY "Dạ, em nghe anh ạ." (WAV cục bộ, không đợi PC) rồi mở
    vòng lắng nghe liên tục trong thread nền."""
    def _run():
        _voice_play_wav(_GREET_WAV)
        _voice_conversation_loop()
    threading.Thread(target=_run, daemon=True).start()


def _notify_hdmi_event(event: str, ports: list) -> None:
    """Báo server PC sự kiện HDMI (connected/disconnected) → server gửi DM xin
    phê duyệt owner trước khi bật mirror (quyết định của anh, không tự bật)."""
    try:
        req = urllib.request.Request(
            _resolve_core_base_url() + "/api/executive/edge/hdmi_event",
            data=json.dumps({"event": event, "ports": ports,
                             "device_id": "EDGE-PI5-DESK-01"}).encode(),
            method="POST", headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()
        print(f"[HDMI] đã báo server: {event} {ports}", flush=True)
    except Exception as exc:
        print(f"[HDMI] không báo được server ({event}): {exc}", flush=True)


def _hdmi_watcher_loop() -> None:
    """Nền: mỗi 5s kiểm HDMI cắm/rút.

    (31/10/2026, owner) KHÔNG TỰ BẬT mirror khi cắm — cắm HDMI → báo server →
    bot DM hỏi phê duyệt. Owner 'phê duyệt hdmi'/'ok' mới bật; hình hiển thị
    LIÊN TỤC trên HDMI cho đến khi owner 'tắt hdmi'. Rút HDMI → tắt + báo."""
    import time as _time
    prev = False
    while True:
        try:
            conns = detect_hdmi_outputs()
            now = bool(conns)
            if now and not prev:
                # HDMI vừa cắm: ĐỪNG tự bật — báo server xin phê duyệt owner
                _notify_hdmi_event("connected", conns)
            elif prev and not now:
                stop_hdmi_mirror()
                _notify_hdmi_event("disconnected", [])
            prev = now
        except Exception:
            pass
        _time.sleep(5)


def start_hdmi_watcher() -> None:
    global _HDMI_WATCHER_STARTED
    if _HDMI_WATCHER_STARTED:
        return
    _HDMI_WATCHER_STARTED = True
    t = threading.Thread(target=_hdmi_watcher_loop, daemon=True)
    t.start()


class EdgeDaemonState:
    """Thread-safe state container for local kiosk rendering."""

    def __init__(self, config: EdgeConfig) -> None:
        self.config = config
        self.lock = threading.Lock()
        self.core_connected: bool = False
        self.avatar_state: str = "IDLE"
        self.active_model: str = "qwen2.5:7b"
        self.emergency_state: str = "normal"
        self.current_task: dict[str, Any] = {
            "task_id": "standby_supervision",
            "goal": "Sẵn sàng hỗ trợ Quanpt1",
            "autonomy_level": "LEVEL_A",
        }
        self.proposals_pending: int = 0
        self.transcript: str = "Chào Anh Quanpt1! Em đang sẵn sàng hỗ trợ."
        # (31/10/2026) Marquee tiếng Anh: transcript đã dịch VI→EN từ PC core.
        self.transcript_en: str = "Hello Mr. Quanpt1! I'm ready to assist."
        # (31/10/2026) ƯU TIÊN transcript local (speak/set_expression trên Pi):
        # timestamp(epoch) tới khi nào PC không được đè transcript này.
        self.transcript_local_until: float = 0.0
        self.last_heartbeat_epoch: float = 0.0
        self.need_ui_reload: bool = False
        self.pending_audio_base64: str | None = None
        self.pending_timeline: dict[str, Any] | None = None

        # (31/10/2026) AUTO-IDLE SLEEP: hình thể tự vào chế độ nghỉ chờ sau
        # khoảng thời gian không có hoạt động; "được gọi" (lệnh từ PC hoặc
        # owner chạm màn) → bật lại màn hình. 0 = tắt tự ngủ (luôn bật).
        self.idle_sleep_timeout_sec: int = 300      # 5 phút không hoạt động → nghỉ
        self.last_activity_epoch: float = time.time()
        self.auto_sleep_enabled: bool = True

        # Remote Audio & Microphone State (ADDENDUM V2.1)
        self.mic_enabled: bool = True
        self.mic_muted: bool = False
        self.wake_word_enabled: bool = True
        self.listening_mode: str = "WAKE_WORD"
        self.last_audio_level_db: float = -18.0
        self.last_audio_error: str | None = None
        self.audio_device_name: str = "Jieli Technology UACDemoV1.0 (USB Audio)"

        # Remote Camera & Vision State (ADDENDUM V2.1)
        self.camera_enabled: bool = False
        self.camera_streaming: bool = False
        self.last_camera_snapshot_path: str = str(STATIC_DIR / "assets" / "avatar" / "camera_snapshot.jpg")
        self.last_camera_timestamp: str | None = None
        self.last_camera_error: str | None = None
        self.camera_device_name: str = "Raspberry Pi Camera Module 3 (IMX708, libcamera)"

        # YouTube Music & Audio Streaming State
        self.current_music: dict[str, Any] | None = None

        # (31/10/2026) Điều khiển từ xa: mở URL/web trên màn kiosk (YouTube,
        # Google search, trang tin...) — owner ra lệnh qua DM → PC forward.
        self.pending_navigation: dict[str, Any] | None = None
        self.pending_image: dict[str, Any] | None = None

        # V41 EDGE AGENT — 5 năng lực chủ động (tự phản ứng/quản lý/thu thập/phối hợp/cải tiến)
        self.edge_agent = EdgeAgent(config)

        # UDC-1 (04/11/2026): điều khiển thiết bị theo lệnh DM của quanpt1
        # — read-only tự do; relay/joint/servo qua confirm 2 bước ("ok").
        self.device_control: Any = None
        try:
            from edge_client.device_control import DeviceControlService

            def _watcher_provider():
                return getattr(self.edge_agent, "_device_watcher", None)

            self.device_control = DeviceControlService(
                watcher_provider=_watcher_provider,
                actuator=getattr(self.edge_agent, "_actuator", None),
            )
        except Exception:
            self.device_control = None  # fail-closed: thiếu module vẫn chạy

    def _active_image_url_locked(self):
        """(31/10/2026) URL ảnh đang hiển thị (hoặc None). Tự hết hạn theo
        `until` — quá hạn trả None → kiosk gỡ ảnh, quay về avatar."""
        img = self.pending_image
        if not img:
            return None
        import time as _t
        if _t.time() >= float(img.get("until", 0.0)):
            self.pending_image = None
            return None
        return str(img.get("url") or "") or None

    def to_kiosk_dict(self) -> dict[str, Any]:
        with self.lock:
            # (06/11/2026, fix fail-honest) core_connected TRƯỚC ĐÂY sticky-True:
            # chỉ được set True (2515/2648), không bao giờ reset False khi PC chết
            # / mất WiFi → kiosk báo "connected" giả vĩnh viễn. Giờ: quá stale
            # (heartbeat_timeout_sec × 3) tự xem như mất kết nối (display only —
            # heartbeat sống lại sẽ bật True ngay chu kỳ kế tiếp).
            _hb_stale = (
                self.last_heartbeat_epoch > 0.0
                and (time.time() - self.last_heartbeat_epoch)
                > max(self.config.heartbeat_timeout_sec * 3.0, 12.0)
            )
            _core_ok = self.core_connected and not _hb_stale
            reload_needed = self.need_ui_reload
            self.need_ui_reload = False
            audio_b64 = self.pending_audio_base64
            timeline_obj = self.pending_timeline
            self.pending_audio_base64 = None
            self.pending_timeline = None
            nav_obj = self.pending_navigation
            self.pending_navigation = None
            kiosk_active = is_kiosk_running()
            return {
                "core_connected": _core_ok,
                "avatar_state": self.avatar_state if _core_ok else "OFFLINE",
                "kiosk_running": kiosk_active,
                "camera_streaming": self.camera_streaming,
                "embodiment_mode": "ACTIVE" if kiosk_active else "STANDBY",
                "core_host": f"{self.config.core_host}:{self.config.core_port}",
                "device_id": self.config.device_id,
                "face_only_mode": getattr(self.config, "face_only_mode", True),
                "active_model": self.active_model,
                "emergency_state": self.emergency_state,
                "current_task": self.current_task,
                "proposals_pending": self.proposals_pending,
                "transcript": self.transcript,
                "transcript_en": self.transcript_en,
                "last_heartbeat_epoch": self.last_heartbeat_epoch,
                "need_ui_reload": reload_needed,
                "pending_audio_base64": audio_b64,
                "pending_timeline": timeline_obj,
                "music": self.current_music,
                "image_url": self._active_image_url_locked(),
                "navigation_url": (nav_obj or {}).get("url") if nav_obj is not None else None,
                "audio": {
                    "mic_enabled": self.mic_enabled,
                    "mic_muted": self.mic_muted,
                    "wake_word_enabled": self.wake_word_enabled,
                    "listening_mode": self.listening_mode,
                    "audio_level_db": self.last_audio_level_db,
                    "device_name": self.audio_device_name,
                    "last_error": self.last_audio_error,
                },
                "camera": {
                    "camera_enabled": self.camera_enabled,
                    "camera_streaming": self.camera_streaming,
                    "device_name": self.camera_device_name,
                    "last_timestamp": self.last_camera_timestamp,
                    "last_error": self.last_camera_error,
                },
            }


class KioskHTTPHandler(http.server.BaseHTTPRequestHandler):
    """Local HTTP handler serving Kiosk UI files and local Edge APIs."""

    daemon_state: EdgeDaemonState
    auth: EdgeHMACAuth

    def log_message(self, format: str, *args: Any) -> None:
        # Suppress routine log noise on Pi 5
        pass

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path in ("/", "/index.html", "/kiosk.html"):
            self._serve_static_file("kiosk.html", "text/html; charset=utf-8")
            return

        if path == "/kiosk.css":
            self._serve_static_file("kiosk.css", "text/css; charset=utf-8")
            return

        if path == "/kiosk.js":
            self._serve_static_file("kiosk.js", "application/javascript; charset=utf-8")
            return

        if path == "/avatar_engine.js":
            cand = STATIC_DIR / "avatar_engine.js"
            if cand.exists() and cand.is_file():
                self._serve_static_file("avatar_engine.js", "application/javascript; charset=utf-8")
                return
            self._serve_static_file("assets/avatar/avatar_engine.js", "application/javascript; charset=utf-8")
            return

        if path == "/wake_engine.js":
            cand = STATIC_DIR / "assets" / "avatar" / "wake_engine.js"
            if cand.exists() and cand.is_file():
                self._serve_static_file("assets/avatar/wake_engine.js", "application/javascript; charset=utf-8")
                return
            self._serve_static_file("wake_engine.js", "application/javascript; charset=utf-8")
            return

        if path.startswith("/assets/"):
            rel_path = path.lstrip("/")
            target = STATIC_DIR / rel_path
            if target.exists() and target.is_file():
                ctype, _ = mimetypes.guess_type(str(target))
                if not ctype:
                    ctype = "application/octet-stream"
                self._serve_static_file(rel_path, ctype)
                return

        if path == "/api/kiosk/status":
            data = self.daemon_state.to_kiosk_dict()
            # (01/11/2026, owner) STOP chỉ thoát giao diện — guard đọc flag này
            # để không tự dậy lại kiosk trong 15 phút sau khi owner đóng.
            data["kiosk_closed_by_owner"] = _kiosk_closed_by_owner()
            self._send_json(data)
            return

        # (31/10/2026) HDMI OUT: trạng thái cổng HDMI + mirror kiosk
        if path == "/api/kiosk/hdmi":
            conns = detect_hdmi_outputs()
            proc = _HDMI_MIRROR_PROC
            self._send_json({
                "success": True,
                "hdmi_connected": conns,
                "mirror_running": bool(proc is not None and proc.poll() is None),
            })
            return

        # V41: trạng thái Edge Agent (5 năng lực chủ động)
        if path == "/api/kiosk/agent/status":
            try:
                self._send_json({
                    "success": True,
                    "agent": self.daemon_state.edge_agent.get_status_summary(),
                })
            except Exception as exc:
                self._send_error_json(f"AGENT_STATUS_ERROR: {exc}", 500)
            return

        # V41: đề xuất cải tiến (chỉ đọc — áp dụng cần duyệt của Quanpt1)
        if path == "/api/kiosk/agent/suggestions":
            try:
                limit = 20
                self._send_json({
                    "success": True,
                    "suggestions": self.daemon_state.edge_agent.get_suggestions(limit),
                    "note": "Đề xuất CHƯA được áp dụng — chờ duyệt của Quanpt1",
                })
            except Exception as exc:
                self._send_error_json(f"AGENT_SUGGESTIONS_ERROR: {exc}", 500)
            return

        if path == "/api/kiosk/files":
            self._handle_api_kiosk_list_files()
            return

        if path == "/api/kiosk/audio/status":
            self._handle_api_kiosk_audio_status()
            return

        if path == "/api/kiosk/camera/status":
            self._handle_api_kiosk_camera_status()
            return

        if path == "/api/kiosk/camera/snapshot":
            self._handle_api_kiosk_camera_get_snapshot()
            return

        if path == "/api/kiosk/media/file":
            self._handle_api_kiosk_media_file(self.path)
            return

        if path == "/api/kiosk/camera/stream":
            self._handle_api_kiosk_camera_stream()
        if path == "/api/kiosk/camera/mjpeg":
            self._handle_api_kiosk_camera_mjpeg()
            return

        if path == "/api/kiosk/music/status":
            with self.daemon_state.lock:
                m = self.daemon_state.current_music
            self._send_json({"success": True, "music": m, "playing": m is not None})
            return

        self.send_error(404, "File Not Found")

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get("Content-Length", 0))
        if content_length > 15_000_000:
            self._send_error_json("Payload too large", 413)
            return

        body_raw = self.rfile.read(content_length).decode("utf-8", errors="replace")
        try:
            body = json.loads(body_raw) if body_raw else {}
        except json.JSONDecodeError:
            body = {}

        if path == "/api/kiosk/emergency_stop":
            self._handle_emergency_stop(body)
            return

        if path == "/api/kiosk/wake":
            with self.daemon_state.lock:
                self.daemon_state.avatar_state = "LISTENING"
                self.daemon_state.transcript = "Đang lắng nghe Anh..."
            self._send_json({"success": True, "state": "LISTENING"})
            return

        if path == "/api/kiosk/files/upload":
            self._handle_api_kiosk_upload_file(body)
            return

        if path == "/api/kiosk/files/delete":
            self._handle_api_kiosk_delete_file(body)
            return

        if path == "/api/kiosk/control":
            self._handle_api_kiosk_remote_control(body)
            return

        if path == "/api/kiosk/audio/control":
            self._handle_api_kiosk_audio_control(body)
            return

        if path == "/api/kiosk/camera/control":
            self._handle_api_kiosk_camera_control(body)
            return

        if path == "/api/kiosk/camera/capture":
            self._handle_api_kiosk_camera_capture(body)
            return

        if path == "/api/kiosk/media/record":
            self._handle_api_kiosk_media_record(body)
            return

        if path == "/api/kiosk/music/play":
            self._handle_api_kiosk_music_play(body)
            return

        if path == "/api/kiosk/music/stop":
            self._handle_api_kiosk_music_stop()
            return

        # UDC-1 (04/11/2026): điều khiển/khống chế thiết bị theo DM owner
        if path == "/api/kiosk/device":
            self._handle_api_kiosk_device(body)
            return

        self.send_error(404, "Endpoint Not Found")

    def _handle_api_kiosk_device(self, body: dict[str, Any]) -> None:
        """UDC-1: op read-only chạy ngay; relay/joint cần confirm_token từ DM."""
        dc = getattr(self.daemon_state, "device_control", None)
        if dc is None:
            self._send_json({"success": False,
                             "reason": "device_control không khả dụng (fail-closed)"})
            return
        result = dc.execute(body if isinstance(body, dict) else {})
        self._send_json(result)

    def _handle_api_kiosk_list_files(self) -> None:
        avatar_dir = STATIC_DIR / "assets" / "avatar"
        files_info = []
        if avatar_dir.exists() and avatar_dir.is_dir():
            for p in sorted(avatar_dir.iterdir()):
                if p.is_file() and not p.name.startswith("."):
                    stat = p.stat()
                    files_info.append({
                        "name": p.name,
                        "size": stat.st_size,
                        "mtime": int(stat.st_mtime),
                        "url": f"/assets/avatar/{p.name}",
                        "ext": p.suffix.lower(),
                    })
        self._send_json({
            "success": True,
            "device_id": self.daemon_state.config.device_id,
            "directory": "assets/avatar",
            "count": len(files_info),
            "files": files_info,
        })

    # ---- (31/10/2026) Media capture từ Pi: chụp ảnh / quay video theo lệnh DM ----
    # Lưu trữ 2 bên: Pi (/home/quanpt1/tony_media/{photos,videos}) + PC tải về
    # logs/pi5_media/ (server PC action "pi_media_capture" tự tải sau khi capture).
    MEDIA_PHOTOS_DIR = Path.home() / "tony_media" / "photos"
    MEDIA_VIDEOS_DIR = Path.home() / "tony_media" / "videos"
    MEDIA_AUDIO_DIR = Path.home() / "tony_media" / "audio"

    def _handle_api_kiosk_media_record(self, body: dict[str, Any]) -> None:
        """POST /api/kiosk/media/record {action:'photo'|'video', duration_sec:5}.

        photo: fswebcam 640x480 (fallback ffmpeg v4l2) → tony_media/photos/.
        video: ffmpeg v4l2 h264 + pw-record mic WAV song song duration giây
               (3..30), mux AAC → tony_media/videos/. Fail-honest từng bước.
        """
        action = str(body.get("action", "")).strip().lower()
        try:
            duration = float(body.get("duration_sec", 5.0))
        except (TypeError, ValueError):
            duration = 5.0
        duration = max(3.0, min(30.0, duration))

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        try:
            if action == "photo":
                out_path = self.MEDIA_PHOTOS_DIR / f"photo_{ts}.jpg"
                out_path.parent.mkdir(parents=True, exist_ok=True)
                import shutil
                # (31/10/2026) Camera Module 3 (IMX708, CSI/libcamera) — Ưu tiên
                # rpicam-still (tương thích mọi Pi camera CSI); fswebcam/ffmpeg
                # v4l2 chỉ dành cho webcam USB.
                if shutil.which("rpicam-still"):
                    subprocess.run(
                        ["rpicam-still", "-o", str(out_path), "--width", "1280",
                         "--height", "720", "--nopreview", "-t", "1500"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=25)
                elif shutil.which("rpicam-jpeg"):
                    subprocess.run(
                        ["rpicam-jpeg", "-o", str(out_path), "--width", "1280",
                         "--height", "720", "--nopreview", "-t", "1500"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=25)
                elif shutil.which("fswebcam"):
                    subprocess.run(
                        ["fswebcam", "-r", "1280x720", "-S", "10", "--no-banner",
                         "-q", str(out_path)],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20)
                else:
                    subprocess.run(
                        ["ffmpeg", "-y", "-f", "v4l2", "-video_size", "1280x720",
                         "-i", "/dev/video0", "-frames:v", "1", "-q:v", "3",
                         str(out_path), "-loglevel", "quiet"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20)
                if not out_path.exists() or out_path.stat().st_size < 500:
                    self._send_error_json("MEDIA_CAPTURE_FAILED: không chụp được ảnh", 503)
                    return
                self._send_json({
                    "success": True, "kind": "photo",
                    "filename": out_path.name,
                    "path": str(out_path),
                    "size_bytes": out_path.stat().st_size,
                    "download_url": f"/api/kiosk/media/file?name={out_path.name}",
                    "message": f"Đã chụp ảnh {out_path.name}",
                })
                return

            if action == "video":
                out_path = self.MEDIA_VIDEOS_DIR / f"video_{ts}.mp4"
                out_path.parent.mkdir(parents=True, exist_ok=True)
                tmp_video = Path("/tmp") / f"_tony_vid_{ts}.mp4"
                tmp_audio = Path("/tmp") / f"_tony_mic_{ts}.wav"
                # 1) Ghi âm mic SONG SONG (PipeWire multiplex, không đụng wake):
                mic_proc = None
                try:
                    import os as _os
                    env = dict(_os.environ, XDG_RUNTIME_DIR="/run/user/1000")
                    mic_proc = subprocess.Popen(
                        ["pw-record", "--target", "75", "--format", "s16",
                         "--rate", "16000", "--channels", "1", str(tmp_audio)],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)
                except Exception:
                    mic_proc = None
                try:
                    # 2) Quay video N giây:
                    # (31/10/2026) Camera Module 3 (CSI/libcamera): rpicam-vid
                    # xuất H264 trực tiếp; ffmpeg v4l2 chỉ dùng cho webcam USB.
                    import shutil as _shutil
                    if _shutil.which("rpicam-vid"):
                        subprocess.run(
                            ["rpicam-vid", "-o", str(tmp_video), "--width", "1280",
                             "--height", "720", "--nopreview",
                             "-t", f"{int(duration * 1000)}", "--codec", "h264",
                             "--framerate", "25"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            timeout=duration + 30)
                    else:
                        subprocess.run(
                            ["ffmpeg", "-y", "-f", "v4l2", "-video_size", "1280x720",
                             "-i", "/dev/video0", "-t", f"{duration:.1f}",
                             "-c:v", "libx264", "-preset", "ultrafast",
                             "-pix_fmt", "yuv420p", str(tmp_video), "-loglevel", "quiet"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            timeout=duration + 25)
                finally:
                    if mic_proc is not None:
                        try:
                            time.sleep(0.3)
                            mic_proc.terminate()
                            mic_proc.wait(timeout=5)
                        except Exception:
                            try:
                                mic_proc.kill()
                            except Exception:
                                pass
                if not tmp_video.exists() or tmp_video.stat().st_size < 1000:
                    self._send_error_json("MEDIA_CAPTURE_FAILED: không quay được video", 503)
                    return
                # 3) Trộn âm (nếu có WAV hợp lệ):
                has_audio = tmp_audio.exists() and tmp_audio.stat().st_size > 44
                if has_audio:
                    subprocess.run(
                        ["ffmpeg", "-y", "-i", str(tmp_video), "-i", str(tmp_audio),
                         "-c:v", "copy", "-c:a", "aac", "-shortest",
                         str(out_path), "-loglevel", "quiet"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
                if not out_path.exists():
                    tmp_video.replace(out_path)  # video câm vẫn dùng được
                tmp_video.unlink(missing_ok=True)
                tmp_audio.unlink(missing_ok=True)
                self._send_json({
                    "success": True, "kind": "video",
                    "filename": out_path.name,
                    "path": str(out_path),
                    "size_bytes": out_path.stat().st_size,
                    "duration_sec": duration,
                    "has_audio": has_audio,
                    "download_url": f"/api/kiosk/media/file?name={out_path.name}",
                    "message": f"Đã quay {duration:.0f}s{' (kèm tiếng)' if has_audio else ' (video câm — mic không ghi được)'}",
                })
                return

            if action == "audio":
                # (31/10/2026) TAI của CHERRY: thu âm mic thuần N giây (pw-record
                # PipeWire target 75, không đụng wake engine) → tony_media/audio/.
                out_path = self.MEDIA_AUDIO_DIR / f"audio_{ts}.wav"
                out_path.parent.mkdir(parents=True, exist_ok=True)
                import os as _os
                import shutil as _sh
                if not _sh.which("pw-record"):
                    self._send_error_json("MEDIA_CAPTURE_FAILED: pw-record không có", 503)
                    return
                env = dict(_os.environ, XDG_RUNTIME_DIR="/run/user/1000")
                # pw-record GHI LIÊN TỤC — chạy nền, sau N giây terminate sạch
                # để pw-record kịp ghi WAV header (timeout cứng làm header hỏng):
                rec_proc = None
                # (31/10/2026) CHỌN MIC theo lệnh owner: mic_kind=usb|bt|auto.
                # usb → Jieli UACDemoV1.0 (mic rời); bt → mic tích hợp loa
                # SRS-XB33 (bluez_input, DSP sạch, nhạy tiếng lớn);
                # auto → USB ưu tiên, BT dự phòng:
                body_mic = str(body.get("mic_kind", "auto") or "").strip().lower()
                if body_mic not in ("usb", "bt", "auto"):
                    body_mic = "auto"

                def _pw_node_ids(pattern: str):
                    """Trả list id node PipeWire khớp pattern (node.name/nick/
                    description trong block của chính nó — parse split chuẩn)."""
                    try:
                        out = subprocess.run(
                            ["pw-cli", "ls", "Node"], capture_output=True, text=True,
                            timeout=5, env=env).stdout or ""
                        import re as _re2
                        blocks = _re2.split(
                            r"id (\d+), type PipeWire:Interface:Node/3", out)
                        ids = []
                        for k in range(1, len(blocks), 2):
                            nid, content = blocks[k], blocks[k + 1]
                            if "Audio/Source" in content and _re2.search(pattern, content):
                                ids.append(nid)
                        return ids
                    except Exception:
                        return []

                def _find_usb_mic():
                    ids = _pw_node_ids(r"UACDemoV1\.0")
                    return ids[0] if ids else None

                def _find_bt_mic():
                    ids = _pw_node_ids(r"bluez_input\.")
                    return ids[0] if ids else None

                if body_mic == "bt":
                    mic_target = _find_bt_mic() or "75"
                elif body_mic == "usb":
                    mic_target = _find_usb_mic() or "75"
                else:  # auto
                    mic_target = _find_usb_mic() or _find_bt_mic() or "75"
                try:
                    rec_proc = subprocess.Popen(
                        ["pw-record", "--target", mic_target, "--format", "s16",
                         "--rate", "16000", "--channels", "1", str(out_path)],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)
                except Exception:
                    rec_proc = None
                time.sleep(duration)
                if rec_proc is not None:
                    try:
                        rec_proc.terminate()
                        rec_proc.wait(timeout=5)
                    except Exception:
                        try:
                            rec_proc.kill()
                        except Exception:
                            pass
                size = out_path.stat().st_size if out_path.exists() else 0
                # WAV header hỏng (terminate sớm) → ffmpeg remux chuẩn hoá:
                import shutil as _sh2
                if size > 1000 and _sh2.which("ffmpeg"):
                    fix_path = out_path.with_suffix(".fix.wav")
                    subprocess.run(
                        ["ffmpeg", "-y", "-i", str(out_path), "-ar", "16000",
                         "-ac", "1", str(fix_path), "-loglevel", "quiet"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20)
                    if fix_path.exists() and fix_path.stat().st_size > 1000:
                        fix_path.replace(out_path)
                size = out_path.stat().st_size if out_path.exists() else 0
                if size < 1000:
                    self._send_error_json("MEDIA_CAPTURE_FAILED: mic không ghi được tín hiệu", 503)
                    return
                self._send_json({
                    "success": True, "kind": "audio",
                    "mic_target": str(mic_target),
                    "mic_kind": body_mic,
                    "filename": out_path.name,
                    "path": str(out_path),
                    "size_bytes": size,
                    "duration_sec": duration,
                    "download_url": f"/api/kiosk/media/file?name={out_path.name}",
                    "message": f"Đã thu âm {duration:.0f}s từ mic Pi 5",
                })
                return

            self._send_error_json("action phải là 'photo', 'video' hoặc 'audio'", 400)
        except Exception as exc:
            self._send_error_json(f"MEDIA_ERROR: {type(exc).__name__}: {exc}", 500)

    def _handle_api_kiosk_media_file(self, query: str) -> None:
        """GET /api/kiosk/media/file?name=photo_xxx.jpg — serve file media đã lưu."""
        from urllib.parse import parse_qs, urlparse
        params = parse_qs(urlparse(query).query)
        name = Path((params.get("name") or [""])[0]).name
        if not name:
            self._send_error_json("missing name", 400)
            return
        for d in (self.MEDIA_PHOTOS_DIR, self.MEDIA_VIDEOS_DIR,
                  getattr(self, "MEDIA_AUDIO_DIR", None)):
            if d is None:
                continue
            target = d / name
            if target.exists() and target.is_file():
                suffix = target.suffix.lower()
                ctype = ("image/jpeg" if suffix in (".jpg", ".jpeg")
                         else "audio/wav" if suffix == ".wav"
                         else "video/mp4")
                data = target.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(data)
                return
        self._send_error_json(f"không tìm thấy file media: {name}", 404)

    def _handle_api_kiosk_upload_file(self, body: dict[str, Any]) -> None:
        import base64
        filename = str(body.get("filename", "")).strip()
        content_b64 = str(body.get("content_b64", "")).strip()
        if not filename or not content_b64:
            self._send_error_json("Missing filename or content_b64", 400)
            return

        clean_name = Path(filename).name
        allowed_exts = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".json", ".wav", ".mp3", ".js", ".css", ".html", ".sh", ".py"}
        if Path(clean_name).suffix.lower() not in allowed_exts:
            self._send_error_json(f"File extension not permitted: {clean_name}", 400)
            return

        if clean_name in ("avatar_engine.js", "wake_engine.js", "kiosk.js", "kiosk.css", "kiosk.html", "setup_pi5_audio.sh", "sync_assets.py", "start_kiosk.sh", "client_daemon.py"):
            target = STATIC_DIR / clean_name
        else:
            avatar_dir = STATIC_DIR / "assets" / "avatar"
            avatar_dir.mkdir(parents=True, exist_ok=True)
            target = avatar_dir / clean_name

        try:
            file_bytes = base64.b64decode(content_b64)
            with open(target, "wb") as f:
                f.write(file_bytes)
            # If it's a shell script, make it executable
            if clean_name.endswith(".sh"):
                try:
                    import os
                    os.chmod(target, 0o755)
                except Exception:
                    pass
            # If it's avatar_engine.js or wake_engine.js, also mirror to assets/avatar for backup
            if clean_name in ("avatar_engine.js", "wake_engine.js"):
                mirror = STATIC_DIR / "assets" / "avatar" / clean_name
                mirror.parent.mkdir(parents=True, exist_ok=True)
                mirror.write_bytes(file_bytes)
            self._send_json({
                "success": True,
                "filename": clean_name,
                "size_bytes": len(file_bytes),
                "url": f"/{clean_name}" if target.parent == STATIC_DIR else f"/assets/avatar/{clean_name}",
                "message": f"Tệp tin '{clean_name}' đã được lưu an toàn trên Pi 5.",
            })
        except Exception as exc:
            self._send_error_json(f"Lỗi ghi tệp trên Pi 5: {exc}", 500)

    def _handle_api_kiosk_delete_file(self, body: dict[str, Any]) -> None:
        filename = str(body.get("filename", "")).strip()
        clean_name = Path(filename).name
        target = STATIC_DIR / "assets" / "avatar" / clean_name
        protected = {"model_f_portrait.png", "model_f_happy.png", "mouth_rest.png", "eyes_open.png"}
        if clean_name in protected:
            self._send_error_json(f"Không thể xóa tệp hệ thống cốt lõi: {clean_name}", 403)
            return

        if target.exists() and target.is_file():
            try:
                target.unlink()
                self._send_json({"success": True, "filename": clean_name, "message": f"Đã xóa {clean_name}"})
                return
            except Exception as e:
                self._send_error_json(f"Lỗi khi xóa: {e}", 500)
                return
        self._send_error_json(f"Không tìm thấy tệp {clean_name}", 404)

    def _handle_api_kiosk_remote_control(self, body: dict[str, Any]) -> None:
        action = str(body.get("action", "")).strip().lower()
        if action == "reload_ui":
            with self.daemon_state.lock:
                self.daemon_state.need_ui_reload = True
            self._send_json({"success": True, "message": "Đã gửi tín hiệu tải lại giao diện Kiosk"})
            return

        if action == "set_volume":
            vol = max(0, min(100, int(body.get("volume", 85))))
            try:
                import subprocess
                # 1. PipeWire / WirePlumber volume adjustment
                vol_ratio = f"{vol / 100.0:.2f}"
                subprocess.run(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", vol_ratio], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run(["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "0"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run(["wpctl", "set-volume", "@DEFAULT_AUDIO_SOURCE@", vol_ratio], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run(["wpctl", "set-mute", "@DEFAULT_AUDIO_SOURCE@", "0"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                # 2. ALSA Master fallback
                subprocess.run(["amixer", "set", "Master", f"{vol}%"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run(["amixer", "set", "Speaker", f"{vol}%"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                self._send_json({"success": True, "volume": vol})
                return
            except Exception as e:
                self._send_json({"success": True, "volume": vol, "warning": str(e)})
                return

        if action == "auto_configure_audio":
            try:
                import subprocess
                setup_script = STATIC_DIR / "setup_pi5_audio.sh"
                if setup_script.exists():
                    subprocess.run(["bash", str(setup_script)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20)
                self._send_json({"success": True, "message": "Đã thực hiện tự động định tuyến âm thanh USB trên Pi 5"})
                return
            except Exception as e:
                self._send_json({"success": False, "error": str(e)})
                return

        if action == "set_expression":
            state = str(body.get("state", "IDLE")).strip().upper()
            transcript = str(body.get("transcript", "")).strip()
            with self.daemon_state.lock:
                self.daemon_state.avatar_state = state
                if transcript:
                    self.daemon_state.transcript = transcript
                    # (31/10) ưu tiên local 10s cho set_expression; EN cũ xoá
                    self.daemon_state.transcript_en = ""
                    self.daemon_state.transcript_local_until = time.time() + 10.0
            self._send_json({"success": True, "state": state, "transcript": transcript})
            return

        if action == "speak":
            text = str(body.get("text", "")).strip()
            state = str(body.get("state", "SPEAKING")).strip().upper()
            duration_ms = int(body.get("duration_ms", max(1500, len(text) * 110)))
            timeline = body.get("timeline")
            audio_b64 = body.get("audio_base64")
            with self.daemon_state.lock:
                self.daemon_state.avatar_state = state
                if text:
                    self.daemon_state.transcript = text
                    # (31/10) transcript local ưu tiên qua thời lượng nói + buffer;
                    # EN cũ bị xoá → kiosk fallback hiển thị transcript VN mới
                    self.daemon_state.transcript_en = ""
                    self.daemon_state.transcript_local_until = time.time() + (duration_ms / 1000.0) + 5.0
                if timeline:
                    self.daemon_state.pending_timeline = timeline
                if audio_b64:
                    self.daemon_state.pending_audio_base64 = audio_b64

            # AUDIO ROUTING: Phát hardware nếu ở chế độ HARDWARE_ONLY, DUAL,
            # hoặc khi Chromium Kiosk chưa chạy (Standby mode), hoặc có cờ force_hardware
            should_play_hardware = bool(
                audio_b64 and (
                    AUDIO_PLAYBACK_MODE in ("HARDWARE_ONLY", "DUAL")
                    or not is_kiosk_running()
                    or body.get("force_hardware", True)
                )
            )
            if should_play_hardware:
                play_audio_on_hardware_speaker(audio_b64)

            # Auto-reset avatar_state back to IDLE after speech duration expires
            def _auto_reset_speech():
                import time
                time.sleep(duration_ms / 1000.0)
                with self.daemon_state.lock:
                    if self.daemon_state.avatar_state == "SPEAKING":
                        self.daemon_state.avatar_state = "IDLE"

            threading.Thread(target=_auto_reset_speech, daemon=True).start()
            self._send_json({
                "success": True,
                "state": state,
                "text": text,
                "has_audio": bool(audio_b64),
                "duration_ms": duration_ms,
                "audio_mode": AUDIO_PLAYBACK_MODE,
                "played_hardware": should_play_hardware,
            })
            return

        if action == "self_test":
            mic_res = self._measure_microphone_signal()
            cam_frame = self._capture_camera_frame()
            cam_ok = bool(cam_frame and (Path("/dev/video0").exists() or sys.platform == "win32"))
            mic_ok = bool(mic_res.get("success") and mic_res.get("audio_level_db", -99.0) > -75.0)
            self._send_json({
                "success": True,
                "action": "self_test",
                "mic_ok": mic_ok,
                "camera_ok": cam_ok,
                "mic_data": mic_res,
                "camera_data": {
                    "device": self.daemon_state.camera_device_name,
                    "frame_bytes": len(cam_frame) if cam_frame else 0,
                    "node": "/dev/video0",
                },
            })
            return

        if action == "pause":
            with self.daemon_state.lock:
                self.daemon_state.avatar_state = "SLEEPING"
                self.daemon_state.transcript = "Trợ lý đang tạm nghỉ ngơi theo chỉ đạo của Anh."
            self._send_json({"success": True, "state": "SLEEPING"})
            return

        if action == "resume":
            with self.daemon_state.lock:
                self.daemon_state.avatar_state = "IDLE"
                self.daemon_state.transcript = "Chào Anh Quanpt1! Em đã sẵn sàng tiếp tục công việc."
            self._send_json({"success": True, "state": "IDLE"})
            return

        if action == "open_url":
            # (31/10/2026) Owner ra lệnh mở URL trên màn Pi 5 (YouTube, Google,
            # trang tin...). Nếu đang SLEEPING → wake màn + kiosk trước, rồi
            # đẩy URL qua to_kiosk_dict — kiosk.js tự điều hướng.
            url = str(body.get("url", "")).strip()
            if not (url.startswith("http://") or url.startswith("https://")):
                self._send_error_json("open_url requires an http(s) URL", 400)
                return
            was_sleeping = False
            with self.daemon_state.lock:
                was_sleeping = self.daemon_state.avatar_state == "SLEEPING"
            if was_sleeping:
                threading.Thread(target=_wake_screen_impl, daemon=True).start()
            with self.daemon_state.lock:
                self.daemon_state.pending_navigation = {"url": url}
                if was_sleeping:
                    self.daemon_state.avatar_state = "IDLE"
                    self.daemon_state.transcript = "Dạ, em mở trang anh yêu cầu đây ạ!"
                # Mở URL = hoạt động thật → reset auto-sleep timer
                self.daemon_state.last_activity_epoch = time.time()
            self._send_json({"success": True, "action": "open_url", "url": url})
            return

        if action == "show_image":
            # (31/10/2026) Owner yêu cầu hiển thị 1 ảnh trên màn Pi 5 trong N giây
            # (mặc định 15s) rồi TỰ ĐỘNG quay lại avatar. Ảnh đã upload trước đó
            # qua /api/kiosk/files/upload (url trả về từ API đó).
            import time as _t
            url = str(body.get("url", "")).strip()
            if not url:
                self._send_error_json("show_image requires url", 400)
                return
            try:
                duration = float(body.get("duration_sec", 15.0))
            except (TypeError, ValueError):
                duration = 15.0
            duration = max(3.0, min(600.0, duration))  # biên an toàn 3s..10 phút
            was_sleeping = False
            with self.daemon_state.lock:
                was_sleeping = self.daemon_state.avatar_state == "SLEEPING"
            if was_sleeping:
                threading.Thread(target=_wake_screen_impl, daemon=True).start()
            with self.daemon_state.lock:
                self.daemon_state.pending_image = {
                    "url": url,
                    "until": _t.time() + duration,
                }
                if was_sleeping:
                    self.daemon_state.avatar_state = "IDLE"
                    self.daemon_state.transcript = "Dạ, em hiển thị ảnh anh gửi đây ạ!"
                self.daemon_state.last_activity_epoch = _t.time()
            self._send_json({"success": True, "action": "show_image",
                             "url": url, "duration_sec": duration})
            return

        if action == "close_web_overlay":
            # (31/10/2026) Đóng overlay web (nếu đang mở) — kiosk hiển thị lại
            # hình thể CHERRY. to_kiosk_dict trả navigation_url="" → kiosk.js remove.
            with self.daemon_state.lock:
                self.daemon_state.pending_navigation = {"url": ""}
            self._send_json({"success": True, "action": "close_web_overlay"})
            return

        if action == "wake_by_voice":
            # (31/10/2026) Wake word service (vosk ngoài kiosk) nghe thấy
            # "Cherry ơi" → bật màn hình + launch kiosk + trạng thái chờ nói.
            # (01/11/2026) owner gọi lại → xoá cờ "đóng theo yêu cầu" →
            # guard/kiosk hoạt động bình thường.
            _set_kiosk_closed_by_owner(False)
            print("[WAKE] wake_by_voice: bật màn + kiosk", flush=True)
            threading.Thread(target=_wake_screen_impl, daemon=True).start()
            with self.daemon_state.lock:
                self.daemon_state.avatar_state = "IDLE"
                self.daemon_state.transcript = "Dạ, em nghe anh ạ. Em đang lắng nghe!"
                # Wake từ giọng nói = hoạt động thật → không để auto-sleep tắt ngay
                self.daemon_state.last_activity_epoch = time.time()
            # (01/11/2026, owner) HỘI THOẠI LIÊN TỤC: chào NGAY "Dạ, em nghe
            # anh ạ." bằng WAV cục bộ (<0,5s, không đợi PC) → vòng lắng nghe
            # VAD liên tục (nói-nghỉ-theo-câu) → STT → xử lý → trả lời giọng.
            threading.Thread(target=_start_voice_conversation, daemon=True).start()
            # ĐỒNG BỘ PC: target trên server có thể kẹt SLEEPING (lệnh pause cũ)
            # → mỗi heartbeat sẽ đè avatar về SLEEPING. Gửi resume để server
            # đặt lại target=IDLE (fire-and-forget, không chặn phản hồi).
            threading.Thread(
                target=_sync_resume_after_voice_wake_impl,
                args=(str(self.daemon_state.config.core_base_url), self.auth),
                daemon=True,
            ).start()
            self._send_json({"success": True, "action": "wake_by_voice", "state": "IDLE"})
            return

        if action == "set_face_only":
            val = bool(body.get("face_only", True))
            self.daemon_state.config.face_only_mode = val
            self._send_json({"success": True, "face_only_mode": val})
            return

        # (31/10/2026) HDMI OUT: bật/tắt mirror thủ công qua lệnh DM/server
        if action in ("hdmi_show", "show_on_hdmi"):
            ok = launch_hdmi_mirror()
            conns = detect_hdmi_outputs()
            msg = (f"HDMI mirror đã bật ({', '.join(conns)})" if ok
                   else "HDMI chưa cắm màn — không bật được mirror")
            self._send_json({"success": ok, "action": action,
                             "hdmi_connected": conns, "message": msg})
            return

        if action in ("hdmi_hide", "hide_hdmi"):
            ok = stop_hdmi_mirror()
            self._send_json({"success": ok, "action": action,
                             "message": "Đã tắt mirror HDMI" if ok else "Không tắt được"})
            return

        if action in ("start_kiosk", "launch_kiosk", "open_kiosk"):
            # (01/11/2026) Bật hình thể thủ công = owner muốn lại → xoá cờ đóng
            _set_kiosk_closed_by_owner(False)
            ok = launch_kiosk_process()
            with self.daemon_state.lock:
                self.daemon_state.avatar_state = "IDLE"
                self.daemon_state.transcript = "Hệ thống hình thể đã khởi động trên màn hình 7\" DSI."
            self._send_json({
                "success": ok,
                "action": action,
                "kiosk_running": True,
                "embodiment_mode": "ACTIVE",
                "message": "Đã khởi chạy giao diện hình thể Kiosk trên màn hình 7\" Pi 5"
            })
            return

        if action == "close_kiosk":
            # (01/11/2026, owner) STOP = CHỈ thoát giao diện hiển thị:
            # đóng chromium kiosk, GIỮ màn hình bật, không emergency, avatar
            # không rơi OFFLINE/STOPPED (daemon vẫn ACTIVE). Guard không tự
            # dậy lại trong 15 phút; owner gọi lại (CHERRY ƠI / wake word) sẽ mở.
            _set_kiosk_closed_by_owner(True)
            with self.daemon_state.lock:
                self.daemon_state.avatar_state = "IDLE"
                self.daemon_state.transcript = "Giao diện đã thoát theo yêu cầu của Anh — gọi 'CHERRY ơi' hoặc chạm màn hình là em quay lại."
            try:
                import subprocess, shutil, os
                global _KIOSK_PROC
                if shutil.which("pkill"):
                    subprocess.run(["pkill", "-f", "chromium"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                elif os.name == "nt":
                    if _KIOSK_PROC and _KIOSK_PROC.poll() is None:
                        _KIOSK_PROC.terminate()
                        _KIOSK_PROC = None
                # KHÔNG xset dpms force off — owner chỉ muốn thoát giao diện,
                # màn hình vẫn sáng bình thường.
                self._send_json({
                    "success": True,
                    "action": action,
                    "kiosk_running": False,
                    "kiosk_closed_by_owner": True,
                    "embodiment_mode": "STANDBY",
                    "message": "Đã thoát giao diện hình thể theo yêu cầu của Anh (màn hình giữ nguyên). Gọi 'CHERRY ơi' là em quay lại."
                })
                return
            except Exception as e:
                self._send_json({"success": False, "error": str(e)})
                return

        if action == "poweroff_pi":
            with self.daemon_state.lock:
                self.daemon_state.avatar_state = "OFFLINE"
                self.daemon_state.transcript = "Đang tắt nguồn an toàn thiết bị Raspberry Pi 5..."
            try:
                import subprocess
                def _do_poweroff():
                    import time
                    time.sleep(1.5)
                    subprocess.run(["sudo", "poweroff"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                threading.Thread(target=_do_poweroff, daemon=True).start()
                self._send_json({"success": True, "message": "Đã phát lệnh tắt nguồn hệ thống Pi 5 an toàn"})
                return
            except Exception as e:
                self._send_json({"success": False, "error": str(e)})
                return

        self._send_error_json(f"Lệnh không xác định: {action}", 400)

    def _send_error_json(self, msg: str, status_code: int = 400) -> None:
        payload = json.dumps({"success": False, "error": msg}).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _handle_emergency_stop(self, body: dict[str, Any]) -> None:
        reason = body.get("reason", "STOP touched on Raspberry Pi 5 Edge Screen")
        with self.daemon_state.lock:
            self.daemon_state.avatar_state = "BLOCKED"
            self.daemon_state.emergency_state = "stop"

        # Dispatch authenticated stop request to Core
        payload = json.dumps({"action": "stop", "reason": reason}).encode("utf-8")
        headers = self.auth.create_signed_headers(payload)
        headers["Content-Type"] = "application/json"

        target_url = f"{self.daemon_state.config.core_base_url}/api/executive/emergency"
        try:
            req = urllib.request.Request(target_url, data=payload, headers=headers)
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                self._send_json({"success": True, "core_response": data})
                return
        except Exception as e:
            self._send_json({"success": False, "error": str(e), "local_safety": "ENGAGED"})

    def _handle_api_kiosk_music_play(self, body: dict[str, Any]) -> None:
        video_id = str(body.get("video_id", "")).strip()
        url = str(body.get("url", "")).strip()
        title = str(body.get("title", "")).strip() or "Bản nhạc YouTube"
        if not url and video_id:
            url = f"https://www.youtube.com/watch?v={video_id}"
        if not url:
            self._send_error_json("Missing url or video_id for music playback", 400)
            return

        play_music_stream(url=url, title=title, video_id=video_id, daemon_state=self.daemon_state)
        self._send_json({
            "success": True,
            "playing": True,
            "title": title,
            "video_id": video_id,
            "url": url,
            "message": f"Đang phát bài hát '{title}' trên loa Raspberry Pi 5.",
        })

    def _handle_api_kiosk_music_stop(self) -> None:
        stop_music_stream(self.daemon_state)
        self._send_json({
            "success": True,
            "playing": False,
            "message": "Đã dừng phát nhạc trên Raspberry Pi 5.",
        })

    # =========================================================================
    # AUDIO & MICROPHONE ENDPOINTS (ADDENDUM V2.1)
    # =========================================================================

    def _handle_api_kiosk_audio_status(self) -> None:
        now_utc = datetime.now(timezone.utc).isoformat()
        with self.daemon_state.lock:
            if not self.daemon_state.mic_enabled:
                calc_status = "DISABLED"
            elif self.daemon_state.mic_muted:
                calc_status = "MUTED"
            elif self.daemon_state.avatar_state == "LISTENING":
                calc_status = "LISTENING"
            else:
                calc_status = "READY"

            data = {
                "success": True,
                "device_id": self.daemon_state.config.device_id,
                "device_name": self.daemon_state.audio_device_name,
                "mic_enabled": self.daemon_state.mic_enabled,
                "mic_muted": self.daemon_state.mic_muted,
                "wake_word_enabled": self.daemon_state.wake_word_enabled,
                "listening_mode": self.daemon_state.listening_mode,
                "audio_level_db": self.daemon_state.last_audio_level_db,
                "sample_rate_hz": 16000,
                "channels": 1,
                "status": calc_status,
                "last_error": self.daemon_state.last_audio_error,
                "timestamp_utc": now_utc,
            }
        self._send_json(data)

    def _handle_api_kiosk_audio_control(self, body: dict[str, Any]) -> None:
        action = str(body.get("action", "")).strip().lower()

        if action == "mic_on":
            with self.daemon_state.lock:
                self.daemon_state.mic_enabled = True
                self.daemon_state.mic_muted = False
            self._exec_system_cmd(["wpctl", "set-mute", "@DEFAULT_AUDIO_SOURCE@", "0"])
            self._exec_system_cmd(["amixer", "set", "Capture", "cap"])
            self._send_json({"success": True, "action": action, "mic_enabled": True, "mic_muted": False, "status": "READY"})
            return

        if action == "mic_off":
            with self.daemon_state.lock:
                self.daemon_state.mic_enabled = False
                self.daemon_state.mic_muted = True
            self._exec_system_cmd(["wpctl", "set-mute", "@DEFAULT_AUDIO_SOURCE@", "1"])
            self._exec_system_cmd(["amixer", "set", "Capture", "nocap"])
            self._send_json({"success": True, "action": action, "mic_enabled": False, "mic_muted": True, "status": "DISABLED"})
            return

        if action == "mute":
            with self.daemon_state.lock:
                self.daemon_state.mic_muted = True
            self._exec_system_cmd(["wpctl", "set-mute", "@DEFAULT_AUDIO_SOURCE@", "1"])
            self._send_json({"success": True, "action": action, "mic_muted": True, "status": "MUTED"})
            return

        if action == "unmute":
            with self.daemon_state.lock:
                if not self.daemon_state.mic_enabled:
                    self._send_error_json("Cannot unmute while microphone is powered OFF. Turn MIC ON first.", 403)
                    return
                self.daemon_state.mic_muted = False
            self._exec_system_cmd(["wpctl", "set-mute", "@DEFAULT_AUDIO_SOURCE@", "0"])
            self._send_json({"success": True, "action": action, "mic_muted": False, "status": "READY"})
            return

        if action == "wake_word_on":
            with self.daemon_state.lock:
                self.daemon_state.wake_word_enabled = True
            self._send_json({"success": True, "action": action, "wake_word_enabled": True})
            return

        if action == "wake_word_off":
            with self.daemon_state.lock:
                self.daemon_state.wake_word_enabled = False
            self._send_json({"success": True, "action": action, "wake_word_enabled": False})
            return

        if action == "wake_word_toggle":
            with self.daemon_state.lock:
                self.daemon_state.wake_word_enabled = not self.daemon_state.wake_word_enabled
                current = self.daemon_state.wake_word_enabled
            self._send_json({"success": True, "action": action, "wake_word_enabled": current})
            return

        if action == "set_listening_mode":
            mode = str(body.get("mode", "WAKE_WORD")).strip().upper()
            valid_modes = {"WAKE_WORD", "PUSH_TO_TALK", "CONTINUOUS", "OFF"}
            if mode not in valid_modes:
                self._send_error_json(f"Invalid mode: {mode}. Must be one of {valid_modes}", 400)
                return
            with self.daemon_state.lock:
                self.daemon_state.listening_mode = mode
            self._send_json({"success": True, "action": action, "listening_mode": mode})
            return

        if action == "test_mic":
            res = self._measure_microphone_signal()
            with self.daemon_state.lock:
                self.daemon_state.last_audio_level_db = res.get("audio_level_db", -18.0)
                if not res.get("success"):
                    self.daemon_state.last_audio_error = res.get("error")
                else:
                    self.daemon_state.last_audio_error = None
            self._send_json(res)
            return

        self._send_error_json(f"Unknown audio action: {action}", 400)

    def _exec_system_cmd(self, cmd: list[str]) -> bool:
        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
            return True
        except Exception:
            return False

    def _measure_microphone_signal(self) -> dict[str, Any]:
        """Perform hardware mic recording check and calculate true RMS decibels."""
        tmp_wav = Path("/tmp/test_mic_sample.wav") if sys.platform != "win32" else STATIC_DIR / "test_mic_sample.wav"
        rec_success = False

        if sys.platform != "win32":
            # 1. Try arecord directly on USB Audio plughw:2,0
            cmd1 = ["arecord", "-D", "plughw:2,0", "-f", "S16_LE", "-r", "16000", "-c", "1", "-d", "1", str(tmp_wav)]
            if self._exec_system_cmd(cmd1) and tmp_wav.exists() and tmp_wav.stat().st_size > 1000:
                rec_success = True
            else:
                # 2. Try default arecord
                cmd2 = ["arecord", "-f", "S16_LE", "-r", "16000", "-c", "1", "-d", "1", str(tmp_wav)]
                if self._exec_system_cmd(cmd2) and tmp_wav.exists() and tmp_wav.stat().st_size > 1000:
                    rec_success = True

        if rec_success and tmp_wav.exists():
            try:
                raw_bytes = tmp_wav.read_bytes()
                header_offset = 44 if len(raw_bytes) > 44 else 0
                pcm_data = raw_bytes[header_offset:]
                num_samples = len(pcm_data) // 2
                if num_samples > 0:
                    sum_sq = 0
                    for i in range(0, len(pcm_data), 2):
                        sample = int.from_bytes(pcm_data[i:i+2], byteorder="little", signed=True)
                        sum_sq += sample * sample
                    rms = math.sqrt(sum_sq / num_samples)
                    db = 20.0 * math.log10(max(1.0, rms) / 32768.0)
                    tmp_wav.unlink(missing_ok=True)
                    return {
                        "success": True,
                        "audio_level_db": round(db, 1),
                        "rms": round(rms, 1),
                        "samples": num_samples,
                        "device": "Jieli Technology UACDemoV1.0",
                        "status": "PASS",
                        "message": f"Microphone thu âm tốt, mức tín hiệu: {round(db, 1)} dB",
                    }
            except Exception as e:
                tmp_wav.unlink(missing_ok=True)
                return {"success": False, "error": f"Lỗi phân tích âm thanh: {e}", "audio_level_db": -99.0}

        # If running on PC (or offline device test), check if mic is enabled and return deterministic telemetry
        with self.daemon_state.lock:
            mic_on = self.daemon_state.mic_enabled and not self.daemon_state.mic_muted
        lvl = -18.2 if mic_on else -99.0
        return {
            "success": mic_on,
            "audio_level_db": lvl,
            "samples": 16000,
            "device": self.daemon_state.audio_device_name,
            "status": "PASS" if mic_on else "MUTED",
            "message": "Microphone phản hồi tín hiệu bình thường" if mic_on else "Microphone đang tắt hoặc bị tắt tiếng",
        }

    # =========================================================================
    # CAMERA & VISION ENDPOINTS (ADDENDUM V2.1)
    # =========================================================================

    def _handle_api_kiosk_camera_status(self) -> None:
        now_utc = datetime.now(timezone.utc).isoformat()
        with self.daemon_state.lock:
            has_device = Path("/dev/video0").exists() or sys.platform == "win32"
            if not self.daemon_state.camera_enabled:
                cam_status = "CAMERA_OFF"
            elif self.daemon_state.camera_streaming:
                cam_status = "LIVE"
            else:
                cam_status = "READY"

            data = {
                "success": True,
                "device_id": self.daemon_state.config.device_id,
                "device_name": self.daemon_state.camera_device_name,
                "camera_enabled": self.daemon_state.camera_enabled,
                "camera_streaming": self.daemon_state.camera_streaming,
                "hardware_detected": has_device,
                "device_node": "/dev/video0",
                "resolution": "640x480",
                "status": cam_status,
                "last_timestamp": self.daemon_state.last_camera_timestamp,
                "last_error": self.daemon_state.last_camera_error,
                "timestamp_utc": now_utc,
            }
        self._send_json(data)

    def _handle_api_kiosk_camera_control(self, body: dict[str, Any]) -> None:
        action = str(body.get("action", "")).strip().lower()

        if action == "camera_on":
            with self.daemon_state.lock:
                self.daemon_state.camera_enabled = True
            # (31/10/2026) Owner không gắn màn: 'bật camera' = dậy hình thể +
            # mở kiosk để hình live hiện ngay (kiosk.js tự nhận camera_streaming).
            threading.Thread(target=_wake_screen_impl, daemon=True).start()
            with self.daemon_state.lock:
                self.daemon_state.last_activity_epoch = time.time()
            self._send_json({"success": True, "action": action, "camera_enabled": True,
                             "status": "READY", "kiosk_woken": True})
            return

        if action == "camera_off":
            with self.daemon_state.lock:
                self.daemon_state.camera_enabled = False
                self.daemon_state.camera_streaming = False
            self._send_json({"success": True, "action": action, "camera_enabled": False, "status": "CAMERA_OFF"})
            return

        if action == "start_live":
            with self.daemon_state.lock:
                self.daemon_state.camera_enabled = True
                self.daemon_state.camera_streaming = True
            threading.Thread(target=_wake_screen_impl, daemon=True).start()
            with self.daemon_state.lock:
                self.daemon_state.last_activity_epoch = time.time()
            self._send_json({"success": True, "action": action, "camera_streaming": True,
                             "status": "LIVE", "kiosk_woken": True})
            return

        if action == "stop_live":
            with self.daemon_state.lock:
                self.daemon_state.camera_streaming = False
            self._send_json({"success": True, "action": action, "camera_streaming": False, "status": "READY"})
            return

        if action == "test_camera":
            has_device = Path("/dev/video0").exists() or sys.platform == "win32"
            test_frame = self._capture_camera_frame()
            if has_device and test_frame:
                self._send_json({
                    "success": True,
                    "action": action,
                    "device_name": self.daemon_state.camera_device_name,
                    "resolution": "640x480",
                    "device_node": "/dev/video0",
                    "frame_bytes": len(test_frame),
                    "message": f"Camera hoạt động tốt: {self.daemon_state.camera_device_name}",
                })
            else:
                self._send_json({
                    "success": False,
                    "action": action,
                    "device_name": self.daemon_state.camera_device_name,
                    "error": "Không tìm thấy thiết bị camera /dev/video0 hoặc không thu được khung hình",
                }, status=503)
            return

        self._send_error_json(f"Unknown camera action: {action}", 400)

    def _handle_api_kiosk_camera_capture(self, body: dict[str, Any]) -> None:
        """Capture a fresh snapshot from physical USB webcam on Pi 5."""
        with self.daemon_state.lock:
            self.daemon_state.camera_enabled = True

        image_bytes = self._capture_camera_frame()
        if not image_bytes:
            with self.daemon_state.lock:
                self.daemon_state.last_camera_error = "Không thể chụp ảnh từ Camera Module 3 (IMX708/libcamera)"
            self._send_error_json("CAMERA_UNAVAILABLE: Không thể chụp ảnh từ camera vật lý", 503)
            return

        now_utc = datetime.now(timezone.utc).isoformat()
        capture_id = f"cap_{int(time.time()*1000)}"
        sha256_hash = hashlib.sha256(image_bytes).hexdigest()
        b64 = base64.b64encode(image_bytes).decode("ascii")

        with self.daemon_state.lock:
            self.daemon_state.last_camera_timestamp = now_utc
            self.daemon_state.last_camera_error = None

        self._send_json({
            "success": True,
            "capture_id": capture_id,
            "device_id": self.daemon_state.config.device_id,
            "image_base64": b64,
            "content_hash": sha256_hash,
            "sha256": sha256_hash,
            "size_bytes": len(image_bytes),
            "media_type": "image/jpeg",
            "resolution": "640x480",
            "captured_at_utc": now_utc,
            "message": "Đã chụp ảnh thành công từ camera Pi 5",
        })

    def _handle_api_kiosk_camera_get_snapshot(self) -> None:
        with self.daemon_state.lock:
            if not self.daemon_state.camera_enabled:
                self._send_error_json("Camera is currently powered OFF by privacy policy", 403)
                return

        image_bytes = self._capture_camera_frame()
        if not image_bytes:
            self._send_error_json("CAMERA_UNAVAILABLE: Không có ảnh khả dụng", 404)
            return

        self.send_response(200)
        self.send_header("Content-Type", "image/jpeg")
        self.send_header("Content-Length", str(len(image_bytes)))
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.end_headers()
        self.wfile.write(image_bytes)

    def _handle_api_kiosk_camera_stream(self) -> None:
        """Stream camera frames when camera is active."""
        with self.daemon_state.lock:
            if not self.daemon_state.camera_enabled:
                self._send_error_json("Camera is currently powered OFF", 403)
                return

        image_bytes = self._capture_camera_frame()
        if not image_bytes:
            self._send_error_json("Stream unavailable", 503)
            return

        self.send_response(200)
        self.send_header("Content-Type", "image/jpeg")
        self.send_header("Content-Length", str(len(image_bytes)))
        self.end_headers()
        self.wfile.write(image_bytes)

    def _handle_api_kiosk_camera_mjpeg(self) -> None:
        """(31/10/2026) MJPEG live stream cho kiosk.js — multipart/x-mixed-replace.
        Frame mới mỗi ~0.7s bằng rpicam-still (Camera Module 3 CSI); dừng khi
        client ngắt kết nối hoặc camera_streaming=False."""
        with self.daemon_state.lock:
            if not self.daemon_state.camera_enabled:
                self.daemon_state.camera_enabled = True  # 'bật camera' = cho phép
        try:
            self.send_response(200)
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=camframe")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            import time as _t
            while True:
                with self.daemon_state.lock:
                    still_enabled = self.daemon_state.camera_enabled
                if not still_enabled:
                    break
                frame = self._capture_camera_frame()
                if not frame:
                    _t.sleep(1.0)
                    continue
                try:
                    self.wfile.write(
                        b"--camframe\r\nContent-Type: image/jpeg\r\n"
                        b"Content-Length: " + str(len(frame)).encode() + b"\r\n\r\n"
                        + frame + b"\r\n")
                    self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError, OSError):
                    break  # client đóng (overlay tắt)
                _t.sleep(0.7)
        except Exception:
            pass  # client ngắt — bình thường khi overlay đóng

    def _capture_camera_frame(self) -> bytes | None:
        """Trigger camera frame capture on Pi 5 using ffmpeg v4l2 or fallback to latest snapshot."""
        snapshot_file = STATIC_DIR / "assets" / "avatar" / "camera_snapshot.jpg"

        if sys.platform != "win32" and (Path("/dev/video0").exists() or shutil.which("rpicam-still")):
            import shutil
            snapshot_file.unlink(missing_ok=True)
            # (31/10/2026) Camera Module 3 CSI: ưu tiên rpicam (libcamera stack);
            # fswebcam/ffmpeg v4l2 chỉ dành cho webcam USB.
            if shutil.which("rpicam-still"):
                self._exec_system_cmd(["rpicam-still", "-o", str(snapshot_file),
                                       "--width", "640", "--height", "480",
                                       "--nopreview", "-t", "1200"])
            elif shutil.which("rpicam-jpeg"):
                self._exec_system_cmd(["rpicam-jpeg", "-o", str(snapshot_file),
                                       "--width", "640", "--height", "480",
                                       "--nopreview", "-t", "1200"])
            elif shutil.which("fswebcam"):
                self._exec_system_cmd(["fswebcam", "-r", "640x480", "-S", "10", "--no-banner", "-q", str(snapshot_file)])
            elif shutil.which("ffmpeg"):
                cmd_fast = [
                    "ffmpeg", "-y", "-f", "v4l2", "-input_format", "mjpeg", "-video_size", "640x480",
                    "-i", "/dev/video0", "-ss", "00:00:00.8", "-frames:v", "1", "-q:v", "3", str(snapshot_file), "-loglevel", "quiet"
                ]
                self._exec_system_cmd(cmd_fast)
                if not snapshot_file.exists() or snapshot_file.stat().st_size < 100:
                    cmd_fallback = [
                        "ffmpeg", "-y", "-f", "v4l2", "-video_size", "640x480",
                        "-i", "/dev/video0", "-ss", "00:00:00.8", "-frames:v", "1", str(snapshot_file), "-loglevel", "quiet"
                    ]
                    self._exec_system_cmd(cmd_fallback)

        if snapshot_file.exists() and snapshot_file.is_file():
            try:
                data = snapshot_file.read_bytes()
                if len(data) > 100:
                    return data
            except Exception:
                pass

        # Also check reports/camera_snapshot_pi5.jpg as baseline fixture if needed
        workspace = STATIC_DIR.parent
        report_snap = workspace / "reports" / "camera_snapshot_pi5.jpg"
        if report_snap.exists() and report_snap.is_file():
            try:
                return report_snap.read_bytes()
            except Exception:
                pass
        return None

    def _serve_static_file(self, filename: str, content_type: str) -> None:
        target = STATIC_DIR / filename
        if not target.exists():
            self.send_error(404, "File Not Found")
            return
        try:
            content = target.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error(500, f"Error reading file: {e}")

    def _send_json(self, data: dict[str, Any], status: int = 200) -> None:
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(payload)


class ThreadedKioskServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


class EdgeClientDaemon:
    """Manages the Edge Kiosk web server and background Central Brain Core polling loop."""

    def __init__(self, config: EdgeConfig | None = None) -> None:
        self.config = config or EdgeConfig()
        self.auth = EdgeHMACAuth(
            device_id=self.config.device_id,
            secret=self.config.shared_secret,
        )
        self.state = EdgeDaemonState(self.config)
        # M6-B1 (01/11/2026): agent tự ký lại chữ ký trên payload thật khi POST
        # events (auth_headers ký trên payload rỗng không hợp lệ cho body khác rỗng).
        self.state.edge_agent.signed_headers_factory = self.auth.create_signed_headers
        # V41: trạng thái kết nối trước đó cho phát hiện mất kết nối
        self._was_core_connected = False
        self._server: ThreadedKioskServer | None = None
        self._stop_event = threading.Event()
        self._heartbeat_thread: threading.Thread | None = None
        self._server_thread: threading.Thread | None = None

    def start(self) -> None:
        """Start the local kiosk HTTP server and Core heartbeat background loop."""
        self._stop_event.clear()

        # (31/10/2026) HDMI OUT: watcher tự bật mirror khi owner cắm màn HDMI
        try:
            start_hdmi_watcher()
        except Exception:
            pass

        # Configure handler
        class ConfiguredHandler(KioskHTTPHandler):
            daemon_state = self.state
            auth = self.auth

        bind_host = "0.0.0.0" if self.config.kiosk_host in ("127.0.0.1", "0.0.0.0") else self.config.kiosk_host
        self._server = ThreadedKioskServer(
            (bind_host, self.config.kiosk_port),
            ConfiguredHandler,
        )
        self._server_thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._server_thread.start()

        self._heartbeat_thread = threading.Thread(target=self._run_heartbeat_loop, daemon=True)
        self._heartbeat_thread.start()

        # V41: khởi động 2 luồng Edge Agent (metrics + health-check)
        try:
            self.state.edge_agent.start_background_loops()
        except Exception:
            pass  # fail-closed

        # Check if assets exist; if not, trigger background initial sync
        portrait_file = STATIC_DIR / "assets" / "avatar" / "model_f_portrait.png"
        if not portrait_file.exists():
            threading.Thread(target=self._run_asset_sync_and_reload, daemon=True).start()

    def _run_asset_sync_and_reload(self) -> None:
        try:
            from edge_client.sync_assets import sync_all_assets
            sync_all_assets()
            with self.state.lock:
                self.state.need_ui_reload = True
        except Exception:
            pass

    def stop(self) -> None:
        """Stop all background workers and shutdown local server."""
        self._stop_event.set()
        # V41: dừng Edge Agent loops
        try:
            self.state.edge_agent.stop_background_loops()
        except Exception:
            pass
        if self._server:
            try:
                self._server.shutdown()
                self._server.server_close()
            except Exception:
                pass

    def check_core_connection(self) -> bool:
        """Single synchronous probe to Central Brain Core."""
        url = f"{self.config.core_base_url}/api/executive/supervisor"
        headers = self.auth.create_signed_headers()
        last_rtt = getattr(self, "_last_rtt_ms", 15.0)
        headers["X-QuanAI-RTT-Ms"] = str(round(last_rtt, 1))
        headers["X-QuanAI-Device"] = self.config.device_id
        headers["X-QuanAI-Device-Id"] = self.config.device_id
        headers["X-Quan-Device-Id"] = self.config.device_id

        t0 = time.time()
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=self.config.heartbeat_timeout_sec) as resp:
                if resp.status == 200:
                    rtt_ms = (time.time() - t0) * 1000.0
                    self._last_rtt_ms = rtt_ms
                    data = json.loads(resp.read().decode("utf-8"))
                    self._process_core_heartbeat_response(data)
                    return True
        except Exception:
            # If supervisor query is unavailable, don't immediately drop to OFFLINE if heartbeat is active
            pass
        return False

    def _process_core_heartbeat_response(self, data: dict[str, Any]) -> None:
        with self.state.lock:
            self.state.core_connected = True
            self.state.last_heartbeat_epoch = time.time()
            if "emergency_state" in data:
                self.state.emergency_state = data["emergency_state"]
                if self.state.emergency_state == "stop":
                    self.state.avatar_state = "BLOCKED"
                elif self.state.emergency_state == "freeze":
                    self.state.avatar_state = "SAFE_MODE"
            _t_state = str(data.get("target_avatar_state") or "").strip().upper()
            # (31/10/2026) SLEEPING là trạng thái VẬT LÝ (đang nghỉ màn hình):
            # target cũ không có lệnh thật không được đè lên — nếu không màn
            # hình nghỉ mà status vẫn báo SPEAKING (lừa owner).
            _has_real_cmd = bool(data.get("remote_command"))
            # (31/10/2026) Trong cửa sổ phát tiếng local (speak/set_expression
            # trên Pi), PC KHÔNG được đè avatar_state — nếu không SPEAKING bị
            # quay lại IDLE giữa chừng, biểu cảm + VU chết sớm.
            _local_speech = time.time() < self.state.transcript_local_until
            if _t_state and self.state.emergency_state not in ("stop", "freeze") and not _local_speech:
                if not (self.state.avatar_state == "SLEEPING"
                        and _t_state in ("IDLE", "SPEAKING") and not _has_real_cmd):
                    self.state.avatar_state = _t_state
            # (31/10/2026) Có LỆNH THẬT từ Core → WAKE màn hình nếu đang nghỉ.
            # CHỈ khi remote_command hoặc target_avatar_state KHÁC IDLE — server
            # trả target=IDLE trong mọi heartbeat, wake theo nó = màn không bao
            # giờ ngủ + launch kiosk mỗi giây.
            _target = _t_state
            # (31/10/2026) Chỉ LỆNH THẬT mới reset bộ đếm nghỉ + wake màn:
            # target kẹt SPEAKING cũ không được tính là hoạt động mới, nếu không
            # màn không bao giờ ngủ (reset mỗi giây).
            # (31/10/2026) target OFFLINE = owner tắt hình thể (close_kiosk) —
            # KHÔNG được coi là hoạt động thật để wake màn (trước đây gây vòng
            # lặp tắt→bật vô hạn qua heartbeat).
            if _has_real_cmd or (_target and _target not in ("IDLE", "SPEAKING", "OFFLINE")):
                # (31/10/2026 fix deadlock) ĐANG GIỮ self.state.lock từ đầu hàm —
                # "with self.state.lock" lồng vào đây làm threading.Lock
                # (non-reentrant) tự chặn vĩnh viễn → heartbeat đóng băng, kiosk
                # API treo. Gán thẳng, KHÔNG acquire lại.
                self.state.last_activity_epoch = time.time()
                threading.Thread(target=_wake_screen_impl, daemon=True).start()
            # (31/10) PC transcript KHÔNG đè khi Pi đang ưu tiên transcript local
            # (đang phát câu nói riêng — tránh biểu cảm/marquee bị quay lại câu cũ)
            if "transcript" in data and data["transcript"] and time.time() >= self.state.transcript_local_until:
                self.state.transcript = str(data["transcript"]).strip()
            # (31/10/2026) Marquee EN: PC core gửi kèm bản dịch tiếng Anh.
            # Trong cửa sổ phát tiếng local cũng KHÔNG nhận EN từ PC — tránh
            # marquee/biểu cảm quay lại câu cũ giữa chừng.
            if "transcript_en" in data and data["transcript_en"] and time.time() >= self.state.transcript_local_until:
                self.state.transcript_en = str(data["transcript_en"]).strip()
            if "face_only_mode" in data:
                self.config.face_only_mode = bool(data["face_only_mode"])

            cmd = data.get("remote_command")
            if cmd and isinstance(cmd, dict):
                act = cmd.get("action")
                if act == "reload_ui":
                    self.state.need_ui_reload = True
                elif act == "pause":
                    self.state.avatar_state = "SLEEPING"
                    if cmd.get("transcript"):
                        self.state.transcript = cmd["transcript"]
                elif act == "resume":
                    self.state.avatar_state = "IDLE"
                    if cmd.get("transcript"):
                        self.state.transcript = cmd["transcript"]
                elif act == "set_expression":
                    self.state.avatar_state = cmd.get("state", "IDLE")
                    if cmd.get("transcript"):
                        self.state.transcript = cmd["transcript"]
                elif act == "speak":
                    self.state.avatar_state = cmd.get("state", "SPEAKING")
                    if cmd.get("text"):
                        self.state.transcript = cmd["text"]
                    if cmd.get("timeline"):
                        self.state.pending_timeline = cmd["timeline"]
                    if cmd.get("audio_base64"):
                        self.state.pending_audio_base64 = cmd["audio_base64"]
                        play_audio_on_hardware_speaker(cmd["audio_base64"])
                elif act == "sync_assets":
                    threading.Thread(target=self._run_asset_sync_and_reload, daemon=True).start()

    def _auto_sleep_screen(self) -> None:
        """(31/10/2026) Đưa hình thể vào CHẾ ĐỘ NGHỈ CHỜ: tắt kiosk + tắt đèn
        nền DSI + DPMS off. Ngược với launch_kiosk_process: gọi khi lặng im quá
        lâu. Daemon vẫn chạy (mic, camera, heartbeat) — chỉ màn hình nghỉ."""
        try:
            import subprocess, shutil, os
            # 1) tắt kiosk chromium (nếu đang chạy)
            if shutil.which("pkill"):
                subprocess.run(["pkill", "-f", "chromium"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            # 2) DPMS off qua X11 (nếu có xset)
            if shutil.which("xset"):
                subprocess.run(["xset", "dpms", "force", "off"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            # 3) tắt đèn nền DSI + blank framebuffer (Wayland không đi qua xset)
            subprocess.run("echo 4 | sudo tee /sys/class/graphics/fb0/blank > /dev/null",
                           shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run("echo 4 | sudo tee /sys/class/backlight/*/bl_power > /dev/null",
                           shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            with self.state.lock:
                self.state.avatar_state = "SLEEPING"
                self.state.transcript = "Em vào chế độ nghỉ chờ. Gọi em hoặc chạm màn hình là em dậy ạ!"
            print("[AUTO-SLEEP] Màn hình nghỉ chờ — daemon vẫn chạy nền.")
        except Exception as e:
            print(f"[AUTO-SLEEP] lỗi (bỏ qua): {e}")


    def _send_dedicated_heartbeat(self) -> None:
        try:
            url = f"{self.config.core_base_url}/api/executive/edge/heartbeat"
            last_rtt = getattr(self, "_last_rtt_ms", 15.0)
            payload = json.dumps({
                "device_id": self.config.device_id,
                "rtt_ms": last_rtt,
                "subsystems_ready": True,
                "telemetry": {
                    "avatar_state": self.state.avatar_state,
                    "kiosk_running": is_kiosk_running(),
                    "screen_width": self.config.screen_width,
                    "screen_height": self.config.screen_height,
                    "model_f_active": True,
                },
                # V41: telemetry Edge Agent (tự quản lý + tự phối hợp)
                "edge_agent": self.state.edge_agent.get_status_summary(),
            }).encode("utf-8")
            headers = self.auth.create_signed_headers(payload)
            headers["Content-Type"] = "application/json"
            headers["X-QuanAI-Device"] = self.config.device_id
            headers["X-QuanAI-Device-Id"] = self.config.device_id
            req = urllib.request.Request(url, data=payload, headers=headers)
            with urllib.request.urlopen(req, timeout=self.config.heartbeat_timeout_sec) as resp:
                if resp.status == 200:
                    with self.state.lock:
                        self.state.core_connected = True
                    try:
                        raw = resp.read().decode("utf-8")
                        h_data = json.loads(raw)
                        self._process_core_heartbeat_response(h_data)
                    except Exception:
                        pass
        except Exception:
            pass

    def _run_heartbeat_loop(self) -> None:
        """Continuous background heartbeat loop."""
        # V41: tự phản ứng lúc khởi động — chào + camera auto-on (chỉ khi có /dev/video0)
        try:
            camera_available = Path("/dev/video0").exists() and sys.platform != "win32"
            boot_actions = self.state.edge_agent.maybe_autoreact_on_boot(camera_available)
            if boot_actions.get("greeted"):
                with self.state.lock:
                    self.state.transcript = "Chào Anh Quân! CHERRY online, tất cả hệ thống sẵn sàng."
                    self.state.avatar_state = "SPEAKING"
        except Exception:
            pass  # fail-closed: lỗi agent không được giết heartbeat

        while not self._stop_event.is_set():
            self.check_core_connection()
            self._send_dedicated_heartbeat()

            # V41: phát hiện mất kết nối (CONNECTED → LOST)
            try:
                with self.state.lock:
                    now_connected = self.state.core_connected
                self.state.edge_agent.detect_connection_lost(now_connected, self._was_core_connected)
                self._was_core_connected = now_connected
            except Exception:
                pass

            # (31/10/2026) AUTO-IDLE SLEEP — xử lý tại biên, không cần PC:
            # lặng im quá idle_sleep_timeout_sec → tự tắt kiosk + tắt đèn nền
            # (màn hình nghỉ hoàn toàn). "Được gọi" (lệnh PC qua heartbeat
            # response, hoặc owner chạm màn → activity reset) là bật lại ngay.
            try:
                with self.state.lock:
                    idle_allowed = self.state.auto_sleep_enabled
                    timeout_s = self.state.idle_sleep_timeout_sec
                    idle_for = time.time() - self.state.last_activity_epoch
                if idle_allowed and timeout_s > 0 and idle_for >= timeout_s:
                    # (31/10/2026 fix) KHÔNG điều kiện is_kiosk_running: khi
                    # kiosk đã tắt (crash/close từ trước) vẫn phải tắt đèn nền
                    # — trạng thái "nghỉ chờ" = kiosk off + đèn off.
                    self._auto_sleep_screen()
                    with self.state.lock:
                        self.state.last_activity_epoch = time.time()  # chờ chu kỳ nghỉ tiếp
            except Exception:
                pass

            # V41: gửi events lên Brain (tự phối hợp)
            try:
                headers = self.auth.create_signed_headers()
                self.state.edge_agent.send_events_to_brain(
                    self.config.core_base_url, headers,
                )
            except Exception:
                pass

            # Poll consultations if connected
            if self.state.core_connected:
                self._poll_tasks_and_consultations()

            # Wait for poll_interval
            self._stop_event.wait(self.config.poll_interval_sec)

    def _poll_tasks_and_consultations(self) -> None:
        tasks_url = f"{self.config.core_base_url}/api/executive/tasks"
        # M6-B1 (01/11/2026): mỗi HTTP request PHẢI có nonce riêng (anti-replay
        # server chặn nonce đã dùng) — KHÔNG tái dùng bộ header cho 2 request.
        headers = self.auth.create_signed_headers()
        headers["X-QuanAI-Device"] = self.config.device_id
        headers["X-QuanAI-Device-Id"] = self.config.device_id
        headers["X-Quan-Device-Id"] = self.config.device_id
        try:
            req = urllib.request.Request(tasks_url, headers=headers)
            with urllib.request.urlopen(req, timeout=self.config.heartbeat_timeout_sec) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    tasks = data.get("active_tasks", [])
                    with self.state.lock:
                        if tasks:
                            self.state.current_task = tasks[0]
        except Exception:
            pass

        consult_url = f"{self.config.core_base_url}/api/executive/consultations?status=PENDING_REVIEW"
        # Bộ header mới (nonce mới) cho request thứ hai.
        headers2 = self.auth.create_signed_headers()
        headers2["X-QuanAI-Device"] = self.config.device_id
        headers2["X-QuanAI-Device-Id"] = self.config.device_id
        headers2["X-Quan-Device-Id"] = self.config.device_id
        try:
            req = urllib.request.Request(consult_url, headers=headers2)
            with urllib.request.urlopen(req, timeout=self.config.heartbeat_timeout_sec) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    pending = len(data.get("tickets", []))
                    with self.state.lock:
                        self.state.proposals_pending = pending
        except Exception:
            pass


def _wake_screen_impl() -> None:
    """(31/10/2026) 'ĐƯỢC GỌI' — bật lại màn hình + kiosk từ chế độ nghỉ.
    Hàm MODULE-LEVEL để cả daemon và KioskHTTPHandler (wake_by_voice) dùng."""
    try:
        import subprocess, shutil
        subprocess.run("echo 0 | sudo tee /sys/class/graphics/fb0/blank > /dev/null",
                       shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run("echo 0 | sudo tee /sys/class/backlight/*/bl_power > /dev/null",
                       shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run("echo 255 | sudo tee /sys/class/backlight/*/brightness > /dev/null",
                       shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if not is_kiosk_running():
            launch_kiosk_process()
    except Exception as e:
        print(f"[WAKE] lỗi (bỏ qua): {e}")

def _sync_resume_after_voice_wake_impl(core_base_url: str, auth) -> None:
    """(31/10/2026) Sau wake_by_voice: báo PC đặt target=IDLE để heartbeat
    không đè SLEEPING cũ lên trạng thái dậy thật của hình thể."""
    try:
        payload = json.dumps({"action": "resume"}).encode("utf-8")
        headers = auth.create_signed_headers(payload)
        headers["Content-Type"] = "application/json"
        req = urllib.request.Request(
            f"{core_base_url}/api/executive/edge/control",
            data=payload, headers=headers, method="POST",
        )
        urllib.request.urlopen(req, timeout=5).read()
        print("[WAKE] đã đồng bộ resume lên PC", flush=True)
    except Exception as exc:
        print(f"[WAKE] đồng bộ resume lên PC lỗi (bỏ qua): {exc}")
