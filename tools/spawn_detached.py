# -*- coding: utf-8 -*-
"""Spawn process detached — workaround Windows CMD `start` quirk spawn 2 process.

Usage:
    python tools/spawn_detached.py <pythonw_path> <script_path> [args...]

Dùng subprocess.Popen với DETACHED_PROCESS + CREATE_NEW_PROCESS_GROUP để
process con KHÔNG bị Windows CMD tìm thêm trong PATH.
"""
import subprocess, sys
from pathlib import Path

if len(sys.argv) < 3:
    print("Usage: spawn_detached.py <pythonw> <script> [args...]")
    sys.exit(1)

pythonw = Path(sys.argv[1]).resolve()
script = Path(sys.argv[2]).resolve()
args = sys.argv[3:]

if not pythonw.exists():
    print(f"pythonw not found: {pythonw}")
    sys.exit(1)

DETACHED_PROCESS = 0x00000008
CREATE_NEW_PROCESS_GROUP = 0x00000200
CREATE_NO_WINDOW = 0x08000000

flags = DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW

p = subprocess.Popen(
    [str(pythonw), str(script)] + args,
    cwd=str(script.parent.parent),
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    stdin=subprocess.DEVNULL,
    creationflags=flags,
    close_fds=True,
)
print(f"spawned PID={p.pid}: {script.name}")
