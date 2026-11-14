#!/usr/bin/env python3
"""(14/11/2026) v2: Crop emotion sheet -> xóa nhãn chữ (inpaint) -> resize cover 1024.
Cover: scale lấp đầy 1024x1024, cắt phần thừa (ưu tiên giữ mặt/vai — cắt nhiều ở trên).
"""
import cv2
import numpy as np
from PIL import Image
import os, json

WS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(WS, "bao cao xay dung he thong", "avatar")
OUT = os.path.join(WS, "src", "quan_ai_brain", "web", "static", "assets", "avatar")
os.makedirs(OUT, exist_ok=True)

img1 = Image.open(os.path.join(SRC, "1.png")).convert("RGB")
img2 = Image.open(os.path.join(SRC, "2.png")).convert("RGB")

# (box trong ảnh gốc, cần bỏ nhãn?)
cells = [
    # ảnh 1 — 4 ô 1024 vuông
    ("thu_thai",    img1, (0, 0, 1024, 1024)),
    ("chop_mat",    img1, (1024, 0, 2048, 1024)),
    ("nghieng_dau", img1, (0, 1024, 1024, 2048)),
    ("dang_noi",    img1, (1024, 1024, 2048, 2048)),
    # ảnh 2 — hàng 1: 3 ô 618x768
    ("ngac_nhien",  img2, (0, 0, 618, 768)),
    ("tap_trung",   img2, (626, 0, 1238, 768)),
    ("buon_ba",     img2, (1246, 0, 1856, 768)),
    # ảnh 2 — hàng 2: 2 ô 924x756
    ("tuc_gian",    img2, (0, 776, 924, 1532)),
    ("lang_nghe",   img2, (932, 776, 1856, 1532)),
    # ảnh 2 — hàng 3: 2 ô 924x764
    ("vui_suong",   img2, (0, 1540, 924, 2304)),
    ("mo_mong",     img2, (932, 1540, 1856, 2304)),
]

B = 10  # lùi vào tránh viền cyan sheet

def remove_label(arr):
    """Inpaint vùng nhãn trắng góc trên trái (0-32% w, 0-16% h)."""
    h, w = arr.shape[:2]
    x1, y1 = int(w * 0.34), int(h * 0.17)
    roi = arr[0:y1, 0:x1]
    gray = cv2.cvtColor(roi, cv2.COLOR_RGB2GRAY)
    # chữ trắng sáng > 185
    mask = (gray > 175).astype(np.uint8) * 255
    mask = cv2.dilate(mask, np.ones((9, 9), np.uint8), iterations=2)
    n = int(mask.sum() / 255)
    if n > 300:  # có chữ thật mới inpaint
        m2 = np.zeros(arr.shape[:2], np.uint8)
        m2[0:y1, 0:x1] = mask
        bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
        bgr = cv2.inpaint(bgr, m2, 7, cv2.INPAINT_TELEA)
        arr = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    return arr, n

def cover_1024(arr):
    """Scale-to-cover 1024x1024, cắt phần thừa: cắt nhiều phía trên (trống), ít phía dưới."""
    h, w = arr.shape[:2]
    scale = max(1024 / w, 1024 / h)
    nw, nh = int(round(w * scale)), int(round(h * scale))
    r = cv2.resize(arr, (nw, nh), interpolation=cv2.INTER_LANCZOS4)
    ox, oy = (nw - 1024) // 2, 0
    # cắt ngang: chia đều; cắt dọc: 65% phía trên, 35% phía dưới (giữ mặt+vai)
    oy = int((nh - 1024) * 0.65)
    if nh <= 1024:
        oy = 0
    return r[oy:oy + 1024, ox:ox + 1024]

report = {}
for name, img, (x0, y0, x1, y1) in cells:
    c = np.asarray(img.crop((x0 + B, y0 + B, x1 - B, y1 - B)))
    c, npx = remove_label(c)
    c = cover_1024(c)
    out = os.path.join(OUT, f"avatar_v3_{name}.png")
    Image.fromarray(c).save(out, optimize=True)
    report[name] = {"label_px": npx, "size": f"{c.shape[1]}x{c.shape[0]}"}
    print(f"{name}: label_px={npx} -> {out.split(chr(92))[-1]}")

print(json.dumps(report, indent=0))
