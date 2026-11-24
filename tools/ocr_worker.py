# -*- coding: utf-8 -*-
"""OCR worker — subprocess entry cho tools/ocr_module.py (24/11/2026).

Dùng FILE thay cho chuỗi `python -c` nối dài (đã gây SyntaxError khi nối
ngoặc). Gọi:
    python ocr_worker.py rapidocr <ảnh>   → JSON [{text,score,x,y,w,h}]
    python ocr_worker.py winocr <ảnh> <lang> → JSON cùng shape

Pre-process: grayscale + autocontrast + upscale 2x nếu ảnh nhỏ (<1400px);
kết quả rỗng → thử lại ảnh gốc. Fail-honest: lỗi → in JSON [] (rỗng) thay
vì crash để caller xử lý.
"""
from __future__ import annotations

import json
import sys


def _prep(path: str) -> str:
    try:
        from PIL import Image, ImageOps
        im = Image.open(path)
        if im.mode != "RGB":
            im = im.convert("RGB")
        w, h = im.size
        if max(w, h) < 1400:
            im = im.resize((w * 2, h * 2))
        im = ImageOps.autocontrast(im.convert("L").convert("RGB"))
        out = path + ".ocrprep.png"
        im.save(out)
        return out
    except Exception:
        return path


def _box_to_xywh(line) -> dict:
    box, text, score = line[0], line[1], line[2]
    xs = [pt[0] for pt in box]
    ys = [pt[1] for pt in box]
    x0, y0 = int(min(xs)), int(min(ys))
    return {
        "text": str(text),
        "score": float(score),
        "x": x0,
        "y": y0,
        "w": int(max(xs)) - x0,
        "h": int(max(ys)) - y0,
    }


def main() -> int:
    mode = sys.argv[1]
    path = sys.argv[2]
    try:
        if mode == "rapidocr":
            from rapidocr_onnxruntime import RapidOCR
            engine = RapidOCR()
            pp = _prep(path)
            result, _elapse = engine(pp)
            if not (result or []):
                result, _elapse = engine(path)
            out = [_box_to_xywh(line) for line in (result or [])]
            print(json.dumps(out, ensure_ascii=False))
            return 0
        if mode == "winocr":
            import winocr
            from PIL import Image
            img = Image.open(path)
            img.load()
            res = winocr.recognize_pil(img, sys.argv[3]).get()
            lines = []
            for line in res.lines:
                if not line.words:
                    continue
                # tọa độ lấy từ WORD level (OcrLine không có bounding_rect);
                # line box = bao các word box
                xs = [w.bounding_rect.x for w in line.words]
                ys = [w.bounding_rect.y for w in line.words]
                xe = [w.bounding_rect.x + w.bounding_rect.width for w in line.words]
                ye = [w.bounding_rect.y + w.bounding_rect.height for w in line.words]
                x0, y0 = int(min(xs)), int(min(ys))
                lines.append({
                    "text": line.text,
                    "score": None,
                    "x": x0, "y": y0,
                    "w": int(max(xe)) - x0, "h": int(max(ye)) - y0,
                })
            print(json.dumps(lines, ensure_ascii=False))
            return 0
        print(json.dumps({"error": f"mode không hợp lệ: {mode}"}))
        return 2
    except Exception as exc:  # fail-honest: JSON rỗng + error ra stderr
        print("[]")
        print(f"ocr_worker error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
