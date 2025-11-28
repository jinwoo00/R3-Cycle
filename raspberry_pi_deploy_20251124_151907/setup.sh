#!/bin/bash
###############################################################################
# R3-Cycle Automated Setup Script
# Run this script on Raspberry Pi after transferring files
#
# Usage: bash setup.sh
###############################################################################

set -e

echo "======================================"
echo "R3-Cycle Automated Setup"
echo "======================================"
echo ""

# Check if running as root
if [ "" -ne 0 ]; then
    echo "[ERROR] Please run as root: sudo bash setup.sh"
    exit 1
fi

# Step 1: Update system
echo "[1/6] Updating system packages..."
apt-get update -y
apt-get upgrade -y

# Step 2: Install system dependencies
echo ""
echo "[2/6] Installing system dependencies..."
apt-get install -y \
    python3-pip \
    python3-dev \
    python3-smbus \
    i2c-tools \
    git \
    vim \
    htop

# Step 3: Install Python libraries
echo ""
echo "[3/6] Installing Python libraries..."
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

# Step 4: Enable interfaces
echo ""
echo "[4/6] Enabling GPIO interfaces..."

# Enable SPI
if ! grep -q "^dtparam=spi=on" /boot/config.txt; then
    echo "dtparam=spi=on" >> /boot/config.txt
    echo "SPI enabled"
fi

# Enable I2C
if ! grep -q "^dtparam=i2c_arm=on" /boot/config.txt; then
    echo "dtparam=i2c_arm=on" >> /boot/config.txt
    echo "I2C enabled"
fi

# Enable UART
if ! grep -q "^enable_uart=1" /boot/config.txt; then
    echo "enable_uart=1" >> /boot/config.txt
    echo "UART enabled"
fi

# Add user to i2c group
usermod -aG i2c pi

# Step 5: Create directories and set permissions
echo ""
echo "[5/6] Setting up directories..."
mkdir -p /home/pi/r3cycle
chown pi:pi /home/pi/r3cycle

# Create log directory
mkdir -p /home/pi/r3cycle/logs
touch /home/pi/r3cycle/logs/r3cycle.log
chown pi:pi /home/pi/r3cycle/logs
chown pi:pi /home/pi/r3cycle/logs/r3cycle.log

# Step 6: Set file permissions
echo ""
echo "[6/6] Setting file permissions..."
if [ -f "/home/pi/r3cycle/main.py" ]; then
    chmod +x /home/pi/r3cycle/main.py
fi
if [ -f "/home/pi/r3cycle/install.sh" ]; then
    chmod +x /home/pi/r3cycle/install.sh
fi

echo ""
echo "======================================"
echo "Setup Complete!"
echo "======================================"
echo ""
echo "IMPORTANT: Reboot required for interface changes"
echo "  sudo reboot"
echo ""
echo "After reboot:"
echo "1. Edit config.py with your backend IP"
echo "2. Run tests: python3 tests/test_api.py"
echo "3. Test hardware: sudo python3 tests/test_lcd.py"
echo ""

