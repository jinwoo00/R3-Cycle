# 🪟 POWERSHELL API TESTING GUIDE

Quick guide for testing R3-Cycle APIs using Windows PowerShell.

---

## 🚀 AUTOMATED TESTING (Recommended)

### Run All Tests

```powershell
.\test-api.ps1
```

**What it tests:**
- ✅ Server health check
- ✅ RFID verification
- ✅ Valid transaction (5.2g, no metal)
- ✅ Rejected transaction (metal detected)
- ✅ Rejected transaction (invalid weight)
- ✅ Machine heartbeat

**Example Output:**
```
╔═══════════════════════════════════════════════════════════╗
║           R3-CYCLE API TEST SUITE (PowerShell)            ║
╚═══════════════════════════════════════════════════════════╝

========================================
 TEST 1: Health Check
========================================

✓ Health check passed
ℹ Server is running at: http://localhost:3000/api

========================================
 TEST 2: RFID Verification
========================================

⚠ RFID not registered in system
ℹ Message: Card not registered. Please link your RFID card via the web dashboard.

[... more tests ...]

╔═══════════════════════════════════════════════════════════╗
║                      TEST SUMMARY                         ║
╚═══════════════════════════════════════════════════════════╝

  ✓ HealthCheck
  ✗ RfidVerify
  ✓ ValidTransaction
  ✓ RejectedMetal
  ✓ RejectedWeight
  ✓ Heartbeat

  Total: 5 / 6 tests passed

  ⚠ Most tests passed. Check failures above.
```

---

## 🎯 TESTING WITH SPECIFIC RFID

```powershell
# Test with your linked RFID tag
.\test-api.ps1 -RfidTag "YOUR_RFID_TAG_HERE"
```

---

## 🔨 MANUAL TESTING COMMANDS

### 1. Test Health Check

```powershell
Invoke-RestMethod -Uri "http://localhost:3000/api/health" -Method Get
```

**Expected:**
```json
{
  "success": true,
  "status": "online",
  "timestamp": "2025-11-19T...",
  "message": "R3-Cycle API is running"
}
```

---

### 2. Link RFID to Your Account

**Prerequisites:** Login to web dashboard first, then get session cookie.

**Get Session Cookie:**
1. Login at `http://localhost:3000/login`
2. Press F12 → Application → Cookies
3. Copy `connect.sid` value

**Link RFID:**
```powershell
$headers = @{
    "Content-Type" = "application/json"
    "Cookie" = "connect.sid=YOUR_SESSION_COOKIE_HERE"
}

$body = @{
    rfidTag = "A1B2C3D4"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:3000/api/rfid/register" `
    -Method Post `
    -Headers $headers `
    -Body $body
```

**Expected:**
```json
{
  "success": true,
  "message": "RFID card successfully linked to your account"
}
```

---

### 3. Verify RFID (Machine Endpoint)

```powershell
$headers = @{
    "Content-Type" = "application/json"
    "X-Machine-ID" = "RPI_001"
    "X-Machine-Secret" = "test-secret"
}

$body = @{
    rfidTag = "A1B2C3D4"
    machineId = "RPI_001"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:3000/api/rfid/verify" `
    -Method Post `
    -Headers $headers `
    -Body $body
```

**Expected (if linked):**
```json
{
  "success": true,
  "valid": true,
  "userId": "AbCd1234XyZ",
  "userName": "Your Name",
  "currentPoints": 0,
  "totalTransactions": 0,
  "message": "Welcome, Your Name!"
}
```

---

### 4. Submit Transaction

```powershell
$headers = @{
    "Content-Type" = "application/json"
    "X-Machine-ID" = "RPI_001"
    "X-Machine-Secret" = "test-secret"
}

$body = @{
    rfidTag = "A1B2C3D4"
    weight = 5.2
    metalDetected = $false
    timestamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:3000/api/transaction/submit" `
    -Method Post `
    -Headers $headers `
    -Body $body
```

**Expected (accepted):**
```json
{
  "success": true,
  "accepted": true,
  "transaction": {
    "id": "txn_abc123...",
    "pointsAwarded": 1,
    "totalPoints": 1,
    "weight": 5.2,
    "message": "Paper accepted! +1 point. Total: 1"
  }
}
```

---

### 5. Send Machine Heartbeat

```powershell
$headers = @{
    "Content-Type" = "application/json"
    "X-Machine-ID" = "RPI_001"
    "X-Machine-Secret" = "test-secret"
}

$body = @{
    machineId = "RPI_001"
    status = "online"
    bondPaperStock = 85
    sensorHealth = @{
        rfid = "ok"
        loadCell = "ok"
        inductiveSensor = "ok"
        irSensor = "ok"
        servo = "ok"
    }
    timestamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:3000/api/machine/heartbeat" `
    -Method Post `
    -Headers $headers `
    -Body $body
```

**Expected:**
```json
{
  "success": true,
  "message": "Heartbeat received"
}
```

---

### 6. Get User Stats

```powershell
# Replace YOUR_USER_ID and YOUR_SESSION_COOKIE
$headers = @{
    "Cookie" = "connect.sid=YOUR_SESSION_COOKIE"
}

Invoke-RestMethod -Uri "http://localhost:3000/api/user/stats/YOUR_USER_ID" `
    -Method Get `
    -Headers $headers
```

**Expected:**
```json
{
  "success": true,
  "stats": {
    "currentPoints": 5,
    "totalPaperRecycled": 26.1,
    "totalTransactions": 5,
    "bondsEarned": 0,
    "lastTransactionAt": "2025-11-19T14:35:00.000Z"
  }
}
```

---

## 🛠️ USING CURL FOR WINDOWS

If you prefer curl, use `curl.exe` (not PowerShell's curl alias):

### Health Check
```powershell
curl.exe http://localhost:3000/api/health
```

### Submit Transaction
```powershell
curl.exe -X POST http://localhost:3000/api/transaction/submit `
  -H "Content-Type: application/json" `
  -H "X-Machine-ID: RPI_001" `
  -H "X-Machine-Secret: test-secret" `
  -d '{\"rfidTag\": \"A1B2C3D4\", \"weight\": 5.2, \"metalDetected\": false, \"timestamp\": \"2025-11-19T14:35:00Z\"}'
```

**Note:** Use backticks `` ` `` for line continuation in PowerShell!

---

## 📋 COMMON POWERSHELL TIPS

### Save Response to Variable
```powershell
$response = Invoke-RestMethod -Uri "http://localhost:3000/api/health" -Method Get
$response.status  # Access specific field
```

### Pretty Print JSON
```powershell
$response | ConvertTo-Json -Depth 10
```

### Check if Server is Running
```powershell
try {
    $response = Invoke-RestMethod -Uri "http://localhost:3000/api/health" -Method Get
    Write-Host "✓ Server is running" -ForegroundColor Green
} catch {
    Write-Host "✗ Server is not running" -ForegroundColor Red
}
```

### Auto-Generate Timestamp
```powershell
# Use this in transaction body
$timestamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
```

---

## 🐛 TROUBLESHOOTING

### Error: "The term 'Invoke-RestMethod' is not recognized"
- You're using an old PowerShell version
- Upgrade to PowerShell 5.1+ or PowerShell 7+

### Error: "Unable to connect to the remote server"
- Server is not running
- Run: `npm run xian` first

### Error: "401 Unauthorized" (Machine endpoints)
- Missing headers: `X-Machine-ID` and `X-Machine-Secret`
- Check your headers are set correctly

### Error: "401 Unauthorized" (User endpoints)
- Not logged in or invalid session cookie
- Login via web, copy fresh `connect.sid` cookie

### Error: "RFID not found in system"
- RFID not linked to any user account
- Link it via `POST /api/rfid/register` (web session required)

---

## 📚 ADDITIONAL RESOURCES

- **Full API Guide:** [API_TESTING.md](API_TESTING.md)
- **Quick Start:** [QUICKSTART.md](QUICKSTART.md)
- **Development Guide:** [CLAUDE.md](CLAUDE.md)

---

**Happy Testing! 🚀**

