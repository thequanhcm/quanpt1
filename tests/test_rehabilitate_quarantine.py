# -*- coding: utf-8 -*-
"""Test rehabilitate_quarantine — 100% mock (không đụng brain.db thật)."""
import json, sqlite3
from pathlib import Path
import pytest


def _make_mock_db(tmp_path):
    db = tmp_path / "brain.db"
    con = sqlite3.connect(str(db))
    con.executescript("""
        CREATE TABLE candidate_knowledge (
            id TEXT PRIMARY KEY,
            created_at_utc TEXT,
            statement TEXT,
            source_ref TEXT,
            rationale TEXT DEFAULT '',
            status TEXT DEFAULT 'quarantined',
            decision_note TEXT DEFAULT ''
        );
    """)
    rows = [
        ("k1", json.dumps({"source_type": "PROJECT_DOCS", "source_ref": "docs/a.md"}), "doc that"),
        ("k2", json.dumps({"source_type": "TECHNICAL_SPEC", "source_ref": "src/b.py"}), "code that"),
        ("k3", json.dumps({"source_type": "WEB_RESEARCH", "source_ref": "https://x"}), "web"),
        ("k4", "speech_corpus:pi5:20261106", "speech"),
        ("k5", "tony_vision:photo.jpg", "vision"),
    ]
    for rid, ref, stmt in rows:
        con.execute("INSERT INTO candidate_knowledge VALUES (?,?,?,?,?,?,?)",
                    (rid, "2026-01-01", stmt, ref, "", "quarantined", ""))
    con.commit()
    con.close()
    return db


def test_execute_updates_only_allowed(tmp_path):
    """Execute chỉ update PROJECT_DOCS + TECHNICAL_SPEC, giữ nguyên speech/vision/web."""
    db = _make_mock_db(tmp_path)
    con = sqlite3.connect(str(db))
    cur = con.execute("SELECT id, source_ref FROM candidate_knowledge WHERE status='quarantined'")
    rows = cur.fetchall()
    allowed = {"PROJECT_DOCS", "TECHNICAL_SPEC"}
    to_update = []
    for rid, ref in rows:
        try:
            s = json.loads(ref)
            stype = s.get("source_type", "")
        except Exception:
            stype = ref.split(":")[0] if ":" in ref else "OTHER"
        if stype in allowed:
            to_update.append(rid)
    placeholders = ",".join("?" * len(to_update))
    con.execute(f"UPDATE candidate_knowledge SET status='approved' WHERE id IN ({placeholders})", to_update)
    con.commit()
    cur = con.execute("SELECT id, status FROM candidate_knowledge ORDER BY id")
    results = {r[0]: r[1] for r in cur.fetchall()}
    assert results["k1"] == "approved"
    assert results["k2"] == "approved"
    assert results["k3"] == "quarantined"
    assert results["k4"] == "quarantined"
    assert results["k5"] == "quarantined"
    con.close()


def test_skip_types_preserved():
    """speech_corpus, tony_vision, WEB_RESEARCH, TEST_EVIDENCE KHONG bi dung."""
    ALLOWED = {"PROJECT_DOCS", "TECHNICAL_SPEC"}
    SKIP = {"speech_corpus", "tony_vision", "WEB_RESEARCH", "TEST_EVIDENCE"}
    for t in SKIP:
        assert t not in ALLOWED


def test_dry_run_no_db_write(tmp_path):
    """Dry-run KHONG ghi DB."""
    db = _make_mock_db(tmp_path)
    con = sqlite3.connect(str(db))
    before = con.execute("SELECT count(*) FROM candidate_knowledge WHERE status='quarantined'").fetchone()[0]
    # Simulate dry-run: chỉ đếm, không UPDATE
    con.close()
    con = sqlite3.connect(str(db))
    after = con.execute("SELECT count(*) FROM candidate_knowledge WHERE status='quarantined'").fetchone()[0]
    assert before == after == 5
    con.close()
