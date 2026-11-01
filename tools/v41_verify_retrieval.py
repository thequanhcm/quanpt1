#!/usr/bin/env python3
"""V41 verify: truy xuất kho_tai_lieu có dẫn chứng (filename + page + score)."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from quan_ai_brain.knowledge.knowledge_query import KnowledgeQueryEngine  # noqa: E402


def main() -> int:
    eng = KnowledgeQueryEngine(db_path=Path("data/knowledge_db"))
    queries = [
        "RLS Row Level Security là gì",
        "cách giảm churn khách hàng viễn thông",
        "PM counter RAN 5G định nghĩa",
        "Transformer attention mechanism",
    ]
    for q in queries:
        t0 = time.time()
        try:
            res = eng.search(q, top_k=3)
        except Exception as exc:
            print(f"Q: {q}\n  ERROR: {exc}\n")
            continue
        dt = time.time() - t0
        print(f"Q: {q}  ({dt:.1f}s, {len(res)} results)")
        for r in res:
            print(f"  {r.score:.2f} | {r.filename} | page={r.page_number} | {r.content[:70]!r}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
