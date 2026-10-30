"""V38 Multi-Domain Knowledge Base Query Engine.

Provides semantic search with filtering by:
- Industry (engineering, ai, telecom, business, training)
- Category (technical, training, reference, procedure, data, code)
- Subcategory (electrical, machine_learning, nlp, etc.)
- Confidence score
- Date range

Features:
- Hybrid search (semantic + keyword)
- Filtered retrieval with metadata
- Result ranking by relevance and confidence
- Source attribution
- Context-aware answers
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

import chromadb
from chromadb.config import Settings

from quan_ai_brain.cognition.embedding import BGEEmbeddingService


@dataclass
class SearchResult:
    """A search result with metadata."""
    chunk_id: str
    content: str
    score: float
    filename: str
    filepath: str
    industry: str
    category: str
    subcategory: str
    file_type: str
    file_size: int
    page_number: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class KnowledgeQueryEngine:
    """Query engine for multi-domain knowledge base."""
    
    def __init__(self, db_path: Path = None):
        if db_path is None:
            # __file__ = src/quan_ai_brain/knowledge/knowledge_query.py
            # 4 parents: knowledge -> quan_ai_brain -> src -> project root
            db_path = Path(__file__).parent.parent.parent.parent / "data" / "knowledge_db"
        
        self.db_path = db_path
        self.db_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(
            path=str(self.db_path),
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Get or create collection
        # V40 fix: dùng cosine space — BGE-M3 vectors là cosine similarity;
        # mặc định L2 của ChromaDB làm công thức score = 1 - distance/2 sai hoàn toàn.
        self.collection = self.client.get_or_create_collection(
            name="knowledge_base",
            metadata={
                "description": "Multi-domain knowledge base",
                "hnsw:space": "cosine",
            }
        )
        
        # Initialize embedding service
        self.embedding_service = BGEEmbeddingService()
        
        print(f"✅ Knowledge Query Engine initialized")
        print(f"   Database: {self.db_path}")
        print(f"   Total documents: {self.collection.count()}")
    
    def search(
        self,
        query: str,
        industry: Optional[str] = None,
        category: Optional[str] = None,
        subcategory: Optional[str] = None,
        file_types: Optional[List[str]] = None,
        min_score: float = 0.5,
        top_k: int = 10
    ) -> List[SearchResult]:
        """Search knowledge base with filters."""
        
        # Generate embedding for query (BGEEmbeddingService API = embed_text)
        query_embedding = self.embedding_service.embed_text(query)
        if not query_embedding:
            return []
        
        # Build where clause for filtering
        where_clause = {}
        if industry:
            where_clause['industry'] = industry
        if category:
            where_clause['category'] = category
        if subcategory:
            where_clause['subcategory'] = subcategory
        if file_types:
            where_clause['file_type'] = {'$in': file_types}
        
        # Search
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k * 2,  # Get more to filter by score
            where=where_clause if where_clause else None,
            include=['documents', 'metadatas', 'distances']
        )
        
        # Process results
        search_results = []
        if results['documents'] and results['documents'][0]:
            for i, doc in enumerate(results['documents'][0]):
                if i >= len(results['distances'][0]):
                    break
                
                distance = results['distances'][0][i]
                metadata = results['metadatas'][0][i] if results['metadatas'] else {}
                
                # Convert distance to similarity score
                score = 1.0 - (distance / 2.0)  # Assuming cosine distance
                
                if score >= min_score:
                    search_results.append(SearchResult(
                        chunk_id=metadata.get('chunk_id', ''),
                        content=doc,
                        score=score,
                        filename=metadata.get('filename', ''),
                        filepath=metadata.get('filepath', ''),
                        industry=metadata.get('industry', 'unknown'),
                        category=metadata.get('category', 'unknown'),
                        subcategory=metadata.get('subcategory', 'unknown'),
                        file_type=metadata.get('file_type', ''),
                        file_size=metadata.get('file_size', 0)
                    ))
        
        # Sort by score and return top_k
        search_results.sort(key=lambda x: x.score, reverse=True)
        return search_results[:top_k]
    
    def search_by_keyword(
        self,
        keyword: str,
        industry: Optional[str] = None,
        category: Optional[str] = None,
        top_k: int = 10
    ) -> List[SearchResult]:
        """Keyword-based search with filters."""
        
        # Build where clause
        where_clause = {}
        if industry:
            where_clause['industry'] = industry
        if category:
            where_clause['category'] = category
        
        # Search for exact matches in content
        results = self.collection.get(
            where=where_clause if where_clause else None,
            include=['documents', 'metadatas']
        )
        
        search_results = []
        if results['documents']:
            for i, doc in enumerate(results['documents']):
                if keyword.lower() in doc.lower():
                    metadata = results['metadatas'][i]
                    search_results.append(SearchResult(
                        chunk_id=metadata.get('chunk_id', ''),
                        content=doc[:500] + "..." if len(doc) > 500 else doc,
                        score=0.8,  # Keyword match score
                        filename=metadata.get('filename', ''),
                        filepath=metadata.get('filepath', ''),
                        industry=metadata.get('industry', 'unknown'),
                        category=metadata.get('category', 'unknown'),
                        subcategory=metadata.get('subcategory', 'unknown'),
                        file_type=metadata.get('file_type', ''),
                        file_size=metadata.get('file_size', 0)
                    ))
        
        search_results.sort(key=lambda x: x.score, reverse=True)
        return search_results[:top_k]
    
    def ingest_documents(self, documents) -> Dict[str, int]:
        """Store parsed KnowledgeDocument chunks into ChromaDB.

        V40 fix: pipeline calls vector_store.ingest_documents() but this method
        was missing. Embeds each chunk via BGE-M3 (Ollama) and adds to the
        knowledge_base collection with full metadata. Skips chunks that fail
        to embed (fail-honest, no fake vectors).
        """
        added = 0
        skipped = 0
        for doc in documents:
            for chunk in doc.chunks:
                content = chunk.get("content", "").strip()
                if not content:
                    skipped += 1
                    continue
                try:
                    vector = self.embedding_service.embed_text(content)
                except Exception:
                    vector = []
                if not vector:
                    skipped += 1
                    continue

                meta = dict(chunk.get("metadata") or {})
                meta["chunk_id"] = chunk.get("id", f"{doc.id}_{chunk.get('chunk_id', 0)}")
                meta["chunk_seq"] = chunk.get("chunk_id", 0)
                meta["doc_id"] = doc.id
                meta["filename"] = doc.filename
                meta["filepath"] = doc.filepath
                meta["file_type"] = doc.file_type
                meta["file_size"] = doc.file_size
                meta["industry"] = doc.industry
                meta["category"] = doc.category
                meta["subcategory"] = doc.subcategory

                try:
                    self.collection.upsert(
                        ids=[meta["chunk_id"]],
                        embeddings=[vector],
                        documents=[content],
                        metadatas=[meta],
                    )
                    added += 1
                except Exception:
                    skipped += 1
        return {"added": added, "skipped": skipped}

    def get_document_info(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific document."""
        results = self.collection.get(
            where={'doc_id': doc_id},
            include=['metadatas']
        )
        
        if results['metadatas'] and results['metadatas'][0]:
            return results['metadatas'][0]
        return None
    
    def list_industries(self) -> Dict[str, int]:
        """List all industries with document counts."""
        all_metadata = self.collection.get(include=['metadatas'])
        
        industries = {}
        if all_metadata['metadatas']:
            for meta in all_metadata['metadatas']:
                ind = meta.get('industry', 'unknown')
                industries[ind] = industries.get(ind, 0) + 1
        
        return industries
    
    def list_categories(self) -> Dict[str, int]:
        """List all categories with document counts."""
        all_metadata = self.collection.get(include=['metadatas'])
        
        categories = {}
        if all_metadata['metadatas']:
            for meta in all_metadata['metadatas']:
                cat = meta.get('category', 'unknown')
                categories[cat] = categories.get(cat, 0) + 1
        
        return categories
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get knowledge base statistics."""
        total_chunks = self.collection.count()
        all_metadata = self.collection.get(include=['metadatas'])
        
        stats = {
            'total_chunks': total_chunks,
            'total_documents': 0,
            'industries': {},
            'categories': {},
            'subcategories': {},
            'file_types': {}
        }
        
        doc_ids = set()
        if all_metadata['metadatas']:
            for meta in all_metadata['metadatas']:
                doc_ids.add(meta.get('doc_id', ''))
                stats['total_documents'] += 1
                
                ind = meta.get('industry', 'unknown')
                stats['industries'][ind] = stats['industries'].get(ind, 0) + 1
                
                cat = meta.get('category', 'unknown')
                stats['categories'][cat] = stats['categories'].get(cat, 0) + 1
                
                subcat = meta.get('subcategory', 'unknown')
                stats['subcategories'][subcat] = stats['subcategories'].get(subcat, 0) + 1
                
                ftype = meta.get('file_type', 'unknown')
                stats['file_types'][ftype] = stats['file_types'].get(ftype, 0) + 1
        
        stats['total_documents'] = len(doc_ids)
        return stats
    
    def format_results(self, results: List[SearchResult], show_content: bool = True) -> str:
        """Format search results for display."""
        if not results:
            return "❌ Không tìm thấy kết quả phù hợp."
        
        output = []
        output.append(f"\n📊 **Tìm thấy {len(results)} kết quả:**\n")
        
        for i, result in enumerate(results, 1):
            file_size_mb = result.file_size / (1024 * 1024)
            
            output.append(f"**{i}. {result.filename}**")
            output.append(f"   📁 Industry: `{result.industry}` | Category: `{result.category}` | Subcategory: `{result.subcategory}`")
            output.append(f"   📄 Type: `{result.file_type}` | Size: `{file_size_mb:.2f} MB`")
            output.append(f"   ⭐ Relevance: `{result.score:.2%}`")
            
            if show_content:
                content_preview = result.content[:300] + "..." if len(result.content) > 300 else result.content
                output.append(f"   💬 **Nội dung:** {content_preview}")
            
            output.append("")
        
        return "\n".join(output)
    
    def answer_question(
        self,
        question: str,
        industry: Optional[str] = None,
        category: Optional[str] = None,
        top_k: int = 5
    ) -> str:
        """Answer a question using knowledge base."""
        
        # Search for relevant chunks
        results = self.search(
            query=question,
            industry=industry,
            category=category,
            top_k=top_k
        )
        
        if not results:
            return "❌ Em không tìm thấy thông tin liên quan trong kho dữ liệu. Anh có thể thử lại với từ khóa khác hoặc kiểm tra xem tài liệu đã được nạp vào hệ thống chưa."
        
        # Build answer from results
        context_parts = []
        for i, result in enumerate(results, 1):
            context_parts.append(f"[{i}] Từ file: {result.filename} ({result.industry}/{result.category})")
            context_parts.append(result.content)
            context_parts.append("")
        
        context = "\n---\n".join(context_parts)
        
        answer = f"""🔍 **Kết quả tìm kiếm từ kho dữ liệu:**

{self.format_results(results, show_content=False)}

📝 **Chi tiết nguồn tài liệu:**
{context}

💡 **Gợi ý:** Anh có thể lọc theo ngành (engineering, ai, telecom) hoặc hạng mục (technical, training, reference) để tìm chính xác hơn."""
        
        return answer