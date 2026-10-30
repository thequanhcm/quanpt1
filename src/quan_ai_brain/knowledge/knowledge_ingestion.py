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

# V41.3: OCR support — đọc text từ file ảnh (png/jpg/jpeg)
try:
    import pytesseract
    from PIL import Image
    OCR_SUPPORT = True
except ImportError:
    OCR_SUPPORT = False

# Đường dẫn tesseract.exe trên Windows (cài qua UB-Mannheim installer);
# trên Pi/Linux tesseract có sẵn trong PATH.
TESSERACT_CMD_CANDIDATES = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    str(Path.home() / "Programs" / "Tesseract-OCR" / "tesseract.exe"),
    "/usr/bin/tesseract",
]


def _resolve_tesseract_cmd() -> Optional[str]:
    for candidate in TESSERACT_CMD_CANDIDATES:
        if Path(candidate).exists():
            return candidate
    return None


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
        '.csv', '.ipynb', '.json', '.xml', '.html', '.htm',
        # V41.3: file ảnh qua OCR
        '.png', '.jpg', '.jpeg', '.bmp',
    }
    
    def __init__(self, root_path: Path):
        self.root_path = root_path
    
    def scan(self) -> List[Path]:
        """Scan all supported files recursively (deduplicated)."""
        candidates = []
        for ext in self.SUPPORTED_EXTENSIONS:
            candidates.extend(self.root_path.rglob(f"*{ext}"))
            candidates.extend(self.root_path.rglob(f"*{ext.upper()}"))
        
        # Filter out large files (>50MB) and temporary files.
        # Dedupe: Windows rglob is case-insensitive, so lower/upper patterns
        # yield the same file twice.
        valid_files = []
        seen = set()
        for f in candidates:
            if f in seen:
                continue
            seen.add(f)
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
        # V41.3: file ảnh qua OCR (đăng ký động — không phá dict khi thiếu pytesseract)
        if OCR_SUPPORT:
            self.supported['.png'] = self._parse_image
            self.supported['.jpg'] = self._parse_image
            self.supported['.jpeg'] = self._parse_image
            self.supported['.bmp'] = self._parse_image
        self._tesseract_cmd = _resolve_tesseract_cmd() if OCR_SUPPORT else None
    
    def parse(self, filepath: Path) -> str:
        """Parse file and extract text content."""
        ext = filepath.suffix.lower()
        
        if ext not in self.supported:
            raise ValueError(f"Unsupported file type: {ext}")
        
        parser = self.supported[ext]
        return parser(filepath)
    
    def _parse_pdf(self, filepath: Path) -> str:
        """V41: extract theo TỪNG TRANG với marker <<<PAGE N>>> để chunker
        gắn page_number vào metadata — phục vụ trích dẫn 'tài liệu nào, trang nào'."""
        if not PDF_SUPPORT:
            return "[PDF parsing not available - install pypdf]"

        try:
            reader = PdfReader(str(filepath))
            parts = []
            for page_num, page in enumerate(reader.pages, start=1):
                page_text = page.extract_text() or ""
                if page_text.strip():
                    parts.append(f"<<<PAGE {page_num}>>>\n{page_text}")
            return "\n".join(parts)
        except Exception as e:
            return f"[PDF parse error: {e}]"

    def _parse_docx(self, filepath: Path) -> str:
        """V41: đọc CẢ paragraphs VÀ tables — trước đây bỏ sót toàn bộ bảng
        (Sổ tay VT-CNTT 2026: 70 bảng = 544k ký tự bị mất, chiếm 97% nội dung)."""
        if not DOCX_SUPPORT:
            return "[DOCX parsing not available - install python-docx]"

        try:
            doc = Document(str(filepath))
            lines = [para.text for para in doc.paragraphs if para.text.strip()]
            # Tables: mỗi bảng một marker, cells nối bằng " | " giữ cấu trúc
            for table_idx, table in enumerate(doc.tables, start=1):
                lines.append(f"[BẢNG {table_idx}]")
                for row in table.rows:
                    cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                    if cells:
                        lines.append(" | ".join(cells))
            return "\n".join(lines)
        except Exception as e:
            return f"[DOCX parse error: {e}]"

    def _parse_xlsx(self, filepath: Path) -> str:
        """V41: marker <<<SHEET name>>> để chunker gắn page_label = tên sheet."""
        if not PANDAS_SUPPORT:
            return "[Excel parsing not available - install pandas/openpyxl]"

        try:
            xls = pd.read_excel(str(filepath), sheet_name=None)
            text_parts = []
            for sheet_name, df in xls.items():
                text_parts.append(f"<<<SHEET {sheet_name}>>>")
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

    def _parse_image(self, filepath: Path) -> str:
        """V41.3: OCR file ảnh (png/jpg/jpeg/bmp) qua Tesseract vie+eng.

        Trả về header ghi rõ nguồn OCR + nội dung; nếu không đọc được chữ
        (ảnh đồ họa thuần) trả marker rỗng để pipeline skip — fail-honest.
        """
        if not OCR_SUPPORT:
            return "[OCR not available - install pytesseract + Pillow]"
        try:
            if self._tesseract_cmd:
                pytesseract.pytesseract.tesseract_cmd = self._tesseract_cmd
            img = Image.open(str(filepath))
            # Ảnh lớn: thu nhỏ về <=2000px cạnh dài để OCR nhanh, giữ chi tiết
            max_side = max(img.size)
            if max_side > 2000:
                ratio = 2000 / max_side
                img = img.resize((int(img.width * ratio), int(img.height * ratio)))
            if img.mode not in ("L", "RGB"):
                img = img.convert("RGB")
            text = pytesseract.image_to_string(img, lang="vie+eng", timeout=90)
            text = text.strip()
            if not text:
                # ảnh đồ họa/icon không có chữ — báo rõ để pipeline bỏ qua
                return ""
            return f"[NỘI DUNG ẢNH — OCR từ {filepath.name}]\n{text}"
        except Exception as e:
            return f"[OCR parse error: {e}]"


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
        
        # Check path segments (normalize: lowercase + underscores->spaces)
        path_norm = path_str.replace('_', ' ').replace('-', ' ')
        if 'co dien' in path_norm or 'cơ điện' in path_norm:
            return 'electrical'
        elif 'machine learning' in path_norm or 'ml' in path_norm:
            return 'machine_learning'
        elif 'nlp' in path_norm:
            return 'nlp'
        elif 'computer vision' in path_norm or 'cv' in path_norm:
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

    # V41: marker trang/sheet do FormatParser chèn — regex phải khớp chuỗi
    # thực tế trong content (trên một dòng riêng).
    _PAGE_MARKER_RE = re.compile(r"<<<PAGE (\d+)>>>")
    _SHEET_MARKER_RE = re.compile(r"<<<SHEET (.+?)>>>")

    @classmethod
    def _strip_marker(cls, text: str) -> tuple[str, Optional[int], Optional[str]]:
        """Trích + loại marker trang/sheet khỏi text chunk.

        Trả về (content_sạch, page_number | None, page_label | None).
        """
        page_num: Optional[int] = None
        page_label: Optional[str] = None
        m = cls._PAGE_MARKER_RE.search(text)
        if m:
            page_num = int(m.group(1))
        m2 = cls._SHEET_MARKER_RE.search(text)
        if m2:
            page_label = m2.group(1).strip()
        clean = cls._PAGE_MARKER_RE.sub("", cls._SHEET_MARKER_RE.sub("", text))
        clean = re.sub(r"\n{3,}", "\n\n", clean).strip()
        return clean, page_num, page_label

    def chunk(self, content: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Split content into overlapping chunks (word-boundary aware).

        V41: sau khi chia xong, mỗi chunk được gắn metadata['page_number'] /
        metadata['page_label'] dựa trên marker <<<PAGE N>>>/<<<SHEET ...>>>
        nằm trong nội dung chunk — phục vụ citation 'tài liệu nào, trang nào'.
        """
        chunks = []

        # Split by paragraphs first
        paragraphs = re.split(r'\n\s*\n', content)
        
        current_chunk = ""
        chunk_id = 0
        
        def _split_long_paragraph(text: str) -> List[str]:
            """Split an oversized paragraph at word boundaries into <=chunk_size pieces."""
            pieces = []
            words = text.split()
            current = ""
            for word in words:
                if current and len(current) + 1 + len(word) > self.chunk_size:
                    pieces.append(current)
                    # carry overlap tail into next piece for continuity
                    tail = current[-self.overlap:] if self.overlap > 0 else ""
                    current = (tail + " " + word).strip() if tail else word
                else:
                    current = f"{current} {word}".strip()
            if current.strip():
                pieces.append(current)
            return pieces
        
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
                    for piece in _split_long_paragraph(para):
                        chunks.append(self._create_chunk(
                            piece.strip(), chunk_id, metadata
                        ))
                        chunk_id += 1
                    current_chunk = ""
                else:
                    current_chunk = para + "\n\n"
        
        # Add last chunk
        if current_chunk.strip():
            chunks.append(self._create_chunk(
                current_chunk.strip(), chunk_id, metadata
            ))

        # V41: gắn page_number/page_label vào metadata từng chunk từ marker.
        # Marker có thể bị overlap cắt mất ở chunk sau → chunk không có marker
        # THỪA HƯỚNG page của chunk trước liền kề (cùng tài liệu, đọc liên tục).
        current_page: Optional[int] = None
        current_label: Optional[str] = None
        for chunk in chunks:
            clean, page_num, page_label = self._strip_marker(chunk['content'])
            chunk['content'] = clean
            if page_num is not None:
                current_page = page_num
            if page_label is not None:
                current_label = page_label
            if current_page is not None:
                chunk['metadata']['page_number'] = current_page
            if current_label is not None:
                chunk['metadata']['page_label'] = current_label

        return chunks
    
    def _create_chunk(self, content: str, chunk_id: int, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Create a chunk with metadata.

        V41 FIX (30/10/2026): phải copy metadata dict — trước đây dùng chung
        reference, khi gắn page_number cho từng chunk thì mọi chunk đều nhận
        giá trị của chunk cuối (page đè lẫn nhau, citation sai trang).
        """
        return {
            'id': f"{metadata['doc_id']}_chunk_{chunk_id}",
            'content': content,
            'chunk_id': chunk_id,
            'total_chunks': 0,  # Will be updated later
            'metadata': dict(metadata)
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