"""V37.2 Long-Term Memory with Vector DB (ChromaDB).

Implements tiered memory architecture:
1. Short-term: Session memory (SQLite brain.db)
2. Long-term: Vector DB (ChromaDB) for semantic search
3. Verified knowledge: USER_PROVIDED with provenance

Features:
- Automatic embedding generation
- Semantic search with filters
- Memory tiering (short → long → verified)
- Incremental ingestion pipeline
- Retrieval with confidence scoring
"""
from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional

import chromadb
from chromadb.config import Settings

from quan_ai_brain.memory.models import MemoryType, VerificationStatus, LifecycleStatus
from quan_ai_brain.cognition.embedding import BGEEmbeddingService


@dataclass
class MemoryChunk:
    """A chunk of memory ready for vector storage."""
    id: str
    content: str
    memory_type: str
    source_ref: str
    verification_status: str
    tags: List[str]
    metadata: dict[str, Any]
    embedding: Optional[List[float]] = None
    
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_memory_record(cls, record: dict, chunk_size: int = 500) -> List['MemoryChunk']:
        """Split memory record into chunks for better retrieval."""
        content = record.get('content', '')
        chunks = []
        
        # Simple chunking by sentences (can be improved with NLP)
        sentences = content.split('. ')
        current_chunk = ""
        chunk_id = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            if len(current_chunk) + len(sentence) <= chunk_size:
                current_chunk += sentence + ". "
            else:
                # Save current chunk and start new one
                if current_chunk.strip():
                    chunks.append(cls(
                        id=f"{record['id']}_chunk_{chunk_id}",
                        content=current_chunk.strip(),
                        memory_type=record.get('memory_type', MemoryType.SEMANTIC.value),
                        source_ref=record.get('source_ref', ''),
                        verification_status=record.get('verification_status', VerificationStatus.UNVERIFIED.value),
                        tags=record.get('tags', []),
                        metadata={
                            'original_id': record['id'],
                            'chunk_id': chunk_id,
                            'created_at': record.get('created_at_utc', ''),
                            **record.get('metadata', {})
                        }
                    ))
                    chunk_id += 1
                current_chunk = sentence + ". "
        
        # Add last chunk
        if current_chunk.strip():
            chunks.append(cls(
                id=f"{record['id']}_chunk_{chunk_id}",
                content=current_chunk.strip(),
                memory_type=record.get('memory_type', MemoryType.SEMANTIC.value),
                source_ref=record.get('source_ref', ''),
                verification_status=record.get('verification_status', VerificationStatus.UNVERIFIED.value),
                tags=record.get('tags', []),
                metadata={
                    'original_id': record['id'],
                    'chunk_id': chunk_id,
                    'created_at': record.get('created_at_utc', ''),
                    **record.get('metadata', {})
                }
            ))
        
        return chunks


class LongTermMemoryStore:
    """ChromaDB-based long-term memory store with tiered architecture."""
    
    def __init__(
        self,
        db_path: str = "data/vector_db",
        embedding_service: Optional[BGEEmbeddingService] = None,
        collection_name: str = "quan_ai_brain_memory"
    ):
        self.db_path = Path(db_path)
        self.db_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize ChromaDB (persistent)
        self.client = chromadb.PersistentClient(
            path=str(self.db_path),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True  # For development/testing
            )
        )
        self.collection_name = collection_name
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"description": "QUAN AI BRAIN long-term memory"}
        )
        
        # Embedding service
        self.embedding_service = embedding_service
        self.embedding_dim = embedding_service.get_dimension() if embedding_service else 1024
        
        print(f"✅ Long-term memory store initialized: {self.collection.count()} chunks")
    
    def add_memory(self, memory_chunk: MemoryChunk) -> str:
        """Add a memory chunk to vector store."""
        # Generate embedding if not provided
        if memory_chunk.embedding is None and self.embedding_service:
            embeddings = self.embedding_service.embed([memory_chunk.content])
            memory_chunk.embedding = embeddings[0]
        
        if memory_chunk.embedding is None:
            raise ValueError("Cannot add memory without embedding")
        
        # Prepare metadata for ChromaDB
        metadata = {
            "id": memory_chunk.id,
            "content": memory_chunk.content,
            "memory_type": memory_chunk.memory_type,
            "source_ref": memory_chunk.source_ref,
            "verification_status": memory_chunk.verification_status,
            "tags": json.dumps(memory_chunk.tags),
            **memory_chunk.metadata
        }
        
        # Add to collection
        self.collection.add(
            ids=[memory_chunk.id],
            embeddings=[memory_chunk.embedding],
            metadatas=[metadata],
            documents=[memory_chunk.content]
        )
        
        return memory_chunk.id
    
    def add_memories_batch(self, chunks: List[MemoryChunk]) -> int:
        """Add multiple memory chunks in batch."""
        if not chunks:
            return 0
        
        if self.embedding_service:
            # Batch embed
            contents = [chunk.content for chunk in chunks]
            embeddings = self.embedding_service.embed(contents)
            
            for chunk, emb in zip(chunks, embeddings):
                chunk.embedding = emb
        
        # Prepare batch data
        ids = []
        embeddings = []
        metadatas = []
        documents = []
        
        for chunk in chunks:
            if chunk.embedding is None:
                continue
            
            ids.append(chunk.id)
            embeddings.append(chunk.embedding)
            
            metadata = {
                "id": chunk.id,
                "content": chunk.content,
                "memory_type": chunk.memory_type,
                "source_ref": chunk.source_ref,
                "verification_status": chunk.verification_status,
                "tags": json.dumps(chunk.tags),
                **chunk.metadata
            }
            metadatas.append(metadata)
            documents.append(chunk.content)
        
        if ids:
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=documents
            )
        
        return len(ids)
    
    def search(
        self,
        query: str,
        n_results: int = 10,
        filters: Optional[dict] = None,
        include: List[str] = ["documents", "metadatas", "distances"]
    ) -> dict:
        """Semantic search with optional filters."""
        # Generate query embedding
        if not self.embedding_service:
            raise ValueError("Embedding service required for search")
        
        query_embedding = self.embedding_service.embed([query])[0]
        
        # Build ChromaDB where clause
        where_clause = None
        if filters:
            where_clause = {}
            for key, value in filters.items():
                if key == "verification_status":
                    where_clause["verification_status"] = value
                elif key == "memory_type":
                    where_clause["memory_type"] = value
                elif key == "tags":
                    where_clause["tags"] = {"$contains": value}
                elif key == "source_ref":
                    where_clause["source_ref"] = value
        
        # Search
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where_clause,
            include=include
        )
        
        return results
    
    def search_by_verification(
        self,
        query: str,
        verification_status: str = VerificationStatus.VERIFIED.value,
        n_results: int = 5
    ) -> List[dict]:
        """Search only verified knowledge."""
        results = self.search(
            query=query,
            n_results=n_results,
            filters={"verification_status": verification_status}
        )
        
        return self._format_results(results)
    
    def search_user_provided(self, query: str, n_results: int = 5) -> List[dict]:
        """Search USER_PROVIDED knowledge specifically."""
        return self.search_by_verification(
            query=query,
            verification_status=VerificationStatus.USER_PROVIDED.value,
            n_results=n_results
        )
    
    def get_similar_chunks(self, chunk_id: str, n_results: int = 5) -> List[dict]:
        """Find chunks similar to a given chunk."""
        # Get the chunk first
        chunk_data = self.collection.get(ids=[chunk_id], include=["embeddings"])
        
        if not chunk_data["embeddings"]:
            return []
        
        # Search with same embedding
        results = self.collection.query(
            query_embeddings=chunk_data["embeddings"],
            n_results=n_results,
            where={"id": {"$ne": chunk_id}}  # Exclude self
        )
        
        return self._format_results(results)
    
    def _format_results(self, results: dict) -> List[dict]:
        """Format ChromaDB results into readable format."""
        formatted = []
        
        if not results["ids"] or not results["ids"][0]:
            return formatted
        
        for i, chunk_id in enumerate(results["ids"][0]):
            metadata = results["metadatas"][0][i] if results["metadatas"] else {}
            document = results["documents"][0][i] if results["documents"] else ""
            distance = results["distances"][0][i] if results["distances"] else None
            
            formatted.append({
                "id": chunk_id,
                "content": document,
                "memory_type": metadata.get("memory_type"),
                "source_ref": metadata.get("source_ref"),
                "verification_status": metadata.get("verification_status"),
                "tags": json.loads(metadata.get("tags", "[]")),
                "similarity": 1 - (distance / 2) if distance else 1.0,  # Convert distance to similarity
                "metadata": metadata
            })
        
        return formatted
    
    def get_stats(self) -> dict:
        """Get memory store statistics."""
        total_chunks = self.collection.count()

        # Count by verification status
        # (30/10/2026) FIX chroma 1.5.9: collection.get(where=...) KHÔNG trả
        # key 'count' (chỉ ids/embeddings/documents/metadatas) → mọi count
        # rơi vào except → 0. Đếm bằng len(ids).
        verification_counts = {}
        for status in VerificationStatus:
            try:
                res = self.collection.get(
                    where={"verification_status": status.value}
                )
                ids = res.get("ids") or []
                verification_counts[status.value] = len(ids) if not isinstance(ids, int) else ids
            except Exception:
                verification_counts[status.value] = 0

        # Count by memory type
        type_counts = {}
        for mtype in MemoryType:
            try:
                res = self.collection.get(
                    where={"memory_type": mtype.value}
                )
                ids = res.get("ids") or []
                type_counts[mtype.value] = len(ids) if not isinstance(ids, int) else ids
            except Exception:
                type_counts[mtype.value] = 0
        
        return {
            "total_chunks": total_chunks,
            "by_verification": verification_counts,
            "by_type": type_counts,
            "embedding_dim": self.embedding_dim,
            "db_path": str(self.db_path)
        }
    
    def delete_chunk(self, chunk_id: str) -> bool:
        """Delete a specific chunk."""
        try:
            self.collection.delete(ids=[chunk_id])
            return True
        except Exception as e:
            print(f"Error deleting chunk {chunk_id}: {e}")
            return False
    
    def reset(self):
        """Reset the entire memory store (for development/testing)."""
        # (30/10/2026) FIX chroma 1.5.9: client.reset() xóa CẢ database →
        # collection handle cũ trở thành NotFound (mọi thao tác sau crash).
        # Sau reset phải get_or_create lại collection.
        self.client.reset()
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"description": "QUAN AI BRAIN long-term memory"}
        )
        print("⚠️ Memory store reset")
    
    def export_to_json(self, output_path: str):
        """Export all memories to JSON file."""
        all_data = self.collection.get(include=["documents", "metadatas"])
        
        memories = []
        for i, chunk_id in enumerate(all_data["ids"]):
            metadata = all_data["metadatas"][i] if all_data["metadatas"] else {}
            document = all_data["documents"][i] if all_data["documents"] else ""
            
            memories.append({
                "id": chunk_id,
                "content": document,
                **metadata
            })
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(memories, f, ensure_ascii=False, indent=2)
        
        return len(memories)
    
    def import_from_json(self, input_path: str) -> int:
        """Import memories from JSON file."""
        with open(input_path, 'r', encoding='utf-8') as f:
            memories = json.load(f)
        
        chunks = []
        for mem in memories:
            chunk = MemoryChunk(
                id=mem["id"],
                content=mem["content"],
                memory_type=mem.get("memory_type", MemoryType.SEMANTIC.value),
                source_ref=mem.get("source_ref", ""),
                verification_status=mem.get("verification_status", VerificationStatus.UNVERIFIED.value),
                tags=mem.get("tags", []),
                metadata={k: v for k, v in mem.items() if k not in ["id", "content", "memory_type", "source_ref", "verification_status", "tags"]}
            )
            chunks.append(chunk)
        
        return self.add_memories_batch(chunks)


class MemoryTieringEngine:
    """Manages memory tiering: short-term → long-term → verified."""
    
    def __init__(
        self,
        long_term_store: LongTermMemoryStore,
        short_term_db_path: str = "data/brain.db"
    ):
        self.long_term = long_term_store
        self.short_term_db_path = short_term_db_path
    
    def tier_memory(
        self,
        memory_record: dict,
        target_tier: str = "long_term"
    ) -> str:
        """Move memory to appropriate tier."""
        if target_tier == "long_term":
            # Split into chunks and add to vector DB
            chunks = MemoryChunk.from_memory_record(memory_record)
            added = self.long_term.add_memories_batch(chunks)
            return f"Added {added} chunks to long-term memory"
        
        elif target_tier == "verified":
            # Add to long-term with VERIFIED status
            memory_record["verification_status"] = VerificationStatus.VERIFIED.value
            chunks = MemoryChunk.from_memory_record(memory_record)
            added = self.long_term.add_memories_batch(chunks)
            return f"Verified and added {added} chunks"
        
        elif target_tier == "user_provided":
            # Add with USER_PROVIDED status
            memory_record["verification_status"] = VerificationStatus.USER_PROVIDED.value
            chunks = MemoryChunk.from_memory_record(memory_record)
            added = self.long_term.add_memories_batch(chunks)
            return f"Added {added} USER_PROVIDED chunks"
        
        return "Unknown tier"
    
    def retrieve_with_tiering(
        self,
        query: str,
        require_verified: bool = False,
        n_results: int = 5
    ) -> List[dict]:
        """Retrieve memory with tier preference."""
        if require_verified:
            # Only search verified knowledge
            return self.long_term.search_by_verification(query, n_results=n_results)
        else:
            # Search all, but rank verified higher
            # (30/10/2026) FIX: search() trả dict chroma thô (ids/embeddings/
            # documents/metadatas/distances), KHÔNG phải list các record —
            # sort trên str gây AttributeError. Chuẩn hóa trước khi xếp hạng.
            raw = self.long_term.search(query, n_results=n_results * 2)
            ids = raw.get("ids") or [[]]
            metas = (raw.get("metadatas") or [[]])[0] if raw.get("metadatas") else []
            docs = (raw.get("documents") or [[]])[0] if raw.get("documents") else []
            dists = (raw.get("distances") or [[]])[0] if raw.get("distances") else []

            all_results = []
            for i, cid in enumerate(ids[0] if ids else []):
                meta = metas[i] if i < len(metas) and isinstance(metas[i], dict) else {}
                all_results.append({
                    "id": cid,
                    "content": docs[i] if i < len(docs) else "",
                    "similarity": 1.0 - float(dists[i]) if i < len(dists) else 0.0,
                    **meta,
                })

            # Sort by verification status (VERIFIED > USER_PROVIDED > others)
            status_priority = {
                VerificationStatus.VERIFIED.value: 3,
                VerificationStatus.USER_PROVIDED.value: 2,
                VerificationStatus.OBSERVED.value: 1,
                VerificationStatus.INFERRED.value: 0,
                VerificationStatus.UNVERIFIED.value: 0,
                VerificationStatus.CANDIDATE.value: -1
            }
            
            sorted_results = sorted(
                all_results,
                key=lambda x: (
                    status_priority.get(x.get("verification_status"), 0),
                    x.get("similarity", 0)
                ),
                reverse=True
            )
            
            return sorted_results[:n_results]
    
    def get_memory_lifecycle(self, memory_id: str) -> dict:
        """Get lifecycle info for a memory across tiers."""
        # Check long-term
        try:
            chunk_data = self.long_term.collection.get(ids=[memory_id])
            if chunk_data["ids"]:
                return {
                    "tier": "long_term",
                    "found": True,
                    "data": chunk_data
                }
        except:
            pass
        
        # Check short-term (SQLite)
        # TODO: Implement SQLite lookup
        
        return {"tier": "unknown", "found": False}


# Factory function
def create_memory_store(
    db_path: str = "data/vector_db",
    embedding_service: Optional[BGEEmbeddingService] = None
) -> LongTermMemoryStore:
    """Create and configure memory store."""
    return LongTermMemoryStore(db_path=db_path, embedding_service=embedding_service)