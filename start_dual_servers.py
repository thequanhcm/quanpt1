"""Start BOTH QUAN AI BRAIN servers with NETMIND_EXTERNAL_DATA_ALLOWED=true.

- Port 8765: Local Web UI Dashboard (chat, memories, plans)
- Port 8766: Executive Command Center (persona, consultation, NetChat tab)

Run each in its own thread and block forever. Use start_server_fixed.py if
only the 8765 dashboard is needed.
"""
import os
import threading
import time

# Set env var BEFORE importing server
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
