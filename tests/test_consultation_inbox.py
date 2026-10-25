"""Tests for ConsultationStore and ConsultationTicket in QUAN AI BRAIN."""
from __future__ import annotations

import pytest

from quan_ai_brain.governance.consultation_inbox import (
    ConsultationCategory,
    ConsultationStore,
    ConsultationTicket,
    TicketStatus,
)


def test_consultation_store_init_and_seed():
    store = ConsultationStore(":memory:")
    tickets = store.list_tickets()
    assert len(tickets) >= 3
    pending_count = store.count_pending()
    assert pending_count == len(tickets)

    ticket = store.get_ticket("cst_ollama_r4")
    assert ticket is not None
    assert ticket.category == ConsultationCategory.CODE_PATCH_R4
    assert ticket.status == TicketStatus.PENDING_REVIEW
    store.close()


def test_consultation_ticket_create():
    store = ConsultationStore(":memory:")
    t = ConsultationTicket(
        ticket_id="cst_test_01",
        title="Test Consultation Question",
        category=ConsultationCategory.TASK_ORCHESTRATION,
        priority="URGENT",
        context_summary="Need owner review on high risk task.",
        proposed_action="Execute with supervisor sign-off.",
        options=[{"id": "opt1", "label": "Approve", "action": "APPROVE"}],
    )
    tid = store.create_ticket(t)
    assert tid == "cst_test_01"

    fetched = store.get_ticket("cst_test_01")
    assert fetched is not None
    assert fetched.priority == "URGENT"
    assert fetched.status == TicketStatus.PENDING_REVIEW
    store.close()


def test_consultation_respond():
    store = ConsultationStore(":memory:")
    # Respond with APPROVE
    updated = store.respond_ticket("cst_ollama_r4", decision="APPROVE", guidance="Đồng ý triển khai ngay")
    assert updated.status == TicketStatus.APPROVED
    assert updated.owner_decision == "APPROVE"
    assert updated.owner_guidance == "Đồng ý triển khai ngay"
    assert updated.resolved_at is not None

    # Respond with DIRECT
    updated2 = store.respond_ticket("cst_satellite_dc", decision="DIRECT", guidance="Chỉ đọc thư mục docs/ và SOP")
    assert updated2.status == TicketStatus.DIRECTED
    assert updated2.owner_guidance == "Chỉ đọc thư mục docs/ và SOP"

    # Pending count decreased
    assert store.count_pending() == 1
    store.close()
