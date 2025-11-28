#!/usr/bin/env python3
"""
Servo Motor Test Script
Tests both plastic and paper bin servos independently
"""

import RPi.GPIO as GPIO
import time
import sys

# Servo pins (BCM numbering)
SERVO_PLASTIC_PIN = 18  # GPIO 18 (Physical Pin 12)
SERVO_PAPER_PIN = 13    # GPIO 13 (Physical Pin 33)

def setup_servos():
    """Initialize GPIO and servo PWM"""
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(SERVO_PLASTIC_PIN, GPIO.OUT)
    GPIO.setup(SERVO_PAPER_PIN, GPIO.OUT)
    
    # Create PWM instances (50Hz for standard servos)
    plastic_pwm = GPIO.PWM(SERVO_PLASTIC_PIN, 50)
    paper_pwm = GPIO.PWM(SERVO_PAPER_PIN, 50)
    
    # Start PWM with 0% duty cycle
    plastic_pwm.start(0)
    paper_pwm.start(0)
    
    return plastic_pwm, paper_pwm

def set_servo_angle(pwm, angle):
    """
    Set servo to specific angle (0-180 degrees)
    
    Duty cycle calculation:
    - 0° = 2.5% duty cycle
    - 90° = 7.5% duty cycle
    - 180° = 12.5% duty cycle
    """
    duty = 2.5 + (angle / 180.0) * 10.0
    pwm.ChangeDutyCycle(duty)
    time.sleep(0.5)  # Wait for servo to reach position
    pwm.ChangeDutyCycle(0)  # Stop sending signal to prevent jitter

def test_servo(pwm, name):
    """Test a single servo through its range"""
    print(f"\n{'='*60}")
    print(f"Testing {name}")
    print(f"{'='*60}")
    
    try:
        print(f"Moving to 0° (closed position)...")
        set_servo_angle(pwm, 0)
        time.sleep(1)
        
        print(f"Moving to 90° (middle position)...")
        set_servo_angle(pwm, 90)
        time.sleep(1)
        
        print(f"Moving to 180° (fully open)...")
        set_servo_angle(pwm, 180)
        time.sleep(1)
        
        print(f"Moving back to 90°...")
        set_servo_angle(pwm, 90)
        time.sleep(1)
        
        print(f"Moving back to 0° (closed)...")
        set_servo_angle(pwm, 0)
        time.sleep(1)
        
        print(f"✅ {name} test complete!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing {name}: {e}")
        return False

def main():
    print("="*60)
    print("SERVO MOTOR TEST")
    print("="*60)
    print("\nThis will test both servos:")
    print("  1. Plastic Bin Servo (GPIO 18, Pin 12)")
    print("  2. Paper Bin Servo (GPIO 13, Pin 33)")
    print("\nMake sure servos are connected correctly!")
    print("Watch the servo motors - they should move smoothly.\n")
    
    input("Press ENTER to start test...")
    
    try:
        # Initialize servos
        print("\nInitializing servos...")
        plastic_pwm, paper_pwm = setup_servos()
        print("✅ Servos initialized\n")
        
        # Test plastic servo
        plastic_ok = test_servo(plastic_pwm, "Plastic Bin Servo (GPIO 18)")
        
        # Wait between tests
        time.sleep(2)
        
        # Test paper servo
        paper_ok = test_servo(paper_pwm, "Paper Bin Servo (GPIO 13)")
        
        # Summary
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        print(f"Plastic Servo: {'✅ PASS' if plastic_ok else '❌ FAIL'}")
        print(f"Paper Servo:   {'✅ PASS' if paper_ok else '❌ FAIL'}")
        print("="*60)
        
        # Cleanup
        plastic_pwm.stop()
        paper_pwm.stop()
        GPIO.cleanup()
        print("\n✅ Test complete - GPIO cleaned up")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        GPIO.cleanup()
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        GPIO.cleanup()
        sys.exit(1)

if __name__ == "__main__":
    main()

