# RASPBERRY PI REDEMPTION FLOW DOCUMENTATION

This document explains how the Raspberry Pi Zero 2 W handles redemption requests and dispenses bond paper using the servo motor.

---

## OVERVIEW

The redemption system works as a **polling-based queue**:

1. User clicks "Redeem" on web dashboard → Backend creates pending redemption
2. Raspberry Pi polls `/api/redemption/pending` every 5 seconds
3. When redemption found, Pi activates servo motor to dispense paper
4. After successful dispensing, Pi calls `/api/redemption/dispense` to mark complete

---

## HARDWARE SETUP

### Servo Motor Configuration

**Component:** MG996R Servo Motor (or similar)

**Connections:**
```
Servo Motor → Raspberry Pi Zero 2 W
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Red Wire    → 5V External Power Supply (NOT Pi's 5V pin - draws too much current)
Brown Wire  → Ground (shared with Pi ground)
Orange Wire → GPIO 18 (PWM-capable pin)
```

**IMPORTANT:** MG996R draws significant current (up to 2.5A at stall). **DO NOT power from Raspberry Pi's 5V pin!** Use external 5V power supply (e.g., DC-DC buck converter from 12V) with shared ground.

---

## API ENDPOINTS FOR RASPBERRY PI

### 1. Poll for Pending Redemptions

**Endpoint:** `GET /api/redemption/pending`

**Authentication:** Machine credentials required

**PowerShell Example:**
```powershell
$headers = @{
    "X-Machine-ID" = "RPI_001"
    "X-Machine-Secret" = "test-secret"
}

$response = Invoke-RestMethod -Uri "http://localhost:3000/api/redemption/pending" `
    -Method Get `
    -Headers $headers
```

**Expected Response (when redemptions exist):**
```json
{
  "success": true,
  "count": 2,
  "redemptions": [
    {
      "id": "rdmp_abc123",
      "userId": "user_xyz789",
      "rewardType": "1 Bond Paper (Short)",
      "pointsCost": 20,
      "status": "pending",
      "requestedAt": {
        "_seconds": 1732041234,
        "_nanoseconds": 567000000
      }
    },
    {
      "id": "rdmp_def456",
      "userId": "user_uvw456",
      "rewardType": "1 Bond Paper (Long)",
      "pointsCost": 40,
      "status": "pending",
      "requestedAt": {
        "_seconds": 1732041300,
        "_nanoseconds": 123000000
      }
    }
  ]
}
```

**Expected Response (no pending redemptions):**
```json
{
  "success": true,
  "count": 0,
  "redemptions": []
}
```

---

### 2. Mark Redemption as Dispensed

**Endpoint:** `POST /api/redemption/dispense`

**Authentication:** Machine credentials required

**Request Body:**
```json
{
  "redemptionId": "rdmp_abc123",
  "machineId": "RPI_001"
}
```

**PowerShell Example:**
```powershell
$headers = @{
    "Content-Type" = "application/json"
    "X-Machine-ID" = "RPI_001"
    "X-Machine-Secret" = "test-secret"
}

$body = @{
    redemptionId = "rdmp_abc123"
    machineId = "RPI_001"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:3000/api/redemption/dispense" `
    -Method Post `
    -Headers $headers `
    -Body $body
```

**Expected Response:**
```json
{
  "success": true,
  "message": "Redemption marked as dispensed"
}
```

---

## PYTHON CODE FOR RASPBERRY PI

### Complete Redemption Handler

```python
#!/usr/bin/env python3
"""
R3-Cycle Redemption Handler for Raspberry Pi Zero 2 W
Polls for pending redemptions and dispenses bond paper using servo motor
"""

import requests
import time
import RPi.GPIO as GPIO
from datetime import datetime

# ============================================
# CONFIGURATION
# ============================================

API_BASE_URL = "http://your-server-ip:3000/api"
MACHINE_ID = "RPI_001"
MACHINE_SECRET = "test-secret"
SERVO_PIN = 18  # GPIO pin for servo motor (PWM-capable)
POLL_INTERVAL = 5  # seconds

# Servo positions (adjust based on your mechanical setup)
SERVO_IDLE_POSITION = 0      # degrees (resting position)
SERVO_DISPENSE_POSITION = 90 # degrees (dispense one sheet)

# ============================================
# SETUP
# ============================================

def setup_servo():
    """Initialize GPIO and servo motor"""
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(SERVO_PIN, GPIO.OUT)

    # Create PWM instance (50Hz for most servos)
    pwm = GPIO.PWM(SERVO_PIN, 50)
    pwm.start(0)  # Start with 0% duty cycle

    return pwm

def angle_to_duty_cycle(angle):
    """
    Convert angle (0-180) to duty cycle (2-12)

    Standard servo: 1ms = 0°, 1.5ms = 90°, 2ms = 180°
    At 50Hz (20ms period):
    - 1ms / 20ms = 5% duty cycle = 0°
    - 1.5ms / 20ms = 7.5% duty cycle = 90°
    - 2ms / 20ms = 10% duty cycle = 180°
    """
    duty_cycle = 2 + (angle / 180) * 10
    return duty_cycle

# ============================================
# API FUNCTIONS
# ============================================

def get_pending_redemptions():
    """Poll server for pending redemptions"""
    try:
        headers = {
            "X-Machine-ID": MACHINE_ID,
            "X-Machine-Secret": MACHINE_SECRET
        }

        response = requests.get(
            f"{API_BASE_URL}/redemption/pending",
            headers=headers,
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            return data.get("redemptions", [])
        else:
            print(f"[ERROR] Failed to fetch redemptions: {response.status_code}")
            return []

    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Network error: {e}")
        return []

def mark_redemption_dispensed(redemption_id):
    """Notify server that redemption has been dispensed"""
    try:
        headers = {
            "Content-Type": "application/json",
            "X-Machine-ID": MACHINE_ID,
            "X-Machine-Secret": MACHINE_SECRET
        }

        payload = {
            "redemptionId": redemption_id,
            "machineId": MACHINE_ID
        }

        response = requests.post(
            f"{API_BASE_URL}/redemption/dispense",
            headers=headers,
            json=payload,
            timeout=10
        )

        if response.status_code == 200:
            print(f"[SUCCESS] Redemption {redemption_id} marked as dispensed")
            return True
        else:
            print(f"[ERROR] Failed to mark dispensed: {response.status_code}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Network error: {e}")
        return False

# ============================================
# SERVO CONTROL
# ============================================

def dispense_paper(pwm):
    """
    Activate servo motor to dispense one sheet of bond paper

    Mechanical action:
    1. Move servo to dispense position (pushes paper)
    2. Hold for 1 second
    3. Return to idle position
    """
    print(f"[SERVO] Dispensing paper...")

    try:
        # Move to dispense position
        duty = angle_to_duty_cycle(SERVO_DISPENSE_POSITION)
        pwm.ChangeDutyCycle(duty)
        time.sleep(1.0)  # Hold position

        # Return to idle
        duty = angle_to_duty_cycle(SERVO_IDLE_POSITION)
        pwm.ChangeDutyCycle(duty)
        time.sleep(0.5)  # Settle time

        # Stop PWM signal (prevents jitter)
        pwm.ChangeDutyCycle(0)

        print(f"[SERVO] Dispense complete")
        return True

    except Exception as e:
        print(f"[ERROR] Servo error: {e}")
        return False

# ============================================
# MAIN LOOP
# ============================================

def main():
    """Main redemption polling loop"""
    print("=" * 50)
    print("R3-CYCLE REDEMPTION HANDLER")
    print("=" * 50)
    print(f"Machine ID: {MACHINE_ID}")
    print(f"API URL: {API_BASE_URL}")
    print(f"Poll Interval: {POLL_INTERVAL} seconds")
    print(f"Servo Pin: GPIO {SERVO_PIN}")
    print("=" * 50)

    # Initialize servo
    pwm = setup_servo()

    # Set to idle position on startup
    duty = angle_to_duty_cycle(SERVO_IDLE_POSITION)
    pwm.ChangeDutyCycle(duty)
    time.sleep(1)
    pwm.ChangeDutyCycle(0)

    print("[READY] Waiting for redemption requests...\n")

    try:
        while True:
            # Poll for pending redemptions
            redemptions = get_pending_redemptions()

            if redemptions:
                print(f"[INFO] Found {len(redemptions)} pending redemption(s)")

                # Process each redemption (FIFO order)
                for redemption in redemptions:
                    redemption_id = redemption["id"]
                    reward_type = redemption["rewardType"]
                    user_id = redemption["userId"]

                    print(f"\n[PROCESS] Redemption ID: {redemption_id}")
                    print(f"          Reward: {reward_type}")
                    print(f"          User: {user_id}")

                    # Dispense paper
                    success = dispense_paper(pwm)

                    if success:
                        # Mark as dispensed in database
                        mark_redemption_dispensed(redemption_id)
                        print(f"[COMPLETE] Redemption processed successfully\n")
                    else:
                        print(f"[FAILED] Could not dispense paper for {redemption_id}\n")
                        # TODO: Implement retry logic or error notification

                    # Small delay between dispensing multiple items
                    time.sleep(2)

            # Wait before next poll
            time.sleep(POLL_INTERVAL)

    except KeyboardInterrupt:
        print("\n\n[SHUTDOWN] Redemption handler stopped by user")

    finally:
        # Cleanup
        pwm.stop()
        GPIO.cleanup()
        print("[CLEANUP] GPIO cleanup complete")

if __name__ == "__main__":
    main()
```

---

## MECHANICAL DESIGN NOTES

### Servo-Based Paper Dispenser Mechanism

**Design 1: Push Mechanism**
```
┌─────────────────────────────────────┐
│  Bond Paper Stack (vertical)        │
│  ┌───────────────────┐              │
│  │   │   │   │   │   │              │
│  │   │   │   │   │   │              │
│  │   │   │   │   │   │              │
│  │   │   │   │   │   │              │
│  └───────────────────┘              │
│         ↑                            │
│         │ Servo arm pushes           │
│      ───┴───  (bottom sheet)         │
│      Servo                           │
└─────────────────────────────────────┘
```

**How it works:**
1. Servo arm starts horizontal (idle)
2. When activated, rotates 90° to push bottom sheet forward
3. Paper falls into collection tray
4. Servo returns to idle position

**Design 2: Roller Mechanism (More Reliable)**
```
┌─────────────────────────────────────┐
│  Bond Paper Stack (horizontal)      │
│  ════════════════════                │
│        ↓                             │
│    ┌───┴───┐  Servo-driven          │
│    │ Roller│  rubber roller          │
│    └───────┘  grips and pulls       │
│        ↓      one sheet              │
│    [Output]                          │
└─────────────────────────────────────┘
```

**How it works:**
1. Servo rotates rubber roller
2. Friction pulls one sheet at a time
3. More consistent than push mechanism
4. Requires mechanical coupling (gears or belt)

**Recommended:** Start with **Design 1** (push mechanism) for simplicity. Upgrade to **Design 2** if jamming occurs.

---

## TESTING THE REDEMPTION SYSTEM

### Step-by-Step Test Procedure

#### 1. Start the Backend Server
```powershell
npm run xian
```

#### 2. Login to Dashboard and Earn Points
1. Navigate to `http://localhost:3000/login`
2. Login with verified account
3. Link RFID card if not already linked
4. Submit test transactions to earn at least 20 points

#### 3. Request Redemption via Dashboard
1. Go to dashboard
2. Click "Redeem" on "1 Bond Paper (Short)"
3. Confirm redemption
4. Points should be deducted immediately

#### 4. Test Raspberry Pi Polling (PowerShell Simulation)

**Check for pending redemptions:**
```powershell
$headers = @{
    "X-Machine-ID" = "RPI_001"
    "X-Machine-Secret" = "test-secret"
}

Invoke-RestMethod -Uri "http://localhost:3000/api/redemption/pending" `
    -Method Get `
    -Headers $headers
```

**You should see:**
```json
{
  "success": true,
  "count": 1,
  "redemptions": [
    {
      "id": "XYZ123ABC",
      "rewardType": "1 Bond Paper (Short)",
      "pointsCost": 20,
      "status": "pending"
    }
  ]
}
```

#### 5. Simulate Dispensing (PowerShell)

**Mark as dispensed:**
```powershell
$headers = @{
    "Content-Type" = "application/json"
    "X-Machine-ID" = "RPI_001"
    "X-Machine-Secret" = "test-secret"
}

$body = @{
    redemptionId = "XYZ123ABC"  # Use actual ID from step 4
    machineId = "RPI_001"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:3000/api/redemption/dispense" `
    -Method Post `
    -Headers $headers `
    -Body $body
```

#### 6. Verify Completion

**Check pending redemptions again:**
```powershell
Invoke-RestMethod -Uri "http://localhost:3000/api/redemption/pending" `
    -Method Get `
    -Headers $headers
```

**Should return:**
```json
{
  "success": true,
  "count": 0,
  "redemptions": []
}
```

**Check Firebase Console:**
1. Go to Firestore → `redemptions` collection
2. Find your redemption document
3. Verify `status` changed from `"pending"` to `"completed"`
4. Verify `dispensedAt` timestamp exists
5. Verify `machineId` is set to `"RPI_001"`

---

## TROUBLESHOOTING

### Issue: Redemptions not appearing in pending queue

**Cause:** User doesn't have enough points

**Solution:** Check user's `currentPoints` in Firestore. Submit more transactions to earn points.

---

### Issue: Servo motor not moving

**Possible Causes:**
1. **Insufficient power** - MG996R requires external 5V supply (2A minimum)
2. **Wrong GPIO pin** - Verify GPIO 18 is used (PWM-capable)
3. **PWM frequency wrong** - Should be 50Hz for standard servos
4. **Mechanical jam** - Check if servo arm is blocked

**Debug Steps:**
```python
# Test servo directly
import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)
GPIO.setup(18, GPIO.OUT)
pwm = GPIO.PWM(18, 50)
pwm.start(0)

# Test sweep
for angle in range(0, 181, 10):
    duty = 2 + (angle / 180) * 10
    pwm.ChangeDutyCycle(duty)
    time.sleep(0.1)

pwm.stop()
GPIO.cleanup()
```

---

### Issue: Multiple papers dispensed at once

**Cause:** Paper stack too loose or servo travels too far

**Solution:**
- Reduce `SERVO_DISPENSE_POSITION` angle (try 60° instead of 90°)
- Add friction pad to stack to separate sheets
- Reduce servo speed by adding intermediate steps

---

### Issue: Network timeout when polling

**Cause:** Server not reachable from Raspberry Pi

**Solution:**
```bash
# Test connectivity from Pi
ping your-server-ip

# Test API directly
curl http://your-server-ip:3000/api/health
```

---

## INTEGRATION CHECKLIST

Before deploying to production:

- [ ] Servo motor tested and calibrated
- [ ] External power supply connected (5V, 2A+)
- [ ] Shared ground between Pi and power supply
- [ ] Python script runs on startup (systemd service)
- [ ] API endpoints tested with PowerShell
- [ ] Redemption flow tested end-to-end
- [ ] Error handling implemented (retry logic)
- [ ] Mechanical dispenser tested with 100+ sheets
- [ ] No paper jams observed
- [ ] LED indicator added for "dispensing" status

---

## NEXT STEPS

1. **Test with actual hardware** - Run Python script on Raspberry Pi
2. **Calibrate servo angles** - Adjust `SERVO_IDLE_POSITION` and `SERVO_DISPENSE_POSITION`
3. **Build mechanical dispenser** - Fabricate push/roller mechanism
4. **Add error handling** - Retry failed redemptions, log errors
5. **Create startup service** - Auto-run redemption handler on Pi boot
6. **Add status indicators** - LCD display showing "Dispensing..." message

---

**Happy Dispensing! 📄**
