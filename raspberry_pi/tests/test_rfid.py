#!/usr/bin/env python3
"""
Test script for RC522 RFID Reader
Tests RFID card reading functionality

Usage: sudo python3 test_rfid.py
"""

import sys
import time

try:
    from mfrc522 import SimpleMFRC522
    import RPi.GPIO as GPIO
except ImportError as e:
    print(f"[ERROR] Missing library: {e}")
    print("Run: pip3 install mfrc522 RPi.GPIO")
    sys.exit(1)

def test_rfid():
    """Test RFID reader"""
    print("=" * 50)
    print("R3-Cycle RFID Reader Test")
    print("=" * 50)
    print()

    try:
        # Initialize RFID reader
        print("[1] Initializing RFID reader...")
        reader = SimpleMFRC522()
        print("[OK] RFID reader initialized")
        print()

        # Read loop
        print("[2] Waiting for RFID card...")
        print("    Place your RFID card near the reader")
        print("    Press Ctrl+C to exit")
        print()

        while True:
            try:
                print("Scanning...")
                tag_id, tag_text = reader.read()

                print("-" * 50)
                print(f"[SUCCESS] Card Detected!")
                print(f"  Tag ID:   {tag_id}")
                print(f"  Tag Text: {tag_text.strip() if tag_text else '(empty)'}")
                print("-" * 50)
                print()

                # Wait before next scan
                print("Remove card and scan again, or press Ctrl+C to exit")
                time.sleep(3)

            except KeyboardInterrupt:
                print("\n\n[INFO] Test interrupted by user")
                break

    except Exception as e:
        print(f"[ERROR] RFID test failed: {e}")
        return False

    finally:
        print("\n[CLEANUP] Cleaning up GPIO...")
        GPIO.cleanup()
        print("[DONE] Test complete")

    return True

if __name__ == "__main__":
    success = test_rfid()
    sys.exit(0 if success else 1)
