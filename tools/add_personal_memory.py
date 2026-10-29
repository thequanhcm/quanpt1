#!/usr/bin/env python3
"""
Add personal memory to brain.db

Usage:
    python tools/add_personal_memory.py "Vợ anh tên là Phương Lan"
    python tools/add_personal_memory.py "Anh tên là Phạm Thế Quân" --tags name,personal
"""

import sqlite3
import sys
import json
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "brain.db"


def add_memory(statement, tags=None, approved_by="owner"):
    """Add memory to semantic_memory table."""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    try:
        # Generate ID
        import uuid
        memory_id = str(uuid.uuid4())[:12]
        
        # Timestamp
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Tags
        tags_str = json.dumps(tags) if tags else "[]"
        
        # Insert into semantic_memory
        cursor.execute('''
            INSERT INTO semantic_memory (id, created_at_utc, statement, source_ref, approved_by, regression_passed)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            memory_id,
            timestamp,
            statement,
            f"manual:{tags_str}",
            approved_by,
            1  # regression_passed = 1 (approved)
        ))
        
        conn.commit()
        
        print("\n" + "="*70)
        print("✅ TRÍ NHỚ ĐÃ ĐƯỢC THÊM THÀNH CÔNG!")
        print("="*70)
        print(f"  ID: {memory_id}")
        print(f"  Nội dung: {statement}")
        print(f"  Tags: {tags_str}")
        print(f"  Phê duyệt bởi: {approved_by}")
        print(f"  Thời gian: {timestamp}")
        print("="*70)
        print("\n💡 TONY giờ đã nhớ thông tin này!")
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"\n❌ Lỗi: {e}\n")
    finally:
        conn.close()


def search_memory(query):
    """Search memory by statement."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT id, created_at_utc, statement, source_ref, approved_by, regression_passed
            FROM semantic_memory
            WHERE statement LIKE ?
            ORDER BY created_at_utc DESC
            LIMIT 10
        ''', (f'%{query}%',))
        
        rows = cursor.fetchall()
        
        if not rows:
            print(f"\n❌ Không tìm thấy trí nhớ nào chứa '{query}'\n")
            return
        
        print("\n" + "="*70)
        print(f"🔍 KẾT QUẢ TÌM KIẾM: '{query}' ({len(rows)} kết quả)")
        print("="*70)
        
        for row in rows:
            print(f"\n[ID: {row['id']}]")
            print(f"  Nội dung: {row['statement']}")
            print(f"  Nguồn: {row['source_ref']}")
            print(f"  Phê duyệt: {row['approved_by']}")
            print(f"  Thời gian: {row['created_at_utc']}")
        
        print("\n" + "="*70 + "\n")
        
    except Exception as e:
        print(f"\n❌ Lỗi tìm kiếm: {e}\n")
    finally:
        conn.close()


def main():
    if len(sys.argv) < 2:
        print("""
🧠 QUẢN LÝ TRÍ NHỚ CÁ NHÂN

Cách dùng:
  Thêm trí nhớ:
    python tools/add_personal_memory.py "Vợ anh tên là Phương Lan"
    python tools/add_personal_memory.py "Anh tên là Phạm Thế Quân" --tags name,personal
  
  Tìm kiếm trí nhớ:
    python tools/add_personal_memory.py --search "phương lan"
    python tools/add_personal_memory.py --search "tên"

Ví dụ:
  python tools/add_personal_memory.py "Vợ anh tên là Phương Lan"
  python tools/add_personal_memory.py --search "vợ"
        """)
        return
    
    if sys.argv[1] == "--search":
        if len(sys.argv) < 3:
            print("❌ Vui lòng nhập từ khóa tìm kiếm")
            return
        search_memory(sys.argv[2])
    else:
        # Add memory
        statement = sys.argv[1]
        tags = []
        
        # Check for --tags
        for i, arg in enumerate(sys.argv):
            if arg == "--tags" and i + 1 < len(sys.argv):
                tags = sys.argv[i + 1].split(",")
                break
        
        add_memory(statement, tags)


if __name__ == "__main__":
    main()