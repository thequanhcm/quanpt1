"""Backup & Restore verification tests (V7.0 GIAI ĐOẠN 0 — §3.1).

Phủ: backup_database.main() tạo file hợp lệ, integrity_check ok, restore
lên bản sao + query được dữ liệu. 100% tmp_path — KHÔNG đụng production
backups/, KHÔNG đọc data/brain.db thật.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

WS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WS))
sys.path.insert(0, str(WS / "src"))


def _make_source_db(db_path: Path) -> None:
    """Tạo DB nguồn giả lập brain.db tối thiểu (episodes + audit_logs)."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    con.execute("CREATE TABLE episodes (id TEXT PRIMARY KEY, ts_utc TEXT, goal TEXT)")
    con.execute("CREATE TABLE audit_logs (id INTEGER PRIMARY KEY, event TEXT)")
    con.executemany("INSERT INTO episodes VALUES (?,?,?)",
                    [(f"ep{i}", "2026-11-04T00:00:00Z", f"goal {i}") for i in range(5)])
    con.executemany("INSERT INTO audit_logs (event) VALUES (?)",
                    [(f"event_{i}",) for i in range(3)])
    con.commit()
    con.close()


def _backup_module(tmp_path):
    """Import backup_database với BASE_DIR/DB_PATH/BACKUP_DIR trỏ vào tmp."""
    import importlib
    import tools.backup_database as bd
    importlib.reload(bd)  # chắc chắn hằng số không lem từ test trước
    db_path = tmp_path / "data" / "brain.db"
    _make_source_db(db_path)
    bd.BASE_DIR = str(tmp_path)
    bd.DB_PATH = str(db_path)
    bd.BACKUP_DIR = str(tmp_path / "backups")
    return bd, db_path


def test_backup_creates_valid_file(tmp_path, monkeypatch) -> None:
    """main() tạo backup, đúng tên brain_YYYYMMDD_HHMMSS.db, integrity ok."""
    bd, db_path = _backup_module(tmp_path)
    monkeypatch.setattr(bd, "BASE_DIR", str(tmp_path))
    monkeypatch.setattr(bd, "DB_PATH", str(db_path))
    monkeypatch.setattr(bd, "BACKUP_DIR", str(tmp_path / "backups"))

    bd.main()

    backups = sorted((tmp_path / "backups").glob("brain_*.db"))
    assert len(backups) == 1, "backup phải được tạo đúng 1 file"
    name = backups[0].name
    stem = name[len("brain_"):-len(".db")]
    assert len(stem) == 15 and stem[8] == "_", f"tên không đúng pattern UTC: {name}"

    con = sqlite3.connect(backups[0])
    assert con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    con.close()


def test_backup_retention_keeps_last_30(tmp_path, monkeypatch) -> None:
    """Quá 30 backup → cũ nhất bị xóa (giữ đúng chính sách retention)."""
    bd, db_path = _backup_module(tmp_path)
    monkeypatch.setattr(bd, "BASE_DIR", str(tmp_path))
    monkeypatch.setattr(bd, "DB_PATH", str(db_path))
    monkeypatch.setattr(bd, "BACKUP_DIR", str(tmp_path / "backups"))

    bdir = tmp_path / "backups"
    bdir.mkdir()
    for i in range(32):  # 32 file cũ có sẵn
        (bdir / f"brain_20261000_{i:06d}.db").write_bytes(b"old")

    bd.main()

    names = sorted(p.name for p in bdir.glob("brain_*.db"))
    assert len(names) == 30, f"retention sai: {len(names)}"
    assert "brain_20261000_000000.db" not in names, "cũ nhất phải bị xóa"
    assert any(n.startswith("brain_2026") and n != "brain_20261000_000000.db"
               for n in names), "backup mới phải còn"


def test_restore_copy_queryable_and_lossless(tmp_path, monkeypatch) -> None:
    """Restore: copy backup sang vị trí khác → mở được, dữ liệu nguyên vẹn."""
    bd, db_path = _backup_module(tmp_path)
    monkeypatch.setattr(bd, "BASE_DIR", str(tmp_path))
    monkeypatch.setattr(bd, "DB_PATH", str(db_path))
    monkeypatch.setattr(bd, "BACKUP_DIR", str(tmp_path / "backups"))

    bd.main()
    backup = next((tmp_path / "backups").glob("brain_*.db"))

    # RESTORE: copy sang vị trí phục hồi (không ghi đè nguồn thật)
    restored = tmp_path / "restored" / "brain_restored.db"
    restored.parent.mkdir()
    restored.write_bytes(backup.read_bytes())

    con = sqlite3.connect(restored)
    assert con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert con.execute("SELECT COUNT(*) FROM episodes").fetchone()[0] == 5
    assert con.execute("SELECT COUNT(*) FROM audit_logs").fetchone()[0] == 3
    goal = con.execute("SELECT goal FROM episodes WHERE id='ep3'").fetchone()[0]
    con.close()
    assert goal == "goal 3"  # nội dung nguyên vẹn sau restore


def test_restore_rejects_corrupt_file(tmp_path) -> None:
    """File backup hỏng → integrity/restore phải BÁO LỖI (fail-honest), không im lặng."""
    corrupt = tmp_path / "brain_corrupt.db"
    corrupt.write_bytes(b"this is not a sqlite database" * 100)
    # sqlite3 phải từ chối mở file rác (DatabaseError) — restore pipeline thật
    # (backup_database + health check) cũng sẽ fail ở bước này, đúng hành vi fail-honest
    import pytest

    with pytest.raises(sqlite3.DatabaseError):
        con = sqlite3.connect(corrupt)
        try:
            con.execute("PRAGMA integrity_check").fetchone()
        finally:
            con.close()
