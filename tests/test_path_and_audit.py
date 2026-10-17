import json
from pathlib import Path
import pytest

from quan_ai_brain.core.audit import AuditLogger
from quan_ai_brain.tools.path_guard import PathGuard, PathOutsideWorkspaceError


def test_path_guard_allows_relative_path_and_rejects_escape(tmp_path: Path):
    guard = PathGuard(tmp_path)
    assert guard.resolve("docs/test.md") == (tmp_path / "docs" / "test.md").resolve()
    with pytest.raises(PathOutsideWorkspaceError):
        guard.resolve("../../outside.txt")
    with pytest.raises(PathOutsideWorkspaceError):
        guard.resolve("C:\\private\\secret.txt")


def test_audit_redacts_secrets_before_persisting(tmp_path: Path):
    logger = AuditLogger(tmp_path)
    logger.record("test.event", {"note": "Bearer token-abc", "password": "dont-log-me"})
    log_path = tmp_path / "logs" / "audit.jsonl"
    raw = log_path.read_text(encoding="utf-8")
    assert "token-abc" not in raw
    assert "dont-log-me" not in raw
    event = json.loads(raw)
    assert event["event_type"] == "test.event"
