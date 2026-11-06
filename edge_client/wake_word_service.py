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
    # (06/11/2026) OWNER ĐỔI TÊN: cherry / cherry ơi / hi cherry / hay cherry
    # (cũ: tony — giữ biến thể cũ 1 tuần quá độ rồi bỏ) + biến thể dấu/không dấu
    # Vosk hay trả về ("cherry" → "cherry"/"cheri"/"ché ri"):
    "cherry", "cherry ơi", "cherry oi", "hi cherry", "hay cherry", "hey cherry",
    "hay cherry ơi", "hay cherry oi", "hi cherry ơi", "hi cherry oi",
    "cheri", "ché ri", "che ri", "chè ri",
    # biến thể TONY cũ (quá độ — owner quen miệng):
    "tony", "tony ơi", "tony oi", "hi tony", "hay tony", "hey tony",
    "hay tony ơi", "hay tony oi", "hi tony ơi", "hi tony oi",
    "tôi nghĩ", "toi nghi", "tới mì", "toi mi", "mì tươi", "mi tuoi",
    "tôi nghe", "tôi ơi", "toi oi", "chào trợ lý", "chao tro ly",
    "trợ lý ơi", "tro ly oi",
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

            # (31/10/2026) AGC: mic Jieli hẹp 30–50cm + tiếng xa rất yếu —
            # normalize RMS mỗi chunk về mức mục tiêu 9000 (~-11dBFS), gain
            # tối đa 8x, clip guard 32000. Tiếng to giữ nguyên, tiếng nhỏ kéo lên:
            try:
                import struct as _struct, array as _array, math as _math
                samples = _array.array("h")
                samples.frombytes(chunk)
                if samples:
                    _rms = _math.sqrt(
                        sum(x * x for x in samples) / len(samples))
                    if _rms > 60:  # không khuếch đại tĩnh điện nền
                        _gain = min(8.0, 9000.0 / max(_rms, 1))
                    else:
                        _gain = 1.0
                    if _gain > 1.01:
                        for _i in range(len(samples)):
                            _v = int(samples[_i] * _gain)
                            samples[_i] = (32000 if _v > 32000
                                           else (-32000 if _v < -32000 else _v))
                        chunk = samples.tobytes()
            except Exception:
                pass  # AGC fail → dùng chunk gốc (vẫn nghe khi tiếng to)

            if recognizer.AcceptWaveform(chunk):
                text = json.loads(recognizer.Result()).get("text", "").strip().lower()
            else:
                text = json.loads(recognizer.PartialResult()).get("partial", "").strip().lower()

            now = time.time()
            if text and now >= _last_debug + 5.0:
                print(f"[WAKE-DBG] Vosk: '{text}'", flush=True)
                _last_debug = now
            if not text or now < cooldown_until:
                continue

            def _fuzzy_hit(txt: str) -> bool:
                # (31/10/2026) Vosk small nhận "TONY ơi" thành 'thừa'/'tôi'/
                # 'vực'... — khớp mờ từng token (Levenshtein <=2) với tên + 'ơi':
                # (06/11/2026) thêm bộ tên CHERRY + giữ TONY quá độ.
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

                tokens = txt.replace("ơi", " ơi").split()
                has_name = any(
                    _lev(t, w) <= 2
                    for t in tokens
                    for w in ("cherry", "cheri", "ché ri", "che ri",
                              "tony", "toi", "tôi", "tony.", "tó-ni")
                )
                has_oi = "ơi" in tokens or "oi" in tokens or "ơi!" in tokens
                if has_name and has_oi:
                    return True
                # cụm đầy đủ khớp mờ 1 lỗi:
                return any(_lev(txt[:24], p) <= 3 for p in
                           ("cherry ơi", "cherry oi", "cheri oi",
                            "tony ơi", "tôi ơi", "tony oi", "tới mì"))

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
