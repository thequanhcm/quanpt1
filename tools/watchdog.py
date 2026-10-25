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