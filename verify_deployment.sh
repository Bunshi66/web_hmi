#!/bin/bash
# verify_deployment.sh - Run this on the NUC after cloning to verify the environment

set -e
echo "Starting Web HMI Deployment Verification..."

# 1. Check if MVS is installed
echo ">>> Checking for MVS SDK..."
if [ -d "/opt/MVS" ]; then
    echo "[OK] /opt/MVS exists."
else
    echo "[ERROR] /opt/MVS not found! Please install the Hikrobot MVS Linux SDK first."
    echo "Without it, docker-compose will fail to mount the volume."
    exit 1
fi

# 2. Check Docker
echo ">>> Checking Docker..."
if command -v docker &> /dev/null; then
    echo "[OK] Docker is installed."
else
    echo "[ERROR] Docker is not installed."
    exit 1
fi

# 3. Check Docker Compose
if command -v docker-compose &> /dev/null || docker compose version &> /dev/null; then
    echo "[OK] Docker Compose is available."
else
    echo "[ERROR] Docker Compose is not installed."
    exit 1
fi

# 4. Check Network Interfaces for MTU > 1500 (Jumbo frames)
echo ">>> Checking Network MTU settings (looking for Jumbo Frames)..."
MTU_FOUND=false
for iface in $(ip -o link show | awk -F': ' '{print $2}'); do
    mtu=$(cat /sys/class/net/$iface/mtu 2>/dev/null || echo 1500)
    if [ "$mtu" -gt 1500 ]; then
        echo "[OK] Interface $iface has Jumbo Frames enabled (MTU=$mtu)."
        MTU_FOUND=true
    fi
done

if [ "$MTU_FOUND" = false ]; then
    echo "[WARNING] No interfaces found with MTU > 1500! Jumbo frames are strongly recommended for GigE Vision."
    echo "Run: sudo ip link set dev <interface_name> mtu 9000"
fi

echo "======================================"
echo "Verification complete! You can now run:"
echo "sudo docker-compose up -d"
