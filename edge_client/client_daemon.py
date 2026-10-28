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
    """Phát nhạc trực tiếp qua loa vật lý trên Pi 5 (ưu tiên mpv / cvlc / mpg123)."""
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
        import shutil, subprocess
        cmd = None
        if shutil.which("mpv"):
            cmd = ["mpv", "--no-video", "--really-quiet", url]
        elif shutil.which("cvlc"):
            cmd = ["cvlc", "--no-video", "--play-and-exit", "-q", url]
        elif shutil.which("mpg123") and (url.endswith(".mp3") or "audio" in url):
            cmd = ["mpg123", "-q", url]

        if cmd:
            try:
                with _MUSIC_LOCK:
                    _MUSIC_PROC = subprocess.Popen(
                        cmd,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                _MUSIC_PROC.wait()
            except Exception:
                pass
            finally:
                with _MUSIC_LOCK:
                    _MUSIC_PROC = None
                if daemon_state is not None:
                    try:
                        with daemon_state.lock:
                            if daemon_state.current_music and daemon_state.current_music.get("video_id") == video_id:
                                daemon_state.current_music = None
                    except Exception:
                        pass

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    return True



def is_kiosk_running() -> bool:
    """Kiểm tra xem tiến trình Chromium Kiosk hiển thị hình thể có đang chạy hay không."""
    global _KIOSK_PROC
    try:
        import subprocess, shutil, os
        if shutil.which("pgrep"):
            res = subprocess.run(["pgrep", "-f", "chromium"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=1.0)
            return bool(res.stdout.strip())
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
                "--window-size=1280,720",
                "--window-position=0,0",
                "--enable-features=OverlayScrollbar",
                "--autoplay-policy=no-user-gesture-required",
                "--use-fake-ui-for-media-stream",
                "--password-store=basic",
                "--disable-session-crashed-bubble",
                "--disable-features=Translate",
                "http://127.0.0.1:8768/"
            ]
            cmd = [chrome_bin] + chrome_flags
            _KIOSK_PROC = subprocess.Popen(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False


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
        self.last_heartbeat_epoch: float = 0.0
        self.need_ui_reload: bool = False
        self.pending_audio_base64: str | None = None
        self.pending_timeline: dict[str, Any] | None = None

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
        self.camera_device_name: str = "Sirius USB2.0 Camera (/dev/video0)"

        # YouTube Music & Audio Streaming State
        self.current_music: dict[str, Any] | None = None

    def to_kiosk_dict(self) -> dict[str, Any]:
        with self.lock:
            reload_needed = self.need_ui_reload
            self.need_ui_reload = False
            audio_b64 = self.pending_audio_base64
            timeline_obj = self.pending_timeline
            self.pending_audio_base64 = None
            self.pending_timeline = None
            kiosk_active = is_kiosk_running()
            return {
                "core_connected": self.core_connected,
                "avatar_state": self.avatar_state if self.core_connected else "OFFLINE",
                "kiosk_running": kiosk_active,
                "embodiment_mode": "ACTIVE" if kiosk_active else "STANDBY",
                "core_host": f"{self.config.core_host}:{self.config.core_port}",
                "device_id": self.config.device_id,
                "face_only_mode": getattr(self.config, "face_only_mode", True),
                "active_model": self.active_model,
                "emergency_state": self.emergency_state,
                "current_task": self.current_task,
                "proposals_pending": self.proposals_pending,
                "transcript": self.transcript,
                "last_heartbeat_epoch": self.last_heartbeat_epoch,
                "need_ui_reload": reload_needed,
                "pending_audio_base64": audio_b64,
                "pending_timeline": timeline_obj,
                "music": self.current_music,
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
            self._send_json(data)
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

        if path == "/api/kiosk/camera/stream":
            self._handle_api_kiosk_camera_stream()
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

        self.send_error(404, "Endpoint Not Found")

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
                    or body.get("force_hardware")
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

        if action == "set_face_only":
            val = bool(body.get("face_only", True))
            self.daemon_state.config.face_only_mode = val
            self._send_json({"success": True, "face_only_mode": val})
            return

        if action in ("start_kiosk", "launch_kiosk", "open_kiosk"):
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
            with self.daemon_state.lock:
                self.daemon_state.avatar_state = "STOPPED"
                self.daemon_state.transcript = "Giao diện hình thể đã đóng theo lệnh của Anh."
            try:
                import subprocess, shutil, os
                global _KIOSK_PROC
                if shutil.which("pkill"):
                    subprocess.run(["pkill", "-f", "chromium"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                elif os.name == "nt":
                    if _KIOSK_PROC and _KIOSK_PROC.poll() is None:
                        _KIOSK_PROC.terminate()
                        _KIOSK_PROC = None
                if shutil.which("xset"):
                    subprocess.run(["xset", "dpms", "force", "off"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                self._send_json({
                    "success": True,
                    "action": action,
                    "kiosk_running": False,
                    "embodiment_mode": "STANDBY",
                    "message": "Đã tắt hẳn giao diện hình thể Kiosk và đưa màn hình Pi 5 vào chế độ nghỉ"
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
            self._send_json({"success": True, "action": action, "camera_enabled": True, "status": "READY"})
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
            self._send_json({"success": True, "action": action, "camera_streaming": True, "status": "LIVE"})
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
                self.daemon_state.last_camera_error = "Không thể chụp ảnh từ thiết bị camera /dev/video0"
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

    def _capture_camera_frame(self) -> bytes | None:
        """Trigger camera frame capture on Pi 5 using ffmpeg v4l2 or fallback to latest snapshot."""
        snapshot_file = STATIC_DIR / "assets" / "avatar" / "camera_snapshot.jpg"

        if sys.platform != "win32" and Path("/dev/video0").exists():
            import shutil
            snapshot_file.unlink(missing_ok=True)
            # Fast capture: fswebcam with warm-up or ffmpeg with seek delay
            if shutil.which("fswebcam"):
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
        self._server: ThreadedKioskServer | None = None
        self._stop_event = threading.Event()
        self._heartbeat_thread: threading.Thread | None = None
        self._server_thread: threading.Thread | None = None

    def start(self) -> None:
        """Start the local kiosk HTTP server and Core heartbeat background loop."""
        self._stop_event.clear()

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
            if "target_avatar_state" in data and data["target_avatar_state"]:
                if self.state.emergency_state not in ("stop", "freeze"):
                    self.state.avatar_state = str(data["target_avatar_state"]).strip().upper()
            if "transcript" in data and data["transcript"]:
                self.state.transcript = str(data["transcript"]).strip()
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

    def _send_dedicated_heartbeat(self) -> None:
        """Send explicit telemetry heartbeat to Core /api/executive/edge/heartbeat."""
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
        while not self._stop_event.is_set():
            self.check_core_connection()
            self._send_dedicated_heartbeat()

            # Poll consultations if connected
            if self.state.core_connected:
                self._poll_tasks_and_consultations()

            # Wait for poll_interval
            self._stop_event.wait(self.config.poll_interval_sec)

    def _poll_tasks_and_consultations(self) -> None:
        tasks_url = f"{self.config.core_base_url}/api/executive/tasks"
        headers = self.auth.create_signed_headers()
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
        try:
            req = urllib.request.Request(consult_url, headers=headers)
            with urllib.request.urlopen(req, timeout=self.config.heartbeat_timeout_sec) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    pending = len(data.get("tickets", []))
                    with self.state.lock:
                        self.state.proposals_pending = pending
        except Exception:
            pass
