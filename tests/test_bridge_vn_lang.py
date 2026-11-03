"""VN-LANG tầng cuối — mọi DM gửi owner chuẩn tiếng Việt (02/11/2026).

Owner yêu cầu: "toàn bộ tin nhắn gửi DM cho anh đều chuẩn hóa tiếng việt".
Điểm chặn DUY NHẤT: netchat_bridge.send_message — mọi đường gửi (alert engine,
voice, dashboard, responder) đi qua đây nên không thể bỏ sót.
"""
from __future__ import annotations

import pytest

from quan_ai_brain.integration.netchat_bridge import _vn_normalize


def test_alert_line_translated():
    raw = "[pc_host] ram_percent=95.5 → CRITICAL"
    out = _vn_normalize(raw)
    assert out == "[máy chính] RAM=95.5 → NGHIÊM TRỌNG"


def test_component_and_status_translated():
    out = _vn_normalize("[selfcare_engine] connectivity=2 → CRITICAL")
    assert "tự chăm sóc" in out and "kết nối" in out and "NGHIÊM TRỌNG" in out
    assert "selfcare_engine" not in out


def test_numbers_and_ids_untouched():
    raw = "task 579: status RUNNING, retry 2, id abc123"
    out = _vn_normalize(raw)
    assert "579" in out and "abc123" in out and "ĐANG CHẠY" in out


def test_proper_names_untouched():
    raw = "Ollama ONLINE, Pi 5 OFFLINE, GLM OK"
    out = _vn_normalize(raw)
    assert "Ollama" in out and "Pi 5" in out and "GLM" in out
    assert "HOẠT ĐỘNG" in out and "MẤT KẾT NỐI" in out


def test_vietnamese_text_passes_through():
    raw = "Em đã hoàn thành việc anh giao lúc 02:00 sáng."
    assert _vn_normalize(raw) == raw


def test_empty_and_none_safe():
    assert _vn_normalize("") == ""
    assert _vn_normalize(None) == "None" or _vn_normalize(None) == ""  # không nổ


def test_multi_status_line():
    raw = "PC chính: ONLINE | Pi 5: OFFLINE | Ollama: RUNNING."
    out = _vn_normalize(raw)
    assert "HOẠT ĐỘNG" in out and "MẤT KẾT NỐI" in out and "ĐANG CHẠY" in out
