#!/bin/bash
# System PWM Configuration Check

echo "=========================================="
echo "RASPBERRY PI PWM SYSTEM CHECK"
echo "=========================================="
echo ""

echo "1. Checking if running as root..."
if [ "$EUID" -eq 0 ]; then 
    echo "   ✅ Running as root"
else 
    echo "   ❌ NOT running as root (servos need sudo!)"
fi
echo ""

echo "2. Checking GPIO access..."
if [ -w /sys/class/gpio/export ]; then
    echo "   ✅ GPIO access OK"
else
    echo "   ❌ GPIO access DENIED (need sudo!)"
fi
echo ""

echo "3. Checking if GPIO pins are already in use..."
for pin in 18 13; do
    if [ -d "/sys/class/gpio/gpio${pin}" ]; then
        echo "   ⚠️  GPIO ${pin} is already exported!"
    else
        echo "   ✅ GPIO ${pin} is available"
    fi
done
echo ""

echo "4. Checking PWM kernel modules..."
if lsmod | grep -q pwm; then
    echo "   ✅ PWM modules loaded"
    lsmod | grep pwm
else
    echo "   ⚠️  No PWM kernel modules found (software PWM should still work)"
fi
echo ""

echo "5. Checking /boot/config.txt for PWM settings..."
if [ -f /boot/config.txt ]; then
    if grep -q "dtoverlay=pwm" /boot/config.txt; then
        echo "   ✅ PWM overlay configured"
        grep "dtoverlay=pwm" /boot/config.txt
    else
        echo "   ⚠️  No PWM overlay in config.txt (software PWM should still work)"
    fi
else
    echo "   ❌ Cannot find /boot/config.txt"
fi
echo ""

echo "6. Checking Python GPIO library..."
python3 -c "import RPi.GPIO; print('   ✅ RPi.GPIO library available')" 2>/dev/null || echo "   ❌ RPi.GPIO library NOT available!"
echo ""

echo "=========================================="
echo "RECOMMENDATIONS:"
echo "=========================================="
echo "If servos don't work:"
echo "  1. Run test with: sudo python3 test_servo.py"
echo "  2. Check external 5V power supply is ON"
echo "  3. Check GND connection to Pi Pin 14"
echo "  4. Verify wiring connections"
echo "=========================================="

