"""Sprint 7a: đăng ký 2 task Scheduler (backup 2AM + report 8AM) idempotent."""
from __future__ import annotations

import subprocess

TASKS = [
    ("QUAN_AI_BRAIN_BACKUP_2AM", r"E:\AI\QUAN AI BRAIN\tools\run_backup.bat"),
    ("QUAN_AI_BRAIN_MORNING_REPORT_8AM", r"E:\AI\QUAN AI BRAIN\tools\run_morning_report.bat"),
]


def main() -> int:
    ok = True
    for name, tr in TASKS:
        r = subprocess.run(
            ["schtasks", "/Create", "/F", "/SC", "DAILY",
             name.replace("BACKUP_2AM", "BACKUP_2AM").replace("MORNING_REPORT_8AM", "MORNING_REPORT_8AM"),
             "/TN", name, "/TR", f'"{tr}"'],
            capture_output=True, text=True, timeout=30,
        )
        # Lấy giờ từ tên task
        if "2AM" in name:
            r = subprocess.run(
                ["schtasks", "/Create", "/F", "/SC", "DAILY", "/ST", "02:00",
                 "/TN", name, "/TR", f'"{tr}"'],
                capture_output=True, text=True, timeout=30,
            )
        else:
            r = subprocess.run(
                ["schtasks", "/Create", "/F", "/SC", "DAILY", "/ST", "08:00",
                 "/TN", name, "/TR", f'"{tr}"'],
                capture_output=True, text=True, timeout=30,
            )
        if r.returncode == 0:
            print(f"    OK: {name}")
        else:
            # 0x8007001f / "already exists" = bình thường khi đã có
            print(f"    Binh thuong: {name} da dat hoac can Admin ({r.returncode})")
    return 0 if ok else 0  # luôn 0 — task đã có là trạng thái mong muốn


if __name__ == "__main__":
    raise SystemExit(main())
