"""
QUAN AI BRAIN — Installer & Verifier for DB Browser for SQLite 3.13.1-win64
Downloads official v3.13.1-win64 portable release, extracts to tools/DBBrowser,
and creates 1-click launcher for data/brain.db.
"""
import os
import sys
import urllib.request
import zipfile
import subprocess
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent
TOOLS_DIR = WORKSPACE / "tools"
INSTALL_DIR = TOOLS_DIR / "DBBrowser"
EXE_PATH = INSTALL_DIR / "DB Browser for SQLite.exe"
ZIP_PATH = TOOLS_DIR / "DB.Browser.for.SQLite-v3.13.1-win64.zip"
DOWNLOAD_URL = "https://github.com/sqlitebrowser/sqlitebrowser/releases/download/v3.13.1/DB.Browser.for.SQLite-v3.13.1-win64.zip"
DB_PATH = WORKSPACE / "data" / "brain.db"
LAUNCHER_BAT = WORKSPACE / "MO_TRAP_TRI_NHO_SQLITE.bat"

def download_file(url: str, dest_path: Path):
    print(f"[*] Downloading {url} ...")
    def report_hook(block_num, block_size, total_size):
        downloaded = block_num * block_size
        if total_size > 0:
            percent = min(100.0, downloaded * 100.0 / total_size)
            mb_down = downloaded / (1024 * 1024)
            mb_tot = total_size / (1024 * 1024)
            sys.stdout.write(f"\r    -> {percent:.1f}% ({mb_down:.2f}/{mb_tot:.2f} MB)")
            sys.stdout.flush()
    urllib.request.urlretrieve(url, dest_path, reporthook=report_hook)
    print("\n[+] Download completed successfully.")

def install_portable():
    INSTALL_DIR.mkdir(parents=True, exist_ok=True)
    if EXE_PATH.exists():
        print(f"[+] DB Browser for SQLite already present at: {EXE_PATH}")
        return True

    if not ZIP_PATH.exists() or ZIP_PATH.stat().st_size < 10000000:
        download_file(DOWNLOAD_URL, ZIP_PATH)

    print(f"[*] Extracting {ZIP_PATH.name} to {INSTALL_DIR} ...")
    with zipfile.ZipFile(ZIP_PATH, 'r') as zf:
        zf.extractall(INSTALL_DIR)
    print("[+] Extraction completed.")

    if EXE_PATH.exists():
        print(f"[+] Verified executable: {EXE_PATH}")
        # Clean up zip archive to save disk space
        try:
            ZIP_PATH.unlink()
            print("[+] Cleaned up temporary zip archive.")
        except Exception:
            pass
        return True
    else:
        # Check subdirectories
        sub_exes = list(INSTALL_DIR.rglob("DB Browser for SQLite.exe"))
        if sub_exes:
            print(f"[+] Found executable in subfolder: {sub_exes[0]}")
            return True
        print("[-] Executable not found after extraction!")
        return False

def create_one_click_launcher():
    actual_exe = EXE_PATH
    if not actual_exe.exists():
        sub_exes = list(INSTALL_DIR.rglob("DB Browser for SQLite.exe"))
        if sub_exes:
            actual_exe = sub_exes[0]

    bat_content = f"""@echo off
chcp 65001 > nul
title QUAN AI BRAIN — Mo Trap Tri Nho Chuyen Sau (SQLite)
echo ======================================================================
echo    QUAN AI BRAIN — MO TRAP TRI NHO CHUYEN SAU (DB BROWSER FOR SQLITE)
echo ======================================================================
echo Dang mo kho tri nho: data\\brain.db ...
start "" "{actual_exe}" "%~dp0data\\brain.db"
exit
"""
    with open(LAUNCHER_BAT, "w", encoding="utf-8") as f:
        f.write(bat_content)
    print(f"[+] Created 1-click launcher: {LAUNCHER_BAT}")

def try_winget_install():
    print("[*] Checking if winget system-wide install is possible...")
    try:
        cmd = [
            "winget", "install", "--id=sqlitebrowser.sqlitebrowser", "-e",
            "--accept-package-agreements", "--accept-source-agreements", "--silent"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        print(f"[i] Winget return code: {res.returncode}")
        if res.returncode == 0:
            print("[+] Winget system-wide installation succeeded.")
        else:
            print(f"[i] Winget info: {res.stdout.strip()[:100]} | {res.stderr.strip()[:100]}")
    except Exception as e:
        print(f"[i] Winget skipped: {e}")

if __name__ == "__main__":
    print("=== QUAN AI BRAIN: DB BROWSER INSTALLATION ===")
    ok = install_portable()
    if ok:
        create_one_click_launcher()
    try_winget_install()
    print("=== INSTALLATION COMPLETE ===")

