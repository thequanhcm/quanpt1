r"""Di trá duong dan may cu -> may moi (DESKTOP-SNMI929, user quocd).

May cu: user DELL, workspace E:\AI\QUAN AI BRAIN, Ollama E:\AI\Ollama
May moi: user quocd, workspace D:\AI\AI Quanpt1 2026\BRAIN,
         Ollama C:\Users\quocd\AppData\Local\Programs\Ollama

Pham vi: CHI file code thao tac (src/, tools/, *.bat, *.ps1 goc workspace).
KHONG dong vao logs/, reports/, docs/, 'bao cao...' - do la ho so lich su.

Cach dung:
    python tools/migrate_paths_to_new_pc.py --dry-run   # xem truoc
    python tools/migrate_paths_to_new_pc.py             # ap dung (co backup)
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent
BACKUP_DIR = WORKSPACE / "backups" / "path_migration_20261030"

# Thu tu quan trong: chuoi dai/dac biet truoc, fallback ngan sau cung.
RAW_REPLACEMENTS: list[tuple[str, str]] = [
    # Workspace may cu -> may moi ( moi kieu escape 1 lan )
    (r"E:\AI\QUAN AI BRAIN", r"D:\AI\AI Quanpt1 2026\BRAIN"),
    (r"E:/AI/QUAN AI BRAIN", r"D:/AI/AI Quanpt1 2026/BRAIN"),
    (r"E:\\AI\\QUAN AI BRAIN", r"D:\\AI\\AI Quanpt1 2026\\BRAIN"),
    # netmind Desktop may cu -> may moi
    (r"C:\Users\DELL\AppData\Local\netmind_desktop",
     r"C:\Users\quocd\AppData\Local\netmind_desktop"),
    (r"C:/Users/DELL/AppData/Local/netmind_desktop",
     r"C:/Users/quocd/AppData/Local/netmind_desktop"),
    (r"C:\\Users\\DELL\\AppData\\Local\\netmind_desktop",
     r"C:\\Users\\quocd\\AppData\\Local\\netmind_desktop"),
    # Ollama may cu -> may moi
    (r"E:\AI\Ollama", r"C:\Users\quocd\AppData\Local\Programs\Ollama"),
    (r"E:/AI/Ollama", r"C:/Users/quocd/AppData/Local/Programs/Ollama"),
    (r"E:\\AI\\Ollama", r"C:\\Users\\quocd\\AppData\\Local\\Programs\\Ollama"),
    # Fallback cung: bat ky con lai cua user cu
    (r"C:\Users\DELL", r"C:\Users\quocd"),
    (r"C:/Users/DELL", r"C:/Users/quocd"),
    (r"C:\\Users\\DELL", r"C:\\Users\\quocd"),
]

# Logon trigger dang goi userId may cu "DELL"
TARGET_FILES = sorted(
    set(
        list((WORKSPACE / "src").rglob("*.py"))
        + list((WORKSPACE / "tools").glob("*.py"))
        + list((WORKSPACE / "tools").glob("*.bat"))
        + list((WORKSPACE / "tools").glob("*.ps1"))
        + list(WORKSPACE.glob("*.bat"))
        + list(WORKSPACE.glob("*.ps1"))
    )
)


def apply_replacements(text: str) -> tuple[str, int]:
    count = 0
    for old, new in RAW_REPLACEMENTS:
        n = text.count(old)
        if n:
            text = text.replace(old, new)
            count += n
    # userId "DELL" trong logon trigger scripts
    for token in ('UserId = "DELL"', 'trig.UserId = "DELL"'):
        n = text.count(token)
        if n:
            text = text.replace(token, token.replace("DELL", "quocd"))
            count += n
    return text, count


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    changed = []
    self_path = Path(__file__).resolve()
    for path in TARGET_FILES:
        if path.resolve() == self_path:
            continue  # khong tu-sua script migration nay (bao ve bang mapping)
        try:
            raw = path.read_bytes()
        except OSError:
            continue
        has_bom = raw.startswith(b"\xef\xbb\xbf")
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            continue  # file nhi phan / encoding khac: bo qua
        new_text, n = apply_replacements(text)
        if n == 0:
            continue
        changed.append((path, n))

    print(f"Scan {len(TARGET_FILES)} files, can sua {len(changed)} file "
          f"({sum(n for _, n in changed)} thay the):")
    for path, n in changed:
        print(f"  {n:2d}x {path.relative_to(WORKSPACE)}")

    if args.dry_run:
        print("[DRY-RUN] Khong ghi gi ca.")
        return 0

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    for path, _n in changed:
        rel = path.relative_to(WORKSPACE)
        dest = BACKUP_DIR / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.exists():
            shutil.copy2(path, dest)
        raw = path.read_bytes()
        has_bom = raw.startswith(b"\xef\xbb\xbf")
        text = raw.decode("utf-8-sig")
        new_text, _ = apply_replacements(text)
        data = new_text.encode("utf-8")
        if has_bom:
            data = b"\xef\xbb\xbf" + data
        path.write_bytes(data)
    print(f"[APPLIED] Da backup goc vao {BACKUP_DIR.relative_to(WORKSPACE)} "
          f"va sua {len(changed)} file.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
