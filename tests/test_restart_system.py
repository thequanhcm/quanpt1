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
    # (30/10/2026) Launcher chuẩn hiện tại là TONY_START.bat; bat cũ
    # KHOI_DONG_QUAN_AI_BRAIN.bat đã bị xóa trong cleanup b63d62d.
    assert (WORKSPACE_ROOT / "TONY_START.bat").exists() or (
        WORKSPACE_ROOT / "KHOI_DONG_QUAN_AI_BRAIN.bat"
    ).exists()
    assert (
        (WORKSPACE_ROOT / "TU_DONG_KHOI_DONG_LAI_HE_THONG.bat").exists()
        or (WORKSPACE_ROOT / "tools" / "legacy_launchers" / "TU_DONG_KHOI_DONG_LAI_HE_THONG.bat").exists()
    )
    assert (
        (WORKSPACE_ROOT / "RESTART_SYSTEM.bat").exists()
        or (WORKSPACE_ROOT / "tools" / "legacy_launchers" / "RESTART_SYSTEM.bat").exists()
    )


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
