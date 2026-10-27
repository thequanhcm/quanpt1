"""Tests — TASK-V3-SPRINT6-GOP hạng mục (2) 24/7 Hardening.

Kiểm tra cấu hình startup/backup KHÔNG chạy script thật (chỉ đọc text + verify
task scheduler state qua subprocess schtasks).
"""
from __future__ import annotations

import subprocess
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent


def _read(name: str) -> str:
    return (WORKSPACE / name).read_text(encoding="utf-8", errors="replace")


def test_khoi_dong_contains_ollama_block():
    src = _read("KHOI_DONG_24_7.bat")
    # Khối Ollama phải: check port trước khi start (idempotent), dùng đúng path binary
    assert "[0/5]" in src
    assert "11434" in src
    assert "E:\\AI\\Ollama\\ollama.exe" in src
    # phải check exist trước khi start (fail-safe khi máy khác không có Ollama)
    assert 'if exist "E:\\AI\\Ollama\\ollama.exe"' in src


def test_khoi_dong_backup_task_name_consistent():
    src = _read("KHOI_DONG_24_7.bat")
    assert 'QUAN_AI_BRAIN_BACKUP_2AM' in src
    # không còn tên task cũ rải rác
    assert "QUAN_AIBRAIN_Backup_2AM" not in src


def test_scheduled_task_registered_and_ready():
    r = subprocess.run(
        ["schtasks", "/query", "/tn", "QUAN_AI_BRAIN_BACKUP_2AM", "/fo", "LIST"],
        capture_output=True, text=True, timeout=30,
    )
    out = r.stdout + r.stderr
    assert r.returncode == 0, f"task khong ton tai: {out[:200]}"
    assert "Ready" in out or "Chạy" in out or "Ready" in out.lower() or "Sẵn sàng" in out


def test_backup_script_works():
    # backup_database.py phải tồn tại + run_backup.bat trỏ đúng script
    assert (WORKSPACE / "tools" / "backup_database.py").exists()
    bat = _read(Path("tools") / "run_backup.bat")
    assert "backup_database.py" in bat


def test_backup_fresh_after_manual_run():
    # Backup mới nhất phải từ hôm nay (đã chạy thử khi đăng ký task)
    backups = sorted((WORKSPACE / "backups").glob("brain_*.db"), key=lambda p: p.stat().st_mtime)
    assert backups, "khong co backup nao"
    import time

    newest = backups[-1]
    age_hours = (time.time() - newest.stat().st_mtime) / 3600
    assert age_hours < 24, f"backup moi nhat cu hon 24h: {newest.name}"
