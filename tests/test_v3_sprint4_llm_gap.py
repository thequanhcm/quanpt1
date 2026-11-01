"""Tests — V3 Sprint 4 (a): LLM Gap Detection fail-closed (mock curl 100%)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE / "src"))

from quan_ai_brain.cognition import llm_gap_detector as lgd  # noqa: E402


VALID_LLM_JSON = {
    "goal": "kiểm tra website nội bộ",
    "expected_outcome": "báo trạng thái website",
    "required_inputs": [{"key": "url", "note": "link cần kiểm tra"}],
    "conflicts": [],
    "owner_decisions_required": [],
    "acceptance_criteria": ["HTTP 200"],
    "constraints": [],
}


def _mock_run(payload, returncode=0):
    class R:
        pass

    r = R()
    r.returncode = returncode
    r.stdout = payload
    r.stderr = b""
    return lambda *a, **k: r


@pytest.fixture(autouse=True)
def with_key(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-real")


def test_valid_json_extracted(monkeypatch):
    raw = json.dumps({
        "candidates": [{"content": {"parts": [{"text": json.dumps(VALID_LLM_JSON)}]}}]
    }).encode()
    monkeypatch.setattr(lgd.subprocess, "run", _mock_run(raw))
    r = lgd.extract_gaps_with_llm("anh ơi kiểm tra giúp web nội bộ với")
    assert r is not None
    assert r["goal"] == "kiểm tra website nội bộ"
    assert r["required_inputs"][0]["key"] == "url"


def test_empty_text_returns_none_without_call(monkeypatch):
    called = {"n": 0}

    def spy(*a, **k):
        called["n"] += 1
        return _mock_run(b"")(*a, **k)

    monkeypatch.setattr(lgd.subprocess, "run", spy)
    assert lgd.extract_gaps_with_llm("   ") is None
    assert called["n"] == 0  # không gọi LLM cho text rỗng


def test_curl_failure_returns_none(monkeypatch):
    monkeypatch.setattr(lgd.subprocess, "run", _mock_run(b"", returncode=7))
    assert lgd.extract_gaps_with_llm("kiểm tra web") is None


def test_timeout_returns_none(monkeypatch):
    def boom(*a, **k):
        raise subprocess.TimeoutExpired(cmd="curl", timeout=8)

    monkeypatch.setattr(lgd.subprocess, "run", boom)
    assert lgd.extract_gaps_with_llm("kiểm tra web") is None


def test_malformed_json_returns_none(monkeypatch):
    raw = '{"candidates": [{"content": {"parts": [{"text": "khong phai json {"}]}}]}'.encode("utf-8")
    monkeypatch.setattr(lgd.subprocess, "run", _mock_run(raw))
    assert lgd.extract_gaps_with_llm("kiểm tra web") is None


def test_wrong_types_return_none_not_fixed(monkeypatch):
    bad = dict(VALID_LLM_JSON)
    bad["required_inputs"] = "không phải list"  # kiểu sai → fail-closed, KHÔNG tự sửa
    raw = json.dumps({
        "candidates": [{"content": {"parts": [{"text": json.dumps(bad)}]}}]
    }).encode()
    monkeypatch.setattr(lgd.subprocess, "run", _mock_run(raw))
    assert lgd.extract_gaps_with_llm("kiểm tra web") is None


def test_missing_goal_returns_none(monkeypatch):
    bad = {k: v for k, v in VALID_LLM_JSON.items() if k != "goal"}
    raw = json.dumps({
        "candidates": [{"content": {"parts": [{"text": json.dumps(bad)}]}}]
    }).encode()
    monkeypatch.setattr(lgd.subprocess, "run", _mock_run(raw))
    assert lgd.extract_gaps_with_llm("kiểm tra web") is None


def test_missing_key_returns_none_without_call(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    # HKCU registry thật có key → mock registry fallback bằng cách mock _read_key
    monkeypatch.setattr(lgd, "_read_key", lambda: None)
    called = {"n": 0}

    def spy(*a, **k):
        called["n"] += 1
        return _mock_run(b"")(*a, **k)

    monkeypatch.setattr(lgd.subprocess, "run", spy)
    assert lgd.extract_gaps_with_llm("kiểm tra web") is None
    assert called["n"] == 0


def test_llm_result_feeds_analyzer(monkeypatch):
    """LLM trích được url thiếu → analyzer hỏi đúng câu hỏi (tích hợp fail-closed)."""
    raw = json.dumps({
        "candidates": [{"content": {"parts": [{"text": json.dumps(VALID_LLM_JSON)}]}}]
    }).encode()
    monkeypatch.setattr(lgd.subprocess, "run", _mock_run(raw))
    import tempfile

    from quan_ai_brain.cognition.information_gap_analyzer import (
        InformationGapAnalyzer, InfoItem,
    )

    ana = InformationGapAnalyzer(workspace=tempfile.mkdtemp())
    r = lgd.extract_gaps_with_llm("kiểm tra web nội bộ giúp anh")
    assert r is not None
    a = ana.analyze_request(
        "TASK-LLM1",
        goal=r["goal"],
        acceptance_criteria=r["acceptance_criteria"],
        required_inputs=[InfoItem(key=i["key"], note=i["note"]) for i in r["required_inputs"]],
    )
    assert a.readiness is not None
    assert a.questions  # url thiếu → hỏi
