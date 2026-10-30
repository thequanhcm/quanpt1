# V38 Multi-Domain Knowledge Base Architecture

## Overview

V38 implements a comprehensive multi-domain knowledge base system that enables TONY assistant to:
- **Read and understand** documents from multiple industries
- **Auto-categorize** by domain, category, and subcategory
- **Semantic search** with filtering capabilities
- **Answer questions** with source attribution
- **Support multiple formats**: PDF, DOCX, XLSX, TXT, MD, IPYNB, CSV, JSON, HTML

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    KNOWLEDGE BASE SYSTEM                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   File       │    │   Format     │    │   Domain     │  │
│  │   Scanner    │───▶│   Parser     │───▶│   Classifier │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│         │                   │                   │            │
│         ▼                   ▼                   ▼            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Chunking Engine                          │  │
│  │  - Split into semantic chunks (1000 chars)           │  │
│  │  - Overlap for context preservation                  │  │
│  │  - Metadata enrichment                               │  │
│  └──────────────────────────────────────────────────────┘  │
│                           │                                 │
│                           ▼                                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           Embedding Generator (BGE-M3)                │  │
│  │  - 1024-dimensional vectors                           │  │
│  │  - Vietnamese language optimized                      │  │
│  └──────────────────────────────────────────────────────┘  │
│                           │                                 │
│                           ▼                                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Vector Database (ChromaDB)               │  │
│  │  - Indexed by embeddings                              │  │
│  │  - Filterable metadata (industry, category, etc.)    │  │
│  │  - Efficient similarity search                       │  │
│  └──────────────────────────────────────────────────────┘  │
│                           │                                 │
│                           ▼                                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Query Engine & API                       │  │
│  │  - Semantic search with filters                       │  │
│  │  - Keyword search                                     │  │
│  │  - Question answering                                 │  │
│  │  - Source attribution                                 │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Industry Classification

### Supported Industries

1. **Engineering** (`engineering`)
   - Electrical systems (co_dien, cơ điện)
   - Equipment maintenance (bảo trì)
   - Alarm systems
   - Schematics and diagrams

2. **Artificial Intelligence** (`ai`)
   - Machine learning
   - Deep learning
   - NLP
   - Computer vision
   - Transformers
   - LLMs

3. **Telecommunications** (`telecom`)
   - Viettel infrastructure
   - Network systems (LTE, 5G, 4G)
   - Base stations
   - Subscriber data

4. **Business** (`business`)
   - Business processes
   - Contracts
   - Reports and analysis
   - Procedures

5. **Training** (`training`)
   - Course materials
   - Lectures
   - Labs
   - Exercises

## Category Classification

### Supported Categories

1. **Technical** (`technical`)
   - Technical specifications
   - Standards
   - Engineering docs

2. **Training** (`training`)
   - Lecture materials
   - Lab exercises
   - Course content

3. **Reference** (`reference`)
   - Handbooks
   - Reference materials
   - Documentation

4. **Procedure** (`procedure`)
   - SOPs
   - Workflows
   - Processes

5. **Data** (`data`)
   - Datasets
   - CSV/Excel files
   - Database exports

6. **Code** (`code`)
   - Source code
   - Scripts
   - Jupyter notebooks

## File Format Support

| Format | Extension | Parser | Status |
|--------|-----------|--------|--------|
| PDF | `.pdf` | PyPDF | ✅ |
| Word | `.docx` | python-docx | ✅ |
| Excel | `.xlsx`, `.xls` | pandas | ✅ |
| Text | `.txt` | Built-in | ✅ |
| Markdown | `.md` | Built-in | ✅ |
| CSV | `.csv` | pandas | ✅ |
| Jupyter | `.ipynb` | nbformat | ✅ |
| JSON | `.json` | Built-in | ✅ |
| HTML | `.html`, `.htm` | Built-in | ✅ |

## Metadata Schema

Each document chunk stores:

```json
{
  "doc_id": "unique_document_id",
  "chunk_id": "doc_id_chunk_0",
  "filename": "document.pdf",
  "filepath": "E:/AI/QUAN AI BRAIN/kho_tai_lieu/...",
  "file_size": 1024000,
  "file_type": ".pdf",
  "industry": "engineering",
  "category": "technical",
  "subcategory": "electrical",
  "ingested_at": "2026-10-29T14:30:00Z",
  "total_chunks": 15
}
```

## API Endpoints

### 1. Ingest Knowledge Base

```http
POST /api/knowledge/ingest
Content-Type: application/json

{
  "source": "E:/AI/QUAN AI BRAIN/kho_tai_lieu",
  "workers": 4
}
```

**Response:**
```json
{
  "success": true,
  "message": "Ingestion complete",
  "stats": {
    "total_files": 100,
    "processed": 95,
    "failed": 5,
    "total_chunks": 1500
  }
}
```

### 2. Search with Filters

```http
GET /api/knowledge/search?q=kỹ+thuật+điện&industry=engineering&category=technical&top_k=10
```

**Response:**
```json
{
  "success": true,
  "query": "kỹ thuật điện",
  "filters": {
    "industry": "engineering",
    "category": "technical"
  },
  "results": [
    {
      "chunk_id": "abc123_chunk_0",
      "content": "Nội dung chunk...",
      "score": 0.92,
      "filename": "technical_spec.pdf",
      "industry": "engineering",
      "category": "technical",
      "subcategory": "electrical",
      "file_type": ".pdf",
      "file_size": 1024000
    }
  ],
  "count": 10
}
```

### 3. Answer Question

```http
GET /api/knowledge/question?question=Cách+bảo+trì+thiết+bị+điện?&industry=engineering
```

**Response:**
```json
{
  "success": true,
  "question": "Cách bảo trì thiết bị điện?",
  "answer": "🔍 Kết quả tìm kiếm từ kho dữ liệu:\n\n[1] Từ file: maintenance_guide.pdf (engineering/technical)\n...\n\n💡 Gợi ý: Anh có thể lọc theo ngành..."
}
```

### 4. Get Statistics

```http
GET /api/knowledge/stats
```

**Response:**
```json
{
  "success": true,
  "stats": {
    "total_chunks": 1500,
    "total_documents": 95,
    "industries": {
      "engineering": 45,
      "ai": 30,
      "training": 20
    },
    "categories": {
      "technical": 40,
      "training": 35,
      "reference": 20
    }
  }
}
```

## Usage Examples

### Command Line Ingestion

```bash
# Ingest all files
python tools/ingest_knowledge_base.py --source "E:/AI/QUAN AI BRAIN/kho_tai_lieu"

# Ingest with specific industry filter
python tools/ingest_knowledge_base.py --source "E:/AI/QUAN AI BRAIN/kho_tai_lieu" --industry engineering

# Show statistics
python tools/ingest_knowledge_base.py --status

# Use 8 parallel workers
python tools/ingest_knowledge_base.py --workers 8
```

### Python API

```python
from quan_ai_brain.knowledge.knowledge_query import KnowledgeQueryEngine

# Initialize
engine = KnowledgeQueryEngine()

# Search with filters
results = engine.search(
    query="bảo trì thiết bị điện",
    industry="engineering",
    category="technical",
    top_k=10
)

# Answer question
answer = engine.answer_question(
    question="Cách bảo trì alarm system?",
    industry="engineering",
    top_k=5
)

# Get statistics
stats = engine.get_statistics()
print(f"Total chunks: {stats['total_chunks']}")
```

## Performance

- **Ingestion Speed**: ~50-100 files/minute (depending on file size and format)
- **Search Latency**: <200ms for semantic search with filters
- **Chunk Size**: 1000 characters with 200 character overlap
- **Embedding Dimension**: 1024 (BGE-M3)
- **Database**: ChromaDB (persistent, local)

## Scalability

- **Parallel Processing**: Multi-threaded ingestion (configurable workers)
- **Incremental Updates**: Only process new/modified files
- **Memory Efficient**: Stream processing for large files
- **Index Optimization**: ChromaDB HNSW index for fast search

## Future Enhancements

1. **OCR Support**: Extract text from scanned PDFs and images
2. **Auto-Tagging**: ML-based automatic tagging
3. **Cross-Reference**: Link related documents
4. **Version Tracking**: Track document versions
5. **Access Control**: Role-based access to sensitive docs
6. **Real-time Updates**: Watch directory for changes
7. **Multi-language**: Support English, Vietnamese, Chinese

## Integration with TONY

TONY assistant can now:
1. **Read** all documents in `kho_tai_lieu/`
2. **Understand** content through semantic embeddings
3. **Filter** by industry, category, subcategory
4. **Answer** questions with source attribution
5. **Explain** complex topics using multiple sources
6. **Cross-reference** information across documents

## Example Workflow

```
User: "TONY ơi, cách bảo trì thiết bị điện trong tổng trạm?"

TONY:
1. Search knowledge base:
   - Query: "bảo trì thiết bị điện tổng trạm"
   - Filter: industry=engineering, category=technical
   - Top 5 results

2. Retrieve relevant chunks:
   - From: "huong_dan_bao_tri.pdf"
   - From: "so_tay_alarm.pdf"
   - From: "quy_trinh_bao_tri.md"

3. Synthesize answer:
   "Dựa trên tài liệu kỹ thuật, quy trình bảo trì thiết bị điện gồm:
   
   1. Kiểm tra nguồn điện chính...
   2. Đo đạc các thông số...
   3. Vệ sinh thiết bị...
   
   Nguồn: huong_dan_bao_tri.pdf (trang 15), so_tay_alarm.pdf"
```

## Testing

```bash
# Run tests
pytest tests/test_v38_knowledge_base.py -v

# Test specific module
pytest tests/test_v38_knowledge_base.py::TestDomainClassifier -v
```

## Dependencies

Add to `pyproject.toml`:

```toml
[project]
dependencies = [
    # Existing dependencies
    "pypdf>=3.0.0",        # PDF parsing
    "python-docx>=0.8.11", # DOCX parsing
    "pandas>=1.5.0",       # Excel/CSV parsing
    "nbformat>=5.0.0",     # Jupyter notebook parsing
    "chromadb>=0.4.0",     # Vector database
    "sentence-transformers>=2.2.0"  # Embeddings
]
```

## Security

- **File Size Limit**: 50MB per file
- **Path Traversal Protection**: Validate file paths
- **No Code Execution**: Safe parsing only
- **Read-Only**: No modification of source files
- **Temporary Files**: Auto-cleanup after processing

## Conclusion

V38 Knowledge Base provides a robust, scalable solution for multi-domain document understanding, enabling TONY to:
- ✅ Read and understand documents from multiple industries
- ✅ Auto-categorize by domain and category
- ✅ Search semantically with filters
- ✅ Answer questions with source attribution
- ✅ Cross-reference information across documents
- ✅ Support multiple file formats

This forms the foundation for advanced RAG (Retrieval-Augmented Generation) capabilities in future versions.