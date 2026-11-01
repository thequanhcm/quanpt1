"""Tests — Sprint 7 (b): learning daemon sống sót lỗi + KHÔNG tự promote.

Mock 100%: không chạy daemon thật, không đụng data/brain.db thật.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE / "src"))

from quan_ai_brain.memory.knowledge_ingestion import KnowledgeIngestionEngine, KnowledgeSource
from quan_ai_brain.memory.sqlite_store import MemoryStore


@pytest.fixture()
def fresh_store(tmp_path):
    """MemoryStore SQLite tạm — schema giống brain.db (candidate_knowledge)."""
    db = tmp_path / "brain_test.db"
    store = MemoryStore(str(db))
    conn = store._connection
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS candidate_knowledge (
            id TEXT PRIMARY KEY,
            created_at_utc TEXT NOT NULL,
            statement TEXT NOT NULL,
            source_ref TEXT NOT NULL,
            rationale TEXT,
            status TEXT NOT NULL,
            decision_note TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS semantic_memory (
            id TEXT PRIMARY KEY,
            created_at_utc TEXT NOT NULL,
            statement TEXT NOT NULL,
            source_ref TEXT NOT NULL,
            approved_by TEXT NOT NULL,
            regression_passed INTEGER NOT NULL DEFAULT 1
        )
        """
    )
    conn.commit()
    return store


class TestNoAutoPromote:
    """Governance: daemon KHÔNG được tự duyệt tri thức quarantine."""

    def test_consolidate_returns_zero_and_keeps_quarantine(self, fresh_store):
        # Import hàm consolidate_memories từ tools/learning_daemon.py
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "learning_daemon", WORKSPACE / "tools" / "learning_daemon.py"
        )
        mod = importlib.util.module_from_spec(spec)
        sys.modules["learning_daemon"] = mod
        spec.loader.exec_module(mod)

        engine = KnowledgeIngestionEngine(fresh_store, owner_id="Quanpt1")
        rec = engine.ingest(
            content="Quy trình backup 2AM phải chạy mỗi ngày",
            source_type=KnowledgeSource.PROJECT_DOCS,
            source_ref="docs/test.md",
        )
        assert rec.id  # ingest vào quarantine

        consolidated = mod.consolidate_memories(engine, fresh_store)
        assert consolidated == 0  # KHÔNG promote

        # Vẫn nằm quarantine, semantic rỗng, không ai tự approve
        status = fresh_store._connection.execute(
            "SELECT status FROM candidate_knowledge WHERE id=?", (rec.id,)
        ).fetchone()[0]
        assert status == "quarantined"
        sem_count = fresh_store._connection.execute(
            "SELECT COUNT(*) FROM semantic_memory"
        ).fetchone()[0]
        assert sem_count == 0


class TestIdempotentIngest:
    """Sprint 7 (b): skip_duplicates=True → ingest cùng statement không tạo dòng mới."""

    def test_duplicate_ingest_creates_single_row(self, fresh_store):
        engine = KnowledgeIngestionEngine(fresh_store, owner_id="Quanpt1")
        r1 = engine.ingest(
            content="Watchdog giám sát cả hai cổng 8765 và 8766",
            source_type=KnowledgeSource.PROJECT_DOCS,
            source_ref="docs/a.md",
            skip_duplicates=True,
        )
        r2 = engine.ingest(
            content="Watchdog giám sát cả hai cổng 8765 và 8766",
            source_type=KnowledgeSource.PROJECT_DOCS,
            source_ref="docs/a.md",
            skip_duplicates=True,
        )
        assert r1.id == r2.id  # cùng record gốc
        count = fresh_store._connection.execute(
            "SELECT COUNT(*) FROM candidate_knowledge WHERE statement=?",
            ("Watchdog giám sát cả hai cổng 8765 và 8766",),
        ).fetchone()[0]
        assert count == 1

    def test_different_statement_creates_new_row(self, fresh_store):
        engine = KnowledgeIngestionEngine(fresh_store, owner_id="Quanpt1")
        r1 = engine.ingest(
            content="Câu A hoàn toàn khác",
            source_type=KnowledgeSource.PROJECT_DOCS,
            source_ref="docs/a.md",
            skip_duplicates=True,
        )
        r2 = engine.ingest(
            content="Câu B nội dung riêng",
            source_type=KnowledgeSource.PROJECT_DOCS,
            source_ref="docs/a.md",
            skip_duplicates=True,
        )
        assert r1.id != r2.id

    def test_skip_duplicates_false_keeps_old_behavior(self, fresh_store):
        engine = KnowledgeIngestionEngine(fresh_store, owner_id="Quanpt1")
        engine.ingest(
            content="Câu trùng lặp cho phép",
            source_type=KnowledgeSource.PROJECT_DOCS,
            source_ref="docs/a.md",
        )
        engine.ingest(
            content="Câu trùng lặp cho phép",
            source_type=KnowledgeSource.PROJECT_DOCS,
            source_ref="docs/a.md",
        )
        count = fresh_store._connection.execute(
            "SELECT COUNT(*) FROM candidate_knowledge WHERE statement='Câu trùng lặp cho phép'"
        ).fetchone()[0]
        assert count == 2  # hành vi cũ nguyên vẹn cho caller khác


class TestDaemonSurvivesTransientErrors:
    """Vòng lặp daemon phải sống sót sqlite3.OperationalError (db locked)."""

    def test_cycle_error_does_not_kill_loop(self, tmp_path, monkeypatch, capsys):
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "learning_daemon2", WORKSPACE / "tools" / "learning_daemon.py"
        )
        mod = importlib.util.module_from_spec(spec)
        sys.modules["learning_daemon2"] = mod
        spec.loader.exec_module(mod)

        calls = {"n": 0}

        def fake_cycle_fail_then_ok():
            calls["n"] += 1
            if calls["n"] == 1:
                raise sqlite3.OperationalError("database is locked")
            raise KeyboardInterrupt  # vòng 2: dừng sạch → daemon vẫn sống

        monkeypatch.setattr(mod, "ingest_document", lambda *a, **k: (_ for _ in ()).throw(
            sqlite3.OperationalError("database is locked")
        ))
        # Thay toàn bộ store/engine bằng mock không đụng DB
        class FakeStore:
            _connection = None

        class FakeEngine:
            pass

        monkeypatch.setattr(mod, "MemoryStore", lambda *a, **k: FakeStore())
        monkeypatch.setattr(
            mod, "KnowledgeIngestionEngine", lambda *a, **k: FakeEngine()
        )
        monkeypatch.setattr(mod, "CONFIG", {
            **mod.CONFIG,
            "workspace": tmp_path,
            "db_path": str(tmp_path / "fake.db"),
            "consolidation_interval": 1,
            "crash_log": "crash_test.log",
        })

        # main() chạy: vòng 1 ingest_document raise OperationalError (bị bắt,
        # retry), vòng 2 dừng bằng KeyboardInterrupt qua fake_sleep.
        import time as _time

        real_sleep = _time.sleep
        state = {"interrupted": False}

        def fake_sleep(seconds):
            # Lần sleep đầu = sau vòng 1 (đã log lỗi) → interrupt
            if not state["interrupted"]:
                state["interrupted"] = True
                raise KeyboardInterrupt
            real_sleep(min(seconds, 0.05))

        monkeypatch.setattr(_time, "sleep", fake_sleep)
        with pytest.raises(KeyboardInterrupt):
            mod.main()

        out = capsys.readouterr().out
        assert "KHÔNG chết" in out or "FAILED" in out  # vòng lỗi được bắt + log
