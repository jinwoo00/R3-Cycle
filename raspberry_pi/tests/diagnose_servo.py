#!/usr/bin/env python3
"""
Servo Diagnostic Script
Tests GPIO pins and PWM functionality to identify issues
"""

import RPi.GPIO as GPIO
import time
import sys

# Servo pins
PLASTIC_PIN = 18  # GPIO 18
PAPER_PIN = 13    # GPIO 13

def check_gpio_state():
    """Check current GPIO pin states"""
    print("="*60)
    print("GPIO PIN STATE CHECK")
    print("="*60)
    
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    
    pins_to_check = [PLASTIC_PIN, PAPER_PIN]
    
    for pin in pins_to_check:
        try:
            # Try to read pin state
            GPIO.setup(pin, GPIO.IN)
            value = GPIO.input(pin)
            print(f"GPIO {pin}: State = {value} (as INPUT)")
        except Exception as e:
            print(f"GPIO {pin}: ❌ ERROR - {e}")
    
    print()

def test_pwm_creation():
    """Test if PWM can be created on pins"""
    print("="*60)
    print("PWM CREATION TEST")
    print("="*60)
    
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    
    results = {}
    
    for pin_name, pin_num in [("Plastic (GPIO 18)", PLASTIC_PIN), ("Paper (GPIO 13)", PAPER_PIN)]:
        try:
            GPIO.setup(pin_num, GPIO.OUT)
            pwm = GPIO.PWM(pin_num, 50)
            pwm.start(0)
            results[pin_name] = "✅ SUCCESS"
            pwm.stop()
            GPIO.cleanup(pin_num)
        except Exception as e:
            results[pin_name] = f"❌ FAILED: {e}"
        print(f"{pin_name}: {results[pin_name]}")
    
    print()
    return results

def test_raw_pwm(pin_num, pin_name):
    """Test raw PWM signal on pin"""
    print(f"Testing {pin_name} (GPIO {pin_num})...")
    
    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(pin_num, GPIO.OUT)
        
        pwm = GPIO.PWM(pin_num, 50)
        pwm.start(0)
        
        print(f"  Starting PWM at 0%...")
        time.sleep(0.5)
        
        print(f"  Setting to 7.5% (90 degrees)...")
        pwm.ChangeDutyCycle(7.5)
        time.sleep(2)
        
        print(f"  Setting to 2.5% (0 degrees)...")
        pwm.ChangeDutyCycle(2.5)
        time.sleep(2)
        
        print(f"  Setting to 12.5% (180 degrees)...")
        pwm.ChangeDutyCycle(12.5)
        time.sleep(2)
        
        print(f"  Returning to 0%...")
        pwm.ChangeDutyCycle(0)
        time.sleep(1)
        
        pwm.stop()
        GPIO.cleanup(pin_num)
        
        print(f"  ✅ {pin_name} PWM test complete!")
        return True
        
    except Exception as e:
        print(f"  ❌ {pin_name} PWM test FAILED: {e}")
        try:
            pwm.stop()
            GPIO.cleanup(pin_num)
        except:
            pass
        return False

def check_system_config():
    """Check system-level configurations"""
    print("="*60)
    print("SYSTEM CONFIGURATION CHECK")
    print("="*60)
    
    import os
    import subprocess
    
    # Check if running as root
    if os.geteuid() != 0:
        print("⚠️  WARNING: Not running as root (sudo)")
        print("   Servos may not work without root privileges!")
    else:
        print("✅ Running as root (sudo)")
    
    # Check GPIO permissions
    try:
        with open('/sys/class/gpio/export', 'w') as f:
            pass
        print("✅ GPIO access available")
    except PermissionError:
        print("❌ GPIO access DENIED - need sudo!")
    except:
        print("⚠️  Cannot check GPIO permissions")
    
    # Check if pins are already exported
    print("\nChecking if pins are already in use...")
    for pin in [PLASTIC_PIN, PAPER_PIN]:
        gpio_path = f"/sys/class/gpio/gpio{pin}"
        if os.path.exists(gpio_path):
            print(f"  ⚠️  GPIO {pin} is already exported!")
        else:
            print(f"  ✅ GPIO {pin} is available")
    
    print()

def main():
    print("="*60)
    print("SERVO DIAGNOSTIC TOOL")
    print("="*60)
    print("\nThis will check:")
    print("  1. GPIO pin states")
    print("  2. PWM creation capability")
    print("  3. System permissions")
    print("  4. Raw PWM signal generation")
    print()
    
    input("Press ENTER to start diagnostics...")
    
    try:
        # System check
        check_system_config()
        
        # GPIO state check
        check_gpio_state()
        
        # PWM creation test
        pwm_results = test_pwm_creation()
        
        # Raw PWM test
        print("="*60)
        print("RAW PWM SIGNAL TEST")
        print("="*60)
        print("\n⚠️  IMPORTANT: Watch your servos!")
        print("   They should move if wiring is correct.\n")
        
        input("Press ENTER to test Plastic Servo (GPIO 18)...")
        plastic_ok = test_raw_pwm(PLASTIC_PIN, "Plastic Servo")
        
        time.sleep(1)
        
        input("Press ENTER to test Paper Servo (GPIO 13)...")
        paper_ok = test_raw_pwm(PAPER_PIN, "Paper Servo")
        
        # Summary
        print("\n" + "="*60)
        print("DIAGNOSTIC SUMMARY")
        print("="*60)
        print(f"Plastic Servo (GPIO 18): {'✅ OK' if plastic_ok else '❌ FAILED'}")
        print(f"Paper Servo (GPIO 13):   {'✅ OK' if paper_ok else '❌ FAILED'}")
        print()
        print("If both show ❌ FAILED:")
        print("  1. Check wiring connections")
        print("  2. Check external 5V power supply")
        print("  3. Check GND connection to Pi Pin 14")
        print("  4. Try different GPIO pins")
        print("="*60)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Diagnostics interrupted")
        try:
            GPIO.cleanup()
        except:
            pass
    except Exception as e:
        print(f"\n❌ Diagnostic error: {e}")
        import traceback
        traceback.print_exc()
        try:
            GPIO.cleanup()
        except:
            pass

if __name__ == "__main__":
    main()

