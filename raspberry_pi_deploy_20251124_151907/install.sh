#!/bin/bash
###############################################################################
# R3-Cycle Installation Script for Raspberry Pi
# Installs all required dependencies and configures system
#
# Usage: sudo bash install.sh
#
# Author: R3-Cycle Team
# Last Updated: 2025-11-21
###############################################################################

set -e  # Exit on error

echo "======================================"
echo "R3-Cycle Installation Script"
echo "======================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "[ERROR] Please run as root: sudo bash install.sh"
    exit 1
fi

echo "[1/7] Updating package manager..."
apt-get update

echo ""
echo "[2/7] Installing system dependencies..."
apt-get install -y \
    python3-pip \
    python3-dev \
    python3-smbus \
    i2c-tools \
    git

echo ""
echo "[3/7] Installing Python libraries..."
pip3 install --upgrade pip

# Core libraries
pip3 install RPi.GPIO requests python-socketio

# RFID Reader (RC522)
pip3 install mfrc522

# Load Cell (HX711)
pip3 install hx711

# LCD Display (I2C)
pip3 install RPLCD

# I2C communication
pip3 install smbus2

echo ""
echo "[4/7] Enabling SPI interface (for RFID)..."
if ! grep -q "^dtparam=spi=on" /boot/config.txt; then
    echo "dtparam=spi=on" >> /boot/config.txt
    echo "SPI enabled (reboot required)"
else
    echo "SPI already enabled"
fi

echo ""
echo "[5/7] Enabling I2C interface (for LCD)..."
if ! grep -q "^dtparam=i2c_arm=on" /boot/config.txt; then
    echo "dtparam=i2c_arm=on" >> /boot/config.txt
    echo "I2C enabled (reboot required)"
else
    echo "I2C already enabled"
fi

# Add user to i2c group
usermod -aG i2c pi

echo ""
echo "[6/7] Creating log directory..."
mkdir -p /home/pi/r3cycle
chown pi:pi /home/pi/r3cycle
touch /home/pi/r3cycle/r3cycle.log
chown pi:pi /home/pi/r3cycle/r3cycle.log

echo ""
echo "[7/7] Setting file permissions..."
chmod +x /home/pi/r3cycle/main.py 2>/dev/null || echo "main.py not found yet"

echo ""
echo "======================================"
echo "Installation Complete!"
echo "======================================"
echo ""
echo "Next steps:"
echo "1. Copy Python files to /home/pi/r3cycle/"
echo "2. Edit config.py with your server IP"
echo "3. Run: sudo python3 /home/pi/r3cycle/main.py"
echo ""
echo "Optional: Install systemd service for auto-start"
echo "  sudo cp r3cycle.service /etc/systemd/system/"
echo "  sudo systemctl enable r3cycle.service"
echo "  sudo systemctl start r3cycle.service"
echo ""
echo "IMPORTANT: Reboot required for SPI/I2C changes"
echo "  sudo reboot"
echo ""
