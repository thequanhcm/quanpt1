"""Check brain.db schema."""
import sqlite3

conn = sqlite3.connect("E:/AI/QUAN AI BRAIN/data/brain.db")
cursor = conn.cursor()

# List tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = cursor.fetchall()

print("TABLES IN brain.db:")
for table in tables:
    table_name = table[0]
    print(f"\n{'='*70}")
    print(f"TABLE: {table_name}")
    print('='*70)
    
    # Get schema
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    
    print("Columns:")
    for col in columns:
        print(f"  {col[1]:20} {col[2]:15} {'NOT NULL' if col[3] else ''}")
    
    # Count
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    count = cursor.fetchone()[0]
    print(f"\nTotal records: {count}")
    
    # Sample
    cursor.execute(f"SELECT * FROM {table_name} LIMIT 1")
    row = cursor.fetchone()
    if row:
        print("\nSample record:")
        for i, col in enumerate(columns):
            val = row[i] if row[i] is not None else "NULL"
            val_str = str(val)[:50]
            print(f"  {col[1]:20}: {val_str}")

conn.close()