# -*- coding: utf-8 -*-
"""Archive 693 noise khỏi candidate_knowledge — safety net backup sẵn có.

Phân loại (audit 12/11):
- speech_corpus (677): transcript VOSK nhiễu, không phải tri thức ("lóa mắt mực nước ở hồ cốc")
- tony_vision (12): metadata ảnh, 4 bản trùng cùng 1 ảnh
- WEB_RESEARCH (3): nguồn web generic
- TEST_EVIDENCE (1): evidence test, không phải tri thức

Hành động: INSERT INTO candidate_knowledge_archive + DELETE khỏi candidate_knowledge.
Default DRY-RUN; --execute mới ghi DB. Backup: data/pre_rehabilitate_20261112_133541.db
"""
import argparse
import json
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "brain.db"
ARCHIVE_REASONS = {
    "speech_corpus": "vosk_transcript_noise",
    "tony_vision": "image_metadata_noise",
    "WEB_RESEARCH": "generic_web_noise",
    "TEST_EVIDENCE": "test_evidence_not_knowledge",
}


def classify(source_ref: str) -> str:
    if source_ref.startswith("speech_corpus"):
        return "speech_corpus"
    if source_ref.startswith("tony_vision"):
        return "tony_vision"
    try:
        st = json.loads(source_ref).get("source_type", "")
        if st in ("WEB_RESEARCH", "TEST_EVIDENCE"):
            return st
    except Exception:
        pass
    return "UNKNOWN"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--execute", action="store_true")
    args = ap.parse_args()
    if not args.execute:
        args.dry_run = True

    con = sqlite3.connect(str(DB))
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT id, created_at_utc, statement, source_ref, rationale, status, decision_note "
        "FROM candidate_knowledge WHERE status='quarantined'"
    ).fetchall()

    buckets: dict[str, list] = {}
    unknown = []
    for r in rows:
        t = classify(r["source_ref"])
        if t == "UNKNOWN":
            unknown.append(r["id"])
        buckets.setdefault(t, []).append(r)

    print(f"Total quarantined: {len(rows)}")
    for t, lst in sorted(buckets.items()):
        print(f"  {t}: {len(lst)} → {ARCHIVE_REASONS.get(t, '?')}")
    if unknown:
        print(f"  UNKNOWN (GIỮ LẠI): {len(unknown)}")

    if args.dry_run:
        print("\n[DRY-RUN] Không ghi DB. Chạy --execute để áp dụng.")
        con.close()
        return 0

    if unknown:
        print(f"\n[ABORT] Có {len(unknown)} UNKNOWN — giữ lại, chỉ archive loại đã phân loại rõ.")
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    n_arch = 0
    for t in ("speech_corpus", "tony_vision", "WEB_RESEARCH", "TEST_EVIDENCE"):
        for r in buckets.get(t, []):
            con.execute(
                "INSERT INTO candidate_knowledge_archive "
                "(id, created_at_utc, statement, source_ref, rationale, status, decision_note, archived_at_utc, archive_reason) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (r["id"], r["created_at_utc"], r["statement"], r["source_ref"],
                 r["rationale"], r["status"], r["decision_note"], now, ARCHIVE_REASONS[t]),
            )
            con.execute("DELETE FROM candidate_knowledge WHERE id=?", (r["id"],))
            n_arch += 1
    con.commit()
    left = con.execute("SELECT count(*) FROM candidate_knowledge WHERE status='quarantined'").fetchone()[0]
    con.close()
    print(f"\n[EXECUTE] Archived {n_arch} rows. Còn lại quarantined: {left}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
