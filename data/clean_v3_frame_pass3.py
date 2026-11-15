# -*- coding: utf-8 -*-
"""(16/11/2026 v6full_1511) Pass 3 — nhắm sót màu line gốc trong inset<60.

Pass 2 để lại ~610px màu line (48,97,126) ở mép dưới (ref bị tint glow).
Pass 3: mọi px khớp màu line ±tol trong inset<60 → thay bằng nền sạch lấy từ
inset 70-90 CÙNG hàng/cột (vectorized). Chạy 1 lần cho đủ 11 file.
"""
from pathlib import Path

import numpy as np
from PIL import Image

DIR = Path(__file__).resolve().parents[1] / "src" / "quan_ai_brain" / "web" / "static" / "assets" / "avatar"


def main():
    for f in sorted(DIR.glob("avatar_v3_*.png")):
        arr = np.array(Image.open(f).convert("RGB"))
        h, w, _ = arr.shape
        inset = np.minimum.reduce([
            np.arange(w)[None, :].repeat(h, 0), np.arange(h)[:, None].repeat(w, 1),
            (w - 1 - np.arange(w))[None, :].repeat(h, 0), (h - 1 - np.arange(h))[:, None].repeat(w, 1)])
        r, g, b = arr[:, :, 0].astype(int), arr[:, :, 1].astype(int), arr[:, :, 2].astype(int)
        line = (g > 90) & (b > 90) & (r < 110) & (g + b - 2 * r > 40) & (inset < 60)
        n_total = int(line.sum())
        if n_total == 0:
            print(f"{f.name:38s} sạch sẵn (0)")
            continue
        # Nền sạch: trung bình inset 70-90 theo hàng (cho px gần mép dọc)
        # và theo cột (cho px gần mép ngang). Dùng hàng cho mọi trường hợp —
        # nội dung inset 70-90 gần như luôn là nền navy.
        inner_mask = (inset >= 70) & (inset <= 90)
        row_ref = np.zeros((h, 3))
        for y in range(h):
            sel = arr[y, inner_mask[y]]
            if sel.size:
                row_ref[y] = sel.mean(axis=0)
        ys, xs = np.where(line)
        # Quyết định theo trục gần mép nhất: px gần mép ngang → ref theo hàng
        # (đúng bản chất), px gần mép dọc → ref theo cột.
        col_ref = np.zeros((w, 3))
        inner_mask_c = inner_mask.T
        for x in range(w):
            sel = arr[inner_mask_c[x], x]
            if sel.size:
                col_ref[x] = sel.mean(axis=0)
        near_top_bottom = np.minimum(ys, h - 1 - ys) <= np.minimum(xs, w - 1 - xs)
        arr[ys[near_top_bottom], xs[near_top_bottom]] = row_ref[ys[near_top_bottom]]
        arr[ys[~near_top_bottom], xs[~near_top_bottom]] = col_ref[xs[~near_top_bottom]]
        Image.fromarray(arr).save(f, optimize=True)
        # verify
        r, g, b = arr[:, :, 0].astype(int), arr[:, :, 1].astype(int), arr[:, :, 2].astype(int)
        remain = int(((g > 90) & (b > 90) & (r < 110) & (g + b - 2 * r > 40) & (inset < 60)).sum())
        print(f"{f.name:38s} đổi: {n_total:5d} → còn: {remain}")


if __name__ == "__main__":
    main()
