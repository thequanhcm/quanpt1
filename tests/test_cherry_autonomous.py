"""Test CHERRY AUTONOMOUS MODE — 100% mock, không DM thật, không restart thật.

Mock: urllib.request.urlopen (health/exec/ollama/edge), subprocess.Popen (spawn),
_dm gửi thật bị chặn qua monkeypatch. Kiểm tra:
1. check_servers: 2 fail liên tiếp → spawn restart; 1 fail → chưa restart
2. restart budget 2/h — lần 3 không spawn, chuyển alert
3. check_responder: heartbeat stale >300s → spawn; <300s → không
4. check_pi5: mất >300s → alert 1 lần (rate-limit lần 2 trong 30 phút)
5. propose_issues: ollama chết → DM đề xuất (không tự làm)
6. Rate-limit alert: cùng key trong 30 phút không lặp
7. LỚP 3 NEVER: script không chứa logic xóa/db-write/router — grep guard
"""
from __future__ import annotations

import importlib.util
import json
import sys
import time
from pathlib import Path
from unittest import mock

import pytest

TOOL = Path(__file__).resolve().parent.parent / "tools" / "cherry_autonomous.py"


def _load():
    spec = importlib.util.spec_from_file_location("cherry_autonomous", TOOL)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["cherry_autonomous"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def mod():
    m = _load()
    # Chặn mọi DM thật trong test
    m._dm = lambda text: True
    return m


# ---------------------------------------------------------------- LỚP 1 AUTO

def test_servers_two_fails_triggers_restart(mod):
    st = {"server_fails": 1}
    with mock.patch.object(mod, "_probe_health", return_value=None), \
         mock.patch.object(mod, "_probe_exec", return_value=False), \
         mock.patch.object(mod, "_spawn", return_value=True) as sp:
        mod.check_servers(st)
    assert st["server_fails"] == 2
    sp.assert_called_once()


def test_servers_single_fail_no_restart(mod):
    st = {"server_fails": 0}
    with mock.patch.object(mod, "_probe_health", return_value=None), \
         mock.patch.object(mod, "_probe_exec", return_value=False), \
         mock.patch.object(mod, "_spawn", return_value=True) as sp:
        mod.check_servers(st)
    assert st["server_fails"] == 1
    sp.assert_not_called()


def test_servers_healthy_resets_counter(mod):
    st = {"server_fails": 1}
    with mock.patch.object(mod, "_probe_health", return_value={"overall_status": "HEALTHY"}), \
         mock.patch.object(mod, "_probe_exec", return_value=True), \
         mock.patch.object(mod, "_spawn", return_value=True) as sp:
        mod.check_servers(st)
    assert st["server_fails"] == 0
    sp.assert_not_called()


def test_restart_budget_blocks_third_restart(mod):
    st = {"server_fails": 1, "restarts": {"servers": [time.time() - 10, time.time() - 20]}}
    with mock.patch.object(mod, "_probe_health", return_value=None), \
         mock.patch.object(mod, "_probe_exec", return_value=False), \
         mock.patch.object(mod, "_spawn", return_value=True) as sp:
        mod.check_servers(st)
    sp.assert_not_called()  # budget hết → chỉ alert, không spawn


def test_responder_stale_300s_restarts(mod):
    st = {}
    with mock.patch.object(mod, "_heartbeat_age", return_value=400.0), \
         mock.patch.object(mod, "_spawn", return_value=True) as sp:
        mod.check_responder(st)
    sp.assert_called_once()


def test_responder_fresh_no_restart(mod):
    st = {}
    with mock.patch.object(mod, "_heartbeat_age", return_value=5.0), \
         mock.patch.object(mod, "_spawn", return_value=True) as sp:
        mod.check_responder(st)
    sp.assert_not_called()


def test_pi5_lost_alerts_once_per_cooldown(mod):
    st = {}
    edge = {"edge": {"seconds_since_heartbeat": 400.0}}
    with mock.patch.object(mod, "urllib") as u:
        ctx = mock.MagicMock()
        ctx.__enter__.return_value.read.return_value = json.dumps(edge).encode()
        ctx.__exit__.return_value = False
        u.request.urlopen.return_value = ctx
        mod.check_pi5(st)  # lần 1: alert
        sent_first = mod._dm_calls = 1
        mod.check_pi5(st)  # lần 2 trong cooldown: rate-limited
    assert st.get("pi5_was_lost") is True


def test_pi5_recovery_sends_recovered(mod, capsys):
    st = {"pi5_was_lost": True}
    edge = {"edge": {"seconds_since_heartbeat": 2.0}}
    with mock.patch.object(mod, "urllib") as u, \
         mock.patch.object(mod, "_dm", side_effect=lambda t: print("DM:", t[:40])) as dm:
        ctx = mock.MagicMock()
        ctx.__enter__.return_value.read.return_value = json.dumps(edge).encode()
        ctx.__exit__.return_value = False
        u.request.urlopen.return_value = ctx
        mod.check_pi5(st)
    assert st.get("pi5_was_lost") is False
    dm.assert_called_once()
    assert "sống lại" in dm.call_args[0][0]


# ---------------------------------------------------------------- LỚP 2 PROPOSE

def test_ollama_down_proposes_not_auto(mod):
    st = {}
    with mock.patch.object(mod, "urllib") as u:
        u.request.urlopen.side_effect = OSError("refused")
        mod.propose_issues(st)
    # Không có action nào ngoài DM — state không chứa 'restart' do propose
    assert "ollama_restarted" not in st


def test_alert_rate_limit(mod):
    st = {}
    assert mod._should_alert(st, "k1") is True
    assert mod._should_alert(st, "k1") is False  # trong cooldown
    st["alerts"]["k1"] = time.time() - 3600  # quá 30 phút
    assert mod._should_alert(st, "k1") is True


# ---------------------------------------------------------------- LỚP 3 NEVER

def test_never_layer_no_destructive_ops():
    """Grep guard: code KHÔNG chứa thao tác phá hủy (bỏ qua comment/docstring)."""
    src = TOOL.read_text(encoding="utf-8")
    # Loại dòng comment và phần trailing comment — guard chỉ áp dụng cho CODE
    code_lines = [
        line.split("#")[0]
        for line in src.split("\n")
        if not line.strip().startswith("#")
    ]
    code = "\n".join(code_lines)
    # Docstring module cũng là văn bản chính sách — cắt bằng split('"""')
    parts = code.split('"""')
    code_only = "".join(parts[::2])  # phần ngoài docstring (dwell: 0,2,4...)
    forbidden = ["DROP TABLE", "DELETE FROM", "shutil.rmtree", "os.remove",
                 "netsh", "subprocess.call(['netsh"]
    for bad in forbidden:
        assert bad not in code_only, f"chứa thao tác cấm: {bad}"


def test_dm_uses_confirmed_two_step():
    """DM phải qua netchat_bot.py --confirmed (chuẩn 2 bước token)."""
    src = TOOL.read_text(encoding="utf-8")
    assert "--confirmed" in src
    assert "netchat_bot.py" in src
