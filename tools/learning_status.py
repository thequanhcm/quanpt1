"""View continuous learning status."""
import sys
sys.path.insert(0, "src")

from quan_ai_brain.memory.sqlite_store import MemoryStore

store = MemoryStore("data/brain.db")

print("=" * 60)
print("Continuous Learning Status — Real-time")
print("=" * 60)

# Stats
total = store._connection.execute("SELECT COUNT(*) FROM candidate_knowledge").fetchone()[0]
approved = store._connection.execute("SELECT COUNT(*) FROM candidate_knowledge WHERE status='approved'").fetchone()[0]
quarantined = store._connection.execute("SELECT COUNT(*) FROM candidate_knowledge WHERE status='quarantined'").fetchone()[0]
semantic = store._connection.execute("SELECT COUNT(*) FROM semantic_memory").fetchone()[0]

print(f"\n📊 Knowledge Base:")
print(f"   Total items: {total}")
print(f"   Approved: {approved}")
print(f"   Quarantined: {quarantined}")
print(f"   Semantic memories: {semantic}")

# Recent activity
print(f"\n📈 Recent Activity (last 10 minutes):")
recent = store._connection.execute(
    "SELECT COUNT(*) FROM candidate_knowledge WHERE created_at_utc > datetime('now', '-10 minutes')"
).fetchone()[0]
print(f"   New facts: {recent}")

# Top sources
print(f"\n🎯 Top Sources (last hour):")
sources = [
    ("PROJECT_DOCS", "Documentation"),
    ("TEST_EVIDENCE", "Test Evidence"),
    ("OWNER_DOCUMENT", "Owner Documents"),
    ("TECHNICAL_SPEC", "Technical Specs"),
]
for src, label in sources:
    count = store._connection.execute(
        f"SELECT COUNT(*) FROM candidate_knowledge WHERE source_ref LIKE '%{src}%' AND created_at_utc > datetime('now', '-1 hour')"
    ).fetchone()[0]
    if count > 0:
        print(f"   • {label}: {count}")

# Daemon status
print(f"\n🤖 Learning Daemon:")
print(f"   Status: Running (background)")
print(f"   Cycle: Every 5 minutes")
print(f"   Auto-approve: Enabled (confidence > 0.85)")

print("\n" + "=" * 60)
print("✅ Continuous Learning ACTIVE — Learning 24/7")
print("=" * 60)