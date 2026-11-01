"""Test continuous learning by checking if new facts were learned."""
import sys
sys.path.insert(0, "src")

from quan_ai_brain.memory.sqlite_store import MemoryStore

store = MemoryStore("data/brain.db")

print("=" * 60)
print("Testing Continuous Learning — Fact Extraction")
print("=" * 60)

# Check for new knowledge about work hours
print("\n🔍 Searching for 'work hours' knowledge:")
rows = store._connection.execute(
    "SELECT id, statement, status, created_at_utc "
    "FROM candidate_knowledge "
    "WHERE LOWER(statement) LIKE '%buổi sáng%' OR LOWER(statement) LIKE '%8h%' OR LOWER(statement) LIKE '%làm việc%'"
    "ORDER BY created_at_utc DESC LIMIT 5"
).fetchall()

if rows:
    print(f"   ✅ Found {len(rows)} knowledge items about work hours:")
    for row in rows:
        print(f"\n   [{row[0][:20]}...]")
        print(f"   Statement: {row[1][:80]}...")
        print(f"   Status: {row[2]}")
        print(f"   Created: {row[3][:19]}")
else:
    print("   ⚠️  No knowledge about work hours found yet")
    print("   ℹ️  Fact may still be in quarantine or not yet extracted")

# Check total counts
print("\n📊 Current Knowledge State:")
total = store._connection.execute("SELECT COUNT(*) FROM candidate_knowledge").fetchone()[0]
approved = store._connection.execute("SELECT COUNT(*) FROM candidate_knowledge WHERE status='approved'").fetchone()[0]
quarantined = store._connection.execute("SELECT COUNT(*) FROM candidate_knowledge WHERE status='quarantined'").fetchone()[0]

print(f"   Total knowledge items: {total}")
print(f"   Approved: {approved}")
print(f"   Quarantined (awaiting approval): {quarantined}")

# Check recent episodes
print("\n📝 Recent Conversations (last 5 minutes):")
episodes = store._connection.execute(
    "SELECT COUNT(*) FROM episodes WHERE created_at_utc > datetime('now', '-5 minutes')"
).fetchone()[0]
print(f"   {episodes} episodes in last 5 minutes")

print("\n" + "=" * 60)
if rows:
    print("✅ SUCCESS: System learned new facts!")
else:
    print("ℹ️  Fact extraction may take a few minutes (background process)")
print("=" * 60)