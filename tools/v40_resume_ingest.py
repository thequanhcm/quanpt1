#!/usr/bin/env python3
"""Resume V40 ingestion — tiếp tục từ chunk 9035/34897 (upsert = idempotent)."""
import sys
import time
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root))

import logging

# Giảm log noise từ parser
logging.basicConfig(level=logging.WARNING)

from quan_ai_brain.knowledge.knowledge_ingestion import KnowledgeIngestionPipeline
from quan_ai_brain.knowledge.knowledge_query import KnowledgeQueryEngine

source_path = Path("E:/AI/QUAN AI BRAIN/kho_tai_lieu")
query_engine = KnowledgeQueryEngine()
pipeline = KnowledgeIngestionPipeline(source_path, query_engine)

print(f"Resume ingestion from {source_path}")
print(f"Existing chunks: 9035")
t0 = time.time()
stats = pipeline.ingest(max_workers=2)
elapsed = time.time() - t0
print(f"\nDONE in {elapsed/60:.1f} min")
print(f"  Processed: {stats['processed']} files")
print(f"  Total chunks: {stats['total_chunks']}")
print(f"  Failed: {stats['failed']}")
