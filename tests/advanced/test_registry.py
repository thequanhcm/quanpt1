"""Advanced Assurance — Test Governance Center self-test (Phần 3)."""
from __future__ import annotations

import pytest

from tests.advanced.registry import TEST_CATEGORIES, TestGovernanceError, TestRegistry


@pytest.fixture()
def reg(tmp_path):
    return TestRegistry(tmp_path / "tgov.db")


class TestRegistryRegistration:
    def test_register_minimal_case(self, reg):
        case = reg.register(test_name="smoke", test_category="UNIT")
        assert case["test_id"].startswith("tc_")
        assert case["status"] == "DESIGNED"
        assert case["regression_status"] == "NOT_RUN"

    def test_register_full_17_fields(self, reg):
        case = reg.register(
            test_name="approval race",
            test_category="CONCURRENCY",
            test_objective="chứng minh consume đúng 1 lần",
            target_module="governance.approval_service",
            risk_level="R4",
            preconditions="card APPROVED",
            input_dataset="2 thread",
            execution_environment="integration",
            expected_result="1 consume OK, 1 bị chặn",
            verification_method="assert consumed_at_utc khác None",
        )
        for field in (
            "test_id", "test_name", "test_category", "test_objective", "target_module",
            "risk_level", "preconditions", "input_dataset", "execution_environment",
            "expected_result", "verification_method", "actual_result", "evidence_refs",
            "status", "regression_status", "created_at", "last_executed_at",
        ):
            assert field in case, f"missing {field}"

    def test_unknown_category_rejected(self, reg):
        with pytest.raises(TestGovernanceError, match="unknown category"):
            reg.register(test_name="x", test_category="MAGIC")

    def test_invalid_risk_rejected(self, reg):
        with pytest.raises(TestGovernanceError, match="invalid risk_level"):
            reg.register(test_name="x", test_category="UNIT", risk_level="R9")

    def test_empty_name_rejected(self, reg):
        with pytest.raises(TestGovernanceError, match="test_name is required"):
            reg.register(test_name="  ", test_category="UNIT")

    def test_18_categories_available(self):
        assert len(TEST_CATEGORIES) == 18


class TestEvidenceAndVerificationLevels:
    def test_record_pass_run_updates_case(self, reg):
        case = reg.register(test_name="t", test_category="INTEGRATION")
        out = reg.record_run(test_id=case["test_id"], result="PASS", git_commit="7d9e7cd")
        assert out["result"] == "PASS"
        refreshed = reg.get_case(case["test_id"])
        assert refreshed["status"] == "IMPLEMENTED"
        assert refreshed["regression_status"] == "PASS"
        assert refreshed["last_executed_at"] is not None

    def test_evidence_has_12_fields(self, reg):
        case = reg.register(test_name="t", test_category="CHAOS")
        reg.record_run(
            test_id=case["test_id"], result="FAIL", error="boom",
            random_seed="42", refs=["log://x"], runner_version="pytest-9.1.1",
        )
        ev = reg.evidence_for(case["test_id"])[0]
        for field in (
            "evidence_id", "test_id", "git_commit", "software_version", "environment",
            "dataset_version", "config_fingerprint", "random_seed", "started_at",
            "ended_at", "result", "error", "logs_redacted", "refs", "runner_version",
        ):
            assert field in ev, f"missing {field}"
        assert ev["random_seed"] == "42"
        import json as _json

        assert _json.loads(ev["refs"]) == ["log://x"]

    def test_cannot_self_assign_owner_acceptance(self, reg):
        case = reg.register(test_name="t", test_category="ACCEPTANCE")
        with pytest.raises(TestGovernanceError, match="không tự nâng"):
            reg.record_run(test_id=case["test_id"], result="PASS", verification_level="OWNER_ACCEPTED")

    def test_cannot_self_assign_live_verified(self, reg):
        case = reg.register(test_name="t", test_category="HARDWARE")
        with pytest.raises(TestGovernanceError, match="không tự nâng"):
            reg.record_run(test_id=case["test_id"], result="PASS", verification_level="LIVE_VERIFIED")

    def test_can_self_assign_unit_tested(self, reg):
        case = reg.register(test_name="t", test_category="UNIT")
        reg.record_run(test_id=case["test_id"], result="PASS", verification_level="UNIT_TESTED")
        assert reg.get_case(case["test_id"])["status"] == "UNIT_TESTED"

    def test_invalid_result_rejected(self, reg):
        case = reg.register(test_name="t", test_category="UNIT")
        with pytest.raises(TestGovernanceError, match="PASS/FAIL/SKIP"):
            reg.record_run(test_id=case["test_id"], result="MAYBE")

    def test_unknown_case_rejected(self, reg):
        with pytest.raises(TestGovernanceError, match="not registered"):
            reg.record_run(test_id="tc_ghost", result="PASS")


class TestSummary:
    def test_summary_counts(self, reg):
        c1 = reg.register(test_name="a", test_category="UNIT")
        c2 = reg.register(test_name="b", test_category="SECURITY")
        reg.record_run(test_id=c1["test_id"], result="PASS", verification_level="UNIT_TESTED")
        reg.record_run(test_id=c2["test_id"], result="FAIL", error="e")
        s = reg.summary()
        assert s["total_cases"] == 2
        assert s["by_status"].get("UNIT_TESTED") == 1  # c1 promoted by level
        assert len(s["latest_runs"]) == 2
