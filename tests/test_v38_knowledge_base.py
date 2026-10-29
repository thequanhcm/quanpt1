"""Tests for V38 Multi-Domain Knowledge Base."""

import pytest
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from quan_ai_brain.knowledge.knowledge_ingestion import (
    FileScanner, FormatParser, DomainClassifier, ChunkingEngine
)
from quan_ai_brain.knowledge.knowledge_query import KnowledgeQueryEngine, SearchResult


class TestDomainClassifier:
    """Test domain classification."""
    
    def test_classify_engineering_document(self):
        classifier = DomainClassifier()
        content = "Kỹ thuật điện, bảo trì thiết bị, sơ đồ mạch điện"
        filepath = Path("kho_tai_lieu/co_dien/bao_cao.docx")
        
        industry, category, subcategory = classifier.classify(content, filepath)
        
        assert industry == "engineering"
        assert subcategory == "electrical"
    
    def test_classify_ai_document(self):
        classifier = DomainClassifier()
        content = "Machine learning, neural networks, deep learning, transformer"
        filepath = Path("kho_tai_lieu/ai/module1.pdf")
        
        industry, category, subcategory = classifier.classify(content, filepath)
        
        assert industry == "ai"
    
    def test_classify_training_document(self):
        classifier = DomainClassifier()
        content = "Bài giảng, lab, thực hành, đào tạo"
        filepath = Path("kho_tai_lieu/training/module1/lecture.pdf")
        
        industry, category, subcategory = classifier.classify(content, filepath)
        
        assert industry == "training"
        assert category == "training"


class TestChunkingEngine:
    """Test chunking functionality."""
    
    def test_basic_chunking(self):
        chunker = ChunkingEngine(chunk_size=100, overlap=20)
        content = "This is paragraph one. " * 10 + "This is paragraph two. " * 10
        
        chunks = chunker.chunk(content, {'doc_id': 'test123'})
        
        assert len(chunks) > 1
        assert all(len(c['content']) <= 120 for c in chunks)  # chunk_size + overlap
    
    def test_chunk_metadata(self):
        chunker = ChunkingEngine(chunk_size=100)
        content = "Test content"
        metadata = {'doc_id': 'test456', 'filename': 'test.txt'}
        
        chunks = chunker.chunk(content, metadata)
        
        assert len(chunks) == 1
        assert chunks[0]['metadata']['doc_id'] == 'test456'
        assert chunks[0]['metadata']['filename'] == 'test.txt'


class TestKnowledgeQueryEngine:
    """Test knowledge query engine."""
    
    @pytest.fixture
    def query_engine(self):
        return KnowledgeQueryEngine(db_path=Path("data/test_knowledge_db"))
    
    def test_initialization(self, query_engine):
        assert query_engine.collection is not None
        assert query_engine.embedding_service is not None
    
    def test_search_empty(self, query_engine):
        results = query_engine.search("test query")
        assert isinstance(results, list)
    
    def test_format_results(self, query_engine):
        results = [
            SearchResult(
                chunk_id="test1",
                content="Test content",
                score=0.85,
                filename="test.pdf",
                filepath="/path/test.pdf",
                industry="engineering",
                category="technical",
                subcategory="electrical",
                file_type=".pdf",
                file_size=1024
            )
        ]
        
        formatted = query_engine.format_results(results)
        assert "test.pdf" in formatted
        assert "engineering" in formatted
        assert "85%" in formatted


class TestFileScanner:
    """Test file scanning."""
    
    def test_scan_supported_files(self, tmp_path):
        # Create test files
        (tmp_path / "test.pdf").touch()
        (tmp_path / "test.docx").touch()
        (tmp_path / "test.txt").touch()
        (tmp_path / "test.xyz").touch()  # Not supported
        
        scanner = FileScanner(tmp_path)
        files = scanner.scan()
        
        assert len(files) == 3
        assert all(f.suffix.lower() in FileScanner.SUPPORTED_EXTENSIONS for f in files)
    
    def test_scan_recursive(self, tmp_path):
        # Create nested directories
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "test.pdf").touch()
        (tmp_path / "test.docx").touch()
        
        scanner = FileScanner(tmp_path)
        files = scanner.scan()
        
        assert len(files) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])