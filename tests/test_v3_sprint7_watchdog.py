"""Tests — Sprint 7 (b): watchdog mở rộng auto-restart daemon sở hữu.

Mock 100%: không spawn process thật, không đụng daemon đang chạy.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[1]


@pytest.fixture()
def wd():
    """Import tools/watchdog.py như module (không chạy main)."""
    spec = importlib.util.spec_from_file_location("watchdog_s7", WORKSPACE / "tools" / "watchdog.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["watchdog_s7"] = mod
    spec.loader.exec_module(mod)
    return mod


class TestEnsureDaemonAlive:
    def test_dead_daemon_triggers_restart(self, wd, monkeypatch):
        started = []

        class FakeProc:
            def poll(self):
                return 0  # đã thoát

        monkeypatch.setattr(wd, "start_daemon", lambda script, title: started.append(script) or FakeProc())
        wd._daemon_processes.clear()
        wd._daemon_restart_times.clear()

        wd.ensure_daemon_alive("netchat_bot", "netchat_auto_responder.py", alive=False)

        assert started == ["netchat_auto_responder.py"]

    def test_alive_daemon_no_restart(self, wd, monkeypatch):
        started = []
        monkeypatch.setattr(wd, "start_daemon", lambda script, title: started.append(script))
        wd._daemon_processes.clear()
        wd._daemon_restart_times.clear()

        wd.ensure_daemon_alive("netchat_bot", "netchat_auto_responder.py", alive=True)

        assert started == []

    def test_restart_cap_5_per_hour(self, wd, monkeypatch):
        started = []

        class FakeProc:
            def poll(self):
                return 0  # mỗi lần start là chết ngay (để restart lần kế)

        monkeypatch.setattr(wd, "start_daemon", lambda script, title: started.append(script) or FakeProc())
        wd._daemon_processes.clear()
        wd._daemon_restart_times.clear()

        for _ in range(8):  # 8 lần chết liên tiếp
            wd.ensure_daemon_alive("learning_daemon", "learning_daemon.py", alive=False)

        assert len(started) == 5  # cap 5 — 3 lần sau bị chặn

    def test_cap_resets_after_window(self, wd, monkeypatch):
        from datetime import datetime, timedelta, timezone

        started = []

        class FakeProc:
            def poll(self):
                return 0

        monkeypatch.setattr(wd, "start_daemon", lambda script, title: started.append(script) or FakeProc())
        wd._daemon_processes.clear()
        wd._daemon_restart_times.clear()

        # Giả lập 5 restart đã xảy ra 2 giờ trước (ngoài cửa sổ 1 giờ)
        old = datetime.now(timezone.utc) - timedelta(hours=2)
        wd._daemon_restart_times["netchat_bot"] = [old] * 5

        wd.ensure_daemon_alive("netchat_bot", "netchat_auto_responder.py", alive=False)
        assert len(started) == 1  # cửa sổ reset → restart được tiếp

    def test_owned_vs_foreign_policy(self, wd):
        """Ollama (không sở hữu) KHÔNG có hàm restart — chỉ probe + alert."""
        # check_ollama tồn tại nhưng không có ensure_daemon cho ollama
        assert hasattr(wd, "check_ollama")
        # Đảm bảo main loop không gọi ensure_daemon_alive("ollama", ...)
        import inspect

        src = inspect.getsource(wd.main)
        assert 'ensure_daemon_alive("ollama"' not in src


class TestCheckLearningDaemon:
    def test_missing_log_is_offline(self, wd, tmp_path, monkeypatch):
        wd.CONFIG["learning_daemon_log"] = str(tmp_path / "khongtontai.log")
        alive = wd.check_learning_daemon()
        assert alive is False

    def test_fresh_log_is_alive(self, wd, tmp_path):
        log = tmp_path / "learning_daemon.log"
        log.write_text("iteration 1", encoding="utf-8")  # mtime = bây giờ
        wd.CONFIG["learning_daemon_log"] = str(log)
        alive = wd.check_learning_daemon()
        assert alive is True

    def test_stale_log_is_dead(self, wd, tmp_path):
        import os

        log = tmp_path / "learning_daemon.log"
        log.write_text("iteration 1", encoding="utf-8")
        old_ts = __import__("time").time() - 2000  # 33 phút trước (>15 phút)
        os.utime(log, (old_ts, old_ts))
        wd.CONFIG["learning_daemon_log"] = str(log)
        alive = wd.check_learning_daemon()
        assert alive is False
