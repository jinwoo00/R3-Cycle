#!/usr/bin/env python3
"""
Test script for IR Obstacle Sensor
Improved version with timestamps and stability checking

Usage: sudo python3 test_ir_sensor.py
"""

import sys
import time
from datetime import datetime

# Add parent directory to path
sys.path.append('/home/r3cycle/r3cycle')

try:
    import RPi.GPIO as GPIO
    import config
except ImportError as e:
    print(f"[ERROR] Missing library: {e}")
    print("Run: pip3 install RPi.GPIO")
    sys.exit(1)

def test_ir_sensor():
    """Test IR sensor with improved feedback"""
    print("=" * 60)
    print("R3-Cycle IR Obstacle Sensor Test (Improved)")
    print("=" * 60)
    print()

    try:
        # Setup GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        print("[1] Initializing IR sensor...")
        print(f"    GPIO Pin: {config.PIN_IR_SENSOR}")
        print("    Note: LOW (0) = object detected, HIGH (1) = no object")
        print()

        # Setup GPIO - without pull-up (sensor may have built-in pull-up)
        GPIO.setup(config.PIN_IR_SENSOR, GPIO.IN)
        print("[OK] IR sensor initialized")
        print()

        # Establish baseline first - more readings for better stability
        print("[2] Establishing baseline (10 seconds)...")
        print("    Please ensure NO object is near the sensor!")
        print("    Keep sensor clear for the next 10 seconds...")
        baseline_readings = []
        for i in range(100):  # 10 seconds at 0.1s intervals
            baseline_readings.append(GPIO.input(config.PIN_IR_SENSOR))
            time.sleep(0.1)
            if (i + 1) % 20 == 0:
                print(f"    Baseline: {i+1}/100 readings...")
        
        # Use majority vote for baseline
        baseline_state = max(set(baseline_readings), key=baseline_readings.count)
        baseline_count = baseline_readings.count(baseline_state)
        baseline_ratio = (baseline_count / len(baseline_readings)) * 100
        
        print(f"[OK] Baseline established: GPIO={baseline_state} ({'LOW' if baseline_state == GPIO.LOW else 'HIGH'})")
        print(f"    Stability: {baseline_count}/100 readings ({baseline_ratio:.1f}%)")
        
        # If baseline is too unstable, reject the test IMMEDIATELY
        if baseline_ratio < 75:
            print()
            print("=" * 60)
            print("[ERROR] Baseline too unstable! Cannot proceed with test.")
            print("=" * 60)
            print(f"Baseline stability: {baseline_ratio:.1f}% (need at least 75%)")
            print()
            print("Possible causes:")
            print("  1. Potentiometer too sensitive - adjust counter-clockwise")
            print("  2. Object too close to sensor - remove any objects")
            print("  3. Wiring issue - check GPIO 27 connection")
            print("  4. Sensor hardware problem - try different sensor")
            print()
            print("Please fix the issue and try again.")
            print("=" * 60)
            GPIO.cleanup()
            return False
        
        if baseline_ratio < 85:
            print(f"[WARNING] Baseline may be unstable! ({baseline_ratio:.1f}% consistent)")
            print(f"[WARNING] Sensor may be too sensitive or have interference")
            print(f"[WARNING] Consider adjusting potentiometer or checking wiring")
        
        print()
        print("[3] Starting detection test...")
        print("    ==========================================")
        print(f"    Baseline: GPIO={baseline_state} ({'LOW' if baseline_state == GPIO.LOW else 'HIGH'})")
        print(f"    Detection: Will detect when GPIO CHANGES from baseline {baseline_state}")
        print("    ==========================================")
        print("    Instructions:")
        print("    1. Place paper at 15cm → Should NOT detect")
        print("    2. Place paper at 10cm → Should NOT detect")
        print("    3. Place paper at 5cm → Should DETECT (GPIO changes)")
        print("    4. Place paper at 2-3cm → Should DETECT (GPIO changes)")
        print("    ==========================================")
        print()
        print("Waiting for state changes (CHANGE from baseline only)...")
        print()

        # Start with baseline state (no detection)
        last_state = False  # False = at baseline (no detection), True = changed from baseline (detection)
        state_start_time = time.time()
        read_count = 0
        state_changes = 0
        last_log_time = time.time()
        
        # Stronger debouncing: require 15 consecutive reads (1.5 seconds) for stable state
        consecutive_count = 0
        debounce_threshold = 15  # 1.5 seconds at 0.1s intervals
        current_stable_state = None
        
        # Minimum stable time before considering state change valid (3 seconds)
        min_stable_time = 3.0
        state_candidate = None
        state_candidate_start = None

        while True:
            try:
                read_count += 1
                current_time = time.time()
                
                # Read raw GPIO value
                raw_value = GPIO.input(config.PIN_IR_SENSOR)
                
                # IMPORTANT: Detect CHANGE from baseline, not absolute value!
                # If baseline is LOW (0), detection happens when GPIO goes HIGH (1)
                # If baseline is HIGH (1), detection happens when GPIO goes LOW (0)
                changed_from_baseline = (raw_value != baseline_state)
                
                # Strong debouncing: count consecutive reads of changed state
                if changed_from_baseline == current_stable_state:
                    consecutive_count += 1
                else:
                    consecutive_count = 1
                    current_stable_state = changed_from_baseline
                
                # Check if we have a candidate state change
                if consecutive_count >= debounce_threshold:
                    # We have enough consecutive reads, check if it's different from current state
                    if changed_from_baseline != last_state:
                        # New state candidate
                        if state_candidate != changed_from_baseline:
                            # New candidate, start timing
                            state_candidate = changed_from_baseline
                            state_candidate_start = current_time
                        elif current_time - state_candidate_start >= min_stable_time:
                            # Candidate has been stable for minimum time, accept it
                            stable_detected = changed_from_baseline
                        else:
                            # Candidate not stable long enough yet
                            stable_detected = last_state if last_state is not None else False
                    else:
                        # Same as current state, reset candidate
                        state_candidate = None
                        state_candidate_start = None
                        stable_detected = changed_from_baseline
                else:
                    # Still settling, keep current state
                    stable_detected = last_state if last_state is not None else False
                    state_candidate = None
                    state_candidate_start = None
                
                # Check for state change
                if stable_detected != last_state:
                    # State changed! (after debouncing and minimum stable time)
                    state_changes += 1
                    
                    if state_start_time is not None:
                        duration = current_time - state_start_time
                        prev_status = "DETECTED" if last_state else "CLEAR"
                        print(f"[CHANGE #{state_changes}] State changed after {duration:.2f}s (stable)")
                    
                    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                    
                    if stable_detected:
                        # Changed from baseline = detection
                        print(f"[{timestamp}] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                        print(f"[{timestamp}] ✅ DETECTED: Object present!")
                        print(f"[{timestamp}]    GPIO changed: {baseline_state} → {raw_value}")
                        print(f"[{timestamp}]    Baseline was {baseline_state}, current is {raw_value} (CHANGED)")
                        print(f"[{timestamp}]    (Stable for {min_stable_time:.1f}s with {debounce_threshold} consecutive reads)")
                        print(f"[{timestamp}] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                    else:
                        # Back to baseline = no detection
                        print(f"[{timestamp}] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                        print(f"[{timestamp}] ⬜ CLEAR: No object detected")
                        print(f"[{timestamp}]    GPIO returned to baseline: {raw_value} (same as baseline {baseline_state})")
                        print(f"[{timestamp}]    (Stable for {min_stable_time:.1f}s with {debounce_threshold} consecutive reads)")
                        print(f"[{timestamp}] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                    
                    last_state = stable_detected
                    state_start_time = current_time
                    state_candidate = None
                    state_candidate_start = None
                    print()
                
                # Periodic status (every 10 seconds if no changes)
                elif current_time - last_log_time >= 10.0:
                    duration = current_time - state_start_time if state_start_time else 0
                    status = "DETECTED" if stable_detected else "CLEAR"
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    print(f"[{timestamp}] [STATUS] {status} (stable for {duration:.1f}s, {read_count} total reads)")
                    last_log_time = current_time

                time.sleep(0.1)

            except KeyboardInterrupt:
                print("\n\n" + "=" * 60)
                print("[INFO] Test interrupted by user")
                print()
                print("Summary:")
                print(f"  Total reads: {read_count}")
                print(f"  State changes: {state_changes}")
                if state_start_time:
                    final_duration = time.time() - state_start_time
                    final_status = "DETECTED" if last_state else "CLEAR"
                    print(f"  Final state: {final_status} (stable for {final_duration:.2f}s)")
                print("=" * 60)
                break

    except Exception as e:
        print(f"[ERROR] IR sensor test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        print("\n[CLEANUP] Cleaning up GPIO...")
        GPIO.cleanup()
        print("[DONE] Test complete")

    return True

if __name__ == "__main__":
    success = test_ir_sensor()
    sys.exit(0 if success else 1)
