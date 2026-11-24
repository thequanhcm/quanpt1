# -*- coding: utf-8 -*-
"""OCR module chuẩn hóa cho CHERRY — "mắt" đọc mọi hình ảnh trong DM.

(24/11/2026, owner: "phat trien module OCR (rapidocr-onnxruntime + winocr)
trong moi truong chay cua em")

Vì sao tách module riêng:
- _ocr_image trong netchat_auto_responder.py chỉ trả TEXT THÔ — mất cấu trúc
  (bảng, cột) vì RapidOCR trả từng dòng kèm TỌA ĐỘ (box) + SCORE mà code cũ
  bỏ qua. Ghép dòng theo tọa độ đọc bảng/biểu đồ chuẩn hơn nhiều.
- Cần 1 nơi duy nhất để bench + test cả 2 engine (RapidOCR chính, Windows
  OCR dự phòng) — trước giờ winocr chưa từng được test thật.

API chính:
- ocr_image_structured(path) -> dict:
    {
      "engine": "rapidocr" | "winocr" | "none",
      "text_flat": str,            # text ghép dòng (đọc bảng theo y→x)
      "lines": [{"text", "score", "x", "y", "w", "h"}],
      "avg_score": float | None,   # chất lượng OCR (0..1), None nếu winocr
      "elapsed_ms": int,
      "error": str | None,         # fail-honest: lý do nếu không đọc được
    }
- ocr_image_text(path) -> str: convenience wrapper (text_flat hoặc raise)

Pre-process giữ nguyên triết lý sprint trước: grayscale + autocontrast +
upscale 2x nếu ảnh nhỏ; nếu pre-process làm OCR RỖNG thì fallback ảnh gốc.

KHÔNG phụ thuộc mạng. Chỉ stdlib + rapidocr_onnxruntime + winocr + PIL.
R2 READONLY: không ghi gì ngoài file .ocrprep.png tạm trong cùng thư mục.
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path
from typing import Any

# Interpreter chạy OCR = BRAIN venv (module đã cài: rapidocr, winocr, PIL)
_VENV_PY = Path(__file__).resolve().parent.parent / ".venv" / "Scripts" / "python.exe"
if not _VENV_PY.exists():
    _VENV_PY = Path(sys.executable)

_NO_WIN = 0x08000000 if sys.platform == "win32" else 0

_WORKER = str(Path(__file__).resolve().parent / "ocr_worker.py")


def _group_lines(lines: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    """Gom các box thành dòng theo tọa độ y (cluster ngưỡng nửa chiều cao)."""
    if not lines:
        return []
    ordered = sorted(lines, key=lambda l: (l["y"], l["x"]))
    groups: list[list[dict[str, Any]]] = []
    for ln in ordered:
        placed = False
        for g in groups:
            ref = g[-1]
            mid_new = ln["y"] + ln["h"] / 2
            mid_ref = ref["y"] + ref["h"] / 2
            if abs(mid_new - mid_ref) <= max(ln["h"], ref["h"]) * 0.6:
                g.append(ln)
                placed = True
                break
        if not placed:
            groups.append([ln])
    for g in groups:
        g.sort(key=lambda l: l["x"])
    groups.sort(key=lambda g: min(l["y"] for l in g))
    return groups


def _flat_from_lines(lines: list[dict[str, Any]]) -> str:
    groups = _group_lines(lines)
    rows = []
    for g in groups:
        parts = []
        prev = None
        for ln in g:
            # hai box cùng dòng cách xa nhau (>= 2 ký tự rộng) → chèn gap để
            # giữ cấu trúc cột của bảng/biểu đồ
            if prev is not None and ln["x"] - (prev["x"] + prev["w"]) > prev["h"] * 1.2:
                parts.append("   |   ")
            parts.append(ln["text"])
            prev = ln
        rows.append(" ".join(parts) if "|" not in "".join(parts) else " ".join(parts))
    return "\n".join(rows)


def run_rapidocr(path: str | Path) -> dict[str, Any]:
    """Tầng 1: RapidOCR (onnx, offline, tốt với tiếng Việt)."""
    t0 = time.time()
    try:
        res = subprocess.run(
            [str(_VENV_PY), _WORKER, "rapidocr", str(path)],
            capture_output=True, creationflags=_NO_WIN, text=True, timeout=300,
        )
    except Exception as exc:
        return {"engine": "none", "text_flat": "", "lines": [], "avg_score": None,
                "elapsed_ms": int((time.time() - t0) * 1000),
                "error": f"{type(exc).__name__}: {exc}"}
    import json
    if res.returncode != 0 or not res.stdout.strip():
        return {"engine": "none", "text_flat": "", "lines": [], "avg_score": None,
                "elapsed_ms": int((time.time() - t0) * 1000),
                "error": (res.stderr or "").strip()[-300:] or "rapidocr trả rỗng"}
    try:
        lines = json.loads(res.stdout)
    except Exception as exc:
        return {"engine": "none", "text_flat": "", "lines": [], "avg_score": None,
                "elapsed_ms": int((time.time() - t0) * 1000),
                "error": f"JSON parse: {exc}"}
    scores = [l["score"] for l in lines if l.get("score") is not None]
    return {
        "engine": "rapidocr",
        "text_flat": _flat_from_lines(lines),
        "lines": lines,
        "avg_score": round(sum(scores) / len(scores), 3) if scores else None,
        "elapsed_ms": int((time.time() - t0) * 1000),
        "error": None,
    }


def run_winocr(path: str | Path, lang: str = "vi-VN") -> dict[str, Any]:
    """Tầng 2 dự phòng: Windows OCR (winocr). Trả dict cùng shape, fail-honest."""
    t0 = time.time()
    try:
        res = subprocess.run(
            [str(_VENV_PY), _WORKER, "winocr", str(path), lang],
            capture_output=True, creationflags=_NO_WIN, text=True, timeout=180,
        )
    except Exception as exc:
        return {"engine": "none", "text_flat": "", "lines": [], "avg_score": None,
                "elapsed_ms": int((time.time() - t0) * 1000),
                "error": f"{type(exc).__name__}: {exc}"}
    import json
    if res.returncode != 0 or not res.stdout.strip():
        return {"engine": "none", "text_flat": "", "lines": [], "avg_score": None,
                "elapsed_ms": int((time.time() - t0) * 1000),
                "error": (res.stderr or "").strip()[-300:] or f"winocr({lang}) trả rỗng"}
    try:
        lines = json.loads(res.stdout)
    except Exception as exc:
        return {"engine": "none", "text_flat": "", "lines": [], "avg_score": None,
                "elapsed_ms": int((time.time() - t0) * 1000),
                "error": f"JSON parse: {exc}"}
    return {
        "engine": "winocr",
        "text_flat": _flat_from_lines(lines),
        "lines": lines,
        "avg_score": None,  # Windows OCR không trả score từng dòng
        "elapsed_ms": int((time.time() - t0) * 1000),
        "error": None,
    }


def ocr_image_structured(path: str | Path) -> dict[str, Any]:
    """Chuỗi 2 tầng: RapidOCR chính → Windows OCR dự phòng (vi-VN rồi en-US).

    Chọn kết quả ĐỌC ĐƯỢC đầu tiên (fail-honest: nếu cả hai rỗng trả
    engine='none' + error, KHÔNG bịa).
    """
    p = str(path)
    best = run_rapidocr(p)
    if best["engine"] == "rapidocr" and best["text_flat"].strip():
        return best
    for lang in ("vi-VN", "en-US"):
        w = run_winocr(p, lang)
        if w["engine"] == "winocr" and w["text_flat"].strip():
            w["error"] = None
            return w
    # cả hai thất bại → báo lỗi tầng cuối (fail-honest)
    return {
        "engine": "none",
        "text_flat": "",
        "lines": [],
        "avg_score": None,
        "elapsed_ms": best.get("elapsed_ms", 0),
        "error": f"OCR rỗng cả 2 engine. RapidOCR: {best.get('error')}; winocr: {w.get('error') if 'w' in dir() else '?'}",
    }


def ocr_image_text(path: str | Path) -> str:
    """Convenience: trả text_flat; raise RuntimeError nếu không đọc được."""
    r = ocr_image_structured(path)
    if r["text_flat"].strip():
        return r["text_flat"]
    raise RuntimeError(r.get("error") or "OCR rỗng")


if __name__ == "__main__":
    # CLI bench nhanh: python ocr_module.py <ảnh>
    import json as _json
    r = ocr_image_structured(sys.argv[1])
    print(_json.dumps({k: v for k, v in r.items() if k != "lines"},
                      ensure_ascii=False, indent=2))
