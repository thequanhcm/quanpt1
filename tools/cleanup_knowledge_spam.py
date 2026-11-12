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
    return {"A_spam_candidate": spam_c, "B_spam_semantic": spam_s}


def dup_count(con: sqlite3.Connection) -> int:
    """Số dòng thừa do trùng (giữ 1/nhóm — bản ghi đầu tiên MIN(rowid)).

    (12/11/2026) Fix bug rollback: hàm này PHẢI được gọi SAU khi đã xóa B
    (spam) — trước đây kỳ vọng C tính trước, B xóa 700 spam làm các nhóm
    spam trùng nhau tự tan → C thực tế 1.758 < kỳ vọng 2.448 (đếm kép 690)
    → drift-guard rollback oan. Giờ kỳ vọng C đo trong transaction sau B.
    """
    return con.execute(
        "SELECT COALESCE(SUM(c - 1), 0) FROM ("
        "  SELECT COUNT(*) c FROM semantic_memory"
        "  GROUP BY LOWER(TRIM(statement)) HAVING c > 1)"
    ).fetchone()[0]


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
        if not args.execute:
            # (12/11/2026) Dry-run đo C TRONG transaction mô phỏng (không ghi):
            # B xóa trước → C còn lại chính xác, không đếm kép như lần trước.
            sim = sqlite3.connect(str(DB_PATH), timeout=30)
            try:
                sim.execute("BEGIN")
                sim.execute(
                    "DELETE FROM semantic_memory WHERE LOWER(TRIM(statement)) LIKE 'test suite:%'"
                )
                c_after_b = dup_count(sim)
                sim.rollback()
            finally:
                sim.close()
            c["C_semantic_dup_extra"] = c_after_b
            total = sum(c.values())
            print(f"  C_semantic_dup_extra: {c_after_b} (đo sau khi mô phỏng xóa B — không đếm kép)")
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
        # (12/11/2026) Kỳ vọng C đo NGAY TRONG transaction sau khi B xóa —
        # tránh đếm kép (B làm nhóm spam trùng tự tan)
        c_expected = dup_count(con)
        cur.execute(
            "DELETE FROM semantic_memory WHERE rowid NOT IN ("
            "  SELECT MIN(rowid) FROM semantic_memory"
            "  GROUP BY LOWER(TRIM(statement)))"
        )
        cc = cur.rowcount
        # verify kỳ vọng ±5%
        drift = abs(a - c["A_spam_candidate"]) + abs(b - c["B_spam_semantic"]) + abs(cc - c_expected)
        if drift > 0.05 * max(c["A_spam_candidate"] + c["B_spam_semantic"] + c_expected, 1):
            con.rollback()
            print(f"ROLLBACK: số dòng thực {a}/{b}/{cc} lệch dự kiến {c['A_spam_candidate']}/{c['B_spam_semantic']}/{c_expected} >5% (drift={drift})")
            return 2
        con.commit()
        print(f"ĐÃ DỌN: A={a}, B={b}, C={cc} (tổng {a+b+cc}). Backup restore: {bak}")
        return 0
    finally:
        con.close()


if __name__ == "__main__":
    raise SystemExit(main())
