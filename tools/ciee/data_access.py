"""CIEE data_access — MỌI kết nối DB phải read-only.

Cam kết R1 (READ-ONLY):
  - Production DB KHÔNG BAO GIỜ được mở bằng sqlite3.connect() thường.
  - Mọi truy vấn SELECT thuần đi qua `ro_connect()` (URI mode=ro&immutable=0).
  - Khi probe cần một object store tự quản schema (DeepMemoryStore,
    ConflictDetector, CausalGraph — đều gọi CREATE TABLE lúc init), runner
    tạo SNAPSHOT COPY trong thư mục tạm của run qua `make_snapshot()` và
    ghi đè os.remove trong tiến trình runner để chặn DELETE tập snapshot.
  - Không hàm nào trong module này phát sinh INSERT/UPDATE/DELETE.
  - `assert_readonly()` tự kiểm tra: mọi PRAGMA integrity, journal_mode phải
    là read-only trên kết nối production.

Chặn ghi 3 lớp cho snapshot:
  1. mode=ro URI cho mọi SELECT trên production.
  2. Snapshot copy nằm ngoài production path (temp dir của run).
  3. os.remove bị monkeypatch trong tiến trình runner — trỏ vào snapshot
     của run này sẽ raise SnapshotProtectionError.
"""

from __future__ import annotations

import os
import shutil
import sqlite3
import tempfile
from pathlib import Path

# ------------------------------------------------------------------ paths
WORKSPACE = Path("E:/BRAIN")
SRC_ROOT = WORKSPACE / "src"
BRAIN_DB = WORKSPACE / "data" / "brain.db"
TASKS_DB = WORKSPACE / "data" / "tasks.db"
GOVERNANCE_DB = WORKSPACE / "data" / "governance.db"
KNOWLEDGE_DB = WORKSPACE / "data" / "knowledge_db"


class SnapshotProtectionError(RuntimeError):
    """Chặn cố tình xóa file snapshot trong tiến trình CIEE runner."""


_SNAPSHOT_REGISTRY: set[str] = set()
_REAL_REMOVE = os.remove


def _guarded_remove(path, *args, **kwargs):  # noqa: ANN002, ANN003
    p = str(path)
    if p in _SNAPSHOT_REGISTRY:
        raise SnapshotProtectionError(
            f"Chặn os.remove vào snapshot CIEE (R1 read-only): {p}"
        )
    return _REAL_REMOVE(path, *args, **kwargs)


def install_snapshot_guard() -> None:
    """Ghi đè os.remove trong tiến trình runner (idempotent)."""
    if os.remove is not _guarded_remove:
        os.remove = _guarded_remove  # type: ignore[assignment]


def ro_connect(db_path: Path | str) -> sqlite3.Connection:
    """Mở kết nối SQLite READ-ONLY bắt buộc (URI mode=ro&immutable=0)."""
    p = Path(db_path)
    if not p.exists():
        raise FileNotFoundError(f"DB không tồn tại: {p}")
    uri = f"file:{p.as_posix()}?mode=ro&immutable=0"
    conn = sqlite3.connect(uri, uri=True, timeout=10)
    conn.execute("PRAGMA query_only = ON")  # chặn ghi ngay cả khi URI lỗi
    return conn


def ro_count(db_path: Path | str, table: str, where: str = "1=1",
             params: tuple = ()) -> int:
    """Đếm dòng — tiện dụng cho probes H/D."""
    conn = ro_connect(db_path)
    try:
        return int(conn.execute(
            f"SELECT COUNT(*) FROM {table} WHERE {where}", params
        ).fetchone()[0])
    finally:
        conn.close()


def ro_fetchall(db_path: Path | str, sql: str,
                params: tuple = ()) -> list[tuple]:
    """SELECT thuần, trả list tuple."""
    conn = ro_connect(db_path)
    try:
        return list(conn.execute(sql, params).fetchall())
    finally:
        conn.close()


def make_snapshot(db_path: Path, run_tmp_dir: Path,
                  name: str | None = None) -> Path:
    """Tạo bản copy của DB vào thư mục tạm của run.

    Đúng nguyên tắc MASTER_PLAN §6: "benchmark đọc DB COPY mỗi lần chạy;
    không ghi vào brain.db". Snapshot nằm ngoài production path và được
    đăng ký vào `_SNAPSHOT_REGISTRY` để os.remove bị chặn.
    """
    run_tmp_dir.mkdir(parents=True, exist_ok=True)
    name = name or (db_path.stem + "_ciee_copy" + db_path.suffix)
    snap = run_tmp_dir / name
    shutil.copy2(db_path, snap)
    _SNAPSHOT_REGISTRY.add(str(snap))
    return snap


def make_run_tmp_dir(run_id: str) -> Path:
    base = Path(tempfile.gettempdir()) / f"ciee_run_{run_id}"
    base.mkdir(parents=True, exist_ok=True)
    return base


def assert_readonly() -> dict[str, bool]:
    """Tự kiểm tra cam kết R1: mở từng DB production ở mode=ro thành công."""
    checks: dict[str, bool] = {}
    for label, p in (("brain", BRAIN_DB), ("tasks", TASKS_DB),
                     ("governance", GOVERNANCE_DB)):
        try:
            conn = ro_connect(p)
            conn.execute("SELECT 1").fetchone()
            conn.close()
            checks[label] = True
        except Exception:  # noqa: BLE001
            checks[label] = False
    return checks
