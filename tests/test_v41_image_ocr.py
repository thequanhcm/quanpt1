"""Tests V41.3 — OCR file ảnh trong knowledge pipeline (30/10/2026).

Yêu cầu Quanpt1: cài đặt + xử lý để đọc được file ảnh.
Verify: FormatParser nhận png/jpg/jpeg/bmp, OCR vie+eng, fail-honest với ảnh không chữ.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

from quan_ai_brain.knowledge.knowledge_ingestion import (  # noqa: E402
    OCR_SUPPORT,
    FormatParser,
    FileScanner,
    _resolve_tesseract_cmd,
)


@pytest.mark.skipif(not OCR_SUPPORT, reason="pytesseract/Pillow chưa cài")
class TestImageOCR:
    def test_tesseract_cmd_resolved(self):
        if sys.platform == "win32":
            assert _resolve_tesseract_cmd() is not None

    def test_parser_supports_image_extensions(self):
        p = FormatParser()
        for ext in (".png", ".jpg", ".jpeg", ".bmp"):
            assert ext in p.supported, f"thiếu {ext}"

    def test_ocr_vietnamese_chart(self):
        """Ảnh chart tiếng Việt thật trong kho — phải đọc được chữ."""
        p = FormatParser()
        img = SRC.parent / "kho_tai_lieu" / "Train AI course" / "Data Scientist Course" / "Module 3" / "Bài 1" / "Bài 1 - Lab" / "charts" / "Chart_01.png"
        if not img.exists():
            pytest.skip("ảnh sample không tồn tại")
        content = p.parse(img)
        assert "[NỘI DUNG ẢNH" in content
        assert "Cước trung bình" in content  # text tiếng Việt đã đọc ra

    def test_ocr_graphic_only_image_returns_empty(self):
        """Ảnh icon/đồ họa thuần không có chữ → trả rỗng (fail-honest, skip)."""
        p = FormatParser()
        img = SRC.parent / "Pi5" / "02_tony_assistant.png"
        if not img.exists():
            pytest.skip("ảnh sample không tồn tại")
        content = p.parse(img)
        assert content == ""

    def test_ocr_error_fail_honest(self, tmp_path):
        """File hỏng → trả marker lỗi, không raise."""
        p = FormatParser()
        bad = tmp_path / "broken.png"
        bad.write_bytes(b"not an image")
        content = p.parse(bad)
        assert "OCR parse error" in content or content == ""

    def test_scanner_includes_images(self, tmp_path):
        (tmp_path / "a.png").write_bytes(b"x")
        (tmp_path / "b.txt").write_text("hi")
        files = FileScanner(tmp_path).scan()
        names = {f.name for f in files}
        assert "a.png" in names and "b.txt" in names


class TestScannerNoOcr:
    def test_scanner_extensions_declared(self):
        assert ".png" in FileScanner.SUPPORTED_EXTENSIONS
        assert ".jpg" in FileScanner.SUPPORTED_EXTENSIONS
        assert ".jpeg" in FileScanner.SUPPORTED_EXTENSIONS
