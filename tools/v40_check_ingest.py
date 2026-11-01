#!/usr/bin/env python3
"""Check chính xác process ingest + chunks count."""
import subprocess

# Filter chính xác: python.exe + cmdline chứa ingest_knowledge_base
ps_cmd = (
    "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" "
    "| Where-Object { $_.CommandLine -match 'ingest_knowledge_base' } "
    "| Select-Object -ExpandProperty ProcessId"
)
r = subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True, text=True, timeout=25)
pids = [line.strip() for line in r.stdout.strip().splitlines() if line.strip().isdigit()]
print("INGEST PIDs:", pids if pids else "(KHONG CON CHAY)")

import chromadb
from chromadb.config import Settings
c = chromadb.PersistentClient(path="data/knowledge_db", settings=Settings(anonymized_telemetry=False))
col = c.get_or_create_collection("knowledge_base")
print("chunks in DB:", col.count())
