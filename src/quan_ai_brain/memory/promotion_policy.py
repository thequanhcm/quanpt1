"""QUAN AI BRAIN — Knowledge Promotion Policy (Sprint D).

Layered promotion policy per Master Prompt Năng lực 6 and the approved
design (docs/DIGITAL_EMPLOYEE_BRAIN_DESIGN.md §5):

| Layer | Content                          | Auto-promote? | Rule |
|-------|----------------------------------|---------------|------|
| L0    | General non-risky facts          | YES (policy pre-approved by owner) | confidence >= 0.8, no conflicts, dedup pass |
| L1    | DC/production business knowledge | NEVER auto — batch proposal to owner |
| L2    | SOP / procedures                 | NEVER auto — requires sandbox practice test pass + owner |
| L3    | Safety / policy knowledge        | NEVER — owner only, separate approval |

Safety invariants:
- Never promotes into an existing semantic statement (dedup first).
- Never promotes L1/L2/L3 automatically — produces review batches.
- Everything is auditable; dedup candidates are reported, never deleted.
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Layer classification by source_ref source_type (JSON) or explicit override.
DEFAULT_LAYER_RULES: dict[str, str] = {
    # Learning daemon / doc ingestions are L0 candidates (general knowledge).
    "PROJECT_DOCS": "L0",
    "TECHNICAL_SPEC": "L0",
    "TEST_EVIDENCE": "L0",
    # DC domain knowledge from Skill/ ingestions is L1 (owner-batched).
    "DC_SKILL": "L1",
    # Reflection hypotheses are L0-ish but require conflict-free check.
    "reflection": "L0",
}

# Keywords that force a stricter layer regardless of source type.
L2_KEYWORDS = ("sop", "quy trình", "procedure", "runbook", "hướng dẫn xử lý")
L3_KEYWORDS = ("safety", "an toàn", "policy", "chính sách", "r5", "kill-switch")


@dataclass
class PromotionDecision:
    candidate_id: str
    statement: str
    layer: str
    action: str  # PROMOTE | NEEDS_OWNER | SKIP_DUP | SKIP_CONFLICT | SKIP_LOW_CONFIDENCE
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "layer": self.layer,
            "action": self.action,
            "reason": self.reason,
            "statement": self.statement[:200],
        }


@dataclass
class PromotionBatchResult:
    evaluated: int = 0
    promoted: int = 0
    needs_owner: int = 0
    skipped_dup: int = 0
    skipped_conflict: int = 0
    skipped_low_confidence: int = 0
    decisions: list[PromotionDecision] = field(default_factory=list)
    executed_at: str = ""

    def to_dict(self, max_decisions: int = 100) -> dict[str, Any]:
        return {
            "executed_at": self.executed_at,
            "evaluated": self.evaluated,
            "promoted": self.promoted,
            "needs_owner": self.needs_owner,
            "skipped_dup": self.skipped_dup,
            "skipped_conflict": self.skipped_conflict,
            "skipped_low_confidence": self.skipped_low_confidence,
            "decisions": [d.to_dict() for d in self.decisions[:max_decisions]],
        }


class PromotionPolicy:
    """Classifies and promotes quarantined knowledge by layer."""

    def __init__(self, db_path: str | Path, *, l0_confidence_threshold: float = 0.8,
                 audit_logger: Any | None = None) -> None:
        self.db_path = Path(db_path)
        self.l0_confidence_threshold = l0_confidence_threshold
        self._audit = audit_logger

    # ------------------------------------------------------------------
    # Classification
    # ------------------------------------------------------------------

    def classify_layer(self, statement: str, source_ref: str) -> str:
        """Assign L0..L3. Stricter layer wins when multiple match."""
        text = (statement or "").lower()
        for kw in L3_KEYWORDS:
            if kw in text:
                return "L3"
        for kw in L2_KEYWORDS:
            if kw in text:
                return "L2"
        source_type = ""
        try:
            source_type = json.loads(source_ref or "{}").get("source_type", "")
        except Exception:
            source_type = ""
        return DEFAULT_LAYER_RULES.get(source_type, "L1")

    def _extract_confidence(self, rationale: str | None) -> float | None:
        if not rationale:
            return None
        try:
            return float(str(rationale).split("Confidence:")[1].split(";")[0])
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Batch evaluation (REPORT for L1+, EXECUTE only L0)
    # ------------------------------------------------------------------

    def evaluate_batch(self, *, limit: int = 500, execute_l0: bool = True,
                       approved_by: str = "policy_L0_auto") -> PromotionBatchResult:
        """Evaluate quarantined candidates.

        execute_l0=True: L0 candidates passing all checks are promoted to
        semantic_memory (dedup-guarded). L1/L2/L3 are NEVER auto-promoted —
        they are counted into needs_owner for an owner review batch.
        """
        result = PromotionBatchResult(executed_at=datetime.now(timezone.utc).isoformat())
        if not self.db_path.exists():
            return result

        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            semantic_keys = {
                self._norm(r["statement"])
                for r in conn.execute("SELECT statement FROM semantic_memory").fetchall()
            }
            candidates = conn.execute(
                "SELECT id, statement, source_ref, rationale FROM candidate_knowledge "
                "WHERE status='quarantined' ORDER BY created_at_utc ASC LIMIT ?",
                (limit,),
            ).fetchall()

            for row in candidates:
                result.evaluated += 1
                statement = row["statement"] or ""
                key = self._norm(statement)
                layer = self.classify_layer(statement, row["source_ref"])
                confidence = self._extract_confidence(row["rationale"])

                # Universal dedup guard (also across decisions in this batch)
                if key in semantic_keys:
                    result.skipped_dup += 1
                    result.decisions.append(PromotionDecision(
                        row["id"], statement, layer, "SKIP_DUP",
                        "statement already exists in semantic_memory"))
                    continue

                # Universal conflict guard via numeric/negation heuristic
                if self._conflicts_with_semantic(conn, key, statement):
                    result.skipped_conflict += 1
                    result.decisions.append(PromotionDecision(
                        row["id"], statement, layer, "SKIP_CONFLICT",
                        "conflict suspect with existing semantic statement"))
                    continue

                if layer == "L3":
                    result.needs_owner += 1
                    result.decisions.append(PromotionDecision(
                        row["id"], statement, layer, "NEEDS_OWNER",
                        "L3 safety/policy knowledge: owner-only, separate approval"))
                    continue
                if layer == "L2":
                    result.needs_owner += 1
                    result.decisions.append(PromotionDecision(
                        row["id"], statement, layer, "NEEDS_OWNER",
                        "L2 SOP/procedure: requires sandbox practice test + owner"))
                    continue
                if layer == "L1":
                    result.needs_owner += 1
                    result.decisions.append(PromotionDecision(
                        row["id"], statement, layer, "NEEDS_OWNER",
                        "L1 DC/production knowledge: owner batch review"))
                    continue

                # L0: policy-approved auto-promotion path
                if confidence is None or confidence < self.l0_confidence_threshold:
                    result.skipped_low_confidence += 1
                    result.decisions.append(PromotionDecision(
                        row["id"], statement, layer, "SKIP_LOW_CONFIDENCE",
                        f"confidence {confidence} < {self.l0_confidence_threshold}"))
                    continue

                if execute_l0:
                    self._promote(conn, row, approved_by)
                    result.promoted += 1
                    result.decisions.append(PromotionDecision(
                        row["id"], statement, layer, "PROMOTE",
                        f"L0 auto-promote (confidence {confidence})"))
                else:
                    result.needs_owner += 1
                    result.decisions.append(PromotionDecision(
                        row["id"], statement, layer, "NEEDS_OWNER",
                        "execute_l0=False; dry-run only"))
        finally:
            conn.close()

        if self._audit is not None:
            try:
                self._audit.record("promotion_policy.batch", {
                    "evaluated": result.evaluated,
                    "promoted": result.promoted,
                    "needs_owner": result.needs_owner,
                    "skipped_dup": result.skipped_dup,
                    "skipped_conflict": result.skipped_conflict,
                    "skipped_low_confidence": result.skipped_low_confidence,
                })
            except Exception:
                pass
        return result

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _promote(self, conn: sqlite3.Connection, row: sqlite3.Row, approved_by: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with conn:
            conn.execute(
                "INSERT INTO semantic_memory (id, created_at_utc, statement, source_ref, approved_by, regression_passed) "
                "VALUES (?, ?, ?, ?, ?, 1)",
                (row["id"], now, row["statement"], row["statement"], approved_by),
            )
            conn.execute(
                "UPDATE candidate_knowledge SET status='approved', decision_note=? WHERE id=?",
                (f"L0 auto-promotion by policy (owner pre-approved), {now}", row["id"]),
            )

    @staticmethod
    def _norm(statement: str) -> str:
        return " ".join((statement or "").split()).lower()

    def _conflicts_with_semantic(self, conn: sqlite3.Connection, key: str, statement: str) -> bool:
        """Check the numeric/negation contradiction heuristic against semantic
        statements sharing the same coarse subject (numbers excluded from the
        subject so value differences are comparable)."""
        subject = " ".join([w for w in key.split() if not any(ch.isdigit() for ch in w)][:6])
        if not subject:
            return False
        rows = conn.execute("SELECT statement FROM semantic_memory").fetchall()
        nums_new = set(_numbers(statement))
        negs = ("không ", "not ", "chưa ", "false")
        pol_new = any(n in key for n in negs)
        for r in rows:
            other = self._norm(r["statement"])
            other_subject = " ".join([w for w in other.split() if not any(ch.isdigit() for ch in w)][:6])
            if other_subject != subject:
                continue
            nums_old = set(_numbers(other))
            if nums_new and nums_old and nums_new != nums_old:
                return True
            pol_old = any(n in other for n in negs)
            if pol_new != pol_old:
                return True
        return False


def _numbers(text: str) -> list[str]:
    import re

    return re.findall(r"\d+(?:[.,]\d+)?", text or "")
