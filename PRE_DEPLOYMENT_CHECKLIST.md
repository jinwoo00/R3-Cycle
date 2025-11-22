# PRE-DEPLOYMENT CONFIGURATION CHECKLIST

**Purpose:** Verify all configurations are correct before hardware testing
**Status:** Use this checklist to ensure backend and Raspberry Pi are properly configured

---

## 📋 TABLE OF CONTENTS

1. [Backend Server Configuration](#backend-server-configuration)
2. [Raspberry Pi Configuration](#raspberry-pi-configuration)
3. [Network Configuration](#network-configuration)
4. [Database Configuration](#database-configuration)
5. [Hardware Verification](#hardware-verification)
6. [Testing Workflow](#testing-workflow)

---

## 🖥️ BACKEND SERVER CONFIGURATION

### 1. Server Must Be Running

**Check server is running:**

```powershell
# In R3-Cycle directory (Windows PowerShell)
npm run xian
```

**Expected output:**
```
Server running on port 3000
Firebase initialized
Session store ready
```

**Verify server is accessible:**

Open browser and navigate to: `http://localhost:3000`

You should see the R3-Cycle landing page.

---

### 2. Firebase Configuration

**File:** `models/firebaseConfig.js`

**Required:** Ensure Firebase credentials are valid

```javascript
// These should already be set up from Phase 1-4
const firebaseConfig = {
  apiKey: "YOUR_API_KEY",
  authDomain: "YOUR_PROJECT.firebaseapp.com",
  projectId: "YOUR_PROJECT_ID",
  // ...
};
```

**Verification:**
- [ ] Firebase project exists and is accessible
- [ ] Service account credentials valid
- [ ] Firestore database created
- [ ] Collections exist: `users`, `transactions`, `machines`, `redemptions`, `alerts`

---

### 3. Environment Variables

**File:** `.env` (if you're using environment variables)

**Check these are set (or defaults are correct):**

```bash
PORT=3000
NODE_ENV=development
SESSION_SECRET=your-session-secret-here
```

**Note:** Session secret is currently hardcoded in `index.js`. For production, move to `.env`.

---

### 4. Machine Authentication Credentials

**Current Default (from Phase 1):**

```javascript
// Used by Raspberry Pi to authenticate
MACHINE_ID: "RPI_001"
MACHINE_SECRET: "test-secret"
```

**Location in backend:** `routes/iot.js` (lines 46-63)

**Middleware:** `authenticateMachine()`

```javascript
const machineId = req.headers['x-machine-id'];
const machineSecret = req.headers['x-machine-secret'];
```

**⚠️ IMPORTANT:**
- These credentials MUST match between backend and Raspberry Pi `config.py`
- Change `"test-secret"` to a stronger secret in production

**Verification:**
- [ ] Default credentials: `MACHINE_ID = "RPI_001"`, `MACHINE_SECRET = "test-secret"`
- [ ] OR custom credentials documented for Raspberry Pi configuration

---

### 5. API Endpoints Status

**Verify all 16 endpoints are working:**

Run PowerShell test script:

```powershell
# In R3-Cycle directory
.\test-api.ps1
```

**Expected:** All tests pass with green checkmarks ✓

**Critical endpoints for Raspberry Pi:**
- [ ] `POST /api/rfid/verify` - User verification
- [ ] `POST /api/transaction/submit` - Transaction submission
- [ ] `POST /api/machine/heartbeat` - Machine status
- [ ] `GET /api/redemption/pending` - Redemption queue
- [ ] `POST /api/redemption/dispense` - Mark as dispensed
- [ ] `GET /api/health` - Health check

---

### 6. Sample Machine Record

**Verify machine exists in Firestore:**

Navigate to Firebase Console → Firestore Database → `machines` collection

**Expected document:**

```javascript
machines/RPI_001 {
  id: "RPI_001",
  location: "Main Campus",
  status: "offline",  // Will be "online" after Pi connects
  bondPaperStock: 100,
  bondPaperCapacity: 100,
  lastHeartbeat: null,
  sensorHealth: {
    rfid: "ok",
    loadCell: "ok",
    inductiveSensor: "ok",
    irSensor: "ok",
    servo: "ok"
  }
}
```

**If missing, create it manually or run:**

```powershell
node scripts/initializeDatabase.js
```

**Verification:**
- [ ] Machine document `RPI_001` exists in Firestore
- [ ] `bondPaperCapacity` set to 100
- [ ] `bondPaperStock` set to 100 (or actual stock level)

---

### 7. Test User Account

**You need at least one verified user with RFID card linked.**

**Option A: Use existing admin account**

1. Login to dashboard: `http://localhost:3000/login`
2. Navigate to "Link RFID Card"
3. Enter test RFID tag (e.g., `"TEST12345"` or actual RFID from your card)
4. Click "Link Card"

**Option B: Create new test user**

```powershell
# Register via web UI or manually add to Firestore
```

**Required fields for testing:**

```javascript
users/userId {
  email: "test@example.com",
  name: "Test User",
  role: "user",
  emailVerified: true,
  rfidTag: "YOUR_RFID_TAG_HERE",  // From actual RFID card
  currentPoints: 0,
  totalPaperRecycled: 0,
  totalTransactions: 0,
  bondsEarned: 0
}
```

**Verification:**
- [ ] Test user exists with `emailVerified: true`
- [ ] RFID tag linked (if you have physical RFID card)
- [ ] OR use `"TEST12345"` for initial API testing without hardware

---

## 🥧 RASPBERRY PI CONFIGURATION

### 1. File: `raspberry_pi/config.py`

**Critical settings to update:**

```python
# ============================================
# API CONFIGURATION
# ============================================

# TODO: UPDATE THIS WITH YOUR ACTUAL SERVER IP!
API_BASE_URL = "http://192.168.1.100:3000/api"  # ← CHANGE THIS!

# Machine authentication (must match backend)
MACHINE_ID = "RPI_001"
MACHINE_SECRET = "test-secret"  # ← MUST MATCH BACKEND!

# API request timeout (seconds)
API_TIMEOUT = 10
```

**How to find your server IP:**

**Option 1: If backend is on same computer as Raspberry Pi is connecting to:**

```powershell
# Windows PowerShell
ipconfig

# Look for "IPv4 Address" under your active network adapter
# Example: 192.168.1.50
```

**Option 2: If backend is on different computer:**

Use that computer's local IP address.

**Option 3: If testing locally on same Raspberry Pi:**

```python
API_BASE_URL = "http://localhost:3000/api"
```

**⚠️ CRITICAL CONFIGURATION:**

```python
# ============================================
# UPDATE THESE BEFORE DEPLOYMENT:
# ============================================

# 1. SERVER IP ADDRESS
API_BASE_URL = "http://YOUR_SERVER_IP:3000/api"  # ← Required!

# 2. MACHINE CREDENTIALS (must match backend)
MACHINE_ID = "RPI_001"           # ← Must match Firestore machine document
MACHINE_SECRET = "test-secret"   # ← Must match backend authentication

# 3. LOAD CELL CALIBRATION (after running test_loadcell.py)
LOAD_CELL_REFERENCE_UNIT = 1  # ← Update after calibration!
```

**Verification Checklist:**

- [ ] `API_BASE_URL` updated with actual server IP (NOT `192.168.1.100`)
- [ ] `MACHINE_ID` matches Firestore machine document ID
- [ ] `MACHINE_SECRET` matches backend authentication
- [ ] `LOAD_CELL_REFERENCE_UNIT` will be calibrated during testing

---

### 2. GPIO Pin Assignments (config.py)

**Verify these match your physical wiring:**

```python
# RFID Reader (RC522) - SPI Interface
PIN_RFID_RST = 25

# Load Cell (HX711)
PIN_LOAD_CELL_DT = 5
PIN_LOAD_CELL_SCK = 6

# IR Obstacle Sensor
PIN_IR_SENSOR = 17

# Inductive Proximity Sensor
PIN_INDUCTIVE_SENSOR = 27

# Servo Motors
PIN_SERVO_COLLECTION = 18
PIN_SERVO_REWARD = 23

# LED Indicator
PIN_LED_RED = 24

# LCD I2C
LCD_I2C_ADDRESS = 0x27  # ← May need adjustment!
```

**⚠️ LCD I2C Address:**

Most LCD I2C modules use `0x27`, but some use `0x3f`.

**To verify:**

```bash
# On Raspberry Pi after hardware is connected
sudo i2cdetect -y 1
```

**Expected output:**
```
     0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
00:          -- -- -- -- -- -- -- -- -- -- -- -- --
10: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
20: -- -- -- -- -- -- -- 27 -- -- -- -- -- -- -- --  ← LCD at 0x27
30: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
...
```

**If LCD shows at different address (e.g., `3f`):**

Update `config.py`:
```python
LCD_I2C_ADDRESS = 0x3f
```

**Verification:**
- [ ] GPIO pins match your physical wiring
- [ ] LCD I2C address verified with `i2cdetect`
- [ ] No pin conflicts

---

### 3. Weight Thresholds (config.py)

**Default values:**

```python
# Weight thresholds (grams)
MIN_WEIGHT = 1.0        # Minimum valid paper weight
MAX_WEIGHT = 20.0       # Maximum valid paper weight
```

**These should match backend validation:**

Check `utils/validation.js`:

```javascript
export function validatePaperWeight(weight) {
  const MIN_WEIGHT = 1;    // grams
  const MAX_WEIGHT = 20;   // grams
  // ...
}
```

**Verification:**
- [ ] Pi `MIN_WEIGHT = 1.0` matches backend `MIN_WEIGHT = 1`
- [ ] Pi `MAX_WEIGHT = 20.0` matches backend `MAX_WEIGHT = 20`

---

### 4. Timing Configuration (config.py)

**Default values:**

```python
# Machine heartbeat interval (seconds)
HEARTBEAT_INTERVAL = 60  # Send status every 60 seconds

# Redemption polling interval (seconds)
REDEMPTION_POLL_INTERVAL = 5  # Check redemptions every 5 seconds

# RFID scan timeout (seconds)
RFID_TIMEOUT = 30  # Max wait time for RFID card

# Transaction timeout (seconds)
TRANSACTION_TIMEOUT = 60  # Max time for complete transaction
```

**Verification:**
- [ ] `HEARTBEAT_INTERVAL = 60` (matches backend expectation)
- [ ] `REDEMPTION_POLL_INTERVAL = 5` (matches RASPBERRY_PI_REDEMPTION.md)
- [ ] Timeouts are reasonable for your use case

---

## 🌐 NETWORK CONFIGURATION

### 1. Raspberry Pi Network Setup

**WiFi Configuration:**

When flashing Raspberry Pi OS with Raspberry Pi Imager, configure:

```
WiFi SSID: YOUR_NETWORK_NAME
WiFi Password: YOUR_WIFI_PASSWORD
WiFi Country: YOUR_COUNTRY_CODE (e.g., US, GB, PH)
```

**OR manually edit `/boot/wpa_supplicant.conf`:**

```bash
country=US
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1

network={
    ssid="YOUR_NETWORK_NAME"
    psk="YOUR_WIFI_PASSWORD"
    key_mgmt=WPA-PSK
}
```

**Verification:**

```bash
# On Raspberry Pi via SSH
ifconfig wlan0

# Should show IP address like: 192.168.1.100
```

- [ ] Raspberry Pi connected to WiFi
- [ ] IP address assigned (e.g., `192.168.1.100`)
- [ ] Same network as backend server

---

### 2. Network Connectivity Test

**From Raspberry Pi, test connectivity to backend:**

```bash
# Ping server IP
ping YOUR_SERVER_IP

# Test HTTP connectivity
curl http://YOUR_SERVER_IP:3000/api/health

# Expected response:
# {"success":true,"status":"online","timestamp":"...","message":"R3-Cycle API is running"}
```

**Verification:**
- [ ] Raspberry Pi can ping server IP
- [ ] `/api/health` endpoint returns success
- [ ] No firewall blocking port 3000

---

### 3. Firewall Configuration

**On backend server (Windows):**

**Option 1: Allow Node.js through firewall**

```
Windows Defender Firewall → Allow an app through firewall
→ Find "Node.js" → Check both Private and Public
```

**Option 2: Allow port 3000**

```powershell
# Run as Administrator
New-NetFirewallRule -DisplayName "R3-Cycle API" -Direction Inbound -LocalPort 3000 -Protocol TCP -Action Allow
```

**Verification:**
- [ ] Port 3000 accessible from Raspberry Pi network
- [ ] No firewall blocking connections

---

## 🗄️ DATABASE CONFIGURATION

### 1. Firestore Collections

**Required collections and sample documents:**

#### ✅ `users` Collection

**Sample document:**

```javascript
users/testUserId {
  name: "Test User",
  email: "test@example.com",
  role: "user",
  emailVerified: true,
  rfidTag: "TEST12345",  // Your actual RFID tag ID
  rfidRegisteredAt: Timestamp,
  currentPoints: 0,
  totalPaperRecycled: 0,
  totalTransactions: 0,
  bondsEarned: 0,
  lastTransactionAt: null,
  createdAt: Timestamp
}
```

**Verification:**
- [ ] At least one user with `emailVerified: true`
- [ ] User has `rfidTag` linked (if testing with real RFID)

---

#### ✅ `machines` Collection

**Sample document:**

```javascript
machines/RPI_001 {
  id: "RPI_001",
  location: "Main Campus",
  status: "offline",
  bondPaperStock: 100,
  bondPaperCapacity: 100,
  stockPercentage: 100,
  lastHeartbeat: null,
  lastMaintenance: Timestamp,
  totalTransactions: 0,
  totalPaperCollected: 0,
  sensorHealth: {
    rfid: "ok",
    loadCell: "ok",
    inductiveSensor: "ok",
    irSensor: "ok",
    servo: "ok"
  },
  alerts: []
}
```

**Verification:**
- [ ] Machine document `RPI_001` exists
- [ ] `id` field matches Raspberry Pi `MACHINE_ID`

---

#### ✅ `transactions` Collection

**Will be auto-created on first transaction.**

Sample structure:
```javascript
transactions/transactionId {
  userId: "testUserId",
  rfidTag: "TEST12345",
  machineId: "RPI_001",
  weight: 5.2,
  weightUnit: "grams",
  weightValid: true,
  metalDetected: false,
  pointsAwarded: 1,
  status: "completed",
  rejectionReason: null,
  timestamp: Timestamp,
  syncedAt: Timestamp
}
```

**Verification:**
- [ ] Collection exists (or will be created automatically)

---

#### ✅ `redemptions` Collection

**Will be created when user redeems points.**

Sample structure:
```javascript
redemptions/redemptionId {
  userId: "testUserId",
  machineId: "RPI_001",
  rewardType: "1 Bond Paper (Short)",
  pointsCost: 20,
  status: "pending",  // or "completed"
  requestedAt: Timestamp,
  dispensedAt: null,
  dispensedVia: "web"
}
```

**Verification:**
- [ ] Collection exists (or will be created automatically)

---

#### ✅ `alerts` Collection

**Auto-created by heartbeat endpoint when issues detected.**

Sample structure:
```javascript
alerts/alertId {
  machineId: "RPI_001",
  severity: "critical",  // or "warning", "error", "info"
  title: "Reward Paper Critical Low",
  description: "Bond paper stock at 15%...",
  type: "stock_critical",
  status: "active",  // or "dismissed"
  createdAt: Timestamp,
  resolvedAt: null,
  dismissedBy: null
}
```

**Verification:**
- [ ] Collection exists (or will be created automatically)

---

### 2. Firestore Indexes

**May be required for complex queries.**

If you see errors like "Index required", create indexes via Firebase Console.

**Common indexes needed:**

1. **Transactions by user + timestamp:**
   - Collection: `transactions`
   - Fields: `userId` (Ascending), `timestamp` (Descending)

2. **Alerts by machine + status:**
   - Collection: `alerts`
   - Fields: `machineId` (Ascending), `status` (Ascending)

**Verification:**
- [ ] Check Firebase Console → Firestore → Indexes tab
- [ ] Create indexes if prompted by errors

---

## 🔧 HARDWARE VERIFICATION

### 1. Component Checklist

**Before powering on Raspberry Pi, verify:**

- [ ] **Raspberry Pi Zero 2 W** - microSD card inserted
- [ ] **RC522 RFID Reader** - Connected via logic level converter
- [ ] **HX711 + Load Cell** - DT → GPIO 5, SCK → GPIO 6
- [ ] **IR Sensor** - OUT → GPIO 17
- [ ] **Inductive Sensor** - OUT → GPIO 27
- [ ] **LCD 16x2 I2C** - SDA → GPIO 2, SCL → GPIO 3
- [ ] **Servo Motor #1** - Signal → GPIO 18, **external 5V power** ⚠️
- [ ] **Servo Motor #2** - Signal → GPIO 23, **external 5V power** ⚠️
- [ ] **LED Red** - GPIO 24 via 220Ω resistor
- [ ] **Logic Level Converter** - LV → 3.3V, HV → 5V
- [ ] **Power Supply** - 5V 3A micro USB to Raspberry Pi

---

### 2. Wiring Verification

**Use multimeter to verify:**

- [ ] **No short circuits** between GPIO pins
- [ ] **3.3V rail** measures ~3.3V
- [ ] **5V rail** measures ~5V
- [ ] **All grounds connected** (Pi GND, servo power GND, sensors GND)
- [ ] **Logic converter** LV side connected to 3.3V, HV side to 5V
- [ ] **Servo motors** powered from **external supply**, NOT Pi 5V ⚠️

---

### 3. Power Supply Verification

**Measurements with multimeter:**

- [ ] Raspberry Pi power supply: 5V ± 0.25V (at micro USB)
- [ ] Servo external power: 5V ± 0.25V (at servo red wire)
- [ ] Shared ground between Pi and servo power

**⚠️ WARNING:**

If servos are powered from Raspberry Pi 5V pin, **DISCONNECT IMMEDIATELY!**

Servos draw high current and will damage the Pi.

---

## 🧪 TESTING WORKFLOW

### Phase 1: Backend Server Testing (NO HARDWARE)

```powershell
# 1. Start backend server
npm run xian

# 2. Run API tests
.\test-api.ps1

# Expected: All tests pass ✓
```

**Verification:**
- [ ] Server starts without errors
- [ ] All API endpoints respond
- [ ] Firebase connection successful

---

### Phase 2: Raspberry Pi Software Testing (NO HARDWARE)

```bash
# On Raspberry Pi via SSH

# 1. Navigate to directory
cd /home/pi/r3cycle

# 2. Test API connectivity (no hardware needed)
python3 tests/test_api.py

# Expected: All 5/5 tests pass
```

**Verification:**
- [ ] Raspberry Pi can reach backend server
- [ ] API authentication works
- [ ] Network latency acceptable (<1000ms)

---

### Phase 3: Individual Sensor Testing (WITH HARDWARE)

**Test each sensor separately:**

```bash
# 1. Test LCD display
sudo python3 tests/test_lcd.py
# Expected: Messages appear on LCD

# 2. Test RFID reader
sudo python3 tests/test_rfid.py
# Place RFID card near reader
# Expected: Tag ID displayed

# 3. Test load cell
sudo python3 tests/test_loadcell.py
# Follow calibration wizard
# Place known weight (e.g., 100g)
# Update config.py with reference unit

# 4. Test IR sensor
sudo python3 tests/test_ir_sensor.py
# Insert paper/object
# Expected: "DETECTED" message

# 5. Test inductive sensor
sudo python3 tests/test_inductive.py
# Bring metal object near sensor
# Expected: "METAL DETECTED" message
```

**Verification:**
- [ ] LCD displays messages correctly
- [ ] RFID reads cards successfully
- [ ] Load cell calibrated and accurate
- [ ] IR sensor detects paper insertion
- [ ] Inductive sensor detects metal

---

### Phase 4: Complete System Test (FULL INTEGRATION)

```bash
# Run main application
sudo python3 /home/pi/r3cycle/main.py
```

**Test complete transaction flow:**

1. **LCD shows:** `"R3-Cycle Ready / Scan RFID Card"`
2. **Scan RFID card** (must be linked in web dashboard)
3. **LCD shows:** `"Hello [Name]! / Insert paper"`
4. **Insert paper** (IR sensor detects)
5. **LCD shows:** `"Weighing paper / Please wait..."`
6. **Weight measured** (1-20g range)
7. **Metal check** (should be clean)
8. **Transaction submitted** to backend
9. **LCD shows:** `"Success! +1 / Total: X pts"`

**Verification:**
- [ ] Complete flow works end-to-end
- [ ] Backend receives transaction
- [ ] User points updated in Firestore
- [ ] LCD feedback at each step
- [ ] No errors in logs

**Check backend:**

```
Firebase Console → Firestore → transactions collection
```

You should see new transaction document with:
- `userId`, `rfidTag`, `machineId`
- `weight`, `metalDetected`, `pointsAwarded`
- `status: "completed"`
- `timestamp`

---

### Phase 5: Production Deployment

```bash
# 1. Install systemd service
sudo cp /home/pi/r3cycle/r3cycle.service /etc/systemd/system/

# 2. Reload systemd
sudo systemctl daemon-reload

# 3. Enable auto-start on boot
sudo systemctl enable r3cycle.service

# 4. Start service
sudo systemctl start r3cycle.service

# 5. Check status
sudo systemctl status r3cycle.service

# Expected: "active (running)"
```

**Monitor logs:**

```bash
# Real-time logs
sudo journalctl -u r3cycle.service -f

# Or view log file
tail -f /home/pi/r3cycle/r3cycle.log
```

**Verification:**
- [ ] Service starts successfully
- [ ] Auto-starts after reboot
- [ ] Restarts on crash
- [ ] Logs are being written

---

## ✅ FINAL VERIFICATION CHECKLIST

### Backend Server ✅

- [ ] Server running on port 3000
- [ ] Firebase initialized
- [ ] Machine document `RPI_001` exists in Firestore
- [ ] Test user with RFID tag exists
- [ ] All 16 API endpoints tested and working
- [ ] Firewall allows port 3000

### Raspberry Pi Software ✅

- [ ] Files transferred to `/home/pi/r3cycle/`
- [ ] Installation script run: `sudo bash install.sh`
- [ ] SPI enabled (for RFID)
- [ ] I2C enabled (for LCD)
- [ ] Python libraries installed
- [ ] Reboot completed

### Configuration ✅

- [ ] `config.py` → `API_BASE_URL` updated with server IP
- [ ] `config.py` → `MACHINE_ID = "RPI_001"`
- [ ] `config.py` → `MACHINE_SECRET = "test-secret"` (matches backend)
- [ ] `config.py` → `LCD_I2C_ADDRESS` verified with `i2cdetect`
- [ ] `config.py` → `LOAD_CELL_REFERENCE_UNIT` calibrated

### Hardware ✅

- [ ] All 11 components wired according to GPIO diagram
- [ ] Logic level converter connected (RC522 SPI)
- [ ] Servos powered from **external 5V supply** ⚠️
- [ ] All grounds shared (Pi, servos, sensors)
- [ ] No short circuits verified with multimeter
- [ ] Power supplies tested (5V ± 0.25V)

### Network ✅

- [ ] Raspberry Pi connected to WiFi
- [ ] Same network as backend server
- [ ] Raspberry Pi can ping server IP
- [ ] `/api/health` endpoint accessible from Pi
- [ ] No firewall blocking connections

### Testing ✅

- [ ] Backend API tests pass (PowerShell)
- [ ] Raspberry Pi API connectivity test pass
- [ ] LCD displays messages
- [ ] RFID reads cards
- [ ] Load cell calibrated
- [ ] IR sensor detects paper
- [ ] Inductive sensor detects metal
- [ ] Complete transaction flow successful
- [ ] Backend receives transaction data
- [ ] User points updated in Firestore

### Production ✅

- [ ] Systemd service installed
- [ ] Service starts successfully
- [ ] Service enabled for auto-start
- [ ] Service survives reboot
- [ ] Logs are accessible

---

## 📝 QUICK REFERENCE

### Essential IP Addresses

```
Backend Server IP:    ___________________  (e.g., 192.168.1.50)
Raspberry Pi IP:      ___________________  (e.g., 192.168.1.100)
API Base URL:         http://___________:3000/api
```

### Essential Credentials

```
MACHINE_ID:           RPI_001
MACHINE_SECRET:       test-secret
LCD I2C Address:      0x27 (or 0x3f)
Load Cell Ref Unit:   _______ (after calibration)
```

### Essential Commands

```bash
# Start server (Windows)
npm run xian

# SSH to Raspberry Pi (Windows)
ssh pi@192.168.1.100

# Transfer files (Windows)
pscp.exe -r raspberry_pi pi@192.168.1.100:/home/pi/r3cycle

# Run main program (Pi)
sudo python3 /home/pi/r3cycle/main.py

# View logs (Pi)
tail -f /home/pi/r3cycle/r3cycle.log

# Check service status (Pi)
sudo systemctl status r3cycle.service
```

---

## 🎯 READY TO DEPLOY?

**If all checkboxes above are checked ✅, you are ready to:**

1. Wire hardware according to [RASPBERRY_PI_SETUP.md](RASPBERRY_PI_SETUP.md)
2. Transfer files to Raspberry Pi
3. Update `config.py` with your server IP
4. Run individual sensor tests
5. Calibrate load cell
6. Test complete transaction flow
7. Install systemd service
8. Start recycling paper! ♻️

---

**Good luck with your deployment!** 🚀

*If you encounter any issues, refer to the Troubleshooting section in [RASPBERRY_PI_SETUP.md](RASPBERRY_PI_SETUP.md)*
