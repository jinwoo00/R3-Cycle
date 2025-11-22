# 🚀 R3-CYCLE QUICK START GUIDE

Get your R3-Cycle development environment up and running in 5 minutes!

---

## ✅ PREREQUISITES

- [x] Node.js 18+ installed
- [x] Firebase project created (r3-cycle)
- [x] Gmail account for sending emails
- [x] Git installed (optional)

---

## 📦 INSTALLATION

### 1. Install Dependencies
```bash
cd C:\Users\Admin\R3-Cycle
npm install
```

### 2. Configure Environment Variables

Create `.env` file (copy from `.env.example`):

```bash
# Email Configuration
EMAIL_USER=r3cycleiot@gmail.com
EMAIL_PASSWORD=your-gmail-app-password
EMAIL_FROM_NAME=R3-Cycle
EMAIL_FROM_ADDRESS=r3cycleiot@gmail.com

# Server Configuration
PORT=3000
NODE_ENV=development
```

**Get Gmail App Password:**
1. Go to [Google Account Security](https://myaccount.google.com/security)
2. Enable 2-Step Verification
3. Go to App Passwords
4. Generate password for "Mail"
5. Copy 16-character password to `EMAIL_PASSWORD`

### 3. Initialize Database
```bash
node scripts/initializeDatabase.js
```

This will:
- ✅ Add new fields to existing users
- ✅ Create sample machine (RPI_001)
- ✅ Show Firestore index instructions

---

## 🏃 RUNNING THE APPLICATION

### Development Mode (with auto-restart)
```bash
npm run xian
```

### Production Mode
```bash
npm start
```

Server will be running at: **http://localhost:3000**

---

## 🧪 TESTING THE SYSTEM

### Automated Testing (Recommended for PowerShell)

**Run all Phase 1 API tests automatically:**

```powershell
.\test-api.ps1
```

This script will test:
- ✅ Health check
- ✅ RFID verification
- ✅ Valid transaction submission
- ✅ Rejected transactions (metal, weight)
- ✅ Machine heartbeat

**Expected output:** Green checkmarks for all tests! 🎉

---

### 1. Web Authentication Test

**Register a New User:**
1. Open browser: `http://localhost:3000/register`
2. Enter name, email, password
3. Click "Register"
4. Check email for verification link
5. Click verification link
6. Login with email + 2FA code (sent to email)

**Expected Result:** Successfully logged into dashboard

### 2. Link RFID Card

**Using Postman/curl:**

First, get your session cookie:
1. Login via browser
2. Open DevTools (F12) → Application → Cookies
3. Copy `connect.sid` value

Then link RFID:
```bash
curl -X POST http://localhost:3000/api/rfid/register \
  -H "Content-Type: application/json" \
  -H "Cookie: connect.sid=YOUR_COOKIE_HERE" \
  -d '{"rfidTag": "A1B2C3D4"}'
```

**Expected Response:**
```json
{
  "success": true,
  "message": "RFID card successfully linked to your account"
}
```

### 3. Test Raspberry Pi Endpoints

**Health Check (no auth):**
```bash
curl http://localhost:3000/api/health
```

**Verify RFID (machine auth):**
```bash
curl -X POST http://localhost:3000/api/rfid/verify \
  -H "Content-Type: application/json" \
  -H "X-Machine-ID: RPI_001" \
  -H "X-Machine-Secret: test-secret" \
  -d '{
    "rfidTag": "A1B2C3D4",
    "machineId": "RPI_001"
  }'
```

**Submit Transaction:**
```bash
curl -X POST http://localhost:3000/api/transaction/submit \
  -H "Content-Type: application/json" \
  -H "X-Machine-ID: RPI_001" \
  -H "X-Machine-Secret: test-secret" \
  -d '{
    "rfidTag": "A1B2C3D4",
    "weight": 5.2,
    "metalDetected": false,
    "timestamp": "2025-11-19T14:35:00Z"
  }'
```

**Expected Result:** Points awarded, transaction recorded

### 4. Verify in Firebase Console

1. Go to [Firebase Console](https://console.firebase.google.com)
2. Select project: **r3-cycle**
3. Navigate to: **Firestore Database**

Check collections:
- **users** → Find your user → Verify new fields (currentPoints, rfidTag, etc.)
- **transactions** → Should have transaction record
- **machines** → Should have RPI_001 with status

---

## 📊 VERIFY SYSTEM STATUS

### Quick Checks

**1. Server Running?**
```bash
curl http://localhost:3000/api/health
```
Should return: `{"success": true, "status": "online", ...}`

**2. Database Connected?**
- Check Firebase Console → Firestore
- Verify `users` collection has new fields
- Verify `machines` collection exists

**3. Email Working?**
- Register new user
- Check email inbox for verification link
- Click link and verify it works

---

## 🐛 TROUBLESHOOTING

### Server won't start
```bash
# Check if port 3000 is in use
netstat -ano | findstr :3000

# Kill process if needed (replace PID)
taskkill /PID <process_id> /F

# Restart server
npm run xian
```

### Email not sending
```bash
# Check .env file exists
dir .env

# Verify EMAIL_PASSWORD is set (16 chars)
# Make sure it's an App Password, not your regular password
```

### API returns 401 Unauthorized
```bash
# For machine endpoints: Add headers
X-Machine-ID: RPI_001
X-Machine-Secret: test-secret

# For user endpoints: Login via web first, copy session cookie
```

### Firebase errors
```bash
# Check firebaseConfig.js has correct credentials
# Ensure Firestore is enabled in Firebase Console
# Check Firebase Rules allow read/write
```

---

## 📁 PROJECT STRUCTURE

```
R3-Cycle/
├── controllers/
│   ├── authController.js       # User authentication & 2FA
│   ├── homeController.js       # Landing page
│   └── iotController.js        # 🆕 IoT API endpoints
├── routes/
│   ├── index.js                # Web routes
│   └── iot.js                  # 🆕 IoT API routes
├── models/
│   ├── firebaseConfig.js       # Firebase setup
│   └── emailConfig.js          # Nodemailer setup
├── utils/
│   └── validation.js           # 🆕 Validation functions
├── views/
│   ├── user/
│   │   └── dashboard.xian      # User dashboard
│   ├── adminDashboard.xian     # Admin panel
│   ├── login.xian              # Login page
│   └── register.xian           # Registration page
├── scripts/
│   └── initializeDatabase.js   # 🆕 Database setup
├── public/
│   └── tailwind.css            # Compiled CSS
├── .env                        # Environment variables (create this!)
├── .env.example                # Template
├── package.json                # Dependencies
├── index.js                    # 🆕 UPDATED - Added IoT routes
├── CLAUDE.md                   # 🆕 Development tracker
├── API_TESTING.md              # 🆕 API testing guide
├── PHASE1_SUMMARY.md           # 🆕 Phase 1 completion report
└── QUICKSTART.md               # 🆕 This file!
```

---

## 🎯 COMMON TASKS

### Add New User Manually
1. Go to `http://localhost:3000/register`
2. Fill form and submit
3. Verify email
4. Login with 2FA

### Make User Admin
1. Login to [Firebase Console](https://console.firebase.google.com)
2. Go to Firestore → users collection
3. Find user document
4. Change `role` from `"user"` to `"admin"`
5. User logout and login again

### Link RFID to User
See "Link RFID Card" section above

### View Transaction Logs
```bash
# Get user ID from Firebase Console or session
curl http://localhost:3000/api/transaction/user/YOUR_USER_ID \
  -H "Cookie: connect.sid=YOUR_COOKIE"
```

### Send Machine Heartbeat
```bash
curl -X POST http://localhost:3000/api/machine/heartbeat \
  -H "Content-Type: application/json" \
  -H "X-Machine-ID: RPI_001" \
  -H "X-Machine-Secret: test-secret" \
  -d '{
    "machineId": "RPI_001",
    "status": "online",
    "bondPaperStock": 85,
    "sensorHealth": {
      "rfid": "ok",
      "loadCell": "ok",
      "inductiveSensor": "ok",
      "irSensor": "ok",
      "servo": "ok"
    },
    "timestamp": "2025-11-19T15:00:00Z"
  }'
```

---

## 📚 DOCUMENTATION LINKS

- **[CLAUDE.md](CLAUDE.md)** - Complete development guide & progress tracker
- **[API_TESTING.md](API_TESTING.md)** - Detailed API testing guide with examples
- **[PHASE1_SUMMARY.md](PHASE1_SUMMARY.md)** - Phase 1 completion report
- **[README.md](README.md)** - Project overview and setup instructions

---

## 🆘 GETTING HELP

### Error Messages

| Error | Solution |
|-------|----------|
| `EADDRINUSE` | Port 3000 in use, kill process or change PORT in .env |
| `Firebase: Error (auth/...)` | Check Firebase credentials in firebaseConfig.js |
| `Cannot find module` | Run `npm install` |
| `Machine ID required` | Add X-Machine-ID header to request |
| `Authentication required` | Login via web, copy session cookie |

### Useful Commands

```bash
# Check server logs
npm run xian

# Restart server (Ctrl+C then)
npm run xian

# View database
node scripts/initializeDatabase.js

# Test API health
curl http://localhost:3000/api/health
```

---

## ✅ SYSTEM READY CHECKLIST

Before testing with Raspberry Pi hardware:

- [ ] Server starts without errors (`npm run xian`)
- [ ] Health endpoint works (`/api/health`)
- [ ] User can register and verify email
- [ ] User can login with 2FA
- [ ] User can link RFID card
- [ ] RFID verification endpoint works
- [ ] Transaction submission works (valid paper)
- [ ] Transaction rejection works (metal detected)
- [ ] User stats endpoint returns data
- [ ] Machine heartbeat endpoint works
- [ ] Firebase Console shows all data correctly

**If all checked, you're ready for Raspberry Pi integration! 🎉**

---

## 🚀 NEXT STEPS

### Phase 2: RFID Registration UI
1. Create RFID registration page (`views/link-rfid.xian`)
2. Update user dashboard with RFID status
3. Connect dashboard to real API data

### Phase 3: Reward System
1. Implement redemption endpoints
2. Add servo motor control logic
3. Build offline redemption support

### Phase 4: Raspberry Pi Code
1. Write Python main program
2. Integrate all sensors (RFID, load cell, etc.)
3. Connect to API endpoints
4. Test hardware flow end-to-end

---

**Happy Coding! 🚀**

For questions, check [CLAUDE.md](CLAUDE.md) or consult the detailed guides.

