"""Tests for Sprint 6 — Self-Care Engine.

Tests:
- Health checks (ollama, web, pi5)
- Alert generation
- Auto-recovery
- Incident management
- Health summary
"""
import sys

sys.path.insert(0, "src")

from quan_ai_brain.cognition.self_care_engine import (
    SelfCareEngine,
    HealthLevel,
    HealthCheck,
    Alert,
    Incident,
)


def test_ollama_health_check():
    """Test Ollama health check."""
    engine = SelfCareEngine()
    check = engine.check_ollama_health()

    assert check.component == "ollama"
    assert check.metric in ["response_time", "connectivity"]
    assert check.status in [HealthLevel.HEALTHY, HealthLevel.WARNING, HealthLevel.CRITICAL, HealthLevel.DOWN]
    assert check.timestamp is not None

    print(f"✓ Ollama health: {check.status.value} - {check.message}")


def test_web_health_check():
    """Test web server health check."""
    engine = SelfCareEngine()
    check_8765 = engine.check_web_health(8765)
    check_8766 = engine.check_web_health(8766)

    assert check_8765.component == "web_8765"
    assert check_8766.component == "web_8766"
    assert check_8765.status in [HealthLevel.HEALTHY, HealthLevel.DOWN]
    assert check_8766.status in [HealthLevel.HEALTHY, HealthLevel.DOWN]

    print(f"✓ Web health: 8765={check_8765.status.value}, 8766={check_8766.status.value}")


def test_pi5_health_check():
    """Test Pi 5 health check."""
    engine = SelfCareEngine()
    check = engine.check_pi5_connection()

    assert check.component == "pi5"
    assert check.status in [HealthLevel.HEALTHY, HealthLevel.DOWN]

    print(f"✓ Pi 5 health: {check.status.value} - {check.message}")


def test_run_all_health_checks():
    """Test running all health checks."""
    engine = SelfCareEngine()
    checks = engine.run_all_health_checks()

    assert len(checks) >= 4  # Ollama, web 8765, web 8766, Pi 5
    assert all(isinstance(c, HealthCheck) for c in checks)

    healthy = sum(1 for c in checks if c.status == HealthLevel.HEALTHY)
    print(f"✓ All health checks: {healthy}/{len(checks)} healthy")


def test_alert_generation():
    """Test alert generation from health checks."""
    engine = SelfCareEngine()
    checks = engine.run_all_health_checks()
    alerts = engine.generate_alerts(checks)

    # Should have alerts for unhealthy components
    unresolved = [a for a in alerts if not a.resolved]
    print(f"✓ Alerts generated: {len(alerts)} total, {len(unresolved)} unresolved")


def test_auto_recovery():
    """Test auto-recovery for critical issues."""
    engine = SelfCareEngine()

    # Create a DOWN alert
    alert = Alert(
        alert_id="test_auto_recover",
        severity=HealthLevel.DOWN,
        component="ollama",
        message="Ollama offline",
        detected_at="2026-10-25T12:00:00Z",
    )

    # Attempt auto-recovery
    engine._attempt_auto_recovery(alert)

    # Should have attempted recovery
    assert alert.action_taken != ""
    assert "Ollama" in alert.action_taken or "restart" in alert.action_taken.lower()

    print("✓ Auto-recovery: PASS")


def test_incident_creation():
    """Test incident creation from alert."""
    engine = SelfCareEngine()

    alert = Alert(
        alert_id="test_incident",
        severity=HealthLevel.CRITICAL,
        component="ollama",
        message="Ollama offline",
        detected_at="2026-10-25T12:00:00Z",
    )

    incident = engine.create_incident(alert, root_cause="Ollama daemon crashed")

    assert incident.component == "ollama"
    assert incident.severity == HealthLevel.CRITICAL
    assert incident.root_cause == "Ollama daemon crashed"
    assert len(incident.symptoms) == 1

    print("✓ Incident creation: PASS")


def test_incident_resolution():
    """Test incident resolution."""
    engine = SelfCareEngine()

    alert = Alert(
        alert_id="test_resolve",
        severity=HealthLevel.DOWN,
        component="ollama",
        message="Ollama offline",
        detected_at="2026-10-25T12:00:00Z",
    )

    incident = engine.create_incident(alert)
    success = engine.resolve_incident(
        incident.incident_id,
        resolution="Restarted Ollama daemon",
        lessons=["Add health check monitoring"],
    )

    assert success is True
    assert incident.resolution == "Restarted Ollama daemon"
    assert incident.resolved_at is not None
    assert len(incident.lessons_learned) == 1

    print("✓ Incident resolution: PASS")


def test_health_summary():
    """Test health summary generation."""
    engine = SelfCareEngine()
    engine.run_all_health_checks()
    engine.generate_alerts()

    summary = engine.get_health_summary()

    assert "total_checks" in summary
    assert "healthy" in summary
    assert "health_percentage" in summary
    assert "active_alerts" in summary
    assert "auto_recoveries" in summary
    assert summary["total_checks"] >= 4

    print(f"✓ Health summary: {summary['health_percentage']*100:.1f}% healthy, {summary['active_alerts']} active alerts")


def test_get_active_alerts():
    """Test getting active alerts."""
    engine = SelfCareEngine()
    engine.run_all_health_checks()
    engine.generate_alerts()

    active = engine.get_active_alerts(limit=10)
    assert isinstance(active, list)

    print(f"✓ Active alerts: {len(active)}")


def test_get_incidents():
    """Test getting incidents."""
    engine = SelfCareEngine()

    # Create a test incident
    alert = Alert(
        alert_id="test_inc_1",
        severity=HealthLevel.WARNING,
        component="test",
        message="Test alert",
        detected_at="2026-10-25T12:00:00Z",
    )
    engine.create_incident(alert)

    incidents = engine.get_incidents(limit=10)
    assert len(incidents) >= 1

    print(f"✓ Incidents: {len(incidents)}")


def main() -> int:
    """Run all tests."""
    print("=" * 60)
    print("Sprint 6 — Self-Care Engine Tests")
    print("=" * 60)

    tests = [
        test_ollama_health_check,
        test_web_health_check,
        test_pi5_health_check,
        test_run_all_health_checks,
        test_alert_generation,
        test_auto_recovery,
        test_incident_creation,
        test_incident_resolution,
        test_health_summary,
        test_get_active_alerts,
        test_get_incidents,
    ]

    failed = 0
    for test in tests:
        try:
            test()
        except AssertionError as e:
            print(f"✗ {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test.__name__}: {type(e).__name__}: {e}")
            failed += 1

    print("=" * 60)
    if failed == 0:
        print(f"✓ All {len(tests)} tests passed — Sprint 6 self-care ready")
        return 0
    else:
        print(f"✗ {failed}/{len(tests)} tests failed")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())