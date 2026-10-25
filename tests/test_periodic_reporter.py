"""Tests for PeriodicLearningReporter in QUAN AI BRAIN."""
from __future__ import annotations

from pathlib import Path
import pytest

from quan_ai_brain.governance.consultation_inbox import ConsultationStore, TicketStatus
from quan_ai_brain.learning.periodic_reporter import PeriodicLearningReport, PeriodicLearningReporter
from quan_ai_brain.memory.sqlite_store import MemoryStore


def test_periodic_reporter_initialization_and_seed(tmp_path: Path):
    mem_store = MemoryStore(":memory:")
    cst_store = ConsultationStore(":memory:")
    reporter = PeriodicLearningReporter(
        workspace=tmp_path,
        db_path=":memory:",
        memory_store=mem_store,
        consultation_store=cst_store,
    )

    reports = reporter.list_reports()
    assert len(reports) >= 1
    baseline = reports[0]
    assert baseline.cycle_number == 1
    assert "Báo Cáo Tự Học" in baseline.title
    assert baseline.confidence_score >= 0.90
    assert len(baseline.upgrade_proposals) >= 1


def test_trigger_learning_cycle(tmp_path: Path):
    mem_store = MemoryStore(":memory:")
    cst_store = ConsultationStore(":memory:")
    reporter = PeriodicLearningReporter(
        workspace=tmp_path,
        db_path=":memory:",
        memory_store=mem_store,
        consultation_store=cst_store,
    )

    # Trigger cycle #2
    new_report = reporter.trigger_learning_cycle(trigger_reason="owner_manual_request")
    assert new_report.cycle_number == 2
    assert "Kỳ 2" in new_report.title
    assert len(new_report.gaps_detected) >= 1
    assert len(new_report.quarantined_candidates) >= 1

    # Check consultation ticket was automatically created
    tickets = cst_store.list_tickets()
    cycle_ticket = next((t for t in tickets if "Chu kỳ #2" in t.title or "cycle_2" in t.ticket_id), None)
    assert cycle_ticket is not None
    assert cycle_ticket.status == TicketStatus.PENDING_REVIEW

    # Latest report should be cycle 2
    latest = reporter.get_latest_report()
    assert latest is not None
    assert latest.cycle_number == 2
