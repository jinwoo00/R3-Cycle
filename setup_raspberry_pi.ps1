# R3-Cycle Raspberry Pi Setup Script for Windows
# Automates file transfer and setup preparation
#
# Usage: .\setup_raspberry_pi.ps1
#
# This script prepares all files and creates a deployment package
# that can be easily transferred to Raspberry Pi

param(
    [string]$PiIP = "",
    [string]$PiUser = "pi",
    [string]$PiPath = "/home/pi/r3cycle",
    [switch]$TransferFiles = $false,
    [switch]$RemoteSetup = $false
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "R3-Cycle Raspberry Pi Setup Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if we're in the right directory
if (-not (Test-Path "raspberry_pi")) {
    Write-Host "[ERROR] Please run this script from the R3-Cycle project root directory" -ForegroundColor Red
    exit 1
}

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$deployDir = "raspberry_pi_deploy_$timestamp"

Write-Host "[1/5] Creating deployment package..." -ForegroundColor Yellow

# Create deployment directory
New-Item -ItemType Directory -Force -Path $deployDir | Out-Null

# Copy all Raspberry Pi files
Write-Host "  Copying Raspberry Pi files..." -ForegroundColor Gray
Copy-Item -Path "raspberry_pi\*" -Destination $deployDir -Recurse -Force

# Create setup script that will be run on Raspberry Pi
$setupScript = @"
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
if [ "$EUID" -ne 0 ]; then
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

"@

# Save setup script
$setupScript | Out-File -FilePath "$deployDir\setup.sh" -Encoding ASCII

# Create README for deployment
$readme = @"
# R3-Cycle Raspberry Pi Deployment Package

## Quick Setup Instructions

### Option 1: USB Drive Transfer (Easiest)

1. **Copy this entire folder to USB drive**
   - Copy the `raspberry_pi_deploy_*` folder to a USB drive

2. **Transfer to Raspberry Pi:**
   - Insert USB drive into Raspberry Pi
   - Mount USB drive:
     ```bash
     sudo mkdir -p /mnt/usb
     sudo mount /dev/sda1 /mnt/usb
     # Or use: lsblk to find your USB device
     ```
   - Copy files:
     ```bash
     sudo cp -r /mnt/usb/raspberry_pi_deploy_* /home/pi/r3cycle
     sudo chown -R pi:pi /home/pi/r3cycle
     ```
   - Run setup:
     ```bash
     cd /home/pi/r3cycle
     sudo bash setup.sh
     ```

3. **Reboot:**
   ```bash
   sudo reboot
   ```

### Option 2: SCP Transfer (Requires SSH/Network)

From Windows PowerShell:
```powershell
scp -r raspberry_pi_deploy_* pi@<RASPBERRY_PI_IP>:/home/pi/r3cycle
```

Then SSH to Raspberry Pi:
```bash
ssh pi@<RASPBERRY_PI_IP>
cd /home/pi/r3cycle
sudo bash setup.sh
sudo reboot
```

### Option 3: Git Clone (If code is in Git repository)

On Raspberry Pi:
```bash
cd /home/pi
git clone <your-repo-url> r3cycle
cd r3cycle
sudo bash setup.sh
sudo reboot
```

## After Setup

1. **Edit configuration:**
   ```bash
   nano config.py
   # Update: API_BASE_URL = "http://YOUR_BACKEND_IP:3000/api"
   ```

2. **Run tests:**
   ```bash
   # Test backend connection
   python3 tests/test_api.py
   
   # Test all hardware
   sudo python3 tests/run_all_tests.py
   ```

3. **Start system:**
   ```bash
   sudo python3 main.py
   ```

## Files Included

- `main.py` - Main program
- `config.py` - Configuration file
- `realtime_client.py` - Real-time WebSocket client
- `tests/` - Hardware test scripts
- `setup.sh` - Automated setup script
- All other required files

Generated: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")

"@

$readme | Out-File -FilePath "$deployDir\README.txt" -Encoding UTF8

Write-Host "  [OK] Deployment package created: $deployDir" -ForegroundColor Green

# Create ZIP archive for easy transfer
Write-Host ""
Write-Host "[2/5] Creating ZIP archive..." -ForegroundColor Yellow
$zipFile = "$deployDir.zip"
Compress-Archive -Path $deployDir -DestinationPath $zipFile -Force
Write-Host "  [OK] ZIP archive created: $zipFile" -ForegroundColor Green

# Create automated transfer script (if IP provided)
if ($PiIP -ne "") {
    Write-Host ""
    Write-Host "[3/5] Creating transfer script for IP: $PiIP..." -ForegroundColor Yellow
    
    $transferScriptContent = @"
# Automated Transfer Script
# Run this from PowerShell (as Administrator if needed)

`$PiIP = "$PiIP"
`$PiUser = "$PiUser"
`$PiPath = "$PiPath"

Write-Host "Transferring files to Raspberry Pi..." -ForegroundColor Yellow
Write-Host "Target: `$PiUser@`$PiIP:`$PiPath" -ForegroundColor Gray

# Create directory on Pi
ssh `$PiUser@`$PiIP "mkdir -p `$PiPath"

# Transfer files
`$DeployDir = (Get-ChildItem -Filter "raspberry_pi_deploy_*" -Directory | Select-Object -First 1).Name
scp -r `$DeployDir/* `$PiUser@`$PiIP:`$PiPath/

Write-Host ""
Write-Host "[OK] Files transferred successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. SSH to Raspberry Pi: ssh `$PiUser@`$PiIP" -ForegroundColor White
Write-Host "2. Run setup: cd `$PiPath && sudo bash setup.sh" -ForegroundColor White
Write-Host "3. Reboot: sudo reboot" -ForegroundColor White
"@

    $transferScriptContent | Out-File -FilePath "transfer_to_pi.ps1" -Encoding UTF8
    Write-Host "  [OK] Transfer script created: transfer_to_pi.ps1" -ForegroundColor Green
}

Write-Host ""
Write-Host "[4/5] Creating one-click setup script..." -ForegroundColor Yellow

# Create a comprehensive setup guide
$oneClickGuide = @"
# ONE-CLICK SETUP GUIDE

## Step 1: Prepare on Windows (You are here!)

This script has created:
- Deployment package: $deployDir
- ZIP archive: $zipFile
- Setup script for Raspberry Pi: $deployDir\setup.sh

## Step 2: Transfer to Raspberry Pi

### Method A: USB Drive (Recommended)
1. Copy $zipFile to USB drive
2. Insert USB into Raspberry Pi
3. Extract: unzip $zipFile -d /home/pi
4. Run: cd /home/pi/$deployDir && sudo bash setup.sh

### Method B: Network Transfer
From PowerShell (if Pi IP known):
```powershell
.\transfer_to_pi.ps1
```

Or manually:
```powershell
scp -r $deployDir pi@<PI_IP>:/home/pi/r3cycle
```

### Method C: Manual Copy
- Copy folder to Raspberry Pi via any method
- Extract files to /home/pi/r3cycle

## Step 3: Run Setup on Raspberry Pi

```bash
cd /home/pi/r3cycle
sudo bash setup.sh
sudo reboot
```

## Step 4: After Reboot

1. Edit config.py:
   ```bash
   nano config.py
   # Change: API_BASE_URL = "http://YOUR_BACKEND_IP:3000/api"
   ```

2. Test connection:
   ```bash
   python3 tests/test_api.py
   ```

3. Test hardware:
   ```bash
   sudo python3 tests/run_all_tests.py
   ```

4. Run system:
   ```bash
   sudo python3 main.py
   ```

## That's it! Ready to deploy.

"@

$oneClickGuide | Out-File -FilePath "SETUP_INSTRUCTIONS.txt" -Encoding UTF8
Write-Host "  [OK] Setup guide created: SETUP_INSTRUCTIONS.txt" -ForegroundColor Green

Write-Host ""
Write-Host "[5/5] Summary" -ForegroundColor Yellow
Write-Host ""
Write-Host "[OK] Deployment package created:" -ForegroundColor Green
Write-Host "  - Folder: $deployDir" -ForegroundColor White
Write-Host "  - ZIP: $zipFile" -ForegroundColor White
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Copy $zipFile to USB drive" -ForegroundColor White
Write-Host "2. Transfer to Raspberry Pi" -ForegroundColor White
Write-Host "3. Extract and run: sudo bash setup.sh" -ForegroundColor White
Write-Host "4. Reboot Raspberry Pi" -ForegroundColor White
Write-Host ""
Write-Host "See SETUP_INSTRUCTIONS.txt for detailed guide" -ForegroundColor Gray
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Setup preparation complete! [OK]" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
