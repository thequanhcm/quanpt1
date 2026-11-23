# -*- coding: utf-8 -*-
"""Mirror backup E:\\BRAIN → D:\\BRAIN_MIRROR (P0-2, audit 23/11).

Lý do: Toàn bộ hệ thống (100k+ lines code + data + memory) hiện chỉ nằm trên
1 ổ vật lý E:. Nếu ổ E: hỏng = mất toàn bộ. Backup DB 2AM cũng chỉ nằm trên
E: → không phải backup thật sự.

Mirror D: trống 131 GB, đủ chứa code + data (loại .venv, .git, runtime junk).
Dùng robocopy incremental — chỉ copy file mới/thay đổi, nhanh + ít I/O.

Chạy:
  1. Lần đầu: robocopy full copy E:\\BRAIN → D:\\BRAIN_MIRROR (có thể mất ~30-60')
  2. Sau đó: incremental mỗi ngày (chỉ file đổi, ~5-15 phút)
  3. Weekly: md5 sample 10 file ngẫu nhiên để phát hiện silent corruption

Task Scheduler: QUAN_AI_BRAIN_MIRROR_D_DAILY (02:30, sau backup 2AM).

Fail-honest: robocopy exit code > 7 = lỗi (CHÚ Ý: exit code 0-7 là THÀNH CÔNG
theo Microsoft convention — bit 0x01=no extra, bit 0x02=extra, etc.). Code 8+
mới lỗi. Heartbeat ghi status="error" khi exit ≥ 8.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import os
import random
import subprocess
import sys
import time
from pathlib import Path

WORKSPACE = Path(r"E:/BRAIN")
MIRROR = Path(r"D:/BRAIN_MIRROR")

# Folders (dùng /XD) — không copy thư mục + toàn bộ nội dung
EXCLUDE_DIRS = [
    ".venv",
    "__pycache__",
    ".git",
    "_QUARANTINE_20261123",
    ".tmp_motion_frames",
    ".tmp_motion_test",
    "tmp_m5b",
    "backups",
    # data runtime
    "edge_media", "audio", "voice_records", "uat_logs",
    "netchat_files", "mau_frames", "poc_arms", "poc_assets",
    "vector_db_semantic", "frames_345", "frames_vi", "vi_frames", "ref_frames", "v3_check",
]
# Files (dùng /XF) — không copy file khớp pattern
EXCLUDE_FILES = [
    "*.tmp", "*.log",
    "*.db-wal", "*.db-shm", "*.db-journal",
    "_pi5_*",
    "_poc_*", "_m12_*", "_m3_*",
    "_nm_probe.json", "_probe_vids.py",
    "pi5_audio_*.wav",
]


def build_robocopy_args(extra: list[str] | None = None) -> list[str]:
    """Tạo lệnh robocopy với exclude."""
    cmd = [
        "robocopy",
        str(WORKSPACE),
        str(MIRROR),
        "/E",              # copy subtree, kể cả folder rỗng
        "/R:2", "/W:5",    # retry 2 lần, wait 5s
        "/MT:4",           # multi-thread 4 (tiết kiệm I/O)
        "/NFL", "/NDL",    # no file/dir list → log gọn
        "/NP",             # no progress
        "/BYTES",          # size theo byte (chính xác)
    ]
    for d in EXCLUDE_DIRS:
        cmd.extend(["/XD", d])
    for f in EXCLUDE_FILES:
        cmd.extend(["/XF", f])
    if extra:
        cmd.extend(extra)
    return cmd


def run_mirror(dry_run: bool = False, log_path: Path | None = None) -> int:
    """Chạy robocopy. Trả exit code (0-7 = OK theo MS convention; 8+ = lỗi)."""
    if log_path is None:
        log_path = WORKSPACE / "logs" / "mirror_d.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = build_robocopy_args()
    # Ghi log ra file (robocopy ghi stdout vào console, không capture được qua PIPE)
    cmd.append("/LOG+:" + str(log_path))
    if dry_run:
        cmd.append("/L")

    print(f"[{datetime.datetime.now().isoformat(timespec='seconds')}] Bắt đầu mirror...")
    print(f"CMD: {' '.join(cmd[:4])} ... ({len(cmd)} args, {len(EXCLUDE_DIRS)} dir-excludes, {len(EXCLUDE_FILES)} file-excludes)")

    started = time.time()
    try:
        r = subprocess.run(
            cmd,
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=5400,  # 90 phút max
            cwd=str(WORKSPACE),
        )
        rc = r.returncode
        elapsed = time.time() - started
        # Đọc summary từ log file (vì stdout của robocopy qua PIPE thường rỗng)
        try:
            log_content = log_path.read_text(encoding="utf-8", errors="replace")
            last_section = log_content.rsplit("---", 1)[-1]
            # Tìm dòng "Total" trở đi
            total_idx = last_section.rfind("Total")
            summary = last_section[total_idx:total_idx + 500] if total_idx >= 0 else last_section[-300:]
            print(summary.strip())
        except Exception:
            pass
        # Ghi exit vào log
        with open(log_path, "a", encoding="utf-8") as logf:
            logf.write(f"\nexit={rc} elapsed={elapsed:.1f}s\n")
        print(f"exit={rc} elapsed={elapsed:.1f}s")
        return rc
    except subprocess.TimeoutExpired:
        with open(log_path, "a", encoding="utf-8") as logf:
            logf.write("\nTIMEOUT 90 phút — mirror quá chậm\n")
        print("TIMEOUT 90 phút")
        return 9
    except Exception as e:
        with open(log_path, "a", encoding="utf-8") as logf:
            logf.write(f"\nEXCEPTION: {type(e).__name__}: {e}\n")
        return 10


def md5_file(p: Path) -> str:
    h = hashlib.md5()
    try:
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return ""


def md5_sample_verify(n: int = 10, seed: int | None = None) -> tuple[int, int, list[dict]]:
    """Sample n file ngẫu nhiên trong workspace, md5 so với mirror."""
    if seed is not None:
        random.seed(seed)

    all_files = []
    skip_dirs = {".venv", "__pycache__", ".git"}
    for dp, dn, fn in os.walk(WORKSPACE):
        dn[:] = [d for d in dn if d not in skip_dirs]
        for f in fn:
            all_files.append(Path(dp) / f)

    sample = random.sample(all_files, min(n, len(all_files)))
    matched = 0
    details = []
    for f in sample:
        rel = f.relative_to(WORKSPACE)
        mirror_f = MIRROR / rel
        if not mirror_f.exists():
            details.append({"file": str(rel), "status": "missing_in_mirror"})
            continue
        s = md5_file(f)
        m = md5_file(mirror_f)
        if s == m and s:
            matched += 1
            details.append({"file": str(rel), "status": "ok", "md5": s[:8]})
        else:
            details.append({"file": str(rel), "status": "mismatch", "src": s[:8], "mirror": m[:8]})
    return matched, len(sample), details


def install_task() -> None:
    """Cài Task Scheduler chạy 02:30 mỗi ngày (sau backup 2AM)."""
    py = r"E:/BRAIN/.venv/Scripts/python.exe"
    script = str(Path(__file__).resolve())
    task_name = "QUAN_AI_BRAIN_MIRROR_D_DAILY"
    vbs = WORKSPACE / "tools" / "run_mirror_d_hidden.vbs"
    vbs_content = (
        'Set WshShell = CreateObject("WScript.Shell")\r\n'
        f'WshShell.CurrentDirectory = "{WORKSPACE}"\r\n'
        f'WshShell.Run """{py}"" ""{script}"" --once", 0, False\r\n'
    )
    vbs.write_bytes(vbs_content.encode("ascii"))
    print(f"wrote {vbs}")
    cmd = ["schtasks", "/create", "/tn", task_name, "/tr",
           f'"{vbs}"', "/sc", "daily", "/st", "02:30", "/rl", "LIMITED", "/f"]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
    print("schtasks STDOUT:", r.stdout)
    print("schtasks STDERR:", r.stderr)
    print("rc:", r.returncode)


def write_heartbeat(success: bool) -> None:
    """Heartbeat cho task mirror."""
    try:
        sys.path.insert(0, str(WORKSPACE / "tools"))
        from heartbeat import write_heartbeat
        write_heartbeat("QUAN_AI_BRAIN_MIRROR_D_DAILY", "ok" if success else "error")
    except Exception:
        pass


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true", help="Chạy 1 lần (cho Task Scheduler)")
    ap.add_argument("--dry-run", action="store_true", help="Chỉ list, không copy")
    ap.add_argument("--verify", type=int, metavar="N", help="Sample md5 N file (weekly)")
    ap.add_argument("--install-task", action="store_true", help="Cài Task Scheduler")
    args = ap.parse_args()

    if args.install_task:
        install_task()
        write_heartbeat(True)
        return 0
    if args.verify:
        ok, total, details = md5_sample_verify(args.verify, seed=int(time.time()) % 100000)
        print(f"\nMD5 sample: {ok}/{total} khớp")
        for d in details[:5]:
            print(f"  {d['status']:<20} {d['file']}")
        write_heartbeat(ok == total)
        return 0 if ok == total else 1
    rc = run_mirror(dry_run=args.dry_run)
    success = rc < 8
    write_heartbeat(success)
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
