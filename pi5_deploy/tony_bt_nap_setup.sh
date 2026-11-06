#!/bin/bash
# TONY BT-NAP: Bluetooth Network Access Point trên Pi5
# Kênh dự phòng cấp 3 PC↔Pi5 khi WiFi+mesh chết hoàn toàn (bandwidth ~200KB/s
# đủ cho heartbeat + DM text khẩn, KHÔNG đủ cho audio/camera)
set -u
LOG_TAG="tony_bt_nap"

# 1. Bluetooth service phải chạy
systemctl is-active --quiet bluetooth || sudo systemctl start bluetooth

# 2. Cấu hình bluetoothctl: discoverable + pairable + trust PC MAC (nếu truyền)
MAC_FILE="/home/quanpt1/.tony_bt_pc_mac"
if [ -f "$MAC_FILE" ]; then
    PC_MAC=$(cat "$MAC_FILE")
    bluetoothctl <<EOF
power on
discoverable on
pairable on
agent NoInputNoOutput
default-agent
trust $PC_MAC
EOF
fi

# 3. Đăng ký NAP service qua bluez (bt-network deprecated; dùng new bluez dbus)
# BlueZ 5.x: dbuses network_server. Cách bền: bt-network từ bluez-test? Pi OS Bookworm
# → dùng bluetoothctl network off/on? Không có. Dùng helper bt_pan:
# Pi OS Bookworm có /usr/bin/bt-pan? kiểm:
if command -v bt-pan >/dev/null 2>&1; then
    sudo brctl addbr pan0 2>/dev/null || sudo ip link add name pan0 type bridge 2>/dev/null
    sudo ip addr add 172.30.99.1/24 dev pan0 2>/dev/null
    sudo ip link set pan0 up
    sudo bt-pan server pan0 &
    logger -t $LOG_TAG "NAP started via bt-pan bridge pan0 172.30.99.1"
else
    # BlueZ modern: dùng dbus registration qua python
    python3 /home/quanpt1/Desktop/edge_client/bt_nap_server.py &
    logger -t $LOG_TAG "NAP started via python bluez server"
fi

# 4. DHCP cho bridge? PC join sẽ xin DHCP qua PAN — cần dnsmasq trên pan0
if ! systemctl is-active --quiet dnsmasq; then
    sudo apt-get install -y dnsmasq >/dev/null 2>&1
fi
# cấu hình dnsmasq chỉ listen pan0
if ! grep -q "interface=pan0" /etc/dnsmasq.conf 2>/dev/null; then
    echo -e "interface=pan0\nbind-interfaces\ndhcp-range=172.30.99.10,172.30.99.50,12h\nlisten-address=172.30.99.1" | sudo tee -a /etc/dnsmasq.conf
fi
sudo systemctl enable --now dnsmasq
logger -t $LOG_TAG "BT NAP ready: pan0=172.30.99.1/24, DHCP 172.30.99.10-50"
