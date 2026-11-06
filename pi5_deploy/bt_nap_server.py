#!/usr/bin/env python3
"""TONY BT-NAP server (BlueZ 5.x D-Bus) — Bluetooth Network Access Point trên Pi5.

Kênh dự phòng cấp 3 PC↔Pi5: khi WiFi + Tailscale mesh chết hoàn toàn,
PC join Bluetooth PAN (172.30.99.x) → heartbeat + DM text khẩn vẫn chạy.
Băng thông ~200KB/s — KHÔNG đủ audio/camera, chỉ transport heartbeat/DM.

Cơ chế: BlueZ network_server1 D-Bus API (org.bluez.Network1) register NAP
với bridge pan0. dnsmasq cấp DHCP cho PC join.
"""
from __future__ import annotations

import logging
import signal
import subprocess
import sys
import time

import dbus

BUS_NAME = "org.bluez"
PATH = "/org/bluez"
IFACE_ADAPTER = "org.bluez.Adapter1"
IFACE_NET_SERVER = "org.bluez.Network1"
DBUS_PROPS = "org.freedesktop.DBus.Properties"

BRIDGE = "pan0"
BRIDGE_IP = "172.30.99.1/24"
UUID_NAP = "00001116-0000-1000-8000-00805f9b34fb"  # NAP service UUID

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("tony_bt_nap")


def setup_bridge() -> None:
    """Tạo bridge pan0 + IP tĩnh (idempotent)."""
    subprocess.run(["sudo", "ip", "link", "show", BRIDGE], capture_output=True)
    if subprocess.run(["ip", "link", "show", BRIDGE], capture_output=True).returncode != 0:
        subprocess.run(["sudo", "ip", "link", "add", "name", BRIDGE, "type", "bridge"], check=True)
        log.info("created bridge %s", BRIDGE)
    subprocess.run(["sudo", "ip", "addr", "add", BRIDGE_IP, "dev", BRIDGE], capture_output=True)
    subprocess.run(["sudo", "ip", "link", "set", BRIDGE, "up"], check=True)
    log.info("bridge %s up at %s", BRIDGE, BRIDGE_IP)


def find_adapter() -> dbus.Interface:
    bus = dbus.SystemBus()
    om = bus.get_object("org.bluez", "/")
    interfaces = om.GetManagedObjects(dbus_interface="org.freedesktop.DBus.ObjectManager")
    for path, ifaces in interfaces.items():
        if IFACE_ADAPTER in ifaces:
            log.info("adapter: %s", path)
            return dbus.Interface(bus.get_object(BUS_NAME, path), IFACE_NET_SERVER)
    raise RuntimeError("Không tìm thấy Bluetooth adapter trên Pi5")


def main() -> int:
    setup_bridge()
    net_server = find_adapter()
    # Register NAP service trên bridge
    net_server.RegisterServer(UUID_NAP, BRIDGE)
    log.info("NAP registered: uuid=%s bridge=%s", UUID_NAP, BRIDGE)

    # Bluetooth discoverable + pairable để PC tìm thấy
    bus = dbus.SystemBus()
    om = bus.get_object("org.bluez", "/")
    interfaces = om.GetManagedObjects(dbus_interface="org.freedesktop.DBus.ObjectManager")
    for path, ifaces in interfaces.items():
        if IFACE_ADAPTER in ifaces:
            props = dbus.Interface(bus.get_object(BUS_NAME, path), DBUS_PROPS)
            props.Set(IFACE_ADAPTER, "Discoverable", dbus.Boolean(True))
            props.Set(IFACE_ADAPTER, "Pairable", dbus.Boolean(True))
            props.Set(IFACE_ADAPTER, "Alias", "TONY-PI5")
            log.info("adapter discoverable+pairable, alias=TONY-PI5")

    signal.signal(signal.SIGTERM, lambda *a: sys.exit(0))
    log.info("BT-NAP sẵn sàng — PC có thể join Bluetooth PAN tới Pi5")
    while True:
        time.sleep(30)
        # liveness: bridge còn up?
        r = subprocess.run(["ip", "link", "show", BRIDGE], capture_output=True)
        if r.returncode != 0:
            log.warning("bridge %s mất — dựng lại", BRIDGE)
            setup_bridge()


if __name__ == "__main__":
    sys.exit(main())
