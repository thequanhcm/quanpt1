"""Unit tests for EdgeConnectionMonitor and Watchdog on PC Central Brain Core."""
from __future__ import annotations

import time

import pytest

from quan_ai_brain.web.edge_monitor import (
    EdgeAlertCode,
    EdgeConnectionMonitor,
    EdgeConnectionState,
)


def test_initial_state_triggers_alert_a():
    monitor = EdgeConnectionMonitor(heartbeat_timeout_sec=2.0)
    assert monitor.state == EdgeConnectionState.DISCONNECTED
    assert not monitor.paired

    status = monitor.get_status()
    assert status["state"] == "DISCONNECTED"
    assert status["active_alert_count"] == 1
    assert status["active_alerts"][0]["code"] == EdgeAlertCode.ALERT_A_PI5_NOT_CONNECTED.value


def test_pairing_transitions_to_connecting():
    monitor = EdgeConnectionMonitor()
    monitor.record_pairing("EDGE-PI5-DESK-01", "Bàn Làm Việc Quanpt1")
    assert monitor.paired is True
    assert monitor.state == EdgeConnectionState.CONNECTING
    assert EdgeAlertCode.ALERT_A_PI5_NOT_CONNECTED not in monitor.active_alerts


def test_heartbeat_normal_transitions_to_ready():
    monitor = EdgeConnectionMonitor()
    monitor.record_pairing("EDGE-PI5-DESK-01", "Bàn Làm Việc Quanpt1")

    # Send healthy heartbeat
    status = monitor.record_heartbeat("EDGE-PI5-DESK-01", rtt_ms=18.5, subsystems_ready=True)
    assert status["state"] == EdgeConnectionState.READY.value
    assert status["rtt_ms"] == 18.5
    assert status["active_alert_count"] == 0
    assert status["last_heartbeat_utc"] is not None


def test_degraded_channel_triggers_alert_c():
    monitor = EdgeConnectionMonitor(degraded_rtt_threshold_ms=100.0)
    monitor.record_pairing("EDGE-PI5-DESK-01", "Bàn Làm Việc Quanpt1")

    # Send high latency heartbeat
    monitor.record_heartbeat("EDGE-PI5-DESK-01", rtt_ms=250.0)
    assert monitor.state == EdgeConnectionState.DEGRADED
    assert EdgeAlertCode.ALERT_C_CHANNEL_DEGRADED in monitor.active_alerts

    # Next healthy heartbeat resolves degradation
    monitor.record_heartbeat("EDGE-PI5-DESK-01", rtt_ms=25.0)
    assert monitor.state == EdgeConnectionState.READY
    assert EdgeAlertCode.ALERT_C_CHANNEL_DEGRADED not in monitor.active_alerts


def test_watchdog_detects_sudden_disconnect_alert_b():
    # Set short timeout of 0.2s for deterministic testing
    monitor = EdgeConnectionMonitor(heartbeat_timeout_sec=0.2)
    monitor.record_pairing("EDGE-PI5-DESK-01", "Bàn Làm Việc Quanpt1")
    monitor.record_heartbeat("EDGE-PI5-DESK-01", rtt_ms=15.0)
    assert monitor.state == EdgeConnectionState.READY

    # Wait past timeout
    time.sleep(0.25)
    monitor.check_deadline()

    # Must transition to DISCONNECTED and trigger Alert B
    assert monitor.state == EdgeConnectionState.DISCONNECTED
    assert EdgeAlertCode.ALERT_B_SUDDEN_DISCONNECT in monitor.active_alerts
    alert_b = monitor.active_alerts[EdgeAlertCode.ALERT_B_SUDDEN_DISCONNECT]
    assert alert_b.severity == "CRITICAL"
    assert "MẤT KẾT NỐI" in alert_b.title


def test_recovery_triggers_alert_e_and_preserves_history():
    monitor = EdgeConnectionMonitor(heartbeat_timeout_sec=0.15)
    monitor.record_pairing("EDGE-PI5-DESK-01", "Bàn Làm Việc Quanpt1")
    monitor.record_heartbeat("EDGE-PI5-DESK-01", rtt_ms=15.0)

    # Disconnect
    time.sleep(0.20)
    monitor.check_deadline()
    assert monitor.state == EdgeConnectionState.DISCONNECTED

    # Reconnect / Recover
    monitor.record_heartbeat("EDGE-PI5-DESK-01", rtt_ms=12.0)
    assert monitor.state == EdgeConnectionState.READY
    # Alert B cleared, Alert E triggered
    assert EdgeAlertCode.ALERT_B_SUDDEN_DISCONNECT not in monitor.active_alerts
    assert EdgeAlertCode.ALERT_E_PI5_RECOVERED in monitor.active_alerts

    # Verify history preserved past incident
    history = monitor.get_alert_history()
    codes = [h["code"] for h in history]
    assert EdgeAlertCode.ALERT_B_SUDDEN_DISCONNECT.value in codes
    assert EdgeAlertCode.ALERT_E_PI5_RECOVERED.value in codes


def test_auth_and_sync_faults():
    monitor = EdgeConnectionMonitor()

    # Security fault
    monitor.record_auth_failure("HMAC Signature verification failed; invalid key or tampered payload")
    assert monitor.state == EdgeConnectionState.AUTH_FAILED
    assert EdgeAlertCode.ALERT_F_SECURITY_OR_AUTH_FAULT in monitor.active_alerts

    # Sync fault
    monitor.record_sync_failure("Timeout waiting for task queue ACK")
    assert EdgeAlertCode.ALERT_D_SYNC_FAILED in monitor.active_alerts
