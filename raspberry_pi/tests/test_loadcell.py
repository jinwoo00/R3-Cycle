#!/usr/bin/env python3
"""
Test script for HX711 Load Cell
Tests weight measurement and calibration

Usage: sudo python3 test_loadcell.py
"""

import sys
import time
import statistics

# Add parent directory to path
sys.path.append('/home/r3cycle/r3cycle')

try:
    from hx711 import HX711
    import RPi.GPIO as GPIO
    import config
except ImportError as e:
    print(f"[ERROR] Missing library: {e}")
    print("Run: pip3 install hx711 RPi.GPIO")
    sys.exit(1)

def calculate_weight(raw_value, zero_offset, reference_unit, inverted=False):
    """Calculate weight from raw value using manual formula"""
    # Always use absolute value of reference_unit (should be positive)
    ref_unit = abs(reference_unit)
    if ref_unit <= 0:
        return 0.0
    
    if inverted:
        # For inverted load cells (raw decreases when weight increases)
        weight = (zero_offset - raw_value) / ref_unit
    else:
        # Normal load cells (raw increases when weight increases)
        weight = (raw_value - zero_offset) / ref_unit
    
    return weight

def test_loadcell():
    """Test load cell"""
    print("=" * 50)
    print("R3-Cycle Load Cell Test & Calibration")
    print("=" * 50)
    print()

    # Store zero offset and reference unit for manual calculation
    zero_offset = None
    reference_unit = config.LOAD_CELL_REFERENCE_UNIT
    use_manual_calculation = False

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

        # Check library compatibility
        has_tare = hasattr(hx, 'tare')
        has_set_reference = hasattr(hx, 'set_reference_unit')
        has_get_weight = hasattr(hx, 'get_weight')

        if not has_set_reference or not has_get_weight:
            print("[INFO] Library version detected - some methods not available")
            print("[INFO] Will use manual weight calculation from raw values")
            use_manual_calculation = True
        print()

        # Reset and tare
        print("[2] Resetting and taring...")
        print("    Make sure load cell platform is EMPTY")
        input("    Press Enter when ready...")

        hx.reset()
        
        # Check if tare method exists (library version compatibility)
        if has_tare:
            hx.tare()
            print("[OK] Load cell tared (zeroed)")
        else:
            print("[INFO] tare() method not available - will use manual zero offset")
        print()

        # Read raw values for zero offset (take multiple samples for stability)
        print("[3] Reading raw values (zero offset)...")
        print("    ⚠️  CRITICAL: Make sure sensor platform is COMPLETELY EMPTY!")
        print("    ⚠️  Remove ALL objects, wait for vibrations to settle")
        print("    Waiting 3 seconds for sensor to stabilize...")
        time.sleep(3)  # Longer wait for stability
        
        print("    Taking multiple readings for stability...")
        zero_offset_readings = []
        for i in range(5):  # More samples for better stability
            raw_readings = hx.get_raw_data(5)
            if isinstance(raw_readings, list):
                avg_val = sum(raw_readings) / len(raw_readings) if raw_readings else 0
            else:
                avg_val = raw_readings
            zero_offset_readings.append(avg_val)
            print(f"    Sample {i+1}/5: {avg_val:.2f}")
            time.sleep(0.5)
        
        # Use average of all samples as zero offset
        zero_offset = sum(zero_offset_readings) / len(zero_offset_readings)
        
        # Check stability (standard deviation)
        import statistics
        if len(zero_offset_readings) > 1:
            std_dev = statistics.stdev(zero_offset_readings)
            print(f"\n    Zero offset (empty): {zero_offset:.2f}")
            print(f"    Stability (std dev): {std_dev:.2f}")
            
            if std_dev > 500:
                print(f"    ⚠️  WARNING: High variation ({std_dev:.2f}) - readings not stable!")
                print(f"    ⚠️  Possible causes:")
                print(f"       - Something is still on the sensor")
                print(f"       - Electrical noise or loose connections")
                print(f"       - Mechanical vibrations")
                print(f"    ⚠️  Continuing anyway, but accuracy may be affected...")
        else:
            print(f"    Zero offset (empty): {zero_offset:.2f}")
        
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
            raw_readings_weight = hx.get_raw_data(10)
            if isinstance(raw_readings_weight, list):
                raw_with_weight = sum(raw_readings_weight) / len(raw_readings_weight)
            else:
                raw_with_weight = raw_readings_weight

            print(f"\n    Zero offset (empty): {zero_offset:.2f}")
            print(f"    Raw value (with {known_weight}g): {raw_with_weight:.2f}")
            
            # Calculate reference unit
            raw_difference = raw_with_weight - zero_offset
            
            # Check if raw value increased or decreased
            if raw_difference < 0:
                print(f"    ⚠️  WARNING: Raw value DECREASED by {abs(raw_difference):.2f}")
                print(f"    ⚠️  This suggests load cell might be inverted or wires reversed")
                print(f"    ⚠️  Load cell appears to be INVERTED (raw decreases with weight)")
                # Use absolute value for reference unit (always positive)
                reference_unit = abs(raw_difference) / known_weight
                # Mark as inverted - we'll use inverted calculation
                use_inverted_calculation = True
            else:
                print(f"    Raw value INCREASED by {raw_difference:.2f} (normal)")
                reference_unit = raw_difference / known_weight
                use_inverted_calculation = False
            
            print(f"\n    Calculated Reference Unit: {reference_unit:.4f}")
            print(f"    (Always store as POSITIVE value in config.py)")
            print(f"    Update config.py with:")
            print(f"    LOAD_CELL_REFERENCE_UNIT = {reference_unit:.4f}")
            
            if use_inverted_calculation:
                print(f"\n    ⚠️  IMPORTANT: Load cell is INVERTED")
                print(f"    ⚠️  System will automatically detect and handle inversion")
                print(f"    ⚠️  You may want to fix wiring, but software will compensate")
            print()

            # Try to set reference unit if method exists
            if has_set_reference:
                hx.set_reference_unit(reference_unit)
                print("[OK] Reference unit set")
            else:
                print("[INFO] Using manual reference unit for calculations")
        else:
            print("    Skipping calibration")
            print(f"    Using current reference unit: {reference_unit}")
            print("    ⚠️  WARNING: Reference unit = 1 means readings will be INCORRECT!")
            print("    ⚠️  Weight readings will show raw differences, not actual grams.")
            print("    ⚠️  You MUST calibrate for accurate measurements.")
            print()
            
            # Try to set reference unit if method exists
            if has_set_reference:
                try:
                    hx.set_reference_unit(reference_unit)
                except:
                    use_manual_calculation = True
            else:
                use_manual_calculation = True
            
            print("    [INFO] For testing purposes, showing raw differences...")
            print()

        # Continuous reading
        print("[5] Continuous weight measurement")
        print("    Place objects on the sensor to test")
        print("    Remove all objects to see zero weight reading")
        print("    Press Ctrl+C to exit")
        print()
        
        # Show current zero offset for reference
        print(f"    [Reference] Zero offset: {zero_offset:.2f}")
        print(f"    [Reference] Expected empty reading: ~0.00g")
        print()

        consecutive_stable_readings = 0
        last_weight = None

        while True:
            try:
                if use_manual_calculation or not has_get_weight:
                    # Manual calculation from raw values
                    raw_readings = hx.get_raw_data(5)
                    if isinstance(raw_readings, list):
                        raw_value = sum(raw_readings) / len(raw_readings)
                    else:
                        raw_value = raw_readings
                    
                    # Ensure reference_unit is positive (use absolute value)
                    # use_inverted_calculation flag handles the calculation direction
                    weight = calculate_weight(raw_value, zero_offset, abs(reference_unit), use_inverted_calculation)
                else:
                    # Use library's get_weight if available
                    weight = hx.get_weight(5)
                
                weight = round(weight, 2)

                # Check stability (if reading is similar to last, count as stable)
                if last_weight is not None and abs(weight - last_weight) < 2.0:
                    consecutive_stable_readings += 1
                else:
                    consecutive_stable_readings = 0
                
                last_weight = weight

                # Validate against thresholds
                status = "OK"
                if weight < config.MIN_WEIGHT:
                    status = "TOO LIGHT"
                elif weight > config.MAX_WEIGHT:
                    status = "TOO HEAVY"
                
                # Show stability indicator
                stability_indicator = " ⭐" if consecutive_stable_readings >= 3 else ""
                
                # Show raw value for debugging if weight seems wrong
                if abs(weight) > 50 or (abs(weight) < 1 and raw_value is not None):
                    raw_display = f" (raw: {raw_value:.0f})"
                else:
                    raw_display = ""

                print(f"Weight: {weight:7.2f}g   [{status}]{stability_indicator}{raw_display}")

                time.sleep(1)

            except KeyboardInterrupt:
                print("\n\n[INFO] Test interrupted by user")
                print(f"[INFO] Final zero offset was: {zero_offset:.2f}")
                print("[INFO] If readings were unstable, try re-establishing zero offset")
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
