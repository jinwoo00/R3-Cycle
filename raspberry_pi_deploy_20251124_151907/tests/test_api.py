#!/usr/bin/env python3
"""
Test script for API Connectivity
Tests connection to backend server

Usage: python3 test_api.py
"""

import sys
import time

# Add parent directory to path
sys.path.append('/home/pi/r3cycle')

try:
    import requests
    import config
except ImportError as e:
    print(f"[ERROR] Missing library: {e}")
    print("Run: pip3 install requests")
    sys.exit(1)

def test_api():
    """Test API connectivity"""
    print("=" * 60)
    print("R3-Cycle API Connectivity Test")
    print("=" * 60)
    print()

    print("[CONFIG]")
    print(f"  API URL:       {config.API_BASE_URL}")
    print(f"  Machine ID:    {config.MACHINE_ID}")
    print(f"  Machine Secret: {config.MACHINE_SECRET}")
    print()

    headers = {
        "Content-Type": "application/json",
        "X-Machine-ID": config.MACHINE_ID,
        "X-Machine-Secret": config.MACHINE_SECRET
    }

    tests_passed = 0
    tests_failed = 0

    # Test 1: Health Check
    print("[1/5] Testing Health Check Endpoint")
    print(f"      GET {config.API_BASE_URL}/health")

    try:
        response = requests.get(
            f"{config.API_BASE_URL}/health",
            timeout=config.API_TIMEOUT
        )

        if response.status_code == 200:
            data = response.json()
            print(f"      [OK] {data.get('message', 'Server is online')}")
            tests_passed += 1
        else:
            print(f"      [FAIL] HTTP {response.status_code}")
            tests_failed += 1

    except requests.exceptions.RequestException as e:
        print(f"      [FAIL] {e}")
        tests_failed += 1

    time.sleep(1)

    # Test 2: RFID Verification (with invalid tag)
    print("\n[2/5] Testing RFID Verification")
    print(f"      POST {config.API_BASE_URL}/rfid/verify")

    try:
        response = requests.post(
            f"{config.API_BASE_URL}/rfid/verify",
            headers=headers,
            json={"rfidTag": "TEST12345", "machineId": config.MACHINE_ID},
            timeout=config.API_TIMEOUT
        )

        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                print(f"      [OK] RFID endpoint working")
                print(f"           Valid: {data.get('valid')}")
                print(f"           Message: {data.get('message', 'N/A')}")
                tests_passed += 1
            else:
                print(f"      [FAIL] Unexpected response: {data}")
                tests_failed += 1
        else:
            print(f"      [FAIL] HTTP {response.status_code}")
            tests_failed += 1

    except requests.exceptions.RequestException as e:
        print(f"      [FAIL] {e}")
        tests_failed += 1

    time.sleep(1)

    # Test 3: Transaction Submission (will be rejected due to invalid weight)
    print("\n[3/5] Testing Transaction Submission")
    print(f"      POST {config.API_BASE_URL}/transaction/submit")

    try:
        response = requests.post(
            f"{config.API_BASE_URL}/transaction/submit",
            headers=headers,
            json={
                "rfidTag": "TEST12345",
                "weight": 0.5,  # Too light, will be rejected
                "metalDetected": False,
                "timestamp": "2025-11-21T12:00:00Z"
            },
            timeout=config.API_TIMEOUT
        )

        if response.status_code == 200:
            data = response.json()
            print(f"      [OK] Transaction endpoint working")
            print(f"           Accepted: {data.get('accepted')}")
            print(f"           Reason: {data.get('reason', 'N/A')}")
            tests_passed += 1
        else:
            print(f"      [FAIL] HTTP {response.status_code}")
            tests_failed += 1

    except requests.exceptions.RequestException as e:
        print(f"      [FAIL] {e}")
        tests_failed += 1

    time.sleep(1)

    # Test 4: Machine Heartbeat
    print("\n[4/5] Testing Machine Heartbeat")
    print(f"      POST {config.API_BASE_URL}/machine/heartbeat")

    try:
        response = requests.post(
            f"{config.API_BASE_URL}/machine/heartbeat",
            headers=headers,
            json={
                "machineId": config.MACHINE_ID,
                "status": "online",
                "bondPaperStock": 50,
                "bondPaperCapacity": 100,
                "sensorHealth": {
                    "rfid": "ok",
                    "loadCell": "ok",
                    "inductiveSensor": "ok",
                    "irSensor": "ok",
                    "servo": "ok"
                },
                "timestamp": "2025-11-21T12:00:00Z"
            },
            timeout=config.API_TIMEOUT
        )

        if response.status_code == 200:
            data = response.json()
            print(f"      [OK] Heartbeat endpoint working")
            print(f"           Success: {data.get('success')}")
            tests_passed += 1
        else:
            print(f"      [FAIL] HTTP {response.status_code}")
            tests_failed += 1

    except requests.exceptions.RequestException as e:
        print(f"      [FAIL] {e}")
        tests_failed += 1

    time.sleep(1)

    # Test 5: Redemption Pending Check
    print("\n[5/5] Testing Redemption Pending Check")
    print(f"      GET {config.API_BASE_URL}/redemption/pending")

    try:
        response = requests.get(
            f"{config.API_BASE_URL}/redemption/pending",
            headers=headers,
            timeout=config.API_TIMEOUT
        )

        if response.status_code == 200:
            data = response.json()
            print(f"      [OK] Redemption endpoint working")
            print(f"           Pending count: {data.get('count', 0)}")
            tests_passed += 1
        else:
            print(f"      [FAIL] HTTP {response.status_code}")
            tests_failed += 1

    except requests.exceptions.RequestException as e:
        print(f"      [FAIL] {e}")
        tests_failed += 1

    # Summary
    print()
    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"  Tests Passed: {tests_passed}/5")
    print(f"  Tests Failed: {tests_failed}/5")
    print()

    if tests_passed == 5:
        print("[SUCCESS] All API tests passed!")
        print("Your Raspberry Pi can communicate with the backend server.")
        return True
    else:
        print("[FAILED] Some tests failed")
        print()
        print("Troubleshooting:")
        print("  1. Check server is running: npm run xian")
        print("  2. Verify API_BASE_URL in config.py")
        print("  3. Ensure Raspberry Pi can reach server (ping test)")
        print("  4. Check firewall allows port 3000")
        return False

if __name__ == "__main__":
    success = test_api()
    sys.exit(0 if success else 1)
