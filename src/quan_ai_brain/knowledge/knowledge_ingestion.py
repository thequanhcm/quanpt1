"""V38 Multi-Domain Knowledge Base Ingestion Pipeline.

This module implements a comprehensive knowledge ingestion system that:
1. Supports multiple file formats (PDF, DOCX, XLSX, TXT, MD, IPYNB, CSV)
2. Automatically categorizes by industry/domain
3. Extracts metadata and tags
4. Creates semantic embeddings for retrieval
5. Enables filtered search by category, industry, confidence

Architecture:
- File Scanner: Recursively scan kho_tai_lieu/
- Format Parser: Extract text from different file types
- Content Analyzer: Auto-categorize by domain/industry
- Chunking Engine: Split into semantic chunks
- Embedding Generator: Create vector embeddings
- Vector Store: Store in ChromaDB with metadata filters
- Query Engine: Search with filters (industry, category, confidence)

Usage:
    python tools/ingest_knowledge_base.py --source "E:/AI/QUAN AI BRAIN/kho_tai_lieu"
"""

from __future__ import annotations

import json
import os
import re
import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

# Third-party imports
try:
    from pypdf import PdfReader
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

try:
    from docx import Document
    DOCX_SUPPORT = True
except ImportError:
    DOCX_SUPPORT = False

try:
    import pandas as pd
    PANDAS_SUPPORT = True
except ImportError:
    PANDAS_SUPPORT = False

try:
    import nbformat
    NBFORMAT_SUPPORT = True
except ImportError:
    NBFORMAT_SUPPORT = False


@dataclass
class KnowledgeDocument:
    """Represents a parsed document with metadata."""
    id: str
    filename: str
    filepath: str
    file_size: int
    file_type: str
    industry: str  # e.g., "engineering", "ai", "telecom"
    category: str  # e.g., "technical", "training", "reference"
    subcategory: str  # e.g., "electrical", "machine_learning", "protocols"
    content: str
    chunks: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    ingestion_timestamp: str
    confidence_score: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class FileScanner:
    """Recursively scan directory for supported files."""
    
    SUPPORTED_EXTENSIONS = {
        '.pdf', '.docx', '.xlsx', '.xls', '.txt', '.md', 
        '.csv', '.ipynb', '.json', '.xml', '.html', '.htm'
    }
    
    def __init__(self, root_path: Path):
        self.root_path = root_path
    
    def scan(self) -> List[Path]:
        """Scan all supported files recursively."""
        files = []
        for ext in self.SUPPORTED_EXTENSIONS:
            files.extend(self.root_path.rglob(f"*{ext}"))
            files.extend(self.root_path.rglob(f"*{ext.upper()}"))
        
        # Filter out large files (>50MB) and temporary files
        valid_files = []
        for f in files:
            if f.is_file() and f.stat().st_size < 50 * 1024 * 1024:
                if not f.name.startswith('~') and not f.suffix == '.bak':
                    valid_files.append(f)
        
        return sorted(valid_files)


class FormatParser:
    """Extract text from different file formats."""
    
    def __init__(self):
        self.supported = {
            '.pdf': self._parse_pdf,
            '.docx': self._parse_docx,
            '.xlsx': self._parse_xlsx,
            '.xls': self._parse_xlsx,
            '.txt': self._parse_text,
            '.md': self._parse_text,
            '.csv': self._parse_csv,
            '.ipynb': self._parse_notebook,
            '.json': self._parse_json,
            '.html': self._parse_html,
            '.htm': self._parse_html,
        }
    
    def parse(self, filepath: Path) -> str:
        """Parse file and extract text content."""
        ext = filepath.suffix.lower()
        
        if ext not in self.supported:
            raise ValueError(f"Unsupported file type: {ext}")
        
        parser = self.supported[ext]
        return parser(filepath)
    
    def _parse_pdf(self, filepath: Path) -> str:
        if not PDF_SUPPORT:
            return "[PDF parsing not available - install pypdf]"
        
        try:
            reader = PdfReader(str(filepath))
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""
            return text
        except Exception as e:
            return f"[PDF parse error: {e}]"
    
    def _parse_docx(self, filepath: Path) -> str:
        if not DOCX_SUPPORT:
            return "[DOCX parsing not available - install python-docx]"
        
        try:
            doc = Document(str(filepath))
            return "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
        except Exception as e:
            return f"[DOCX parse error: {e}]"
    
    def _parse_xlsx(self, filepath: Path) -> str:
        if not PANDAS_SUPPORT:
            return "[Excel parsing not available - install pandas/openpyxl]"
        
        try:
            xls = pd.read_excel(str(filepath), sheet_name=None)
            text_parts = []
            for sheet_name, df in xls.items():
                text_parts.append(f"=== Sheet: {sheet_name} ===")
                text_parts.append(df.to_string())
            return "\n\n".join(text_parts)
        except Exception as e:
            return f"[Excel parse error: {e}]"
    
    def _parse_text(self, filepath: Path) -> str:
        try:
            return filepath.read_text(encoding='utf-8', errors='replace')
        except Exception as e:
            return f"[Text parse error: {e}]"
    
    def _parse_csv(self, filepath: Path) -> str:
        if not PANDAS_SUPPORT:
            return "[CSV parsing not available - install pandas]"
        
        try:
            df = pd.read_csv(str(filepath))
            return df.to_string()
        except Exception as e:
            return f"[CSV parse error: {e}]"
    
    def _parse_notebook(self, filepath: Path) -> str:
        if not NBFORMAT_SUPPORT:
            return "[Notebook parsing not available - install nbformat]"
        
        try:
            nb = nbformat.read(str(filepath), as_version=4)
            text_parts = []
            for cell in nb.cells:
                if cell.cell_type == 'markdown':
                    text_parts.append(cell.source)
                elif cell.cell_type == 'code':
                    text_parts.append(f"# Code:\n{cell.source}")
            return "\n\n".join(text_parts)
        except Exception as e:
            return f"[Notebook parse error: {e}]"
    
    def _parse_json(self, filepath: Path) -> str:
        try:
            data = json.loads(filepath.read_text(encoding='utf-8'))
            return json.dumps(data, indent=2, ensure_ascii=False)
        except Exception as e:
            return f"[JSON parse error: {e}]"
    
    def _parse_html(self, filepath: Path) -> str:
        try:
            content = filepath.read_text(encoding='utf-8', errors='replace')
            # Simple HTML tag removal
            text = re.sub(r'<[^>]+>', ' ', content)
            return re.sub(r'\s+', ' ', text).strip()
        except Exception as e:
            return f"[HTML parse error: {e}]"


class DomainClassifier:
    """Auto-categorize documents by industry and domain."""
    
    INDUSTRY_KEYWORDS = {
        'engineering': [
            'kỹ thuật', 'electrical', 'cơ điện', 'co dien', 'điện', 
            'power', 'tram', 'tổng trạm', 'thiết bị', 'equipment',
            'bảo trì', 'maintenance', 'alarm', 'sơ đồ', 'schematic'
        ],
        'ai': [
            'ai', 'machine learning', 'deep learning', 'neural', 'transformer',
            'llm', 'nlp', 'computer vision', 'embedding', 'rag', 'fine-tuning',
            'python', 'numpy', 'pandas', 'tensorflow', 'pytorch'
        ],
        'telecom': [
            'viettel', 'telecom', 'mạng', 'network', 'lte', '5g', '4g',
            'base station', 'trạm gốc', 'subscriber', 'dữ liệu di động'
        ],
        'business': [
            'kinh doanh', 'business', 'quy trình', 'procedure', 'hợp đồng',
            'contract', 'báo cáo', 'report', 'phân tích', 'analysis'
        ],
        'training': [
            'đào tạo', 'training', 'khóa học', 'course', 'module',
            'bài giảng', 'lecture', 'lab', 'thực hành'
        ]
    }
    
    CATEGORY_KEYWORDS = {
        'technical': ['technical', 'kỹ thuật', 'spec', 'tiêu chuẩn', 'standard'],
        'training': ['training', 'đào tạo', 'bài giảng', 'lecture', 'lab'],
        'reference': ['reference', 'tài liệu tham khảo', 'handbook', 'cẩm nang'],
        'procedure': ['procedure', 'quy trình', 'workflow', 'sop'],
        'data': ['data', 'dữ liệu', 'dataset', 'csv', 'excel', 'database'],
        'code': ['code', 'source', 'script', 'python', 'jupyter', 'ipynb']
    }
    
    def classify(self, content: str, filepath: Path) -> Tuple[str, str, str]:
        """Classify document into industry, category, subcategory."""
        text_lower = content.lower() + filepath.name.lower()
        
        # Classify industry
        industry = 'general'
        industry_score = 0
        for ind, keywords in self.INDUSTRY_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > industry_score:
                industry_score = score
                industry = ind
        
        # Classify category
        category = 'general'
        category_score = 0
        for cat, keywords in self.CATEGORY_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > category_score:
                category_score = score
                category = cat
        
        # Classify subcategory based on path and content
        subcategory = self._extract_subcategory(filepath, text_lower)
        
        return industry, category, subcategory
    
    def _extract_subcategory(self, filepath: Path, text: str) -> str:
        """Extract subcategory from path or content."""
        path_str = str(filepath).lower()
        
        # Check path segments
        if 'co dien' in path_str or 'cơ điện' in path_str:
            return 'electrical'
        elif 'machine learning' in path_str or 'ml' in path_str:
            return 'machine_learning'
        elif 'nlp' in path_str:
            return 'nlp'
        elif 'computer vision' in path_str or 'cv' in path_str:
            return 'computer_vision'
        elif 'alarm' in path_str:
            return 'alarm_systems'
        elif 'bảo trì' in path_str or 'maintenance' in path_str:
            return 'maintenance'
        elif 'module' in path_str:
            return 'course_module'
        elif 'lab' in path_str:
            return 'laboratory'
        elif 'slide' in path_str or 'lecture' in path_str:
            return 'lecture_materials'
        else:
            return 'general'


class ChunkingEngine:
    """Split documents into semantic chunks."""
    
    def __init__(self, chunk_size: int = 1000, overlap: int = 200):
        self.chunk_size = chunk_size
        self.overlap = overlap
    
    def chunk(self, content: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Split content into overlapping chunks."""
        chunks = []
        
        # Split by paragraphs first
        paragraphs = re.split(r'\n\s*\n', content)
        
        current_chunk = ""
        chunk_id = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            if len(current_chunk) + len(para) <= self.chunk_size:
                current_chunk += para + "\n\n"
            else:
                # Save current chunk
                if current_chunk.strip():
                    chunks.append(self._create_chunk(
                        current_chunk.strip(), chunk_id, metadata
                    ))
                    chunk_id += 1
                
                # Start new chunk with overlap
                if len(para) > self.chunk_size:
                    # Split long paragraph
                    words = para.split()
                    current_chunk = ""
                    for word in words:
                        if len(current_chunk) + len(word) <= self.overlap:
                            current_chunk += word + " "
                        else:
                            break
                    current_chunk += " ".join(words[len(current_chunk.split()):])
                else:
                    current_chunk = para + "\n\n"
        
        # Add last chunk
        if current_chunk.strip():
            chunks.append(self._create_chunk(
                current_chunk.strip(), chunk_id, metadata
            ))
        
        return chunks
    
    def _create_chunk(self, content: str, chunk_id: int, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Create a chunk with metadata."""
        return {
            'id': f"{metadata['doc_id']}_chunk_{chunk_id}",
            'content': content,
            'chunk_id': chunk_id,
            'total_chunks': 0,  # Will be updated later
            'metadata': metadata
        }


class KnowledgeIngestionPipeline:
    """Main pipeline for ingesting knowledge base."""
    
    def __init__(self, source_path: Path, vector_store):
        self.source_path = source_path
        self.vector_store = vector_store
        self.parser = FormatParser()
        self.classifier = DomainClassifier()
        self.chunker = ChunkingEngine()
        self.scanner = FileScanner(source_path)
        
        self.stats = {
            'total_files': 0,
            'processed': 0,
            'failed': 0,
            'total_chunks': 0,
            'industries': {},
            'categories': {}
        }
    
    def ingest(self, max_workers: int = 4) -> Dict[str, Any]:
        """Ingest all documents from source path."""
        print("\n" + "="*70)
        print("📚 KNOWLEDGE BASE INGESTION PIPELINE")
        print("="*70)
        print(f"Source: {self.source_path}")
        print(f"Max workers: {max_workers}")
        print("="*70 + "\n")
        
        # Scan files
        files = self.scanner.scan()
        self.stats['total_files'] = len(files)
        print(f"📂 Found {len(files)} files to process\n")
        
        # Process files
        documents = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_file = {
                executor.submit(self._process_file, f): f for f in files
            }
            
            for future in as_completed(future_to_file):
                filepath = future_to_file[future]
                try:
                    doc = future.result()
                    if doc:
                        documents.append(doc)
                        self.stats['processed'] += 1
                        print(f"✅ {filepath.name} ({len(doc.chunks)} chunks)")
                    else:
                        self.stats['failed'] += 1
                        print(f"❌ {filepath.name} (skipped)")
                except Exception as e:
                    self.stats['failed'] += 1
                    print(f"❌ {filepath.name} (error: {e})")
        
        # Update chunk counts
        for doc in documents:
            for chunk in doc.chunks:
                chunk['metadata']['total_chunks'] = len(doc.chunks)
            self.stats['total_chunks'] += len(doc.chunks)
        
        # Store in vector DB
        print(f"\n💾 Storing {self.stats['total_chunks']} chunks in vector DB...")
        self.vector_store.ingest_documents(documents)
        
        # Print summary
        self._print_summary()
        
        return self.stats
    
    def _process_file(self, filepath: Path) -> Optional[KnowledgeDocument]:
        """Process a single file."""
        try:
            # Parse content
            content = self.parser.parse(filepath)
            if not content.strip():
                return None
            
            # Classify
            industry, category, subcategory = self.classifier.classify(content, filepath)
            
            # Create metadata
            doc_id = hashlib.md5(str(filepath).encode()).hexdigest()[:12]
            metadata = {
                'doc_id': doc_id,
                'filename': filepath.name,
                'filepath': str(filepath),
                'file_size': filepath.stat().st_size,
                'file_type': filepath.suffix,
                'industry': industry,
                'category': category,
                'subcategory': subcategory,
                'ingested_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Update stats
            self.stats['industries'][industry] = self.stats['industries'].get(industry, 0) + 1
            self.stats['categories'][category] = self.stats['categories'].get(category, 0) + 1
            
            # Chunk
            chunks = self.chunker.chunk(content, metadata)
            
            # Create document
            return KnowledgeDocument(
                id=doc_id,
                filename=filepath.name,
                filepath=str(filepath),
                file_size=filepath.stat().st_size,
                file_type=filepath.suffix,
                industry=industry,
                category=category,
                subcategory=subcategory,
                content=content[:5000],  # Store first 5000 chars
                chunks=chunks,
                metadata=metadata,
                ingestion_timestamp=datetime.now(timezone.utc).isoformat()
            )
        
        except Exception as e:
            print(f"  ⚠️  Error processing {filepath.name}: {e}")
            return None
    
    def _print_summary(self):
        """Print ingestion summary."""
        print("\n" + "="*70)
        print("📊 INGESTION SUMMARY")
        print("="*70)
        print(f"Total files scanned: {self.stats['total_files']}")
        print(f"Successfully processed: {self.stats['processed']}")
        print(f"Failed/Skipped: {self.stats['failed']}")
        print(f"Total chunks created: {self.stats['total_chunks']}")
        print("\nBy Industry:")
        for ind, count in sorted(self.stats['industries'].items()):
            print(f"  • {ind}: {count} files")
        print("\nBy Category:")
        for cat, count in sorted(self.stats['categories'].items()):
            print(f"  • {cat}: {count} files")
        print("="*70 + "\n")