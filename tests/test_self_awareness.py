"""Tests for Sprint 4 — Self-Awareness Engine.

Tests:
1. System inventory scan
2. Component health check
3. Self-model generation
4. Conversational summary
"""
import sys
from pathlib import Path

sys.path.insert(0, "src")

from quan_ai_brain.cognition.system_inventory import SystemInventory, ComponentStatus
from quan_ai_brain.cognition.self_model_engine import SelfModelEngine


def test_system_inventory_scan():
    """Test full system inventory scan."""
    inventory = SystemInventory(".")
    components = inventory.scan_all()

    assert len(components) > 0, "Should discover at least some components"

    # Check for expected components
    component_ids = list(components.keys())
    assert any("python" in cid for cid in component_ids), "Should have Python runtime"
    assert any("db_" in cid for cid in component_ids), "Should have databases"
    assert any("module_" in cid for cid in component_ids), "Should have modules"

    print(f"✓ System inventory scan: {len(components)} components discovered")


def test_component_health_check():
    """Test health status of components."""
    inventory = SystemInventory(".")
    components = inventory.scan_all()

    # Check that we have both healthy and potentially unhealthy components
    healthy_count = sum(1 for c in components.values() if c.status == ComponentStatus.HEALTHY)
    failed_count = sum(1 for c in components.values() if c.status == ComponentStatus.FAILED)
    not_installed_count = sum(1 for c in components.values() if c.status == ComponentStatus.NOT_INSTALLED)

    assert healthy_count > 0, "Should have at least some healthy components"

    print(f"✓ Component health: {healthy_count} healthy, {failed_count} failed, {not_installed_count} not installed")


def test_health_summary():
    """Test health summary generation."""
    inventory = SystemInventory(".")
    inventory.scan_all()
    summary = inventory.get_health_summary()

    assert "total_components" in summary
    assert "healthy" in summary
    assert "health_percentage" in summary
    assert summary["total_components"] > 0
    assert 0 <= summary["health_percentage"] <= 1

    print(f"✓ Health summary: {summary['health_percentage']*100:.1f}% healthy")


def test_self_model_generation():
    """Test self-model generation."""
    engine = SelfModelEngine(".")
    model = engine.generate_self_model()

    assert model.identity["system_name"] == "QUAN AI BRAIN"
    assert model.identity["assistant_name"] == "TONY PHAM"
    assert model.identity["owner"] == "Quanpt1"
    assert len(model.active_modules) > 0
    assert len(model.memory_types) > 0
    assert len(model.ai_models) > 0
    assert len(model.verified_capabilities) > 0
    assert model.generated_at is not None
    assert 0 <= model.confidence <= 1

    print(f"✓ Self-model generated: {len(model.active_modules)} modules, {len(model.verified_capabilities)} verified capabilities")


def test_conversational_summary():
    """Test conversational self-introduction."""
    engine = SelfModelEngine(".")
    model = engine.generate_self_model()
    summary = model.to_conversational_summary()

    assert "TONY PHAM" in summary
    assert "Quanpt1" in summary
    assert "PC Core" in summary or "Raspberry Pi" in summary
    assert "Bộ nhớ" in summary or "Memory" in summary
    assert "Giới hạn" in summary or "Limitation" in summary

    print("✓ Conversational summary generated")


def test_component_to_dict():
    """Test component serialization."""
    inventory = SystemInventory(".")
    components = inventory.scan_all()

    for comp in list(components.values())[:3]:  # Test first 3
        comp_dict = comp.to_dict()
        assert "component_id" in comp_dict
        assert "name" in comp_dict
        assert "status" in comp_dict
        assert "confidence" in comp_dict

    print("✓ Component serialization: PASS")


def main() -> int:
    """Run all tests."""
    print("=" * 60)
    print("Sprint 4 — Self-Awareness Engine Tests")
    print("=" * 60)

    tests = [
        test_system_inventory_scan,
        test_component_health_check,
        test_health_summary,
        test_self_model_generation,
        test_conversational_summary,
        test_component_to_dict,
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
        print(f"✓ All {len(tests)} tests passed — Sprint 4 self-awareness ready")
        return 0
    else:
        print(f"✗ {failed}/{len(tests)} tests failed")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())