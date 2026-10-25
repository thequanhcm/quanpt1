"""Ingest owner documents into QUAN AI BRAIN Deep Memory — Sprint 3.

Usage:
    python tools/ingest_owner_documents.py

This script ingests:
1. Project documentation from docs/
2. Sprint reports from reports/
3. Owner preferences from memory (if any)
4. Test evidence from tests/

Each document is ingested with:
- source_type: OWNER_DOCUMENT or PROJECT_DOCS
- source_ref: relative path
- source_version: git commit hash
- tags: document category
- expires_days: None (permanent for project docs)

Giai đoạn Sprint 3 (2026-10-25): Ingest baseline documents.
"""
import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, "src")

from quan_ai_brain.memory.knowledge_ingestion import (
    KnowledgeIngestionEngine,
    KnowledgeSource,
)
from quan_ai_brain.memory.sqlite_store import MemoryStore


def ingest_document(engine: KnowledgeIngestionEngine, doc_path: Path, source_type: KnowledgeSource, tags: list[str]) -> int:
    """Ingest a single document."""
    try:
        content = doc_path.read_text(encoding="utf-8")
        if len(content.strip()) < 50:
            return 0  # Skip empty files

        # Extract first 500 chars as statement (simplified for Sprint 3)
        statement = content[:500].strip()
        if len(content) > 500:
            statement += "..."

        record = engine.ingest(
            content=statement,
            source_type=source_type,
            source_ref=str(doc_path.relative_to(Path("."))),
            source_version="baseline_2026-10-25",
            tags=tags,
        )
        print(f"  ✓ Ingested: {doc_path.name} → {record.id}")
        return 1
    except Exception as e:
        print(f"  ✗ Failed: {doc_path.name} — {e}")
        return 0


def main() -> int:
    """Ingest owner documents."""
    print("=" * 60)
    print("Ingesting Owner Documents into Deep Memory")
    print("=" * 60)

    store = MemoryStore("data/brain.db")
    engine = KnowledgeIngestionEngine(store, owner_id="Quanpt1")

    total_ingested = 0

    # 1. Project documentation
    print("\n1. Ingesting project documentation...")
    docs_dir = Path("docs")
    if docs_dir.exists():
        for doc_file in docs_dir.glob("*.md"):
            total_ingested += ingest_document(
                engine, doc_file,
                KnowledgeSource.PROJECT_DOCS,
                ["documentation", "project"]
            )
    else:
        print("  ⚠ docs/ directory not found")

    # 2. Sprint reports
    print("\n2. Ingesting sprint reports...")
    reports_dir = Path("reports")
    if reports_dir.exists():
        for report_file in reports_dir.glob("QUAN_AI_BRAIN_*.md"):
            total_ingested += ingest_document(
                engine, report_file,
                KnowledgeSource.TEST_EVIDENCE,
                ["sprint_report", "evidence"]
            )
    else:
        print("  ⚠ reports/ directory not found")

    # 3. AGENTS.md (master prompt)
    print("\n3. Ingesting master prompt...")
    agents_md = Path("AGENTS.md")
    if agents_md.exists():
        total_ingested += ingest_document(
            engine, agents_md,
            KnowledgeSource.TECHNICAL_SPEC,
            ["master_prompt", "governance"]
        )
    else:
        print("  ⚠ AGENTS.md not found")

    # 4. Owner preferences (hard-coded for now)
    print("\n4. Ingesting owner preferences...")
    owner_facts = [
        ("Chủ sở hữu QUAN AI BRAIN là Anh Quân — Quanpt1 (quanpt1@viettel.com.vn)", ["owner_identity", "governance"]),
        ("Workspace chính: E:/AI/QUAN AI BRAIN", ["workspace", "configuration"]),
        ("GPU: NVIDIA Quadro T1000 4GB VRAM", ["hardware", "configuration"]),
        ("Model chủ lực: zai-org/GLM-5.3-Flash qua NetMind Gateway", ["llm", "configuration"]),
        ("Pi 5 IP: 192.168.1.21, port 8768", ["hardware", "pi5"]),
        ("Voice profile: vi-VN-HoaiMyNeural (EdgeTTS)", ["voice", "configuration"]),
        ("Avatar Model A: tóc đen dài, dịu dàng, trang phục trắng bạc, ánh sáng cyan", ["avatar", "configuration"]),
    ]

    for fact, tags in owner_facts:
        record = engine.ingest(
            content=fact,
            source_type=KnowledgeSource.OWNER_FEEDBACK,
            source_ref="owner_statement_2026-10-25",
            source_version="v1",
            tags=tags,
        )
        print(f"  ✓ Ingested preference: {fact[:50]}... → {record.id}")
        total_ingested += 1

    # 5. Sprint 3-6 completion facts
    print("\n5. Ingesting Sprint 3-6 achievements...")
    sprint_facts = [
        ("Sprint 3: Knowledge ingestion pipeline với provenance, conflict detection, benchmark", ["sprint3", "achievement"]),
        ("Sprint 4: Self-Model Engine với SystemInventory 26 components, 100% healthy", ["sprint4", "achievement"]),
        ("Sprint 5: 5-Type Learning Engine (A:tri thức, B:kinh nghiệm, C:usage, D:sandbox, E:hệ thống)", ["sprint5", "achievement"]),
        ("Sprint 6: Self-Care Engine với health monitoring, auto-recovery levels 0-2", ["sprint6", "achievement"]),
        ("Test suite: 548 passed, 1 skipped, 0 failed — zero regressions", ["testing", "evidence"]),
    ]

    for fact, tags in sprint_facts:
        record = engine.ingest(
            content=fact,
            source_type=KnowledgeSource.TEST_EVIDENCE,
            source_ref="sprint_completion_2026-10-25",
            source_version="v1",
            tags=tags,
        )
        print(f"  ✓ Ingested achievement: {fact[:50]}... → {record.id}")
        total_ingested += 1

    print("\n" + "=" * 60)
    print(f"✅ Ingested {total_ingested} documents/knowledge items")
    print(f"📁 Database: data/brain.db")
    print("=" * 60)

    # List quarantined items
    quarantined = engine.list_quarantined(limit=10)
    if quarantined:
        print(f"\n⏳ {len(quarantined)} items awaiting approval:")
        for item in quarantined[:5]:
            print(f"  - {item['statement'][:80]}...")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())