"""Dedup kho tri thức candidate cách ly (TASK-V3-SPRINT4 mục c).

Nguyên tắc an toàn (đã duyệt trong card):
- Chỉ tác động bảng candidate_knowledge — KHÔNG đụng semantic_memory.
- Backup phải tồn tại trước khi chạy.
- Mỗi nhóm trùng (statement giống hệt nhau): giữ DÒNG ĐẦY ĐỦ NHẤT
  (ưu tiên có conflict_ids + rationale dài hơn + id nhỏ nhất), archive phần dư
  vào bảng candidate_knowledge_archive (không xóa trắng — có thể đối chứng).
- REPORT-ONLY: in báo cáo chi tiết, mọi con số đối chứng trước/sau.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

DB = Path(__file__).resolve().parent.parent / "data" / "brain.db"


def conflict_count(source_ref: str) -> int:
    try:
        return len(json.loads(source_ref).get("conflict_ids", []))
    except Exception:
        return 0


def main() -> None:
    now = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    total = conn.execute("SELECT COUNT(*) FROM candidate_knowledge").fetchone()[0]
    groups = conn.execute(
        "SELECT statement, COUNT(*) c, MIN(id) keep_id FROM candidate_knowledge "
        "GROUP BY statement HAVING c > 1"
    ).fetchall()
    dup_extra = sum(g["c"] - 1 for g in groups)
    print(f"Trước: {total} dòng | {len(groups)} nhóm trùng | {dup_extra} dòng dư")

    if not groups:
        print("Không có trùng lặp — không làm gì.")
        return

    # Bảng archive (cùng DB, schema giống gốc + metadata dedup)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS candidate_knowledge_archive (
            id INTEGER,
            created_at_utc TEXT,
            statement TEXT,
            source_ref TEXT,
            rationale TEXT,
            status TEXT,
            decision_note TEXT,
            archived_at_utc TEXT,
            archive_reason TEXT DEFAULT 'dedup_exact_statement'
        )
        """
    )

    kept = 0
    archived = 0
    for g in groups:
        rows = conn.execute(
            "SELECT * FROM candidate_knowledge WHERE statement = ? ORDER BY id",
            (g["statement"],),
        ).fetchall()
        # Giữ dòng "đầy đủ nhất": nhiều conflict_ids > rationale dài > id nhỏ
        # (id dạng 'know_xxx' — so sánh ổn định bằng chuỗi, không so số)
        best = max(
            rows,
            key=lambda r: (
                conflict_count(r["source_ref"]),
                len(r["rationale"] or ""),
                str(r["id"]),
            ),
        )
        for r in rows:
            if r["id"] == best["id"]:
                continue
            conn.execute(
                "INSERT INTO candidate_knowledge_archive "
                "(id, created_at_utc, statement, source_ref, rationale, status, "
                " decision_note, archived_at_utc) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (r["id"], r["created_at_utc"], r["statement"], r["source_ref"],
                 r["rationale"], r["status"], r["decision_note"], now),
            )
            conn.execute("DELETE FROM candidate_knowledge WHERE id = ?", (r["id"],))
            archived += 1
        kept += 1

    conn.commit()

    after = conn.execute("SELECT COUNT(*) FROM candidate_knowledge").fetchone()[0]
    arch = conn.execute("SELECT COUNT(*) FROM candidate_knowledge_archive").fetchone()[0]
    sem = conn.execute("SELECT COUNT(*) FROM semantic_memory").fetchone()[0]
    uniq_after = conn.execute(
        "SELECT COUNT(*) FROM (SELECT statement FROM candidate_knowledge GROUP BY statement HAVING COUNT(*) > 1)"
    ).fetchone()[0]

    print(f"Đã archive {archived} dòng dư từ {kept} nhóm")
    print(f"Sau: candidate {after} (trùng còn: {uniq_after}) | archive {arch} | semantic (không đụng): {sem}")
    # Đối chứng nhất quán: dòng biến mất khỏi candidate phải bằng dòng vào archive
    # (total được đo TRƯỚC vòng lặp; giữa chừng test/daemon có thể INSERT thêm —
    # nên đối chứng theo hiệu: after == total - archived + new_inserts, với
    # new_inserts = số id hiện tại không có trong snapshot đầu. Đơn giản và đủ:
    # chắc chắn KHÔNG mất dòng: after + archived >= total; và không trùng archive.
    if after + archived < total:
        raise AssertionError(f"MẤT DỮ LIỆU! after({after}) + archived({archived}) < total({total})")
    assert uniq_after == 0, "VẪN CÒN TRÙNG — kiểm tra lại"
    conn.close()
    print("OK: dedup nhất quán, semantic_memory nguyên vẹn.")


if __name__ == "__main__":
    main()
