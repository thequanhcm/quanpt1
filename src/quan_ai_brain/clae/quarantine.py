"""Candidate knowledge lifecycle helpers. Production learning is not autonomous."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from quan_ai_brain.memory.sqlite_store import MemoryStore

ApprovalVerifier = Callable[[str, str, str], bool]


@dataclass(frozen=True)
class KnowledgeCandidate:
    id: str
    statement: str
    source_ref: str
    status: str = "quarantined"


class KnowledgeQuarantine:
    def __init__(self, memory: MemoryStore, approval_verifier: ApprovalVerifier | None = None) -> None:
        self.memory = memory
        # Disabled by default. A production integration must inject a trusted verifier
        # wired to an authenticated owner approval surface, not an LLM-generated string.
        self.approval_verifier = approval_verifier

    def submit(self, statement: str, source_ref: str, rationale: str = "") -> KnowledgeCandidate:
        candidate_id = self.memory.add_candidate(statement, source_ref, rationale)
        return KnowledgeCandidate(candidate_id, statement, source_ref)

    def approve_and_promote(
        self,
        candidate_id: str,
        *,
        approved_by: str,
        regression_passed: bool,
        approval_evidence: str = "",
        decision_note: str = "",
    ) -> None:
        if self.approval_verifier is None:
            raise PermissionError("Approval verifier is not configured; candidate remains quarantined")
        if not self.approval_verifier(candidate_id, approved_by, approval_evidence):
            raise PermissionError("Owner approval could not be verified; candidate remains quarantined")
        self.memory.promote_candidate(
            candidate_id,
            approved_by=approved_by,
            regression_passed=regression_passed,
            decision_note=decision_note,
            approval_verified=True,
        )
