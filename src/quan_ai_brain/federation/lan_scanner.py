"""SEC-S2 (b): Quét LAN chỉ-đọc — phát hiện thiết bị hiện diện trên mạng nội bộ.

Owner directive: PC lõi phải "nhìn thấy" các thiết bị để quản. Phạm vi SỰ HIỆN
DIỆN ONLY: ping song song (ThreadPool, timeout ngắn) + gộp bảng ARP lấy MAC.
KHÔNG quét cổng tấn công, KHÔNG khai thác lỗ hổng, KHÔNG đụng thiết bị —
read-only recon đúng chuẩn an ninh nội bộ.

Fail-honest: thiết bị không phản hồi → không liệt kê (không đoán).
"""
from __future__ import annotations

import concurrent.futures
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class LanDevice:
    ip: str
    mac: str = ""
    vendor_hint: str = ""      # từ OUI prefix nếu nhận ra (không tra online)
    hostname: str = ""         # chỉ DNS ngược local, thường trống
    is_registered_node: bool = False
    node_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "ip": self.ip, "mac": self.mac, "hostname": self.hostname,
            "vendor_hint": self.vendor_hint,
            "is_registered_node": self.is_registered_node, "node_id": self.node_id,
        }


# OUI quen thuộc (cục bộ, không tra mạng) — chỉ để hint, không chắc chắn
_KNOWN_OUI = {
    "dc-a6-32": "Raspberry Pi", "b8-27-eb": "Raspberry Pi", "e4-5f-01": "Raspberry Pi",
    "d8-3a-dd": "Raspberry Pi", "2c-cf-67": "Raspberry Pi",
    "fc-57-03": "(?)" ,  # gateway nhà anh — không đoán vendor
}


class LanScanner:
    """Quét /24 hiện diện-only. stdlib only."""

    def __init__(self, base_subnet: str = "") -> None:
        self.local_ip = self._detect_local_ip()
        if base_subnet:
            m = re.match(r"^(\d{1,3}(?:\.\d{1,3}){2})\.?$", base_subnet.rstrip("."))
            self.subnet = (m.group(1) if m else base_subnet).rstrip(".")
        else:
            # Tự dò theo IP LAN của máy — không hardcode subnet (fix SEC-S2)
            self.subnet = self.local_ip.rsplit(".", 1)[0]
        if self.local_ip.startswith(self.subnet + "."):
            self.subnet = self.local_ip.rsplit(".", 1)[0]

    @staticmethod
    def _detect_local_ip() -> str:
        """IP LAN thật của máy (UDP connect trick — không gửi gói ra ngoài)."""
        import socket

        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("10.255.255.255", 1))
            return s.getsockname()[0]
        except Exception:
            return "127.0.0.1"
        finally:
            s.close()

    @staticmethod
    def _ping_one(ip: str, timeout_ms: int = 500) -> str | None:
        try:
            r = subprocess.run(
                ["ping", "-n", "1", "-w", str(timeout_ms), ip],
                capture_output=True, text=True, timeout=3,
                encoding="utf-8", errors="replace",
            )
            return ip if "ttl=" in (r.stdout or "").lower() else None
        except Exception:
            return None

    @staticmethod
    def _arp_table() -> dict[str, str]:
        try:
            r = subprocess.run(["arp", "-a"], capture_output=True, text=True,
                               timeout=10, encoding="utf-8", errors="replace")
            pairs = re.findall(r"(192\.168\.\d+\.\d+)\s+([0-9a-f-]{14,17})",
                               (r.stdout or ""), re.IGNORECASE)
            return {ip: mac.lower() for ip, mac in pairs}
        except Exception:
            return {}

    def scan(self, max_workers: int = 80, timeout_ms: int = 500,
             registered_hosts: dict[str, str] | None = None) -> list[LanDevice]:
        """Quét toàn bộ /24. registered_hosts: {host: node_id} để đánh dấu nút mình."""
        base = self.subnet
        targets = [f"{base}.{i}" for i in range(1, 255)]
        live: list[str] = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
            for res in ex.map(lambda ip: self._ping_one(ip, timeout_ms), targets):
                if res:
                    live.append(res)
        mac_map = self._arp_table()
        reg = registered_hosts or {}
        devices: list[LanDevice] = []
        for ip in sorted(live, key=lambda x: int(x.split(".")[-1])):
            mac = mac_map.get(ip, "")
            oui = mac[:8] if mac else ""
            dev = LanDevice(
                ip=ip, mac=mac,
                vendor_hint=_KNOWN_OUI.get(oui.lower(), ""),
                hostname=self._reverse_dns(ip),
                is_registered_node=ip in reg,
                node_id=reg.get(ip, ""),
            )
            devices.append(dev)
        return devices

    @staticmethod
    def _reverse_dns(ip: str) -> str:
        import socket

        try:
            return socket.gethostbyaddr(ip)[0]
        except Exception:
            return ""

    def scan_summary(self, registered_hosts: dict[str, str] | None = None) -> dict[str, Any]:
        devices = self.scan(registered_hosts=registered_hosts)
        nodes_seen = [d.to_dict() for d in devices if d.is_registered_node]
        raspis = [d.to_dict() for d in devices if "raspberry" in d.vendor_hint.lower()]
        return {
            "scanned_at": datetime.now(timezone.utc).isoformat(),
            "subnet": self.subnet + ".0/24",
            "local_ip": self.local_ip,
            "total_alive": len(devices),
            "devices": [d.to_dict() for d in devices],
            "registered_nodes_seen": nodes_seen,
            "raspberry_pi_candidates": raspis,
        }
