#!/usr/bin/env python3
"""
Test script for IR Obstacle Sensor
Tests paper insertion detection

Usage: sudo python3 test_ir_sensor.py
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

def test_ir_sensor():
    """Test IR sensor"""
    print("=" * 50)
    print("R3-Cycle IR Obstacle Sensor Test")
    print("=" * 50)
    print()

    try:
        # Setup GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        print("[1] Initializing IR sensor...")
        print(f"    GPIO Pin: {config.PIN_IR_SENSOR}")

        GPIO.setup(config.PIN_IR_SENSOR, GPIO.IN)
        print("[OK] IR sensor initialized")
        print()

        # Test reading
        print("[2] Testing sensor")
        print("    Insert and remove objects to test detection")
        print("    Press Ctrl+C to exit")
        print()

        last_state = None

        while True:
            try:
                # Read sensor (HIGH = object detected)
                detected = GPIO.input(config.PIN_IR_SENSOR) == GPIO.HIGH

                # Only print on state change
                if detected != last_state:
                    if detected:
                        print("[DETECTED] *** Paper/Object Detected! ***")
                    else:
                        print("[CLEAR]    No object detected")

                    last_state = detected

                time.sleep(0.1)

            except KeyboardInterrupt:
                print("\n\n[INFO] Test interrupted by user")
                break

    except Exception as e:
        print(f"[ERROR] IR sensor test failed: {e}")
        return False

    finally:
        print("\n[CLEANUP] Cleaning up GPIO...")
        GPIO.cleanup()
        print("[DONE] Test complete")

    return True

if __name__ == "__main__":
    success = test_ir_sensor()
    sys.exit(0 if success else 1)
