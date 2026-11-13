#!/usr/bin/env python3
"""QUAN AI BRAIN — Wake Word Service cho Pi 5 (24/7, chạy ngoài kiosk).

Nghe liên tục qua mic USB (Jieli), nhận tiếng Việt offline bằng Vosk.
Khi nghe thấy "CHERRY ơi" (hoặc "Cherry", "Hi Cherry"...):
  1. POST http://127.0.0.1:8768/api/kiosk/control {"action":"wake_by_voice"}
     → daemon _wake_screen: bật màn hình + launch kiosk + avatar ACTIVE.
  2. Kiosk chạy → wake_engine.js (Web Speech) tiếp quản hội thoại.

(Rename 06/11/2026 theo lệnh owner: wake word TONY ơi → CHERRY ơi.)

Chạy bằng systemd quan_ai_wake.service (user quanpt1), tự restart nếu lỗi.
Mic bị daemon kiosk giữ? Vosk mở cùng thiết bị qua ALSA default (dsnoop PipeWire)
— nếu "Device busy" thì service chờ 5s thử lại (daemon kiosk chỉ giữ mic khi
wake word trong kiosk BẬT; auto-sleep tắt kiosk → mic tự do).
"""
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from vosk import Model, KaldiRecognizer

MODEL_PATH = str(Path.home() / "vosk-model-small-vn-0.3")
KIOSK_API = "http://127.0.0.1:8768"
SAMPLE_RATE = 16000
# Model small-vn nhận "Cherry ơi" thành nhiều biến thể gần giống — dùng bộ khớp
# RỘNG (đã kiểm chứng cách khớp với "Tony ơi" từ 31/10). Wake là hành động
# vô hại (chỉ bật màn hình) nên chấp nhận false-positive thấp.
WAKE_PHRASES = (
    # (11/11/2026) OWNER CHỐT BỘ TỪ ĐÁNH THỨC — CHỈ CHERRY, bỏ hết TONY quá độ:
    # "Cherry ơi" / "Cherry" / "Cherry à" + biến thể Vosk hay trả về
    # ("cherry" → "cherry"/"cheri"/"ché ri"/"che ri"):
    "cherry", "cherry ơi", "cherry oi", "cherry à", "cherry a",
    "cheri", "cheri ơi", "cheri oi", "cheri à", "cheri a",
    "ché ri", "ché ri ơi", "ché ri à",
    "che ri", "che ri ơi", "che ri oi", "che ri à", "che ri a",
    "chè ri", "chè ri ơi", "chè ri à",
)
# Từ khóa phụ trong lúc nghe: "ngủ đi" → sleep ngay (đồng bộ lệnh DM)
SLEEP_PHRASES = ("ngủ đi", "ngu di", "ngu ngu", "đi ngủ")

def wake_kiosk():
    try:
        req = urllib.request.Request(
            f"{KIOSK_API}/api/kiosk/control",
            data=json.dumps({"action": "wake_by_voice", "source": "vosk"}).encode(),
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            print(f"[WAKE] gửi wake_by_voice → {data.get('success')}", flush=True)
            return True
    except Exception as exc:
        print(f"[WAKE] lỗi gọi kiosk API: {exc}", flush=True)
        return False

def sleep_kiosk():
    try:
        req = urllib.request.Request(
            f"{KIOSK_API}/api/kiosk/control",
            data=json.dumps({"action": "pause"}).encode(),
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            resp.read()
        print("[WAKE] 'ngủ đi' → pause", flush=True)
    except Exception as exc:
        print(f"[WAKE] lỗi pause: {exc}", flush=True)

# ---------------------------------------------------------------------------
# (13/11/2026) LỌC TẠP ÂM + ÂM THANH MÔI TRƯỜNG — 3 lớp DSP
# Owner yêu cầu sau buổi đo: mic Jieli RMS 130-205 khi owner gọi (≈ −48dBFS),
# TV/nhạc nền 122-147 → SNR≈0dB. Các lớp dưới giúp Vosk chỉ nhận tiếng nói.
# ---------------------------------------------------------------------------

class NoiseFloorEstimator:
    """Bám mức tạp âm nền phòng bằng trung bình trượt bất đối xứng.

    - Nền thấp dần (phòng im hơn): bám NHANH (down factor) — tránh kẹt
      floor cao làm gate nuốt tiếng nói.
    - Tiếng nói/tiếng to: KHÔNG được kéo floor lên nhanh (up factor nhỏ,
      và chỉ khi RMS > floor × 1.8) — tiếng nói chỉ 0.25-2s không đủ kéo.
    """

    def __init__(self, init: float = 150.0, up: float = 0.002,
                 down: float = 0.08) -> None:
        self.level = init
        self._up = up
        self._down = down

    def update(self, rms: float) -> float:
        if rms < self.level:
            self.level += (rms - self.level) * self._down
        else:
            # Nền tăng: bám chậm nhưng CHẮC CHẮN (TV bật lâu = nền mới);
            # tiếng nói ngắn 0.25-2s chỉ nâng floor <1% → vô hại.
            self.level += (rms - self.level) * self._up
        return self.level

    def is_speech(self, rms: float, snr: float = 2.2,
                  absolute_min: float = 90.0) -> bool:
        return rms >= max(absolute_min, self.level * snr)


def make_highpass(cutoff_hz: float = 180.0, rate: int = 16000):
    """Trả hàm lọc high-pass 1 bậc (single-pole) cắt tần số trầm.

    Cắt rumble/HVAC/TV-bass (<180Hz) nhưng giữ dải giọng nói (300-3400Hz).
    Dùng danh sách hệ số tĩnh — không cấp phát trong vòng lặp nóng.
    """
    import math as _math
    rc = 1.0 / (2.0 * _math.pi * cutoff_hz)
    dt = 1.0 / rate
    alpha = rc / (rc + dt)
    state = {"prev_in": 0.0, "prev_out": 0.0}

    def _filter(x: float) -> float:
        y = alpha * (state["prev_out"] + x - state["prev_in"])
        state["prev_in"] = x
        state["prev_out"] = y
        return y

    return _filter


# instance dùng chung cho vòng lặp chính + test
_hp = make_highpass()
_noise = NoiseFloorEstimator(init=140.0)


def _agc_boost(samples, floor_level: float = 100.0):
    """AGC normalize về 9000, gain max 24x, clip guard 32000 (test helper)."""
    import math as _math
    if not samples:
        return samples
    rms = _math.sqrt(sum(x * x for x in samples) / len(samples))
    base = max(rms, 90.0, floor_level)
    gain = min(24.0, 9000.0 / max(base, 1))
    out = samples
    for _i in range(len(out)):
        v = int(out[_i] * gain)
        # clip guard LUÔN áp (kể cả gain<1) — đảm bảo biên ≤ ±32000
        out[_i] = 32000 if v > 32000 else (-32000 if v < -32000 else v)
    return out


def _process_chunk(chunk: bytes, noise_est: NoiseFloorEstimator):
    """Xử lý 1 chunk PCM16 → (chunk_mới|None, gated?).

    Pipeline: high-pass → đo RMS → gate theo SNR → trả chunk đã lọc
    (chưa AGC — AGC áp trong vòng lặp chính sau gate).
    Dùng cho test; vòng lặp chính nội tuyến 3 lớp để tránh overhead.
    """
    import array as _array, math as _math
    samples = _array.array("h")
    samples.frombytes(chunk)
    if not samples:
        return None, True
    samples = _array.array("h", [
        int(max(-32768, min(32767, v * 32768)))
        for v in map(_hp, (s / 32768.0 for s in samples))
    ])
    rms = _math.sqrt(sum(x * x for x in samples) / len(samples))
    noise_est.update(rms)
    if not noise_est.is_speech(rms):
        return None, True
    return samples.tobytes(), False


def main():
    print(f"[WAKE] nạp model {MODEL_PATH} ...", flush=True)
    model = Model(MODEL_PATH)
    recognizer = None

    # Ghi âm qua arecord subprocess (đơn giản, tránh dependency pyaudio):
    import shutil
    if not shutil.which("arecord"):
        print("[WAKE] KHÔNG có arecord — thoát", flush=True)
        return 1

    import io
    proc = None
    buf = io.BytesIO()
    print("[WAKE] sẵn sàng — lắng nghe 'CHERRY ơi'", flush=True)

    # Ghi qua pw-record (PipeWire) — device USB bị PipeWire giữ độc quyền nên
    # arecord plughw:2,0 luôn 'Device busy'. pw-record đọc từ source node mặc
    # định (Jieli UACDemoV1.0 Mono — priority.session 2000) hoặc --target chỉ định.
    def _pw_env():
        env = dict(os.environ)
        env.setdefault("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
        return env

    def _find_mic_node():
        # (31/10/2026) MIC BT ƯU TIÊN: SRS-XB33 tích hợp mic + DSP — nhạy gấp ~3x
        # mic USB Jieli với cùng nguồn âm (đo 31/10: peak 2892 vs 820). Fallback
        # mic USB Jieli khi loa BT rời (nguồn ngắt lúc 22:07 - micro BT biến mất).
        try:
            out = subprocess.run(
                ["pw-cli", "ls", "Node"], capture_output=True, text=True,
                timeout=5, env=_pw_env(),
            ).stdout
            import re as _re
            # bluez_input (mic BT) — split chuẩn để không bắt nhầm id:
            blocks = _re.split(r"id (\d+), type PipeWire:Interface:Node/3", out)
            usb_id = None
            for k in range(1, len(blocks), 2):
                nid, content = blocks[k], blocks[k + 1]
                if "Audio/Source" not in content:
                    continue
                if _re.search(r"bluez_input\.[0-9A-Fa-f:]+", content):
                    return nid  # mic BT ưu tiên
                if "UACDemoV1.0" in content and usb_id is None:
                    usb_id = nid
            if usb_id:
                return usb_id
        except Exception:
            pass
        return None

    _mic_node = _find_mic_node()
    print(f"[WAKE] mic PipeWire node: {_mic_node or 'mặc định'}", flush=True)

    cooldown_until = 0.0
    _last_debug = 0.0
    _gated = 0  # (13/11/2026) đếm chunk bị gate — báo cáo lọc tạp âm
    _last_gate_report = 0.0
    while True:
        try:
            if proc is None or proc.poll() is not None:
                # pw-record (PipeWire): mono 16kHz s16le, raw ra stdout.
                cmd = ["pw-record", "--format", "s16", "--rate", "16000",
                       "--channels", "1", "--raw"]
                if _mic_node:
                    cmd += ["--target", _mic_node]
                cmd += ["-"]
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    env=_pw_env(),
                )
                recognizer = KaldiRecognizer(model, SAMPLE_RATE)
                print("[WAKE] pw-record bắt đầu (mic Jieli qua PipeWire)", flush=True)

            chunk = proc.stdout.read(8000)  # ~0.25s audio
            if not chunk:
                time.sleep(0.2)
                if proc.poll() is not None:
                    # arecord chết (busy/EOF) — tái tạo recognizer để không lệch sample
                    proc = None
                    time.sleep(2)
                continue

            # (13/11/2026) LỌC TẠP ÂM 3 LỚP — owner yêu cầu lọc tạp âm + âm
            # thanh môi trường (TV/nhạc/phòng): đo được mic chỉ RMS 130-205
            # khi owner gọi xa, trong khi TV nền 122-147 → SNR≈0dB, Vosk
            # transcribe TV chứ không nghe owner. Xử lý theo thứ tự:
            #   Lớp 1: high-pass 1 bậc fc≈180Hz — cắt rumble/HVAC/TV-bass
            #   Lớp 2: noise floor adaptive (percentile bám nền phòng)
            #   Lớp 3: speech gate theo SNR + AGC gain max 24x (cũ 8x)
            try:
                import struct as _struct, array as _array, math as _math
                samples = _array.array("h")
                samples.frombytes(chunk)

                # Lớp 1: high-pass cắt trầm
                samples = _array.array("h", [
                    int(max(-32768, min(32767, v * 32768)))
                    for v in map(_hp, (s / 32768.0 for s in samples))
                ])

                if samples:
                    _rms = _math.sqrt(
                        sum(x * x for x in samples) / len(samples))
                    _noise.update(_rms)

                    # Lớp 3a: speech gate — chunk chỉ toàn tạp âm thì bỏ,
                    # không đưa Vosk (chặn TV/xe/nhạc transcribe nhầm).
                    # Ngưỡng: RMS phải vượt noise floor × 2.2 (~7dB SNR)
                    # và tuyệt đối > 90 (tĩnh điện) mới coi là tiếng nói.
                    _speech_rms = max(_rms, 90.0)
                    if _rms < max(90.0, _noise.level * 2.2):
                        _gated += 1
                        continue

                    # Lớp 3b: AGC normalize về 9000 (~-11dBFS), gain tối đa
                    # 24x (cũ 8x — mic Jieli xa nguồn chỉ RMS 130-205),
                    # clip guard 32000:
                    _gain = min(24.0, 9000.0 / max(_speech_rms, 1))
                    if _gain > 1.01:
                        for _i in range(len(samples)):
                            _v = int(samples[_i] * _gain)
                            samples[_i] = (32000 if _v > 32000
                                           else (-32000 if _v < -32000 else _v))
                    chunk = samples.tobytes()
            except Exception:
                pass  # lọc fail → dùng chunk gốc (vẫn nghe khi tiếng to)

            if recognizer.AcceptWaveform(chunk):
                text = json.loads(recognizer.Result()).get("text", "").strip().lower()
            else:
                text = json.loads(recognizer.PartialResult()).get("partial", "").strip().lower()

            now = time.time()
            if text and now >= _last_debug + 5.0:
                # (13/11/2026) kèm thống kê gate + noise floor để owner audit
                print(f"[WAKE-DBG] Vosk: '{text}' (gate {_gated} chunk, "
                      f"floor {_noise.level:.0f})", flush=True)
                _last_debug = now
                _gated = 0
            if not text or now < cooldown_until:
                continue

            def _fuzzy_hit(txt: str) -> bool:
                # (31/10/2026) Vosk small nhận "TONY ơi" thành 'thừa'/'tôi'/
                # 'vực'... — khớp mờ từng token (Levenshtein <=2) với tên + 'ơi':
                # (06/11/2026) thêm bộ tên CHERRY + giữ TONY quá độ.
                # (10/11/2026) SIẾT FALSE-POSITIVE TV: khớp cụm siết từ ≤3 lỗi
                # xuống ≤2 lỗi — 'với mục'/'với mỹ'/'tôi bất'/'tải về' (tiếng TV)
                # khớp 'tới mì'/'tôi ơi' với 3 lỗi đã khiến TV tự wake CHERRY
                # cả chục lần/ngày. 2 lỗi vẫn giữ 'cherry ơi'/'tony ơi' thật.
                def _lev(a: str, b: str) -> int:
                    if abs(len(a) - len(b)) > 2:
                        return 9
                    prev = list(range(len(b) + 1))
                    for i, ca in enumerate(a, 1):
                        cur = [i]
                        for j, cb in enumerate(b, 1):
                            cur.append(min(prev[j] + 1, cur[j - 1] + 1,
                                           prev[j - 1] + (ca != cb)))
                        prev = cur
                    return prev[-1]

                # (10/11/2026) 'ơi'/'à' phải là token ĐỘC LẬP (không tách từ giữa
                #   từ khác — 'ngoài khơi' không sinh token 'ơi').
                # (11/11/2026) OWNER CHỐT: chỉ tên CHERRY — bỏ 'tony'/'tó-ni' khỏi
                #   danh sách tên, bỏ cụm 'tony ơi'/'tôi ơi'/'tony oi' khỏi khớp
                #   mờ. Thêm token đuôi 'à' ("Cherry à" = wake chuẩn owner).
                tokens = txt.replace(" ơi", " ơi ").replace(" à", " à ").split()
                has_name = any(
                    _lev(t, w) <= 2
                    for t in tokens
                    for w in ("cherry", "cheri", "ché ri", "che ri", "chè ri")
                )
                has_tail = any(t in ("ơi", "oi", "ơi!", "à", "a", "à!") for t in tokens)
                if has_name and has_tail:
                    return True
                # cụm đầy đủ khớp mờ 2 lỗi (siết từ 3 — anti TV-noise 10/11):
                return any(_lev(txt[:24], p) <= 2 for p in
                           ("cherry ơi", "cherry oi", "cheri oi",
                            "cherry à", "cherry a", "cheri à"))

            if any(p in text for p in WAKE_PHRASES) or _fuzzy_hit(text):
                print(f"[WAKE] NGHE THẤY: '{text}' → wake!", flush=True)
                wake_kiosk()
                cooldown_until = now + 8  # chống double-trigger
            elif any(p in text for p in SLEEP_PHRASES):
                print(f"[WAKE] NGHE: '{text}' → sleep", flush=True)
                sleep_kiosk()
                cooldown_until = now + 8

        except KeyboardInterrupt:
            print("[WAKE] dừng", flush=True)
            if proc: proc.terminate()
            return 0
        except Exception as exc:
            print(f"[WAKE] lỗi vòng lặp (thử lại 5s): {exc}", flush=True)
            if proc: proc.terminate(); proc = None
            time.sleep(5)

if __name__ == "__main__":
    sys.exit(main())
