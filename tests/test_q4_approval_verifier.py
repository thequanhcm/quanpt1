"""Tests Q-4 approval verifier (01/11/2026, ĐÃ DUYỆT) — fail-closed semantics."""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

WS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WS / "src"))

from quan_ai_brain.governance.approval_verifier import (  # noqa: E402
    GovernanceApprovalVerifier,
    Q4BatchLedger,
)


@pytest.fixture()
def gov_db(tmp_path: Path) -> Path:
    """governance.db tối giản: approval_cards + approvals đúng schema."""
    p = tmp_path / "governance.db"
    con = sqlite3.connect(p)
    con.execute(
        """CREATE TABLE approval_cards (
            task_code TEXT PRIMARY KEY, title TEXT, card_markdown TEXT,
            status TEXT, version INTEGER DEFAULT 1,
            created_at_utc TEXT, updated_at_utc TEXT,
            ttl_expires_at_utc TEXT, request_id TEXT DEFAULT '',
            evidence_json TEXT DEFAULT '[]')"""
    )
    con.execute(
        """CREATE TABLE approvals (
            approval_id TEXT PRIMARY KEY, request_id TEXT, approver TEXT,
            tool_id TEXT, action TEXT, params_json TEXT, resource_scope TEXT,
            risk_level INTEGER, fingerprint TEXT, status TEXT,
            granted_at_utc TEXT, expires_at_utc TEXT, consumed INTEGER DEFAULT 0,
            consumed_at_utc TEXT, revoked INTEGER DEFAULT 0,
            revocation_reason TEXT, auth_method TEXT, notes TEXT, audit_ref TEXT)"""
    )
    con.commit()
    con.close()
    return p


def _insert_card(gov_db: Path, task_code: str, status: str, auth: str,
                 ttl_hours: int = 48, request_id: str = "REQ-Q4-TEST") -> None:
    ttl = (datetime.now(timezone.utc) + timedelta(hours=ttl_hours)).isoformat()
    evidence = json.dumps([{
        "event": "APPROVED", "approver": "quanpt1", "auth_method": auth,
        "at": datetime.now(timezone.utc).isoformat(),
    }])
    con = sqlite3.connect(gov_db)
    con.execute(
        "INSERT INTO approval_cards VALUES (?,?,?,?,1,?,?,?,?,?)",
        (task_code, "Q-4 batch test", "# card", status,
         datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat(),
         ttl, request_id, evidence),
    )
    con.commit()
    con.close()


def _insert_approval(gov_db: Path, request_id: str = "REQ-Q4-TEST",
                     approver: str = "quanpt1", status: str = "completed") -> None:
    con = sqlite3.connect(gov_db)
    con.execute(
        "INSERT INTO approvals (approval_id, request_id, approver, tool_id, action, "
        "params_json, resource_scope, risk_level, fingerprint, status, granted_at_utc, "
        "expires_at_utc, consumed, revoked) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,0,0)",
        ("apv-1", request_id, approver, "netchat_approval", "owner_decision",
         "{}", "workspace", 2, "fp", status,
         datetime.now(timezone.utc).isoformat(),
         (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()),
    )
    con.commit()
    con.close()


def test_fail_closed_no_card(gov_db):
    v = GovernanceApprovalVerifier(gov_db, workspace=gov_db.parent)
    assert v.verify("cand-1", "Quanpt1", "TASK-Q4-NOPE") is False


def test_fail_closed_card_not_approved(gov_db):
    _insert_card(gov_db, "TASK-Q4-A", status="PENDING_APPROVAL", auth="netchat_dm")
    _insert_approval(gov_db)
    v = GovernanceApprovalVerifier(gov_db, workspace=gov_db.parent)
    assert v.verify("cand-1", "Quanpt1", "TASK-Q4-A") is False


def test_fail_closed_bad_auth_method(gov_db):
    _insert_card(gov_db, "TASK-Q4-B", status="APPROVED", auth="llm_generated_string")
    _insert_approval(gov_db)
    v = GovernanceApprovalVerifier(gov_db, workspace=gov_db.parent)
    assert v.verify("cand-1", "Quanpt1", "TASK-Q4-B") is False


def test_fail_closed_missing_approvals_record(gov_db):
    _insert_card(gov_db, "TASK-Q4-C", status="APPROVED", auth="netchat_dm")
    # KHÔNG insert approvals record
    v = GovernanceApprovalVerifier(gov_db, workspace=gov_db.parent)
    assert v.verify("cand-1", "Quanpt1", "TASK-Q4-C") is False


def test_fail_closed_expired_ttl(gov_db):
    _insert_card(gov_db, "TASK-Q4-D", status="APPROVED", auth="netchat_dm", ttl_hours=-1)
    _insert_approval(gov_db)
    v = GovernanceApprovalVerifier(gov_db, workspace=gov_db.parent)
    assert v.verify("cand-1", "Quanpt1", "TASK-Q4-D") is False


def test_fail_closed_wrong_owner(gov_db):
    _insert_card(gov_db, "TASK-Q4-E", status="APPROVED", auth="netchat_dm")
    _insert_approval(gov_db)
    v = GovernanceApprovalVerifier(gov_db, workspace=gov_db.parent)
    assert v.verify("cand-1", "tony_bot", "TASK-Q4-E") is False


def test_pass_valid_approval(gov_db):
    _insert_card(gov_db, "TASK-Q4-OK", status="APPROVED", auth="netchat_dm")
    _insert_approval(gov_db)
    v = GovernanceApprovalVerifier(gov_db, workspace=gov_db.parent)
    assert v.verify("cand-1", "Quanpt1", "TASK-Q4-OK") is True


def test_pass_owner_desktop_directive(gov_db):
    _insert_card(gov_db, "TASK-Q4-OK2", status="APPROVED", auth="owner_desktop_directive")
    _insert_approval(gov_db)
    v = GovernanceApprovalVerifier(gov_db, workspace=gov_db.parent)
    assert v.verify("cand-1", "Quanpt1", "TASK-Q4-OK2") is True


def test_ledger_one_time_use(gov_db):
    _insert_card(gov_db, "TASK-Q4-ONCE", status="APPROVED", auth="netchat_dm")
    _insert_approval(gov_db)
    v = GovernanceApprovalVerifier(gov_db, workspace=gov_db.parent)
    assert v.verify("cand-1", "Quanpt1", "TASK-Q4-ONCE") is True
    # Ledger ghi DONE → verify fail (1-lần-dùng)
    ledger = Q4BatchLedger(gov_db.parent)
    ledger.mark_in_progress("TASK-Q4-ONCE", "b1")
    ledger.mark_done("TASK-Q4-ONCE", 10)
    assert v.verify("cand-2", "Quanpt1", "TASK-Q4-ONCE") is False


def test_ledger_resume_in_progress(gov_db):
    _insert_card(gov_db, "TASK-Q4-RES", status="APPROVED", auth="netchat_dm")
    _insert_approval(gov_db)
    v = GovernanceApprovalVerifier(gov_db, workspace=gov_db.parent)
    ledger = Q4BatchLedger(gov_db.parent)
    ledger.mark_in_progress("TASK-Q4-RES", "b1")
    # IN_PROGRESS (chưa DONE) → vẫn verify pass để resume crash-safely
    assert v.verify("cand-1", "Quanpt1", "TASK-Q4-RES") is True


def test_empty_evidence_fail_closed(gov_db):
    v = GovernanceApprovalVerifier(gov_db, workspace=gov_db.parent)
    assert v.verify("cand-1", "Quanpt1", "") is False
    assert v.verify("cand-1", "Quanpt1", None) is False
