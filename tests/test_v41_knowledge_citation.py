"""Tests V41 — Knowledge citation pipeline (30/10/2026).

Yêu cầu của Quanpt1: khi hỏi, hệ thống phải nắm/hiểu/phân tích được và đưa ra
DẪN CHỨNG là tài liệu nào, trang nào.

Phủ: FormatParser (PDF page markers, DOCX tables), ChunkingEngine (page tracking),
SearchResult.citation(), render_evidence_block, answer_question format.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from quan_ai_brain.knowledge.knowledge_ingestion import (  # noqa: E402
    ChunkingEngine,
    FormatParser,
)
from quan_ai_brain.knowledge.knowledge_query import (  # noqa: E402
    KnowledgeQueryEngine,
    SearchResult,
)


# ============================================================
# FormatParser — PDF page markers
# ============================================================
class TestPdfPageExtraction:
    def _make_reader(self, pages_text: list[str]):
        reader = MagicMock()
        pages = []
        for txt in pages_text:
            p = MagicMock()
            p.extract_text.return_value = txt
            pages.append(p)
        reader.pages = pages
        return reader

    def test_pdf_parse_adds_page_markers(self):
        parser = FormatParser()
        fake_path = Path("fake.pdf")
        with patch("quan_ai_brain.knowledge.knowledge_ingestion.PDF_SUPPORT", True), \
             patch("quan_ai_brain.knowledge.knowledge_ingestion.PdfReader") as MockReader:
            MockReader.return_value = self._make_reader(["Nội dung trang một", "Nội dung trang hai"])
            content = parser._parse_pdf(fake_path)
        assert "<<<PAGE 1>>>" in content
        assert "<<<PAGE 2>>>" in content
        assert "Nội dung trang hai" in content

    def test_pdf_empty_page_skipped_no_marker(self):
        parser = FormatParser()
        with patch("quan_ai_brain.knowledge.knowledge_ingestion.PDF_SUPPORT", True), \
             patch("quan_ai_brain.knowledge.knowledge_ingestion.PdfReader") as MockReader:
            MockReader.return_value = self._make_reader(["Trang 1 nội dung", "", "  "])
            content = parser._parse_pdf(Path("fake.pdf"))
        assert "<<<PAGE 1>>>" in content
        assert "<<<PAGE 2>>>" not in content  # trang rỗng không có marker
        assert "<<<PAGE 3>>>" not in content

    def test_pdf_parse_error_returns_marker_string(self):
        parser = FormatParser()
        with patch("quan_ai_brain.knowledge.knowledge_ingestion.PDF_SUPPORT", True), \
             patch("quan_ai_brain.knowledge.knowledge_ingestion.PdfReader", side_effect=Exception("bad pdf")):
            content = parser._parse_pdf(Path("bad.pdf"))
        assert "PDF parse error" in content


# ============================================================
# FormatParser — DOCX tables (lỗ hổng 544k ký tự bị mất)
# ============================================================
class TestDocxTableExtraction:
    def _make_doc(self, paras: list[str], tables: list[list[list[str]]]):
        doc = MagicMock()
        p_objs = []
        for txt in paras:
            p = MagicMock()
            p.text = txt
            p_objs.append(p)
        doc.paragraphs = p_objs
        t_objs = []
        for table_rows in tables:
            t = MagicMock()
            rows = []
            for row_cells in table_rows:
                r = MagicMock()
                c_objs = []
                for cell_text in row_cells:
                    c = MagicMock()
                    c.text = cell_text
                    c_objs.append(c)
                r.cells = c_objs
                rows.append(r)
            t.rows = rows
            t_objs.append(t)
        doc.tables = t_objs
        return doc

    def test_docx_parse_includes_tables(self):
        parser = FormatParser()
        doc = self._make_doc(
            paras=["Đoạn mở đầu"],
            tables=[[["Thuật ngữ", "Định nghĩa"], ["RLS", "Row Level Security"]]],
        )
        with patch("quan_ai_brain.knowledge.knowledge_ingestion.DOCX_SUPPORT", True), \
             patch("quan_ai_brain.knowledge.knowledge_ingestion.Document", return_value=doc):
            content = parser._parse_docx(Path("fake.docx"))
        assert "Đoạn mở đầu" in content
        assert "[BẢNG 1]" in content
        assert "RLS | Row Level Security" in content

    def test_docx_parse_table_cells_joined(self):
        parser = FormatParser()
        doc = self._make_doc(paras=[], tables=[[["A", "B", "C"]]])
        with patch("quan_ai_brain.knowledge.knowledge_ingestion.DOCX_SUPPORT", True), \
             patch("quan_ai_brain.knowledge.knowledge_ingestion.Document", return_value=doc):
            content = parser._parse_docx(Path("f.docx"))
        assert "A | B | C" in content


# ============================================================
# ChunkingEngine — page tracking qua marker
# ============================================================
class TestChunkPageTracking:
    def test_chunk_pdf_pages_tracked(self):
        engine = ChunkingEngine(chunk_size=200, overlap=20)
        content = (
            "<<<PAGE 1>>>\nGiới thiệu về RAN 5G. " * 3
            + "\n\n<<<PAGE 2>>>\nĐịnh nghĩa PM counter. " * 3
        )
        metadata = {"doc_id": "d1", "filename": "ran.pdf"}
        chunks = engine.chunk(content, metadata)
        assert len(chunks) >= 2
        pages = {c["metadata"].get("page_number") for c in chunks}
        assert 1 in pages and 2 in pages
        # content đã sạch marker
        for c in chunks:
            assert "<<<PAGE" not in c["content"]

    def test_chunk_xlsx_sheet_label_tracked(self):
        engine = ChunkingEngine(chunk_size=500, overlap=50)
        content = "<<<SHEET Cong suat>>>\n" + "Dữ liệu công suất trạm. " * 50
        chunks = engine.chunk(content, {"doc_id": "d2", "filename": "cs.xlsx"})
        assert all(c["metadata"].get("page_label") == "Cong suat" for c in chunks)

    def test_chunk_without_marker_no_page(self):
        engine = ChunkingEngine()
        chunks = engine.chunk("Text thường không marker. " * 100, {"doc_id": "d3"})
        assert all("page_number" not in c["metadata"] for c in chunks)

    def test_strip_marker_returns_clean(self):
        clean, page, label = ChunkingEngine._strip_marker("<<<PAGE 7>>>\nNội dung")
        assert page == 7
        assert "<<<" not in clean
        assert "Nội dung" in clean
        assert label is None


# ============================================================
# SearchResult.citation — 'tài liệu nào, trang nào'
# ============================================================
class TestCitation:
    def _result(self, **kw):
        defaults = dict(
            chunk_id="c1", content="nội dung", score=0.87,
            filename="C3_Lecture.pdf", filepath="E:/x/C3_Lecture.pdf",
            industry="ai", category="training", subcategory="course_module",
            file_type=".pdf", file_size=1000,
        )
        defaults.update(kw)
        return SearchResult(**defaults)

    def test_citation_with_page(self):
        r = self._result(page_number=12)
        assert r.citation() == "C3_Lecture.pdf (trang 12)"

    def test_citation_with_sheet_label(self):
        r = self._result(page_label="Cong suat")
        assert r.citation() == "C3_Lecture.pdf (sheet 'Cong suat')"

    def test_citation_unknown_location(self):
        r = self._result()
        assert "không xác định" in r.citation()

    def test_page_number_takes_precedence(self):
        r = self._result(page_number=3, page_label="SheetA")
        assert r.citation() == "C3_Lecture.pdf (trang 3)"


# ============================================================
# render_evidence_block — evidence cho LLM với citation bắt buộc
# ============================================================
class TestEvidenceBlock:
    def _engine(self):
        with patch.object(KnowledgeQueryEngine, "__init__", lambda self, db_path=None: None):
            eng = KnowledgeQueryEngine(db_path=None)
        return eng

    def test_evidence_block_contains_citations(self):
        eng = self._engine()
        results = [
            SearchResult(
                chunk_id="c1", content="RLS là Row Level Security", score=0.9,
                filename="Bai5_Lecture_RAG.pdf", filepath="x", industry="ai",
                category="training", subcategory="rag", file_type=".pdf",
                file_size=1, page_number=5,
            ),
        ]
        block = eng.render_evidence_block(results)
        assert "[EVIDENCE KHO TRI THỨC" in block
        assert "Bai5_Lecture_RAG.pdf (trang 5)" in block
        assert "RLS là Row Level Security" in block
        # hướng dẫn LLM phải dẫn nguồn
        assert "phải dẫn nguồn" in block

    def test_evidence_block_empty_when_no_results(self):
        eng = self._engine()
        assert eng.render_evidence_block([]) == ""

    def test_evidence_block_truncates_long_content(self):
        eng = self._engine()
        results = [
            SearchResult(
                chunk_id="c1", content="X" * 5000, score=0.8,
                filename="f.pdf", filepath="x", industry="ai", category="c",
                subcategory="s", file_type=".pdf", file_size=1, page_number=1,
            ),
        ]
        block = eng.render_evidence_block(results)
        assert len(block) < 2000  # 1200 content + header/citation


# ============================================================
# answer_question — citation trong output
# ============================================================
class TestAnswerQuestion:
    def test_answer_includes_citation_line(self):
        with patch.object(KnowledgeQueryEngine, "__init__", lambda self, db_path=None: None):
            eng = KnowledgeQueryEngine(db_path=None)
        fake_results = [
            SearchResult(
                chunk_id="c1", content="Churn là khách hàng rời bỏ dịch vụ",
                score=0.88, filename="Customer_Churn.pdf", filepath="x",
                industry="ai", category="data", subcategory="churn",
                file_type=".pdf", file_size=1, page_number=8,
            ),
        ]
        with patch.object(eng, "search", return_value=fake_results):
            answer = eng.answer_question("churn là gì?")
        assert "Customer_Churn.pdf (trang 8)" in answer
        assert "Churn là khách hàng rời bỏ dịch vụ" in answer

    def test_answer_no_results_fail_honest(self):
        with patch.object(KnowledgeQueryEngine, "__init__", lambda self, db_path=None: None):
            eng = KnowledgeQueryEngine(db_path=None)
        with patch.object(eng, "search", return_value=[]):
            answer = eng.answer_question("câu hỏi không có dữ liệu")
        assert "không tìm thấy" in answer.lower()
