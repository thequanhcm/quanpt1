"""Simple Memory Service wrapper for server.

M3 (01/11/2026, ĐÃ DUYỆT): fix bug add_memory() gọi vector_store.add() — method
không tồn tại (chỉ có add_memory(MemoryChunk)) → mọi lệnh add trả error im lặng.
Giữ nguyên signature cũ để server.py không phải đổi.
"""

from pathlib import Path
import sys
import uuid

# Add project root to path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from quan_ai_brain.memory.vector_store import LongTermMemoryStore, MemoryChunk


class MemoryService:
    """Simple memory service for searching memories."""

    def __init__(self):
        self.vector_store = LongTermMemoryStore()

    def search_memories(self, query: str, top_k: int = 5) -> list:
        """Search for relevant memories."""
        try:
            results = self.vector_store.search(query, n_results=top_k)
            return [r.to_dict() if hasattr(r, "to_dict") else r for r in results]
        except Exception:
            return []

    def add_memory(self, content: str, memory_type: str = "semantic") -> dict:
        """Add new memory to vector store (M3 fix: dùng add_memory chuẩn)."""
        try:
            chunk = MemoryChunk(
                id=str(uuid.uuid4()),
                content=content,
                memory_type=memory_type,
                source_ref="memory_service",
                verification_status="UNVERIFIED",
                tags=[],
                metadata={},
            )
            chunk_id = self.vector_store.add_memory(chunk)
            return {"id": chunk_id}
        except Exception as e:
            return {"error": str(e)}
