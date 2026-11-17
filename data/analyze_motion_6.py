"""Phân tích 6.mp4 — GỘP 1 LẦN: metadata + flow toàn khung + flow vùng + FFT chu kỳ."""
import cv2
import numpy as np
import json

PATH = r"E:\BRAIN\Pi5\6.mp4"

cap = cv2.VideoCapture(PATH)
if not cap.isOpened():
    print(json.dumps({"error": "cannot open"}))
    raise SystemExit(1)

fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
h_full = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
dur = total / fps if fps else 0.0
print(json.dumps({"w": w, "h": h_full, "fps": round(fps, 2), "frames": total,
                  "duration_s": round(dur, 1)}))

start_f = int(total * 0.4)
step = max(1, int(fps / 2.0))
n_target = 200

flow_means, v_head, h_head, v_torso, h_torso = [], [], [], [], []
head_s, torso_s, headx_s, micro = [], [], [], []
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
        flow_means.append(float(mag.mean() * scale))
        head = mag[: int(hh * 0.30)]
        torso = mag[int(hh * 0.30): int(hh * 0.60)]
        arms = np.concatenate([
            mag[int(hh * 0.30): int(hh * 0.75), : int(640 * 0.25)],
            mag[int(hh * 0.30): int(hh * 0.75), int(640 * 0.75):],
        ], axis=1)
        head_s.append(float(head.mean() * scale))
        torso_s.append(float(torso.mean() * scale))
        headx_s.append(float(np.abs(fl[: int(hh * 0.30), :, 0]).mean() * scale))
        v_head.append(float(np.abs(fl[: int(hh * 0.30), :, 1]).mean() * scale))
        h_head.append(float(np.abs(fl[: int(hh * 0.30), :, 0]).mean() * scale))
        v_torso.append(float(np.abs(fl[int(hh * 0.30): int(hh * 0.60), :, 1]).mean() * scale))
        h_torso.append(float(np.abs(fl[int(hh * 0.30): int(hh * 0.60), :, 0]).mean() * scale))
        micro.append(float((mag * scale < 3.0).mean()))
        got += 1
    prev = gray
    fidx += step
    if got < n_target:
        cap.set(cv2.CAP_PROP_POS_FRAMES, fidx)
cap.release()

def fft_peaks(sig, dt=0.5, top=4):
    sig = np.array(sig) - np.mean(sig)
    if len(sig) < 20:
        return []
    fft = np.abs(np.fft.rfft(sig))
    freqs = np.fft.rfftfreq(len(sig), d=dt)
    if len(fft) < 4 or fft[1:].max() <= 0:
        return []
    order = np.argsort(fft[1:])[::-1][:top] + 1
    return [{"hz": round(float(freqs[k]), 4),
             "period_s": round(float(1 / freqs[k]), 2),
             "power": round(float(fft[k]), 1)} for k in order if freqs[k] > 0.01]

arr = np.array(flow_means) if flow_means else np.array([0.0])
out = {
    "meta": {"w": w, "h": h_full, "fps": round(fps, 2), "frames": total, "duration_s": round(dur, 1)},
    "sampled": got,
    "flow_mean_px": round(float(arr.mean()), 2),
    "flow_p95_px": round(float(np.percentile(arr, 95)), 2),
    "still_ratio": round(float((arr < 1.0).mean()), 2),
    "head_flow_mean": round(float(np.mean(head_s)), 2),
    "torso_flow_mean": round(float(np.mean(torso_s)), 2),
    "head_to_torso": round(float(np.mean(head_s) / max(np.mean(torso_s), 1e-6)), 2),
    "head_v_over_h": round(float(np.mean(v_head) / max(np.mean(h_head), 1e-6)), 2),
    "torso_v_over_h": round(float(np.mean(v_torso) / max(np.mean(h_torso), 1e-6)), 2),
    "micro_still_ratio": round(float(np.mean(micro)), 2),
    "head_cycles": fft_peaks(head_s),
    "torso_cycles": fft_peaks(torso_s),
    "head_sway_cycles": fft_peaks(headx_s),
}
with open(r"E:\BRAIN\data\motion_6_analysis.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))
print("SAVED")
