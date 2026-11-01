"""Q-4 (01/11/2026, ĐÃ DUYỆT): Batch promotion candidates qua R4 approval verifier.

Quy trình (theo charter — owner governed):
  1. Owner duyệt LÔ qua approval card (NetChat DM: "DUYỆT TASK-Q4-BATCH-..." 
     hoặc mệnh lệnh verbatim trong phiên desktop — auth_method=owner_desktop_directive)
  2. Card APPROVED với auth_method hợp lệ → verifier pass
  3. promote: mỗi candidate status='quarantined' → KnowledgeQuarantine
     .approve_and_promote(candidate_id, approved_by='Quanpt1',
        regression_passed=True, approval_evidence=task_code)
  4. regression_passed=True chỉ khi: pytest suite đã PASS (bằng chứng
     reports/TEST_RUN_LATEST.txt trong ngày) — script KIỂM TRA trước khi chạy.
  5. Ledger 1-lần-dùng + resume an toàn.

Rollback: promoted candidates nằm trong semantic_memory (dễ truy vết approved_by +
thời điểm); giữ nguyên bản ghi candidate_knowledge (status='promoted') — KHÔNG xoá
gì cả. Toàn bộ qua promote_candidate chuẩn → audit trail đầy đủ.

Usage:
  python tools/q4_batch_promote.py --dry-run
  python tools/q4_batch_promote.py --limit 200 --batch TASK-Q4-BATCH-20261101
  python tools/q4_batch_promote.py --status
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

WS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WS / "src"))

from quan_ai_brain.governance.approval_verifier import GovernanceApprovalVerifier, Q4BatchLedger  # noqa: E402
from quan_ai_brain.memory.sqlite_store import MemoryStore  # noqa: E402

GOVERNANCE_DB = WS / "data" / "governance.db"
BRAIN_DB = WS / "data" / "brain.db"


def check_regression_evidence(max_age_hours: int = 24) -> tuple[bool, str]:
    """regression_passed=True chỉ khi test run PASS trong max_age_hours gần nhất."""
    p = WS / "reports" / "TEST_RUN_LATEST.txt"
    if not p.exists():
        return False, "reports/TEST_RUN_LATEST.txt không tồn tại"
    age = datetime.now(timezone.utc) - datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)
    if age > timedelta(hours=max_age_hours):
        return False, f"TEST_RUN_LATEST cũ {age.total_seconds()/3600:.1f}h (> {max_age_hours}h)"
    text = p.read_text(encoding="utf-8", errors="replace")
    if "failed" in text.lower() and "0 failed" not in text.lower():
        return False, "TEST_RUN_LATEST có failed > 0"
    return True, f"PASS (age {age.total_seconds()/60:.0f}m)"


def iter_quarantined(conn: sqlite3.Connection, limit: int):
    cur = conn.execute(
        "SELECT id, statement, source_ref FROM candidate_knowledge "
        "WHERE status = 'quarantined' ORDER BY created_at_utc ASC LIMIT ?",
        (limit,),
    )
    for row in cur.fetchall():
        yield row


def promote_batch(batch_id: str, limit: int, dry_run: bool) -> int:
    verifier = GovernanceApprovalVerifier(GOVERNANCE_DB, workspace=WS)
    ledger = Q4BatchLedger(WS)

    # Bước 1-2: verifier phải pass với batch card TRƯỚC khi đụng 1 candidate nào
    if not verifier.verify(candidate_id="batch", approved_by="Quanpt1", approval_evidence=batch_id):
        print(f"❌ FAIL-CLOSED: không tìm thấy approval hợp lệ cho lô '{batch_id}'.")
        print("   Owner phải duyệt card này qua NetChat DM (auth_method=netchat_dm)")
        print("   hoặc mệnh lệnh verbatim desktop (auth_method=owner_desktop_directive).")
        return 4

    ok_reg, why = check_regression_evidence()
    if not ok_reg:
        print(f"❌ FAIL-CLOSED: regression evidence không đạt — {why}")
        return 4

    entry = ledger.get(batch_id) or {}
    done_before = int(entry.get("items_done", 0))
    print(f"✅ Approval verified cho lô {batch_id} · regression: {why}")
    if done_before:
        print(f"   (resume — đã làm {done_before} items trước đó)")

    store = MemoryStore(str(BRAIN_DB))
    quarantine = __import__(
        "quan_ai_brain.clae.quarantine", fromlist=["KnowledgeQuarantine"]
    ).KnowledgeQuarantine(store, approval_verifier=verifier)

    conn = sqlite3.connect(str(BRAIN_DB))
    promoted = 0
    skipped = 0
    if not dry_run:
        ledger.mark_in_progress(batch_id, batch_id)

    for cid, statement, source_ref in iter_quarantined(conn, limit):
        note = (statement or "")[:60].replace("\n", " ")
        if dry_run:
            promoted += 1
            continue
        try:
            quarantine.approve_and_promote(
                cid,
                approved_by="Quanpt1",
                regression_passed=True,
                approval_evidence=batch_id,
                decision_note=f"Q-4 batch {batch_id} (owner approved)",
            )
            promoted += 1
            ledger.increment(batch_id)
            if promoted % 100 == 0:
                print(f"   ... {promoted} promoted")
        except PermissionError as exc:
            # fail-closed giữa chừng: dừng + báo cáo, không nuốt lỗi
            print(f"⛔ PermissionError tại item {promoted + skipped}: {exc}")
            break
        except (ValueError, KeyError):
            # candidate đã promoted/không còn — bỏ qua an toàn
            skipped += 1

    conn.close()

    if not dry_run:
        ledger.mark_done(batch_id, done_before + promoted)
    mode = "DRY-RUN" if dry_run else "PROMOTED"
    print(f"✅ [{mode}] {batch_id}: {promoted} candidates, {skipped} skipped (đã xử lý/không hợp lệ)")
    return 0


def show_status() -> int:
    conn = sqlite3.connect(f"file:{BRAIN_DB}?mode=ro", uri=True)
    rows = conn.execute(
        "SELECT status, COUNT(*) FROM candidate_knowledge GROUP BY status"
    ).fetchall()
    conn.close()
    print("=== candidate_knowledge ===")
    for status, count in rows:
        print(f"  {status}: {count}")
    ledger = Q4BatchLedger(WS)
    entry = ledger.path
    if entry.exists():
        print(f"=== ledger ({entry.name}) ===")
        print(entry.read_text(encoding="utf-8")[:500])
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Q-4 batch promote với R4 verifier")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=200)
    ap.add_argument("--batch", type=str, default="TASK-Q4-BATCH-20261101")
    ap.add_argument("--status", action="store_true")
    args = ap.parse_args()
    if args.status:
        return show_status()
    return promote_batch(args.batch, args.limit, args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
