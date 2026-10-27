"""Tests — Master Prompt V7 Cấp 1: v7_skills.py + workflow_memory.py + SkillRegistry V7.

Phủ 10 lớp test bắt buộc §3.5: input hợp lệ, input không hợp lệ, dữ liệu thiếu,
dữ liệu mâu thuẫn, nguồn unavailable, timeout/nguồn lỗi, quyền không đủ,
yêu cầu vượt quyền (read-only chứng minh), output sai schema, từ chối/fail-honest.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, "src")

import pytest

from quan_ai_brain.cognition.skill_registry import SkillRegistry, SkillStatus
from quan_ai_brain.cognition.v7_skills import (
    analyze_email,
    cross_source_evidence_analysis,
    owner_advisory_report,
    progress_risk_detection,
    reconcile_task_status,
)
from quan_ai_brain.cognition.workflow_memory import WorkflowMemory

VALID_EMAIL = """From: Nguyen Van A
To: quanpt1@viettel.com.vn
Subject: Yeu cau kiem tra tien do du an Datacenter

Chao anh Quan,

Yeu cầu anh kiểm tra tiến độ các hạng mục của dự án Datacenter.
Deadline: 30/11/2026
- Nhiệm vụ 1: cài đặt server
- Nhiệm vụ 2: cấu hình mạng

Cam kết sẽ hoàn thành và báo cáo trước hạn.
Khi nào có kết quả cho em biết được không?
"""


# ---------------------------------------------------------------------------
# EMAIL_ANALYSIS
# ---------------------------------------------------------------------------
class TestEmailAnalysis:
    def test_valid_email_extracts_fields(self):
        out = analyze_email(VALID_EMAIL)
        assert out["analysis"]["sender"] == "Nguyen Van A"
        assert "quanpt1" in out["analysis"]["recipient"].lower()
        assert out["analysis"]["subject"] != "UNKNOWN"
        assert "kiem tra tien do" in out["analysis"]["request"].lower() or "kiểm tra tiến độ" in out["analysis"]["request"].lower()
        assert out["analysis"]["deadline"] == "30/11/2026"
        assert len(out["commitments"]) >= 1
        assert len(out["questions"]) >= 1

    def test_invalid_input_rejected(self):
        with pytest.raises(ValueError):
            analyze_email("quá ngắn")
        with pytest.raises(ValueError):
            analyze_email(None)  # type: ignore[arg-type]
        with pytest.raises(ValueError):
            analyze_email(123)  # type: ignore[arg-type]

    def test_missing_data_fail_honest(self):
        out = analyze_email("Đây là một đoạn văn bản dài hơn hai mươi ký tự nhưng không có header email nào cả.")
        assert out["analysis"]["sender"] == "UNKNOWN"
        assert out["analysis"]["deadline"] == "UNKNOWN"

    def test_inferences_separated(self):
        out = analyze_email(VALID_EMAIL)
        # mọi suy luận phải nằm riêng và được đánh dấu
        for inf in out["inferences"]:
            assert "suy luận" in inf.lower() or "xác nhận" in inf.lower()

    def test_sources_declared(self):
        out = analyze_email(VALID_EMAIL)
        assert "email_text (do chủ cung cấp trực tiếp)" in out["sources_accessed"]
        assert any("BLOCKED" in s for s in out["sources_blocked"])


# ---------------------------------------------------------------------------
# TASK_STATUS_RECONCILIATION
# ---------------------------------------------------------------------------
@pytest.fixture()
def ws_with_tasks(tmp_path: Path) -> Path:
    """Workspace test có data/tasks.db + todos.db schema thật."""
    data = tmp_path / "data"
    data.mkdir(parents=True)
    conn = sqlite3.connect(data / "tasks.db")
    conn.execute(
        """CREATE TABLE durable_tasks (
            task_id TEXT PRIMARY KEY, correlation_id TEXT, idempotency_key TEXT,
            goal TEXT, risk_level INTEGER, autonomy_level INTEGER, status TEXT,
            acceptance_criteria_json TEXT, approved_scope_json TEXT,
            created_at_utc TEXT, updated_at_utc TEXT, completed_at_utc TEXT,
            resource_budget_json TEXT, retry_count INTEGER, max_retries INTEGER,
            error_message TEXT, evidence_refs_json TEXT, result_payload_json TEXT,
            checkpoint_data_json TEXT)"""
    )
    old = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    fresh = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO durable_tasks (task_id, goal, status, created_at_utc, updated_at_utc) VALUES (?,?,?,?,?)",
        ("task_1", "cài đặt server dự án Datacenter", "COMPLETED", old, old),
    )
    conn.execute(
        "INSERT INTO durable_tasks (task_id, goal, status, created_at_utc, updated_at_utc) VALUES (?,?,?,?,?)",
        ("task_2", "cấu hình mạng trung tâm dữ liệu", "PENDING", fresh, fresh),
    )
    conn.commit()
    conn.close()
    conn = sqlite3.connect(data / "todos.db")
    conn.execute("CREATE TABLE todos (id INTEGER PRIMARY KEY, title TEXT, due TEXT, priority TEXT, status TEXT, created_at TEXT, done_at TEXT)")
    conn.commit()
    conn.close()
    return tmp_path


class TestTaskStatusReconciliation:
    def test_reconcile_with_real_db(self, ws_with_tasks):
        analysis = analyze_email(VALID_EMAIL)
        out = reconcile_task_status(analysis, ws_with_tasks)
        assert out["conclusion"] == "RECONCILED_WITH_LIMITS"
        assert any("tasks.db" in s for s in out["sources_accessed"])
        ids = [r["task_id"] for r in out["unified_records"]]
        assert "task_1" in ids  # match theo keyword 'datacenter'
        # task_2 không khớp keyword nào của email -> bị lọc (hành vi đúng)
        rec1 = next(r for r in out["unified_records"] if r["task_id"] == "task_1")
        assert rec1["db_status"] == "COMPLETED"
        assert rec1["email_claim"] == "UNKNOWN"  # email không nêu trạng thái từng task
        assert rec1["evidence_refs"] == ["data/tasks.db#durable_tasks/task_1"]

    def test_no_sources_fail_honest(self, tmp_path):
        analysis = analyze_email(VALID_EMAIL)
        out = reconcile_task_status(analysis, tmp_path)  # workspace rỗng
        assert out["conclusion"] == "UNKNOWN"
        assert out["sources_accessed"] == []
        assert len(out["sources_blocked"]) >= 1

    def test_corrupt_db_blocked_not_crash(self, tmp_path):
        data = tmp_path / "data"
        data.mkdir(parents=True)
        (data / "tasks.db").write_text("khong phai sqlite", encoding="utf-8")
        analysis = analyze_email(VALID_EMAIL)
        out = reconcile_task_status(analysis, tmp_path)
        assert any("tasks.db" in s for s in out["sources_blocked"])

    def test_read_only_no_writes(self, ws_with_tasks):
        db = ws_with_tasks / "data" / "tasks.db"
        before = db.read_bytes()
        analysis = analyze_email(VALID_EMAIL)
        reconcile_task_status(analysis, ws_with_tasks)
        assert db.read_bytes() == before  # chứng minh read-only (yêu cầu vượt quyền bị chặn)

    def test_invalid_analysis_input(self, ws_with_tasks):
        with pytest.raises(ValueError):
            reconcile_task_status({"wrong": "shape"}, ws_with_tasks)
        with pytest.raises(ValueError):
            reconcile_task_status("not a dict", ws_with_tasks)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# CROSS_SOURCE_EVIDENCE_ANALYSIS
# ---------------------------------------------------------------------------
class TestCrossSourceEvidence:
    DB_RECORDS = [
        {"task_id": "t1", "name": "cài đặt server", "db_status": "PENDING", "evidence_refs": ["db#t1"]},
        {"task_id": "t2", "name": "cấu hình mạng", "db_status": "COMPLETED", "evidence_refs": ["db#t2"]},
    ]

    def test_conflict_detected(self):
        claims = [{"task_name": "cài đặt server", "claim_status": "hoàn thành", "evidence": "email nói xong"}]
        out = cross_source_evidence_analysis(claims, self.DB_RECORDS)
        assert len(out["conflicts"]) == 1
        c = out["conflicts"][0]
        assert c["email_says"] == "hoàn thành"
        assert c["db_says"] == "chưa làm"  # PENDING normalized
        assert c["db_evidence"] == ["db#t1"]
        assert "phân xử" in c["resolution"]

    def test_agreement_verified(self):
        claims = [{"task_name": "cấu hình mạng", "claim_status": "completed", "evidence": "email nói xong"}]
        out = cross_source_evidence_analysis(claims, self.DB_RECORDS)
        assert len(out["verified_agreements"]) == 1
        assert out["verified_agreements"][0]["status"] == "hoàn thành"

    def test_unresolved_no_match(self):
        claims = [{"task_name": "việc không tồn tại", "claim_status": "hoàn thành", "evidence": "email"}]
        out = cross_source_evidence_analysis(claims, self.DB_RECORDS)
        assert len(out["unresolved"]) == 1
        assert "không tìm thấy" in out["unresolved"][0]["reason"]

    def test_invalid_input(self):
        with pytest.raises(ValueError):
            cross_source_evidence_analysis("not list", [])  # type: ignore[arg-type]
        with pytest.raises(ValueError):
            cross_source_evidence_analysis([], "not list")  # type: ignore[arg-type]

    def test_no_default_truth(self):
        out = cross_source_evidence_analysis([], self.DB_RECORDS)
        assert "không nguồn nào được mặc định đúng" in out["rule"]


# ---------------------------------------------------------------------------
# PROGRESS_RISK_DETECTION
# ---------------------------------------------------------------------------
class TestProgressRiskDetection:
    def test_overdue_detected(self):
        rec = [{
            "task_id": "t1", "deadline": (datetime.now(timezone.utc) - timedelta(days=3)).strftime("%Y-%m-%d"),
            "db_status": "PENDING", "owner": "anh B", "evidence_refs": ["db#t1"],
        }]
        out = progress_risk_detection(rec)
        assert any(r["type"] == "OVERDUE" and r["severity"] == "HIGH" for r in out["risks"])

    def test_missing_deadline_unknown_not_risk(self):
        rec = [{"task_id": "t1", "deadline": "UNKNOWN", "db_status": "PENDING", "owner": "anh B"}]
        out = progress_risk_detection(rec)
        assert out["risks"] == []
        assert any(u["field"] == "deadline" for u in out["unknowns"])

    def test_future_deadline_no_overdue(self):
        rec = [{
            "task_id": "t1", "deadline": (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%d"),
            "db_status": "PENDING", "owner": "anh B",
        }]
        out = progress_risk_detection(rec)
        assert not any(r["type"] == "OVERDUE" for r in out["risks"])

    def test_stale_pending(self):
        old = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        rec = [{"task_id": "t2", "deadline": "UNKNOWN", "db_status": "PENDING", "last_updated": old, "owner": "x"}]
        out = progress_risk_detection(rec)
        assert any(r["type"] == "STALE_PENDING" for r in out["risks"])

    def test_missing_owner_flagged(self):
        rec = [{"task_id": "t3", "deadline": "UNKNOWN", "db_status": "DONE", "owner": "UNKNOWN"}]
        out = progress_risk_detection(rec)
        assert any(u["field"] == "owner" for u in out["unknowns"])

    def test_invalid_input(self):
        with pytest.raises(ValueError):
            progress_risk_detection("not list")  # type: ignore[arg-type]

    def test_completed_not_overdue(self):
        rec = [{
            "task_id": "t4", "deadline": "2020-01-01", "db_status": "COMPLETED", "owner": "anh C",
        }]
        out = progress_risk_detection(rec)
        assert not any(r["type"] == "OVERDUE" for r in out["risks"])


# ---------------------------------------------------------------------------
# OWNER_ADVISORY_REPORT
# ---------------------------------------------------------------------------
class TestOwnerAdvisoryReport:
    def _inputs(self):
        ea = analyze_email(VALID_EMAIL)
        rec = [{"task_id": "t1", "name": "cài đặt server", "db_status": "COMPLETED", "email_claim": "UNKNOWN",
                "deadline": "UNKNOWN", "owner": "UNKNOWN", "last_updated": "2026-10-27T10:00:00",
                "evidence_refs": ["db#t1"], "missing_fields": []}]
        reconciliation = {"unified_records": rec, "sources_accessed": ["data/tasks.db (read-only)"],
                          "sources_blocked": ["Vmail (BLOCKED)"], "reconciled_at": "2026-10-27T10:00:00"}
        risks = progress_risk_detection(rec)
        return ea, reconciliation, risks

    def test_all_12_sections(self):
        ea, rec, risks = self._inputs()
        out = owner_advisory_report(ea, rec, risks)
        assert out["sections_filled"] == 12
        for section in out["sections"]:
            assert section in out["report_md"]

    def test_traceability_present(self):
        ea, rec, risks = self._inputs()
        out = owner_advisory_report(ea, rec, risks)
        assert out["traceability"]["reconciliation_sources"] == ["data/tasks.db (read-only)"]
        assert "Vmail (BLOCKED)" in str(out["traceability"]["blocked_sources"])

    def test_no_external_action(self):
        ea, rec, risks = self._inputs()
        out = owner_advisory_report(ea, rec, risks)
        assert out["action_policy"].startswith("report_only")
        assert "không gửi email" in out["report_md"].lower() or "KHÔNG tự thực hiện" in out["report_md"]

    def test_invalid_input(self):
        with pytest.raises(ValueError):
            owner_advisory_report(None, {}, {})  # type: ignore[arg-type]
        with pytest.raises(ValueError):
            owner_advisory_report({}, "not dict", {})  # type: ignore[arg-type]

    def test_blocked_sources_listed(self):
        ea, rec, risks = self._inputs()
        out = owner_advisory_report(ea, rec, risks)
        assert "BLOCKED" in out["report_md"]


# ---------------------------------------------------------------------------
# SkillRegistry V7 fields
# ---------------------------------------------------------------------------
class TestSkillRegistryV7:
    def _reg(self, tmp_path):
        return SkillRegistry(tmp_path / "skill_registry.json")

    def test_register_v7_fields(self, tmp_path):
        reg = self._reg(tmp_path)
        s = reg.register_skill(
            name="T", goal="g", trigger_patterns=[], inputs={}, steps=["s"], tools=[], acceptance_criteria=["c"],
            input_schema={"a": "string"}, output_schema={"b": "object"},
            permissions_required=["read:x"], data_sources=["data/x.db"],
            timeout_policy="5s", error_policy="fail_closed", risk_level=3, test_suite_ref="tests/x.py",
        )
        assert s.input_schema == {"a": "string"}
        assert s.risk_level == 3
        assert s.error_policy == "fail_closed"

    def test_risk_level_validated(self, tmp_path):
        reg = self._reg(tmp_path)
        with pytest.raises(ValueError):
            reg.register_skill(name="T", goal="g", trigger_patterns=[], inputs={}, steps=["s"], tools=[],
                               acceptance_criteria=["c"], risk_level=9)

    def test_error_policy_validated(self, tmp_path):
        reg = self._reg(tmp_path)
        with pytest.raises(ValueError):
            reg.register_skill(name="T", goal="g", trigger_patterns=[], inputs={}, steps=["s"], tools=[],
                               acceptance_criteria=["c"], error_policy="yolo")

    def test_record_test_result_pass_fail_only(self, tmp_path):
        reg = self._reg(tmp_path)
        s = reg.register_skill(name="T", goal="g", trigger_patterns=[], inputs={}, steps=["s"], tools=[],
                               acceptance_criteria=["c"])
        with pytest.raises(ValueError):
            reg.record_test_result(s.skill_id, "HOÀN HẢO")  # không phải PASS/FAIL
        out = reg.record_test_result(s.skill_id, "PASS (10/10)")
        assert out.test_result.startswith("PASS")
        assert out.last_verified_at != ""

    def test_v7_ready_filter(self, tmp_path):
        reg = self._reg(tmp_path)
        s = reg.register_skill(name="T", goal="g", trigger_patterns=[], inputs={}, steps=["s"], tools=[],
                               acceptance_criteria=["c"])
        assert reg.list_skills_v7_ready() == []
        reg.transition(s.skill_id, SkillStatus.IMPLEMENTED_IN_SANDBOX, reason="built")
        reg.transition(s.skill_id, SkillStatus.TESTED, reason="tested")
        reg.transition(s.skill_id, SkillStatus.APPROVED, reason="owner ok", evidence_refs=["ev1"])
        assert reg.list_skills_v7_ready() == []  # chưa có test_result PASS
        reg.record_test_result(s.skill_id, "PASS (5/5)")
        assert len(reg.list_skills_v7_ready()) == 1


# ---------------------------------------------------------------------------
# WorkflowMemory (Cấp 3 groundwork)
# ---------------------------------------------------------------------------
class TestWorkflowMemory:
    def _wf_args(self):
        return dict(
            task_type="progress_check",
            preconditions=["source:data/tasks.db", "perm:read:tasks"],
            input_schema={"email_text": "string"},
            step_sequence=["analyze", "reconcile", "risk", "report"],
            tools_required=["sqlite3"],
            evidence_requirements=["mỗi kết luận có nguồn"],
            validation_rules=["UNKNOWN khi thiếu dữ liệu"],
            failure_modes=["DB locked -> thử lại"],
            expected_outputs=["report_md 12 mục"],
            test_refs=["tests/test_v7_skills.py"],
        )

    def test_save_and_verified_run(self, tmp_path):
        wm = WorkflowMemory(tmp_path / "wf.json")
        wf = wm.save_workflow(source_task_ref="task_test_1", **self._wf_args())
        assert wf.status == "PROPOSED"
        out = wm.record_verified_run(wf.workflow_id, "task_test_1", passed=True, measured={"duration_s": 12})
        assert out.status == "VERIFIED"
        assert out.last_verified_at != ""

    def test_find_reusable_only_verified(self, tmp_path):
        wm = WorkflowMemory(tmp_path / "wf.json")
        wf = wm.save_workflow(**self._wf_args())
        assert wm.find_reusable("progress_check") == []  # PROPOSED không tái sử dụng
        wm.record_verified_run(wf.workflow_id, "t1", passed=True, measured={})
        assert len(wm.find_reusable("progress_check")) == 1

    def test_preconditions_checked(self, tmp_path):
        wm = WorkflowMemory(tmp_path / "wf.json")
        wf = wm.save_workflow(**self._wf_args())
        wm.record_verified_run(wf.workflow_id, "t1", passed=True, measured={})
        ok = wm.check_preconditions(wf.workflow_id, available_sources=["data/tasks.db"], available_permissions=["read:tasks"])
        assert ok["reusable"] is True
        missing = wm.check_preconditions(wf.workflow_id, available_sources=[], available_permissions=[])
        assert missing["reusable"] is False
        assert "source:data/tasks.db" in missing["missing_sources"]
        assert "perm:read:tasks" in missing["missing_permissions"]

    def test_failed_run_needs_review(self, tmp_path):
        wm = WorkflowMemory(tmp_path / "wf.json")
        wf = wm.save_workflow(**self._wf_args())
        wm.record_verified_run(wf.workflow_id, "t1", passed=True, measured={})
        out = wm.record_verified_run(wf.workflow_id, "t2", passed=False, measured={"error": "x"})
        assert out.status == "NEEDS_REVIEW"
        assert wm.find_reusable("progress_check") == []

    def test_corrupt_file_fail_honest(self, tmp_path):
        p = tmp_path / "wf.json"
        p.write_text("{broken", encoding="utf-8")
        with pytest.raises(ValueError):
            WorkflowMemory(p)
        assert p.with_suffix(".json.corrupt").exists()


# ---------------------------------------------------------------------------
# E2E chain — dress rehearsal Cấp 2 trên dữ liệu test
# ---------------------------------------------------------------------------
class TestE2EChain:
    def test_full_chain_on_test_data(self, ws_with_tasks):
        ea = analyze_email(VALID_EMAIL)
        rec = reconcile_task_status(ea, ws_with_tasks)
        risks = progress_risk_detection(rec["unified_records"])
        cs = cross_source_evidence_analysis([], rec["unified_records"])
        out = owner_advisory_report(ea, rec, risks, cs)
        assert out["sections_filled"] == 12
        assert "task_1" in json.dumps(rec["unified_records"])
        assert out["traceability"]["reconciliation_sources"]
