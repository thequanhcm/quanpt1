"""Tests for tools/restart_system.py and system auto-restart routines."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
RESTART_TOOL = WORKSPACE_ROOT / "tools" / "restart_system.py"


def test_restart_script_exists() -> None:
    assert RESTART_TOOL.exists()
    # (23/11/2026) Manual-start chuẩn sau cleanup: KHOI_DONG_CHERRY.bat +
    # TAT_CHERRY.bat (quyết định owner 19/11 — KHÔNG auto-start).
    # Launcher cũ TONY_START / KHOI_DONG_QUAN_AI_BRAIN đã chuyển sang
    # tools/legacy_launchers/ để dự phòng.
    assert (WORKSPACE_ROOT / "KHOI_DONG_CHERRY.bat").exists(), (
        "Manual-start launcher KHOI_DONG_CHERRY.bat missing"
    )
    assert (WORKSPACE_ROOT / "TAT_CHERRY.bat").exists(), (
        "Manual-stop launcher TAT_CHERRY.bat missing"
    )
    legacy = WORKSPACE_ROOT / "tools" / "legacy_launchers"
    assert legacy.is_dir(), "legacy_launchers/ archive missing"
    # Restart-script cũ vẫn còn trong archive để rollback nếu cần
    assert (legacy / "TU_DONG_KHOI_DONG_LAI_HE_THONG.bat").exists()
    assert (legacy / "RESTART_SYSTEM.bat").exists()


def test_restart_preflight_imports() -> None:
    sys.path.insert(0, str(WORKSPACE_ROOT / "tools"))
    import restart_system  # noqa: E402

    assert restart_system.check_preflight_imports() is True


def test_restart_status_command() -> None:
    res = subprocess.run(
        [sys.executable, str(RESTART_TOOL), "--status"],
        cwd=WORKSPACE_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert res.returncode == 0
    assert "TRẠNG THÁI CÁC DỊCH VỤ CỦA QUAN AI BRAIN" in res.stdout
    assert "8766" in res.stdout


def test_cli_restart_help() -> None:
    res = subprocess.run(
        [sys.executable, "-m", "quan_ai_brain.cli", "restart", "--help"],
        cwd=WORKSPACE_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert res.returncode == 0
    assert "--target" in res.stdout
    assert "--validate" in res.stdout
