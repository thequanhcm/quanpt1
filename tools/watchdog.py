"""QUAN AI BRAIN 24/7 Watchdog - Auto-restart on crash.

Usage (Windows):
    1. Install NSSM: https://nssm.cc/download
    2. nssm install QUAN_AIBRAIN "C:\\Users\\DELL\\.venv\\Scripts\\python.exe" "E:\\AI\\QUAN AI BRAIN\\tools\\watchdog.py"
    3. nssm start QUAN_AIBRAIN
    4. nssm set QUAN_AIBRAIN Start SERVICE_AUTO_START

Features:
- Monitor web server (port 8765)
- Auto-restart on crash (max 5 restarts/hour)
- Log rotation (daily, keep 30 days)
- Health check every 60s
- Alert on repeated failures
"""
import logging
import os
import shutil
import socket
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

# Configuration - use raw strings for Windows paths
BASE_DIR = r"E:\AI\QUAN AI BRAIN"
CONFIG = {
    # 24/7 reboot-proof (27/10/2026): watchdog now supervises BOTH servers via
    # start_dual_servers.py (8765 UI + 8766 Executive) using the project venv.
    # The previous venv_python pointed to C:\Users\DELL\.venv which does NOT
    # exist — auto-restart would have failed silently forever.
    "server_script": os.path.join(BASE_DIR, "start_dual_servers.py"),
    "venv_python": os.path.join(BASE_DIR, ".venv", "Scripts", "python.exe"),
    "workdir": BASE_DIR,
    "port": 8765,
    "second_port": 8766,
    "health_check_interval": 60,
    "max_restart_per_hour": 5,
    "log_dir": os.path.join(BASE_DIR, "logs"),
    "log_retention_days": 30,
}

# Setup logging
log_dir = Path(CONFIG["log_dir"])
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_dir / "watchdog.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("watchdog")


def rotate_logs() -> None:
    """Rotate logs older than retention period."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=CONFIG["log_retention_days"])
    for log_file in log_dir.glob("*.log"):
        mtime = datetime.fromtimestamp(log_file.stat().st_mtime, tz=timezone.utc)
        if mtime < cutoff:
            try:
                log_file.unlink()
                logger.info(f"Deleted old log: {log_file.name}")
            except Exception as e:
                logger.warning(f"Failed to delete {log_file.name}: {e}")


def is_server_running(port: int = CONFIG["port"]) -> bool:
    """Check if server is listening on port."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2)
            result = s.connect_ex(("127.0.0.1", port))
            return result == 0
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return False


def both_servers_healthy() -> bool:
    """24/7 reboot-proof: dual server is healthy only when BOTH ports answer."""
    return is_server_running(CONFIG["port"]) and is_server_running(CONFIG["second_port"])


# ---------------------------------------------------------------------------
# Sprint A-fix (GAP-R3): extended component monitoring with circuit breaker
# ---------------------------------------------------------------------------

CONFIG.setdefault("ollama_port", 11434)
CONFIG.setdefault("netchat_responder_log", os.path.join(BASE_DIR, "logs", "netchat_responder_heartbeat.log"))
CONFIG.setdefault("learning_daemon_log", os.path.join(BASE_DIR, "logs", "learning_daemon.log"))
CONFIG.setdefault("disk_free_min_percent", 10.0)
CONFIG.setdefault("max_component_fail_streak", 3)  # circuit breaker threshold
CONFIG.setdefault("max_daemon_restart_per_hour", 5)  # Sprint 7 (b): cap giống server

_component_fail_streaks: dict[str, int] = {}
_component_states: dict[str, str] = {}  # component_id -> HEALTHY|DEGRADED|OFFLINE


def _probe_tcp(port: int, timeout: float = 2.0) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            return s.connect_ex(("127.0.0.1", port)) == 0
    except Exception:
        return False


def _update_component_state(component_id: str, alive: bool) -> str:
    """Update per-component circuit breaker. Returns the new state.

    alive probe fails <max_component_fail_streak> consecutive times -> DEGRADED
    (still possibly transient); >= threshold -> OFFLINE. Recovery resets to
    HEALTHY only on a passing probe — never on configuration or hope.
    """
    streak = _component_fail_streaks.get(component_id, 0)
    if alive:
        _component_fail_streaks[component_id] = 0
        state = "HEALTHY"
    else:
        _component_fail_streaks[component_id] = streak + 1
        if streak + 1 >= CONFIG["max_component_fail_streak"]:
            state = "OFFLINE"
        else:
            state = "DEGRADED"
    _component_states[component_id] = state
    return state


def check_ollama() -> bool:
    """GAP-R1 visibility: probe local Ollama daemon; circuit-broken alerts."""
    alive = _probe_tcp(CONFIG["ollama_port"])
    state = _update_component_state("ollama", alive)
    if state != _component_states.get("ollama_prev", state):
        logger.info(f"Ollama state changed: {state}")
    _component_states["ollama_prev"] = state
    if not alive:
        logger.warning(f"Ollama port {CONFIG['ollama_port']} not responding (state={state})")
    return alive


def check_netchat_bot() -> bool:
    """GAP-R3: NetChat auto-responder liveness via heartbeat freshness in its log."""
    log_path = Path(CONFIG["netchat_responder_log"])
    if not log_path.exists():
        logger.warning("NetChat responder log missing; bot may not be running")
        return _update_component_state("netchat_bot", False) == "HEALTHY"
    age_seconds = time.time() - log_path.stat().st_mtime
    # Responder polls every 5s; 10 minutes without any write means it is stuck/dead
    alive = age_seconds < 600
    state = _update_component_state("netchat_bot", alive)
    if not alive:
        logger.warning(f"NetChat responder heartbeat stale ({int(age_seconds)}s; state={state})")
    return alive


def check_learning_daemon() -> bool:
    """Sprint 7 (b): learning daemon liveness via its crash/heartbeat log.

    28/10/2026 (sửa mất đồng bộ): daemon có thể ghi vào learning_daemon.log
    (stdout redirect minimized window) HOẶC learning_daemon.py.log (stdout
    redirect của start_daemon trong watchdog) — trước đây chỉ tra 1 file nên
    daemon sống nhưng bị báo OFFLINE 12.6h. Lấy mtime MỚI NHẤT của cả hai;
    thiếu cả hai → fail-closed OFFLINE.
    """
    candidates = [
        Path(CONFIG["learning_daemon_log"]),                      # logs/learning_daemon.log
        Path(BASE_DIR) / "logs" / "learning_daemon.py.log",       # watchdog-spawned redirect
        Path(BASE_DIR) / "logs" / "learning_daemon_crash.log",
    ]
    ages = [
        time.time() - p.stat().st_mtime
        for p in candidates
        if p.exists()
    ]
    if not ages:
        # Không có log nào → không xác nhận được sự sống → OFFLINE (fail-closed)
        return _update_component_state("learning_daemon", False) == "HEALTHY"
    age_seconds = min(ages)  # file ghi gần nhất quyết định
    # Chu kỳ 300s; 15 phút không ghi gì = chết/treo
    alive = age_seconds < 900
    state = _update_component_state("learning_daemon", alive)
    if not alive:
        logger.warning(f"Learning daemon log stale ({int(age_seconds)}s; state={state})")
    return alive


def check_disk_space() -> bool:
    """GAP-R3: workspace drive free-space guard (fail before DB corruption)."""
    try:
        usage = shutil.disk_usage(BASE_DIR)
        free_percent = 100.0 * usage.free / usage.total
        ok = free_percent >= CONFIG["disk_free_min_percent"]
        if not ok:
            logger.error(
                f"LOW DISK: {free_percent:.1f}% free (< {CONFIG['disk_free_min_percent']}%). "
                "Database writes at risk; manual cleanup required."
            )
        state = _update_component_state("disk", ok)
        if state in ("OFFLINE",):
            logger.error(f"Disk guard circuit breaker OPEN (state={state})")
        return ok
    except Exception as e:
        logger.error(f"Disk check failed: {e}")
        return False


def start_daemon(script_name: str, window_title: str):
    """Sprint 7 (b): start 1 daemon em sở hữu (responder/learning) bằng venv
    python, log ra logs/<name>.log append. Trả về Popen hoặc None."""
    try:
        script_path = Path(BASE_DIR) / "tools" / script_name
        if not script_path.exists():
            logger.error(f"Daemon script missing: {script_path}")
            return None
        out_path = Path(CONFIG["log_dir"]) / f"{script_name}.log"
        out_handle = open(out_path, "a", encoding="utf-8", buffering=1)
        # (30/10/2026) FIX UTF-8 tổng lớp — như start_server() bên dưới.
        _env = dict(os.environ)
        _env["PYTHONUTF8"] = "1"
        _env["PYTHONIOENCODING"] = "utf-8"
        process = subprocess.Popen(
            [CONFIG["venv_python"], str(script_path)],
            cwd=CONFIG["workdir"],
            stdout=out_handle,
            stderr=subprocess.STDOUT,
            text=True,
            env=_env,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        _daemon_log_handles.append(out_handle)
        logger.info(f"Daemon {script_name} started (PID: {process.pid})")
        return process
    except Exception as e:
        logger.error(f"Failed to start daemon {script_name}: {e}")
        return None


_daemon_log_handles: list = []
_daemon_processes: dict[str, subprocess.Popen] = {}
_daemon_restart_times: dict[str, list[datetime]] = {}


def ensure_daemon_alive(component_id: str, script_name: str, alive: bool) -> None:
    """Sprint 7 (b): auto-restart daemon em SỞ HỮU khi chết — cap 5 lần/giờ.

    Khác policy GAP-R3 với Ollama (không sở hữu → chỉ cảnh báo): responder +
    learning là script trong tools/ của chính dự án → watchdog có quyền và
    trách nhiệm hồi phục. Restart track riêng per-daemon, đúng chuẩn server.
    """
    if alive:
        # Sống: nếu mình từng spawn mà giờ alive lại (hoặc xác nhận từ đầu)
        # → dọn handle cũ nếu process đã thoát
        proc = _daemon_processes.get(component_id)
        if proc is not None and proc.poll() is not None:
            _daemon_processes.pop(component_id, None)
        return

    now = datetime.now(timezone.utc)
    window = [t for t in _daemon_restart_times.get(component_id, []) if now - t < timedelta(hours=1)]
    if len(window) >= CONFIG["max_daemon_restart_per_hour"]:
        logger.error(
            f"Daemon {component_id}: max restart limit reached "
            f"({CONFIG['max_daemon_restart_per_hour']}/hour). Manual intervention required!"
        )
        return
    # Chưa có process ta spawn đang chạy → start mới
    proc = _daemon_processes.get(component_id)
    if proc is not None and proc.poll() is None:
        return  # process ta spawn vẫn chạy (khai báo chết sai — không đúp)
    window.append(now)
    _daemon_restart_times[component_id] = window
    new_proc = start_daemon(script_name, component_id)
    if new_proc is not None:
        _daemon_processes[component_id] = new_proc


def start_server() -> Optional[subprocess.Popen]:
    """Start the web server (dual 8765+8766).

    24/7 fix (27/10/2026): stdout/stderr were subprocess.PIPE and never read —
    the pipe buffer (~64KB) fills with request logs and the child then BLOCKS
    on write, looking exactly like a hang. Redirect to an append log instead.
    """
    try:
        logger.info(f"Starting servers via {os.path.basename(CONFIG['server_script'])} on ports {CONFIG['port']}+{CONFIG['second_port']}...")
        out_path = Path(CONFIG["log_dir"]) / "dual_servers_watchdog.log"
        out_handle = open(out_path, "a", encoding="utf-8", buffering=1)
        # (30/10/2026) FIX UTF-8 tổng lớp: daemon windowless không có console →
        # cp1252 giết mọi print() tiếng Việt. Ép UTF-8 cho toàn bộ process con.
        _env = dict(os.environ)
        _env["PYTHONUTF8"] = "1"
        _env["PYTHONIOENCODING"] = "utf-8"
        process = subprocess.Popen(
            [CONFIG["venv_python"], CONFIG["server_script"]],
            cwd=CONFIG["workdir"],
            stdout=out_handle,
            stderr=subprocess.STDOUT,
            text=True,
            env=_env,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        _server_log_handles.append(out_handle)  # closed on stop_server
        logger.info(f"Servers started (PID: {process.pid})")
        return process
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        return None


_server_log_handles: list = []


def stop_server(process: Optional[subprocess.Popen]) -> None:
    """Stop the server process."""
    if process:
        try:
            logger.info(f"Stopping servers (PID: {process.pid})...")
            process.terminate()
            process.wait(timeout=10)
            logger.info("Servers stopped")
        except Exception as e:
            logger.error(f"Failed to stop server: {e}")
            try:
                process.kill()
            except:
                pass
    while _server_log_handles:
        try:
            _server_log_handles.pop().close()
        except Exception:
            pass


def main() -> int:
    """Main watchdog loop."""
    logger.info("=" * 60)
    logger.info("QUAN AI BRAIN Watchdog Starting")
    logger.info("=" * 60)

    # Rotate old logs
    rotate_logs()

    process: Optional[subprocess.Popen] = None
    restart_times: list[datetime] = []

    while True:
        try:
            # Sprint A-fix: extended component checks (probe-only, no restart
            # for components we don't own — Ollama/disk are monitored and
            # alerted, never blindly restarted — GAP-R3 policy).
            check_ollama()
            check_disk_space()

            # Sprint 7 (b): daemons em SỞ HỮU → auto-restart khi chết (cap 5/h)
            responder_alive = check_netchat_bot()
            ensure_daemon_alive("netchat_bot", "netchat_auto_responder.py", responder_alive)
            learning_alive = check_learning_daemon()
            ensure_daemon_alive("learning_daemon", "learning_daemon.py", learning_alive)

            # Check if server is running
            if both_servers_healthy():
                logger.debug("Servers healthy (8765 + 8766)")
            else:
                # Server is down, check restart limit
                now = datetime.now(timezone.utc)
                restart_times = [t for t in restart_times if now - t < timedelta(hours=1)]

                if len(restart_times) >= CONFIG["max_restart_per_hour"]:
                    logger.error(
                        f"Max restart limit reached ({CONFIG['max_restart_per_hour']}/hour). "
                        "Manual intervention required!"
                    )
                    time.sleep(300)
                    continue

                # Stop old process if any
                if process:
                    stop_server(process)
                    process = None

                # Start new process
                restart_times.append(now)
                process = start_server()

                if not process:
                    time.sleep(10)
                    continue

                logger.info(f"Server restarted (attempt {len(restart_times)})")

            # Wait for next check
            time.sleep(CONFIG["health_check_interval"])

        except KeyboardInterrupt:
            logger.info("Watchdog shutting down...")
            if process:
                stop_server(process)
            return 0
        except Exception as e:
            logger.error(f"Watchdog error: {e}", exc_info=True)
            time.sleep(10)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())