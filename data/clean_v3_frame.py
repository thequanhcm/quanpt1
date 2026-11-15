# -*- coding: utf-8 -*-
"""(16/11/2026 v6full_1511) Xóa khung viền cyan in sẵn (bake) trong portrait v3.

Owner duyệt "duyệt để làm" cho Hướng 2 (giao diện full như 6.mp4). Đo đạc phát
hiện CẢ 11 portrait v3 có khung cyan ~2px (#4AA5C7-ish) inset ~15-20px, bo góc
R~30px, chạy đủ 4 cạnh (mật độ 84-86% mỗi cạnh). Khung nằm trong VÙNG NỀN ngoài
nhân vật (nội dung nhân vật bắt đầu ~x106/x790) nên xóa bằng cách chiếu màu
nền liền trong vào dải viền (inpaint hàng loạt theo trục) — KHÔNG đụng vào vùng
mặt (EYES/MOUTH_BOX y367-509 / y609-732 an toàn tuyệt đối).

Kỹ thuật: với mỗi hàng/cột trong dải mép (band 0..42), tìm pixel "viền cyan"
(g/b cao, r thấp, chênh g+b-2r > 40) rồi thay bằng màu trung bình của đoạn
nền SẠCH kế bên trong (offset 6px, bỏ qua pixel cyan khác). Xử lý 4 mép độc
lập. Không resize, không đổi số pixel — chỉ recolor.

Chạy: python data/clean_v3_frame.py [--dry-run]
Kết quả: ghi đè in-place vào src/quan_ai_brain/web/static/assets/avatar/
(bản gốc đã có trên git — rollback bằng git checkout).
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

DIR = Path(__file__).resolve().parents[1] / "src" / "quan_ai_brain" / "web" / "static" / "assets" / "avatar"
BAND = 42          # dải mép cần quét (viền inset 15-20px + glow ~5px + dự phòng)
THRESH_DIFF = 40   # g+b-2r vượt ngưỡng = cyan (viền #4AA5C7 có diff ~130)
OFFSET = 6         # khoảng cách lấy màu nền tham chiếu trong viền cyan


def fix_edge(arr, axis, side, diag_mask=None):
    """Recolor pixel cyan trong dải mép bằng màu nền liền trong. axis 0=ngang(hàng), 1=dọc(cột)."""
    h, w, _ = arr.shape
    n = h if axis == 0 else w
    r = arr[:, :, 0].astype(int)
    g = arr[:, :, 1].astype(int)
    b = arr[:, :, 2].astype(int)
    cyan = (g > 90) & (b > 90) & (r < 110) & (g + b - 2 * r > THRESH_DIFF)
    if diag_mask is not None:
        cyan &= diag_mask
    changed = 0
    for i in range(n):
        line = cyan[i, :] if axis == 0 else cyan[:, i]
        idx = np.where(line)[0]
        # Giới hạn trong band mép
        if axis == 0:
            band_px = idx[idx < BAND] if side == 0 else idx[idx >= w - BAND]
        else:
            band_px = idx[idx < BAND] if side == 0 else idx[idx >= h - BAND]
        if band_px.size == 0:
            continue
        for p in band_px:
            # Quét theo chiều vuông góc tìm màu nền sạch
            if axis == 0:
                dirs = range(p + OFFSET, w) if side == 0 else range(p - OFFSET, -1, -1)
                def px(t):
                    return arr[i, t, :].astype(int), cyan[i, t]
            else:
                dirs = range(p + OFFSET, h) if side == 0 else range(p - OFFSET, -1, -1)
                def px(t):
                    return arr[t, i, :].astype(int), cyan[t, i]
            found = None
            for t in dirs:
                col, is_cyan = px(t)
                if not is_cyan and col.sum() < 250:  # nền tối navy
                    found = col
                    break
            if found is None:
                continue
            if axis == 0:
                arr[i, p, :] = found
            else:
                arr[p, i, :] = found
            changed += 1
    return changed


def clean_file(path):
    im = Image.open(path).convert("RGB")
    arr = np.array(im)
    before = arr.copy()
    r, g, b = arr[:, :, 0].astype(int), arr[:, :, 1].astype(int), arr[:, :, 2].astype(int)
    total_cyan = ((g > 90) & (b > 90) & (r < 110) & (g + b - 2 * r > THRESH_DIFF)).sum()

    changed = 0
    changed += fix_edge(arr, 0, 0)   # hàng trên
    changed += fix_edge(arr, 0, 1)   # hàng dưới
    changed += fix_edge(arr, 1, 0)   # cột trái
    changed += fix_edge(arr, 1, 1)   # cột phải

    # Pass 2: góc — pixel cyan sót trong khối góc BAND×BAND (bo góc R30)
    r, g, b = arr[:, :, 0].astype(int), arr[:, :, 1].astype(int), arr[:, :, 2].astype(int)
    cyan = (g > 90) & (b > 90) & (r < 110) & (g + b - 2 * r > THRESH_DIFF)
    corners = [(slice(0, BAND), slice(0, BAND)), (slice(0, BAND), slice(-BAND, None)),
               (slice(-BAND, None), slice(0, BAND)), (slice(-BAND, None), slice(-BAND, None))]
    for cs in corners:
        region = cyan[cs]
        ys, xs = np.where(region)
        if ys.size == 0:
            continue
        # Tham chiếu: màu nền từ điểm giữa khối góc lệch vào trong
        y0 = 0 if cs[0].start is None or cs[0].start >= 0 and cs[0].stop == BAND else h - 1
        ref = arr[BAND - 10, BAND - 10] if (cs[0].stop == BAND and cs[1].stop == BAND) else arr[h - BAND + 10, w - BAND + 10]
        sub = arr[cs]
        sub[ys, xs] = ref
        arr[cs] = sub
        changed += ys.size

    after = ((arr[:, :, 2].astype(int) + arr[:, :, 1].astype(int) - 2 * arr[:, :, 0].astype(int) > THRESH_DIFF)
             & (arr[:, :, 1] > 90) & (arr[:, :, 0] < 110)).sum()
    diff = np.abs(arr.astype(int) - before.astype(int)).sum()
    Image.fromarray(arr).save(path, optimize=True)
    return total_cyan, after, changed, diff


def main():
    dry = "--dry-run" in sys.argv
    files = sorted(DIR.glob("avatar_v3_*.png"))
    print(f"{'file':40s} {'cyan_trước':>10s} {'cyan_sau':>9s} {'px_đổi':>8s} {'diff':>8s}")
    for f in files:
        if dry:
            im = Image.open(f).convert("RGB")
            arr = np.array(im)
            r, g, b = arr[:, :, 0].astype(int), arr[:, :, 1].astype(int), arr[:, :, 2].astype(int)
            n = ((g > 90) & (b > 90) & (r < 110) & (g + b - 2 * r > THRESH_DIFF)).sum()
            print(f"{f.name:40s} {n:10d} {'(dry)':>9s}")
            continue
        tc, ta, ch, df = clean_file(f)
        print(f"{f.name:40s} {tc:10d} {ta:9d} {ch:8d} {df:8d}")


if __name__ == "__main__":
    main()
