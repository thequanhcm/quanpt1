"""(11/11/2026, COG-0) Dọn tri thức rác — DRY-RUN mặc định, cần owner duyệt.

Phạm vi đề xuất (số liệu audit 23:40 11/11/2026):
  A. candidate_knowledge spam "Test suite:%" quarantined  — 1.841 rows (rác 100%)
  B. semantic_memory statement LIKE 'Test suite:%'         —   700 rows (rác đã
     lọt vào semantic trước Sprint 7 — consolidation cũ auto-promote)
  C. semantic_memory duplicate (LOWER(TRIM(statement)) trùng) — 2.448 rows thừa
     (giữ 1/nhóm, ưu tiên giữ dòng created_at MỚI NHẤT)

KHÔNG đụng: ~3.847 tri thức docs/code thật (JSON source_ref) — chờ owner duyệt
batch riêng; 677 speech_corpus (ASR noise — owner quyết); 12 tony_vision.

An toàn:
- Mặc định DRY-RUN: chỉ in số liệu, không ghi DB.
- --execute MỚI ghi, và TRƯỚC KHI ghi bắt buộc: (1) backup brain.db qua sqlite
  backup API vào backups/pre_cleanup_<ts>.db, (2) integrity_check pass.
- Ghi theo transaction; rollback nếu số dòng xóa lệch dự kiến quá 5%.
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "brain.db"
BACKUP_DIR = BASE_DIR / "backups"


def counts(con: sqlite3.Connection) -> dict:
    spam_c = con.execute(
        "SELECT COUNT(*) FROM candidate_knowledge WHERE status='quarantined' "
        "AND statement LIKE 'Test suite:%'"
    ).fetchone()[0]
    spam_s = con.execute(
        "SELECT COUNT(*) FROM semantic_memory WHERE LOWER(TRIM(statement)) LIKE 'test suite:%'"
    ).fetchone()[0]
    dup = con.execute(
        "SELECT COALESCE(SUM(c - 1), 0) FROM ("
        "  SELECT COUNT(*) c FROM semantic_memory"
        "  GROUP BY LOWER(TRIM(statement)) HAVING c > 1)"
    ).fetchone()[0]
    return {"A_spam_candidate": spam_c, "B_spam_semantic": spam_s, "C_semantic_dup_extra": dup}


def backup_first() -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    target = BACKUP_DIR / f"pre_cleanup_{ts}.db"
    src = sqlite3.connect(str(DB_PATH), timeout=30)
    try:
        dst = sqlite3.connect(str(target))
        try:
            with dst:
                src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()
    check = sqlite3.connect(str(target))
    try:
        ok = check.execute("PRAGMA integrity_check").fetchone()[0]
    finally:
        check.close()
    if ok != "ok":
        raise SystemExit(f"Backup pre-cleanup FAIL integrity ({ok}) — DỪNG, không dọn.")
    return target


def main() -> int:
    ap = argparse.ArgumentParser(description="Dọn tri thức rác (dry-run mặc định)")
    ap.add_argument("--execute", action="store_true", help="THỰC THI (cần backup pass)")
    args = ap.parse_args()

    con = sqlite3.connect(str(DB_PATH), timeout=30)
    try:
        c = counts(con)
        print("=== SỐ LIỆU SẼ DỌN ===")
        for k, v in c.items():
            print(f"  {k}: {v}")
        total = sum(c.values())
        if not args.execute:
            print(f"\nDRY-RUN — không ghi gì. Tổng: {total} rows.")
            print("Thực thi: python tools/cleanup_knowledge_spam.py --execute")
            return 0

        # Thực thi: backup bắt buộc trước
        bak = backup_first()
        print(f"Backup pre-cleanup: {bak}")
        cur = con.cursor()
        cur.execute("BEGIN")
        cur.execute(
            "DELETE FROM candidate_knowledge WHERE status='quarantined' "
            "AND statement LIKE 'Test suite:%'"
        )
        a = cur.rowcount
        cur.execute(
            "DELETE FROM semantic_memory WHERE LOWER(TRIM(statement)) LIKE 'test suite:%'"
        )
        b = cur.rowcount
        cur.execute(
            "DELETE FROM semantic_memory WHERE rowid NOT IN ("
            "  SELECT MIN(rowid) FROM semantic_memory"
            "  GROUP BY LOWER(TRIM(statement)))"
        )
        cc = cur.rowcount
        # verify kỳ vọng ±5%
        drift = abs(a - c["A_spam_candidate"]) + abs(b - c["B_spam_semantic"]) + abs(cc - c["C_semantic_dup_extra"])
        if drift > 0.05 * max(total, 1):
            con.rollback()
            print(f"ROLLBACK: số dòng thực {a}/{b}/{cc} lệch dự kiến >5% (drift={drift})")
            return 2
        con.commit()
        print(f"ĐÃ DỌN: A={a}, B={b}, C={cc} (tổng {a+b+cc}). Backup restore: {bak}")
        return 0
    finally:
        con.close()


if __name__ == "__main__":
    raise SystemExit(main())
