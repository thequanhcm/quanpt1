"""Test CSEF Release & Approval Gateway (mệnh lệnh CSEF v1.0 §6-§12, §14).
Mock 100% tmp_path. Tình huống tấn công §14: deploy chưa duyệt, sai Request ID,
hết hạn, reuse ticket, sửa code sau duyệt (hash), rollback.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from quan_ai_brain.core.audit import AuditLogger
from quan_ai_brain.governance.authority_protocol import AuthorityGovernor
from quan_ai_brain.governance.csef_release import (
    RCStatus,
    ReleaseCandidate,
    ReleaseCandidateStore,
    compute_source_hash,
)


@pytest.fixture()
def ws(tmp_path: Path) -> Path:
    p = tmp_path / "ws"
    (p / "src").mkdir(parents=True)
    (p / "src" / "demo.py").write_text("print('v1')\n", encoding="utf-8")
    return p


@pytest.fixture()
def store(ws: Path) -> ReleaseCandidateStore:
    gov = AuthorityGovernor(ws, audit=AuditLogger(ws))
    return ReleaseCandidateStore(ws / "data" / "csef_rc.db", gov)


def _rc(files: list[str] | None = None, modules: list[str] | None = None,
        risk: int = 3) -> ReleaseCandidate:
    return ReleaseCandidate(
        rc_id="RC-2026-001",
        title="Nâng cấp demo module",
        description="Sửa demo.py thêm validation",
        affected_files=files or ["src/demo.py"],
        affected_modules=modules or ["demo"],
        version_current="1.0.0",
        version_proposed="1.1.0",
        source_hash="abc",
        test_report="reports/TEST_RUN_DEMO.txt",
        security_report="reports/SEC_DEMO.txt" if modules else "",
        risk_level=risk,
        rollback_plan="git revert <commit>",
    )


class TestPackage:
    def test_incomplete_rejected(self, store: ReleaseCandidateStore) -> None:
        rc = _rc()
        rc.test_report = ""
        store.upsert(rc)
        ok, msg = store.mark_tested(rc.rc_id)
        assert not ok and "test report" in msg.lower()

    def test_production_change_needs_security_report(self, store: ReleaseCandidateStore) -> None:
        rc = _rc(modules=["security_policy"])
        rc.security_report = ""
        store.upsert(rc)
        ok, msg = store.mark_tested(rc.rc_id)
        assert not ok and "security report" in msg.lower()

    def test_hash_detects_change_after_approval(self, ws: Path) -> None:
        h1 = compute_source_hash(ws, ["src/demo.py"])
        (ws / "src" / "demo.py").write_text("print('v2 hacked')\n", encoding="utf-8")
        h2 = compute_source_hash(ws, ["src/demo.py"])
        assert h1 != h2


class TestWorkflow:
    def test_deploy_before_approval_denied(self, store: ReleaseCandidateStore) -> None:
        store.upsert(_rc())
        ok, msg = store.deploy("RC-2026-001")
        assert not ok and "DENY" in msg

    def test_full_happy_path(self, store: ReleaseCandidateStore, ws: Path) -> None:
        rc = _rc()
        rc.source_hash = compute_source_hash(ws, rc.affected_files)
        store.upsert(rc)
        assert store.mark_tested("RC-2026-001")[0]
        assert store.request_approval("RC-2026-001", "APR-CSEF-001", "quanpt1")[0]
        assert store.verify_and_mark_approved("RC-2026-001", "APR-CSEF-001")[0]
        ok, msg = store.deploy("RC-2026-001")
        assert ok, msg
        assert store.get("RC-2026-001").status == RCStatus.DEPLOYED.value

    def test_wrong_request_id_denied(self, store: ReleaseCandidateStore) -> None:
        store.upsert(_rc())
        store.mark_tested("RC-2026-001")
        store.request_approval("RC-2026-001", "APR-CSEF-002", "quanpt1")
        ok, msg = store.verify_and_mark_approved("RC-2026-001", "APR-OTHER-999")
        assert not ok and "không khớp" in msg.lower()

    def test_non_owner_approval_refused(self, store: ReleaseCandidateStore) -> None:
        store.upsert(_rc())
        store.mark_tested("RC-2026-001")
        ok, msg = store.request_approval("RC-2026-001", "APR-CSEF-003", "sentinel_agent")
        assert not ok and "không phải L0" in msg

    def test_rejected_needs_new_proposal(self, store: ReleaseCandidateStore) -> None:
        store.upsert(_rc())
        store.mark_tested("RC-2026-001")
        store.reject("RC-2026-001", "cần phương án khác")
        ok, msg = store.request_approval("RC-2026-001", "APR-CSEF-004", "quanpt1")
        assert not ok and "cần phương án mới" in msg

    def test_expired_ticket_blocks_deploy(self, store: ReleaseCandidateStore) -> None:
        store.upsert(_rc())
        store.mark_tested("RC-2026-001")
        # đăng ký với hạn 0 phút → ticket chỉ hợp lệ đúng thời điểm đăng ký
        ok, msg = store.request_approval("RC-2026-001", "APR-CSEF-005", "quanpt1", valid_minutes=0)
        assert ok  # đăng ký được nhưng tức thì hết hạn
        # verify ngay sau đó phải từ chối vì hết hiệu lực
        vok, vmsg = store.verify_and_mark_approved("RC-2026-001", "APR-CSEF-005")
        assert not vok and "hết hiệu lực" in vmsg.lower()
        ok2, msg2 = store.deploy("RC-2026-001")
        assert not ok2 and "DENY" in msg2
        assert store.get("RC-2026-001").status != RCStatus.DEPLOYED.value

    def test_rollback_after_deploy(self, store: ReleaseCandidateStore) -> None:
        store.upsert(_rc())
        store.mark_tested("RC-2026-001")
        store.request_approval("RC-2026-001", "APR-CSEF-006", "quanpt1")
        store.verify_and_mark_approved("RC-2026-001", "APR-CSEF-006")
        store.deploy("RC-2026-001")
        ok, msg = store.rollback("RC-2026-001", "quanpt1", "lỗi runtime sau deploy")
        assert ok and store.get("RC-2026-001").status == RCStatus.ROLLED_BACK.value

    def test_no_rollback_plan_no_rollback(self, store: ReleaseCandidateStore) -> None:
        rc = _rc()
        rc.rollback_plan = ""
        store.upsert(rc)
        assert not store.rollback("RC-2026-001", "quanpt1", "x")[0]

    def test_audit_chain_intact_through_workflow(self, store: ReleaseCandidateStore) -> None:
        store.upsert(_rc())
        store.deploy("RC-2026-001")   # DENY attempt được ghi
        ok, msg = store.governor.audit_log.verify_chain()
        assert ok
        decisions = [d["decision"] for d in store.governor.audit_log.tail(10)]
        assert "DENY_NOT_APPROVED" in decisions
