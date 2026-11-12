"""Daily database backup for QUAN AI BRAIN.

(11/11/2026, COG-0) Nâng cấp:
- shutil.copy2 (copy thô file đang ghi) → sqlite3 backup API (snapshot nhất quán
  kể cả khi daemon đang ghi; journal_mode=delete nên copy thô có thể dính
  trạng thái bán-transaction).
- Tự verify integrity ngay sau khi sinh backup — file hỏng phải bị xóa + báo
  FAIL (fail-honest), không để lại backup giả tốt.
- main() trả về bool để watchdog guard kiểm tra kết quả (Task Scheduler .bat
  vẫn chạy được như cũ, bỏ qua return value).
"""
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = r"E:\BRAIN"
DB_PATH = os.path.join(BASE_DIR, "data", "brain.db")
BACKUP_DIR = os.path.join(BASE_DIR, "backups")


def main() -> bool:
    """Backup brain.db → backups/brain_YYYYMMDD_HHMMSS.db. Trả True nếu OK."""
    Path(BACKUP_DIR).mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(BACKUP_DIR, f"brain_{timestamp}.db")

    try:
        src = sqlite3.connect(DB_PATH, timeout=30)
        try:
            dst = sqlite3.connect(backup_file)
            try:
                with dst:
                    src.backup(dst)
            finally:
                dst.close()
        finally:
            src.close()

        # Verify NGAY: backup hỏng phải bị xóa, không được im lặng
        check = sqlite3.connect(backup_file)
        try:
            result = check.execute("PRAGMA integrity_check").fetchone()[0]
        finally:
            check.close()
        if result != "ok":
            os.unlink(backup_file)
            print(f"Backup FAILED integrity ({result}): {backup_file}")
            return False

        print(f"Backup created: {backup_file}")

        # Keep only last 30 backups
        backups = sorted(Path(BACKUP_DIR).glob("brain_*.db"))
        for old in backups[:-30]:
            old.unlink()
            print(f"Deleted old backup: {old.name}")
        return True
    except Exception as e:
        print(f"Backup failed: {e}")
        # dọn file rác nếu sqlite tạo dở
        try:
            if os.path.exists(backup_file) and os.path.getsize(backup_file) == 0:
                os.unlink(backup_file)
        except OSError:
            pass
        return False


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
