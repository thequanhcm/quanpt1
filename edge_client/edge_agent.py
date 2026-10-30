"""Edge Agent V41 — Năng lực chủ động (autonomous capabilities) cho Edge Device.

NĂNG LỰC PHỤC VỤ CHỈ THỊ CỦA QUANPT1 (30/10/2026):
1. TỰ PHẢN ỨNG  — camera auto-on + chào mừng khởi động + phát hiện mất kết nối Brain
2. TỰ QUẢN LÝ   — giám sát CPU/RAM/nhiệt độ/throttling + ngoại vi + tình trạng dịch vụ
3. TỰ THU THẬP  — ghi event ring-buffer theo chính sách lưu trữ (giới hạn số lượng)
4. TỰ PHỐI HỢP  — gửi sự kiện quan trọng lên Brain (heartbeat telemetry + /api/executive/edge/events)
5. TỰ CẢI TIẾN CÓ KIỂM SOÁT — health-check định kỳ, self-test GHI NHẬN đề xuất,
   KHÔNG TỰ ĐỘNG áp dụng (fail-closed: mọi nâng cấp chờ duyệt).

NGUYÊN TẮC AN TOÀN:
- Không sửa cấu hình sản xuất, không mở rộng quyền, không tự cài đặt gì.
- Toàn bộ hành vi đọc-ols (read-only); các "đề xuất" chỉ nằm trong buffer.
- Camera auto-on CHỈ bật khi có /dev/video0 (Pi) — win32 không tự bật.
- Không phụ thuộc thư viện ngoài (stdlib-only), không phá AUDIO_PLAYBACK_MODE.
"""
from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import threading
import time
import urllib.request
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

# Chính sách lưu trữ: giới hạn cứng, tự cắt đuôi (ring buffer)
MAX_EVENTS = 200
MAX_SUGGESTIONS = 50
MAX_METRICS_HISTORY = 120  # ~1 giờ với sample mỗi 30s
HEALTH_CHECK_INTERVAL_SEC = 300.0  # năng lực 5: mỗi 5 phút
METRICS_INTERVAL_SEC = 30.0
TEMP_THRESHOLD_C = 75.0  # Pi 5: ngưỡng báo nóng
THROTTLED_BITMASK_DESC = {
    0: "OK - khong co van de",
    1: "Under-voltage hien tai",
    2: "ARM tan so bi gioi han (cap)",
    4: "Dang throttle NGAY LUC NAY",
    16: "Under-voltage da xay ra",
    18: "Da bi throttle (softfab limit)",
}
GREETING_TEXT = "Chào Anh Quân! TONY online, tất cả hệ thống sẵn sàng."

_GREETED_FILE = Path(__file__).resolve().parent / ".greeted_this_boot"


class EdgeAgentError(Exception):
    """Lỗi riêng của Edge Agent."""


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_proc_stat() -> tuple[int, int]:
    """Đọc /proc/stat cpu line → (idle, total). Trả (0,0) nếu không đọc được."""
    try:
        with open("/proc/stat", "r", encoding="utf-8") as f:
            first = f.readline()
        parts = first.split()
        vals = [int(v) for v in parts[1:8]]
        idle = vals[3] + vals[4]  # idle + iowait
        total = sum(vals)
        return idle, total
    except Exception:
        return 0, 0


def _read_mem_available_mb() -> int:
    try:
        with open("/proc/meminfo", "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("MemAvailable"):
                    return int(line.split()[1]) // 1024
    except Exception:
        pass
    return -1


def _read_temp_celsius() -> float:
    """Nhiệt độ SoC Pi: /sys/class/thermal/thermal_zone0/temp (millicelsius)."""
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r", encoding="utf-8") as f:
            return int(f.read().strip()) / 1000.0
    except Exception:
        return -1.0


def _read_throttled_bits() -> int:
    """vcgencmd get_throttled → bitmask. Trả -1 nếu không chạy được (không-Pi / không quyền)."""
    try:
        if shutil.which("vcgencmd") is None:
            return -1
        out = subprocess.run(
            ["vcgencmd", "get_throttled"],
            capture_output=True, text=True, timeout=3,
        ).stdout.strip()
        # dạng: throttled=0x0
        hex_part = out.split("=", 1)[1].strip()
        return int(hex_part, 16)
    except Exception:
        return -1


def _read_uptime_sec() -> float:
    try:
        with open("/proc/uptime", "r", encoding="utf-8") as f:
            return float(f.read().split()[0])
    except Exception:
        return -1.0


def _read_load_avg() -> tuple[float, float, float]:
    try:
        return os.getloadavg()
    except Exception:
        return (-1.0, -1.0, -1.0)


def _detect_peripherals() -> dict[str, Any]:
    """Phát hiện ngoại vi: camera, âm thanh, I2C. Read-only, fail-closed."""
    peripherals: dict[str, Any] = {
        "camera_dev0": Path("/dev/video0").exists(),
        "i2c_dev": Path("/dev/i2c-1").exists(),
        "alsa_cards": -1,
        "platform": platform.system(),
    }
    try:
        out = subprocess.run(
            ["cat", "/proc/asound/cards"],
            capture_output=True, text=True, timeout=3,
        ).stdout
        # đếm các dòng có id card
        n = 0
        for line in out.splitlines():
            if line and line[0].isdigit():
                n += 1
        peripherals["alsa_cards"] = n
    except Exception:
        pass
    return peripherals


def _check_services() -> dict[str, bool]:
    """Tình trạng dịch vụ nền (systemd user-level / process check) — read-only."""
    services = {"edge_daemon_alive": True}
    try:
        out = subprocess.run(
            ["systemctl", "is-active", "edge-client.service"],
            capture_output=True, text=True, timeout=3,
        )
        services["edge_daemon_alive"] = out.stdout.strip() == "active"
    except Exception:
        # không có systemctl (trên PC) → mặc định daemon alive vì chính nó đang chạy
        pass
    return services


class EdgeEventBuffer:
    """Năng lực 3 — TỰ THU THẬP: ring-buffer event giới hạn cứng MAX_EVENTS."""

    def __init__(self, max_events: int = MAX_EVENTS) -> None:
        self._lock = threading.Lock()
        self._events: deque[dict[str, Any]] = deque(maxlen=max_events)
        self._seq = 0

    def add(
        self,
        event_type: str,
        severity: str = "INFO",
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            self._seq += 1
            ev = {
                "seq": self._seq,
                "type": event_type,
                "severity": severity,
                "timestamp_utc": _now_utc_iso(),
                "details": details or {},
            }
            self._events.append(ev)
            return ev

    def drain(self) -> list[dict[str, Any]]:
        """Lấy toàn bộ event CHƯA gửi lên Brain (reset buffer sau khi đọc)."""
        with self._lock:
            events = list(self._events)
            self._events.clear()
            return events

    def snapshot(self) -> list[dict[str, Any]]:
        """Xem không phá hủy (cho kiosk hiển thị / debug)."""
        with self._lock:
            return list(self._events)

    def __len__(self) -> int:
        with self._lock:
            return len(self._events)


class EdgeAgent:
    """Bộ điều phối 5 năng lực chủ động. Chạy 2 luồng nền:
    - metrics_loop: TỰ QUẢN LÝ + TỰ THU THẬP (mỗi METRICS_INTERVAL_SEC)
    - health_loop:  TỰ CẢI TIẾN CÓ KIỂM SOÁT (mỗi HEALTH_CHECK_INTERVAL_SEC)
    """

    def __init__(self, config: Any = None) -> None:
        self.config = config
        self.events = EdgeEventBuffer()
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._metrics_thread: threading.Thread | None = None
        self._health_thread: threading.Thread | None = None

        # TỰ QUẢN LÝ: metrics hiện tại + lịch sử
        self._last_metrics: dict[str, Any] = {}
        self._metrics_history: deque[dict[str, Any]] = deque(maxlen=MAX_METRICS_HISTORY)
        self._prev_cpu_idle_total: tuple[int, int] = (0, 0)

        # TỰ PHẢN ỨNG: đã chào trong boot này chưa
        self._greeted = _GREETED_FILE.exists()

        # TỰ CẢI TIẾN: đề xuất (chỉ ghi nhận)
        self._suggestions: deque[dict[str, Any]] = deque(maxlen=MAX_SUGGESTIONS)

        # Callback do daemon cài (để đóng gói tests)
        self._notify_lost_connection: Callable[[str], None] | None = None
        self._notify_temp_hot: Callable[[float], None] | None = None

    # ------------------------------------------------------------------
    # TỰ PHẢN ỨNG (1)
    # ------------------------------------------------------------------
    def maybe_autoreact_on_boot(self, camera_available: bool) -> dict[str, Any]:
        """Chào mừng khởi động + bật camera tự động (CHỈ trên Pi có /dev/video0).

        Trả dict mô tả đã làm gì — daemon dùng để hiển thị kiosk + gửi Brain.
        """
        actions: dict[str, Any] = {"greeted": False, "camera_auto_on": False}
        if not self._greeted:
            self.events.add(
                "STARTUP_GREETING",
                severity="INFO",
                details={"text": GREETING_TEXT},
            )
            self._greeted = True
            try:
                _GREETED_FILE.touch()
            except Exception:
                pass
            actions["greeted"] = True

        if camera_available:
            self.events.add(
                "CAMERA_AUTO_ON",
                severity="INFO",
                details={"device": "/dev/video0"},
            )
            actions["camera_auto_on"] = True
        return actions

    def detect_connection_lost(self, core_connected: bool, was_connected: bool) -> bool:
        """Phát hiện chuyển trạng thái CONNECTED → LOST. Trả True nếu vừa mất."""
        if was_connected and not core_connected:
            self.events.add(
                "BRAIN_CONNECTION_LOST",
                severity="CRITICAL",
                details={"last_seen_epoch": time.time()},
            )
            if self._notify_lost_connection:
                try:
                    self._notify_lost_connection("Mất kết nối tới Central Brain Core")
                except Exception:
                    pass
            return True
        return False

    # ------------------------------------------------------------------
    # TỰ QUẢN LÝ (2)
    # ------------------------------------------------------------------
    def collect_metrics(self) -> dict[str, Any]:
        """Thu thập metrics hệ thống: CPU/RAM/nhiệt/throttle/load/uptime/dịch vụ."""
        idle, total = _read_proc_stat()
        cpu_pct = -1.0
        if self._prev_cpu_idle_total != (0, 0) and total > 0:
            p_idle, p_total = self._prev_cpu_idle_total
            d_total = total - p_total
            d_idle = idle - p_idle
            if d_total > 0:
                cpu_pct = round(100.0 * (1.0 - d_idle / d_total), 1)
        self._prev_cpu_idle_total = (idle, total)

        temp_c = _read_temp_celsius()
        throttle_bits = _read_throttled_bits()
        load1, load5, load15 = _read_load_avg()

        metrics: dict[str, Any] = {
            "timestamp_utc": _now_utc_iso(),
            "cpu_percent": cpu_pct,
            "mem_available_mb": _read_mem_available_mb(),
            "temp_c": temp_c,
            "throttled_bits": throttle_bits,
            "throttled_desc": THROTTLED_BITMASK_DESC.get(throttle_bits, "unknown"),
            "load_avg": [round(load1, 2), round(load5, 2), round(load15, 2)],
            "uptime_sec": _read_uptime_sec(),
            "peripherals": _detect_peripherals(),
            "services": _check_services(),
        }
        with self._lock:
            self._last_metrics = metrics
            self._metrics_history.append(metrics)

        # Tự động phát cảnh báo nhiệt độ
        if 0 < temp_c and temp_c > TEMP_THRESHOLD_C:
            self.events.add(
                "TEMP_HOT",
                severity="WARNING",
                details={"temp_c": temp_c, "threshold_c": TEMP_THRESHOLD_C},
            )
            if self._notify_temp_hot:
                try:
                    self._notify_temp_hot(temp_c)
                except Exception:
                    pass
        # Throttle đang xảy ra
        if throttle_bits in (2, 4, 18):
            self.events.add(
                "THROTTLED",
                severity="WARNING",
                details={"bits": throttle_bits, "desc": metrics["throttled_desc"]},
            )
        # RAM thấp
        mem_mb = metrics["mem_available_mb"]
        if 0 < mem_mb < 200:
            self.events.add(
                "MEM_LOW",
                severity="WARNING",
                details={"mem_available_mb": mem_mb},
            )
        return metrics

    def get_last_metrics(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._last_metrics)

    def get_metrics_history(self, limit: int = 30) -> list[dict[str, Any]]:
        with self._lock:
            hist = list(self._metrics_history)
        return hist[-limit:]

    # ------------------------------------------------------------------
    # TỰ PHỐI HỢP (4)
    # ------------------------------------------------------------------
    def drain_events(self) -> list[dict[str, Any]]:
        """Lấy events cần gửi lên Brain."""
        return self.events.drain()

    def send_events_to_brain(self, base_url: str, auth_headers: dict[str, str]) -> bool:
        """Gửi batch events lên PC Brain. Fail-closed: trả False, KHÔNG raise."""
        events = self.drain_events()
        if not events:
            return True  # nothing to send = success (không có việc)
        try:
            payload = json.dumps({
                "device_id": getattr(self.config, "device_id", "UNKNOWN"),
                "events": events,
            }).encode("utf-8")
            headers = dict(auth_headers)
            headers["Content-Type"] = "application/json"
            req = urllib.request.Request(
                f"{base_url}/api/executive/edge/events",
                data=payload, headers=headers, method="POST",
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status == 200
        except Exception:
            # Fail-closed: event đã bị drain — push lại đầu buffer để lần sau thử lại
            for ev in reversed(events):
                self.events._events.appendleft(ev)  # noqa: SLF001 — same module
            return False

    # ------------------------------------------------------------------
    # TỰ CẢI TIẾN CÓ KIỂM SOÁT (5)
    # ------------------------------------------------------------------
    def record_suggestion(self, kind: str, detail: dict[str, Any]) -> dict[str, Any]:
        sugg = {
            "kind": kind,
            "detail": detail,
            "timestamp_utc": _now_utc_iso(),
            "status": "PROPOSED",  # KHÔNG BAO GIỜ tự chuyển sang APPLIED
            "requires_owner_approval": True,
        }
        with self._lock:
            self._suggestions.append(sugg)
        return sugg

    def get_suggestions(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._suggestions)[-limit:]

    def run_health_check(self) -> dict[str, Any]:
        """Self-test định kỳ: metrics + ngoại vi + dịch vụ → đề xuất nếu lệch chuẩn."""
        m = self.collect_metrics()
        findings: list[dict[str, Any]] = []

        temp_c = m.get("temp_c", -1.0)
        if temp_c > TEMP_THRESHOLD_C:
            findings.append({
                "area": "thermal",
                "issue": f"CPU temp {temp_c}C vượt ngưỡng {TEMP_THRESHOLD_C}C",
                "suggestion": "Kiểm tra tản nhiệt/quạt; cân nhắc giảm tải hoặc placement",
            })
        peripherals = m.get("peripherals", {})
        if not peripherals.get("camera_dev0", False):
            findings.append({
                "area": "camera",
                "issue": "Không phát hiện /dev/video0",
                "suggestion": "Kiểm tra cáp camera ribbon/USB; chạy vcgencmd get_camera",
            })
        if peripherals.get("alsa_cards", -1) == 0:
            findings.append({
                "area": "audio",
                "issue": "Không có card ALSA nào",
                "suggestion": "Kiểm tra USB audio device; chạy aplay -l",
            })
        services = m.get("services", {})
        if not services.get("edge_daemon_alive", True):
            findings.append({
                "area": "services",
                "issue": "edge-client.service không ở trạng thái active",
                "suggestion": "Chạy: systemctl --user restart edge-client.service",
            })

        result: dict[str, Any] = {
            "timestamp_utc": _now_utc_iso(),
            "metrics": m,
            "findings": findings,
            "healthy": len(findings) == 0,
        }
        for f in findings:
            self.record_suggestion("HEALTH_FINDING", f)
            self.events.add("HEALTH_FINDING", severity="INFO", details=f)
        return result

    # ------------------------------------------------------------------
    # Background threads
    # ------------------------------------------------------------------
    def start_background_loops(self) -> None:
        """Khởi động 2 luồng nền (idempotent)."""
        if self._metrics_thread and self._metrics_thread.is_alive():
            return
        self._stop_event.clear()
        self._metrics_thread = threading.Thread(
            target=self._metrics_loop, daemon=True, name="edge-agent-metrics",
        )
        self._metrics_thread.start()
        self._health_thread = threading.Thread(
            target=self._health_loop, daemon=True, name="edge-agent-health",
        )
        self._health_thread.start()

    def stop_background_loops(self) -> None:
        self._stop_event.set()

    def _metrics_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self.collect_metrics()
            except Exception:
                pass  # fail-closed: không giết daemon vì metrics lỗi
            self._stop_event.wait(METRICS_INTERVAL_SEC)

    def _health_loop(self) -> None:
        self._stop_event.wait(10.0)  # chờ daemon ổn định 10s đầu
        while not self._stop_event.is_set():
            try:
                self.run_health_check()
            except Exception:
                pass
            self._stop_event.wait(HEALTH_CHECK_INTERVAL_SEC)

    # ------------------------------------------------------------------
    # Status tổng (cho kiosk + heartbeat telemetry)
    # ------------------------------------------------------------------
    def get_status_summary(self) -> dict[str, Any]:
        with self._lock:
            last_metrics = dict(self._last_metrics)
            n_suggestions = len(self._suggestions)
        return {
            "agent_version": "V41",
            "capabilities": [
                "AUTO_REACT", "AUTO_MANAGE", "AUTO_COLLECT",
                "AUTO_COORDINATE", "CONTROLLED_IMPROVE",
            ],
            "metrics": last_metrics,
            "suggestions_pending": n_suggestions,
            "events_buffered": len(self.events),
            "greeted_this_boot": self._greeted,
        }
