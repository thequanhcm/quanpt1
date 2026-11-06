"""V7 SUPER MEMORY V2 — WP1 Taxonomy Adapter + Coverage Report tests.

100% tmp_path / in-memory — KHÔNG đụng DB production (ghi số 0 byte).
Chuẩn dự án: fixture tmp_path, không mạng, không daemon.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

BRAIN_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BRAIN_ROOT / "src"))
sys.path.insert(0, str(BRAIN_ROOT / "tools"))

from quan_ai_brain.memory.taxonomy import (  # noqa: E402
    DECISION_KIND,
    MemoryCategory,
    map_episode_kind,
    map_knowledge_type,
    map_memory_record,
    map_memory_type,
    map_task_status,
    taxonomy_summary,
)
import memory_taxonomy_report as mtr  # noqa: E402


# ---------------------------------------------------------------------------
# 1) Mapping đầy đủ giá trị enum thật (models.py:10-16)
# ---------------------------------------------------------------------------
class TestMemoryTypeMapping:
    @pytest.mark.parametrize("mt,expected", [
        ("EPISODIC", MemoryCategory.M1_EPISODIC),
        ("SEMANTIC", MemoryCategory.M2_SEMANTIC),
        ("PROCEDURAL", MemoryCategory.M3_PROCEDURAL),
        ("DECISION", MemoryCategory.M1_EPISODIC),  # content-kind, không lớp 9
        ("PREFERENCE", MemoryCategory.M4_PREFERENCE),
        ("CANDIDATE", MemoryCategory.UNMAPPED),  # lifecycle state
    ])
    def test_enum_values_map(self, mt, expected):
        assert map_memory_type(mt) is expected

    @pytest.mark.parametrize("bad", ["", "WEIRD_TYPE", "episodic_x", "123"])
    def test_unknown_values_fail_honest(self, bad):
        assert map_memory_type(bad) is MemoryCategory.UNMAPPED

    def test_decision_carries_kind(self):
        cat, kind = map_memory_record({"memory_type": "DECISION"})
        assert cat is MemoryCategory.M1_EPISODIC
        assert kind == DECISION_KIND

    def test_non_decision_has_no_kind(self):
        cat, kind = map_memory_record({"memory_type": "EPISODIC"})
        assert cat is MemoryCategory.M1_EPISODIC
        assert kind is None


# ---------------------------------------------------------------------------
# 2) KNOWLEDGE_TYPES (deep_memory.py) + episodes.kind + task status
# ---------------------------------------------------------------------------
class TestOtherMappings:
    @pytest.mark.parametrize("kt,expected", [
        ("FACT", MemoryCategory.M2_SEMANTIC),
        ("OPINION", MemoryCategory.M2_SEMANTIC),
        ("RULE", MemoryCategory.M3_PROCEDURAL),
        ("PROCESS", MemoryCategory.M3_PROCEDURAL),
        ("QUESTION", MemoryCategory.M8_REFLECTIVE),
        ("CONCLUSION", MemoryCategory.M2_SEMANTIC),
    ])
    def test_knowledge_types(self, kt, expected):
        assert map_knowledge_type(kt) is expected

    @pytest.mark.parametrize("kind,expected", [
        ("chat_turn", MemoryCategory.M1_EPISODIC),
        ("task", MemoryCategory.M7_TASK_STATE),
        ("experience_lesson", MemoryCategory.M5_EXPERIENCE),
        ("reflection", MemoryCategory.M8_REFLECTIVE),
        ("emotional_signal", MemoryCategory.M6_EMOTIONAL),
    ])
    def test_episode_kinds(self, kind, expected):
        assert map_episode_kind(kind) is expected

    @pytest.mark.parametrize("st", ["PENDING", "RUNNING", "COMPLETED",
                                    "COMPLETED_VERIFIED", "CANCELLED", "archived"])
    def test_task_status_all_m7(self, st):
        assert map_task_status(st) is MemoryCategory.M7_TASK_STATE

    def test_task_status_unknown_fail_honest(self):
        assert map_task_status("STAGING_XYZ") is MemoryCategory.UNMAPPED

    def test_taxonomy_summary_shape(self):
        s = taxonomy_summary()
        assert set(s) == {"memory_type", "knowledge_type", "episode_kind",
                          "task_status_layer"}
        # Không có giá trị map nào ngoài MemoryCategory
        for table in ("memory_type", "knowledge_type", "episode_kind"):
            assert all(isinstance(v, MemoryCategory) for v in s[table].values())


# ---------------------------------------------------------------------------
# 3) Coverage report: chạy THẬT trên tmp DB dựng theo schema thật
# ---------------------------------------------------------------------------
def _make_brain_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.executescript("""
        CREATE TABLE memories (
            id TEXT PRIMARY KEY, memory_type TEXT, content TEXT,
            verification_status TEXT, lifecycle_status TEXT, version INTEGER
        );
        CREATE TABLE knowledge_units (id TEXT PRIMARY KEY, knowledge_type TEXT);
        CREATE TABLE episodes (id TEXT PRIMARY KEY, kind TEXT);
        CREATE TABLE semantic_memory (id TEXT PRIMARY KEY);
        CREATE TABLE candidate_knowledge (id TEXT PRIMARY KEY);
    """)
    rows_m = [("EPISODIC", 3), ("SEMANTIC", 2), ("DECISION", 1), ("CANDIDATE", 2)]
    for mt, n in rows_m:
        for i in range(n):
            conn.execute("INSERT INTO memories VALUES (?,?,?,?,?,?)",
                         (f"{mt}_{i}", mt, "c", "OBSERVED", "active", 1))
    for kt in ["FACT", "RULE", "QUESTION", "MYSTERY_TYPE"]:
        conn.execute("INSERT INTO knowledge_units VALUES (?,?)", (f"ku_{kt}", kt))
    for i, kind in enumerate(["chat_turn", "chat_turn", "task", "experience_lesson"]):
        conn.execute("INSERT INTO episodes VALUES (?,?)", (f"ep_{i}", kind))
    conn.execute("INSERT INTO semantic_memory VALUES ('sm1')")
    conn.execute("INSERT INTO candidate_knowledge VALUES ('ck1')")
    conn.commit()
    conn.close()


def _make_tasks_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE durable_tasks (id TEXT PRIMARY KEY, status TEXT)")
    for i, st in enumerate(["COMPLETED", "COMPLETED", "CANCELLED",
                            "COMPLETED_VERIFIED", "WEIRD"]):
        conn.execute("INSERT INTO durable_tasks VALUES (?,?)", (f"t_{i}", st))
    conn.commit()
    conn.close()


class TestCoverageReport:
    def test_collect_counts_correctly(self, tmp_path):
        brain = tmp_path / "brain.db"
        tasks = tmp_path / "tasks.db"
        _make_brain_db(brain)
        _make_tasks_db(tasks)
        res = mtr.collect(brain_db=brain, tasks_db=tasks)
        stats = res["stats"]
        # memories: EPISODIC 3 + DECISION 1 → M1=4; SEMANTIC 2 → M2; CANDIDATE → UNMAPPED
        assert stats[MemoryCategory.M1_EPISODIC.value]["memories"] == 4
        assert stats[MemoryCategory.M2_SEMANTIC.value]["memories"] == 2
        assert stats[MemoryCategory.UNMAPPED.value]["memories"] == 2
        # KU: FACT→M2, RULE→M3, QUESTION→M8, MYSTERY_TYPE→UNMAPPED (mỗi loại 1)
        assert stats[MemoryCategory.M2_SEMANTIC.value]["knowledge_units"] == 1
        assert stats[MemoryCategory.M3_PROCEDURAL.value]["knowledge_units"] == 1
        assert stats[MemoryCategory.M8_REFLECTIVE.value]["knowledge_units"] == 1
        assert stats[MemoryCategory.UNMAPPED.value]["knowledge_units"] == 1
        # episodes: 2 chat_turn + 1 task + 1 experience_lesson
        assert stats[MemoryCategory.M1_EPISODIC.value]["episodes"] == 2
        assert stats[MemoryCategory.M7_TASK_STATE.value]["episodes"] == 1
        assert stats[MemoryCategory.M5_EXPERIENCE.value]["episodes"] == 1
        # semantic_memory canonical + candidate tổng
        assert stats[MemoryCategory.M2_SEMANTIC.value]["semantic_memory"] == 1
        assert res["candidate_knowledge_total"] == 1
        # tasks: 4 map được + WEIRD → UNMAPPED
        assert stats[MemoryCategory.M7_TASK_STATE.value]["durable_tasks"] == 4
        assert stats[MemoryCategory.UNMAPPED.value]["durable_tasks"] == 1

    def test_collect_missing_db_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            mtr.collect(brain_db=tmp_path / "nope.db", tasks_db=tmp_path / "t.db")

    def test_render_markdown_contains_all_layers(self, tmp_path):
        brain = tmp_path / "brain.db"
        _make_brain_db(brain)
        res = mtr.collect(brain_db=brain, tasks_db=tmp_path / "t.db")
        md = mtr.render_markdown(res)
        assert "M1 EPISODIC" in md and "M8 REFLECTIVE" in md
        assert "UNMAPPED" in md
        assert "candidate_knowledge" in md
        # Số phải khớp — không làm đẹp
        assert "| 4 |" in md.replace("**", "")  # M1 memories=4 tổng line

    def test_report_is_readonly(self, tmp_path, monkeypatch):
        """Bằng chứng 0-byte-ghi: mở DB thật mode=ro → ghi bị SQLite chặn."""
        brain = tmp_path / "brain.db"
        _make_brain_db(brain)
        conn = mtr._ro_connect(brain)
        with pytest.raises(sqlite3.OperationalError):
            conn.execute("INSERT INTO semantic_memory VALUES ('hack')")
        conn.close()

    def test_main_writes_report_and_exits_zero(self, tmp_path, monkeypatch, capsys):
        brain = tmp_path / "brain.db"
        tasks = tmp_path / "tasks.db"
        _make_brain_db(brain)
        _make_tasks_db(tasks)
        out = tmp_path / "MEMORY_TAXONOMY_LATEST.md"
        monkeypatch.setattr(mtr, "BRAIN_DB", brain)
        monkeypatch.setattr(mtr, "TASKS_DB", tasks)
        monkeypatch.setattr(mtr, "REPORT_OUT", out)
        rc = mtr.main()
        assert rc == 0
        assert out.exists()
        assert "TAXONOMY COVERAGE" in out.read_text(encoding="utf-8")
        import json
        payload = json.loads(capsys.readouterr().out)
        assert payload["candidate_knowledge"] == 1
