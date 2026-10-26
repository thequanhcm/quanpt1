"""Tests for the NetChat command center (owner<->assistant control channel)."""
from __future__ import annotations

import sqlite3

import pytest

from tools.netchat_command_center import (
    detect_intent,
    handle_approve,
    handle_help,
    handle_knowledge,
    handle_report,
    handle_status,
    handle_tasks,
    route_message,
)


# ---------------------------------------------------------------------------
# Intent detection
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("text,expected", [
    ("phê duyệt", "approve"),
    ("duyệt", "approve"),
    ("phe duyet", "approve"),
    ("trạng thái", "status"),
    ("hiện trạng hệ thống", "status"),
    ("báo cáo", "report"),
    ("nhiệm vụ", "tasks"),
    ("tri thức", "knowledge"),
    ("giúp", "help"),
    # read-only command keyword mid-sentence is fine
    ("cho anh xem hiện trạng với", "status"),
])
def test_detect_intent(text, expected):
    assert detect_intent(text) == expected


@pytest.mark.parametrize("text", [
    "",
    "   ",
    "1+1 là bao nhiêu?",
    "Xin chào bot",
    # SAFETY: questions mentioning a state-changing keyword must NOT execute
    "anh có thể phản hồi phê duyệt được không?",
    "em được phép phê duyệt hồ sơ chứ?",
])
def test_detect_intent_none_for_free_text(text):
    assert detect_intent(text) is None


# ---------------------------------------------------------------------------
# Handlers on temp fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def consultations_db(tmp_path, monkeypatch):
    """Command center pointed at a temp workspace with a pending ticket.

    ConsultationStore seeds DEFAULT_SEED_TICKETS (cst_ollama_r4,
    cst_satellite_dc, cst_nightly_learning) into an empty DB by design.
    The seed tickets are dated 2026-10-19, so our fixture ticket
    (dated 2026-10-26) is NOT the oldest — tests account for FIFO order.
    """
    import tools.netchat_command_center as cc

    ws = tmp_path
    (ws / "data").mkdir(exist_ok=True)
    from quan_ai_brain.governance.consultation_inbox import ConsultationStore, ConsultationTicket, ConsultationCategory, TicketStatus

    store = ConsultationStore(str(ws / "data" / "consultations.db"))
    store.create_ticket(ConsultationTicket(
        ticket_id="cst_test_001",
        title="[R4 Cần Phê Duyệt] Bước 1: Sửa cấu hình",
        category=ConsultationCategory.TASK_ORCHESTRATION,
        priority="HIGH",
        context_summary="Kiểm thử phê duyệt qua NetChat",
        proposed_action="Thực hiện thay đổi cấu hình thử nghiệm",
        options=[{"action": "APPROVE", "label": "Chấp thuận"}],
        evidence_notes="fixture",
        metadata={},
    ))
    store.close()

    monkeypatch.setattr(cc, "WORKSPACE", ws)
    return ws


def test_handle_approve_resolves_pending_ticket(consultations_db):
    reply = handle_approve()
    assert "ĐÃ PHÊ DUYỆT" in reply
    # FIFO: the oldest seed ticket (cst_ollama_r4, 2026-10-19) goes first
    assert "cst_ollama_r4" in reply
    # Ticket is now APPROVED in the real store
    from quan_ai_brain.governance.consultation_inbox import ConsultationStore

    store = ConsultationStore(str(consultations_db / "data" / "consultations.db"))
    ticket = store.get_ticket("cst_ollama_r4")
    store.close()
    assert ticket.status.value == "APPROVED"


def test_handle_approve_drains_fifo(consultations_db):
    # 4 pending (3 seeds + 1 fixture): repeated commands drain oldest first
    ids_seen = []
    for _ in range(4):
        reply = handle_approve()
        assert "ĐÃ PHÊ DUYỆT" in reply
        ids_seen.append(reply.split("Hồ sơ: ")[1].split("\n")[0])
    assert ids_seen[0] == "cst_ollama_r4"
    assert set(ids_seen) == {"cst_ollama_r4", "cst_satellite_dc", "cst_nightly_learning", "cst_test_001"}
    # Now honestly empty
    reply = handle_approve()
    assert "không có hồ sơ" in reply.lower()


def test_handle_status_reports_live_probes(consultations_db):
    reply = handle_status()
    # Format ngắn gọn (27/10): 🟢 ONLINE / 🔴 OFFLINE / 📋 Nhiệm vụ
    assert "ONLINE" in reply and "OFFLINE" in reply
    assert "core_server" in reply
    assert "ollama_daemon" in reply  # honesty: offline is reported
    assert "Nhiệm vụ" in reply


def test_handle_tasks_counts_by_status(consultations_db):
    db = consultations_db / "data" / "tasks.db"
    conn = sqlite3.connect(db)
    conn.execute(
        "CREATE TABLE durable_tasks (task_id TEXT PRIMARY KEY, status TEXT, goal TEXT, created_at_utc TEXT)"
    )
    conn.execute("INSERT INTO durable_tasks VALUES ('t1','PENDING','Việc A','2026-10-26T00:00:00Z')")
    conn.execute("INSERT INTO durable_tasks VALUES ('t2','COMPLETED','Việc B','2026-10-26T00:00:00Z')")
    conn.commit()
    conn.close()
    reply = handle_tasks()
    assert "PENDING: 1" in reply
    assert "COMPLETED: 1" in reply


def test_handle_knowledge_counts(consultations_db):
    db = consultations_db / "data" / "brain.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE semantic_memory (id TEXT, created_at_utc TEXT, statement TEXT, source_ref TEXT, approved_by TEXT, regression_passed INTEGER)")
    conn.execute("CREATE TABLE candidate_knowledge (id TEXT, created_at_utc TEXT, statement TEXT, source_ref TEXT, rationale TEXT, status TEXT, decision_note TEXT)")
    conn.execute("CREATE TABLE episodes (id TEXT, created_at_utc TEXT, kind TEXT, summary TEXT, source_ref TEXT, status TEXT, metadata_json TEXT)")
    conn.execute("INSERT INTO semantic_memory VALUES ('s1','2026','X','X','t',1)")
    conn.execute("INSERT INTO candidate_knowledge VALUES ('c1','2026','Y','Y','Confidence: 0.9','quarantined',NULL)")
    conn.commit()
    conn.close()
    reply = handle_knowledge()
    assert "Đã duyệt (semantic): 1" in reply
    assert "quarantined): 1" in reply


def test_handle_report_lists_newest(consultations_db):
    rd = consultations_db / "bao cao xay dung he thong"
    rd.mkdir(exist_ok=True)
    (rd / "BAO_CAO_TEST.md").write_text("# test", encoding="utf-8")
    reply = handle_report()
    assert "BAO_CAO_TEST.md" in reply


def test_route_message_routes_commands():
    intent, reply = route_message("giúp")
    assert intent == "help"
    assert "KÊNH LÀM VIỆC" in reply


def test_route_message_free_text_falls_back():
    intent, reply = route_message("Điểm khác nhau giữa TCP và UDP là gì?")
    assert intent is None
    assert reply == ""
