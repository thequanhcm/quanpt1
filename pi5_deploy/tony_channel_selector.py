#!/usr/bin/env python3
"""TONY CHANNEL SELECTOR — Tự điều tiết chọn kênh truyền mạnh nhất PC↔Pi5.

Chạy trên Pi5 (systemd timer 30s). Thứ tự ưu tiên theo băng thông/độ trễ đo
thật mỗi chu kỳ, cập nhật `edge_client/config.json` core_host tương ứng:

  1. MESH   (Tailscale 100.92.219.98:8766)  — direct ~2-4ms, không phụ thuộc router
  2. LAN    (IP WiFi cùng subnet PC)        — ~1-3ms, phụ thuộc router
  3. DERP   (Tailscale qua Internet)        — 50-200ms, cần Internet
  4. BT-PAN (172.30.99.1:8766)              — ~20-50ms nhưng ~200KB/s,
                                              kênh cứu hộ khi WiFi+mesh chết

Fail-honest: mọi probe đo RTT thật (TCP connect), KHÔNG suy diễn. Kênh nào
probe PASS trước (thứ tự ưu tiên) được chọn. Không đổi config nếu kênh
hiện tại vẫn khỏe (chống dao động — hysteresis: kênh mới phải tốt hơn ≥50%).
"""
from __future__ import annotations

import json
import logging
import socket
import subprocess
import sys
import time
from pathlib import Path

CONFIG_PATH = Path("/home/quanpt1/Desktop/edge_client/config.json")
STATE_PATH = Path("/home/quanpt1/.tony_channel_state.json")

CANDIDATES = [
    {"name": "MESH",   "host": "100.92.219.98",  "port": 8766, "prio": 1},
    {"name": "LAN",    "host": "192.168.1.9",    "port": 8766, "prio": 2},
    {"name": "BT-PAN", "host": "172.30.99.1",    "port": 8766, "prio": 3},
]

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("tony_channel_selector")


def probe_rtt(host: str, port: int = 8766, timeout: float = 2.0) -> float | None:
    """Đo RTT TCP connect (ms). Trả None nếu không nối được — fail-honest."""
    s = socket.socket()
    s.settimeout(timeout)
    t0 = time.time()
    try:
        s.connect((host, port))
        return (time.time() - t0) * 1000.0
    except OSError:
        return None
    finally:
        s.close()


def tailscale_direct() -> bool:
    """Tailscale đang direct hay DERP? (direct = tốt)."""
    r = subprocess.run(["tailscale", "status", "--json"], capture_output=True, text=True, timeout=10)
    try:
        d = json.loads(r.stdout)
        peer = d.get("Peer", {})
        for p in peer.values():
            if "100.92.219.98" in (p.get("TailscaleIPs") or []):
                cur = p.get("CurAddr") or ""
                return bool(cur)  # có CurAddr = direct
    except Exception:
        pass
    return False


def load_state() -> dict:
    try:
        return json.loads(STATE_PATH.read_text())
    except Exception:
        return {"active": "MESH", "active_rtt": 0.0}


def save_state(state: dict) -> None:
    STATE_PATH.write_text(json.dumps(state, indent=1))


def main() -> int:
    state = load_state()
    active_name = state.get("active", "MESH")
    active_rtt = state.get("active_rtt", 0.0)

    # Probe tất cả kênh (RTT thật)
    probes: dict[str, float | None] = {}
    for c in CANDIDATES:
        probes[c["name"]] = probe_rtt(c["host"], c["port"])

    # Kênh hiện tại vẫn sống không?
    active_cfg = next(c for c in CANDIDATES if c["name"] == active_name)
    active_probe = probes.get(active_name)

    if active_probe is not None:
        # Kênh hiện tại sống — chỉ đổi nếu có kênh ưu tiên CAO HƠN sống
        # và khỏe hơn rõ rệt (hysteresis 50%)
        better = None
        for c in CANDIDATES:
            if c["prio"] < active_cfg["prio"]:
                rtt = probes.get(c["name"])
                if rtt is not None and (active_probe is None or rtt < active_probe * 0.5):
                    better = c
                    break
        if better:
            log.info("UPGRADE %s (%.0fms) → %s (%.0fms)", active_name, active_probe, better["name"], probes[better["name"]])
            active_name, active_rtt = better["name"], probes[better["name"]]
        else:
            active_rtt = active_probe
    else:
        # Kênh hiện tại chết — chọn kênh khỏe nhất còn sống theo ưu tiên
        log.warning("kênh %s CHẾT — failover", active_name)
        chosen = None
        for c in sorted(CANDIDATES, key=lambda x: x["prio"]):
            if probes[c["name"]] is not None:
                chosen = c
                break
        if chosen:
            log.info("FAILOVER %s → %s (%.0fms)", active_name, chosen["name"], probes[chosen["name"]])
            active_name, active_rtt = chosen["name"], probes[chosen["name"]]
        else:
            log.error("TẤT CẢ kênh chết — giữ config, đợi chu kỳ sau")
            return 1

    # Ghi config nếu đổi host
    new_host = next(c["host"] for c in CANDIDATES if c["name"] == active_name)
    try:
        cfg = json.loads(CONFIG_PATH.read_text())
        if cfg.get("core_host") != new_host:
            cfg["core_host"] = new_host
            CONFIG_PATH.write_text(json.dumps(cfg, indent=2, ensure_ascii=False))
            log.info("config core_host → %s (%s)", new_host, active_name)
            # restart service để áp dụng ngay
            subprocess.run(["sudo", "systemctl", "restart", "quan_ai_edge"], timeout=30)
            log.info("restart quan_ai_edge")
    except Exception as e:
        log.error("ghi config lỗi: %s", e)

    save_state({"active": active_name, "active_rtt": round(active_rtt, 1),
                "probes": {k: v for k, v in probes.items()}, "ts": time.time()})
    return 0


if __name__ == "__main__":
    sys.exit(main())
