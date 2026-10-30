"""Start BOTH QUAN AI BRAIN servers with NETMIND_EXTERNAL_DATA_ALLOWED=true.

- Port 8765: Local Web UI Dashboard (chat, memories, plans)
- Port 8766: Executive Command Center (persona, consultation, NetChat tab)

Run each in its own thread and block forever. Use start_server_fixed.py if
only the 8765 dashboard is needed.
"""
import os
import sys
import threading
import time

# (29/10/2026) pythonw windowless mode: sys.stdout là None dưới pythonw.exe —
# print() sẽ crash. Redirect ra log file.
if sys.stdout is None or sys.stderr is None:
    _LOG_DIR = __import__("pathlib").Path(__file__).resolve().parent.parent / "logs"
    try:
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        sys.stdout = open(_LOG_DIR / "dual_servers_stdout.log", "a", buffering=1, encoding="utf-8", errors="replace")
        sys.stderr = sys.stdout
    except Exception:
        pass

# (29/10/2026) pythonw: không còn console cha — các subprocess con (vd
# netchat_bridge gọi skill script khi mở tab NetChat trên dashboard) sẽ tạo
# cửa sổ console riêng → nháy. Patch toàn bộ subprocess.run của process này.
import subprocess as _subprocess

_orig_subprocess_run = _subprocess.run

def _subprocess_run_no_window(*args, **kwargs):
    kwargs.setdefault("creationflags", getattr(_subprocess, "CREATE_NO_WINDOW", 0))
    return _orig_subprocess_run(*args, **kwargs)

_subprocess.run = _subprocess_run_no_window
os.environ["NETMIND_EXTERNAL_DATA_ALLOWED"] = "true"

from quan_ai_brain.web.server import run_web_server, run_executive_server  # noqa: E402


def main() -> None:
    t5 = threading.Thread(target=run_web_server, kwargs={"port": 8765, "open_browser": False}, daemon=True)
    t6 = threading.Thread(target=run_executive_server, kwargs={"port": 8766, "open_browser": False}, daemon=True)
    t5.start()
    time.sleep(1.0)
    t6.start()
    print("[start_dual_servers] Both servers running: 8765 (UI) + 8766 (Executive). Ctrl+C to stop.")
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        print("[start_dual_servers] Stopping.")


if __name__ == "__main__":
    main()
