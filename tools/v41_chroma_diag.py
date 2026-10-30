#!/usr/bin/env python3
"""Tách bạch lỗi segfault chroma lúc nãy: chỉ chroma + query thô."""
import chromadb
from chromadb.config import Settings

c = chromadb.PersistentClient(path="data/knowledge_db", settings=Settings(anonymized_telemetry=False))
col = c.get_or_create_collection("knowledge_base")
print("count:", col.count())
r = col.query(query_texts=["RLS Row Level Security"], n_results=3, include=["documents", "metadatas", "distances"])
for i, d in enumerate(r["documents"][0]):
    md = r["metadatas"][0][i]
    print(round(1 - r["distances"][0][i], 3), "|", md.get("filename"), "|", d[:60])
