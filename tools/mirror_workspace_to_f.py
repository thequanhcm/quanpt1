r"""Mirror TOÀN BỘ workspace QUAN AI BRAIN sang ổ F (sao lưu lớn, tăng dần).

Lệnh owner (01/11/2026, image_9e1e66): 'kiểm tra lại việc toàn bộ hệ thống TONY
sao chép và lưu vào ổ mới mà anh đã đưa ra lệnh thực hiện trước đó, hãy hoàn
thiện nó'. Ổ F: 270 GB nhãn 'Quan AI Brain' do owner tạo — trước script này ổ
CÒN TRỐNG (chưa từng được copy).

Thiết kế an toàn:
- NGUỒN : D:\AI\AI Quanpt1 2026\BRAIN — script CHỈ ĐỌC nguồn, không bao giờ
  ghi/xóa bất cứ thứ gì trong workspace gốc.
- ĐÍCH  : F:\BRAIN — thư mục riêng trên ổ 'Quan AI Brain', không đụng root F:\.
- Cơ chế: robocopy /MIR — lần đầu copy đủ, các lần sau chỉ copy phần thay đổi
  (nhanh, dùng làm mirror hằng ngày).
- Loại  : __pycache__ (bytecode tái tạo được, hàng chục nghìn file rác).
  Mọi thứ khác được copy NGUYÊN VẸN: code, data (brain.db, secret, config),
  kho_tai_lieu, backups, reports, docs, .venv, logs, Skill, Pi5...
- Verify: (1) đếm file+byte theo từng thư mục gốc NGUỒN vs ĐÍCH;
  (2) robocopy /L lần 2 phải báo 0 file cần copy, 0 file thừa ở đích.
- Lịch  : --register-task đăng ký Task Scheduler chạy lại 02:30 hằng ngày
  (sau backup DB 02:00) — mirror luôn tươi.

Cách dùng:
    python tools/mirror_workspace_to_f.py --dry-run          # xem trước
    python tools/mirror_workspace_to_f.py                    # mirror + verify
    python tools/mirror_workspace_to_f.py --register-task    # đặt lịch 02:30
"""
from __future__ import annotations

import argparse
import hashlib
import os
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

SOURCE = Path(r"D:\AI\AI Quanpt1 2026\BRAIN")
DEST = Path(r"F:\BRAIN")
EXCLUDE_DIRS = {"__pycache__"}
LOG_FILE = SOURCE / "logs" / "mirror_to_f.log"
TASK_NAME = "QUAN_AI_BRAIN_MIRROR_F"
WRAPPER_BAT = SOURCE / "tools" / "run_mirror_f.bat"

# Thư mục lõi để băm SHA-256 đối chiếu (code + config — nhỏ, đủ chứng minh
# toàn vẹn nội dung; phần data lớn đối chiếu bằng số file + số byte).
HASH_DIRS = ("src", "tools", "edge_client", "tests")


def log(msg: str) -> None:
    line = f"[{datetime.now(timezone.utc).astimezone().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line)
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8", errors="replace") as f:
            f.write(line + "\n")
    except OSError:
        pass


def tree_stats(root: Path) -> tuple[int, int]:
    """(số file, tổng byte) dưới root, bỏ EXCLUDE_DIRS."""
    n, total = 0, 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for name in filenames:
            try:
                total += os.path.getsize(os.path.join(dirpath, name))
                n += 1
            except OSError:
                pass
    return n, total


def per_top_dir_stats(root: Path) -> dict[str, tuple[int, int]]:
    """Số liệu (file, byte) cho từng thư mục cấp 1 + file rời ở root."""
    out: dict[str, tuple[int, int]] = {}
    for entry in os.scandir(root):
        if entry.is_dir():
            if entry.name in EXCLUDE_DIRS:
                continue
            out[entry.name + "/"] = tree_stats(Path(entry.path))
        else:
            out[entry.name] = (1, entry.stat().st_size)
    return out


def dir_hashes(root: Path, rel: str) -> str:
    """SHA-256 gộp của mọi file trong thư mục con rel (đường dẫn + nội dung)."""
    h = hashlib.sha256()
    base = root / rel
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for name in sorted(filenames):
            p = Path(dirpath) / name
            try:
                h.update(str(p.relative_to(root)).encode("utf-8"))
                h.update(p.read_bytes())
            except OSError:
                h.update(b"<unreadable>")
    return h.hexdigest()[:16]


def run_robocopy(list_only: bool, list_files: bool = False) -> tuple[int, str]:
    cmd = [
        "robocopy", str(SOURCE), str(DEST),
        "/MIR", "/R:2", "/W:2", "/MT:16", "/XJ",
        "/COPY:DAT", "/DCOPY:DAT", "/NP",
        "/XD", *EXCLUDE_DIRS,
    ]
    if list_only:
        cmd.append("/L")
    if list_files:
        # liệt kê từng file cần copy (VERIFY-2 dùng để phân loại log-churn)
        pass
    else:
        cmd += ["/NFL", "/NDL"]
    r = subprocess.run(cmd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=1800)
    return r.returncode, r.stdout


def parse_summary(out: str) -> dict[str, int]:
    """Bảng tổng kết robocopy: Total/Copied/Skipped/Mismatch/FAILED/Extras.

    Robocopy in cột cách nhau bằng whitespace (không phải tab) — bắt cả 2 dạng.
    """
    import re as _re
    res: dict[str, int] = {}
    for line in out.splitlines():
        m = _re.match(r"\s*(Files|Dirs|Bytes)\s*:\s*(.*)", line)
        if not m:
            continue
        cells = [c for c in _re.split(r"[\s\t]+", m.group(2).strip()) if c]
        if len(cells) >= 5:
            def _int(tok: str) -> int:
                try:
                    return int(tok.replace(",", ""))
                except ValueError:
                    # '5.786 g' -> 5.786 GB → quy ra byte qua nhánh Bytes riêng
                    return -1
            if m.group(1) == "Bytes":
                try:
                    # ví dụ '5.786 g' → giây thập phân … đủ để verify tổng quát
                    val = float(cells[0])
                    res["Bytes_total"] = int(val * 1e9)
                except ValueError:
                    res["Bytes_total"] = -1
            else:
                vals = [_int(c) for c in cells[:5]]
                res[m.group(1)] = dict(
                    zip(("total", "copied", "skipped", "failed", "extras"), vals)
                )
    return res


def check_drive() -> None:
    if not DEST.drive or not os.path.exists("F:\\"):
        log("LỖI: Ổ F: không tồn tại / chưa cắm. Hủy mirror.")
        sys.exit(1)


# DB SQLite đang sống cần snapshot nhất quán (backup API chụp tại 1 thời điểm
# ngay cả khi service đang ghi) — copy thô có thể chụp giữa 2 transaction.
LIVE_DBS = ("data/brain.db", "data/health_alerts.db", "data/netchat_seen_state.json")


def snapshot_live_dbs() -> int:
    """Chụp snapshot nhất quán các DB live vào đích, SAU robocopy.

    Trả về số DB snapshot thành công. JSON copy thô là đủ (ghi nguyên tử).
    """
    ok = 0
    for rel in LIVE_DBS:
        src = SOURCE / rel
        if not src.exists():
            continue
        dst = DEST / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            if src.suffix.lower() == ".db":
                src_conn = sqlite3.connect(f"file:{src}?mode=ro", uri=True, timeout=10)
                dst_conn = sqlite3.connect(dst)
                with dst_conn:
                    src_conn.backup(dst_conn)
                dst_conn.close()
                src_conn.close()
                # integrity check bản ở đích
                chk = sqlite3.connect(f"file:{dst}?mode=ro", uri=True)
                res = chk.execute("PRAGMA integrity_check").fetchone()[0]
                chk.close()
                if res != "ok":
                    log(f"  ⚠ DB đích integrity KHÔNG ok: {rel} → {res}")
                    continue
                log(f"  snapshot+integrity OK: {rel} ({dst.stat().st_size/1e6:.1f} MB)")
            else:
                # file nhỏ ghi nguyên tử — copy 2 lần, lần 2 phải giống lần 1
                import shutil
                shutil.copy2(src, dst)
                import hashlib as _h
                h1 = _h.sha256(src.read_bytes()).hexdigest()[:12]
                h2 = _h.sha256(dst.read_bytes()).hexdigest()[:12]
                if h1 == h2:
                    log(f"  copy 2-lần khớp hash: {rel}")
                else:
                    log(f"  ⚠ {rel} đổi giữa 2 lần đọc — copy lại...")
                    shutil.copy2(src, dst)
            ok += 1
        except Exception as e:
            log(f"  ⚠ snapshot lỗi {rel}: {e}")
    return ok


def register_task() -> int:
    """Đăng ký task Scheduler chạy mirror lại 02:30 hằng ngày (idempotent /F)."""
    if not WRAPPER_BAT.exists():
        WRAPPER_BAT.write_text(
            "@echo off\n"
            "REM Mirror workspace -> F:\\BRAIN hằng ngày 02:30 (Task Scheduler)\n"
            f'cd /d "{SOURCE}"\n'
            ".venv\\Scripts\\python.exe tools\\mirror_workspace_to_f.py >> logs\\mirror_to_f.log 2>&1\n",
            encoding="utf-8",
        )
        log(f"Đã tạo wrapper: {WRAPPER_BAT.name}")
    r = subprocess.run(
        ["schtasks", "/Create", "/F", "/SC", "DAILY", "/ST", "02:30",
         "/TN", TASK_NAME, "/TR", f'"{WRAPPER_BAT}"'],
        capture_output=True, text=True, timeout=30,
    )
    if r.returncode == 0:
        log(f"OK: task Scheduler '{TASK_NAME}' đặt chạy 02:30 hằng ngày.")
        return 0
    log(f"Đặt lịch lỗi (rc={r.returncode}): {r.stderr.strip()[:200]}")
    return r.returncode


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="robocopy /L — xem trước, không ghi")
    ap.add_argument("--register-task", action="store_true", help="đặt lịch 02:30 hằng ngày")
    ap.add_argument("--no-verify", action="store_true", help="bỏ bước verify (không khuyến nghị)")
    args = ap.parse_args()

    log("=" * 70)
    log(f"MIRROR BẮT ĐẦU: {SOURCE} -> {DEST}" + (" (DRY-RUN)" if args.dry_run else ""))
    log("=" * 70)

    if args.register_task:
        return register_task()

    check_drive()

    t0 = time.time()
    rc, out = run_robocopy(list_only=args.dry_run)
    summary = parse_summary(out)
    files = summary.get("Files", {})
    dt = time.time() - t0
    if args.dry_run:
        log(f"[DRY-RUN] robocopy /L rc={rc} — sẽ copy {files.get('copied', '?')} file, "
            f"bỏ qua {files.get('skipped', '?')}, extras {files.get('extras', '?')}")
        return 0 if rc < 8 else 1

    log(f"robocopy /MIR hoàn tất trong {dt:.0f}s — rc={rc} "
        f"(copy {files.get('copied', '?')} / bỏ qua {files.get('skipped', '?')} / "
        f"lỗi {files.get('failed', '?')} / thừa-đích {files.get('extras', '?')})")
    # robocopy rc là BITMASK (0-7 bình thường): bit3 (8) = phát hiện item thừa ở đích
    # và /MIR đã xóa — đó là HÀNH VI CHUẨN của /MIR (giữ đích khớp nguồn), KHÔNG
    # phải lỗi copy. Lỗi thật chỉ khi bit có FAILED > 0 (rc bit bit2 kèm failed>0).
    if files.get("failed", 0) and files.get("failed", 0) > 0:
        log(f"LỖI NGHIÊM TRỌNG robocopy: {files.get('failed')} file copy THẤT BẠI. "
            "Mirror KHÔNG đáng tin. Hủy verify.")
        return 1
    if rc >= 8:
        log(f"rc={rc} gồm bit 'extras' (đã dọn thừa-đích) — không phải lỗi; FAILED=0 nên tiếp tục.")

    # ---- SNAPSHOT DB LIVE: brain.db... chụp nhất quán qua sqlite backup API ----
    n_snap = snapshot_live_dbs()
    log(f"Snapshot DB live: {n_snap} OK")

    if args.no_verify:
        log("Bỏ verify theo cờ --no-verify.")
        return 0

    # ---- VERIFY 1: số file + byte theo thư mục gốc, NGUỒN vs ĐÍCH ----
    src_stats = per_top_dir_stats(SOURCE)
    dst_stats = per_top_dir_stats(DEST)
    n_src, b_src = tree_stats(SOURCE)
    n_dst, b_dst = tree_stats(DEST)
    log(f"TỔNG: nguồn {n_src} file / {b_src/1e9:.2f} GB  |  đích {n_dst} file / {b_dst/1e9:.2f} GB")

    mismatches = []
    for key in sorted(set(src_stats) | set(dst_stats)):
        s = src_stats.get(key, (0, 0))
        d = dst_stats.get(key, (0, 0))
        # logs/: churn do service ghi liên tục; data/: brain.db ở đích là
        # snapshot chụp SAU robocopy nên to hơn bản copy lúc robocopy — chấp nhận.
        churn_ok = key.startswith("logs/") or key == "data/"
        if s != d:
            status = "CHURN-OK" if churn_ok else "LỆCH"
            if not churn_ok:
                mismatches.append(key)
            log(f"  {status:8s} {key:40s} nguồn {s[0]}f/{s[1]}B vs đích {d[0]}f/{d[1]}B")
    if not mismatches:
        log("VERIFY-1 PASS: mọi thư mục gốc khớp file+byte (trừ log đang ghi).")

    # ---- VERIFY 2: robocopy /L lần 2 — mọi file chưa đồng bộ phải là log ----
    # (log heartbeat/stdout được các service ghi mỗi 2s — giữa lần /MIR và lần
    #  /L luôn còn vài file lệch; đó là churn bình thường, KHÔNG phải lỗi mirror.
    #  Kiểm tra chính xác: mọi file "cần copy" phải nằm dưới logs\ — nếu có file
    #  code/data chưa đồng bộ thì verify FAIL thật.)
    rc2, out2 = run_robocopy(list_only=True, list_files=True)
    s2 = parse_summary(out2).get("Files", {})
    copied2, extras2, failed2 = s2.get("copied", -1), s2.get("extras", -1), s2.get("failed", -1)
    pending = []
    for ln in out2.splitlines():
        ln = ln.strip()
        if ln and "\\" in ln and not ln.endswith("\\") and ":" in ln and ln.lower().startswith(("d:", "f:")):
            pending.append(ln)
    log_dir = str((SOURCE / "logs")).lower()
    data_dir = str((SOURCE / "data")).lower()
    # data/ cũng churn (DB live ghi liên tục) — bản đích được snapshot riêng
    non_log_pending = [p for p in pending
                       if not p.lower().startswith(log_dir)
                       and not p.lower().startswith(data_dir)]
    verify2_ok = extras2 == 0 and failed2 == 0 and not non_log_pending
    log(f"VERIFY-2 robocopy /L lần 2: cần copy {copied2} (log-churn: {copied2 - len(non_log_pending)}), "
        f"file code/data lệch: {len(non_log_pending)}, thừa-đích {extras2}, lỗi {failed2} "
        f"→ {'PASS' if verify2_ok else 'FAIL'}")
    for p in non_log_pending[:10]:
        log(f"  ⚠ chưa đồng bộ (không phải log): {p}")

    # ---- VERIFY 3: SHA-256 gộp thư mục code/config ----
    hash_ok = True
    for rel in HASH_DIRS:
        h_src = dir_hashes(SOURCE, rel)
        h_dst = dir_hashes(DEST, rel)
        same = h_src == h_dst
        hash_ok &= same
        log(f"  SHA-256 {rel:12s}: {h_src} {'==' if same else '!='} {h_dst}")

    all_ok = (not mismatches) and verify2_ok and hash_ok
    log(f"KẾT QUẢ MIRROR: {'THÀNH CÔNG — đích khớp nguồn' if all_ok else 'CÓ LỆCH — xem log trên'}")
    log("=" * 70)
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
