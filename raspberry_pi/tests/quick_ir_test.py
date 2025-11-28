#!/usr/bin/env python3
"""
Quick IR Sensor Test - Direct GPIO Reading
Tests if IR sensor GPIO is responding to objects

Usage: sudo python3 quick_ir_test.py
"""

import RPi.GPIO as GPIO
import time

# Setup
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(27, GPIO.IN)

print("=" * 60)
print("IR SENSOR QUICK TEST (GPIO 27 / Pin 13)")
print("=" * 60)
print()
print("Instructions:")
print("  1. Observe the readings below")
print("  2. Put paper/hand CLOSE (1-3cm) to sensor")
print("  3. Watch if value changes from 1 to 0")
print()
print("Readings:")
print("  1 (HIGH) = No object / Clear")
print("  0 (LOW)  = Object detected")
print()
print("If sensor NEVER changes to 0:")
print("  → Turn potentiometer CLOCKWISE (increase sensitivity)")
print()
print("If sensor is ALWAYS 0:")
print("  → Turn potentiometer COUNTER-CLOCKWISE (decrease sensitivity)")
print()
print("-" * 60)
print()

try:
    count = 0
    last_value = None
    detections = 0
    
    while True:
        value = GPIO.input(27)
        
        # Count state changes
        if last_value is not None and last_value != value:
            if value == 0:
                detections += 1
                print(f"\n🔴 DETECTION #{detections}! GPIO changed: 1 → 0 (Object detected!)\n")
            else:
                print(f"\n🟢 GPIO changed: 0 → 1 (Object removed)\n")
        
        last_value = value
        
        # Display current reading
        bar = "█" * 40 if value == 0 else "░" * 40
        status = "OBJECT DETECTED" if value == 0 else "CLEAR          "
        print(f"\rGPIO 27: {value} [{bar}] {status} | Checks: {count} | Detections: {detections}", end='', flush=True)
        
        count += 1
        time.sleep(0.1)
        
except KeyboardInterrupt:
    print("\n")
    print("-" * 60)
    print(f"\nTest Summary:")
    print(f"  Total checks: {count}")
    print(f"  Total detections: {detections}")
    print()
    if detections == 0:
        print("⚠️  NO DETECTIONS - Try adjusting potentiometer CLOCKWISE")
    elif detections > 100:
        print("⚠️  TOO SENSITIVE - Try adjusting potentiometer COUNTER-CLOCKWISE")
    else:
        print("✅ Sensor is working!")
    print()
finally:
    GPIO.cleanup()
    print("Test complete.")

