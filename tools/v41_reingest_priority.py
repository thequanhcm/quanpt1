#!/usr/bin/env python3
"""V41 re-ingest các tài liệu trọng yếu với extractor mới (page + tables).

Mục tiêu: citation 'tài liệu nào, trang nào' hoạt động thật.
Files ưu tiên:
- So tay ky thuat thuat ngu nganh vien thong va CNTT 2026 (70 bảng, 97% nội dung)
- Train AI course AI Engineer Module 3 (RAG/Prompt/Transformer — 1,620 chunks)
Fail-honest: báo kết quả thật từng file, không bịa.
"""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from quan_ai_brain.knowledge.knowledge_ingestion import (  # noqa: E402
    ChunkingEngine,
    DomainClassifier,
    FormatParser,
)
from quan_ai_brain.knowledge.knowledge_query import KnowledgeQueryEngine  # noqa: E402


PRIORITY_FILES = [
    ROOT / "kho_tai_lieu" / "So tay ky thuat thuat ngu nganh vien thong va CNTT 2026_ban trinh ky.docx",
    ROOT / "kho_tai_lieu" / "Train AI course" / "AI Engineer Course" / "Module 3" / "Bai1_Lecture_Tong_Quan_Transformer.pdf",
    ROOT / "kho_tai_lieu" / "Train AI course" / "AI Engineer Course" / "Module 3" / "Bai3_Lecture_Prompt_Engineering.pdf",
    ROOT / "kho_tai_lieu" / "Train AI course" / "AI Engineer Course" / "Module 3" / "Bai4_Lecture_RAG_Pipeline_VectorDB.pdf",
    ROOT / "kho_tai_lieu" / "Train AI course" / "AI Engineer Course" / "Module 3" / "Bai5_Lecture_RAG_End2End.pdf",
    ROOT / "kho_tai_lieu" / "huong_dan_bao_mat.md",
    ROOT / "kho_tai_lieu" / "quy_trinh_bao_tri.md",
    ROOT / "kho_tai_lieu" / "so_tay_alarm.md",
]


def main() -> int:
    engine = KnowledgeQueryEngine(db_path=ROOT / "data" / "knowledge_db")
    parser = FormatParser()
    classifier = DomainClassifier()
    chunker = ChunkingEngine()
    import hashlib
    from datetime import datetime, timezone

    total_added = 0
    total_pages = 0
    for fp in PRIORITY_FILES:
        if not fp.exists():
            print(f"SKIP (không tồn tại): {fp.name}")
            continue
        t0 = time.time()
        content = parser.parse(fp)
        if "[PDF parse error" in content or "[DOCX parse error" in content:
            print(f"ERROR parse: {fp.name}: {content[:80]}")
            continue
        if not content.strip():
            print(f"EMPTY: {fp.name}")
            continue
        industry, category, subcategory = classifier.classify(content, fp)
        doc_id = hashlib.md5(str(fp).encode()).hexdigest()[:12]
        metadata = {
            "doc_id": doc_id,
            "filename": fp.name,
            "filepath": str(fp),
            "file_size": fp.stat().st_size,
            "file_type": fp.suffix,
            "industry": industry,
            "category": category,
            "subcategory": subcategory,
            "ingested_at": datetime.now(timezone.utc).isoformat(),
            "v41_reingest": "1",
        }
        chunks = chunker.chunk(content, metadata)
        for c in chunks:
            c["metadata"]["total_chunks"] = len(chunks)

        class _Doc:  # duck-type KnowledgeDocument đủ cho ingest_documents
            id = doc_id
            filename = fp.name
            filepath = str(fp)
            file_size = fp.stat().st_size
            file_type = fp.suffix
            industry = industry
            category = category
            subcategory = subcategory
            content = content[:5000]
            chunks = chunks
            metadata = metadata
            ingestion_timestamp = metadata["ingested_at"]

        stats = engine.ingest_documents([_Doc()])
        with_pages = sum(1 for c in chunks if c["metadata"].get("page_number") or c["metadata"].get("page_label"))
        total_added += stats["added"]
        total_pages += with_pages
        dt = time.time() - t0
        print(f"✅ {fp.name}: +{stats['added']} chunks ({stats['unchanged']} unchanged, "
              f"{stats['skipped']} skipped), {with_pages}/{len(chunks)} có page, {dt:.0f}s")

    print(f"\nTỔNG: +{total_added} chunks mới, {total_pages} chunks có page citation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
