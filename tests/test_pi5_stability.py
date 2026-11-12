# -*- coding: utf-8 -*-
"""Test Pi5 stability — 100% mock (không SSH thật, không gửi DM thật)."""
import json
import socket
import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE / "tools"))

import pi5_monitor
import pi5_stability_deploy


def test_probe_alive(monkeypatch):
    def fake_connect(host, port):
        s = socket.socket(); s.settimeout(0.1); return s
    monkeypatch.setattr(socket, "socket", lambda *a, **k: _FakeSocket(connect_ok=True))
    p = pi5_monitor.probe()
    assert p["alive"] is True
    assert p["host"] in pi5_monitor.PI5_HOSTS


def test_probe_dead(monkeypatch):
    monkeypatch.setattr(socket, "socket", lambda *a, **k: _FakeSocket(connect_ok=False))
    p = pi5_monitor.probe()
    assert p["alive"] is False
    assert p["reason"] == "all_hosts_unreachable"


class _FakeSocket:
    def __init__(self, *a, **k): self.connect_ok = k.get("connect_ok", True)
    def settimeout(self, t): pass
    def connect(self, addr): 
        if not self.connect_ok: raise socket.timeout()
    def close(self): pass


def test_should_dm_first_time():
    s = {"last_dm_state": None, "last_dm_utc": None}
    assert pi5_monitor.should_dm(s, "lost") is True


def test_should_dm_cooldown():
    from datetime import datetime, timezone, timedelta
    s = {"last_dm_state": "lost", "last_dm_utc": (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()}
    assert pi5_monitor.should_dm(s, "lost") is False  # < 30 phút
    s["last_dm_utc"] = (datetime.now(timezone.utc) - timedelta(minutes=31)).isoformat()
    assert pi5_monitor.should_dm(s, "lost") is True


def test_run_once_lost_then_notify(monkeypatch, tmp_path):
    monkeypatch.setattr(pi5_monitor, "STATE_PATH", tmp_path / "state.json")
    monkeypatch.setattr(pi5_monitor, "LOG_PATH", tmp_path / "log.txt")
    monkeypatch.setattr(socket, "socket", lambda *a, **k: _FakeSocket(connect_ok=False))
    monkeypatch.setattr(pi5_monitor, "notify_owner", lambda m: True)
    out = pi5_monitor.run_once(notify=True)
    assert out["probe"]["alive"] is False
    assert (tmp_path / "state.json").exists()
    state = json.loads((tmp_path / "state.json").read_text())
    assert state["consecutive_lost_probes"] >= 1


def test_run_once_recovered_dm(monkeypatch, tmp_path):
    monkeypatch.setattr(pi5_monitor, "STATE_PATH", tmp_path / "state.json")
    monkeypatch.setattr(pi5_monitor, "LOG_PATH", tmp_path / "log.txt")
    monkeypatch.setattr(socket, "socket", lambda *a, **k: _FakeSocket(connect_ok=True))
    sent = []
    monkeypatch.setattr(pi5_monitor, "notify_owner", lambda m: sent.append(m) or True)
    # State trước: đã mất
    (tmp_path / "state.json").write_text(json.dumps({
        "last_seen_utc": None, "last_lost_utc": "2026-11-12T05:00:00+00:00",
        "last_dm_state": None, "last_dm_utc": None, "consecutive_lost_probes": 5}))
    out = pi5_monitor.run_once(notify=True)
    assert out["probe"]["alive"] is True
    assert any("SỐNG LẠI" in m for m in sent)


def test_deploy_dry_run():
    out = pi5_stability_deploy.deploy(dry=True)
    statuses = [r["status"] for r in out["results"]]
    assert "WOULD_DEPLOY" in statuses
    assert all("md5" in r for r in out["results"])


def test_deploy_skip_match(monkeypatch):
    # Mock md5_remote trả về cùng md5 local → SKIP_MATCH (KHÔNG gọi SSH thật)
    monkeypatch.setattr(pi5_stability_deploy, "md5_remote", lambda h, p: pi5_stability_deploy.md5_local(WORKSPACE / "edge_client/pi5_stability/wifi_watchdog.sh"))
    # Mock subprocess.run cho phần enable/start timer (Pi5 đang mất)
    import subprocess as sp
    monkeypatch.setattr(sp, "run", lambda *a, **k: sp.CompletedProcess(a, 0, "", ""))
    out = pi5_stability_deploy.deploy(dry=False)
    assert any(r["status"] == "SKIP_MATCH" for r in out["results"] if "file" in r)
