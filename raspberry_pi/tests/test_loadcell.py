#!/usr/bin/env python3
"""
Test script for HX711 Load Cell
Tests weight measurement and calibration

Usage: sudo python3 test_loadcell.py
"""

import sys
import time

# Add parent directory to path
sys.path.append('/home/pi/r3cycle')

try:
    from hx711 import HX711
    import RPi.GPIO as GPIO
    import config
except ImportError as e:
    print(f"[ERROR] Missing library: {e}")
    print("Run: pip3 install hx711 RPi.GPIO")
    sys.exit(1)

def test_loadcell():
    """Test load cell"""
    print("=" * 50)
    print("R3-Cycle Load Cell Test & Calibration")
    print("=" * 50)
    print()

    try:
        # Initialize load cell
        print("[1] Initializing HX711 load cell...")
        print(f"    DT Pin:  GPIO {config.PIN_LOAD_CELL_DT}")
        print(f"    SCK Pin: GPIO {config.PIN_LOAD_CELL_SCK}")

        hx = HX711(
            dout_pin=config.PIN_LOAD_CELL_DT,
            pd_sck_pin=config.PIN_LOAD_CELL_SCK
        )

        print("[OK] Load cell initialized")
        print()

        # Reset and tare
        print("[2] Resetting and taring...")
        print("    Make sure load cell platform is EMPTY")
        input("    Press Enter when ready...")

        hx.reset()
        hx.tare()
        print("[OK] Load cell tared (zeroed)")
        print()

        # Read raw values
        print("[3] Reading raw values...")
        raw_val = hx.get_raw_data(5)
        print(f"    Raw value (empty): {raw_val}")
        print()

        # Calibration
        print("[4] Calibration (optional)")
        print("    Place a known weight on the sensor")
        print("    Example: 100 grams")
        response = input("    Do you want to calibrate? (y/n): ")

        if response.lower() == 'y':
            known_weight = float(input("    Enter known weight in grams: "))
            input("    Place the weight on the sensor, then press Enter...")

            time.sleep(2)
            raw_with_weight = hx.get_raw_data(10)

            reference_unit = (raw_with_weight - raw_val) / known_weight
            print(f"\n    Calculated Reference Unit: {reference_unit}")
            print(f"    Update config.py with:")
            print(f"    LOAD_CELL_REFERENCE_UNIT = {reference_unit}")
            print()

            hx.set_reference_unit(reference_unit)

        else:
            print("    Skipping calibration")
            print(f"    Using current reference unit: {config.LOAD_CELL_REFERENCE_UNIT}")
            hx.set_reference_unit(config.LOAD_CELL_REFERENCE_UNIT)
            print()

        # Continuous reading
        print("[5] Continuous weight measurement")
        print("    Place objects on the sensor to test")
        print("    Press Ctrl+C to exit")
        print()

        while True:
            try:
                weight = hx.get_weight(5)
                weight = round(weight, 2)

                # Validate against thresholds
                status = "OK"
                if weight < config.MIN_WEIGHT:
                    status = "TOO LIGHT"
                elif weight > config.MAX_WEIGHT:
                    status = "TOO HEAVY"

                print(f"Weight: {weight:7.2f}g   [{status}]")

                time.sleep(1)

            except KeyboardInterrupt:
                print("\n\n[INFO] Test interrupted by user")
                break

    except Exception as e:
        print(f"[ERROR] Load cell test failed: {e}")
        return False

    finally:
        print("\n[CLEANUP] Cleaning up GPIO...")
        GPIO.cleanup()
        print("[DONE] Test complete")

    return True

if __name__ == "__main__":
    success = test_loadcell()
    sys.exit(0 if success else 1)
