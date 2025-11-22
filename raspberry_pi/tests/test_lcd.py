#!/usr/bin/env python3
"""
Test script for LCD I2C Display
Tests LCD display functionality

Usage: sudo python3 test_lcd.py
"""

import sys
import time

# Add parent directory to path
sys.path.append('/home/pi/r3cycle')

try:
    from RPLCD.i2c import CharLCD
    import config
except ImportError as e:
    print(f"[ERROR] Missing library: {e}")
    print("Run: pip3 install RPLCD")
    sys.exit(1)

def test_lcd():
    """Test LCD display"""
    print("=" * 50)
    print("R3-Cycle LCD I2C Display Test")
    print("=" * 50)
    print()

    lcd = None

    try:
        # Initialize LCD
        print("[1] Initializing LCD...")
        print(f"    I2C Address: {hex(config.LCD_I2C_ADDRESS)}")
        print(f"    Dimensions:  {config.LCD_COLS}x{config.LCD_ROWS}")

        lcd = CharLCD(
            i2c_expander='PCF8574',
            address=config.LCD_I2C_ADDRESS,
            port=1,
            cols=config.LCD_COLS,
            rows=config.LCD_ROWS
        )

        lcd.clear()
        print("[OK] LCD initialized successfully")
        print()

        # Test 1: Simple text
        print("[2] Test 1: Simple Text Display")
        lcd.cursor_pos = (0, 0)
        lcd.write_string("R3-Cycle Test")
        lcd.cursor_pos = (1, 0)
        lcd.write_string("LCD Working!")

        print("    Display: 'R3-Cycle Test' / 'LCD Working!'")
        time.sleep(3)

        # Test 2: Clear and rewrite
        print("[3] Test 2: Clear and Rewrite")
        lcd.clear()
        lcd.write_string("Clearing...")
        time.sleep(1)
        lcd.clear()
        lcd.write_string("Cleared!")
        print("    Display: 'Cleared!'")
        time.sleep(2)

        # Test 3: All welcome messages
        print("[4] Test 3: Welcome Messages")
        test_messages = [
            config.LCD_MSG_WELCOME,
            config.LCD_MSG_RFID_DETECTED,
            ["Hello User!", "Insert paper"],
            config.LCD_MSG_WEIGHING,
            config.LCD_MSG_METAL_DETECTED,
            config.LCD_MSG_SUCCESS,
            config.LCD_MSG_ERROR
        ]

        for msg in test_messages:
            lcd.clear()
            lcd.cursor_pos = (0, 0)
            line1 = msg[0].replace("{name}", "User").replace("{points}", "5").replace("{total}", "25")
            lcd.write_string(line1[:config.LCD_COLS])

            if len(msg) > 1:
                lcd.cursor_pos = (1, 0)
                line2 = msg[1].replace("{weight}", "5.2")
                lcd.write_string(line2[:config.LCD_COLS])

            print(f"    Display: '{line1}' / '{msg[1] if len(msg) > 1 else ''}'")
            time.sleep(2)

        # Test 4: Character positions
        print("[5] Test 4: Character Positions")
        lcd.clear()

        # Fill with numbers
        for row in range(config.LCD_ROWS):
            for col in range(config.LCD_COLS):
                lcd.cursor_pos = (row, col)
                lcd.write_string(str(col % 10))

        print(f"    Display: Position grid (0-9 repeated)")
        time.sleep(3)

        # Final message
        lcd.clear()
        lcd.write_string("Test Complete!")
        lcd.cursor_pos = (1, 0)
        lcd.write_string("LCD OK!")
        print("\n[SUCCESS] All LCD tests passed!")
        time.sleep(2)

    except Exception as e:
        print(f"[ERROR] LCD test failed: {e}")
        print()
        print("Troubleshooting:")
        print("  1. Check I2C is enabled: sudo raspi-config")
        print("  2. Scan I2C devices: sudo i2cdetect -y 1")
        print(f"  3. Verify LCD address matches: {hex(config.LCD_I2C_ADDRESS)}")
        print("  4. Check wiring: SDA=GPIO2, SCL=GPIO3")
        return False

    finally:
        if lcd:
            print("\n[CLEANUP] Clearing LCD...")
            lcd.clear()

        print("[DONE] Test complete")

    return True

if __name__ == "__main__":
    success = test_lcd()
    sys.exit(0 if success else 1)
