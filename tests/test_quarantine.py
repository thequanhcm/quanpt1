import pytest

from quan_ai_brain.clae.quarantine import KnowledgeQuarantine
from quan_ai_brain.memory.sqlite_store import MemoryStore


def test_candidate_stays_quarantined_until_approval_and_regression():
    with MemoryStore(":memory:") as store:
        quarantine = KnowledgeQuarantine(
            store,
            approval_verifier=lambda candidate_id, approved_by, evidence: (
                candidate_id == candidate.id and approved_by == "owner" and evidence == "signed-test-approval"
            ),
        )
        candidate = quarantine.submit("Use evidence before learning", "test://evidence", "test rationale")
        assert store.list_candidates()[0]["status"] == "quarantined"
        with pytest.raises(PermissionError):
            store.promote_candidate(candidate.id, approved_by="owner", regression_passed=True)
        with pytest.raises(PermissionError):
            quarantine.approve_and_promote(candidate.id, approved_by="owner", approval_evidence="wrong", regression_passed=True)
        with pytest.raises(ValueError):
            quarantine.approve_and_promote(candidate.id, approved_by="owner", approval_evidence="signed-test-approval", regression_passed=False)
        quarantine.approve_and_promote(candidate.id, approved_by="owner", approval_evidence="signed-test-approval", regression_passed=True)
        assert store.list_candidates()[0]["status"] == "promoted"
        semantic = store._connection.execute("SELECT statement, regression_passed FROM semantic_memory").fetchone()
        assert semantic["statement"] == "Use evidence before learning"
        assert semantic["regression_passed"] == 1


def test_quarantine_disables_promotion_without_trusted_verifier():
    with MemoryStore(":memory:") as store:
        quarantine = KnowledgeQuarantine(store)
        candidate = quarantine.submit("Candidate stays quarantined", "test://source")
        with pytest.raises(PermissionError):
            quarantine.approve_and_promote(candidate.id, approved_by="owner", approval_evidence="anything", regression_passed=True)
        assert store.list_candidates()[0]["status"] == "quarantined"


def test_candidate_requires_source():
    with MemoryStore(":memory:") as store:
        with pytest.raises(ValueError):
            store.add_candidate("A rule", "")
