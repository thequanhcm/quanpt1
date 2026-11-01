"""Sprint C+D tests: KnowledgeQualityScanner, SelfModelEngine live probes,
PromotionPolicy layered promotion.

Ground rules: local SQLite fixtures only, no gateway, no API keys.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from quan_ai_brain.memory.knowledge_quality import KnowledgeQualityScanner
from quan_ai_brain.memory.promotion_policy import PromotionPolicy


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def brain_db(tmp_path):
    db = tmp_path / "brain.db"
    conn = sqlite3.connect(db)
    conn.execute(
        """CREATE TABLE semantic_memory (
            id TEXT PRIMARY KEY, created_at_utc TEXT, statement TEXT,
            source_ref TEXT, approved_by TEXT, regression_passed INTEGER)"""
    )
    conn.execute(
        """CREATE TABLE candidate_knowledge (
            id TEXT PRIMARY KEY, created_at_utc TEXT, statement TEXT,
            source_ref TEXT, rationale TEXT, status TEXT, decision_note TEXT)"""
    )
    conn.execute(
        """CREATE TABLE episodes (
            id TEXT PRIMARY KEY, created_at_utc TEXT, kind TEXT, summary TEXT,
            source_ref TEXT, status TEXT, metadata_json TEXT)"""
    )
    yield db
    conn.close()


def _add_sem(conn, sid, statement, when="2026-10-26T00:00:00+00:00"):
    conn.execute(
        "INSERT INTO semantic_memory VALUES (?,?,?,?,?,1)",
        (sid, when, statement, statement, "test"),
    )


def _add_cand(conn, cid, statement, source_ref, rationale, status="quarantined"):
    conn.execute(
        "INSERT INTO candidate_knowledge VALUES (?,?,?,?,?,?,NULL)",
        (cid, "2026-10-26T00:00:00+00:00", statement, source_ref, rationale, status),
    )


# ---------------------------------------------------------------------------
# KnowledgeQualityScanner
# ---------------------------------------------------------------------------


def test_scanner_detects_exact_duplicates_in_semantic(brain_db):
    conn = sqlite3.connect(brain_db)
    _add_sem(conn, "s1", "Server chạy trên cổng 8765")
    _add_sem(conn, "s2", "server  chạy trên cổng  8765")  # whitespace variant
    conn.commit(); conn.close()

    report = KnowledgeQualityScanner(brain_db).scan()
    assert report.exact_duplicates_semantic == 1


def test_scanner_detects_candidates_duplicating_semantic(brain_db):
    conn = sqlite3.connect(brain_db)
    _add_sem(conn, "s1", "Hệ thống có 720 tri thức")
    _add_cand(conn, "c1", "Hệ thống có 720 tri thức", '{"source_type":"PROJECT_DOCS"}', "Confidence: 0.9")
    _add_cand(conn, "c2", "Tri thức mới chưa có trong semantic", '{"source_type":"PROJECT_DOCS"}', "Confidence: 0.9")
    conn.commit(); conn.close()

    report = KnowledgeQualityScanner(brain_db).scan()
    assert report.dup_candidates_of_semantic == 1
    assert report.unique_quarantined_statements == 1


def test_scanner_flags_numeric_conflict_suspects(brain_db):
    conn = sqlite3.connect(brain_db)
    _add_sem(conn, "s1", "Hệ thống có 720 tri thức đã duyệt")
    _add_sem(conn, "s2", "Hệ thống có 980 tri thức đã duyệt")
    conn.commit(); conn.close()

    report = KnowledgeQualityScanner(brain_db).scan()
    assert len(report.conflict_suspects) >= 1


def test_scanner_flags_stale_year_references(brain_db):
    conn = sqlite3.connect(brain_db)
    _add_sem(conn, "s1", "Kết quả benchmark năm 2020 cho thấy tốc độ 10 tok/s")
    conn.commit(); conn.close()

    report = KnowledgeQualityScanner(brain_db, stale_days=180).scan()
    assert any(i.issue_type == "stale" for i in report.stale_suspects)


def test_scanner_is_read_only(brain_db):
    conn = sqlite3.connect(brain_db)
    _add_sem(conn, "s1", "Tri thức A")
    _add_cand(conn, "c1", "Tri thức A", '{"source_type":"PROJECT_DOCS"}', "Confidence: 0.9")
    conn.commit(); conn.close()

    before = sqlite3.connect(brain_db)
    snap = (
        before.execute("SELECT COUNT(*) FROM semantic_memory").fetchone(),
        before.execute("SELECT COUNT(*) FROM candidate_knowledge").fetchone(),
    )
    before.close()

    KnowledgeQualityScanner(brain_db).scan()

    after = sqlite3.connect(brain_db)
    snap2 = (
        after.execute("SELECT COUNT(*) FROM semantic_memory").fetchone(),
        after.execute("SELECT COUNT(*) FROM candidate_knowledge").fetchone(),
    )
    after.close()
    assert snap == snap2, "scanner must never mutate knowledge tables"


# ---------------------------------------------------------------------------
# PromotionPolicy — layered rules
# ---------------------------------------------------------------------------


def test_classify_layers_by_content_and_source(brain_db):
    policy = PromotionPolicy(brain_db)
    assert policy.classify_layer("General fact about testing", '{"source_type":"PROJECT_DOCS"}') == "L0"
    assert policy.classify_layer("SOP xử lý mất điện data center", '{"source_type":"DC_SKILL"}') == "L2"
    assert policy.classify_layer("Quy tắc an toàn R5 không được override", '{"source_type":"DC_SKILL"}') == "L3"
    assert policy.classify_layer("Battery TTKV1 có 96 chuỗi ắc quy", '{"source_type":"DC_SKILL"}') == "L1"


def test_l0_promotes_with_dedup_guard(brain_db):
    conn = sqlite3.connect(brain_db)
    _add_sem(conn, "s1", "Server lắng nghe cổng 8765")
    _add_cand(conn, "c1", "Python 3.11 đang được dùng cho runtime", '{"source_type":"PROJECT_DOCS"}', "Confidence: 0.9")
    _add_cand(conn, "c2", "Server lắng nghe cổng 8765", '{"source_type":"PROJECT_DOCS"}', "Confidence: 0.95")  # dup
    _add_cand(conn, "c3", "Thời gian phản hồi trung bình 42ms", '{"source_type":"PROJECT_DOCS"}', "Confidence: 0.5")  # low conf
    conn.commit(); conn.close()

    result = PromotionPolicy(brain_db).evaluate_batch()
    assert result.promoted == 1
    assert result.skipped_dup == 1
    assert result.skipped_low_confidence == 1

    conn = sqlite3.connect(brain_db)
    n = conn.execute("SELECT COUNT(*) FROM semantic_memory WHERE statement LIKE '%Python 3.11%'").fetchone()[0]
    approved = conn.execute("SELECT status FROM candidate_knowledge WHERE id='c1'").fetchone()[0]
    conn.close()
    assert n == 1
    assert approved == "approved"


def test_l1_l2_l3_never_auto_promote(brain_db):
    conn = sqlite3.connect(brain_db)
    _add_cand(conn, "c1", "Battery TTKV1 có 96 chuỗi ắc quy", '{"source_type":"DC_SKILL"}', "Confidence: 0.99")
    _add_cand(conn, "c2", "SOP xử lý cháy cần luyện tập trong sandbox", '{"source_type":"DC_SKILL"}', "Confidence: 0.99")
    _add_cand(conn, "c3", "Chính sách kill-switch phải luôn bật", '{"source_type":"DC_SKILL"}', "Confidence: 0.99")
    conn.commit(); conn.close()

    result = PromotionPolicy(brain_db).evaluate_batch()
    assert result.needs_owner == 3
    assert result.promoted == 0

    conn = sqlite3.connect(brain_db)
    n = conn.execute("SELECT COUNT(*) FROM semantic_memory").fetchone()[0]
    conn.close()
    assert n == 0, "L1/L2/L3 must never reach semantic without owner"


def test_conflict_guard_blocks_contradicting_promotion(brain_db):
    conn = sqlite3.connect(brain_db)
    _add_sem(conn, "s1", "Hệ thống có 720 tri thức đã duyệt")
    _add_cand(conn, "c1", "Hệ thống có 980 tri thức đã duyệt", '{"source_type":"PROJECT_DOCS"}', "Confidence: 0.95")
    conn.commit(); conn.close()

    result = PromotionPolicy(brain_db).evaluate_batch()
    assert result.skipped_conflict == 1
    assert result.promoted == 0


def test_dry_run_mode_promotes_nothing(brain_db):
    conn = sqlite3.connect(brain_db)
    _add_cand(conn, "c1", "Fact chuẩn bị duyệt", '{"source_type":"PROJECT_DOCS"}', "Confidence: 0.9")
    conn.commit(); conn.close()

    result = PromotionPolicy(brain_db).evaluate_batch(execute_l0=False)
    assert result.needs_owner == 1
    assert result.promoted == 0


def test_l0_promotion_is_idempotent_across_batches(brain_db):
    conn = sqlite3.connect(brain_db)
    _add_cand(conn, "c1", "Fact duy nhất cần duyệt", '{"source_type":"PROJECT_DOCS"}', "Confidence: 0.9")
    conn.commit(); conn.close()

    policy = PromotionPolicy(brain_db)
    r1 = policy.evaluate_batch()
    assert r1.promoted == 1
    # Same candidate now approved; a second batch must not double-insert
    r2 = policy.evaluate_batch()
    assert r2.promoted == 0

    conn = sqlite3.connect(brain_db)
    n = conn.execute("SELECT COUNT(*) FROM semantic_memory WHERE statement LIKE '%Fact duy nhất%'").fetchone()[0]
    conn.close()
    assert n == 1


# ---------------------------------------------------------------------------
# SelfModelEngine — evidence-based live answers (C1)
# ---------------------------------------------------------------------------


def test_self_model_live_probe_answers_with_evidence(tmp_path):
    """The live QA method must answer from real probes with evidence refs,
    not hardcoded inventory claims."""
    from quan_ai_brain.cognition.self_model_engine import SelfModelEngine

    engine = SelfModelEngine(str(tmp_path))
    qa = engine.answer_state_questions()

    assert qa["generated_at"]
    # Q1: running where — always verifiable via cwd
    assert qa["q1_running_where"]["workspace_root"]
    assert qa["q1_running_where"]["verification_status"] in ("VERIFIED_LIVE",)
    # Q2/Q3: components online/offline from real probes
    all_components = qa["q2_components_online"] + qa["q3_components_offline_unverified"]
    assert {c["component_id"] for c in all_components} == {"core_server", "ollama_daemon", "pi5_edge"}
    # Ollama status must reflect the REAL probe — whichever state the environment is in.
    # Honesty contract: the engine reports what it measured, not what the test assumes.
    ollama_states = [e["status"] for e in all_components
                     if e["component_id"] == "ollama_daemon"]
    assert len(ollama_states) == 1
    assert ollama_states[0] in ("OFFLINE", "ONLINE", "HEALTHY", "DEGRADED")
    # exactly one of Q2 (online) or Q3 (offline) contains it, never both
    online_ids = {c["component_id"] for c in qa["q2_components_online"]}
    offline_ids = {c["component_id"] for c in qa["q3_components_offline_unverified"]}
    assert ("ollama_daemon" in online_ids) != ("ollama_daemon" in offline_ids)
    # DB counts come from real SQL
    assert qa["q7_approved_knowledge"]["count"] >= 0
    assert qa["q7_approved_knowledge"]["source"].startswith("sqlite:")
    # Q12: diff vs last check stored under data/self_model_last.json
    assert "changed_since_last_check" in qa


def test_self_model_persists_state_snapshot_for_diffing(tmp_path):
    from quan_ai_brain.cognition.self_model_engine import SelfModelEngine

    engine = SelfModelEngine(str(tmp_path))
    qa1 = engine.answer_state_questions()
    qa2 = engine.answer_state_questions()
    # Second run must have a previous snapshot to diff against
    assert qa2["changed_since_last_check"]["previous_snapshot_at"] is not None
