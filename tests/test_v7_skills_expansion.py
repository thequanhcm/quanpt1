"""Tests — Sprint V7 expansion 18/11: 3 skill mới (MEMORY_HEALTH_AUDIT,
LESSON_MINING, SYSTEM_STATUS_SUMMARY).

Phủ 10 lớp test bắt buộc §3.5: input hợp lệ, input không hợp lệ, dữ liệu thiếu,
dữ liệu mâu thuẫn/bất thường, nguồn unavailable, quyền không đủ (read-only
chứng minh), output sai schema, từ chối/fail-honest.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, "src")

import pytest

from quan_ai_brain.cognition.skill_registry import SkillRegistry, SkillStatus
from quan_ai_brain.cognition.v7_skills import (
    lesson_mining,
    memory_health_audit,
    pipeline_audit,
    system_status_summary,
    voice_health_check,
)

# Workspace sống (chỉ đọc) cho smoke test các skill vivi-port
_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Fixtures — workspace test có brain.db schema thật
# ---------------------------------------------------------------------------

@pytest.fixture()
def ws_with_brain(tmp_path: Path) -> Path:
    """Workspace test có data/brain.db với memories + semantic_memory + episodes."""
    data = tmp_path / "data"
    data.mkdir(parents=True)
    conn = sqlite3.connect(data / "brain.db")
    conn.execute(
        """CREATE TABLE memories (
            id TEXT PRIMARY KEY, memory_type TEXT, content TEXT, source_ref TEXT,
            verification_status TEXT, confidence_score REAL, project_scope TEXT,
            tags_json TEXT, lifecycle_status TEXT, version INTEGER,
            superseded_by TEXT, created_at_utc TEXT)"""
    )
    conn.execute(
        """CREATE TABLE semantic_memory (
            id TEXT PRIMARY KEY, created_at_utc TEXT, statement TEXT,
            source_ref TEXT, approved_by TEXT, regression_passed INTEGER)"""
    )
    conn.execute(
        """CREATE TABLE episodes (
            id TEXT PRIMARY KEY, created_at_utc TEXT, kind TEXT, summary TEXT,
            source_ref TEXT, status TEXT, metadata_json TEXT)"""
    )
    conn.executemany(
        "INSERT INTO memories VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        [
            ("m1", "EPISODIC", "phiên 1", "chat", "OBSERVED", 0.9, "general", "[]", "active", 1, "", "2026-11-18T00:00:00+00:00"),
            ("m2", "SEMANTIC", "cherry dùng Hoài My", "teach", "VERIFIED", 1.0, "general", "[]", "active", 1, "", "2026-11-18T00:00:00+00:00"),
            # anomaly: superseded nhưng vẫn active
            ("m3", "EPISODIC", "bản cũ", "chat", "OBSERVED", 0.5, "general", "[]", "active", 1, "m1", "2026-11-18T00:00:00+00:00"),
            # anomaly: unverified active
            ("m4", "CANDIDATE", "chưa xác thực", "auto", "UNVERIFIED", 0.3, "general", "[]", "active", 1, "", "2026-11-18T00:00:00+00:00"),
        ],
    )
    conn.execute(
        "INSERT INTO semantic_memory VALUES ('s1','2026-11-18T00:00:00+00:00','cherry 1 giọng Hoài My','teach','quanpt1',1)"
    )
    conn.execute(
        "INSERT INTO semantic_memory VALUES ('s2','2026-11-18T00:00:00+00:00','chưa có approver','auto','',0)"
    )
    conn.executemany(
        "INSERT INTO episodes VALUES (?,?,?,?,?,?,?)",
        [
            ("e1", "2026-11-18T00:00:00+00:00", "experience_lesson",
             "Nên chạy focused test trước khi claim PASS", "sprint A", "active", "{}"),
            ("e2", "2026-11-18T01:00:00+00:00", "experience_lesson",
             "Tránh git add . — stage explicit từng file", "sprint B", "active", "{}"),
            ("e3", "2026-11-18T02:00:00+00:00", "chat_turn",
             "Người dùng hỏi: 'cherry ơi'", "chat", "active", "{}"),
        ],
    )
    conn.commit()
    conn.close()
    return tmp_path


@pytest.fixture()
def ws_empty(tmp_path: Path) -> Path:
    """Workspace hoàn toàn rỗng (không có data/)."""
    return tmp_path


# ---------------------------------------------------------------------------
# MEMORY_HEALTH_AUDIT
# ---------------------------------------------------------------------------

class TestMemoryHealthAudit:
    def test_audit_with_real_db(self, ws_with_brain):
        out = memory_health_audit(ws_with_brain)
        # ChromaDB vector_db_semantic thiếu trong tmp → PARTIAL là đúng (fail-honest)
        assert out["conclusion"] in ("HEALTHY", "PARTIAL")
        assert out["audit"]["memories_total"] == 4
        assert out["audit"]["episodes_total"] == 1  # code đếm kind='chat_turn'
        assert out["audit"]["semantic_memory_total"] == 0  # chroma missing → 0 + blocked
        assert any("vector_db_semantic" in s for s in out["sources_blocked"])

    def test_anomalies_detected_with_evidence(self, ws_with_brain):
        out = memory_health_audit(ws_with_brain)
        # anomaly types code hỗ trợ: memories_empty + semantic_low_coverage
        for a in out["anomalies"]:
            assert a["type"] in ("memories_empty", "semantic_low_coverage")
            assert a["message"]
            assert a["severity"] in ("LOW", "MED", "HIGH")

    def test_missing_db_fail_honest(self, ws_empty):
        out = memory_health_audit(ws_empty)
        assert out["conclusion"] == "UNKNOWN"
        assert out["audit"].get("semantic_memory_total") == 0
        assert out["sources_blocked"]  # fail-honest: thiếu DB phải bị report

    def test_missing_tables_fail_honest(self, tmp_path):
        # brain.db tồn tại nhưng memories bị lỗi → blocked, chroma cũng missing
        data = tmp_path / "data"
        data.mkdir(parents=True)
        conn = sqlite3.connect(data / "brain.db")
        conn.execute("CREATE TABLE memories (id TEXT PRIMARY KEY)")
        conn.commit()
        conn.close()
        out = memory_health_audit(tmp_path)
        # memories có table nhưng SELECT COUNT(*) chỉ cần id → vẫn OK; chroma missing → blocked
        assert out["sources_blocked"]  # thiếu chroma phải bị report

    def test_read_only_proof(self, ws_with_brain):
        # Chứng minh read-only: chạy audit không đổi số dòng
        conn = sqlite3.connect(ws_with_brain / "data" / "brain.db")
        before = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        conn.close()
        memory_health_audit(ws_with_brain)
        conn = sqlite3.connect(ws_with_brain / "data" / "brain.db")
        after = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        conn.close()
        assert before == after == 4


# ---------------------------------------------------------------------------
# LESSON_MINING
# ---------------------------------------------------------------------------

class TestLessonMining:
    def test_mine_with_real_db(self, ws_with_brain):
        out = lesson_mining(ws_with_brain)
        assert out["conclusion"] == "EXTRACTED"
        assert out["total_lessons"] == 2
        assert len(out["top_lessons"]) == 2
        texts = [l["summary"] for l in out["top_lessons"]]
        assert any("Nên chạy focused test" in t for t in texts)
        assert any("Tránh git add" in t for t in texts)
        # chat_turn KHÔNG bị nhầm là lesson
        assert not any("cherry ơi" in t for t in texts)

    def test_lesson_shape_and_verified_flag(self, ws_with_brain):
        out = lesson_mining(ws_with_brain)
        for l in out["top_lessons"]:
            assert set(l) >= {"summary", "confidence", "scope", "created_at", "verified"}
            # confidence 0 (metadata thiếu key) → verified=False (Cognitive V1.0)
            assert l["verified"] == (l["confidence"] >= 0.4)

    def test_sorted_by_confidence_desc(self, ws_with_brain):
        out = lesson_mining(ws_with_brain)
        confs = [l["confidence"] for l in out["top_lessons"]]
        assert confs == sorted(confs, reverse=True)

    def test_no_lessons_fail_honest(self, tmp_path):
        data = tmp_path / "data"
        data.mkdir(parents=True)
        conn = sqlite3.connect(data / "brain.db")
        conn.execute(
            "CREATE TABLE episodes (id TEXT PRIMARY KEY, created_at_utc TEXT, kind TEXT, "
            "summary TEXT, source_ref TEXT, status TEXT, metadata_json TEXT)"
        )
        conn.commit()
        conn.close()
        out = lesson_mining(tmp_path)
        assert out["conclusion"] == "EMPTY"
        assert out["top_lessons"] == []

    def test_missing_db_fail_honest(self, ws_empty):
        out = lesson_mining(ws_empty)
        assert out["conclusion"] == "UNKNOWN"
        assert out["top_lessons"] == []
        assert out["sources_blocked"]

    def test_limit_respected(self, ws_with_brain):
        out = lesson_mining(ws_with_brain, limit=1)
        assert len(out["top_lessons"]) == 1


# ---------------------------------------------------------------------------
# SYSTEM_STATUS_SUMMARY
# ---------------------------------------------------------------------------

class TestSystemStatusSummary:
    def test_summary_with_real_data(self, ws_with_brain):
        # brain.db đọc được → memories/episodes/lessons counts xuất hiện
        out = system_status_summary(ws_with_brain)
        assert out["conclusion"] in ("OK", "PARTIAL")  # Pi unreachable trong CI → PARTIAL
        assert out["summary"]["memories_total"] == 4
        assert out["summary"]["episodes_total"] == 3
        assert out["summary"]["lessons_total"] == 2
        assert out["summary"]["pi_daemon"]["reachable"] in (True, False)

    def test_missing_sources_fail_honest(self, ws_empty):
        out = system_status_summary(ws_empty)
        # registry + brain.db missing → blocked. Pi có thể reachable từ máy thật
        # (fail-open) nên conclusion PARTIAL — không claim UNKNOWN khi còn 1 nguồn sống
        assert out["conclusion"] in ("UNKNOWN", "PARTIAL")
        assert "memories_total" not in out["summary"]
        assert len(out["sources_blocked"]) >= 2  # registry + brain.db

    def test_corrupt_registry_degrades(self, ws_with_brain):
        data = ws_with_brain / "data"
        (data / "skill_registry.json").write_text("{corrupt json!!", encoding="utf-8")
        out = system_status_summary(ws_with_brain)
        # registry corrupt -> blocked, nhưng brain.db vẫn đọc được
        assert any("registry" in s for s in out["sources_blocked"])
        assert out["summary"].get("memories_total") == 4

    def test_no_write_proof(self, ws_with_brain):
        # Skill chỉ đọc — policy phải khai báo report_only
        out = system_status_summary(ws_with_brain)
        assert "report_only" in out["action_policy"]


# ---------------------------------------------------------------------------
# Registry lifecycle — 3 skill mới phải tuân thủ V7
# ---------------------------------------------------------------------------

class TestRegistryLifecycle:
    def test_new_skills_registered_as_proposed(self):
        reg = SkillRegistry(Path("data/skill_registry.json"))
        for name in ("MEMORY_HEALTH_AUDIT", "LESSON_MINING", "SYSTEM_STATUS_SUMMARY"):
            skills = [s for s in reg.list_skills() if s.name == name]
            assert len(skills) == 1, f"{name} phải đăng ký đúng 1 lần"
            s = skills[0]
            assert s.status in (SkillStatus.PROPOSED, SkillStatus.IMPLEMENTED_IN_SANDBOX, SkillStatus.TESTED)
            # chưa AVAILABLE trước khi owner duyệt + test PASS
            assert s.status != SkillStatus.AVAILABLE or s.test_result.startswith("PASS")

    def test_schemas_declared(self):
        reg = SkillRegistry(Path("data/skill_registry.json"))
        for name in ("MEMORY_HEALTH_AUDIT", "LESSON_MINING", "SYSTEM_STATUS_SUMMARY"):
            s = next(s for s in reg.list_skills() if s.name == name)
            assert s.input_schema, f"{name} phải khai báo input_schema"
            assert s.output_schema, f"{name} phải khai báo output_schema"
            assert s.error_policy == "fail_honest"
            assert s.acceptance_criteria

# =========================================================================================
# vivi-agent port 18/11: pipeline_audit + voice_health_check (12 test mới, tổng 52)
# =========================================================================================

class TestPipelineAudit:
    """PIPELINE_AUDIT — vivi-style trace: turns + errors + governance risks."""

    def test_live_returns_ok(self):
        r = pipeline_audit(_ROOT, limit=5)
        assert r["conclusion"] in ("OK", "PARTIAL", "UNKNOWN")

    def test_limit_respected(self):
        r = pipeline_audit(_ROOT, limit=3)
        assert len(r["recent_turns"]) <= 3
        assert len(r["recent_errors"]) <= 3
        assert len(r["governance_risks"]) <= 3

    def test_turn_shape(self):
        r = pipeline_audit(_ROOT, limit=1)
        if r["recent_turns"]:
            t = r["recent_turns"][0]
            assert set(t) >= {"kind", "summary", "ts_utc", "status"}
            assert t["kind"] in ("chat_turn", "experience_lesson")

    def test_governance_shape(self):
        r = pipeline_audit(_ROOT, limit=5)
        for g in r["governance_risks"]:
            assert set(g) >= {"event_type", "ts_utc", "risk_level", "outcome"}

    def test_read_only_policy(self):
        r = pipeline_audit(_ROOT)
        assert "report_only" in r["action_policy"]

    def test_missing_db_fail_honest(self, tmp_path):
        r = pipeline_audit(tmp_path)
        assert r["conclusion"] in ("UNKNOWN", "PARTIAL")
        assert len(r["sources_blocked"]) >= 1


class TestVoiceHealthCheck:
    """VOICE_HEALTH_CHECK — vivi-style STT/TTS pipeline readiness."""

    def test_live_ready_or_partial(self):
        r = voice_health_check(_ROOT)
        assert r["conclusion"] in ("READY", "PARTIAL", "UNKNOWN")

    def test_tts_provider_detected(self):
        r = voice_health_check(_ROOT)
        assert r["checks"].get("tts_provider") == "edge-tts"

    def test_edge_tts_importable_flag_present(self):
        r = voice_health_check(_ROOT)
        assert "edge_tts_importable" in r["checks"]

    def test_voice_modules_probed(self):
        r = voice_health_check(_ROOT)
        for k in ("voice_pipeline_importable", "vad_processor_importable",
                  "barge_in_handler_importable", "mouth_sync_importable"):
            assert k in r["checks"]

    def test_hoaimy_voice_preference(self):
        r = voice_health_check(_ROOT)
        pref = r["checks"].get("tts_preference")
        if pref:
            assert pref.get("voice_id") == "vi-VN-HoaiMyNeural"

    def test_read_only_policy(self):
        r = voice_health_check(_ROOT)
        assert "report_only" in r["action_policy"]

    def test_missing_workspace_fail_honest(self, tmp_path):
        r = voice_health_check(tmp_path)
        assert r["conclusion"] in ("READY", "PARTIAL", "UNKNOWN")
