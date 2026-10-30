#!/usr/bin/env python3
"""Smoke test V40 ingestion trên 3 file đại diện (1 PDF, 1 MD, 1 DOCX-derived txt)."""
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "src"))

from quan_ai_brain.knowledge.knowledge_ingestion import KnowledgeIngestionPipeline
from quan_ai_brain.knowledge.knowledge_query import KnowledgeQueryEngine

kho = project_root / "kho_tai_lieu"
# 3 file đại diện nhỏ
samples = [
    kho / "huong_dan_bao_mat.md",
    kho / "quy_trinh_bao_tri.md",
    kho / "so_tay_alarm.md",
]
# Tạo thư mục sample tạm
sample_dir = project_root / "data" / "_v40_sample"
sample_dir.mkdir(parents=True, exist_ok=True)
for f in samples:
    if f.exists():
        (sample_dir / f.name).write_text(f.read_text(encoding="utf-8"), encoding="utf-8")

engine = KnowledgeQueryEngine()
print(f"Before: {engine.collection.count()} chunks")

pipeline = KnowledgeIngestionPipeline(sample_dir, engine)
stats = pipeline.ingest(max_workers=2)

print(f"\nAfter: {engine.collection.count()} chunks")

# Test search
results = engine.search("quy trình bảo trì hệ thống")
print(f"\nSearch 'quy trình bảo trì hệ thống': {len(results)} results")
for r in results[:2]:
    print(f"  - {r.filename} (score {r.score:.2f}): {r.content[:100]}...")

# Cleanup
import shutil
shutil.rmtree(sample_dir, ignore_errors=True)
