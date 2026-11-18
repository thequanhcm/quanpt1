# -*- coding: utf-8 -*-
"""SEMANTIC MEMORY ENGINE — ChromaDB default embedding (ONNX MiniLM, local).

Sprint 18/11 (TASK-SEMANTIC-MEMORY-M6, owner directive "thực hiện sprint kế
(a)"): triệt để hóa trí nhớ ngữ nghĩa KHÔNG cần Ollama/BGE-M3 (Ollama không
tồn tại trên máy QUANPT — đã audit 18/11). chromadb default embedding chạy
ONNX MiniLM local (đã probe: query tiếng Việt OK).

Thiết kế an toàn:
- Collection MỚI 'semantic_memory_v1' tại data/vector_db_semantic — KHÔNG
  đụng collection cũ 'quan_ai_brain_memory' (53 chunks legacy).
- Ingest đọc brain.db mode=ro (không ghi DB người dùng); idempotent theo
  original_id trong metadata (chạy lại = 0 duplicate).
- Fail-honest: lỗi DB/chroma → trả stats lỗi, không raise ra caller.
"""
from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Any

import chromadb

COLLECTION_NAME = "semantic_memory_v1"
MAX_DOC_CHARS = 1000
BATCH_SIZE = 200


class SemanticMemoryEngine:
    """Ingest + search ngữ nghĩa trên ChromaDB (ONNX MiniLM local)."""

    def __init__(self, persist_dir: Path | str, db_path: Path | str | None = None):
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = Path(db_path) if db_path else None
        self.client = chromadb.PersistentClient(path=str(self.persist_dir))
        self.collection = self.client.get_or_create_collection(COLLECTION_NAME)

    # ------------------------------------------------------------------ stats
    def stats(self) -> dict[str, Any]:
        try:
            return {
                "collection": COLLECTION_NAME,
                "persist_dir": str(self.persist_dir),
                "n_chunks": self.collection.count(),
                "db_path": str(self.db_path) if self.db_path else None,
                "embedding": "chromadb-default (ONNX MiniLM local, không cần Ollama)",
            }
        except Exception as exc:  # fail-honest
            return {"collection": COLLECTION_NAME, "error": str(exc)[:200]}

    # ------------------------------------------------------------------ ingest
    def _fetch_sources(self, limit_per_table: int = 4000) -> list[dict[str, str]]:
        """Đọc memories active + episodes chat_turn + lessons (mode=ro)."""
        docs: list[dict[str, str]] = []
        if not self.db_path or not self.db_path.exists():
            return docs
        conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True, timeout=5.0)
        try:
            cur = conn.cursor()
            # 1. memories active (kiến thức dài hạn)
            for mid, content, mtype, vstatus in cur.execute(
                "SELECT id, content, memory_type, verification_status "
                "FROM memories WHERE lifecycle_status='active' AND "
                "LENGTH(TRIM(content)) > 20 LIMIT ?",
                (limit_per_table,),
            ):
                docs.append({
                    "id": f"mem_{mid}",
                    "text": content.strip()[:MAX_DOC_CHARS],
                    "source": "memories",
                    "memory_type": str(mtype),
                    "verification": str(vstatus),
                })
            # 2. episodes chat_turn (hội thoại)
            for eid, summary, created in cur.execute(
                "SELECT id, summary, created_at_utc FROM episodes "
                "WHERE kind='chat_turn' AND LENGTH(TRIM(summary)) > 20 "
                "ORDER BY created_at_utc DESC LIMIT ?",
                (limit_per_table,),
            ):
                docs.append({
                    "id": f"ep_{eid}",
                    "text": summary.strip()[:MAX_DOC_CHARS],
                    "source": "episodes",
                    "created_at": str(created),
                    "memory_type": "chat_turn",
                    "verification": "EPHEMERAL",
                })
            # 3. experience_lesson (bài học)
            for eid, summary, created in cur.execute(
                "SELECT id, summary, created_at_utc FROM episodes "
                "WHERE kind='experience_lesson' AND LENGTH(TRIM(summary)) > 20 "
                "ORDER BY created_at_utc DESC LIMIT ?",
                (limit_per_table,),
            ):
                docs.append({
                    "id": f"ls_{eid}",
                    "text": summary.strip()[:MAX_DOC_CHARS],
                    "source": "lessons",
                    "created_at": str(created),
                    "memory_type": "experience_lesson",
                    "verification": "LESSON",
                })
        finally:
            conn.close()
        return docs

    def ingest(self, limit_per_table: int = 4000) -> dict[str, Any]:
        """Ingest idempotent: skip chunk đã có theo original_id metadata."""
        t0 = time.time()
        try:
            existing: set[str] = set()
            if self.collection.count():
                got = self.collection.get(include=["metadatas"])
                for md in got.get("metadatas") or []:
                    if md and md.get("original_id"):
                        existing.add(md["original_id"])
            docs = self._fetch_sources(limit_per_table)
            new_items = [d for d in docs if d["id"] not in existing]
            added = 0
            for i in range(0, len(new_items), BATCH_SIZE):
                batch = new_items[i:i + BATCH_SIZE]
                self.collection.add(
                    ids=[d["id"] for d in batch],
                    documents=[d["text"] for d in batch],
                    metadatas=[{
                        "original_id": d["id"],
                        "source": d.get("source", ""),
                        "memory_type": d.get("memory_type", ""),
                        "verification": d.get("verification", ""),
                    } for d in batch],
                )
                added += len(batch)
            return {
                "added": added,
                "skipped_existing": len(docs) - len(new_items),
                "total_in_collection": self.collection.count(),
                "seconds": round(time.time() - t0, 2),
            }
        except Exception as exc:  # fail-honest
            return {"error": str(exc)[:300], "added": 0}

    # ------------------------------------------------------------------ search
    def search(self, query: str, top_k: int = 5,
               min_distance: float = 1.2) -> list[dict[str, Any]]:
        """Search ngữ nghĩa; lọc kết quả quá xa (distance > min_distance)."""
        q = (query or "").strip()
        if not q or self.collection.count() == 0:
            return []
        try:
            res = self.collection.query(query_texts=[q], n_results=min(top_k, 10))
            hits: list[dict[str, Any]] = []
            ids = (res.get("ids") or [[]])[0]
            docs = (res.get("documents") or [[]])[0]
            dists = (res.get("distances") or [[]])[0]
            metas = (res.get("metadatas") or [[]])[0]
            for cid, doc, dist, md in zip(ids, docs, dists, metas):
                if dist is not None and dist > min_distance:
                    continue
                hits.append({
                    "id": cid,
                    "text": (doc or "")[:400],
                    "distance": round(dist, 4) if dist is not None else None,
                    "source": (md or {}).get("source", ""),
                    "verification": (md or {}).get("verification", ""),
                })
            return hits
        except Exception:  # fail-honest
            return []
