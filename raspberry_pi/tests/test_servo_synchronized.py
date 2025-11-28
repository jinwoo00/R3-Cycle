#!/usr/bin/env python3
"""
Synchronized Servo Test Script - Complete Rotation Pattern
Tests both servos completing full rotation cycle continuously until Ctrl+C

Pattern:
1. Both servos rotate to 180° (Servo1=CCW, Servo2=CW) - COMPLETE FIRST
2. Both servos return to 0° (Servo1=CW, Servo2=CCW) - COMPLETE FIRST
3. Repeat continuously

Both servos must COMPLETE each phase before moving to next phase
"""

import RPi.GPIO as GPIO
import time
import sys
import signal

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
SERVO_CW_SPEED = 6.0   # Clockwise rotation speed
SERVO_CCW_SPEED = 9.0  # Counter-clockwise rotation speed

# Rotation timing (time to complete "180 degrees" of rotation)
ROTATION_DURATION = 5.0  # How long to rotate to complete 180° (seconds)

# Global variables for cleanup
servo1_pwm = None
servo2_pwm = None
running = True

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    global running
    print("\n\n⚠️  Stopping servos (Ctrl+C detected)...")
    running = False

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

def stop_servos(servo1_pwm, servo2_pwm):
    """Stop both servos"""
    try:
        set_servo_speed(servo1_pwm, SERVO_STOP)
        set_servo_speed(servo2_pwm, SERVO_STOP)
        time.sleep(0.5)
    except:
        pass

def test_synchronized_continuous():
    """Test synchronized servos - complete each phase before next"""
    global servo1_pwm, servo2_pwm, running
    
    print("="*60)
    print("SYNCHRONIZED SERVO TEST - COMPLETE ROTATION PATTERN")
    print("="*60)
    print("\nRotation Pattern:")
    print("  Phase 1: Both servos rotate to 180°")
    print("    - Servo #1: Counter-clockwise")
    print("    - Servo #2: Clockwise")
    print("    ⚠️  Both must COMPLETE 180° rotation first")
    print("\n  Phase 2: Both servos return to 0°")
    print("    - Servo #1: Clockwise (back)")
    print("    - Servo #2: Counter-clockwise (back)")
    print("    ⚠️  Both must COMPLETE return to 0° first")
    print("\n  Then repeat continuously...")
    print(f"\nDuration per phase: {ROTATION_DURATION} seconds")
    print("\n⚠️  Test will run CONTINUOUSLY - NO STOPPING")
    print("⚠️  Press Ctrl+C to stop the test")
    print("="*60)
    
    input("\nPress ENTER to start continuous test...")
    
    try:
        # Setup signal handler for Ctrl+C
        signal.signal(signal.SIGINT, signal_handler)
        
        # Initialize servos
        print("\nInitializing servos...")
        servo1_pwm, servo2_pwm = setup_servos()
        print("✅ Servos initialized at 0° position\n")
        time.sleep(1)
        
        cycle_count = 0
        
        print("="*60)
        print("STARTING CONTINUOUS SYNCHRONIZED ROTATION")
        print("="*60)
        print("\n⚠️  Press Ctrl+C to stop\n")
        
        while running:
            cycle_count += 1
            
            # ============================================
            # PHASE 1: Rotate to 180° - BOTH MUST COMPLETE
            # ============================================
            print(f"\n[Cycle {cycle_count}] PHASE 1: Rotating to 180°...")
            print(f"  Servo #1: Counter-clockwise ({SERVO_CCW_SPEED}%)")
            print(f"  Servo #2: Clockwise ({SERVO_CW_SPEED}%)")
            print("  ⚠️  Both servos must COMPLETE 180° rotation...")
            
            # Start both servos rotating to 180°
            set_servo_speed(servo1_pwm, SERVO_CCW_SPEED)  # Servo 1: Counter-clockwise
            set_servo_speed(servo2_pwm, SERVO_CW_SPEED)   # Servo 2: Clockwise
            
            # Wait for BOTH to complete 180° rotation
            elapsed = 0
            while elapsed < ROTATION_DURATION and running:
                remaining = int(ROTATION_DURATION - elapsed)
                print(f"  Rotating to 180°... {remaining} seconds remaining", end='\r')
                time.sleep(0.5)
                elapsed += 0.5
            
            if not running:
                break
            
            print(f"\n  ✅ Both servos completed 180° rotation")
            time.sleep(0.2)  # Brief pause after completing 180°
            
            # ============================================
            # PHASE 2: Return to 0° - BOTH MUST COMPLETE
            # ============================================
            print(f"\n[Cycle {cycle_count}] PHASE 2: Returning to 0°...")
            print(f"  Servo #1: Clockwise ({SERVO_CW_SPEED}%) - returning")
            print(f"  Servo #2: Counter-clockwise ({SERVO_CCW_SPEED}%) - returning")
            print("  ⚠️  Both servos must COMPLETE return to 0°...")
            
            # Reverse direction - both return to 0°
            set_servo_speed(servo1_pwm, SERVO_CW_SPEED)   # Servo 1: Clockwise (back to 0°)
            set_servo_speed(servo2_pwm, SERVO_CCW_SPEED)  # Servo 2: Counter-clockwise (back to 0°)
            
            # Wait for BOTH to complete return to 0°
            elapsed = 0
            while elapsed < ROTATION_DURATION and running:
                remaining = int(ROTATION_DURATION - elapsed)
                print(f"  Returning to 0°... {remaining} seconds remaining", end='\r')
                time.sleep(0.5)
                elapsed += 0.5
            
            if not running:
                break
            
            print(f"\n  ✅ Both servos completed return to 0°")
            time.sleep(0.2)  # Brief pause before next cycle
            
            # Loop continues automatically - start next cycle
        
        # Stop servos only when Ctrl+C is pressed
        print("\n\nStopping servos...")
        stop_servos(servo1_pwm, servo2_pwm)
        
        # Summary
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        print(f"✅ Completed {cycle_count} full cycle(s)")
        print("✅ Each cycle: 180° rotation → Return to 0°")
        print("✅ Servos stopped successfully")
        print("="*60)
        
        # Cleanup
        servo1_pwm.stop()
        servo2_pwm.stop()
        GPIO.cleanup()
        print("\n✅ Test complete - GPIO cleaned up")
        
        return True
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user (KeyboardInterrupt)")
        stop_servos(servo1_pwm, servo2_pwm)
        try:
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
        stop_servos(servo1_pwm, servo2_pwm)
        try:
            servo1_pwm.stop()
            servo2_pwm.stop()
            GPIO.cleanup()
        except:
            pass
        sys.exit(1)

if __name__ == "__main__":
    test_synchronized_continuous()
