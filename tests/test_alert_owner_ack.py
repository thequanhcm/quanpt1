"""Test owner-ACK: cảnh báo owner đã xác nhận → không gửi DM lại (03/11/2026).

Sự việc: owner nhắn "anh đã biết, tắt hết cảnh báo này" sau 10 tin spam
(pc_host ram CRITICAL/WARNING + selfcare pi5 connectivity CRITICAL, 00:58–01:27).
ACK phải chặn gửi ở TẤT CẢ mức severity (WARNING lẫn CRITICAL), vẫn ghi DB audit.
"""
from __future__ import annotations

import json

import pytest

from quan_ai_brain.monitoring.alert_engine import (
    AlertEngine,
    load_owner_acks,
    save_owner_ack,
)
from quan_ai_brain.monitoring.health_state import CRITICAL, WARNING


class _SpySender:
    def __init__(self):
        self.sent: list[str] = []

    def __call__(self, message: str) -> dict:
        self.sent.append(message)
        return {"success": True}


@pytest.fixture()
def engine(tmp_path):
    spy = _SpySender()
    eng = AlertEngine(tmp_path, cooldown_sec=0.0, sender=spy)
    return eng, spy


def test_ack_blocks_ram_warning_and_critical(tmp_path, engine):
    eng, spy = engine
    save_owner_ack(tmp_path, "ram_percent", reason="owner 03/11: anh đã biết, tắt hết")
    checks = {"ram_percent": {"value": 96.5, "status": "measured"}}
    out = eng.evaluate_checks("pc_host", checks, {"ram_percent": (">=85", ">=95")})
    assert spy.sent == []  # không gửi DM
    assert out == []  # không vào danh sách alert active
    # vẫn ghi DB để audit
    recent = eng.recent_alerts(limit=5)
    assert any(r["check_id"] == "pc_host:ram_percent" and r["sent"] == 0 for r in recent)


def test_ack_covers_both_severities(tmp_path, engine):
    eng, spy = engine
    save_owner_ack(tmp_path, "selfcare:pi5:connectivity", reason="owner ack")
    pseudo = {"selfcare:pi5:connectivity": {"value": 2, "status": "measured"}}
    rules = {"selfcare:pi5:connectivity": (">=1", ">=2")}
    # value=2 → CRITICAL
    eng.evaluate_checks("selfcare_engine", dict(pseudo), dict(rules))
    # value=1 → WARNING (cùng check_id, cùng ack)
    eng.evaluate_checks("selfcare_engine", {"selfcare:pi5:connectivity": {"value": 1}}, dict(rules))
    assert spy.sent == []
    recent = eng.recent_alerts(limit=10)
    assert sum(1 for r in recent if r["suppressed_reason"] == "owner_ack") >= 2


def test_unacked_alerts_still_send(tmp_path, engine):
    eng, spy = engine
    save_owner_ack(tmp_path, "ram_percent", reason="only ram")
    checks = {
        "ram_percent": {"value": 96.0, "status": "measured"},
        "disk_percent": {"value": 99.0, "status": "measured"},
    }
    eng.evaluate_checks("pc_host", checks, {"ram_percent": (">=85", ">=95"), "disk_percent": (">=90", ">=95")})
    assert len(spy.sent) == 1  # chỉ disk gửi, ram bị ack chặn
    assert "ổ đĩa" in spy.sent[0]  # VN-LANG: disk_percent → ổ đĩa


def test_load_owner_acks_returns_reasons(tmp_path):
    save_owner_ack(tmp_path, "x", reason="lý do test")
    acks = load_owner_acks(tmp_path)
    assert "x" in acks
    assert acks["x"]["reason"] == "lý do test"
