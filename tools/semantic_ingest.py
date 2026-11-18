# -*- coding: utf-8 -*-
"""CLI ingest semantic memory (chạy 1 lần + idempotent).

Sprint 18/11 TASK-SEMANTIC-MEMORY-M6 — đọc brain.db mode=ro, ghi vào
data/vector_db_semantic collection semantic_memory_v1. Chạy lại = 0 duplicate.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE / "src"))

from quan_ai_brain.cognition.semantic_memory import SemanticMemoryEngine


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest semantic memory (idempotent)")
    parser.add_argument("--limit", type=int, default=4000,
                        help="Số dòng tối đa mỗi bảng nguồn")
    parser.add_argument("--stats-only", action="store_true",
                        help="Chỉ in stats, không ingest")
    args = parser.parse_args()

    engine = SemanticMemoryEngine(
        WORKSPACE / "data" / "vector_db_semantic",
        WORKSPACE / "data" / "brain.db",
    )
    if args.stats_only:
        print(json.dumps(engine.stats(), ensure_ascii=False, indent=2))
        return 0

    result = engine.ingest(limit_per_table=args.limit)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if "error" not in result else 1


if __name__ == "__main__":
    raise SystemExit(main())
