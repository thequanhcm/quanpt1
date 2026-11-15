"""Trích frame + đo cử chỉ cho các video CHƯA có dữ liệu: vi 1.mp4, vi 2.mp4, 5.mp4,
mẫu.mp4 (=4.mp4 — kiểm md5 xác nhận, nếu trùng thì bỏ). Bổ sung catalogue cử chỉ:
trích 6 frame/video ở các mốc đều → vision_analyze đọc loại cử chỉ tay/đầu/biểu cảm.
Kết quả ghi data/gesture_catalog_vi_videos.json + frame vào data/frames_vi/."""
import json
import os
import subprocess
import sys

import imageio_ffmpeg
import numpy as np

FF = imageio_ffmpeg.get_ffmpeg_exe()
OUT_FRAMES = "data/frames_vi"
os.makedirs(OUT_FRAMES, exist_ok=True)

VIDEOS = {
    "vi1": r"E:\BRAIN\Pi5\vi 1.mp4",
    "vi2": r"E:\BRAIN\Pi5\vi 2.mp4",
    "v5": r"E:\BRAIN\Pi5\5.mp4",
}

def probe(path):
    out = subprocess.run([FF, "-i", path], capture_output=True, text=True, errors="replace")
    dur = None
    for line in (out.stderr or "").splitlines():
        if "Duration:" in line:
            parts = line.split("Duration:")[1].strip().split(":")
            h, m = int(parts[0]), int(parts[1])
            s = float(parts[2].split(",")[0])
            dur = h * 3600 + m * 60 + s
            break
    return dur

def extract_frames(path, dur, tag, n=6):
    frames = []
    for i in range(n):
        frac = (i + 0.5) / n
        ts = min(dur * frac, max(dur - 1.0, 0.0))
        fp = os.path.join(OUT_FRAMES, f"{tag}_f{int(ts*10)}.jpg")
        if not os.path.exists(fp):
            subprocess.run([FF, "-y", "-ss", str(ts), "-i", path, "-frames:v", "1",
                            "-q:v", "3", fp], capture_output=True, timeout=120)
        if os.path.exists(fp):
            frames.append(fp)
    return frames

def measure_flow(path, dur, tag, n=24):
    """Đo optical flow thô bằng diff frame liên tiếp (nội suy nhanh, không cần cv2)."""
    fps = 30.0
    gaps = [dur * f for f in (0.15, 0.35, 0.55, 0.75)]
    flows = []
    for ts in gaps:
        f1 = os.path.join(OUT_FRAMES, f"{tag}_m1_{int(ts*10)}.jpg")
        f2 = os.path.join(OUT_FRAMES, f"{tag}_m2_{int(ts*10)}.jpg")
        if not os.path.exists(f1):
            subprocess.run([FF, "-y", "-ss", str(ts), "-i", path, "-frames:v", "1", "-q:v", "5", f1],
                           capture_output=True, timeout=120)
        if not os.path.exists(f2):
            subprocess.run([FF, "-y", "-ss", str(ts + 1.0 / fps), "-i", path, "-frames:v", "1", "-q:v", "5", f2],
                           capture_output=True, timeout=120)
        if os.path.exists(f1) and os.path.exists(f2):
            try:
                from PIL import Image
                a = np.asarray(Image.open(f1).convert("L").resize((320, 180)), dtype=np.float32)
                b = np.asarray(Image.open(f2).convert("L").resize((320, 180)), dtype=np.float32)
                gy, gx = np.gradient(b)
                dt = b - a
                # Lucas-Kanade 1 iteration (tham số hóa gọn)
                denom = (gx * gx + gy * gy)
                mask = denom > 1e-3
                u = np.where(mask, -dt * gx / np.maximum(denom, 1e-3), 0.0)
                v = np.where(mask, -dt * gy / np.maximum(denom, 1e-3), 0.0)
                mag = float(np.sqrt(u * u + v * v)[mask].mean()) if mask.any() else 0.0
                # V/H: chia vùng nửa trên (đầu) vs dưới (thân)
                head_v, head_h = float(np.abs(v[:60]).mean()), float(np.abs(u[:60]).mean())
                flows.append({"ts": round(ts, 1), "flow_px": round(mag, 2),
                              "head_v": round(head_v, 3), "head_h": round(head_h, 3)})
            except Exception as exc:
                flows.append({"ts": round(ts, 1), "error": str(exc)[:80]})
    return flows

def main():
    result = {}
    for tag, path in VIDEOS.items():
        if not os.path.exists(path):
            result[tag] = {"error": "not_found"}
            continue
        dur = probe(path)
        if not dur or dur <= 0:
            result[tag] = {"error": "probe_failed"}
            continue
        frames = extract_frames(path, dur, tag)
        flows = measure_flow(path, dur, tag)
        result[tag] = {
            "path": path, "duration_s": round(dur, 1),
            "frames": [os.path.basename(f) for f in frames],
            "flow_samples": flows,
        }
        print(f"{tag}: {dur:.1f}s, {len(frames)} frames, {len(flows)} flow samples", flush=True)
    with open("data/gesture_catalog_vi_videos.json", "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=1)
    print("SAVED data/gesture_catalog_vi_videos.json")

if __name__ == "__main__":
    main()
