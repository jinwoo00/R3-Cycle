#!/usr/bin/env python3
"""
Test script for Inductive Proximity Sensor
Tests metal detection (staples, clips, etc.)

Usage: sudo python3 test_inductive.py
"""

import sys
import time

# Add parent directory to path
sys.path.append('/home/pi/r3cycle')

try:
    import RPi.GPIO as GPIO
    import config
except ImportError as e:
    print(f"[ERROR] Missing library: {e}")
    print("Run: pip3 install RPi.GPIO")
    sys.exit(1)

def test_inductive_sensor():
    """Test inductive proximity sensor"""
    print("=" * 50)
    print("R3-Cycle Inductive Proximity Sensor Test")
    print("=" * 50)
    print()

    try:
        # Setup GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        print("[1] Initializing inductive sensor...")
        print(f"    GPIO Pin: {config.PIN_INDUCTIVE_SENSOR}")
        print(f"    Sensor Model: LJ12A3-4-ZBX")

        GPIO.setup(config.PIN_INDUCTIVE_SENSOR, GPIO.IN)
        print("[OK] Inductive sensor initialized")
        print()

        # Test reading
        print("[2] Testing metal detection")
        print("    Bring metal objects (staples, clips, screws) near sensor")
        print("    Detection range: ~4mm")
        print("    Press Ctrl+C to exit")
        print()

        last_state = None
        metal_count = 0

        while True:
            try:
                # Read sensor (HIGH = metal detected)
                metal_detected = GPIO.input(config.PIN_INDUCTIVE_SENSOR) == GPIO.HIGH

                # Only print on state change
                if metal_detected != last_state:
                    if metal_detected:
                        metal_count += 1
                        print(f"[METAL] *** Metal Detected! *** (Count: {metal_count})")
                    else:
                        print("[CLEAR] No metal detected")

                    last_state = metal_detected

                time.sleep(0.1)

            except KeyboardInterrupt:
                print("\n\n[INFO] Test interrupted by user")
                print(f"[STATS] Total metal detections: {metal_count}")
                break

    except Exception as e:
        print(f"[ERROR] Inductive sensor test failed: {e}")
        return False

    finally:
        print("\n[CLEANUP] Cleaning up GPIO...")
        GPIO.cleanup()
        print("[DONE] Test complete")

    return True

if __name__ == "__main__":
    success = test_inductive_sensor()
    sys.exit(0 if success else 1)
