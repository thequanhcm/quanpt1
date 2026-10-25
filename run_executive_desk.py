"""Launch QUAN AI BRAIN — Executive Consultation & Management Cockpit (Port 8766)."""
from __future__ import annotations

from pathlib import Path
import sys

# Ensure src is in sys.path
root = Path(__file__).resolve().parent
src = root / "src"
if str(src) not in sys.path:
    sys.path.insert(0, str(src))

from quan_ai_brain.web.server import run_executive_server

if __name__ == "__main__":
    run_executive_server(port=8766, open_browser=True)
