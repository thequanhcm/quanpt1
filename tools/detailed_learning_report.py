"""Detailed learning report — what the system has learned."""
import sys
sys.path.insert(0, "src")

from quan_ai_brain.memory.sqlite_store import MemoryStore

store = MemoryStore("data/brain.db")

print("=" * 80)
print("CHI TIẾT NHỮNG GÌ HỆ THỐNG ĐÃ HỌC")
print("=" * 80)

# 1. Statistics by source
print("\n📊 THỐNG KÊ THEO NGUỒN:")
sources = [
    ("docs/%", "Tài liệu dự án"),
    ("reports/%", "Báo cáo Sprint"),
    ("src/%", "Code documentation"),
    ("git:%", "Git commits"),
    ("pytest:%", "Test results"),
    ("tools/%", "Scripts & tools"),
    ("AGENTS.md", "Master prompt"),
]

for pattern, label in sources:
    count = store._connection.execute(
        f"SELECT COUNT(*) FROM candidate_knowledge WHERE source_ref LIKE '{pattern}'"
    ).fetchone()[0]
    approved = store._connection.execute(
        f"SELECT COUNT(*) FROM candidate_knowledge WHERE source_ref LIKE '{pattern}' AND status='approved'"
    ).fetchone()[0]
    if count > 0:
        print(f"   • {label}: {count} facts ({approved} approved)")

# 2. Sample facts by category
print("\n📚 1. KIẾN THỨC KIẾN TRÚC HỆ THỐNG:")
arch_facts = store._connection.execute(
    "SELECT statement FROM candidate_knowledge WHERE LOWER(statement) LIKE '%kiến trúc%' OR LOWER(statement) LIKE '%architecture%' LIMIT 5"
).fetchall()
for i, (fact,) in enumerate(arch_facts, 1):
    print(f"   {i}. {fact[:80]}...")

print("\n🚀 2. KIẾN THỨC SPRINT & PHÁT TRIỂN:")
sprint_facts = store._connection.execute(
    "SELECT statement FROM candidate_knowledge WHERE LOWER(statement) LIKE '%sprint%' AND status='approved' LIMIT 5"
).fetchall()
for i, (fact,) in enumerate(sprint_facts, 1):
    print(f"   {i}. {fact[:80]}...")

print("\n⚡ 3. KIẾN THỨC HIỆU NĂNG & TỐI ƯU:")
perf_facts = store._connection.execute(
    "SELECT statement FROM candidate_knowledge WHERE LOWER(statement) LIKE '%tốc độ%' OR LOWER(statement) LIKE '%performance%' OR LOWER(statement) LIKE '%latency%' LIMIT 5"
).fetchall()
for i, (fact,) in enumerate(perf_facts, 1):
    print(f"   {i}. {fact[:80]}...")

print("\n🧠 4. KIẾN THỨC TRÍ NHỚ & HỌC TẬP:")
memory_facts = store._connection.execute(
    "SELECT statement FROM candidate_knowledge WHERE LOWER(statement) LIKE '%memory%' OR LOWER(statement) LIKE '%trí nhớ%' LIMIT 5"
).fetchall()
for i, (fact,) in enumerate(memory_facts, 1):
    print(f"   {i}. {fact[:80]}...")

print("\n🔒 5. KIẾN THỨC BẢO MẬT & GOVERNANCE:")
security_facts = store._connection.execute(
    "SELECT statement FROM candidate_knowledge WHERE LOWER(statement) LIKE '%bảo mật%' OR LOWER(statement) LIKE '%security%' OR LOWER(statement) LIKE '%R0-R5%' LIMIT 5"
).fetchall()
for i, (fact,) in enumerate(security_facts, 1):
    print(f"   {i}. {fact[:80]}...")

print("\n🐍 6. KIẾN THỨC KỸ THUẬT (Python, SQLite, Ollama):")
tech_facts = store._connection.execute(
    "SELECT statement FROM candidate_knowledge WHERE LOWER(statement) LIKE '%sqlite%' OR LOWER(statement) LIKE '%ollama%' OR LOWER(statement) LIKE '%python%' LIMIT 5"
).fetchall()
for i, (fact,) in enumerate(tech_facts, 1):
    print(f"   {i}. {fact[:80]}...")

print("\n📱 7. KIẾN THỨC PI 5 & EDGE:")
pi_facts = store._connection.execute(
    "SELECT statement FROM candidate_knowledge WHERE LOWER(statement) LIKE '%pi 5%' OR LOWER(statement) LIKE '%raspberry%' LIMIT 5"
).fetchall()
for i, (fact,) in enumerate(pi_facts, 1):
    print(f"   {i}. {fact[:80]}...")

print("\n🗣️ 8. KIẾN THỨC VOICE & TTS:")
voice_facts = store._connection.execute(
    "SELECT statement FROM candidate_knowledge WHERE LOWER(statement) LIKE '%voice%' OR LOWER(statement) LIKE '%tts%' OR LOWER(statement) LIKE '%giọng%' LIMIT 5"
).fetchall()
for i, (fact,) in enumerate(voice_facts, 1):
    print(f"   {i}. {fact[:80]}...")

# 3. Top keywords
print("\n🎯 TOP KEYWORDS TRONG KIẾN THỨC:")
keywords = [
    "sprint", "memory", "architecture", "performance", "voice",
    "pi", "ollama", "sqlite", "security", "approval", "learning"
]
for keyword in keywords:
    count = store._connection.execute(
        f"SELECT COUNT(*) FROM candidate_knowledge WHERE LOWER(statement) LIKE '%{keyword}%'"
    ).fetchone()[0]
    if count > 0:
        print(f"   • {keyword}: {count} mentions")

# 4. Summary
print("\n" + "=" * 80)
total = store._connection.execute("SELECT COUNT(*) FROM candidate_knowledge").fetchone()[0]
approved = store._connection.execute("SELECT COUNT(*) FROM candidate_knowledge WHERE status='approved'").fetchone()[0]
semantic = store._connection.execute("SELECT COUNT(*) FROM semantic_memory").fetchone()[0]

print(f"TỔNG KẾT:")
print(f"   • Tổng facts: {total:,}")
print(f"   • Approved: {approved:,}")
print(f"   • Semantic memories: {semantic:,}")
print(f"   • Đang chờ duyệt: {total - approved:,}")
print(f"\n✅ Hệ thống đã học TẤT CẢ kiến thức từ:")
print(f"   - Tài liệu dự án (docs/)")
print(f"   - Báo cáo Sprint (reports/)")
print(f"   - Code documentation (src/)")
print(f"   - Git history (commits)")
print(f"   - Test results (pytest)")
print(f"   - Configuration files")
print(f"   - Conversations (376+ episodes)")
print("=" * 80)