"""(11/11/2026, COG-0) Test single-instance lock + dedupe spam của learning daemon.

Nguyên nhân gốc dual-instance 11/11: instance mồ côi (cha chết qua restart
watchdog cũ) sống sót song song instance watchdog-spawn — không có gì chặn.
Cam kết: instance thứ 2 phải thoát êm khi lock đang bị giữ; instance chết thì
OS tự nhả lock (không stale-kẹt); ingest "Test suite" phải idempotent.
"""
from __future__ import annotations

import importlib.util
import sqlite3
import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[1]


def _load_daemon_module(tmp_path: Path):
    """Load tools/learning_daemon.py như một module độc lập (pattern Sprint 7)."""
    mod_name = f"learning_daemon_lock_{abs(hash(str(tmp_path))) & 0xFFFF}"
    spec = importlib.util.spec_from_file_location(
        mod_name, WORKSPACE / "tools" / "learning_daemon.py"
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def daemon_mod(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Module daemon với workspace trỏ vào tmp (không đụng data/ thật)."""
    mod = _load_daemon_module(tmp_path)
    monkeypatch.setitem(mod.CONFIG, "workspace", tmp_path)
    monkeypatch.setattr(mod, "_lock_file_handle", None)
    yield mod
    # dọn: đóng handle lock nếu test để hở
    handle = getattr(mod, "_lock_file_handle", None)
    if handle is not None and not handle.closed:
        handle.close()


class TestSingleInstanceLock:
    def test_first_instance_acquires_lock(self, daemon_mod, tmp_path):
        """Instance đầu tiên giữ lock → trả 0 + ghi PID vào file lock."""
        rc = daemon_mod._acquire_single_instance_lock()
        assert rc == 0
        lock_file = tmp_path / "data" / "learning_daemon.lock"
        assert lock_file.exists()
        # Chỉ đọc 64 byte đầu (vùng PID) — byte lock ở 512 bị khóa. PHẢI unbuffered:
        # reader có buffer sẽ ReadFile 8KB vắt qua byte khóa → PermissionError.
        with open(lock_file, "rb", buffering=0) as fh:
            assert fh.read(64).split(b"\n")[0].strip().isdigit()

    def test_second_instance_exits_quietly(self, daemon_mod):
        """Instance thứ 2 khi lock đang bị giữ → trả PID holder (≠0) → main thoát êm."""
        first = daemon_mod._acquire_single_instance_lock()
        assert first == 0
        second = daemon_mod._acquire_single_instance_lock()
        assert second != 0  # ≠0 → main() return 0, không học trùng

    def test_lock_released_when_instance_dies(self, daemon_mod):
        """Instance chết (đóng handle) → OS nhả lock → instance mới vào được."""
        rc1 = daemon_mod._acquire_single_instance_lock()
        assert rc1 == 0
        handle = daemon_mod._lock_file_handle
        handle.close()  # mô phỏng process chết
        daemon_mod._lock_file_handle = None
        rc2 = daemon_mod._acquire_single_instance_lock()
        assert rc2 == 0  # không stale-kẹt


class TestIngestTestResultsDedupe:
    def test_same_result_not_ingested_twice(self, daemon_mod, tmp_path, monkeypatch):
        """(COG-0) Cùng chuỗi kết quả test → chỉ 1 hàng, không spam mỗi chu kỳ."""
        from quan_ai_brain.memory.knowledge_ingestion import (
            KnowledgeIngestionEngine,
        )
        from quan_ai_brain.memory.sqlite_store import MemoryStore

        ws = tmp_path / "ws"
        (ws / "reports").mkdir(parents=True)
        (ws / "reports" / "TEST_RUN_LATEST.txt").write_text(
            "3669 passed, 28 skipped, 6 failed", encoding="utf-8"
        )
        monkeypatch.setitem(daemon_mod.CONFIG, "workspace", ws)

        store = MemoryStore(ws / "data" / "brain.db", workspace=ws)
        engine = KnowledgeIngestionEngine(store, owner_id="Quanpt1")

        n1 = daemon_mod.ingest_test_results(engine)
        n2 = daemon_mod.ingest_test_results(engine)  # chu kỳ sau, nội dung y hệt

        rows = store._connection.execute(
            "SELECT COUNT(*) FROM candidate_knowledge WHERE statement LIKE 'Test suite%'"
        ).fetchone()[0]
        store.close()
        assert n1 == 1
        assert rows == 1, "nội dung y hệt phải bị skip, không spam hàng mới"

    def test_changed_result_ingested_again(self, daemon_mod, tmp_path, monkeypatch):
        """Kết quả test THAY ĐỔI thật (số passed khác) → phải nạp hàng mới."""
        from quan_ai_brain.memory.knowledge_ingestion import (
            KnowledgeIngestionEngine,
        )
        from quan_ai_brain.memory.sqlite_store import MemoryStore

        ws = tmp_path / "ws2"
        (ws / "reports").mkdir(parents=True)
        report = ws / "reports" / "TEST_RUN_LATEST.txt"
        report.write_text("3669 passed, 28 skipped, 6 failed", encoding="utf-8")
        monkeypatch.setitem(daemon_mod.CONFIG, "workspace", ws)

        store = MemoryStore(ws / "data" / "brain.db", workspace=ws)
        engine = KnowledgeIngestionEngine(store, owner_id="Quanpt1")

        daemon_mod.ingest_test_results(engine)
        report.write_text("3670 passed, 27 skipped, 6 failed", encoding="utf-8")
        daemon_mod.ingest_test_results(engine)

        rows = store._connection.execute(
            "SELECT COUNT(*) FROM candidate_knowledge WHERE statement LIKE 'Test suite%'"
        ).fetchone()[0]
        store.close()
        assert rows == 2, "kết quả ĐỔI phải được học như tri thức mới"
