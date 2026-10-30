"""
Script xem và quản lý trí nhớ trong brain.db

Usage:
    python tools/manage_brain_memory.py --list
    python tools/manage_brain_memory.py --add "Vợ anh tên là Phương Lan" --type semantic --tags family,wife
    python tools/manage_brain_memory.py --search "phương lan"
    python tools/manage_brain_memory.py --view-table semantic_memory
"""

import sqlite3
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "brain.db"


def get_connection():
    """Get database connection."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def list_tables():
    """List all tables in database."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    print("\n" + "="*70)
    print("📊 TABLES IN brain.db")
    print("="*70)
    for table in tables:
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"  • {table}: {count} records")
    print("="*70 + "\n")


def view_table(table_name, limit=10):
    """View records from a table."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(f"SELECT * FROM {table_name} LIMIT {limit}")
        rows = cursor.fetchall()
        
        if not rows:
            print(f"\n❌ Table '{table_name}' is empty or doesn't exist.\n")
            conn.close()
            return
        
        # Get column names
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [col[1] for col in cursor.fetchall()]
        
        print("\n" + "="*70)
        print(f"📋 TABLE: {table_name} (showing first {limit} records)")
        print("="*70)
        
        # Print headers
        header = " | ".join([str(col)[:20].ljust(20) for col in columns])
        print(header)
        print("-" * len(header))
        
        # Print rows
        for row in rows:
            values = [str(row[col])[:20].ljust(20) for col in columns]
            print(" | ".join(values))
        
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error: {e}\n")
    finally:
        conn.close()


def add_memory(content, memory_type="semantic", tags=None, verification_status="USER_PROVIDED"):
    """Add new memory to database."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Determine which table to use
        if memory_type == "episodic":
            table = "episodic_memory"
            # Check if table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='episodic_memory'")
            if not cursor.fetchone():
                # Create table if not exists
                cursor.execute('''
                    CREATE TABLE episodic_memory (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        content TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        session_id TEXT,
                        metadata TEXT
                    )
                ''')
        else:
            table = "semantic_memory"
            # Check if table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='semantic_memory'")
            if not cursor.fetchone():
                # Create table if not exists
                cursor.execute('''
                    CREATE TABLE semantic_memory (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        content TEXT NOT NULL,
                        memory_type TEXT DEFAULT 'semantic',
                        verification_status TEXT DEFAULT 'UNVERIFIED',
                        tags TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT,
                        metadata TEXT
                    )
                ''')
        
        # Insert record
        timestamp = datetime.now(timezone.utc).isoformat()
        tags_str = ",".join(tags) if tags else ""
        metadata = json.dumps({"source": "manual_add", "added_by": "owner"})
        
        if memory_type == "episodic":
            cursor.execute(f'''
                INSERT INTO {table} (content, timestamp, metadata)
                VALUES (?, ?, ?)
            ''', (content, timestamp, metadata))
        else:
            cursor.execute(f'''
                INSERT INTO {table} (content, memory_type, verification_status, tags, created_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (content, memory_type, verification_status, tags_str, timestamp, metadata))
        
        conn.commit()
        record_id = cursor.lastrowid
        
        print("\n" + "="*70)
        print("✅ MEMORY ADDED SUCCESSFULLY!")
        print("="*70)
        print(f"  ID: {record_id}")
        print(f"  Type: {memory_type}")
        print(f"  Content: {content}")
        print(f"  Tags: {tags_str or 'None'}")
        print(f"  Verification: {verification_status}")
        print(f"  Timestamp: {timestamp}")
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error adding memory: {e}\n")
    finally:
        conn.close()


def search_memory(query, memory_type=None, limit=10):
    """Search memory by content."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        if memory_type == "episodic":
            table = "episodic_memory"
        elif memory_type == "semantic":
            table = "semantic_memory"
        else:
            # Search both
            cursor.execute(f'''
                SELECT 'episodic' as type, id, content, timestamp as date, metadata
                FROM episodic_memory
                WHERE content LIKE ?
                UNION ALL
                SELECT 'semantic' as type, id, content, created_at as date, metadata
                FROM semantic_memory
                WHERE content LIKE ?
                ORDER BY date DESC
                LIMIT ?
            ''', (f'%{query}%', f'%{query}%', limit))
            
            rows = cursor.fetchall()
            
            if not rows:
                print(f"\n❌ No memories found containing '{query}'\n")
                conn.close()
                return
            
            print("\n" + "="*70)
            print(f"🔍 SEARCH RESULTS: '{query}' ({len(rows)} found)")
            print("="*70)
            
            for row in rows:
                print(f"\n[{row['type'].upper()}] ID: {row['id']}")
                print(f"  Content: {row['content']}")
                print(f"  Date: {row['date']}")
                if row['metadata']:
                    print(f"  Metadata: {row['metadata']}")
            
            print("\n" + "="*70 + "\n")
            conn.close()
            return
        
        # Search specific table
        cursor.execute(f'''
            SELECT * FROM {table}
            WHERE content LIKE ?
            LIMIT ?
        ''', (f'%{query}%', limit))
        
        rows = cursor.fetchall()
        
        if not rows:
            print(f"\n❌ No {memory_type} memories found containing '{query}'\n")
            conn.close()
            return
        
        print("\n" + "="*70)
        print(f"🔍 SEARCH RESULTS: '{query}' in {memory_type} ({len(rows)} found)")
        print("="*70)
        
        for row in rows:
            print(f"\n[ID: {row['id']}]")
            print(f"  Content: {row['content']}")
            if 'tags' in row.keys():
                print(f"  Tags: {row['tags']}")
            if 'verification_status' in row.keys():
                print(f"  Status: {row['verification_status']}")
            if 'timestamp' in row.keys():
                print(f"  Date: {row['timestamp']}")
            elif 'created_at' in row.keys():
                print(f"  Date: {row['created_at']}")
        
        print("\n" + "="*70 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error searching: {e}\n")
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Manage brain.db memory")
    parser.add_argument("--list", action="store_true", help="List all tables")
    parser.add_argument("--view-table", type=str, help="View records from a table")
    parser.add_argument("--add", type=str, help="Add new memory")
    parser.add_argument("--type", choices=["semantic", "episodic"], default="semantic", help="Memory type")
    parser.add_argument("--tags", type=str, help="Comma-separated tags")
    parser.add_argument("--status", choices=["USER_PROVIDED", "VERIFIED", "UNVERIFIED"], default="USER_PROVIDED", help="Verification status")
    parser.add_argument("--search", type=str, help="Search memory by content")
    parser.add_argument("--limit", type=int, default=10, help="Limit results")
    
    args = parser.parse_args()
    
    if args.list:
        list_tables()
    elif args.view_table:
        view_table(args.view_table, args.limit)
    elif args.add:
        tags = args.tags.split(",") if args.tags else None
        add_memory(args.add, args.type, tags, args.status)
    elif args.search:
        search_memory(args.search, args.type, args.limit)
    else:
        print("""
🧠 BRAIN.DB MEMORY MANAGER

Usage:
  python tools/manage_brain_memory.py --list
  python tools/manage_brain_memory.py --view-table semantic_memory
  python tools/manage_brain_memory.py --add "Vợ anh tên là Phương Lan" --type semantic --tags family,wife --status USER_PROVIDED
  python tools/manage_brain_memory.py --search "phương lan"
  python tools/manage_brain_memory.py --search "vợ" --type semantic

Examples:
  Add personal info:
    python tools/manage_brain_memory.py --add "Anh tên là Phạm Thế Quân" --type semantic --tags personal,name --status USER_PROVIDED
    
  Add family info:
    python tools/manage_brain_memory.py --add "Vợ anh tên là Phương Lan" --type semantic --tags family,wife --status USER_PROVIDED
    
  Search:
    python tools/manage_brain_memory.py --search "phương lan"
        """)


if __name__ == "__main__":
    main()