"""(11/11/2026) Test edge_pi5_reconcile — Cherry tự liên hệ Pi5 khi sống lại.
(12/11/2026) Mở rộng: deploy theo md5 (không grep), wake display, mDNS fallback,
wake_pi5() bỏ rate-limit, notify owner. 100% mock SSH/SCP/notify — không đụng
mạng thật, không gửi DM thật, không đụng data/ thật.
"""
from __future__ import annotations

import json
import socket
import sys
import time
from pathlib import Path

WS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WS))
sys.path.insert(0, str(WS / "src"))

import tools.edge_pi5_reconcile as rec


def _reset(tmp_path: Path, monkeypatch) -> None:
    """Trỏ log/state về tmp + reset rate-limit + CHẶN notify thật."""
    monkeypatch.setattr(rec, "LOG_PATH", tmp_path / "edge_reconcile_log.jsonl")
    monkeypatch.setattr(rec, "STATE_PATH", tmp_path / "edge_runtime.json")
    monkeypatch.setattr(rec, "_last_reconcile_ts", 0.0)
    rec.CONFIG["edge_host"] = "192.168.1.21"
    rec.CONFIG["notify_owner"] = False
    notified: list[str] = []

    def fake_notify(msg: str):
        notified.append(msg)
        return True, "mocked"

    monkeypatch.setattr(rec, "_notify_owner", fake_notify)
    return notified


def test_dead_to_alive_triggers_reconcile(tmp_path, monkeypatch) -> None:
    """DISCONNECTED → READY + hb mới → reconcile: ssh + md5-deploy + wake display + services + log."""
    notified = _reset(tmp_path, monkeypatch)
    rec.STATE_PATH.write_text(json.dumps({"conn_state": "DISCONNECTED"}), encoding="utf-8")

    ssh_calls: list[str] = []

    def fake_ssh(host, cmd, timeout=None):
        ssh_calls.append(cmd)
        if "hostname" in cmd:
            return 0, "Quanpt1\nup 5 minutes"
        if "md5sum" in cmd:
            return 1, ""  # file chưa có / đọc fail → remote_md5 rỗng → phải scp
        if "vcgencmd" in cmd:
            return 0, "display_power=1"
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
        "last_heartbeat_epoch": time.time() - 5,
    })

    log_lines = rec.LOG_PATH.read_text(encoding="utf-8").splitlines()
    assert log_lines, "phải ghi log reconcile"
    event = json.loads(log_lines[-1])
    assert event["verdict"] == "RECONCILED"
    steps = {s["step"]: s for s in event["steps"]}
    assert steps["deploy_wake_cherry"]["ok"] is True  # scp đã được gọi
    assert steps["wake_display"]["ok"] is True  # wake màn hình chạy
    assert event["pi_ip"] == "192.168.1.77"  # IP mới được cập nhật
    assert rec.CONFIG["edge_host"] == "192.168.1.77"
    # deploy quyết định bằng md5, không còn grep
    assert any("md5sum" in c for c in ssh_calls)
    assert not any("grep -c" in c for c in ssh_calls)
    # (12/11) owner được DM báo Pi5 sống lại
    assert notified and "SỐNG LẠI" in notified[0]


def test_deploy_skipped_when_md5_match(tmp_path, monkeypatch) -> None:
    """md5 remote == md5 local → KHÔNG scp (không đạp mạng vô ích)."""
    notified = _reset(tmp_path, monkeypatch)
    rec.STATE_PATH.write_text(json.dumps({"conn_state": "DISCONNECTED"}), encoding="utf-8")

    local_md5 = rec._md5_local()
    assert local_md5, "file wake_word_service.py phải tồn tại trong repo"
    scp_called = {"n": 0}

    def fake_ssh(host, cmd, timeout=None):
        if "hostname" in cmd:
            return 0, "Quanpt1\nup 9 minutes"
        if "md5sum" in cmd:
            return 0, f"{local_md5}  /home/quanpt1/Desktop/edge_client/wake_word_service.py"
        if "vcgencmd" in cmd:
            return 0, "display_power=1"
        if "is-enabled" in cmd:
            return 0, "enabled\nactive"
        if "wlan0" in cmd:
            return 0, "192.168.1.21"
        return 0, ""

    def fake_scp(host):
        scp_called["n"] += 1
        return True, "should not be called"

    monkeypatch.setattr(rec, "_ssh", fake_ssh)
    monkeypatch.setattr(rec, "_scp_wake_service", fake_scp)

    rec.check_edge_pi5_reconcile({
        "paired": True, "state": "READY",
        "last_heartbeat_epoch": time.time() - 4,
    })
    assert scp_called["n"] == 0, "md5 khớp thì không được scp"
    event = json.loads(rec.LOG_PATH.read_text(encoding="utf-8").splitlines()[-1])
    steps = {s["step"]: s for s in event["steps"]}
    assert "already current" in steps["deploy_wake_cherry"]["detail"]


def test_mdns_fallback_when_primary_ip_dead(tmp_path, monkeypatch) -> None:
    """IP cấu hình chết → thử mDNS quanpt1.local → SSH được + cập nhật edge_host."""
    notified = _reset(tmp_path, monkeypatch)
    rec.CONFIG["edge_host"] = "192.168.1.99"  # IP cũ đã chết
    rec.STATE_PATH.write_text(json.dumps({"conn_state": "DISCONNECTED"}), encoding="utf-8")

    monkeypatch.setattr(socket, "gethostbyname", lambda name: "192.168.1.21")

    def fake_ssh(host, cmd, timeout=None):
        if host == "192.168.1.99":
            return 255, "Connection timed out"  # IP cũ chết
        if "hostname" in cmd:
            return 0, "Quanpt1\nup 1 minute"
        if "md5sum" in cmd:
            return 1, ""
        if "vcgencmd" in cmd:
            return 0, "display_power=1"
        if "is-enabled" in cmd:
            return 0, "enabled\nactive"
        if "wlan0" in cmd:
            return 0, "192.168.1.21"
        return 0, ""

    monkeypatch.setattr(rec, "_ssh", fake_ssh)
    monkeypatch.setattr(rec, "_scp_wake_service", lambda host: (True, "deployed"))

    result = rec.reconcile_once(force=True)
    assert result["verdict"] == "RECONCILED"
    assert rec.CONFIG["edge_host"] == "192.168.1.21"
    steps = {s["step"]: s for s in result["steps"]}
    assert steps["host_resolved_via_mdns"]["ok"] is True
    assert "192.168.1.99" in steps["host_resolved_via_mdns"]["detail"]


def test_steady_alive_does_not_trigger(tmp_path, monkeypatch) -> None:
    """Đã ALIVE từ trước (conn_state=READY) → không reconcile."""
    _reset(tmp_path, monkeypatch)
    rec.STATE_PATH.write_text(json.dumps({"conn_state": "READY"}), encoding="utf-8")

    called = {"n": 0}
    monkeypatch.setattr(rec, "_ssh", lambda *a, **k: called.__setitem__("n", called["n"] + 1) or (0, ""))
    rec.check_edge_pi5_reconcile({
        "paired": True, "state": "READY",
        "last_heartbeat_epoch": time.time() - 5,
    })
    assert called["n"] == 0
    assert not rec.LOG_PATH.exists()


def test_rate_limit_blocks_second_run(tmp_path, monkeypatch) -> None:
    """2 lần transition trong <1h → lần 2 bị rate-limit (skip, không SSH)."""
    notified = _reset(tmp_path, monkeypatch)
    rec.STATE_PATH.write_text(json.dumps({"conn_state": "DISCONNECTED"}), encoding="utf-8")

    monkeypatch.setattr(rec, "_ssh", lambda *a, **k: (0, "enabled\nactive\n192.168.1.21"))
    monkeypatch.setattr(rec, "_scp_wake_service", lambda host: (True, "ok"))

    rec.check_edge_pi5_reconcile({
        "paired": True, "state": "CONNECTED",
        "last_heartbeat_epoch": time.time() - 3,
    })
    # lần 2: transition lại (giả DISCONNECTED lần nữa rồi sống)
    rec.STATE_PATH.write_text(json.dumps({"conn_state": "DISCONNECTED"}), encoding="utf-8")
    skipped = rec.reconcile_once()
    assert skipped.get("skipped") is True


def test_wake_pi5_bypasses_rate_limit(tmp_path, monkeypatch) -> None:
    """(12/11) wake_pi5() CHỦ ĐỘNG đánh thức — bỏ qua rate-limit, chạy thật."""
    notified = _reset(tmp_path, monkeypatch)
    rec.STATE_PATH.write_text(json.dumps({"conn_state": "DISCONNECTED"}), encoding="utf-8")

    monkeypatch.setattr(rec, "_ssh", lambda *a, **k: (0, "enabled\nactive\n192.168.1.21"))
    monkeypatch.setattr(rec, "_scp_wake_service", lambda host: (True, "ok"))

    # Chu kỳ 1 vừa chạy → rate-limit chặn chu kỳ 2
    rec.check_edge_pi5_reconcile({
        "paired": True, "state": "READY",
        "last_heartbeat_epoch": time.time() - 3,
    })
    skipped = rec.reconcile_once()
    assert skipped.get("skipped") is True

    # wake_pi5() vẫn phải chạy thật (force=True)
    result = rec.wake_pi5(reason="owner")
    assert result["verdict"] == "RECONCILED"
    assert result["trigger"] == "owner_wake"
    assert any(s["step"] == "wake_display" for s in result["steps"])


def test_first_run_creates_state_file_no_crash(tmp_path, monkeypatch) -> None:
    """(regression 11/11) File state chưa tồn tại → phải ghi được state, không
    nuốt NameError — nếu không reconcile sẽ không bao giờ kích hoạt."""
    _reset(tmp_path, monkeypatch)
    assert not rec.STATE_PATH.exists()  # chắc chắn chưa có
    rec.check_edge_pi5_reconcile({
        "paired": True, "state": "DISCONNECTED",
        "last_heartbeat_epoch": time.time() - 500,
    })
    assert rec.STATE_PATH.exists(), "state file phải được tạo ở lần chạy đầu"
    merged = json.loads(rec.STATE_PATH.read_text(encoding="utf-8"))
    assert merged["conn_state"] == "DISCONNECTED"


def test_unreachable_pi5_records_honest_verdict(tmp_path, monkeypatch) -> None:
    """SSH fail (cả IP lẫn mDNS) → verdict PI5_UNREACHABLE_VIA_SSH + vẫn DM owner."""
    notified = _reset(tmp_path, monkeypatch)
    rec.STATE_PATH.write_text(json.dumps({"conn_state": "DISCONNECTED"}), encoding="utf-8")
    monkeypatch.setattr(rec, "_ssh", lambda *a, **k: (255, "Connection timed out"))

    result = rec.reconcile_once(force=True)
    assert result["verdict"] == "PI5_UNREACHABLE_VIA_SSH"
    event = json.loads(rec.LOG_PATH.read_text(encoding="utf-8").splitlines()[-1])
    assert event["verdict"] == "PI5_UNREACHABLE_VIA_SSH"
    # (12/11) Pi5 unreachable → owner vẫn phải biết
    assert notified and "UNREACHABLE" in notified[0]
