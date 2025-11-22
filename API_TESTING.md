# R3-CYCLE API TESTING GUIDE

This guide helps you test the newly implemented IoT API endpoints using **Windows PowerShell**, Postman, or any HTTP client.

> **Note:** This guide includes PowerShell-specific commands for Windows users!

## 🚀 QUICK START (PowerShell)

**The easiest way to test all endpoints:**

```powershell
# Run the automated test script
.\test-api.ps1
```

This will test all Phase 1 endpoints automatically! Continue reading for manual testing.

---

## 🔧 SETUP

### 1. Start the Server (PowerShell)
```powershell
npm run xian
# or
npm start
```

Server should be running at: `http://localhost:3000`

### 2. Initialize Database (PowerShell)
```powershell
node scripts/initializeDatabase.js
```

This adds new fields to existing users and creates a sample machine.

### 3. Get Your User ID
1. Register or login to the web dashboard
2. Open browser console (F12)
3. Type: `document.cookie`
4. Or check Firebase Console → Authentication → Users → Copy UID

---

## 📡 API ENDPOINTS

### Base URL
```
http://localhost:3000/api
```

### Authentication

**Machine Endpoints** require headers:
```
X-Machine-ID: RPI_001
X-Machine-Secret: your-secret-key
```

**User Endpoints** require active session (login via web first)

---

## 🧪 TEST CASES

### 1. Health Check (No Auth)

**PowerShell Request:**
```powershell
Invoke-RestMethod -Uri "http://localhost:3000/api/health" -Method Get
```

**Alternative (curl for Windows):**
```powershell
curl.exe http://localhost:3000/api/health
```

**Expected Response:**
```json
{
  "success": true,
  "status": "online",
  "timestamp": "2025-11-19T...",
  "message": "R3-Cycle API is running"
}
```

---

### 2. Link RFID to User Account

**Prerequisites:** Must be logged in via web dashboard first

**PowerShell Request:**
```powershell
$headers = @{
    "Content-Type" = "application/json"
    "Cookie" = "connect.sid=YOUR_SESSION_COOKIE"
}

$body = @{
    rfidTag = "A1B2C3D4"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:3000/api/rfid/register" `
    -Method Post `
    -Headers $headers `
    -Body $body
```

**Alternative (curl for Windows):**
```powershell
curl.exe -X POST http://localhost:3000/api/rfid/register `
  -H "Content-Type: application/json" `
  -H "Cookie: connect.sid=YOUR_SESSION_COOKIE" `
  -d '{\"rfidTag\": \"A1B2C3D4\"}'
```

**Expected Response (Success):**
```json
{
  "success": true,
  "message": "RFID card successfully linked to your account"
}
```

**Expected Response (Already Registered):**
```json
{
  "success": false,
  "message": "This RFID card is already registered to another account"
}
```

**Testing with Postman:**
1. Login via web browser at `http://localhost:3000/login`
2. In Postman, go to Cookies
3. Copy `connect.sid` cookie from browser DevTools
4. Paste into Postman cookie jar
5. Send POST request

---

### 3. Verify RFID (Machine Endpoint)

**PowerShell Request:**
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

**Alternative (curl for Windows):**
```powershell
curl.exe -X POST http://localhost:3000/api/rfid/verify `
  -H "Content-Type: application/json" `
  -H "X-Machine-ID: RPI_001" `
  -H "X-Machine-Secret: test-secret" `
  -d '{\"rfidTag\": \"A1B2C3D4\", \"machineId\": \"RPI_001\"}'
```

**Expected Response (Valid RFID):**
```json
{
  "success": true,
  "valid": true,
  "userId": "AbCd1234XyZ",
  "userName": "Juan Dela Cruz",
  "currentPoints": 0,
  "totalTransactions": 0,
  "message": "Welcome, Juan Dela Cruz!"
}
```

**Expected Response (Invalid RFID):**
```json
{
  "success": true,
  "valid": false,
  "message": "Card not registered. Please link your RFID card via the web dashboard."
}
```

---

### 4. Submit Transaction (Machine Endpoint)

**PowerShell Request - Valid Paper:**
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

**Alternative (curl for Windows):**
```powershell
curl.exe -X POST http://localhost:3000/api/transaction/submit `
  -H "Content-Type: application/json" `
  -H "X-Machine-ID: RPI_001" `
  -H "X-Machine-Secret: test-secret" `
  -d '{\"rfidTag\": \"A1B2C3D4\", \"weight\": 5.2, \"metalDetected\": false, \"timestamp\": \"2025-11-19T14:35:00Z\"}'
```

**Expected Response (Accepted):**
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

**Request - Metal Detected:**
```bash
curl -X POST http://localhost:3000/api/transaction/submit \
  -H "Content-Type: application/json" \
  -H "X-Machine-ID: RPI_001" \
  -H "X-Machine-Secret: test-secret" \
  -d '{
    "rfidTag": "A1B2C3D4",
    "weight": 5.2,
    "metalDetected": true,
    "timestamp": "2025-11-19T14:36:00Z"
  }'
```

**Expected Response (Rejected):**
```json
{
  "success": true,
  "accepted": false,
  "reason": "Metal detected - remove staples, clips, or binders",
  "message": "Metal detected - remove staples, clips, or binders",
  "transactionId": "txn_def456..."
}
```

**Request - Invalid Weight:**
```bash
curl -X POST http://localhost:3000/api/transaction/submit \
  -H "Content-Type: application/json" \
  -H "X-Machine-ID: RPI_001" \
  -H "X-Machine-Secret: test-secret" \
  -d '{
    "rfidTag": "A1B2C3D4",
    "weight": 0.5,
    "metalDetected": false,
    "timestamp": "2025-11-19T14:37:00Z"
  }'
```

**Expected Response (Rejected):**
```json
{
  "success": true,
  "accepted": false,
  "reason": "Paper too light - minimum 1g",
  "message": "Paper too light - minimum 1g",
  "transactionId": "txn_ghi789..."
}
```

---

### 5. Machine Heartbeat (Machine Endpoint)

**Request:**
```bash
curl -X POST http://localhost:3000/api/machine/heartbeat \
  -H "Content-Type: application/json" \
  -H "X-Machine-ID: RPI_001" \
  -H "X-Machine-Secret: test-secret" \
  -d '{
    "machineId": "RPI_001",
    "status": "online",
    "bondPaperStock": 75,
    "sensorHealth": {
      "rfid": "ok",
      "loadCell": "ok",
      "inductiveSensor": "ok",
      "irSensor": "ok",
      "servo": "ok"
    },
    "timestamp": "2025-11-19T14:40:00Z"
  }'
```

**Expected Response:**
```json
{
  "success": true,
  "message": "Heartbeat received"
}
```

---

### 6. Get User Stats

**Request:**
```bash
curl http://localhost:3000/api/user/stats/YOUR_USER_ID \
  -H "Cookie: connect.sid=YOUR_SESSION_COOKIE"
```

**Expected Response:**
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

### 7. Get User Transactions

**Request:**
```bash
curl http://localhost:3000/api/transaction/user/YOUR_USER_ID?limit=10 \
  -H "Cookie: connect.sid=YOUR_SESSION_COOKIE"
```

**Expected Response:**
```json
{
  "success": true,
  "transactions": [
    {
      "id": "txn_abc123",
      "userId": "AbCd1234XyZ",
      "rfidTag": "A1B2C3D4",
      "machineId": "RPI_001",
      "weight": 5.2,
      "weightUnit": "grams",
      "weightValid": true,
      "metalDetected": false,
      "pointsAwarded": 1,
      "status": "completed",
      "rejectionReason": null,
      "timestamp": "2025-11-19T14:35:00.000Z"
    }
  ],
  "count": 1
}
```

---

## 🧩 POSTMAN COLLECTION

### Import these requests into Postman:

```json
{
  "info": {
    "name": "R3-Cycle IoT API",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [
    {
      "name": "Health Check",
      "request": {
        "method": "GET",
        "url": "http://localhost:3000/api/health"
      }
    },
    {
      "name": "Link RFID",
      "request": {
        "method": "POST",
        "url": "http://localhost:3000/api/rfid/register",
        "header": [
          {
            "key": "Content-Type",
            "value": "application/json"
          }
        ],
        "body": {
          "mode": "raw",
          "raw": "{\n  \"rfidTag\": \"A1B2C3D4\"\n}"
        }
      }
    },
    {
      "name": "Verify RFID",
      "request": {
        "method": "POST",
        "url": "http://localhost:3000/api/rfid/verify",
        "header": [
          {
            "key": "Content-Type",
            "value": "application/json"
          },
          {
            "key": "X-Machine-ID",
            "value": "RPI_001"
          },
          {
            "key": "X-Machine-Secret",
            "value": "test-secret"
          }
        ],
        "body": {
          "mode": "raw",
          "raw": "{\n  \"rfidTag\": \"A1B2C3D4\",\n  \"machineId\": \"RPI_001\"\n}"
        }
      }
    },
    {
      "name": "Submit Transaction (Valid)",
      "request": {
        "method": "POST",
        "url": "http://localhost:3000/api/transaction/submit",
        "header": [
          {
            "key": "Content-Type",
            "value": "application/json"
          },
          {
            "key": "X-Machine-ID",
            "value": "RPI_001"
          },
          {
            "key": "X-Machine-Secret",
            "value": "test-secret"
          }
        ],
        "body": {
          "mode": "raw",
          "raw": "{\n  \"rfidTag\": \"A1B2C3D4\",\n  \"weight\": 5.2,\n  \"metalDetected\": false,\n  \"timestamp\": \"2025-11-19T14:35:00Z\"\n}"
        }
      }
    }
  ]
}
```

---

## ✅ TESTING WORKFLOW

### Complete Test Sequence:

1. **Setup**
   ```bash
   npm run xian
   node scripts/initializeDatabase.js
   ```

2. **Web Registration**
   - Open browser: `http://localhost:3000/register`
   - Create account with email/password
   - Verify email via Firebase link
   - Complete 2FA login

3. **Link RFID**
   - Send POST to `/api/rfid/register` with session cookie
   - Use RFID tag: `A1B2C3D4`

4. **Test Machine Flow**
   - Verify RFID: `/api/rfid/verify`
   - Submit valid transaction: `/api/transaction/submit` (weight: 5.2g, no metal)
   - Check user stats: `/api/user/stats/:userId`
   - Verify points increased

5. **Test Rejection Scenarios**
   - Submit with metal detected: `metalDetected: true`
   - Submit with low weight: `weight: 0.5`
   - Submit with high weight: `weight: 25`
   - Verify all are rejected but logged

6. **Test Machine Monitoring**
   - Send heartbeat: `/api/machine/heartbeat`
   - Check Firebase Console → machines collection
   - Verify machine status updated

7. **View Transactions**
   - Get transactions: `/api/transaction/user/:userId`
   - Verify all transactions appear (accepted + rejected)

---

## 🐛 TROUBLESHOOTING

### Error: "Machine ID required"
- Add headers: `X-Machine-ID` and `X-Machine-Secret`

### Error: "Authentication required"
- Login via web first
- Copy `connect.sid` cookie to request

### Error: "RFID not found in system"
- Link RFID first via `/api/rfid/register`

### Error: "Server error"
- Check console logs
- Verify Firebase credentials in `.env`
- Ensure Firestore is enabled

---

## 📊 VERIFY IN FIREBASE CONSOLE

After testing, check Firebase Console:

1. **users collection** - Should have new fields:
   - `rfidTag: "A1B2C3D4"`
   - `currentPoints: 1` (or more)
   - `totalPaperRecycled: 5.2` (or more)
   - `totalTransactions: 1` (or more)

2. **transactions collection** - Should contain transaction records:
   - Both accepted and rejected transactions
   - All sensor data captured

3. **machines collection** - Should have machine status:
   - `RPI_001` with latest heartbeat
   - Current sensor health

---

**Next Steps:**
- Once API testing is complete, proceed to Phase 2 (RFID Registration UI)
- Start building Raspberry Pi Python code
- Test hardware sensor integration

