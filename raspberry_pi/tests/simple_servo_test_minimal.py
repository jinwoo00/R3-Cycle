#!/usr/bin/env python3
"""
Minimal Servo Test - Tests one servo at a time with detailed output
"""
import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

PLASTIC = 18  # Pin 12
PAPER = 13    # Pin 33

print("="*60)
print("MINIMAL SERVO TEST")
print("="*60)
print("\nTesting GPIO pins individually...\n")

def test_pin(pin, name):
    print(f"Testing {name} (GPIO {pin})...")
    
    try:
        # Setup
        GPIO.setup(pin, GPIO.OUT)
        print(f"  ✅ GPIO {pin} set as OUTPUT")
        
        # Create PWM
        pwm = GPIO.PWM(pin, 50)
        print(f"  ✅ PWM created on GPIO {pin}")
        
        # Start PWM
        pwm.start(0)
        print(f"  ✅ PWM started at 0%")
        time.sleep(0.5)
        
        # Test different duty cycles
        for duty, angle in [(2.5, 0), (7.5, 90), (12.5, 180), (7.5, 90), (2.5, 0)]:
            print(f"  Setting to {duty}% ({angle}°)...", end=" ", flush=True)
            pwm.ChangeDutyCycle(duty)
            time.sleep(1)
            print("✅")
        
        # Stop
        pwm.stop()
        GPIO.cleanup(pin)
        print(f"  ✅ {name} test COMPLETE\n")
        return True
        
    except Exception as e:
        print(f"  ❌ ERROR: {e}\n")
        try:
            pwm.stop()
            GPIO.cleanup(pin)
        except:
            pass
        return False

# Test each servo
print("1. Testing PLASTIC SERVO (GPIO 18, Pin 12)")
print("-" * 60)
plastic_ok = test_pin(PLASTIC, "Plastic Servo")

time.sleep(1)

print("2. Testing PAPER SERVO (GPIO 13, Pin 33)")
print("-" * 60)
paper_ok = test_pin(PAPER, "Paper Servo")

# Summary
print("="*60)
print("RESULTS:")
print("="*60)
print(f"Plastic Servo: {'✅ PASS' if plastic_ok else '❌ FAIL'}")
print(f"Paper Servo:   {'✅ PASS' if paper_ok else '❌ FAIL'}")
print("="*60)

if not (plastic_ok and paper_ok):
    print("\n⚠️  If servos didn't move:")
    print("  1. Check external 5V power is ON")
    print("  2. Check GND is connected to Pi Pin 14")
    print("  3. Check signal wires are on correct pins")
    print("  4. Try touching servo - should be warm (has power)")

