#!/bin/bash
# Enable SSH on Raspberry Pi 5
# Run this script on Pi 5 console (not via SSH)

echo "=========================================="
echo "Raspberry Pi 5 SSH Enable Script"
echo "=========================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "❌ Please run as root (sudo $0)"
    exit 1
fi

echo "[1/3] Checking SSH service..."
if systemctl is-active --quiet sshd; then
    echo "✅ SSH service is already running"
else
    echo "⚠️ SSH service is not running"
    
    echo "[2/3] Starting SSH service..."
    systemctl start sshd
    sleep 2
    
    if systemctl is-active --quiet sshd; then
        echo "✅ SSH service started successfully"
    else
        echo "❌ Failed to start SSH service"
        exit 1
    fi
fi

echo "[3/3] Enabling SSH auto-start on boot..."
systemctl enable sshd
sleep 2

if systemctl is-enabled --quiet sshd; then
    echo "✅ SSH enabled for auto-start"
else
    echo "❌ Failed to enable SSH auto-start"
    exit 1
fi

echo ""
echo "=========================================="
echo "✅ SSH ENABLED SUCCESSFULLY"
echo "=========================================="
echo ""
echo "SSH service status:"
systemctl status sshd --no-pager | head -10
echo ""
echo "Pi 5 IP address:"
hostname -I
echo ""
echo "You can now SSH from PC:"
echo "  ssh quanpt1@192.168.1.10"
echo ""