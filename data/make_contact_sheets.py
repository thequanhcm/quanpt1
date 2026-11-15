"""Gộp frame trích từ vi1/vi2/v5 thành contact sheet 3x2 (có nhãn mốc thời gian)
để vision_analyze đọc catalogue cử chỉ trong 1 lần gọi/video."""
import json
import os

from PIL import Image, ImageDraw

FR = "data/frames_vi"
SHEET = "data/frames_vi_sheets"
os.makedirs(SHEET, exist_ok=True)

cat = json.load(open("data/gesture_catalog_vi_videos.json", encoding="utf-8"))

for tag, info in cat.items():
    frames = info.get("frames", [])
    if not frames:
        continue
    cell_w, cell_h = 640, 360
    sheet = Image.new("RGB", (cell_w * 2, cell_h * 3), (10, 12, 24))
    draw = ImageDraw.Draw(sheet)
    for i, fname in enumerate(frames[:6]):
        fp = os.path.join(FR, fname)
        if not os.path.exists(fp):
            continue
        im = Image.open(fp).convert("RGB")
        im.thumbnail((cell_w, cell_h - 28))
        x = (i % 2) * cell_w
        y = (i // 2) * cell_h
        sheet.paste(im, (x + (cell_w - im.width) // 2, y + 28))
        ts = fname.split("_f")[1].rstrip(".jpg") if "_f" in fname else "?"
        try:
            sec = int(ts) / 10.0
            label = f"{tag} — t={sec/60:.0f}p{sec%60:04.1f}s"
        except Exception:
            label = f"{tag} — {fname}"
        draw.text((x + 8, y + 6), label, fill=(125, 211, 252))
    out = os.path.join(SHEET, f"sheet_{tag}.jpg")
    sheet.save(out, quality=82)
    print("SAVED", out, sheet.size)
