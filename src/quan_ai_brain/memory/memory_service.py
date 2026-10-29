"""Simple Memory Service wrapper for server."""

from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from quan_ai_brain.memory.vector_store import LongTermMemoryStore


class MemoryService:
    """Simple memory service for searching memories."""
    
    def __init__(self):
        self.vector_store = LongTermMemoryStore()
    
    def search_memories(self, query: str, top_k: int = 5) -> list:
        """Search for relevant memories."""
        try:
            results = self.vector_store.search(query, top_k=top_k)
            return [r.to_dict() for r in results]
        except Exception as e:
            return []
    
    def add_memory(self, content: str, memory_type: str = "semantic") -> dict:
        """Add new memory to vector store."""
        try:
            result = self.vector_store.add(content, memory_type=memory_type)
            return {"id": result.get("id")}
        except Exception as e:
            return {"error": str(e)}