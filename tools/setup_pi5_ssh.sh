#!/bin/bash
# setup_pi5_ssh.sh - Tự động cấu hình SSH và các dịch vụ cần thiết trên Pi5
# Chạy script này sau khi có quyền truy cập vào Pi5

echo "=========================================="
echo "PI5 SETUP SCRIPT - SSH & SERVICES"
echo "=========================================="
echo ""

# 1. Enable SSH
echo "[1/5] Enabling SSH service..."
sudo systemctl start sshd
sudo systemctl enable sshd
if sudo systemctl is-active --quiet sshd; then
    echo "✅ SSH service started and enabled"
else
    echo "❌ Failed to start SSH service"
fi

# 2. Check SSH status
echo ""
echo "[2/5] SSH service status:"
sudo systemctl status sshd --no-pager | head -10

# 3. Check firewall (if ufw is installed)
echo ""
echo "[3/5] Checking firewall..."
if command -v ufw &> /dev/null; then
    sudo ufw allow 22/tcp
    echo "✅ Firewall rule added for SSH"
else
    echo "ℹ️  UFW not installed, skipping firewall config"
fi

# 4. Check SSH port
echo ""
echo "[4/5] Checking SSH port..."
sudo netstat -tlnp 2>/dev/null | grep :22 || sudo ss -tlnp | grep :22 || echo "⚠️  Port 22 not listening yet"

# 5. Test SSH from local
echo ""
echo "[5/5] Testing SSH loopback..."
ssh -o ConnectTimeout=2 localhost "echo 'SSH loopback test successful'" && echo "✅ SSH loopback OK" || echo "⚠️  SSH loopback failed"

echo ""
echo "=========================================="
echo "SETUP COMPLETE"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Test SSH from Windows: ssh quanpt1@192.168.1.10"
echo "2. If password auth fails, check /etc/ssh/sshd_config"
echo "3. Ensure user 'quanpt1' exists and has password set"
echo ""
echo "Script finished."