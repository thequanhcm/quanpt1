"""(11/11/2026) Test edge_pi5_reconcile — Cherry tự liên hệ Pi5 khi sống lại.

100% mock SSH/SCP — không đụng mạng thật, không đụng data/ thật.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

WS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WS))
sys.path.insert(0, str(WS / "src"))

import tools.edge_pi5_reconcile as rec


def _reset(tmp_path: Path, monkeypatch) -> None:
    """Trỏ log/state về tmp + reset rate-limit."""
    monkeypatch.setattr(rec, "LOG_PATH", tmp_path / "edge_reconcile_log.jsonl")
    monkeypatch.setattr(rec, "STATE_PATH", tmp_path / "edge_runtime.json")
    monkeypatch.setattr(rec, "_last_reconcile_ts", 0.0)
    rec.CONFIG["edge_host"] = "192.168.1.21"


def test_dead_to_alive_triggers_reconcile(tmp_path, monkeypatch) -> None:
    """DISCONNECTED → READY + hb mới → reconcile chạy: ssh probe + service check + log."""
    _reset(tmp_path, monkeypatch)
    # state trước: DISCONNECTED
    rec.STATE_PATH.write_text(json.dumps({"conn_state": "DISCONNECTED"}), encoding="utf-8")

    ssh_calls: list[str] = []

    def fake_ssh(host, cmd, timeout=None):
        ssh_calls.append(cmd)
        if cmd == "echo ok" or "hostname" in cmd:
            return 0, "pi5 up 5 minutes"
        if "grep -c" in cmd:
            return 1, "0"  # chưa có bản CHERRY → phải scp
        if "is-enabled" in cmd:
            return 0, "enabled\nactive"
        if "wlan0" in cmd:
            return 0, "192.168.1.77"
        return 0, ""

    def fake_scp(host):
        return True, "deployed"

    monkeypatch.setattr(rec, "_ssh", fake_ssh)
    monkeypatch.setattr(rec, "_scp_wake_service", fake_scp)

    rec.check_edge_pi5_reconcile({
        "paired": True, "state": "READY",
        "last_heartbeat_epoch": __import__("time").time() - 5,
    })

    log_lines = rec.LOG_PATH.read_text(encoding="utf-8").splitlines()
    assert log_lines, "phải ghi log reconcile"
    event = json.loads(log_lines[-1])
    assert event["verdict"] == "RECONCILED"
    steps = {s["step"]: s for s in event["steps"]}
    assert steps["deploy_wake_cherry"]["ok"] is True  # scp đã được gọi
    assert event["pi_ip"] == "192.168.1.77"  # IP mới được cập nhật
    assert rec.CONFIG["edge_host"] == "192.168.1.77"
    # scp được gọi vì grep trả 0
    assert any("grep -c" in c for c in ssh_calls)


def test_steady_alive_does_not_trigger(tmp_path, monkeypatch) -> None:
    """Đã ALIVE từ trước (conn_state=READY) → không reconcile."""
    _reset(tmp_path, monkeypatch)
    rec.STATE_PATH.write_text(json.dumps({"conn_state": "READY"}), encoding="utf-8")

    called = {"n": 0}
    monkeypatch.setattr(rec, "_ssh", lambda *a, **k: called.__setitem__("n", called["n"] + 1) or (0, ""))
    rec.check_edge_pi5_reconcile({
        "paired": True, "state": "READY",
        "last_heartbeat_epoch": __import__("time").time() - 5,
    })
    assert called["n"] == 0
    assert not rec.LOG_PATH.exists()


def test_rate_limit_blocks_second_run(tmp_path, monkeypatch) -> None:
    """2 lần transition trong <1h → lần 2 bị rate-limit (skip, không SSH)."""
    _reset(tmp_path, monkeypatch)
    rec.STATE_PATH.write_text(json.dumps({"conn_state": "DISCONNECTED"}), encoding="utf-8")

    monkeypatch.setattr(rec, "_ssh", lambda *a, **k: (0, "enabled\nactive\n192.168.1.21"))
    monkeypatch.setattr(rec, "_scp_wake_service", lambda host: (True, "ok"))

    rec.check_edge_pi5_reconcile({
        "paired": True, "state": "CONNECTED",
        "last_heartbeat_epoch": __import__("time").time() - 3,
    })
    # lần 2: transition lại (giả DISCONNECTED lần nữa rồi sống)
    rec.STATE_PATH.write_text(json.dumps({"conn_state": "DISCONNECTED"}), encoding="utf-8")
    skipped = rec.reconcile_once()
    assert skipped.get("skipped") is True


def test_first_run_creates_state_file_no_crash(tmp_path, monkeypatch) -> None:
    """(regression 11/11) File state chưa tồn tại → phải ghi được state, không
    nuốt NameError — nếu không reconcile sẽ không bao giờ kích hoạt."""
    _reset(tmp_path, monkeypatch)
    assert not rec.STATE_PATH.exists()  # chắc chắn chưa có
    rec.check_edge_pi5_reconcile({
        "paired": True, "state": "DISCONNECTED",
        "last_heartbeat_epoch": __import__("time").time() - 500,
    })
    assert rec.STATE_PATH.exists(), "state file phải được tạo ở lần chạy đầu"
    merged = json.loads(rec.STATE_PATH.read_text(encoding="utf-8"))
    assert merged["conn_state"] == "DISCONNECTED"


def test_unreachable_pi5_records_honest_verdict(tmp_path, monkeypatch) -> None:
    """SSH fail → verdict PI5_UNREACHABLE_VIA_SSH, không nổ tung."""
    _reset(tmp_path, monkeypatch)
    rec.STATE_PATH.write_text(json.dumps({"conn_state": "DISCONNECTED"}), encoding="utf-8")
    monkeypatch.setattr(rec, "_ssh", lambda *a, **k: (255, "Connection timed out"))

    result = rec.reconcile_once(force=True)
    assert result["verdict"] == "PI5_UNREACHABLE_VIA_SSH"
    event = json.loads(rec.LOG_PATH.read_text(encoding="utf-8").splitlines()[-1])
    assert event["verdict"] == "PI5_UNREACHABLE_VIA_SSH"
