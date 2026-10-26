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
    "server_script": os.path.join(BASE_DIR, "src", "quan_ai_brain", "web", "server.py"),
    "venv_python": r"C:\Users\DELL\.venv\Scripts\python.exe",
    "workdir": BASE_DIR,
    "port": 8765,
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


# ---------------------------------------------------------------------------
# Sprint A-fix (GAP-R3): extended component monitoring with circuit breaker
# ---------------------------------------------------------------------------

CONFIG.setdefault("ollama_port", 11434)
CONFIG.setdefault("netchat_responder_log", os.path.join(BASE_DIR, "logs", "netchat_responder.log"))
CONFIG.setdefault("disk_free_min_percent", 10.0)
CONFIG.setdefault("max_component_fail_streak", 3)  # circuit breaker threshold

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


def check_disk_space() -> bool:
    """GAP-R3: workspace drive free-space guard (fail before DB corruption)."""
    try:
        usage = os.disk_usage(BASE_DIR)
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


def start_server() -> Optional[subprocess.Popen]:
    """Start the web server."""
    try:
        logger.info(f"Starting server on port {CONFIG['port']}...")
        process = subprocess.Popen(
            [CONFIG["venv_python"], CONFIG["server_script"]],
            cwd=CONFIG["workdir"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        logger.info(f"Server started (PID: {process.pid})")
        return process
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        return None


def stop_server(process: Optional[subprocess.Popen]) -> None:
    """Stop the server process."""
    if process:
        try:
            logger.info(f"Stopping server (PID: {process.pid})...")
            process.terminate()
            process.wait(timeout=10)
            logger.info("Server stopped")
        except Exception as e:
            logger.error(f"Failed to stop server: {e}")
            try:
                process.kill()
            except:
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
            # for components we don't own — Ollama/NetChat/disk are monitored
            # and alerted, never blindly restarted — GAP-R3 policy).
            check_ollama()
            check_netchat_bot()
            check_disk_space()

            # Check if server is running
            if is_server_running():
                logger.debug("Server is healthy")
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