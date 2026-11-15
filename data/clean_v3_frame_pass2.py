# -*- coding: utf-8 -*-
"""(16/11/2026 v6full_1511) Pass 2 VECTORIZED — quét sót glow viền, dải mép 60px.

Pass 1 (clean_v3_frame.py) đã trừ khung cyan đậm. Pass 2 nới ngưỡng (r<135,
diff>25) CHỈ trong dải mép 60px, thay bằng màu nền tham chiếu vectorized
(không vòng lặp per-pixel). Lặp tối đa 8 vòng tới khi sạch.

Chạy: python data/clean_v3_frame_pass2.py
"""
from pathlib import Path

import numpy as np
from PIL import Image

DIR = Path(__file__).resolve().parents[1] / "src" / "quan_ai_brain" / "web" / "static" / "assets" / "avatar"
BAND = 60


def cyan_mask(arr):
    r = arr[:, :, 0].astype(int)
    g = arr[:, :, 1].astype(int)
    b = arr[:, :, 2].astype(int)
    return (g > 80) & (b > 80) & (r < 135) & (g + b - 2 * r > 25)


def band_ref(arr, side):
    """Màu nền tham chiếu vectorized cho từng side (trung bình dải sạch trong)."""
    if side == 0:   # trên: trung bình y=BAND+10..BAND+30
        return arr[BAND + 10:BAND + 30, :, :].mean(axis=0)
    if side == 1:   # dưới
        return arr[-(BAND + 10):-(BAND + 30):-1, :, :].mean(axis=0)
    if side == 2:   # trái
        return arr[:, BAND + 10:BAND + 30, :].mean(axis=1)
    return arr[:, -(BAND + 10):-(BAND + 30):-1, :].mean(axis=1)  # phải


def clean_file(path):
    arr = np.array(Image.open(path).convert("RGB"))
    h, w, _ = arr.shape
    total = 0
    for _ in range(8):
        cyan = cyan_mask(arr)
        changed = 0
        # Trên
        m = cyan[:BAND, :]
        if m.any():
            ref = band_ref(arr, 0)  # (w,3)
            ys, xs = np.where(m)
            arr[ys, xs] = ref[xs]
            changed += len(ys)
        # Dưới
        m = cyan[-BAND:, :]
        if m.any():
            ref = band_ref(arr, 1)
            ys, xs = np.where(m)
            arr[h - BAND + ys, xs] = ref[xs]
            changed += len(ys)
        # Trái
        m = cyan[:, :BAND]
        if m.any():
            ref = band_ref(arr, 2)  # (h,3)
            ys, xs = np.where(m)
            arr[ys, xs] = ref[xs]
            changed += len(ys)
        # Phải
        m = cyan[:, -BAND:]
        if m.any():
            ref = band_ref(arr, 3)
            ys, xs = np.where(m)
            arr[ys, w - BAND + xs] = ref[xs]
            changed += len(ys)
        total += changed
        if changed == 0:
            break
    Image.fromarray(arr).save(path, optimize=True)
    return total


def main():
    print(f"{'file':38s} {'px_đổi':>8s} {'cyan_mép_còn':>13s}")
    for f in sorted(DIR.glob("avatar_v3_*.png")):
        ch = clean_file(f)
        arr = np.array(Image.open(f).convert("RGB"))
        m = cyan_mask(arr)
        edges = int(m[:BAND, :].sum() + m[-BAND:, :].sum() + m[:, :BAND].sum() + m[:, -BAND:].sum())
        print(f"{f.name:38s} {ch:8d} {edges:13d}")


if __name__ == "__main__":
    main()
