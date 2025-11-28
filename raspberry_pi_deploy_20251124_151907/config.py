"""
R3-Cycle Raspberry Pi Configuration
Central configuration file for all hardware pins, API settings, and thresholds

Author: R3-Cycle Team
Last Updated: 2025-11-21
"""

# ============================================
# API CONFIGURATION
# ============================================

# Backend server URL (change to your actual server IP/domain)
API_BASE_URL = "http://192.168.1.100:3000/api"  # TODO: Update with your server IP

# Machine authentication credentials
MACHINE_ID = "RPI_001"
MACHINE_SECRET = "test-secret"  # TODO: Change in production

# API request timeout (seconds)
API_TIMEOUT = 10

# ============================================
# GPIO PIN ASSIGNMENTS
# ============================================
# All pin numbers use BCM (Broadcom) numbering

# RFID Reader (RC522) - SPI Interface
PIN_RFID_RST = 25       # Reset pin
# SPI pins are handled by spidev library:
#   MOSI = GPIO 10
#   MISO = GPIO 9
#   SCLK = GPIO 11
#   CE0  = GPIO 8

# Load Cell (HX711)
PIN_LOAD_CELL_DT = 5    # Data pin
PIN_LOAD_CELL_SCK = 6   # Clock pin

# IR Obstacle Sensor
PIN_IR_SENSOR = 27      # Digital output (HIGH when paper detected) - Pin 13

# Inductive Proximity Sensor (Metal Detection) - LJ12A3 via Logic Level Converter
PIN_INDUCTIVE_SENSOR = 17  # Digital output (HIGH when metal detected) - Pin 11 (via LLC HV1→LV1)

# Servo Motors (PWM-capable pins)
PIN_SERVO_COLLECTION = 18   # Servo #1 - Paper collection mechanism
PIN_SERVO_REWARD = 23       # Servo #2 - Reward dispenser

# LED Indicators
PIN_LED_RED = 22        # Error/rejection indicator - Pin 15 (using GPIO22, not GPIO27 to avoid conflict with IR sensor)
# Note: GPIO27 is also an option, but GPIO22 is recommended to avoid conflict with IR sensor on GPIO27

# LCD Display (I2C)
# SDA = GPIO 2 (handled by I2C library) - Pin 3
# SCL = GPIO 3 (handled by I2C library) - Pin 5
LCD_I2C_ADDRESS = 0x27  # Common I2C address for LCD modules
LCD_COLS = 16           # 16 columns
LCD_ROWS = 2            # 2 rows

# TTL USB-to-Serial Converter (Optional - for debugging)
# TXD = GPIO 14 (Pin 8) - TTL TX → Pi RX
# RXD = GPIO 15 (Pin 10) - TTL RX → Pi TX
# Note: This is optional and used for serial communication/debugging

# ============================================
# WEIGHT SENSOR CALIBRATION
# ============================================

# HX711 Load Cell Configuration
LOAD_CELL_REFERENCE_UNIT = 1  # Calibration factor (adjust after calibration)
# To calibrate:
# 1. Run test_loadcell.py with no weight → record raw value
# 2. Place known weight (e.g., 100g) on sensor → record raw value
# 3. Calculate: REFERENCE_UNIT = (raw_with_weight - raw_zero) / known_weight

# Weight thresholds (grams)
MIN_WEIGHT = 1.0        # Minimum valid paper weight
MAX_WEIGHT = 20.0       # Maximum valid paper weight

# Load cell settling time (seconds)
LOAD_CELL_SETTLE_TIME = 2.0  # Wait for weight to stabilize

# ============================================
# TIMING CONFIGURATION
# ============================================

# Machine heartbeat interval (seconds)
HEARTBEAT_INTERVAL = 60  # Send status update every 60 seconds

# Redemption polling interval (seconds)
REDEMPTION_POLL_INTERVAL = 5  # Check for pending redemptions every 5 seconds

# RFID scan timeout (seconds)
RFID_TIMEOUT = 30       # Maximum time to wait for RFID card

# Transaction timeout (seconds)
TRANSACTION_TIMEOUT = 60  # Maximum time for complete transaction flow

# Sensor read retry attempts
SENSOR_RETRY_ATTEMPTS = 3

# ============================================
# SERVO MOTOR CONFIGURATION
# ============================================

# Servo PWM frequency (Hz)
SERVO_FREQUENCY = 50    # Standard servo frequency

# Servo positions (degrees, 0-180)
# Paper collection servo
SERVO_COLLECTION_IDLE = 0
SERVO_COLLECTION_COLLECT = 90

# Reward dispenser servo
SERVO_REWARD_IDLE = 0
SERVO_REWARD_DISPENSE = 90

# Servo movement timing (seconds)
SERVO_MOVE_DURATION = 1.0    # Time to hold servo at target position
SERVO_RETURN_DURATION = 0.5  # Time to return to idle

# ============================================
# LCD DISPLAY MESSAGES
# ============================================

LCD_MSG_WELCOME = [
    "R3-Cycle Ready",
    "Scan RFID Card"
]

LCD_MSG_RFID_DETECTED = [
    "Card Detected",
    "Verifying..."
]

LCD_MSG_USER_VERIFIED = [
    "Hello {name}!",
    "Insert paper"
]

LCD_MSG_WEIGHING = [
    "Weighing paper",
    "Please wait..."
]

LCD_MSG_METAL_DETECTED = [
    "Metal Detected!",
    "Remove staples"
]

LCD_MSG_WEIGHT_INVALID = [
    "Invalid Weight",
    "{weight}g not 1-20g"
]

LCD_MSG_SUCCESS = [
    "Success! +{points}",
    "Total: {total}pts"
]

LCD_MSG_REJECTED = [
    "Transaction",
    "Rejected"
]

LCD_MSG_ERROR = [
    "System Error",
    "Try again later"
]

LCD_MSG_DISPENSING = [
    "Dispensing",
    "Reward..."
]

LCD_MSG_OFFLINE = [
    "Offline Mode",
    "Working locally"
]

# ============================================
# SENSOR HEALTH MONITORING
# ============================================

# Sensor status codes
SENSOR_OK = "ok"
SENSOR_ERROR = "error"

# Sensor health check interval (seconds)
SENSOR_HEALTH_CHECK_INTERVAL = 300  # Check sensors every 5 minutes

# ============================================
# BOND PAPER STOCK TRACKING
# ============================================

# Bond paper capacity (number of sheets)
BOND_PAPER_CAPACITY = 100

# Initial stock level (sheets)
BOND_PAPER_INITIAL_STOCK = 100

# Stock alert thresholds (percentage)
STOCK_CRITICAL_THRESHOLD = 20  # Alert when below 20%
STOCK_WARNING_THRESHOLD = 50   # Warning when below 50%

# ============================================
# LOGGING CONFIGURATION
# ============================================

# Log file path
LOG_FILE = "/home/pi/r3cycle/r3cycle.log"

# Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_LEVEL = "INFO"

# Log format
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Maximum log file size (bytes)
LOG_MAX_SIZE = 10 * 1024 * 1024  # 10 MB

# Number of backup log files to keep
LOG_BACKUP_COUNT = 5

# ============================================
# DEVELOPMENT/DEBUG SETTINGS
# ============================================

# Enable debug mode (more verbose logging, simulated sensors)
DEBUG_MODE = False

# Simulate sensors (for testing without hardware)
SIMULATE_RFID = False
SIMULATE_LOAD_CELL = False
SIMULATE_IR_SENSOR = False
SIMULATE_INDUCTIVE_SENSOR = False

# Skip hardware initialization (for code testing on non-Pi systems)
SKIP_GPIO_INIT = False

# ============================================
# OFFLINE MODE (PHASE 5 - IMPLEMENTED!)
# ============================================

# Enable offline mode with SQLite
OFFLINE_MODE_ENABLED = True

# SQLite database path
SQLITE_DB_PATH = "/home/pi/r3cycle/offline.db"

# Sync interval when online (seconds)
SYNC_INTERVAL = 300  # Sync every 5 minutes

# Maximum offline transactions to queue
MAX_OFFLINE_TRANSACTIONS = 1000

# Network health check interval (seconds)
NETWORK_CHECK_INTERVAL = 30  # Check connectivity every 30 seconds

# Network timeout for health checks (seconds)
NETWORK_CHECK_TIMEOUT = 5

# Maximum sync retry attempts for failed transactions
MAX_SYNC_RETRIES = 3

# Sync retry delay (seconds)
SYNC_RETRY_DELAY = 60  # Wait 1 minute before retrying failed sync

# User cache expiry (seconds)
USER_CACHE_EXPIRY = 86400  # 24 hours

# Sync on startup
SYNC_ON_STARTUP = True

# ============================================
# REAL-TIME WEBSOCKET CONFIGURATION
# ============================================

# Enable real-time WebSocket streaming
REALTIME_ENABLED = True  # Set to False to disable real-time features

# Real-time streaming interval (seconds)
REALTIME_STREAM_INTERVAL = 2.0  # Stream sensor data every 2 seconds

# ============================================
# HARDWARE VALIDATION
# ============================================

def validate_config():
    """
    Validate configuration values before startup
    Raises ValueError if any critical settings are invalid
    """
    errors = []

    # Validate API URL
    if not API_BASE_URL or API_BASE_URL == "http://192.168.1.100:3000/api":
        errors.append("WARNING: API_BASE_URL not configured - update with your server IP")

    # Validate weight thresholds
    if MIN_WEIGHT >= MAX_WEIGHT:
        errors.append("MIN_WEIGHT must be less than MAX_WEIGHT")

    if MIN_WEIGHT < 0 or MAX_WEIGHT < 0:
        errors.append("Weight thresholds must be positive")

    # Validate GPIO pins (must be unique)
    gpio_pins = [
        PIN_RFID_RST, PIN_LOAD_CELL_DT, PIN_LOAD_CELL_SCK,
        PIN_IR_SENSOR, PIN_INDUCTIVE_SENSOR,
        PIN_SERVO_COLLECTION, PIN_SERVO_REWARD, PIN_LED_RED
    ]

    if len(gpio_pins) != len(set(gpio_pins)):
        errors.append("GPIO pin conflict detected - pins must be unique")

    # Validate servo positions
    if not (0 <= SERVO_COLLECTION_IDLE <= 180):
        errors.append("SERVO_COLLECTION_IDLE must be 0-180 degrees")

    if not (0 <= SERVO_REWARD_IDLE <= 180):
        errors.append("SERVO_REWARD_IDLE must be 0-180 degrees")

    # Print warnings
    for error in errors:
        if error.startswith("WARNING"):
            print(f"[WARNING] {error}")
        else:
            raise ValueError(f"[CONFIG ERROR] {error}")

    print("[CONFIG] Configuration validated successfully")

# Validate on import (unless in debug mode)
if not DEBUG_MODE and not SKIP_GPIO_INIT:
    validate_config()
