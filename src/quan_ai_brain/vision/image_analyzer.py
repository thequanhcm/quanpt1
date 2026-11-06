"""TONY Vision — phân tích ảnh (OCR + mô tả cấu trúc, không bịa).

(06/11/2026) Owner: "em sẽ học tập tri thức để nhận diện hình ảnh. em tải về và
cài đặt OCR, huấn luyện cho TONY biết tất cả các hình ảnh, chi tiết để TONY
phân tích được."

Phạm vi SPRINT NÀY (đã duyệt theo lệnh "em tải về và cài đặt OCR"):
- OCR Tesseract vie+eng trên ảnh DM owner gửi / ảnh TONY tự chụp (logs/pi5_media).
- Mô tả cấu trúc THÔ TIN THẬT đo được từ file (kích thước, độ sáng, màu chủ đạo,
  vùng sáng/tối) — không gán nhãn vật thể (nhà bếp, tủ lạnh...) vì engine
  phân loại chưa có; ghi rõ hạn chế (fail-honest, QPIG: không khai báo
  Operational những gì chưa chạy thử).
- Ghi tri thức rút ra vào brain.db (knowledge) — TONY "học" dần theo từng ảnh.

Huấn luyện model nhận diện vật thể thật (YOLO/CLIP...) = Sprint riêng, CHỜ DUYỆT.
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Any

# File nằm ở src/quan_ai_brain/vision/ → E:\BRAIN = parents[3]
BRAIN_ROOT = Path(__file__).resolve().parents[3]
# Ảnh TONY tự chụp từ camera Pi5 (converse/camera_on) tải về PC:
PI5_MEDIA_DIR = BRAIN_ROOT / "logs" / "pi5_media"
# Ảnh owner gửi qua DM (bot tải đính kèm về):
NETCHAT_FILES_DIR = BRAIN_ROOT / "data" / "netchat_files"

_TESSERACT_CANDIDATES = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    str(Path.home() / "Programs" / "Tesseract-OCR" / "tesseract.exe"),
    "/usr/bin/tesseract",
)


def resolve_tesseract() -> str | None:
    """Trả đường dẫn tesseract.exe (PC: UB-Mannheim; Pi/Linux: PATH)."""
    for cand in _TESSERACT_CANDIDATES:
        if Path(cand).exists():
            return cand
    return None


def _ocr_image(path: Path) -> tuple[str, str]:
    """OCR 1 ảnh → (text, ghi_chú_nguồn). Trả ('', note) khi lỗi — không raise."""
    try:
        import pytesseract
        from PIL import Image

        cmd = resolve_tesseract()
        if cmd:
            pytesseract.pytesseract.tesseract_cmd = cmd
        img = Image.open(path)
        try:
            text = pytesseract.image_to_string(img, lang="vie+eng")
        except Exception:
            # thiếu gói ngôn ngữ vie → eng (fallback trung thực, ghi chú nguồn)
            text = pytesseract.image_to_string(img, lang="eng")
            return text.strip(), "OCR eng (thiếu gói vie)"
        return text.strip(), "OCR vie+eng"
    except Exception as exc:
        return "", f"OCR lỗi: {type(exc).__name__}: {exc}"


def _image_facts(path: Path) -> dict[str, Any]:
    """Sự kiện đo được từ file ảnh — chỉ dữ liệu thật, không suy diễn nội dung."""
    try:
        from PIL import Image

        with Image.open(path) as img:
            facts: dict[str, Any] = {
                "width": img.width,
                "height": img.height,
                "mode": img.mode,
            }
            small = img.convert("L").resize((64, 36))
            pixels = list(small.getdata())
            n = len(pixels)
            facts["brightness_mean"] = round(sum(pixels) / n, 1)
            facts["brightness_max"] = max(pixels)
            facts["brightness_min"] = min(pixels)
            # Vùng sáng/tối (trên 64x36 grid — chỉ tọa độ thô, không gán nhãn)
            w, h = 64, 36
            bright = [(i % w, i // w) for i, v in enumerate(pixels) if v > 230]
            dark = [(i % w, i // w) for i, v in enumerate(pixels) if v < 25]
            facts["bright_regions"] = len(bright)
            facts["dark_regions"] = len(dark)
            # Màu chủ đạo (top 3, quantize 64 màu)
            rgb = img.convert("RGB").resize((64, 36))
            counts: dict[tuple[int, int, int], int] = {}
            for px in rgb.getdata():
                q = (px[0] // 64, px[1] // 64, px[2] // 64)
                counts[q] = counts.get(q, 0) + 1
            top = sorted(counts.items(), key=lambda kv: -kv[1])[:3]
            facts["dominant_colors_rgb64"] = [
                {"rgb": [q[0] * 64 + 32, q[1] * 64 + 32, q[2] * 64 + 32], "ratio": round(c / n, 2)}
                for q, c in top
            ]
            return facts
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}


def _fallback_search(paths: list[Path]) -> Path | None:
    """Ảnh phân tích gần nhất nếu tin không kèm file: DM attach → Pi5 media."""
    now = time.time()
    for d in paths:
        if not d.exists():
            continue
        best, best_mt = None, 0.0
        for f in d.iterdir():
            if f.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".bmp"} \
                    and now - f.stat().st_mtime < 86400:  # ảnh trong 24h
                mt = f.stat().st_mtime
                if mt > best_mt:
                    best, best_mt = f, mt
        if best is not None:
            return best
    return None


def latest_capture_info() -> dict[str, Any]:
    """Info ảnh TONY tự chụp MỚI NHẤT trong logs/pi5_media (dùng cho DM reply)."""
    best, best_mt = None, 0.0
    if PI5_MEDIA_DIR.exists():
        for f in PI5_MEDIA_DIR.iterdir():
            if f.suffix.lower() in {".jpg", ".jpeg", ".png"}:
                mt = f.stat().st_mtime
                if mt > best_mt:
                    best, best_mt = f, mt
    if best is None:
        return {}
    return {
        "path": str(best),
        "filename": best.name,
        "mtime": best_mt,
        "age_min": round((time.time() - best_mt) / 60, 1),
    }


def analyze_image(path: str | Path, *, max_ocr_chars: int = 1200) -> str:
    """Phân tích 1 ảnh → text tiếng Việt trung thực: facts + OCR + ghi vào knowledge.

    Trả về text DM-ready; KHÔNG bịa vật thể, KHÔNG gán nhãn khi không đo được.
    """
    p = Path(path)
    if not p.exists():
        return f"⚠️ Không tìm thấy file ảnh: {p.name}"

    facts = _image_facts(p)
    if "error" in facts:
        return f"⚠️ Không đọc được ảnh {p.name}: {facts['error']}"

    ocr_text, ocr_note = _ocr_image(p)

    # Ghi tri thức vào brain.db (knowledge) — TONY học từ mỗi ảnh phân tích
    saved_k = _save_knowledge(p.name, facts, ocr_text)

    # ---- Soạn reply trung thực ----
    lines = [f"👁️ Phân tích ảnh `{p.name}`:"]

    lines.append(
        f"• Kích thước: {facts['width']}×{facts['height']} px ({facts['mode']}), "
        f"độ sáng TB {facts['brightness_mean']}/255"
    )
    colors = facts.get("dominant_colors_rgb64") or []
    if colors:
        c0 = colors[0]
        rgb = c0["rgb"]
        lines.append(
            f"• Màu chủ đạo: RGB({rgb[0]}, {rgb[1]}, {rgb[2]}) chiếm {c0['ratio']*100:.0f}% "
            f"(top{len(colors)})"
        )
    if facts.get("bright_regions"):
        lines.append(f"• Vùng rất sáng: {facts['bright_regions']} điểm (nguồn sáng/tiền cảnh)")
    if facts.get("dark_regions"):
        lines.append(f"• Vùng rất tối: {facts['dark_regions']} điểm (bóng/vật tối)")

    if ocr_text:
        snippet = ocr_text[:max_ocr_chars].replace("\n", " ⏎ ")
        lines.append(f"• Chữ nhận diện ({ocr_note}): “{snippet}”")
    else:
        lines.append(
            f"• Chữ nhận diện ({ocr_note}): **không có chữ** trong ảnh "
            f"(OCR quét toàn khung hình — đúng nếu ảnh chụp cảnh vật, không có text)."
        )

    if saved_k:
        lines.append(f"• 🧠 Đã lưu tri thức ảnh vào trí nhớ ({saved_k}).")
    lines.append(
        "ℹ️ Em phân tích được cấu trúc + chữ. Nhận diện vật thể (tủ lạnh, người...)"
        " cần huấn luyện model thị giác — anh duyệt sprint riêng em sẽ làm."
    )
    return "\n".join(lines)


def _save_knowledge(filename: str, facts: dict[str, Any], ocr_text: str) -> str | None:
    """Ghi tri thức rút từ ảnh vào brain.db — bảng `candidate_knowledge` (HÀNG ĐỢI
    CÁCH LY, đúng V7.0: learning ≠ deployment; tri thức tự học chờ review của
    owner mới lên semantic_memory). Additive, lỗi không làm hỏng phân tích chính.
    """
    try:
        db = BRAIN_ROOT / "data" / "brain.db"
        if not db.exists():
            return None
        parts = [
            f"Ảnh {filename}: {facts.get('width')}×{facts.get('height')}px, "
            f"độ sáng TB {facts.get('brightness_mean')}/255",
        ]
        colors = facts.get("dominant_colors_rgb64") or []
        if colors:
            rgb = colors[0]["rgb"]
            parts.append(f"màu chủ đạo RGB({rgb[0]},{rgb[1]},{rgb[2]}) {colors[0]['ratio']*100:.0f}%")
        if ocr_text:
            parts.append(f"chữ: {ocr_text[:150]}")
        statement = "[IMAGE] " + " — ".join(parts)
        conn = sqlite3.connect(str(db))
        try:
            import uuid
            from datetime import datetime as _dt, timezone as _tz
            row = {
                "id": uuid.uuid4().hex[:16],
                "created_at_utc": _dt.now(_tz.utc).isoformat(),
                "statement": statement[:2000],
                "source_ref": f"tony_vision:{filename}",
                "rationale": "TONY Vision tự phân tích ảnh theo lệnh DM — CHỜ REVIEW",
                "status": "quarantined",
            }
            cols = [r[1] for r in conn.execute("PRAGMA table_info(candidate_knowledge)").fetchall()]
            row = {k: v for k, v in row.items() if k in cols}
            if "statement" not in row or "id" not in row:
                return None
            conn.execute(
                f"INSERT INTO candidate_knowledge ({', '.join(row)}) "
                f"VALUES ({', '.join('?' for _ in row)})",
                list(row.values()),
            )
            conn.commit()
            return f"{len(ocr_text)} ký tự chữ + {len(facts)} chỉ số, chờ anh duyệt"
        finally:
            conn.close()
    except Exception:
        return None  # knowledge lưu fail không được làm hỏng phân tích chính
