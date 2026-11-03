"""VN-LANG — chuẩn hoá tiếng Việt tầng cuối cho DM (02/11/2026, owner yêu cầu).

Mọi tin nhắn gửi owner qua AlertEngine phải ra tiếng Việt tự nhiên:
- Trạng thái/mức độ: CRITICAL → NGHIÊM TRỌNG, WARNING → CẢNH BÁO, ONLINE → HOẠT ĐỘNG…
- Component mật ngữ: pc_host → máy chính, ram_percent → RAM, connectivity → kết nối…
- Số liệu + token lạ GIỮ NGUYÊN (không biến dữ liệu kỹ thuật thành chữ khác nghĩa).
"""
from __future__ import annotations

import pytest

from quan_ai_brain.monitoring.alert_engine import AlertEngine, _vn_message
from quan_ai_brain.monitoring.health_state import CRITICAL, WARNING


class _SpySender:
    def __init__(self):
        self.sent: list[str] = []

    def __call__(self, message: str) -> dict:
        self.sent.append(message)
        return {"success": True}


def test_ram_alert_becomes_vietnamese(tmp_path):
    spy = _SpySender()
    eng = AlertEngine(tmp_path, cooldown_sec=0.0, sender=spy)
    eng.evaluate_checks("pc_host", {"ram_percent": {"value": 96.5}}, {"ram_percent": (">=85", ">=95")})
    assert len(spy.sent) == 1
    msg = spy.sent[0]
    assert "NGHIÊM TRỌNG" in msg          # CRITICAL → tiếng Việt
    assert "máy chính" in msg             # pc_host → máy chính
    assert "RAM" in msg and "96.5" in msg  # số liệu giữ nguyên
    assert "CRITICAL" not in msg          # không sót tiếng Anh mức độ
    assert "pc_host" not in msg


def test_warning_alert_becomes_vietnamese(tmp_path):
    spy = _SpySender()
    eng = AlertEngine(tmp_path, cooldown_sec=0.0, sender=spy)
    eng.evaluate_checks("pc_host", {"ram_percent": {"value": 87.9}}, {"ram_percent": (">=85", ">=95")})
    msg = spy.sent[0]
    assert "CẢNH BÁO" in msg and "87.9" in msg
    assert "WARNING" not in msg


def test_pi5_connectivity_alert_vietnamese(tmp_path):
    spy = _SpySender()
    eng = AlertEngine(tmp_path, cooldown_sec=0.0, sender=spy)
    pseudo = {"connectivity": {"value": 2, "status": "measured", "reason": "Pi 5 disconnected"}}
    eng.evaluate_checks("pi5_edge", pseudo, {"connectivity": (">=1", ">=2")})
    msg = spy.sent[0]
    assert "MẤT KẾT NỐI" in msg or "NGHIÊM TRỌNG" in msg
    assert "kết nối" in msg
    assert "Pi 5" in msg  # tên riêng giữ nguyên


def test_unknown_tokens_pass_through(tmp_path):
    # Token lạ (tên riêng, ID) không bị biến thành chữ vô nghĩa
    raw = "[glb_admin] quota_xyz=12.3 → CRITICAL"
    out = _vn_message(raw)
    assert "NGHIÊM TRỌNG" in out
    assert "quota_xyz" in out and "12.3" in out


def test_vn_message_direct_mapping():
    assert _vn_message("[pc_host] ram_percent=95.5 → CRITICAL") == "[máy chính] RAM=95.5 → NGHIÊM TRỌNG"
    assert _vn_message("[selfcare_engine] connectivity=2 → CRITICAL").startswith("[tự chăm sóc]")
    assert "12.3" in _vn_message("value 12.3 RUNNING") and "ĐANG CHẠY" in _vn_message("value 12.3 RUNNING")
