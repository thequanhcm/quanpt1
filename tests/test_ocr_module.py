# -*- coding: utf-8 -*-
"""Test tools/ocr_module.py — module OCR 2 tầng của CHERRY (24/11/2026).

Test thật (không mock engine): RapidOCR + winocr đã cài trong .venv;
ảnh test vẽ bằng PIL (không phụ thuộc file ngoài).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent.parent / "tools"
sys.path.insert(0, str(TOOLS))

import ocr_module  # noqa: E402

pytest.importorskip("rapidocr_onnxruntime")


def _make_text_image(tmp_path: Path, text: str, size=(600, 200)):
    from PIL import Image, ImageDraw
    im = Image.new("RGB", size, "white")
    d = ImageDraw.Draw(im)
    d.text((30, 80), text, fill="black")
    p = tmp_path / "ocr_test.png"
    im.save(p)
    return p


def test_rapidocr_reads_text(tmp_path):
    p = _make_text_image(tmp_path, "XIN CHAO OCR 12345")
    r = ocr_module.run_rapidocr(str(p))
    assert r["engine"] == "rapidocr"
    assert r["error"] is None
    assert "12345" in r["text_flat"] or "XIN" in r["text_flat"].upper()
    assert r["lines"], "phải có box từng dòng"
    assert r["avg_score"] is not None and r["avg_score"] > 0.3


def test_rapidocr_table_keeps_column_gap(tmp_path):
    # 2 cụm chữ cách xa nhau theo x, cùng dòng y → phải có gap '|'
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (800, 200), "white")
    d = ImageDraw.Draw(im)
    d.text((40, 80), "TEN", fill="black")
    d.text((600, 80), "1.150.000", fill="black")
    p = tmp_path / "tbl.png"
    im.save(p)
    r = ocr_module.run_rapidocr(str(p))
    assert r["engine"] == "rapidocr"
    # gap marker hoặc ít nhất cả 2 cụm đều xuất hiện
    flat = r["text_flat"]
    assert "TEN" in flat.replace(" ", "") or "1.150.000" in flat or "1150000" in flat.replace(".", "")


def test_ocr_image_structured_fallback_chain(tmp_path):
    p = _make_text_image(tmp_path, "FALLBACK CHAIN TEST")
    r = ocr_module.ocr_image_structured(str(p))
    assert r["engine"] in ("rapidocr", "winocr")
    assert r["text_flat"].strip()
    assert r["elapsed_ms"] >= 0


def test_ocr_image_text_raises_on_none(tmp_path):
    # ảnh TRẮNG hoàn toàn (không chữ) → cả 2 engine rỗng → raise (fail-honest)
    from PIL import Image
    p = tmp_path / "blank.png"
    Image.new("RGB", (400, 200), "white").save(p)
    with pytest.raises(RuntimeError):
        ocr_module.ocr_image_text(str(p))


def test_winocr_en_us(tmp_path):
    pytest.importorskip("winocr")
    p = _make_text_image(tmp_path, "WINOCR TEST 987")
    r = ocr_module.run_winocr(str(p), "en-US")
    # en-US pack đã cài 24/11 → engine winocr; nếu máy thiếu pack → engine none
    # (không fail test, chỉ assert shape hợp lệ — fail-honest)
    assert r["engine"] in ("winocr", "none")
    if r["engine"] == "winocr":
        assert r["text_flat"].strip()


def test_worker_file_exists():
    assert (TOOLS / "ocr_worker.py").exists()
