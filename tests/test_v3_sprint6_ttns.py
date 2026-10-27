"""Tests — Sprint 6-GOP hạng mục (4): TTNS lookup tool (mock subprocess 100%)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE / "src"))

from quan_ai_brain.tools import ttns_lookup as tl  # noqa: E402


def test_looks_like_ttns_query_positive():
    assert tl.looks_like_ttns_query("ngày mai em có lịch họp gì?")
    assert tl.looks_like_ttns_query("khavdt là ai?")
    assert tl.looks_like_ttns_query("số điện thoại của tamlbx")
    assert tl.looks_like_ttns_query("phòng họp tầng 24 còn trống không?")


def test_looks_like_ttns_query_negative():
    assert not tl.looks_like_ttns_query("tin thời tiết hôm nay")
    assert not tl.looks_like_ttns_query("")
    assert not tl.looks_like_ttns_query("tình hình Pin 5 thế nào")


def test_lookup_empty_question_returns_none():
    assert tl.ttns_lookup("") is None
    assert tl.ttns_lookup("   ") is None


def test_lookup_missing_script_returns_none(monkeypatch):
    monkeypatch.setattr(tl, "_SKILL_SCRIPT", tl.Path("Z:/khong-ton-tai.py"))
    assert tl.ttns_lookup("lịch họp hôm nay") is None


def test_lookup_success_parses_json(monkeypatch):
    payload = json.dumps({"answer": "3 lịch họp...", "conversationId": "abc"})

    class R:
        returncode = 0
        stdout = payload
        stderr = ""

    called = {}

    def fake_run(*a, **k):
        called["n"] = called.get("n", 0) + 1
        return R()

    monkeypatch.setattr(tl.subprocess, "run", fake_run)
    out = tl.ttns_lookup("lịch họp của tôi hôm nay")
    assert out is not None
    assert out["answer"] == "3 lịch họp..."
    assert called["n"] == 1


def test_lookup_bad_json_returns_none(monkeypatch):
    class R:
        returncode = 0
        stdout = "không phải json"
        stderr = ""

    monkeypatch.setattr(tl.subprocess, "run", lambda *a, **k: R())
    assert tl.ttns_lookup("lịch họp") is None


def test_lookup_nonzero_exit_returns_none(monkeypatch):
    class R:
        returncode = 2
        stdout = ""
        stderr = "boom"

    monkeypatch.setattr(tl.subprocess, "run", lambda *a, **k: R())
    assert tl.ttns_lookup("lịch họp") is None


def test_lookup_timeout_returns_none(monkeypatch):
    def boom(*a, **k):
        raise tl.subprocess.TimeoutExpired(cmd="x", timeout=35)

    monkeypatch.setattr(tl.subprocess, "run", boom)
    assert tl.ttns_lookup("lịch họp") is None


def test_lookup_question_truncated(monkeypatch):
    """Câu hỏi quá dài phải bị cắt trước khi tới script (an toàn đầu vào)."""
    captured = {}

    class R:
        returncode = 0
        stdout = json.dumps({"answer": "ok", "conversationId": "c"})
        stderr = ""

    def fake_run(cmd, *a, **k):
        captured["q"] = cmd[2]
        return R()

    monkeypatch.setattr(tl.subprocess, "run", fake_run)
    tl.ttns_lookup("lịch họp " + "dài " * 300)
    assert len(captured["q"]) <= 500
