"""Sprint 7a: Ollama check + start bằng python (thay curl/if/else cmd)."""
from __future__ import annotations

import os
import socket
import subprocess
import time
from pathlib import Path

BASE = Path(r"E:\AI\QUAN AI BRAIN")
LOG = BASE / "logs" / "khoi_dong_ollama.log"


def _ollama_up(timeout: float = 2.0) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            return s.connect_ex(("127.0.0.1", 11434)) == 0
    except Exception:
        return False


def main() -> int:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as fh:
        if _ollama_up():
            print("    OK: Ollama dang chay - bo qua")
            fh.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Ollama already up\n")
            return 0
        exe = Path(r"E:\AI\Ollama\ollama.exe")
        if not exe.exists():
            print("    CANH BAO: khong thay ollama.exe - bo qua")
            fh.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ollama.exe missing\n")
            return 0
        DETACHED = 0x00000008
        subprocess.Popen(
            [str(exe), "serve"],
            stdout=open(LOG, "a", encoding="utf-8"),
            stderr=subprocess.STDOUT,
            creationflags=DETACHED,
            cwd=str(BASE),
        )
        for _ in range(10):  # đợi tối đa 10s
            time.sleep(1)
            if _ollama_up():
                print("    OK: Ollama da khoi dong (port 11434)")
                fh.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Ollama started\n")
                return 0
        print("    CANH BAO: Ollama chua len port sau 10s - bo qua (fail-safe)")
        fh.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Ollama start timeout\n")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
