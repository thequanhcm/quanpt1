#!/usr/bin/env python3
"""
Battery AI — Database Inspector
Liệt kê schema và thống kê cơ bản của database Battery AI

Usage:
    python inspect_db.py [--db path/to/battery_ups_v4.db]
"""

import sys
import os
import sqlite3

DEFAULT_DB = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "..",
    "battery-ai-", "BATTERY_AI_V4", "data", "battery_ups_v4.db"
)

def inspect(db_path):
    if not os.path.exists(db_path):
        print(f"❌ Database not found: {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # List tables
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [r[0] for r in cur.fetchall()]
    
    print(f"📦 Database: {db_path}")
    print(f"   Size: {os.path.getsize(db_path) / 1024 / 1024:.1f} MB")
    print(f"   Tables: {len(tables)}")
    print()
    
    for table in tables:
        cur.execute(f"SELECT COUNT(*) FROM [{table}]")
        count = cur.fetchone()[0]
        cur.execute(f"PRAGMA table_info([{table}])")
        cols = cur.fetchall()
        col_names = [c[1] for c in cols]
        print(f"   📋 {table} ({count:,} rows)")
        print(f"      Columns: {', '.join(col_names)}")
    
    conn.close()

if __name__ == "__main__":
    db = DEFAULT_DB
    for i, arg in enumerate(sys.argv[1:], 1):
        if arg == "--db" and i < len(sys.argv) - 1:
            db = sys.argv[i + 1]
    db = os.path.abspath(db)
    inspect(db)
