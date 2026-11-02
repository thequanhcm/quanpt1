"""Create or update 1-Click Master Launcher shortcut on Windows Desktop."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BAT_FILE = ROOT / "KHOI_DONG_QUAN_AI_BRAIN_ONECLICK.bat"
DESKTOP = Path(os.environ.get("USERPROFILE", "C:\\Users\\DELL")) / "Desktop"

SHORTCUT_NAMES = [
    "QUAN AI BRAIN - KHOI DONG 1-CLICK.lnk",
    "KHOI_DONG_QUAN_AI_BRAIN_ONECLICK - Shortcut.lnk",
]

def create_shortcuts() -> None:
    for name in SHORTCUT_NAMES:
        lnk_path = DESKTOP / name
        ps_script = f"""
$ws = New-Object -ComObject WScript.Shell
$sc = $ws.CreateShortcut('{str(lnk_path)}')
$sc.TargetPath = '{str(BAT_FILE)}'
$sc.WorkingDirectory = '{str(ROOT)}'
$sc.Description = 'QUAN AI BRAIN - 1-Click Master Launcher'
$sc.Save()
"""
        cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            print(f"Created shortcut: {lnk_path}")
        else:
            print(f"Error creating {lnk_path}: {res.stderr}")

if __name__ == "__main__":
    create_shortcuts()
