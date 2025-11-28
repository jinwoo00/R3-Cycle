#!/usr/bin/env python3
"""
Synchronized Opposite Rotation Test Script for SG90 Position Servos
Tests both servos moving in opposite directions simultaneously

Pattern:
- Servo #1: 0° → 180° (counter-clockwise)
- Servo #2: 180° → 0° (clockwise)
- Both servos move simultaneously in opposite directions
- Returns to idle (90°) after each cycle

This matches the actual dispensing pattern used in main.py
"""

import RPi.GPIO as GPIO
import time
import sys
import signal

# Import config for servo settings
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import config

# Servo pins (BCM numbering)
SERVO_PIN_1 = config.PIN_SERVO_COLLECTION  # GPIO 18 (Physical Pin 12) - Collection/Roller 1
SERVO_PIN_2 = config.PIN_SERVO_REWARD      # GPIO 13 (Physical Pin 33) - Reward/Roller 2

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
    
    # Create PWM instances (50Hz for standard SG90 servos)
    servo1_pwm = GPIO.PWM(SERVO_PIN_1, config.SERVO_FREQUENCY)
    servo2_pwm = GPIO.PWM(SERVO_PIN_2, config.SERVO_FREQUENCY)
    
    # Calculate duty cycle for idle position (90 degrees)
    idle_duty_cycle = 2.5 + (config.SERVO_COLLECTION_IDLE / 180.0) * 10.0
    
    # Start PWM with idle position
    servo1_pwm.start(idle_duty_cycle)
    servo2_pwm.start(idle_duty_cycle)
    
    # Small delay to allow servos to reach position
    time.sleep(config.SERVO_MOVE_DELAY)
    
    return servo1_pwm, servo2_pwm

def set_servo_angle(pwm, angle, delay=True):
    """
    Set servo to specific angle (SG90 position servo)
    
    Args:
        pwm: PWM object for the servo
        angle: Angle in degrees (0-180)
        delay: Whether to add delay after setting angle
    """
    if pwm is None:
        return
    
    # Clamp angle to valid range (0-180 degrees)
    angle = max(0.0, min(180.0, angle))
    
    # Convert angle to duty cycle
    # SG90: 2.5% (0°) to 12.5% (180°)
    duty_cycle = 2.5 + (angle / 180.0) * 10.0
    
    # Set duty cycle
    pwm.ChangeDutyCycle(duty_cycle)
    
    # Small delay for servo to reach position (optional)
    if delay:
        time.sleep(config.SERVO_MOVE_DELAY)

def stop_servos(servo1_pwm, servo2_pwm):
    """Return both servos to idle position"""
    try:
        set_servo_angle(servo1_pwm, config.SERVO_COLLECTION_IDLE)
        set_servo_angle(servo2_pwm, config.SERVO_REWARD_IDLE)
        time.sleep(0.5)
    except:
        pass

def test_synchronized_opposite():
    """Test synchronized opposite rotation pattern"""
    global servo1_pwm, servo2_pwm, running
    
    print("="*70)
    print("SYNCHRONIZED OPPOSITE ROTATION TEST (SG90 Position Servos)")
    print("="*70)
    print("\nRotation Pattern:")
    print("  Servo #1 (GPIO 18): 0° → 180° (counter-clockwise)")
    print("  Servo #2 (GPIO 13): 180° → 0° (clockwise)")
    print("  ⚠️  Both servos move SIMULTANEOUSLY in OPPOSITE directions")
    print("\nConfiguration:")
    print(f"  Angle Step: {config.SERVO_DISPENSE_ANGLE_STEP}°")
    print(f"  Step Delay: {config.SERVO_DISPENSE_STEP_DELAY}s")
    print(f"  Cycles per test: {config.SERVO_DISPENSE_CYCLES}")
    print("\n⚠️  Test will run CONTINUOUSLY - Press Ctrl+C to stop")
    print("="*70)
    
    input("\nPress ENTER to start test...")
    
    try:
        # Setup signal handler for Ctrl+C
        signal.signal(signal.SIGINT, signal_handler)
        
        # Initialize servos
        print("\nInitializing servos...")
        servo1_pwm, servo2_pwm = setup_servos()
        print(f"✅ Servos initialized at idle position ({config.SERVO_COLLECTION_IDLE}°)\n")
        time.sleep(1)
        
        cycle_count = 0
        
        print("="*70)
        print("STARTING SYNCHRONIZED OPPOSITE ROTATION")
        print("="*70)
        print("\n⚠️  Press Ctrl+C to stop\n")
        
        while running:
            cycle_count += 1
            
            print(f"\n[Cycle {cycle_count}] Starting synchronized opposite rotation...")
            print(f"  Servo #1: {config.SERVO_COLLECTION_START}° → {config.SERVO_COLLECTION_END}°")
            print(f"  Servo #2: {config.SERVO_REWARD_START}° → {config.SERVO_REWARD_END}°")
            
            # Move to starting positions first
            print("  Moving to starting positions...")
            set_servo_angle(servo1_pwm, config.SERVO_COLLECTION_START)
            set_servo_angle(servo2_pwm, config.SERVO_REWARD_START)
            
            if not running:
                break
            
            # Calculate number of steps
            angle_range = abs(config.SERVO_COLLECTION_END - config.SERVO_COLLECTION_START)
            num_steps = int(angle_range / config.SERVO_DISPENSE_ANGLE_STEP)
            
            print(f"  Rotating in opposite directions ({num_steps} steps)...")
            
            # Synchronized opposite rotation: Servo 1 goes 0°→180°, Servo 2 goes 180°→0°
            for step in range(num_steps + 1):
                if not running:
                    break
                
                # Calculate current angles for both servos
                # Servo #1: 0° → 180° (forward)
                angle1 = config.SERVO_COLLECTION_START + (step * config.SERVO_DISPENSE_ANGLE_STEP)
                angle1 = min(angle1, config.SERVO_COLLECTION_END)
                
                # Servo #2: 180° → 0° (reverse, opposite direction)
                angle2 = config.SERVO_REWARD_START - (step * config.SERVO_DISPENSE_ANGLE_STEP)
                angle2 = max(angle2, config.SERVO_REWARD_END)
                
                # Set both servos simultaneously (without delay for faster movement)
                set_servo_angle(servo1_pwm, angle1, delay=False)
                set_servo_angle(servo2_pwm, angle2, delay=False)
                
                # Small delay between steps for smooth movement
                if step < num_steps:
                    time.sleep(config.SERVO_DISPENSE_STEP_DELAY)
                
                # Progress indicator
                if step % 10 == 0 or step == num_steps:
                    progress = int((step / num_steps) * 100)
                    print(f"    Progress: {progress}% (Servo1: {angle1:.0f}°, Servo2: {angle2:.0f}°)", end='\r')
            
            if not running:
                break
            
            print(f"\n  ✅ Cycle {cycle_count} complete - both servos reached end positions")
            
            # Return to idle position
            print("  Returning to idle position...")
            time.sleep(config.SERVO_RETURN_DELAY)
            set_servo_angle(servo1_pwm, config.SERVO_COLLECTION_IDLE)
            set_servo_angle(servo2_pwm, config.SERVO_REWARD_IDLE)
            
            print(f"  ✅ Returned to idle ({config.SERVO_COLLECTION_IDLE}°)\n")
            
            # Brief pause before next cycle
            time.sleep(1)
        
        # Stop servos only when Ctrl+C is pressed
        print("\n\nStopping servos...")
        stop_servos(servo1_pwm, servo2_pwm)
        
        # Summary
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)
        print(f"✅ Completed {cycle_count} cycle(s)")
        print("✅ Each cycle: Synchronized opposite rotation (0°↔180°)")
        print("✅ Servos returned to idle position")
        print("="*70)
        
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
    test_synchronized_opposite()

