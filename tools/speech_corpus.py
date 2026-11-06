#!/usr/bin/env python3
"""QUAN AI BRAIN — Speech Corpus Collector (Pi5 nghe giọng thật → học lời nói tự nhiên).

Owner directive (06/11/2026): "em cho Pi5 nghe giọng nói thực tế và học tập các
lời nói thông thường của con người tự nhiên".

NGUYÊN TẮC (V7.0 — Learning is not deployment):
- Chỉ THU THẬP text STT (Vosk partial trên Pi5) thành câu → ghi vào
  candidate_knowledge với status='quarantined' (KHÔNG BAO GIỜ tự promote).
- KHÔNG lưu/đụn WAV (nội dung riêng tư) — chỉ text máy nhận dạng được.
- KHÔNG gửi bất cứ thứ gì lên cloud.
- Lọc chất lượng nghiêm: câu quá ngắn, trùng lặp, rác Vosk (tv/ambient) bị loại.

Cách chạy (owner duyệt từng lần, KHÔNG daemon nền):
    python tools/speech_corpus.py --pull        # scp journal từ Pi5 + ingest
    python tools/speech_corpus.py --stats       # xem số liệu kho câu
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
DB_PATH = WORKSPACE / "data" / "brain.db"
RAW_DIR = WORKSPACE / "data" / "edge_media" / "voice"
PI5_HOST = "quanpt1@100.100.83.59"
PI5_KEY = str(Path.home() / ".ssh" / "tony_pi5_ed25519")

# ---- Bộ lọc chất lượng lời nói tự nhiên ----
MIN_WORDS = 3          # dưới 3 từ = tiếng ồn/đơn từ rác Vosk
MAX_WORDS = 40         # quá 40 từ = partial bị cắt rối
MIN_CHARS = 8
MAX_CHARS = 240

# Từ khóa phổ biến của partial Vosk khi CHỈ có tiếng TV/quảng cáo nền
# (đo thực tế 06/11 trên kho 1236 dòng — chiếm đa số noise):
NOISE_PATTERNS = re.compile(
    r"(hot nhất mùa đông|phốt ở|ảnh nóng|loạn luân|độc lập|cộng sản|"
    r"quảng cáo|hàng hiệu|giảm giá|sale off|kênh chúng tôi|xem tiếp|"
    r"đăng ký kênh|miễn phí 100%|vô hạn|kim cương miễn)",
    re.I,
)


def _lev(a: str, b: str) -> int:
    """Levenshtein chuẩn (khớp mờ chống trùng gần-dung-sai)."""
    if abs(len(a) - len(b)) > 6:
        return 99
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def clean_lines(raw_lines: list[str]) -> list[str]:
    """Lọc + chuẩn hóa câu nói từ Vosk partial text."""
    out: list[str] = []
    seen: list[str] = []
    for line in raw_lines:
        s = " ".join(line.strip().lower().split())
        if not s:
            continue
        # Chuẩn hóa dấu câu rác Vosk
        s = re.sub(r"[^\w\sàáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩị"
                   r"òóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]", "", s)
        words = s.split()
        if not (MIN_WORDS <= len(words) <= MAX_WORDS):
            continue
        if not (MIN_CHARS <= len(s) <= MAX_CHARS):
            continue
        if NOISE_PATTERNS.search(s):
            continue
        # Chống trùng gần đúng (lev <= 2 so với câu đã nhận)
        if any(_lev(s, prev) <= 2 for prev in seen[-200:]):
            continue
        seen.append(s)
        out.append(s)
    return out


def _row_exists(cur: sqlite3.Cursor, statement: str) -> bool:
    """Kiểm trùng bằng LIKE đầu câu (rẻ, đủ dùng cho partial)."""
    head = statement[:40].replace("'", "''")
    cur.execute(
        "SELECT 1 FROM candidate_knowledge WHERE statement LIKE ? LIMIT 1",
        (f"{head}%",),
    )
    return cur.fetchone() is not None


def ingest_statements(statements: list[str], source_tag: str) -> tuple[int, int]:
    """Ghi câu vào candidate_knowledge (status='quarantined'). Trả (added, skipped)."""
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    added = skipped = 0
    for s in statements:
        try:
            if _row_exists(cur, s):
                skipped += 1
                continue
            cur.execute(
                "INSERT INTO candidate_knowledge "
                "(id, created_at_utc, statement, source_ref, rationale, status, decision_note) "
                "VALUES (?, ?, ?, ?, ?, 'quarantined', '')",
                (
                    f"speech_{uuid.uuid4().hex[:12]}",
                    now_iso,
                    s,
                    f"speech_corpus:{source_tag}:{time.strftime('%Y%m%d_%H%M%S')}",
                    "Lời nói tự nhiên Pi5 nghe được (STT Vosk) — học văn phong hội thoại; "
                    "chờ owner duyệt trước khi dùng chính thức.",
                ),
            )
            added += 1
        except Exception as exc:  # fail-honest: lỗi 1 câu không chết cả lô
            print(f"  [skip] {s[:40]}… → {exc}", file=sys.stderr)
            skipped += 1
    con.commit()
    con.close()
    return added, skipped


def pull_from_pi5() -> tuple[int, int]:
    """SCP dump Vosk 24h từ Pi5 → lọc → ingest. Trả (added, skipped)."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    remote_tmp = "/tmp/vosk_text_24h.txt"
    local_file = RAW_DIR / f"vosk_pull_{time.strftime('%Y%m%d_%H%M%S')}.txt"
    # 1. dump trên Pi5 (journal → text)
    r = subprocess.run(
        ["ssh", "-i", PI5_KEY, "-o", "BatchMode=yes", "-o", "ConnectTimeout=12",
         PI5_HOST,
         f"journalctl -u quan_ai_wake --since '-24hours' --no-pager -o cat "
         f"| grep 'WAKE-DBG' | sed \"s/.*Vosk: '//; s/'$//\" > {remote_tmp}; "
         f"wc -l {remote_tmp}"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=90,
    )
    print(f"[Pi5] {r.stdout.strip() or r.stderr.strip()[:120]}")
    if r.returncode != 0:
        print("[Pi5] SSH/dump lỗi — dừng (fail-honest).", file=sys.stderr)
        return 0, 0
    # 2. scp về PC
    r2 = subprocess.run(
        ["scp", "-i", PI5_KEY, "-o", "BatchMode=yes",
         f"{PI5_HOST}:{remote_tmp}", str(local_file)],
        capture_output=True, text=True, timeout=90,
    )
    if r2.returncode != 0:
        print("[scp] lỗi — dừng.", file=sys.stderr)
        return 0, 0
    raw = local_file.read_text(encoding="utf-8", errors="replace").splitlines()
    # 3. lọc + ingest
    good = clean_lines(raw)
    print(f"[lọc] {len(raw)} dòng thô → {len(good)} câu đạt chuẩn")
    return ingest_statements(good, "pi5_vosk_24h")


def stats() -> None:
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    cur = con.cursor()
    cur.execute("SELECT COUNT(*) FROM candidate_knowledge WHERE source_ref LIKE 'speech_corpus%'")
    total = cur.fetchone()[0]
    cur.execute("SELECT status, COUNT(*) FROM candidate_knowledge "
                "WHERE source_ref LIKE 'speech_corpus%' GROUP BY status")
    by_status = cur.fetchall()
    con.close()
    print(f"Kho lời nói tự nhiên: {total} câu | theo status: {by_status}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Speech Corpus Collector (quarantined-only)")
    ap.add_argument("--pull", action="store_true", help="Pull Vosk journal từ Pi5 + ingest")
    ap.add_argument("--stats", action="store_true", help="Xem số liệu kho câu")
    ap.add_argument("--ingest-file", type=str, help="Ingest từ file text cục bộ (mỗi dòng 1 câu)")
    args = ap.parse_args()

    if args.stats:
        stats()
        return 0
    if args.ingest_file:
        raw = Path(args.ingest_file).read_text(encoding="utf-8", errors="replace").splitlines()
        good = clean_lines(raw)
        added, skipped = ingest_statements(good, "local_file")
        print(f"Đã ghi {added} câu (bỏ {skipped}) — tất cả quarantined chờ duyệt.")
        return 0
    if args.pull:
        added, skipped = pull_from_pi5()
        print(f"Đã ghi {added} câu mới (trùng bỏ {skipped}) — quarantined chờ duyệt.")
        return 0
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
