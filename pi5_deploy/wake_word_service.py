#!/usr/bin/env python3
"""QUAN AI BRAIN — Wake Word Service cho Pi 5 (24/7, chạy ngoài kiosk).

Nghe liên tục qua mic USB (Jieli), nhận tiếng Việt offline bằng Vosk.
Khi nghe thấy "TONY ơi" (hoặc "Tony", "Hi Tony"...):
  1. POST http://127.0.0.1:8768/api/kiosk/control {"action":"wake_by_voice"}
     → daemon _wake_screen: bật màn hình + launch kiosk + avatar ACTIVE.
  2. Kiosk chạy → wake_engine.js (Web Speech) tiếp quản hội thoại.

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
# Model small-vn nhận "Tony ơi" thành nhiều biến thể gần giống — dùng bộ khớp
# RỘNG (đã kiểm chứng: "Tony ơi" → 'tôi nghĩ tới mì tươi'). Wake là hành động
# vô hại (chỉ bật màn hình) nên chấp nhận false-positive thấp.
WAKE_PHRASES = (
    "tony ơi", "tony oi", "hi tony", "hey tony", "tony",
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
    print("[WAKE] sẵn sàng — lắng nghe 'TONY ơi'", flush=True)

    # Ghi qua pw-record (PipeWire) — device USB bị PipeWire giữ độc quyền nên
    # arecord plughw:2,0 luôn 'Device busy'. pw-record đọc từ source node mặc
    # định (Jieli UACDemoV1.0 Mono — priority.session 2000) hoặc --target chỉ định.
    def _pw_env():
        env = dict(os.environ)
        env.setdefault("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
        return env

    def _find_mic_node():
        try:
            out = subprocess.run(
                ["pw-cli", "ls", "Node"], capture_output=True, text=True,
                timeout=5, env=_pw_env(),
            ).stdout
            import re as _re
            m = _re.search(r"id (\d+),[^]*?UACDemoV1\.0[^]*?Audio/Source", out)
            if m:
                return m.group(1)
        except Exception:
            pass
        return None

    _mic_node = _find_mic_node()
    print(f"[WAKE] mic PipeWire node: {_mic_node or 'mặc định'}", flush=True)

    cooldown_until = 0.0
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

            if recognizer.AcceptWaveform(chunk):
                text = json.loads(recognizer.Result()).get("text", "").strip().lower()
            else:
                text = json.loads(recognizer.PartialResult()).get("partial", "").strip().lower()

            now = time.time()
            if not text or now < cooldown_until:
                continue

            if any(p in text for p in WAKE_PHRASES):
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
