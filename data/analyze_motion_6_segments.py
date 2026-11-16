"""Đo lại 6.mp4 ở 3 đoạn KHÁC NHAU (đầu/giữa/cuối) — đoạn 40% có thể là
khoảng lặng/camera tĩnh. Chuẩn hoá cùng phương pháp với video 3/4/5."""
import cv2
import numpy as np
import json

PATH = r"E:\BRAIN\Pi5\6.mp4"
cap = cv2.VideoCapture(PATH)
fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
h_full = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

def segment(start_frac, n_target=120):
    start_f = int(total * start_frac)
    step = max(1, int(fps / 2.0))
    head_s, torso_s, headx_s, means, micro = [], [], [], [], []
    v_head, h_head = [], []
    prev = None
    got = 0
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_f)
    fidx = start_f
    while got < n_target:
        ok, frame = cap.read()
        if not ok:
            break
        small = cv2.resize(frame, (640, int(640 * h_full / w)))
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        if prev is not None:
            fl = cv2.calcOpticalFlowFarneback(prev, gray, None, 0.5, 3, 15, 3, 5, 1.2, 0)
            mag = np.linalg.norm(fl, axis=2)
            hh = small.shape[0]
            scale = w / 640.0
            means.append(float(mag.mean() * scale))
            head_s.append(float(mag[: int(hh * 0.30)].mean() * scale))
            torso_s.append(float(mag[int(hh * 0.30): int(hh * 0.60)].mean() * scale))
            headx_s.append(float(np.abs(fl[: int(hh * 0.30), :, 0]).mean() * scale))
            v_head.append(float(np.abs(fl[: int(hh * 0.30), :, 1]).mean() * scale))
            h_head.append(float(np.abs(fl[: int(hh * 0.30), :, 0]).mean() * scale))
            micro.append(float((mag * scale < 3.0).mean()))
            got += 1
        prev = gray
        fidx += step
        if got < n_target:
            cap.set(cv2.CAP_PROP_POS_FRAMES, fidx)
    return means, head_s, torso_s, headx_s, v_head, h_head, micro

def fft_peaks(sig, dt=0.5, top=3):
    sig = np.array(sig) - np.mean(sig)
    if len(sig) < 20:
        return []
    fft = np.abs(np.fft.rfft(sig))
    freqs = np.fft.rfftfreq(len(sig), d=dt)
    if len(fft) < 4 or fft[1:].max() <= 0:
        return []
    order = np.argsort(fft[1:])[::-1][:top] + 1
    return [{"hz": round(float(freqs[k]), 4), "period_s": round(float(1 / freqs[k]), 2),
             "power": round(float(fft[k]), 1)} for k in order if freqs[k] > 0.01]

out = {}
for name, frac in [("dau_5pct", 0.05), ("giua_60pct", 0.60), ("cuoi_92pct", 0.92)]:
    means, head_s, torso_s, headx_s, v_head, h_head, micro = segment(frac)
    out[name] = {
        "flow_mean": round(float(np.mean(means)), 2),
        "flow_p95": round(float(np.percentile(means, 95)), 2),
        "head_mean": round(float(np.mean(head_s)), 2),
        "torso_mean": round(float(np.mean(torso_s)), 2),
        "head_to_torso": round(float(np.mean(head_s) / max(np.mean(torso_s), 1e-6)), 2),
        "head_v_over_h": round(float(np.mean(v_head) / max(np.mean(h_head), 1e-6)), 2),
        "micro_still": round(float(np.mean(micro)), 2),
        "head_cycles": fft_peaks(head_s),
    }
    print(name, json.dumps(out[name], ensure_ascii=False))
cap.release()

with open(r"E:\BRAIN\data\motion_6_segments.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print("SAVED")
