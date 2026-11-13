#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Audio route auto-switch cho Pi 5 — theo yêu cầu owner (13/11/2026, image_3120a8):

  1) Màn hình HDMI CẮM    → âm thanh ưu tiên ra LOA HDMI (monitor có loa).
  2) Màn hình KHÔNG CẮM   → tự kết nối loa Bluetooth SRS-XB33 và phát qua BT.

Chạy mỗi 30s (systemd timer), idempotent:
  - Đổi default sink chỉ khi trạng thái hiện tại SAI so với mong muốn.
  - BT connect chỉ khi đã trust nhưng chưa connected (loa tắt nguồn → retry lần sau).
Log: /home/quanpt1/Desktop/edge_client/logs/audio_route.log (giữ 200 dòng cuối).
"""
import subprocess
import time
import os
import sys

LOG = os.path.expanduser("~/Desktop/edge_client/logs/audio_route.log")
BT_MAC = "6C:47:60:58:EF:93"   # SRS-XB33 (Sony) — đã pair + trust
HDMI_CARD = "card1"            # vc4 HDMI card trên Pi 5


def log(msg: str) -> None:
    line = time.strftime("%Y-%m-%d %H:%M:%S ") + msg
    print(line, flush=True)
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
        # giữ file nhỏ
        with open(LOG, "r", encoding="utf-8") as f:
            lines = f.readlines()
        if len(lines) > 200:
            with open(LOG, "w", encoding="utf-8") as f:
                f.writelines(lines[-200:])
    except Exception:
        pass


def run(cmd: str, timeout: int = 20) -> str:
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return (r.stdout or "").strip()
    except Exception as exc:
        return f"__ERR__ {type(exc).__name__}: {exc}"


def hdmi_connected() -> bool:
    """True nếu ít nhất 1 cổng HDMI đang có monitor cắm."""
    for port in ("HDMI-A-1", "HDMI-A-2"):
        try:
            with open(f"/sys/class/drm/{HDMI_CARD}-{port}/status") as f:
                if f.read().strip().lower() == "connected":
                    return True
        except FileNotFoundError:
            continue
    return False


def bt_speaker_reachable() -> bool:
    """Ping nhanh BR/EDR — 1 gói, 2s. Loa tắt nguồn/out of range → False."""
    out = run(f"l2ping -c 1 -t 2 {BT_MAC} 2>/dev/null", timeout=8)
    return ("0 bytes" in out or "bytes from" in out.lower()) and "__ERR__" not in out


def bt_connected() -> bool:
    out = run(f"bluetoothctl info {BT_MAC}")
    return "Connected: yes" in out


def current_default_sink() -> str:
    out = run("wpctl status")
    for line in out.splitlines():
        if "*" in line and "Sinks:" not in line:
            #  *   58. Built-in Audio ...
            try:
                return line.split("*", 1)[1].split(".", 1)[0].strip()
            except Exception:
                continue
    return ""


def sink_id_of(name_fragment: str) -> str:
    """Tìm sink id theo fragment tên ('HDMI' hoặc 'bluez')."""
    out = run("wpctl status")
    in_sinks = False
    for line in out.splitlines():
        if "Sinks:" in line:
            in_sinks = True
            continue
        if in_sinks:
            if "Sources:" in line or not line.strip().startswith(("│", "├", "└")):
                in_sinks = "Sources:" in line
                if not in_sinks:
                    continue
            if name_fragment.lower() in line.lower():
                try:
                    return line.split(".", 1)[0].replace("│", "").replace("*", "").strip()
                except Exception:
                    continue
    return ""


def set_default(sink_id: str) -> bool:
    out = run(f"wpctl set-default {sink_id}")
    ok = "__ERR__" not in out
    return ok


def main() -> int:
    want_hdmi = hdmi_connected()
    cur = current_default_sink()

    if want_hdmi:
        hdmi = sink_id_of("HDMI")
        if hdmi and cur != hdmi:
            if set_default(hdmi):
                log(f"SWITCH → HDMI sink {hdmi} (màn hình cắm)")
                return 0
            log(f"FAIL set-default HDMI {hdmi}")
            return 1
        # default đã đúng (hoặc không tìm thấy HDMI sink — PIPEWIRE cũng tự route)
        return 0

    # Không có màn hình → BT là ưu tiên
    if not bt_connected():
        if bt_speaker_reachable():
            out = run(f"bluetoothctl connect {BT_MAC}", timeout=30)
            if "successful" not in out.lower():
                log(f"BT connect fail: {out[:80]}")
                return 1
            time.sleep(2)  # PipeWire cần vài giây tạo bluez sink
            log("BT SRS-XB33 connected")
        else:
            # Loa tắt nguồn/out of range — không log spam: chỉ khi lần trước khác
            return 0

    bt = sink_id_of("bluez")
    if bt and cur != bt:
        if set_default(bt):
            log(f"SWITCH → BT sink {bt} (không có màn hình)")
            return 0
        log(f"FAIL set-default BT {bt}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
