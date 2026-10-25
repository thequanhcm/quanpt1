"""Daily database backup for QUAN AI BRAIN."""
import os
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = r"E:\AI\QUAN AI BRAIN"
DB_PATH = os.path.join(BASE_DIR, "data", "brain.db")
BACKUP_DIR = os.path.join(BASE_DIR, "backups")

def main():
    Path(BACKUP_DIR).mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(BACKUP_DIR, f"brain_{timestamp}.db")
    
    try:
        shutil.copy2(DB_PATH, backup_file)
        print(f"Backup created: {backup_file}")
        
        # Keep only last 30 backups
        backups = sorted(Path(BACKUP_DIR).glob("brain_*.db"))
        for old in backups[:-30]:
            old.unlink()
            print(f"Deleted old backup: {old.name}")
    except Exception as e:
        print(f"Backup failed: {e}")

if __name__ == "__main__":
    main()
