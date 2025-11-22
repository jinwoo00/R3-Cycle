# RASPBERRY PI SETUP GUIDE

Complete deployment guide for R3-Cycle IoT Paper Recycling System on Raspberry Pi Zero 2 W.

---

## 📋 TABLE OF CONTENTS

1. [Hardware Requirements](#hardware-requirements)
2. [Raspberry Pi OS Setup](#raspberry-pi-os-setup)
3. [Hardware Wiring](#hardware-wiring)
4. [Software Installation](#software-installation)
5. [Configuration](#configuration)
6. [Testing](#testing)
7. [Deployment](#deployment)
8. [Troubleshooting](#troubleshooting)
9. [Maintenance](#maintenance)

---

## 🔧 HARDWARE REQUIREMENTS

### Required Components

| # | Component | Qty | Purpose | Notes |
|---|-----------|-----|---------|-------|
| 1 | Raspberry Pi Zero 2 W | 1 | Main controller | Must have WiFi |
| 2 | HX711 + 5kg Load Cell | 1 | Weight measurement | 1-20g range |
| 3 | RC522 RFID Reader | 1 | User identification | SPI interface |
| 4 | IR Obstacle Sensor | 1 | Paper detection | Digital output |
| 5 | Inductive Proximity Sensor (LJ12A3-4-ZBX) | 1 | Metal detection | 4mm range |
| 6 | LCD 16x2 with I2C Module | 1 | User feedback | I2C address 0x27 |
| 7 | SG90-180 Servo Motor | 2 | Paper collection & dispensing | 5V external power |
| 8 | LED Red | 3 | Error indicators | 220Ω resistor |
| 9 | Logic Level Converter | 1 | 3.3V ↔ 5V | For RC522 SPI |
| 10 | 5V 3A Power Supply | 1 | Pi + peripherals | Micro USB |
| 11 | 16GB microSD Card | 1 | OS storage | Class 10 or better |

### Tools Needed

- MicroSD card reader
- PuTTY (SSH client for Windows)
- WinSCP or PSCP (file transfer)
- Multimeter (for testing)
- Screwdriver
- Wire strippers
- Soldering iron (optional)

---

## 💻 RASPBERRY PI OS SETUP

### Step 1: Install Raspberry Pi OS

1. **Download Raspberry Pi Imager**
   - Visit: https://www.raspberrypi.com/software/
   - Install for Windows

2. **Flash OS to microSD Card**
   ```
   - Insert microSD card into PC
   - Open Raspberry Pi Imager
   - Choose OS: "Raspberry Pi OS Lite (64-bit)" (headless, no desktop)
   - Choose Storage: Select your microSD card
   - Click gear icon (Advanced Options):
     ✓ Enable SSH (use password authentication)
     ✓ Set username: pi
     ✓ Set password: [your password]
     ✓ Configure WiFi:
       - SSID: [your network name]
       - Password: [your WiFi password]
       - Country: [your country code]
     ✓ Set hostname: r3cycle
   - Click "Write" and wait for completion
   ```

3. **Boot Raspberry Pi**
   ```
   - Insert microSD card into Raspberry Pi
   - Connect power supply
   - Wait 2 minutes for first boot
   ```

### Step 2: Find Raspberry Pi IP Address

**Method 1: Router Admin Panel**
- Login to your router
- Look for device named "r3cycle" or "raspberrypi"
- Note the IP address (e.g., 192.168.1.100)

**Method 2: Network Scanner**
- Use tool like "Advanced IP Scanner" (Windows)
- Scan your local network
- Find Raspberry Pi by hostname

### Step 3: Connect via PuTTY

1. **Open PuTTY**
   ```
   Host Name: 192.168.1.100 (your Pi's IP)
   Port: 22
   Connection Type: SSH
   ```

2. **Login**
   ```
   login as: pi
   password: [your password]
   ```

3. **Update System**
   ```bash
   sudo apt-get update
   sudo apt-get upgrade -y
   ```

### Step 4: Enable Interfaces

```bash
sudo raspi-config
```

Navigate and enable:
- `3 Interface Options` → `I2 SSH` → **Enable**
- `3 Interface Options` → `I4 SPI` → **Enable** (for RFID)
- `3 Interface Options` → `I5 I2C` → **Enable** (for LCD)

Select "Finish" and **Reboot**:
```bash
sudo reboot
```

Wait 1 minute, then reconnect via PuTTY.

---

## 🔌 HARDWARE WIRING

### GPIO Pin Assignments (BCM Numbering)

| Component | GPIO Pin | Notes |
|-----------|----------|-------|
| **RC522 RFID** | | |
| - RST | GPIO 25 | Via logic converter |
| - SDA/SS | GPIO 8 (CE0) | Via logic converter |
| - MOSI | GPIO 10 | Via logic converter |
| - MISO | GPIO 9 | Via logic converter |
| - SCK | GPIO 11 | Via logic converter |
| **HX711 Load Cell** | | |
| - DT (Data) | GPIO 5 | Direct 5V connection |
| - SCK (Clock) | GPIO 6 | Direct 5V connection |
| **IR Sensor** | GPIO 17 | Direct 5V connection |
| **Inductive Sensor** | GPIO 27 | Direct 5V connection |
| **Servo #1 (Collection)** | GPIO 18 | PWM-capable, external 5V power |
| **Servo #2 (Reward)** | GPIO 23 | PWM-capable, external 5V power |
| **LED Red** | GPIO 24 | Via 220Ω resistor |
| **LCD I2C** | | |
| - SDA | GPIO 2 | Direct I2C connection |
| - SCL | GPIO 3 | Direct I2C connection |

### Wiring Diagram

```
┌────────────────────────────────────────────────────────────┐
│          Raspberry Pi Zero 2 W GPIO Pinout                 │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  3.3V ──┬─→ RC522 VCC (via Logic Converter LV)           │
│         └─→ Logic Converter LV Side                       │
│                                                            │
│  5V ────┬─→ HX711 VCC                                     │
│         ├─→ IR Sensor VCC                                  │
│         ├─→ Inductive Sensor VCC                           │
│         ├─→ LCD I2C VCC                                    │
│         ├─→ Logic Converter HV Side                        │
│         └─→ Servo Motors (EXTERNAL 5V SUPPLY REQUIRED!)   │
│                                                            │
│  GND ───┴─→ All components (shared ground)                │
│                                                            │
│  GPIO 2 (SDA) ────→ LCD I2C SDA                           │
│  GPIO 3 (SCL) ────→ LCD I2C SCL                           │
│  GPIO 5  ─────────→ HX711 DT                              │
│  GPIO 6  ─────────→ HX711 SCK                             │
│  GPIO 8  ─────────→ RC522 SDA (via Logic Converter)       │
│  GPIO 9  ─────────→ RC522 MISO (via Logic Converter)      │
│  GPIO 10 ─────────→ RC522 MOSI (via Logic Converter)      │
│  GPIO 11 ─────────→ RC522 SCK (via Logic Converter)       │
│  GPIO 17 ─────────→ IR Sensor OUT                         │
│  GPIO 18 ─────────→ Servo #1 Signal (PWM)                 │
│  GPIO 23 ─────────→ Servo #2 Signal (PWM)                 │
│  GPIO 24 ─────────→ LED Red (via 220Ω resistor)           │
│  GPIO 25 ─────────→ RC522 RST (via Logic Converter)       │
│  GPIO 27 ─────────→ Inductive Sensor OUT                  │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

### ⚠️ CRITICAL WARNINGS

1. **Servo Motor Power**
   - **DO NOT power servos from Raspberry Pi 5V pin!**
   - Servos draw high current (up to 2.5A) which will damage the Pi
   - Use external 5V power supply (2A minimum)
   - **MUST share ground** between Pi and external power

2. **Logic Level Converter**
   - RC522 operates at 3.3V but Pi SPI is 3.3V safe
   - Use bidirectional level converter for SPI pins (MOSI, MISO, SCK, SS, RST)
   - Connect Pi side to LV (Low Voltage)
   - Connect RC522 side to HV (High Voltage)

3. **Shared Ground**
   - All components MUST share common ground
   - External servo power supply ground → Pi GND
   - Sensor grounds → Pi GND

### Wiring Checklist

Before powering on, verify:

- [ ] All GPIO pins match the table above (no conflicts)
- [ ] RC522 connected via logic level converter
- [ ] Servos powered from external 5V supply
- [ ] All grounds connected together
- [ ] LED has 220Ω resistor
- [ ] No short circuits (use multimeter to test)
- [ ] All connections secure (solder if possible)

---

## 📦 SOFTWARE INSTALLATION

### Step 1: Transfer Files to Raspberry Pi

**Using PSCP (PuTTY SCP):**

```powershell
# From your Windows PC, open PowerShell in R3-Cycle directory

# Transfer entire raspberry_pi folder
pscp.exe -r raspberry_pi pi@192.168.1.100:/home/pi/r3cycle

# Or transfer individual files
pscp.exe raspberry_pi/config.py pi@192.168.1.100:/home/pi/r3cycle/
pscp.exe raspberry_pi/main.py pi@192.168.1.100:/home/pi/r3cycle/
pscp.exe raspberry_pi/install.sh pi@192.168.1.100:/home/pi/r3cycle/
```

**Using WinSCP (GUI):**

1. Open WinSCP
2. New Session:
   - File protocol: SCP
   - Host name: 192.168.1.100
   - User name: pi
   - Password: [your password]
3. Click "Login"
4. Drag and drop `raspberry_pi` folder to `/home/pi/r3cycle/`

### Step 2: Run Installation Script

Connect to Pi via PuTTY:

```bash
# Navigate to directory
cd /home/pi/r3cycle

# Make install script executable
chmod +x install.sh

# Run installation (requires sudo)
sudo bash install.sh
```

The script will:
- Update package manager
- Install Python libraries (RPi.GPIO, requests, mfrc522, hx711, RPLCD, smbus2)
- Enable SPI and I2C interfaces
- Create log directory
- Set file permissions

**Reboot after installation:**

```bash
sudo reboot
```

### Step 3: Verify Installation

Reconnect via PuTTY and check:

```bash
# Check Python libraries
pip3 list | grep -E "RPi.GPIO|requests|mfrc522|hx711|RPLCD|smbus2"

# Check SPI enabled
ls /dev/spidev*
# Should show: /dev/spidev0.0  /dev/spidev0.1

# Check I2C enabled
ls /dev/i2c*
# Should show: /dev/i2c-1

# Scan I2C devices (LCD should appear at 0x27)
sudo i2cdetect -y 1
```

Expected output for I2C scan (with LCD connected):
```
     0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
00:          -- -- -- -- -- -- -- -- -- -- -- -- --
10: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
20: -- -- -- -- -- -- -- 27 -- -- -- -- -- -- -- --
30: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
40: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
50: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
60: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
70: -- -- -- -- -- -- -- --
```

If LCD shows at different address (e.g., 0x3f), update `config.py`:
```python
LCD_I2C_ADDRESS = 0x3f
```

---

## ⚙️ CONFIGURATION

### Edit config.py

```bash
nano /home/pi/r3cycle/config.py
```

**Critical settings to update:**

1. **API Base URL** (line 13)
   ```python
   API_BASE_URL = "http://192.168.1.50:3000/api"  # Your server IP
   ```

2. **Machine Credentials** (lines 16-17)
   ```python
   MACHINE_ID = "RPI_001"              # Unique machine ID
   MACHINE_SECRET = "your-secret-key"  # Change in production
   ```

3. **Load Cell Calibration** (after calibration, line 60)
   ```python
   LOAD_CELL_REFERENCE_UNIT = 437.5  # Your calculated value
   ```

Save: `Ctrl+O`, Enter
Exit: `Ctrl+X`

---

## 🧪 TESTING

### Test Individual Sensors

**1. Test API Connectivity** (no hardware needed)

```bash
cd /home/pi/r3cycle/tests
python3 test_api.py
```

Expected: All 5 tests should pass

**2. Test RFID Reader**

```bash
sudo python3 test_rfid.py
```

- Place RFID card near reader
- Should display tag ID

**3. Test Load Cell**

```bash
sudo python3 test_loadcell.py
```

- Follow calibration prompts
- Place known weight (e.g., 100g)
- Note the calculated reference unit
- Update `config.py` with value

**4. Test IR Sensor**

```bash
sudo python3 test_ir_sensor.py
```

- Insert paper/object into slot
- Should detect insertion

**5. Test Inductive Sensor**

```bash
sudo python3 test_inductive.py
```

- Bring metal object (staple, clip) within 4mm
- Should detect metal

**6. Test LCD Display**

```bash
sudo python3 test_lcd.py
```

- LCD should display test messages
- Verify all characters visible

### Test Complete System

```bash
cd /home/pi/r3cycle
sudo python3 main.py
```

**Expected flow:**
1. LCD shows "R3-Cycle Ready / Scan RFID Card"
2. Scan RFID → LCD shows "Card Detected / Verifying..."
3. If valid user → LCD shows "Hello [Name]! / Insert paper"
4. Insert paper → IR sensor detects → LCD shows "Weighing paper..."
5. Weight measured → Metal check → Transaction submitted
6. LCD shows success or rejection message

**Stop program:** `Ctrl+C`

---

## 🚀 DEPLOYMENT

### Option 1: Manual Start (Testing)

```bash
sudo python3 /home/pi/r3cycle/main.py
```

Logs appear in terminal.

### Option 2: Auto-Start on Boot (Production)

**Install systemd service:**

```bash
# Copy service file
sudo cp /home/pi/r3cycle/r3cycle.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable service (auto-start on boot)
sudo systemctl enable r3cycle.service

# Start service now
sudo systemctl start r3cycle.service
```

**Check status:**

```bash
sudo systemctl status r3cycle.service
```

**View logs:**

```bash
# Real-time logs
sudo journalctl -u r3cycle.service -f

# Or view log file
tail -f /home/pi/r3cycle/r3cycle.log
```

**Stop service:**

```bash
sudo systemctl stop r3cycle.service
```

**Disable auto-start:**

```bash
sudo systemctl disable r3cycle.service
```

---

## 🐛 TROUBLESHOOTING

### LCD Not Detected

**Symptoms:** `i2cdetect` shows no devices

**Solutions:**
1. Check wiring: SDA → GPIO 2, SCL → GPIO 3
2. Verify I2C enabled: `sudo raspi-config` → Interface Options → I2C
3. Reboot: `sudo reboot`
4. Test with multimeter: verify 5V power to LCD

### RFID Not Reading

**Symptoms:** `test_rfid.py` hangs or errors

**Solutions:**
1. Check SPI enabled: `ls /dev/spidev*`
2. Verify wiring via logic level converter
3. Check RC522 power (3.3V)
4. Try different RFID card
5. Reduce distance between card and reader (< 2cm)

### Load Cell Inaccurate

**Symptoms:** Weight readings fluctuate or incorrect

**Solutions:**
1. Re-run calibration: `sudo python3 tests/test_loadcell.py`
2. Ensure platform is stable (no vibrations)
3. Use precise known weight for calibration
4. Check HX711 connections (DT, SCK, VCC, GND)
5. Update `LOAD_CELL_REFERENCE_UNIT` in config.py

### API Connection Failed

**Symptoms:** `test_api.py` fails, "Connection refused"

**Solutions:**
1. Verify server is running: `npm run xian` on backend
2. Check API_BASE_URL in config.py matches server IP
3. Test ping: `ping 192.168.1.50`
4. Check firewall allows port 3000
5. Ensure Pi and server on same network

### Servo Motor Not Moving

**Symptoms:** Servo doesn't respond

**Solutions:**
1. **Verify external 5V power** (NOT from Pi!)
2. Check PWM signal wire connected (GPIO 18 or 23)
3. Ensure shared ground between Pi and servo power
4. Test servo with simple PWM test
5. Check servo power supply voltage (4.8-6V)

### System Crashes / GPIO Errors

**Symptoms:** "GPIO already in use" or random crashes

**Solutions:**
1. Clean up GPIO: `sudo python3 -c "import RPi.GPIO as GPIO; GPIO.cleanup()"`
2. Reboot: `sudo reboot`
3. Check no conflicting programs using GPIO
4. Review logs: `cat /home/pi/r3cycle/r3cycle.log`

### Service Won't Start

**Symptoms:** `systemctl status` shows "failed"

**Solutions:**
1. Check service file syntax: `sudo systemctl cat r3cycle.service`
2. Test manual start: `sudo python3 /home/pi/r3cycle/main.py`
3. Check file permissions: `ls -l /home/pi/r3cycle/`
4. View detailed errors: `sudo journalctl -u r3cycle.service -n 50`
5. Verify Python path: `which python3`

---

## 🔧 MAINTENANCE

### Regular Tasks

**Daily:**
- Check LCD for errors
- Monitor system logs
- Verify API connectivity

**Weekly:**
- Review transaction logs
- Check sensor health via admin dashboard
- Test backup paper stock

**Monthly:**
- Recalibrate load cell
- Clean RFID reader surface
- Check all wiring connections
- Update Raspberry Pi OS: `sudo apt-get update && sudo apt-get upgrade -y`

### System Commands

```bash
# View real-time logs
tail -f /home/pi/r3cycle/r3cycle.log

# Check system resources
htop

# Test network connectivity
ping 8.8.8.8

# View disk usage
df -h

# Check temperature
vcgencmd measure_temp

# Restart service
sudo systemctl restart r3cycle.service

# Clean up old logs
sudo find /home/pi/r3cycle/ -name "*.log.*" -mtime +30 -delete
```

### Backup Configuration

```bash
# Backup config and logs
cd /home/pi
tar -czf r3cycle-backup-$(date +%Y%m%d).tar.gz r3cycle/

# Copy to PC via PSCP (from Windows)
pscp.exe pi@192.168.1.100:/home/pi/r3cycle-backup-*.tar.gz C:\Backups\
```

---

## 📚 ADDITIONAL RESOURCES

### Documentation Files

- [CLAUDE.md](CLAUDE.md) - Complete development guide
- [RASPBERRY_PI_REDEMPTION.md](RASPBERRY_PI_REDEMPTION.md) - Servo dispensing system
- [API_TESTING.md](API_TESTING.md) - Backend API testing
- [PHASE3_SUMMARY.md](PHASE3_SUMMARY.md) - Redemption system details

### Useful Commands

```bash
# Check GPIO pin status
gpio readall

# Monitor I2C traffic
sudo i2cdetect -y 1

# Test SPI communication
ls -l /dev/spidev*

# View system logs
sudo journalctl -b

# Check network interfaces
ifconfig

# Test WiFi signal
iwconfig wlan0
```

### Python Debugging

```python
# Enable debug mode in config.py
DEBUG_MODE = True

# Simulate sensors without hardware
SIMULATE_RFID = True
SIMULATE_LOAD_CELL = True
```

---

## ✅ DEPLOYMENT CHECKLIST

Before production deployment:

- [ ] All sensors tested individually
- [ ] Load cell calibrated with known weight
- [ ] API connectivity verified
- [ ] RFID cards registered in web dashboard
- [ ] Servo motors dispensing correctly (external power!)
- [ ] LCD displaying messages clearly
- [ ] Complete transaction flow tested end-to-end
- [ ] Systemd service installed and enabled
- [ ] Backend server accessible from Pi network
- [ ] Machine credentials configured in config.py
- [ ] Logs directory created with proper permissions
- [ ] Wiring double-checked (no short circuits)
- [ ] External servo power supply rated 5V 2A minimum
- [ ] Admin dashboard showing machine as "online"
- [ ] Paper stock level monitoring working
- [ ] Alert generation tested (low stock, offline)

---

**System Ready for Production! 🎉**

For support, check logs at `/home/pi/r3cycle/r3cycle.log` or contact R3-Cycle development team.
