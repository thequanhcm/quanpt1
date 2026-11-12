# -*- coding: utf-8 -*-
"""Rehabilitate tri thức docs/code thật bị quarantine oan.

Chỉ chuyển status='quarantined' → 'approved' cho:
- PROJECT_DOCS (docs/ thật)
- TECHNICAL_SPEC (src/ code thật)

KHÔNG đụng:
- speech_corpus (cần owner quyết riêng)
- tony_vision (cần owner quyết riêng)
- WEB_RESEARCH, TEST_EVIDENCE (cần owner quyết riêng)

Usage:
    python tools/rehabilitate_quarantine.py --dry-run   # chỉ đếm
    python tools/rehabilitate_quarantine.py --execute  # chuyển status
"""
import argparse, json, sqlite3, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "brain.db"

ALLOWED_TYPES = {"PROJECT_DOCS", "TECHNICAL_SPEC"}


def find_workspace_root() -> Path:
    """Tìm workspace root qua anchor data/brain.db — bắt đầu từ tools/ parent."""
    p = Path(__file__).resolve().parent.parent  # tools/ → workspace root
    if (p / "data" / "brain.db").exists():
        return p
    raise RuntimeError("brain.db not found at " + str(p))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="chỉ đếm, không ghi")
    ap.add_argument("--execute", action="store_true", help="chuyển status quarantined→approved")
    args = ap.parse_args()
    if not args.dry_run and not args.execute:
        args.dry_run = True  # default safe

    db = find_workspace_root() / "data" / "brain.db"
    con = sqlite3.connect(str(db))
    con.row_factory = sqlite3.Row

    # Lấy tất cả quarantined
    cur = con.execute("SELECT id, source_ref, statement FROM candidate_knowledge WHERE status='quarantined'")
    rows = cur.fetchall()

    to_rehab = []
    skipped = []
    for r in rows:
        try:
            s = json.loads(r["source_ref"])
            stype = s.get("source_type", "")
        except Exception:
            stype = r["source_ref"].split(":")[0] if ":" in r["source_ref"] else "OTHER"
        if stype in ALLOWED_TYPES:
            to_rehab.append((r["id"], stype, r["statement"][:60]))
        else:
            skipped.append((r["id"], stype))

    print(f"Total quarantined: {len(rows)}")
    print(f"  → rehabilitate ({len(to_rehab)}):")
    by_type = {}
    for _, t, _ in to_rehab:
        by_type[t] = by_type.get(t, 0) + 1
    for t, n in by_type.items():
        print(f"      {t}: {n}")
    print(f"  → skip ({len(skipped)}):")
    by_type2 = {}
    for _, t in skipped:
        by_type2[t] = by_type2.get(t, 0) + 1
    for t, n in by_type2.items():
        print(f"      {t}: {n}")

    if args.dry_run:
        print("\n[DRY-RUN] Không ghi DB. Chạy --execute để áp dụng.")
        con.close()
        return 0

    # Execute
    ids = [r[0] for r in to_rehab]
    placeholders = ",".join("?" * len(ids))
    cur = con.execute(
        f"UPDATE candidate_knowledge SET status='approved', decision_note='rehabilitated 2026-11-12: PROJECT_DOCS/TECHNICAL_SPEC tri thức thật bị quarantine oan' WHERE id IN ({placeholders})",
        ids
    )
    n_updated = cur.rowcount
    con.commit()
    con.close()
    print(f"\n[EXECUTE] Updated {n_updated} rows: quarantined → approved")
    return 0


if __name__ == "__main__":
    sys.exit(main())
