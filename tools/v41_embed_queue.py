#!/usr/bin/env python3
"""V41.2: embed queue từ v41_reingest_queue.json → chroma (sqlite-wait loop).

Chờ ingestion chính nhả sqlite lock; embed bằng Ollama BGE-M3; upsert chroma.
Fail-honest: log từng kết quả; nếu chroma vẫn khóa → giữ queue để chạy lại.
"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

QUEUE = ROOT / "logs" / "v41_reingest_queue.json"


def main() -> int:
    from quan_ai_brain.cognition.embedding import BGEEmbeddingService
    import chromadb
    from chromadb.config import Settings

    if not QUEUE.exists():
        print("không có queue file")
        return 1
    docs = json.loads(QUEUE.read_text(encoding="utf-8"))
    svc = BGEEmbeddingService()

    # Mở chroma có retry — hnsw có thể đang compact bởi ingestion chính
    col = None
    for attempt in range(30):
        try:
            client = chromadb.PersistentClient(
                path=str(ROOT / "data" / "knowledge_db"),
                settings=Settings(anonymized_telemetry=False),
            )
            col = client.get_or_create_collection("knowledge_base")
            n = col.count()  # probe — nếu hnsw đang khóa sẽ raise ở đây
            print(f"chroma OK, count={n} (attempt {attempt + 1})")
            break
        except Exception as exc:
            print(f"chroma bận ({type(exc).__name__}), retry sau 30s... {exc!r}"[:120])
            time.sleep(30)
    if col is None:
        print("KHÔNG mở được chroma sau 15 phút — giữ queue, chạy lại sau")
        return 1

    total_added = 0
    total_skip = 0
    for d in docs:
        added = 0
        skipped = 0
        for chunk in d["chunks"]:
            content = chunk["content"].strip()
            if not content:
                skipped += 1
                continue
            vec = svc.embed_text(content)
            if not vec:
                skipped += 1
                continue
            meta = dict(chunk["metadata"])
            meta["chunk_id"] = chunk["id"]
            try:
                col.upsert(
                    ids=[chunk["id"]],
                    embeddings=[vec],
                    documents=[content],
                    metadatas=[meta],
                )
                added += 1
            except Exception as exc:
                print(f"  upsert lỗi {chunk['id']}: {exc!r}"[:120])
                skipped += 1
        total_added += added
        total_skip += skipped
        print(f"{d['filename']}: +{added}, skip {skipped}")

    print(f"\nTỔNG: +{total_added} chunks, skip {total_skip}")
    if total_added > 0:
        QUEUE.rename(QUEUE.with_suffix(".done.json"))
        print("queue đã xử lý xong → .done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
