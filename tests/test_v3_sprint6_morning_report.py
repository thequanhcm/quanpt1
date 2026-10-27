"""Tests — Sprint 6-GOP hạng mục (3): morning report.

Probe thật bị mock; chỉ test logic collect + format + đăng ký task.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE / "tools"))

import morning_report as mr  # noqa: E402


def test_ollama_status_offline_when_unreachable(monkeypatch):
    def boom(url, timeout=3):
        raise OSError("no")
    monkeypatch.setattr(mr.urllib.request, "urlopen", boom)
    assert "OFFLINE" in mr._ollama_status()


def test_ollama_status_online_lists_models(monkeypatch):
    class R:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return b'{"models": [{"name": "bge-m3:latest"}]}'

    monkeypatch.setattr(mr.urllib.request, "urlopen", lambda url, timeout=3: R())
    s = mr._ollama_status()
    assert "ONLINE" in s and "bge-m3" in s


def test_backup_status_honest_when_no_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(mr, "WORKSPACE", tmp_path)
    s = mr._backup_status()
    assert "CHƯA CÓ" in s  # không bịa tên file backup


def test_backup_status_lists_newest(tmp_path, monkeypatch):
    (tmp_path / "backups").mkdir()
    b = tmp_path / "backups" / "brain_20261027_010101.db"
    b.write_bytes(b"x")
    monkeypatch.setattr(mr, "WORKSPACE", tmp_path)

    class R:
        returncode = 0
        stdout = '"Ready"'

    monkeypatch.setattr(mr.subprocess, "run", lambda *a, **k: R())
    s = mr._backup_status()
    assert "brain_20261027_010101.db" in s and "Ready" in s


def test_report_contains_mandatory_honesty_when_probe_fails(monkeypatch):
    # Mọi probe lỗi → báo cáo phải nói "chưa xác minh được", không bịa trạng thái
    monkeypatch.setattr(mr, "_probe", lambda url, timeout=4: None)
    monkeypatch.setattr(mr, "_ollama_status", lambda: "🔴 OFFLINE")
    monkeypatch.setattr(mr, "_backup_status", lambda: "chưa xác minh được")
    monkeypatch.setattr(mr, "_pending_counts", lambda: (-1, -1))
    rep = mr.collect_report()
    assert "chưa xác minh được" in rep
    assert "BÁO CÁO SÁNG" in rep


def test_scheduled_task_registered():
    r = subprocess.run(
        ["schtasks", "/query", "/tn", "QUAN_AI_BRAIN_MORNING_REPORT_8AM", "/fo", "LIST"],
        capture_output=True, text=True, timeout=30,
    )
    assert r.returncode == 0
    assert "QUAN_AI_BRAIN_MORNING_REPORT_8AM" in r.stdout


def test_wrapper_bat_points_to_tool():
    bat = (WORKSPACE / "tools" / "run_morning_report.bat").read_text(encoding="utf-8", errors="replace")
    assert "morning_report.py" in bat
