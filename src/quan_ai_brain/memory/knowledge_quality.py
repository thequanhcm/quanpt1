"""QUAN AI BRAIN — Knowledge Quality Scanner (Sprint C).

Detects duplicates, conflicts, and stale knowledge in semantic_memory and
candidate_knowledge. REPORT-ONLY: this module never deletes or rewrites
knowledge — remediation is a separate, approved, auditable step.

Master Prompt mapping:
- Năng lực 5 (Memory): "Phát hiện tri thức mâu thuẫn hoặc lỗi thời",
  "Hợp nhất bản ghi trùng lặp có kiểm soát" (controlled = policy module).
- Sprint C2/C3 of DIGITAL_EMPLOYEE_BRAIN_IMPLEMENTATION_PLAN.
"""
from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


@dataclass
class QualityIssue:
    issue_type: str  # duplicate | conflict_suspect | stale | dup_of_semantic | internal_duplicate
    severity: str  # INFO | WARN | HIGH
    statement_a: str
    statement_b: str | None
    id_a: str
    id_b: str | None
    evidence: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "issue_type": self.issue_type,
            "severity": self.severity,
            "id_a": self.id_a,
            "id_b": self.id_b,
            "statement_a": self.statement_a[:200],
            "statement_b": (self.statement_b or "")[:200],
            "evidence": self.evidence,
        }


@dataclass
class QualityReport:
    scanned_semantic: int = 0
    scanned_candidates: int = 0
    exact_duplicates_semantic: int = 0
    dup_candidates_of_semantic: int = 0
    internal_duplicate_candidates: int = 0
    unique_quarantined_statements: int = 0
    conflict_suspects: list[QualityIssue] = field(default_factory=list)
    stale_suspects: list[QualityIssue] = field(default_factory=list)
    scanned_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "scanned_at": self.scanned_at,
            "scanned_semantic": self.scanned_semantic,
            "scanned_candidates": self.scanned_candidates,
            "exact_duplicates_semantic": self.exact_duplicates_semantic,
            "dup_candidates_of_semantic": self.dup_candidates_of_semantic,
            "internal_duplicate_candidates": self.internal_duplicate_candidates,
            "unique_quarantined_statements": self.unique_quarantined_statements,
            "conflict_suspects": [i.to_dict() for i in self.conflict_suspects[:50]],
            "stale_suspects": [i.to_dict() for i in self.stale_suspects[:50]],
        }

    def to_summary(self) -> str:
        return (
            f"Semantic: {self.scanned_semantic} (exact dups: {self.exact_duplicates_semantic}) | "
            f"Candidates: {self.scanned_candidates} "
            f"(dup-of-semantic: {self.dup_candidates_of_semantic}, "
            f"internal dups: {self.internal_duplicate_candidates}, "
            f"unique: {self.unique_quarantined_statements}) | "
            f"Conflict suspects: {len(self.conflict_suspects)} | "
            f"Stale suspects: {len(self.stale_suspects)}"
        )


# Number/date patterns for stale detection (statements referencing old dates).
_YEAR_RE = re.compile(r"\b(20\d{2})\b")


class KnowledgeQualityScanner:
    """Read-only scanner over brain.db knowledge tables."""

    def __init__(self, db_path: str | Path, *, stale_days: int = 180) -> None:
        self.db_path = Path(db_path)
        self.stale_days = stale_days

    # ------------------------------------------------------------------
    # Scans
    # ------------------------------------------------------------------

    def scan(self) -> QualityReport:
        report = QualityReport(scanned_at=datetime.now(timezone.utc).isoformat())
        if not self.db_path.exists():
            return report

        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            sem = conn.execute(
                "SELECT id, statement, created_at_utc FROM semantic_memory"
            ).fetchall()
            report.scanned_semantic = len(sem)

            # 1. Exact duplicates inside semantic_memory
            seen: dict[str, str] = {}
            for row in sem:
                key = self._normalize(row["statement"])
                if key in seen:
                    report.exact_duplicates_semantic += 1
                else:
                    seen[key] = row["id"]

            # 2. Candidate duplicates of semantic + internal duplicates
            cand = conn.execute(
                "SELECT id, statement, source_ref, status FROM candidate_knowledge "
                "WHERE status = 'quarantined'"
            ).fetchall()
            report.scanned_candidates = len(cand)

            semantic_keys = set(seen.keys())
            unique_candidate_keys: set[str] = set()
            for row in cand:
                key = self._normalize(row["statement"])
                if key in semantic_keys:
                    report.dup_candidates_of_semantic += 1
                elif key in unique_candidate_keys:
                    report.internal_duplicate_candidates += 1
                else:
                    unique_candidate_keys.add(key)
            report.unique_quarantined_statements = len(unique_candidate_keys)

            # 3. Conflict suspects within unique semantic statements:
            #    same normalized subject prefix, contradicting polarity/number.
            by_subject: dict[str, list[sqlite3.Row]] = {}
            for row in sem:
                subj = self._subject_key(row["statement"])
                by_subject.setdefault(subj, []).append(row)
            for subj, group in by_subject.items():
                if len(group) < 2:
                    continue
                for i in range(len(group)):
                    for j in range(i + 1, len(group)):
                        if self._contradicts(group[i]["statement"], group[j]["statement"]):
                            report.conflict_suspects.append(
                                QualityIssue(
                                    issue_type="conflict_suspect",
                                    severity="WARN",
                                    statement_a=group[i]["statement"],
                                    statement_b=group[j]["statement"],
                                    id_a=group[i]["id"],
                                    id_b=group[j]["id"],
                                    evidence=f"same subject '{subj[:60]}' with differing value/polarity",
                                )
                            )

            # 4. Stale suspects: semantic statements referencing old dates.
            cutoff = datetime.now(timezone.utc) - timedelta(days=self.stale_days)
            for row in sem:
                years = [int(y) for y in _YEAR_RE.findall(row["statement"] or "")]
                if not years:
                    continue
                # A statement whose newest referenced year is older than the
                # staleness horizon in days is a staleness suspect.
                newest = max(years)
                ref_date = datetime(newest, 12, 31, tzinfo=timezone.utc)
                if ref_date < cutoff:
                    report.stale_suspects.append(
                        QualityIssue(
                            issue_type="stale",
                            severity="INFO",
                            statement_a=row["statement"],
                            statement_b=None,
                            id_a=row["id"],
                            id_b=None,
                            evidence=f"references year {newest}, older than {self.stale_days}d horizon",
                        )
                    )
        finally:
            conn.close()
        return report

    # ------------------------------------------------------------------
    # Heuristics
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize(statement: str) -> str:
        return re.sub(r"\s+", " ", (statement or "").strip().lower())

    @staticmethod
    def _subject_key(statement: str) -> str:
        """Coarse subject: first 6 normalized NON-NUMERIC words.

        Numbers are excluded so that statements about the same subject
        differing only in values land in the same conflict-check group.
        """
        words = KnowledgeQualityScanner._normalize(statement).split()
        alpha = [w for w in words if not any(ch.isdigit() for ch in w)]
        return " ".join(alpha[:6])

    @staticmethod
    def _contradicts(a: str, b: str) -> bool:
        """Conservative contradiction heuristic (suspect only, human-verifiable):
        same subject but different numbers, or one contains a negation the
        other does not."""
        na = KnowledgeQualityScanner._normalize(a)
        nb = KnowledgeQualityScanner._normalize(b)
        nums_a = set(re.findall(r"\d+(?:[.,]\d+)?", na))
        nums_b = set(re.findall(r"\d+(?:[.,]\d+)?", nb))
        if nums_a and nums_b and nums_a != nums_b:
            return True
        neg = ("không ", "not ", "chưa ", "false")
        pol_a = any(n in na for n in neg)
        pol_b = any(n in nb for n in neg)
        if pol_a != pol_b:
            return True
        return False
