"""Tests for tools/validate_and_report.py generator."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from validate_and_report import (  # noqa: E402
    build_report,
    git_info,
    is_sensitive_name,
    parse_pytest_summary,
    safe_project_inventory,
)


def test_is_sensitive_name_detection():
    """Verify sensitive filenames and extensions are accurately identified."""
    assert is_sensitive_name(".env")
    assert is_sensitive_name(".env.production")
    assert is_sensitive_name("credentials.json")
    assert is_sensitive_name("api_secret.txt")
    assert is_sensitive_name("client_token.key")
    assert is_sensitive_name("private_key.pem")
    assert is_sensitive_name("brain.db")
    assert is_sensitive_name("cache.sqlite3")

    # Safe files must not be flagged
    assert not is_sensitive_name("models.py")
    assert not is_sensitive_name("PROJECT_STATUS.md")
    assert not is_sensitive_name("pyproject.toml")


def test_parse_pytest_summary():
    """Verify pytest output parsing extracts counts, duration, and verdict."""
    sample_success = "==================== 28 passed in 0.18s ===================="
    res = parse_pytest_summary(sample_success, exit_code=0)
    assert res["verdict"] == "PASS"
    assert res["passed"] == 28
    assert res["failed"] == 0
    assert res["duration"] == "0.18"

    sample_failure = "FAILED test_something.py::test_fail\n==== 1 failed, 27 passed in 0.25s ===="
    res_fail = parse_pytest_summary(sample_failure, exit_code=1)
    assert "FAIL" in res_fail["verdict"]
    assert res_fail["failed"] == 1
    assert res_fail["passed"] == 27

    sample_error = "SyntaxError: invalid syntax"
    res_err = parse_pytest_summary(sample_error, exit_code=2)
    assert "BLOCKED" in res_err["verdict"]


def test_build_report_structure_and_sections():
    """Verify generated report contains all 9 required sections and continuation context."""
    report = build_report(
        exit_code=0,
        command="python -m pytest",
        test_output="28 passed in 0.15s",
    )

    required_sections = [
        "## 1. Thông tin phiên làm việc",
        "## 2. Tóm tắt điều hành",
        "## 3. Thay đổi mã nguồn",
        "## 4. Kết quả kiểm thử",
        "## 5. Danh mục module & Trạng thái hiện tại",
        "## 6. Ma trận tích hợp hệ thống ngoại vi",
        "## 7. An toàn và phục hồi",
        "## 8. Danh mục tài liệu ngữ cảnh an toàn",
        "## 9. Việc cần làm tiếp theo",
        "## CONTINUATION CONTEXT FOR CHATGPT",
    ]
    for section in required_sections:
        assert section in report, f"Missing section: {section}"

    assert any(s in report for s in ("SPRINT 4", "Sprint 4", "SPRINT 3B", "Sprint 3B", "SPRINT 3A", "Sprint 3A", "SPRINT 2C", "Sprint 2C", "SPRINT 2B", "Sprint 2B"))
    assert "Memory Engine V1" in report
    assert "CONTINUATION CONTEXT FOR CHATGPT" in report
    assert "PROTECTED_EXTERNAL_PROJECTS" in report
    # Sprint 1 truthfulness fields (approved D4): test suite identity, freshness, verification status
    assert "`test_suite_identity`" in report
    assert "`report_freshness`" in report
    assert "`verification_status`" in report


def test_report_on_test_failure():
    """Verify report still generates and truthfully highlights failures when tests fail."""
    report = build_report(
        exit_code=1,
        command="python -m pytest",
        test_output="1 failed, 20 passed in 0.12s",
    )
    assert "FAIL" in report
    assert "exit code 1" in report.lower() or "failed" in report.lower()


def test_report_test_count_consistency_122():
    """Verify that Executive Summary, Section 4, and Continuation Context have consistent test counts."""
    sample_122_output = "122 passed in 1.63s"
    report = build_report(
        exit_code=0,
        command="python -m pytest",
        test_output=sample_122_output,
    )
    # Check Executive Summary
    assert "122/122" in report or "122" in report
    # Make sure old hardcoded 120/120 does not appear anywhere
    assert "120/120" not in report

    # Check that parsed stats match in Continuation Context
    assert "total_tests: 122" in report
    assert "passed: 122" in report
    assert "failed: 0" in report
    assert "verdict: PASS" in report


def test_parse_pytest_zero_tests_discovered():
    """Verify zero tests does not falsely claim PASS."""
    res = parse_pytest_summary("no tests ran", exit_code=0)
    assert "NOT_VERIFIED" in res["verdict"]
    assert res["total"] == 0
    assert res["passed"] == 0


def test_safe_inventory_excludes_secrets_and_build_dirs():
    """Verify safe inventory excludes sensitive files, databases, and caches."""
    inventory = safe_project_inventory()
    paths = [p for p, _ in inventory]

    for p in paths:
        assert not p.startswith(".venv/"), f"Leaked .venv path: {p}"
        assert not p.startswith(".git/"), f"Leaked .git path: {p}"
        assert not p.startswith("data/"), f"Leaked data/ path: {p}"
        assert not p.endswith(".db"), f"Leaked db file: {p}"
        assert not p.endswith(".log"), f"Leaked log file: {p}"
        assert "secret" not in p.lower(), f"Sensitive keyword in path: {p}"


def test_git_info_is_robust():
    """Verify git_info function returns structured dict safely."""
    info = git_info()
    assert isinstance(info, dict)
    assert "available" in info
    assert "branch" in info
    assert "status_text" in info
