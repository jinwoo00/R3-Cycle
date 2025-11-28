#!/usr/bin/env python3
"""
Test script for LCD "Paper Detected!" Message
Directly tests the LCD message when IR sensor detects paper

Usage: sudo python3 tests/test_lcd_paper_detected.py
"""

import sys
import time

# Add parent directory to path
sys.path.append('/home/r3cycle/r3cycle')

try:
    from RPLCD.i2c import CharLCD
    import RPi.GPIO as GPIO
    import config
except ImportError as e:
    print(f"[ERROR] Missing library: {e}")
    print("Run: sudo pip3 install --break-system-packages RPLCD RPi.GPIO")
    sys.exit(1)

def test_lcd_paper_detected():
    """Test LCD 'Paper Detected!' message with IR sensor"""
    print("=" * 50)
    print("R3-Cycle LCD Paper Detected Test")
    print("=" * 50)
    print()
    print(f"IR Sensor Pin: GPIO {config.PIN_IR_SENSOR}")
    print(f"LCD I2C Address: {hex(config.LCD_I2C_ADDRESS)}")
    print()
    print("Instructions:")
    print("  1. Remove any paper/object from IR sensor")
    print("  2. Press Enter when ready to start monitoring...")
    input()
    print()
    
    lcd = None
    
    try:
        # Initialize GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(config.PIN_IR_SENSOR, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        
        # Initialize LCD
        print("[1] Initializing LCD...")
        lcd = CharLCD(
            i2c_expander='PCF8574',
            address=config.LCD_I2C_ADDRESS,
            port=1,
            cols=config.LCD_COLS,
            rows=config.LCD_ROWS
        )
        lcd.clear()
        print("[OK] LCD initialized")
        print()
        
        # Display initial message
        print("[2] Displaying initial message...")
        lcd.cursor_pos = (0, 0)
        lcd.write_string("Waiting for")
        lcd.cursor_pos = (1, 0)
        lcd.write_string("paper...")
        print("    LCD: 'Waiting for' / 'paper...'")
        print()
        
        # Monitor IR sensor
        print("[3] Monitoring IR sensor...")
        print("    Insert paper/object to test detection")
        print("    (Press Ctrl+C to exit)")
        print()
        
        last_state = None
        detection_count = 0
        
        while True:
            # Read IR sensor (LOW = detected, HIGH = no object)
            raw_value = GPIO.input(config.PIN_IR_SENSOR)
            detected = (raw_value == GPIO.LOW)
            
            # Only update if state changed
            if detected != last_state:
                if detected:
                    detection_count += 1
                    print(f"[DETECTION #{detection_count}] Paper detected!")
                    print(f"    GPIO {config.PIN_IR_SENSOR}: {raw_value} (LOW = detected)")
                    print()
                    
                    # Show "Paper Detected!" message on LCD
                    lcd.clear()
                    lcd.cursor_pos = (0, 0)
                    lcd.write_string(config.LCD_MSG_PAPER_DETECTED[0])
                    lcd.cursor_pos = (1, 0)
                    lcd.write_string(config.LCD_MSG_PAPER_DETECTED[1])
                    print(f"    LCD: '{config.LCD_MSG_PAPER_DETECTED[0]}' / '{config.LCD_MSG_PAPER_DETECTED[1]}'")
                    print()
                else:
                    print("[CLEARED] No paper detected")
                    print()
                    
                    # Show waiting message
                    lcd.clear()
                    lcd.cursor_pos = (0, 0)
                    lcd.write_string("Waiting for")
                    lcd.cursor_pos = (1, 0)
                    lcd.write_string("paper...")
                    print("    LCD: 'Waiting for' / 'paper...'")
                    print()
                
                last_state = detected
            
            time.sleep(0.1)  # Check every 100ms
            
    except KeyboardInterrupt:
        print("\n\n[STOPPED] Test interrupted by user")
        print(f"Total detections: {detection_count}")
        
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        if lcd:
            print("\n[CLEANUP] Clearing LCD...")
            lcd.clear()
            lcd.cursor_pos = (0, 0)
            lcd.write_string("Test Complete")
            time.sleep(1)
            lcd.clear()
        GPIO.cleanup()
        print("[OK] Cleanup complete")
        
    return True

if __name__ == "__main__":
    success = test_lcd_paper_detected()
    sys.exit(0 if success else 1)

