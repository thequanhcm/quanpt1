"""Test fail-honest core_connected: heartbeat stale phải hiển thị OFFLINE.

(06/11/2026) Fix bug sticky-True: `core_connected` chỉ được set True khi
heartbeat/supervisor 200, không bao giờ reset False khi PC chết → kiosk
báo connected giả. `to_kiosk_dict` giờ tự đánh stale theo
`last_heartbeat_epoch` (heartbeat_timeout_sec × 3).
"""
from __future__ import annotations

import time
from edge_client.client_daemon import EdgeDaemonState
from edge_client.config import EdgeConfig


def _make_state() -> EdgeDaemonState:
    cfg = EdgeConfig(heartbeat_timeout_sec=4.0)
    return EdgeDaemonState(cfg)


def test_connected_when_heartbeat_fresh():
    st = _make_state()
    st.core_connected = True
    st.last_heartbeat_epoch = time.time()  # vừa heartbeat
    d = st.to_kiosk_dict()
    assert d["core_connected"] is True
    assert d["avatar_state"] != "OFFLINE"


def test_stale_heartbeat_shows_offline_fail_honest():
    st = _make_state()
    st.core_connected = True  # sticky True (không bao giờ bị reset)
    st.last_heartbeat_epoch = time.time() - 60.0  # 60s trước — quá stale (>12s)
    d = st.to_kiosk_dict()
    assert d["core_connected"] is False, "heartbeat stale phải báo mất kết nối"
    assert d["avatar_state"] == "OFFLINE"


def test_heartbeat_never_seen_keeps_disconnected():
    st = _make_state()
    st.core_connected = False
    st.last_heartbeat_epoch = 0.0  # chưa từng nhận heartbeat
    d = st.to_kiosk_dict()
    assert d["core_connected"] is False
    assert d["avatar_state"] == "OFFLINE"


def test_recovery_after_stale():
    st = _make_state()
    st.core_connected = True
    st.last_heartbeat_epoch = time.time() - 60.0
    assert st.to_kiosk_dict()["core_connected"] is False
    st.last_heartbeat_epoch = time.time()  # heartbeat sống lại
    d = st.to_kiosk_dict()
    assert d["core_connected"] is True
