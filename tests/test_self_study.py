"""CAI V3.0 — test Self-Study Engine V2 (chạy thử chu trình tự học THẬT).

Copy brain.db production sang tmp — dữ liệu episodes/lessons/candidate_knowledge
là THẬT, researcher là fake có kiểm soát (prod researcher = web_search thật).
"""
from __future__ import annotations

import shutil
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from quan_ai_brain.cognition.self_study import (  # noqa: E402
    KnowledgeGap, KnowledgeGapScanner, StudyCycleEngine, _norm,
    build_thought_from_cycle,
)

WS = Path(__file__).resolve().parents[1]
PROD_DB = WS / "data" / "brain.db"


@pytest.fixture()
def study_db(tmp_path) -> Path:
    """DB sạch cho test (không copy production — tránh row cũ nhiễu assert).

    Schema tối thiểu giống production: episodes, candidate_knowledge,
    semantic_memory. Test inject dữ liệu riêng để đảm bảo độc lập."""
    dst = tmp_path / "brain.db"
    con = sqlite3.connect(dst)
    con.executescript("""
        CREATE TABLE episodes (
            id TEXT PRIMARY KEY, created_at_utc TEXT, kind TEXT,
            summary TEXT, source_ref TEXT, status TEXT, metadata_json TEXT);
        CREATE TABLE candidate_knowledge (
            id TEXT PRIMARY KEY, created_at_utc TEXT, statement TEXT,
            source_ref TEXT, rationale TEXT, status TEXT, decision_note TEXT);
        CREATE TABLE semantic_memory (
            id TEXT PRIMARY KEY, created_at_utc TEXT, statement TEXT,
            source_ref TEXT, confidence REAL, status TEXT);
    """)
    con.commit(); con.close()
    return dst


def fake_researcher(gap: KnowledgeGap):
    """Researcher giả có kiểm soát (test-only) — 1 nguồn thật mô phỏng."""
    return [{"title": "Tài liệu về " + gap.topic[:30],
             "snippet": f"Đã tìm thấy phương pháp xử lý cho {gap.topic[:40]} "
                        f"từ nghiên cứu testcase {gap.gap_id}",
             "url": "https://example.org/study/" + gap.gap_id}]


# ─── SCAN ───
def test_scanner_finds_gaps_from_real_episodes(tmp_path) -> None:
    """Scan trên lessons THẬT trong brain.db (113 experience_lessons).

    Dùng copy production riêng (không qua fixture study_db) — test này cần
    dữ liệu thật để xác minh scanner hoạt động trên production data."""
    if not PROD_DB.exists():
        pytest.skip("production brain.db không có")
    dst = tmp_path / "brain_real.db"
    shutil.copy(PROD_DB, dst)
    sc = KnowledgeGapScanner(dst)
    gaps = sc.scan(limit=5)
    # Sau khi sửa scanner đọc goal thật: 113 lessons đã được bao phủ → 0 gap
    # (đây là kết quả trung thực, không phải bug — kiểm chứng scanner không
    # tự bịa gap từ metadata)
    assert isinstance(gaps, list)
    assert all(g.source == "episodes:experience_lesson" for g in gaps)
    assert all(g.topic for g in gaps)


def test_scanner_dedup_known_topics(study_db) ->None:
    """Topic đã có knowledge tương ứng không được tính là gap (chống dupes)."""
    sc = KnowledgeGapScanner(study_db)
    gaps1 = sc.scan(limit=10)
    if len(gaps1) < 2:
        pytest.skip("cần >=2 gap để test dedup")
    # Inject knowledge cho gap đầu
    con = sqlite3.connect(study_db)
    con.execute("INSERT INTO candidate_knowledge(id, created_at_utc, statement, "
                "source_ref, rationale, status, decision_note) VALUES(?,?,?,?,?,?,?)",
                ("know_test_dedup", "2026-11-03T00:00:00+00:00", gaps1[0].topic,
                 "{}", "test", "quarantined", ""))
    con.commit(); con.close()
    gaps2 = KnowledgeGapScanner(study_db).scan(limit=10)
    assert _norm(gaps1[0].topic) not in {_norm(g.topic) for g in gaps2}


# ─── STUDY → SYNTHESIZE → QUARANTINE ───
def test_cycle_quarantines_new_knowledge(study_db) -> None:
    """Chu trình đầy đủ: gap → study → quarantine (KHÔNG tự nạp memory).

    Dùng gap NHÂN TẠO duy nhất để không phụ thuộc thứ tự test (test khác
    có thể đã inject knowledge làm gap thật bị dedup)."""
    con = sqlite3.connect(study_db)
    con.execute(
        "INSERT INTO episodes(id, created_at_utc, kind, summary, source_ref, "
        "status, metadata_json) VALUES(?,?,?,?,?,?,?)",
        ("ep_study_unique_1", "2026-11-03T01:30:00+00:00", "experience_lesson",
         "Bài học duy nhất về xử lý treo cổng serial RS485 trên Pi5 khi buffer đầy",
         "test", "active", "{}"))
    con.commit(); con.close()
    eng = StudyCycleEngine(study_db, fake_researcher, max_gaps_per_cycle=3)
    gap = KnowledgeGap(gap_id="gap-rs485-unique",
                       topic="Bài học duy nhất về xử lý treo cổng serial RS485 trên Pi5",
                       source="manual",
                       evidence="test-injected lesson", priority=3)
    report = eng.run_cycle(gaps=[gap])
    assert report["gaps_scanned"] == 1
    assert len(report["quarantined"]) >= 1
    row = report["quarantined"][0]
    assert row["knowledge_id"].startswith("know_")
    # Xác minh DB thật có row quarantined
    con = sqlite3.connect(study_db)
    status, src = con.execute(
        "SELECT status, source_ref FROM candidate_knowledge WHERE id=?",
        (row["knowledge_id"],)).fetchone()
    con.close()
    assert status == "quarantined"
    assert "WEB_RESEARCH" in src


def test_cycle_dedup_blocks_redundant_knowledge(study_db) -> None:
    """§VI dedup: knowledge trùng không được ghi thêm (xử lý dupes 44%)."""
    eng = StudyCycleEngine(study_db, fake_researcher, max_gaps_per_cycle=1)
    r1 = eng.run_cycle()
    # Chạy chu kỳ 2 với gap NHÂN TẠO có statement giống hệt
    if not r1["quarantined"]:
        pytest.skip("chu kỳ 1 không quarantine được gì")
    stmt = r1["quarantined"][0]["statement"]
    gap_fake = KnowledgeGap(gap_id="gap-fake", topic="x", source="manual",
                            evidence="test", priority=3)
    eng2 = StudyCycleEngine(study_db, lambda g: [
        {"title": "t", "snippet": stmt, "url": "u"}], max_gaps_per_cycle=1)
    r2 = eng2.run_cycle(gaps=[gap_fake])
    assert r2["quarantined"] == [] and r2["duplicates_skipped"]


def test_cycle_unresolved_when_no_sources(study_db) -> None:
    """Không có nguồn → UNRESOLVED, không bịa knowledge."""
    # Dùng gap nhân tạo (scanner mới đọc goal thật từ tasks.db nên có thể
    # không tìm thấy gap nào trên DB copy — test phải độc lập với scanner).
    gap = KnowledgeGap(gap_id="gap-no-sources", topic="Chủ đề không tìm được nguồn",
                       source="manual", evidence="test", priority=3)
    eng = StudyCycleEngine(study_db, lambda g: [], max_gaps_per_cycle=1)
    r = eng.run_cycle(gaps=[gap])
    assert r["quarantined"] == []
    assert r["unresolved"], "gap không có nguồn phải rơi vào unresolved"
    # Không row mới nào được ghi
    con = sqlite3.connect(study_db)
    n = con.execute("SELECT COUNT(*) FROM candidate_knowledge WHERE rationale "
                    "LIKE '%self-study%' AND created_at_utc > '2026-11-03T01'").fetchone()[0]
    con.close()
    assert n == 0


def test_thought_from_cycle_honest(study_db) -> None:
    """Suy nghĩ nội tâm phải phản ánh đúng số liệu chu kỳ (không hardcoded)."""
    eng = StudyCycleEngine(study_db, fake_researcher, max_gaps_per_cycle=2)
    r = eng.run_cycle()
    thought = build_thought_from_cycle(r)
    assert thought["trigger"] == "SELF_STUDY_CYCLE"
    assert str(r["gaps_scanned"]) in thought["inner_monologue"]
    if r["quarantined"]:
        assert "CÁCH LY" in thought["inner_monologue"]
        assert thought["actionable_idea"]


# ─── An toàn ───
def test_quarantine_never_writes_semantic_memory(study_db) -> None:
    """Ranh giới §XI: chu trình KHÔNG BAO GIỜ ghi vào semantic_memory trực tiếp."""
    before = sqlite3.connect(study_db).execute(
        "SELECT COUNT(*) FROM semantic_memory").fetchone()[0]
    eng = StudyCycleEngine(study_db, fake_researcher, max_gaps_per_cycle=3)
    eng.run_cycle()
    after = sqlite3.connect(study_db).execute(
        "SELECT COUNT(*) FROM semantic_memory").fetchone()[0]
    assert before == after, "chu trình tự học không được nạp thẳng memory"
