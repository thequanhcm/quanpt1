#!/usr/bin/env python3
"""V40: Xóa sample test chunks khỏi knowledge_db trước khi ingest toàn bộ."""
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "src"))

import chromadb
from chromadb.config import Settings

client = chromadb.PersistentClient(
    path=str(project_root / "data" / "knowledge_db"),
    settings=Settings(anonymized_telemetry=False),
)
col = client.get_collection("knowledge_base")
before = col.count()
# Xóa 3 chunk sample (huong_dan_bao_mat, quy_trinh_bao_tri, so_tay_alarm)
col.delete(where={"filename": {"$in": ["huong_dan_bao_mat.md", "quy_trinh_bao_tri.md", "so_tay_alarm.md"]}})
after = col.count()
print(f"Deleted sample chunks: {before} -> {after}")
