"""(11/11/2026, COG-0) Test watchdog check_daily_backup — guard backup 2AM.

Bối cảnh: Task Scheduler QUAN_AI_BRAIN_BACKUP_2AM chạy "Interactive only" bị
Windows từ chối khi máy khóa (0x800710E0) → mất backup đêm 10-11. Watchdog
24/7 giờ sở hữu backup: đúng giờ máy, 1 lần/ngày, retry bounded, fail-honest.
100% tmp_path + mock — không đụng backups/ thật.
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

WS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WS))
sys.path.insert(0, str(WS / "src"))

import tools.watchdog as wd


def _fake_backup_main(calls: dict, result: bool):
    def fake_main():
        calls["n"] += 1
        return result

    return fake_main


def test_backup_skips_outside_configured_hour(tmp_path, monkeypatch) -> None:
    """Ngoài giờ backup → không chạy, không ghi marker."""
    monkeypatch.setitem(wd.CONFIG, "log_dir", str(tmp_path))
    monkeypatch.setitem(wd.CONFIG, "daily_backup_hour", 2)
    marker = tmp_path / "daily_backup_last.txt"

    fake_now = datetime(2026, 11, 11, 15, 0, 0)  # 15h — không phải 2AM

    class DT(datetime):
        @classmethod
        def now(cls, tz=None):
            return fake_now

    calls = {"n": 0}
    fake_main = _fake_backup_main(calls, True)
    with patch.object(wd, "datetime", DT), patch.dict(
        sys.modules, {"tools.backup_database": type(sys)("tools.backup_database")}
    ), patch("tools.backup_database.main", fake_main, create=True):
        wd.check_daily_backup()
    assert calls["n"] == 0, "ngoài giờ không được chạy backup"
    assert not marker.exists()


def test_backup_runs_at_configured_hour_and_marks_done(tmp_path, monkeypatch) -> None:
    """Đúng 2AM → chạy backup OK → ghi marker theo ngày, lần sau skip."""
    monkeypatch.setitem(wd.CONFIG, "log_dir", str(tmp_path))
    monkeypatch.setitem(wd.CONFIG, "daily_backup_hour", 2)
    marker = tmp_path / "daily_backup_last.txt"

    fake_now = datetime(2026, 11, 12, 2, 0, 5)  # 2:00 AM

    class DT(datetime):
        @classmethod
        def now(cls, tz=None):
            return fake_now

    calls = {"n": 0}
    fake_main = _fake_backup_main(calls, True)
    with patch.object(wd, "datetime", DT), patch.dict(
        sys.modules, {"tools.backup_database": type(sys)("tools.backup_database")}
    ), patch("tools.backup_database.main", fake_main, create=True):
        wd.check_daily_backup()
        assert calls["n"] == 1
        assert marker.read_text(encoding="utf-8").strip() == "2026-11-12"
        # Chạy lại ngay trong cùng ngày → skip (kể cả Task Scheduler đã chạy)
        wd.check_daily_backup()
        assert calls["n"] == 1, "cùng ngày phải skip"


def test_backup_failure_does_not_mark_done(tmp_path, monkeypatch) -> None:
    """Backup fail liên tục → retry đúng max_attempts, KHÔNG ghi marker."""
    monkeypatch.setitem(wd.CONFIG, "log_dir", str(tmp_path))
    monkeypatch.setitem(wd.CONFIG, "daily_backup_hour", 2)
    monkeypatch.setitem(wd.CONFIG, "daily_backup_max_attempts", 2)
    marker = tmp_path / "daily_backup_last.txt"

    fake_now = datetime(2026, 11, 12, 2, 10, 0)

    class DT(datetime):
        @classmethod
        def now(cls, tz=None):
            return fake_now

    calls = {"n": 0}
    fake_main = _fake_backup_main(calls, False)  # luôn fail
    with patch.object(wd, "datetime", DT), patch.dict(
        sys.modules, {"tools.backup_database": type(sys)("tools.backup_database")}
    ), patch("tools.backup_database.main", fake_main, create=True):
        wd.check_daily_backup()
    assert calls["n"] == 2, "phải retry đúng max_attempts"
    assert not marker.exists(), "fail thì không ghi marker"


def test_backup_marker_from_task_scheduler_respected(tmp_path, monkeypatch) -> None:
    """Marker hôm nay có sẵn (Task Scheduler chạy được) → watchdog skip."""
    monkeypatch.setitem(wd.CONFIG, "log_dir", str(tmp_path))
    monkeypatch.setitem(wd.CONFIG, "daily_backup_hour", 2)
    marker = tmp_path / "daily_backup_last.txt"
    marker.write_text(datetime.now().strftime("%Y-%m-%d"), encoding="utf-8")

    calls = {"n": 0}
    fake_main = _fake_backup_main(calls, True)
    with patch.dict(
        sys.modules, {"tools.backup_database": type(sys)("tools.backup_database")}
    ), patch("tools.backup_database.main", fake_main, create=True):
        wd.check_daily_backup()
    assert calls["n"] == 0, "đã có backup hôm nay thì không chạy lại"
