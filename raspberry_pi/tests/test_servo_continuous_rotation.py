#!/usr/bin/env python3
"""
Continuous Rotation Servo Test Script
Tests both servos rotating 360° continuously in opposite directions

Servo #1: Rotates CLOCKWISE continuously
Servo #2: Rotates COUNTER-CLOCKWISE continuously (opposite)

Perfect for synchronized dispensing with metal rollers!
"""

import RPi.GPIO as GPIO
import time
import sys

# Servo pins (BCM numbering)
SERVO_PIN_1 = 18  # GPIO 18 (Physical Pin 12) - Collection/Roller 1
SERVO_PIN_2 = 13  # GPIO 13 (Physical Pin 33) - Reward/Roller 2

# Configuration
SERVO_FREQUENCY = 50  # Standard servo frequency (Hz)

# Continuous Rotation Servo Duty Cycle Values
# 7.5% = STOP/Neutral
# < 7.5% = Clockwise (faster as decreases)
# > 7.5% = Counter-clockwise (faster as increases)
SERVO_STOP = 7.5       # Stop position
SERVO_CW_FAST = 6.0    # Fast clockwise (adjust as needed)
SERVO_CCW_FAST = 9.0   # Fast counter-clockwise (adjust as needed)

# Test duration
TEST_DURATION = 5.0     # How long to rotate (seconds)

def setup_servos():
    """Initialize GPIO and servo PWM"""
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(SERVO_PIN_1, GPIO.OUT)
    GPIO.setup(SERVO_PIN_2, GPIO.OUT)
    
    # Create PWM instances (50Hz for standard servos)
    servo1_pwm = GPIO.PWM(SERVO_PIN_1, SERVO_FREQUENCY)
    servo2_pwm = GPIO.PWM(SERVO_PIN_2, SERVO_FREQUENCY)
    
    # Start PWM with stop position (neutral)
    servo1_pwm.start(SERVO_STOP)
    servo2_pwm.start(SERVO_STOP)
    
    return servo1_pwm, servo2_pwm

def set_servo_speed(pwm, duty_cycle):
    """
    Set continuous rotation servo speed/direction
    
    Args:
        pwm: PWM object
        duty_cycle: Duty cycle percentage (5-10%)
    """
    # Clamp to safe range
    duty_cycle = max(5.0, min(10.0, duty_cycle))
    pwm.ChangeDutyCycle(duty_cycle)

def test_continuous_rotation():
    """Test continuous rotation servos in opposite directions"""
    print("="*60)
    print("CONTINUOUS ROTATION SERVO TEST (360°)")
    print("="*60)
    print("\nServo Configuration:")
    print("  Servo #1 (GPIO 18, Pin 12): Positioned at 0 degrees")
    print("  Servo #2 (GPIO 13, Pin 33): Positioned at 360 degrees (same as 0°)")
    print("\n  Both servos rotate in SAME direction (synchronized)")
    print(f"\nDuration: {TEST_DURATION} seconds")
    print("\n⚠️  Watch both servos - they should rotate in SAME direction!")
    print("="*60)
    
    input("\nPress ENTER to start test...")
    
    try:
        # Initialize servos
        print("\nInitializing servos...")
        servo1_pwm, servo2_pwm = setup_servos()
        print("✅ Servos initialized at STOP position\n")
        
        # Stop position test
        print("="*60)
        print("TEST 1: STOP Position")
        print("="*60)
        print("Servos should be stopped...")
        set_servo_speed(servo1_pwm, SERVO_STOP)
        set_servo_speed(servo2_pwm, SERVO_STOP)
        time.sleep(2)
        print("✅ Stop position test complete\n")
        
        # Continuous rotation test
        print("="*60)
        print("TEST 2: SYNCHRONIZED CONTINUOUS ROTATION")
        print("="*60)
        print("\nStarting rotation...")
        print("  Servo #1: CLOCKWISE (duty cycle: {}%)".format(SERVO_CW_FAST))
        print("  Servo #2: CLOCKWISE (duty cycle: {}%) - SAME direction".format(SERVO_CW_FAST))
        print("\nRotating for {} seconds...".format(TEST_DURATION))
        print("Watch the servos - they should rotate in SAME direction (synchronized)!\n")
        
        # Start rotation - BOTH in same direction (both start at same position)
        set_servo_speed(servo1_pwm, SERVO_CW_FAST)   # Clockwise
        set_servo_speed(servo2_pwm, SERVO_CW_FAST)   # Clockwise (same direction)
        
        # Countdown
        for i in range(int(TEST_DURATION), 0, -1):
            print(f"  Rotating... {i} seconds remaining", end='\r')
            time.sleep(1)
        
        print("\n\nStopping servos...")
        
        # Stop both servos
        set_servo_speed(servo1_pwm, SERVO_STOP)
        set_servo_speed(servo2_pwm, SERVO_STOP)
        time.sleep(1)
        
        print("✅ Servos stopped\n")
        
        # Speed adjustment test
        print("="*60)
        print("TEST 3: Speed Adjustment")
        print("="*60)
        print("\nTesting different speeds...")
        
        speeds = [
            (6.5, "Medium clockwise"),
            (7.0, "Slow clockwise"),
            (7.5, "STOP"),
            (8.0, "Slow counter-clockwise"),
            (8.5, "Medium counter-clockwise")
        ]
        
        for duty, description in speeds:
            print(f"\n  Setting Servo #1 to: {description} ({duty}%)")
            set_servo_speed(servo1_pwm, duty)
            time.sleep(2)
            set_servo_speed(servo1_pwm, SERVO_STOP)
            time.sleep(0.5)
        
        print("\n✅ Speed adjustment test complete\n")
        
        # Final stop
        print("="*60)
        print("FINAL STOP")
        print("="*60)
        set_servo_speed(servo1_pwm, SERVO_STOP)
        set_servo_speed(servo2_pwm, SERVO_STOP)
        time.sleep(1)
        
        # Summary
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        print("✅ Continuous rotation test complete!")
        print("✅ Servos rotate 360° continuously")
        print("✅ Servo #1: Clockwise (Pin 12, GPIO 18)")
        print("✅ Servo #2: Clockwise (Pin 33, GPIO 13) - SAME direction")
        print("✅ Both servos synchronized - rotating together!")
        print("="*60)
        
        # Cleanup
        servo1_pwm.stop()
        servo2_pwm.stop()
        GPIO.cleanup()
        print("\n✅ Test complete - GPIO cleaned up")
        
        return True
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        try:
            set_servo_speed(servo1_pwm, SERVO_STOP)
            set_servo_speed(servo2_pwm, SERVO_STOP)
            time.sleep(0.5)
            servo1_pwm.stop()
            servo2_pwm.stop()
            GPIO.cleanup()
        except:
            pass
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        try:
            set_servo_speed(servo1_pwm, SERVO_STOP)
            set_servo_speed(servo2_pwm, SERVO_STOP)
            servo1_pwm.stop()
            servo2_pwm.stop()
            GPIO.cleanup()
        except:
            pass
        sys.exit(1)

if __name__ == "__main__":
    test_continuous_rotation()

