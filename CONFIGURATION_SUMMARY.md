# R3-CYCLE CONFIGURATION SUMMARY

**Print this document and fill in the blanks before deployment**

---

## 📋 NETWORK CONFIGURATION

### Backend Server

```
Computer/Server Name:     _______________________________

IP Address:               _______________________________
                         (Example: 192.168.1.50)

Port:                     3000 (default)

Full API URL:            http://_________________:3000/api
```

### Raspberry Pi

```
Hostname:                 r3cycle (default)

IP Address:               _______________________________
                         (Example: 192.168.1.100)

WiFi Network (SSID):      _______________________________

WiFi Password:            _______________________________
```

### Network Verification

```bash
# From Raspberry Pi, test connectivity:
ping YOUR_SERVER_IP
curl http://YOUR_SERVER_IP:3000/api/health
```

- [ ] Raspberry Pi can reach backend server
- [ ] Both devices on same network

---

## 🔑 AUTHENTICATION CREDENTIALS

### Machine Authentication

**These MUST match between backend and Raspberry Pi!**

```
Machine ID:               RPI_001 (default)

Machine Secret:           test-secret (default)
                         ⚠️ Change in production!
```

**Where to update if changed:**

1. **Backend:** `routes/iot.js` (authenticateMachine middleware)
2. **Raspberry Pi:** `config.py` lines 16-17

### Firebase Configuration

```
Project ID:               _______________________________

Project Name:             _______________________________

Service Account:          [Configured in firebaseConfig.js]
```

- [ ] Firebase project accessible
- [ ] Firestore database created

---

## 🗄️ DATABASE CONFIGURATION

### Required Collections

- [ ] `users` - User accounts
- [ ] `machines` - Machine records
- [ ] `transactions` - Transaction logs
- [ ] `redemptions` - Reward requests
- [ ] `alerts` - System alerts

### Machine Document (Firestore)

**Collection:** `machines`
**Document ID:** `RPI_001` (must match MACHINE_ID)

```javascript
{
  id: "RPI_001",
  location: "_______________________________",
  status: "offline",
  bondPaperStock: 100,
  bondPaperCapacity: 100,
  // ... other fields auto-created
}
```

- [ ] Machine document exists in Firestore
- [ ] Document ID matches `MACHINE_ID`

### Test User Account

**For testing, you need at least one user with RFID linked:**

```
User Email:               _______________________________

User Name:                _______________________________

RFID Tag ID:              _______________________________
                         (From your physical RFID card)

Initial Points:           0
```

- [ ] User account created
- [ ] Email verified
- [ ] RFID tag linked (or use "TEST12345" for testing)

---

## 🥧 RASPBERRY PI CONFIG.PY SETTINGS

**File:** `/home/pi/r3cycle/config.py`

### 1. API Configuration (Lines 13-17)

```python
# CRITICAL: Update with your actual server IP!
API_BASE_URL = "http://_________________:3000/api"
                      ↑ YOUR SERVER IP HERE

MACHINE_ID = "RPI_001"
MACHINE_SECRET = "test-secret"
```

### 2. GPIO Pin Assignments (Lines 26-52)

**Default pins (DO NOT CHANGE unless wiring differs):**

```python
PIN_RFID_RST = 25
PIN_LOAD_CELL_DT = 5
PIN_LOAD_CELL_SCK = 6
PIN_IR_SENSOR = 17
PIN_INDUCTIVE_SENSOR = 27
PIN_SERVO_COLLECTION = 18
PIN_SERVO_REWARD = 23
PIN_LED_RED = 24
```

- [ ] Pins match your physical wiring

### 3. LCD I2C Address (Line 48)

```python
LCD_I2C_ADDRESS = 0x27  # or 0x3f
```

**To verify:**

```bash
sudo i2cdetect -y 1
# Look for LCD address (usually 27 or 3f)
```

```
Detected I2C Address:     _______  (hex, e.g., 27 or 3f)
```

- [ ] LCD I2C address verified
- [ ] Updated in config.py if different from 0x27

### 4. Load Cell Calibration (Line 60)

```python
LOAD_CELL_REFERENCE_UNIT = _______
                          ↑ Update after calibration!
```

**Calibration Procedure:**

1. Run: `sudo python3 tests/test_loadcell.py`
2. Follow calibration wizard
3. Place 100g weight on sensor
4. Note calculated reference unit
5. Update this value in config.py

```
Calibration Weight Used:  _______ grams

Calculated Reference Unit: _______

Updated in config.py:      [ ] Yes  [ ] No
```

### 5. Weight Thresholds (Lines 63-64)

```python
MIN_WEIGHT = 1.0   # grams
MAX_WEIGHT = 20.0  # grams
```

- [ ] Thresholds match backend validation (utils/validation.js)

---

## 🔌 HARDWARE WIRING

### Component Connection Status

| Component | GPIO Pin | Status | Notes |
|-----------|----------|--------|-------|
| RC522 RFID (via converter) | 8-11, 25 | [ ] Wired | SPI interface |
| HX711 Load Cell | 5, 6 | [ ] Wired | DT, SCK |
| IR Sensor | 17 | [ ] Wired | Paper detection |
| Inductive Sensor | 27 | [ ] Wired | Metal detection |
| LCD I2C | 2, 3 | [ ] Wired | SDA, SCL |
| Servo #1 (Collection) | 18 | [ ] Wired | External 5V ⚠️ |
| Servo #2 (Reward) | 23 | [ ] Wired | External 5V ⚠️ |
| LED Red | 24 | [ ] Wired | Via 220Ω resistor |
| Logic Level Converter | - | [ ] Wired | 3.3V ↔ 5V |

### Power Supply

```
Raspberry Pi Power:       5V ___ A (min 3A recommended)

Servo External Power:     5V ___ A (min 2A required)
                         ⚠️ NEVER from Pi 5V pin!

Shared Ground:            [ ] Connected
```

### Wiring Verification

- [ ] No short circuits (tested with multimeter)
- [ ] 3.3V rail measures ~3.3V
- [ ] 5V rail measures ~5V
- [ ] All grounds connected (Pi + servos + sensors)
- [ ] Logic converter LV → 3.3V, HV → 5V
- [ ] Servos powered externally (NOT from Pi)

---

## 🧪 TESTING CHECKLIST

### Backend Server Tests

```bash
# 1. Start server
npm run xian

# 2. Test all APIs
.\test-api.ps1
```

- [ ] Server starts without errors
- [ ] All 16 API endpoints pass
- [ ] Firebase connection successful

### Raspberry Pi API Test (No Hardware)

```bash
python3 tests/test_api.py
```

- [ ] All 5/5 tests pass
- [ ] Network latency < 1000ms

### Individual Sensor Tests (With Hardware)

```bash
# Test each sensor separately
sudo python3 tests/test_lcd.py
sudo python3 tests/test_rfid.py
sudo python3 tests/test_loadcell.py  # Calibrate here!
sudo python3 tests/test_ir_sensor.py
sudo python3 tests/test_inductive.py
```

**Test Results:**

- [ ] LCD displays messages correctly
- [ ] RFID reads cards: Tag ID = _______________________
- [ ] Load cell calibrated: Ref Unit = _______
- [ ] IR sensor detects paper
- [ ] Inductive sensor detects metal

### Complete System Test

```bash
sudo python3 /home/pi/r3cycle/main.py
```

**Transaction Flow:**

1. [ ] LCD shows "R3-Cycle Ready / Scan RFID Card"
2. [ ] Scan RFID → User verified
3. [ ] LCD shows "Hello [Name]! / Insert paper"
4. [ ] Insert paper → IR detects
5. [ ] LCD shows "Weighing paper..."
6. [ ] Weight measured: _______ grams
7. [ ] Metal detected: [ ] Yes  [ ] No
8. [ ] Transaction submitted to backend
9. [ ] LCD shows "Success! +X / Total: Y pts"
10. [ ] Backend Firestore updated

**Firestore Verification:**

- [ ] Transaction document created in `transactions` collection
- [ ] User `currentPoints` updated
- [ ] Machine `lastHeartbeat` updated

---

## 🚀 PRODUCTION DEPLOYMENT

### Systemd Service Installation

```bash
sudo cp /home/pi/r3cycle/r3cycle.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable r3cycle.service
sudo systemctl start r3cycle.service
sudo systemctl status r3cycle.service
```

- [ ] Service installed
- [ ] Service enabled (auto-start)
- [ ] Service running (active)
- [ ] Service survives reboot

### Log Monitoring

```bash
# Real-time logs
sudo journalctl -u r3cycle.service -f

# Or log file
tail -f /home/pi/r3cycle/r3cycle.log
```

- [ ] Logs are being written
- [ ] No critical errors in logs

---

## 📞 TROUBLESHOOTING REFERENCE

### Common Issues

| Issue | Check | Fix |
|-------|-------|-----|
| API connection failed | Server IP in config.py | Update API_BASE_URL |
| LCD not detected | I2C address | Run `i2cdetect -y 1`, update config |
| RFID not reading | SPI enabled | `sudo raspi-config` → Enable SPI |
| Load cell inaccurate | Calibration | Run `test_loadcell.py`, update ref unit |
| Servo not moving | External power | Check 5V supply, shared ground |
| Service won't start | Permissions | Check `/home/pi/r3cycle/` ownership |

### Support Commands

```bash
# View system logs
sudo journalctl -b

# Check network
ifconfig wlan0

# Check SPI devices
ls /dev/spidev*

# Check I2C devices
sudo i2cdetect -y 1

# Test API connectivity
curl http://YOUR_SERVER_IP:3000/api/health
```

---

## ✅ FINAL CHECKLIST

**Before declaring system operational:**

### Backend ✅
- [ ] Server running and accessible
- [ ] All APIs tested and working
- [ ] Machine document exists in Firestore
- [ ] Test user with RFID exists

### Raspberry Pi ✅
- [ ] Software installed and configured
- [ ] config.py updated with server IP
- [ ] All sensors tested individually
- [ ] Load cell calibrated

### Hardware ✅
- [ ] All components wired correctly
- [ ] Servos powered externally
- [ ] No short circuits
- [ ] Power supplies tested

### Integration ✅
- [ ] Complete transaction flow works
- [ ] Backend receives data
- [ ] User points updated
- [ ] LCD feedback working

### Production ✅
- [ ] Systemd service installed
- [ ] Auto-start enabled
- [ ] Logs accessible
- [ ] System survives reboot

---

## 🎯 SYSTEM READY FOR OPERATION

**Date deployed:** _______________________

**Deployed by:** _______________________

**Location:** _______________________

**Initial stock level:** _______ sheets

**Notes:**

```
_____________________________________________________________

_____________________________________________________________

_____________________________________________________________
```

---

**Congratulations! Your R3-Cycle system is operational! ♻️**

For ongoing maintenance, refer to [RASPBERRY_PI_SETUP.md](RASPBERRY_PI_SETUP.md) maintenance section.
