"""UDR-1 Universal Device Reader — đọc TOÀN BỘ thiết bị cắm vào Pi5 (04/11/2026).

Chỉ thị quanpt1: "khi anh chỉ cần sử dụng pi5, kết nối thiết bị đó với Pi5 qua
USB, Lan là Pi5 sẽ đọc được tất cả các thông tin, gửi về DM TONY cho anh biết
hiện trạng".

Nguyên tắc an toàn (giữ nguyên triết lý Edge Agent V41):
- READ-ONLY tuyệt đối: không ghi, không cấu hình, không mount, không cài gì.
- Stdlib-only, không thư viện ngoài.
- Fail-closed: mỗi scanner tự bắt lỗi, trả fallback, KHÔNG BAO GIỜ raise.
- Timeout cứng mọi subprocess (2-4s) — thiết bị treo không được treo daemon.
- Windows (máy dev): scanner trả danh sách rỗng + note platform — trung thực.
"""
from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

_SUB_TIMEOUT = 4  # giây — timeout cứng mọi lệnh ngoài


def _is_linux() -> bool:
    return platform.system() == "Linux"


def _run(cmd: list[str], timeout: int = _SUB_TIMEOUT) -> str:
    """Chạy lệnh ngoài, trả stdout; lỗi/treo → chuỗi rỗng."""
    try:
        out = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
        ).stdout
        return out or ""
    except Exception:
        return ""


# ---------------------------------------------------------------- USB ------
def scan_usb_devices() -> list[dict[str, Any]]:
    """USB: lsusb nếu có; fallback /sys/bus/usb/devices (idVendor:idProduct)."""
    devs: list[dict[str, Any]] = []
    if _is_linux():
        out = _run(["lsusb"])
        for line in out.splitlines():
            m = re.match(
                r"Bus (\d+) Device (\d+): ID ([0-9a-fA-F]{4}:[0-9a-fA-F]{4}) (.+)",
                line.strip(),
            )
            if m:
                devs.append({
                    "bus": "usb",
                    "dev_id": f"{m.group(1)}-{m.group(2)}",
                    "vid_pid": m.group(3).lower(),
                    "name": m.group(4).strip()[:80],
                })
        if not devs:
            # fallback: đọc sysfs trực tiếp
            for d in Path("/sys/bus/usb/devices").iterdir():
                if not re.match(r"^\d+-[\d.]+$", d.name):
                    continue  # bỏ cổng root/hub interface
                vid = _read_first(d / "idVendor")
                pid = _read_first(d / "idProduct")
                if not (vid and pid):
                    continue
                prod = _read_first(d / "product", 80)
                mfr = _read_first(d / "manufacturer", 40)
                devs.append({
                    "bus": "usb",
                    "dev_id": d.name,
                    "vid_pid": f"{vid}:{pid}".lower(),
                    "name": (prod or mfr or "USB device")[:80],
                })
    return devs


# -------------------------------------------------------------- Serial -----
def scan_serial_ports() -> list[dict[str, Any]]:
    """Serial/UART: ttyUSB*, ttyACM*, ttyAMA*, Serial0; kèm by-id ổn định."""
    devs: list[dict[str, Any]] = []
    if not _is_linux():
        return devs
    for pattern in ("/dev/ttyUSB*", "/dev/ttyACM*", "/dev/ttyAMA*", "/dev/serial0"):
        for p in Path("/").glob(pattern.lstrip("/")):
            name = str(p)
            byid = ""
            try:
                byid_dir = Path("/dev/serial/by-id")
                if byid_dir.exists():
                    for link in byid_dir.iterdir():
                        try:
                            if link.resolve() == p.resolve():
                                byid = link.name[:80]
                                break
                        except Exception:
                            continue
            except Exception:
                pass
            devs.append({
                "bus": "serial",
                "dev_id": name,
                "name": byid or name,
                "meta": {"by_id": byid},
            })
    return devs


# ----------------------------------------------------------------- I2C -----
def scan_i2c() -> list[dict[str, Any]]:
    """I2C: bus /dev/i2c-* + tên chip từ /sys/bus/i2c/devices (read-only)."""
    devs: list[dict[str, Any]] = []
    if not _is_linux():
        return devs
    for p in Path("/dev").glob("i2c-*"):
        devs.append({"bus": "i2c", "dev_id": str(p), "name": f"I2C bus {p.name}"})
    # thiết bị gắn trên bus (do kernel detect) — read-only
    try:
        for d in Path("/sys/bus/i2c/devices").iterdir():
            chip = _read_first(d / "name", 80)
            if chip and not d.name.replace(".", "").isdigit():
                continue
            if chip:
                devs.append({
                    "bus": "i2c_device",
                    "dev_id": d.name,
                    "name": chip[:80],
                })
    except Exception:
        pass
    return devs


# ----------------------------------------------------------------- SPI/GPIO
def scan_gpio_spi() -> list[dict[str, Any]]:
    """GPIO chips + SPI device nodes (chỉ liệt kê sự tồn tại)."""
    devs: list[dict[str, Any]] = []
    if not _is_linux():
        return devs
    for p in Path("/dev").glob("gpiochip*"):
        devs.append({"bus": "gpio", "dev_id": str(p), "name": f"GPIO chip {p.name}"})
    for p in Path("/dev").glob("spidev*"):
        devs.append({"bus": "spi", "dev_id": str(p), "name": f"SPI device {p.name}"})
    return devs


# ------------------------------------------------------------- Storage -----
def scan_storage() -> list[dict[str, Any]]:
    """Ổ/thẻ nhớ: khối /sys/class/block + điểm mount từ /proc/mounts."""
    devs: list[dict[str, Any]] = []
    if not _is_linux():
        return devs
    try:
        for d in Path("/sys/class/block").iterdir():
            if re.match(r"^(loop|ram|zram)\d*$", d.name):
                continue
            size_sectors = _read_first(d / "size")
            model = _read_first(d / "device/model", 60)
            size_gb = -1.0
            try:
                size_gb = round(int(size_sectors) * 512 / 1e9, 1)
            except Exception:
                pass
            devs.append({
                "bus": "block",
                "dev_id": d.name,
                "name": model or f"Block {d.name}",
                "meta": {"size_gb": size_gb},
            })
    except Exception:
        pass
    mounts = []
    try:
        for line in Path("/proc/mounts").read_text(encoding="utf-8").splitlines():
            parts = line.split()
            if len(parts) >= 3 and parts[1].startswith("/media/") or \
               (len(parts) >= 3 and parts[0].startswith("/dev/s")):
                mounts.append(f"{parts[0]}→{parts[1]}")
    except Exception:
        pass
    if mounts:
        devs.append({"bus": "mount", "dev_id": "removable_mounts",
                     "name": "; ".join(mounts[:5])[:120]})
    return devs


# ---------------------------------------------------------------- HDMI -----
def scan_hdmi() -> list[dict[str, Any]]:
    """HDMI: trạng thái kết nối từ /sys/class/drm (connected/disconnected)."""
    devs: list[dict[str, Any]] = []
    if not _is_linux():
        return devs
    try:
        for d in Path("/sys/class/drm").glob("card*-HDMI*"):
            status = _read_first(d / "status", 20) or "unknown"
            devs.append({
                "bus": "hdmi",
                "dev_id": d.name,
                "name": f"HDMI {status}",
                "meta": {"status": status},
            })
    except Exception:
        pass
    return devs


# -------------------------------------------------------------- Camera -----
def scan_cameras() -> list[dict[str, Any]]:
    devs = []
    if not _is_linux():
        return devs
    for p in Path("/dev").glob("video*"):
        devs.append({"bus": "v4l2", "dev_id": str(p), "name": f"Camera {p.name}"})
    return devs


# ------------------------------------------------------------ Bluetooth ----
def scan_bluetooth() -> list[dict[str, Any]]:
    """BLE/BT: bluetoothctl devices (timeout-guard); không có → hcitool dev."""
    devs: list[dict[str, Any]] = []
    if not _is_linux():
        return devs
    if shutil.which("bluetoothctl"):
        out = _run(["bluetoothctl", "devices"], timeout=6)
        for line in out.splitlines():
            m = re.match(r"Device ([0-9A-Fa-f:]{17}) (.+)", line.strip())
            if m:
                devs.append({
                    "bus": "bluetooth",
                    "dev_id": m.group(1),
                    "name": m.group(2).strip()[:80],
                })
    if not devs and shutil.which("hcitool"):
        out = _run(["hcitool", "dev"])
        for line in out.splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 3:
                devs.append({
                    "bus": "bluetooth_adapter",
                    "dev_id": parts[2],
                    "name": f"BT adapter {parts[1]}",
                })
    return devs


# ------------------------------------------------------------- LAN sees ----
def scan_network_neighbors() -> list[dict[str, Any]]:
    """LAN: hàng xóm ARP (`ip neigh`) — thiết bị mạng Pi5 nhìn thấy."""
    devs: list[dict[str, Any]] = []
    if not _is_linux():
        return devs
    out = _run(["ip", "neigh"])
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 5 and parts[4] not in ("FAILED", "INCOMPLETE"):
            ip, mac, state = parts[0], parts[4], parts[-1]
            if mac == "00:00:00:00:00:00":
                continue
            devs.append({
                "bus": "lan",
                "dev_id": ip,
                "name": f"LAN {ip}",
                "meta": {"mac": mac.lower(), "state": state},
            })
    return devs


# -------------------------------------------------- 1-Wire + hwmon ---------
def scan_sensors_and_onewire() -> list[dict[str, Any]]:
    """Cảm biến: hwmon (nhiệt/điện áp) + w1 GPIO 1-Wire (DS18B20...)."""
    devs: list[dict[str, Any]] = []
    if not _is_linux():
        return devs
    try:
        for d in Path("/sys/class/hwmon").iterdir():
            name = _read_first(d / "name", 60)
            if name:
                devs.append({"bus": "hwmon", "dev_id": d.name, "name": name[:80]})
    except Exception:
        pass
    try:
        for d in Path("/sys/bus/w1/devices").glob("*-*"):
            if d.name.startswith(("w1_bus_master", "00-")):
                continue
            crc_ok = ""
            try:
                raw = (d / "w1_slave").read_text(encoding="utf-8", errors="ignore")
                crc_ok = "YES" if "YES" in raw else "NO"
                m = re.search(r"t=(\-?\d+)", raw)
                temp = int(m.group(1)) / 1000.0 if m else None
            except Exception:
                temp = None
            devs.append({
                "bus": "1wire",
                "dev_id": d.name,
                "name": f"1-Wire {d.name}",
                "meta": {"crc_ok": crc_ok, "temp_c": temp},
            })
    except Exception:
        pass
    return devs


# ------------------------------------------------------------- helpers -----
def _read_first(path: Path, limit: int = 32) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore").strip()[:limit]
    except Exception:
        return ""


SCANNERS: tuple[tuple[str, Any], ...] = (
    ("usb", scan_usb_devices),
    ("serial", scan_serial_ports),
    ("i2c", scan_i2c),
    ("gpio_spi", scan_gpio_spi),
    ("storage", scan_storage),
    ("hdmi", scan_hdmi),
    ("camera", scan_cameras),
    ("bluetooth", scan_bluetooth),
    ("lan", scan_network_neighbors),
    ("sensors", scan_sensors_and_onewire),
)


def scan_all_devices() -> dict[str, Any]:
    """Quét MỌI kênh đọc-only. Trả dict {kênh: [thiết bị]} + platform note.

    Không bao giờ raise — lỗi từng kênh nuốt an toàn (fail-closed).
    """
    result: dict[str, Any] = {"platform": platform.system()}
    total = 0
    for bus, fn in SCANNERS:
        try:
            lst = fn()
        except Exception:
            lst = []
        result[bus] = lst
        total += len(lst)
    result["total"] = total
    if not _is_linux():
        result["note"] = "ngoài Linux (máy dev Windows) — scanner trả rỗng, trung thực"
    return result


def flatten_devices(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    """Phẳng hoá snapshot thành [{bus, dev_id, name, meta}] để so diff."""
    flat: list[dict[str, Any]] = []
    for bus, _fn in SCANNERS:
        for d in snapshot.get(bus, []) or []:
            if not isinstance(d, dict) or not d.get("dev_id"):
                continue
            flat.append({
                "bus": bus,
                "dev_id": str(d.get("dev_id"))[:80],
                "name": str(d.get("name", ""))[:120],
                "vid_pid": str(d.get("vid_pid", ""))[:20],
                "meta": d.get("meta") or {},
            })
    return flat


def device_fingerprint(dev: dict[str, Any]) -> str:
    """Dấu vân tay ổn định của thiết bị: bus + id (+vid_pid nếu có)."""
    base = f"{dev.get('bus', '?')}:{dev.get('dev_id', '?')}"
    vp = dev.get("vid_pid") or ""
    if vp:
        base = f"{base}:{vp}"
    return base[:160]
