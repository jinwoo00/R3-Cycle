#!/usr/bin/env python3
"""
R3-Cycle Main Program for Raspberry Pi Zero 2 W
Complete sensor integration and transaction processing

This script handles:
- RFID card scanning (RC522)
- Paper weight measurement (HX711 load cell)
- Metal detection (inductive proximity sensor)
- Paper insertion detection (IR sensor)
- User feedback (LCD display + LED)
- API communication with backend server
- Machine heartbeat monitoring
- Redemption dispensing (integrated separately)

Author: R3-Cycle Team
Last Updated: 2025-11-21
"""

import sys
import time
import logging
import threading
from datetime import datetime
from enum import Enum

# Import configuration
import config

# Import offline mode modules (if enabled)
if config.OFFLINE_MODE_ENABLED:
    from database import DatabaseManager
    from sync import SyncManager
    import setup_db

# Hardware libraries
try:
    import RPi.GPIO as GPIO
    from mfrc522 import SimpleMFRC522
    from hx711 import HX711
    from RPLCD.i2c import CharLCD
    import requests
except ImportError as e:
    print(f"[ERROR] Missing required library: {e}")
    print("Run install.sh to install dependencies")
    sys.exit(1)

# ============================================
# LOGGING SETUP
# ============================================

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format=config.LOG_FORMAT,
    handlers=[
        logging.FileHandler(config.LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# ============================================
# TRANSACTION STATE MACHINE
# ============================================

class TransactionState(Enum):
    """States for the transaction flow"""
    IDLE = "idle"
    WAITING_FOR_RFID = "waiting_for_rfid"
    VERIFYING_USER = "verifying_user"
    WAITING_FOR_PAPER = "waiting_for_paper"
    WEIGHING = "weighing"
    CHECKING_METAL = "checking_metal"
    SUBMITTING = "submitting"
    SUCCESS = "success"
    REJECTED = "rejected"
    ERROR = "error"

# ============================================
# HARDWARE MANAGER CLASS
# ============================================

class HardwareManager:
    """Manages all hardware sensors and actuators"""

    def __init__(self):
        """Initialize all hardware components"""
        logger.info("Initializing hardware...")

        self.initialized = False
        self.lcd = None
        self.rfid_reader = None
        self.load_cell = None

        try:
            # Setup GPIO mode
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)

            # Initialize LCD display
            self._init_lcd()

            # Initialize RFID reader
            self._init_rfid()

            # Initialize load cell
            self._init_load_cell()

            # Initialize IR sensor
            self._init_ir_sensor()

            # Initialize inductive sensor
            self._init_inductive_sensor()

            # Initialize LED
            self._init_led()

            # Initialize servos (optional for main flow, used in redemption)
            self._init_servos()

            self.initialized = True
            logger.info("Hardware initialization complete")

        except Exception as e:
            logger.error(f"Hardware initialization failed: {e}")
            raise

    def _init_lcd(self):
        """Initialize LCD I2C display"""
        try:
            self.lcd = CharLCD(
                i2c_expander='PCF8574',
                address=config.LCD_I2C_ADDRESS,
                port=1,  # I2C port (1 for Raspberry Pi)
                cols=config.LCD_COLS,
                rows=config.LCD_ROWS
            )
            self.lcd.clear()
            logger.info(f"LCD initialized at address {hex(config.LCD_I2C_ADDRESS)}")
        except Exception as e:
            logger.error(f"LCD initialization failed: {e}")
            self.lcd = None

    def _init_rfid(self):
        """Initialize RC522 RFID reader"""
        try:
            self.rfid_reader = SimpleMFRC522()
            logger.info("RFID reader initialized")
        except Exception as e:
            logger.error(f"RFID initialization failed: {e}")
            self.rfid_reader = None

    def _init_load_cell(self):
        """Initialize HX711 load cell"""
        try:
            self.load_cell = HX711(
                dout_pin=config.PIN_LOAD_CELL_DT,
                pd_sck_pin=config.PIN_LOAD_CELL_SCK
            )
            self.load_cell.set_reference_unit(config.LOAD_CELL_REFERENCE_UNIT)
            self.load_cell.reset()
            self.load_cell.tare()  # Zero the scale
            logger.info("Load cell initialized and tared")
        except Exception as e:
            logger.error(f"Load cell initialization failed: {e}")
            self.load_cell = None

    def _init_ir_sensor(self):
        """Initialize IR obstacle sensor"""
        try:
            GPIO.setup(config.PIN_IR_SENSOR, GPIO.IN)
            logger.info(f"IR sensor initialized on GPIO {config.PIN_IR_SENSOR}")
        except Exception as e:
            logger.error(f"IR sensor initialization failed: {e}")

    def _init_inductive_sensor(self):
        """Initialize inductive proximity sensor"""
        try:
            GPIO.setup(config.PIN_INDUCTIVE_SENSOR, GPIO.IN)
            logger.info(f"Inductive sensor initialized on GPIO {config.PIN_INDUCTIVE_SENSOR}")
        except Exception as e:
            logger.error(f"Inductive sensor initialization failed: {e}")

    def _init_led(self):
        """Initialize LED indicator"""
        try:
            GPIO.setup(config.PIN_LED_RED, GPIO.OUT)
            GPIO.output(config.PIN_LED_RED, GPIO.LOW)
            logger.info(f"LED initialized on GPIO {config.PIN_LED_RED}")
        except Exception as e:
            logger.error(f"LED initialization failed: {e}")

    def _init_servos(self):
        """Initialize servo motors (PWM)"""
        try:
            GPIO.setup(config.PIN_SERVO_COLLECTION, GPIO.OUT)
            GPIO.setup(config.PIN_SERVO_REWARD, GPIO.OUT)
            logger.info("Servo motors initialized")
        except Exception as e:
            logger.error(f"Servo initialization failed: {e}")

    # ========================================
    # LCD DISPLAY METHODS
    # ========================================

    def lcd_display(self, line1, line2=""):
        """Display message on LCD"""
        if not self.lcd:
            logger.warning("LCD not available")
            return

        try:
            self.lcd.clear()
            self.lcd.cursor_pos = (0, 0)
            self.lcd.write_string(line1[:config.LCD_COLS])

            if line2:
                self.lcd.cursor_pos = (1, 0)
                self.lcd.write_string(line2[:config.LCD_COLS])

            logger.debug(f"LCD: {line1} | {line2}")
        except Exception as e:
            logger.error(f"LCD display error: {e}")

    def lcd_welcome(self):
        """Display welcome message"""
        self.lcd_display(*config.LCD_MSG_WELCOME)

    def lcd_rfid_detected(self):
        """Display RFID detected message"""
        self.lcd_display(*config.LCD_MSG_RFID_DETECTED)

    def lcd_user_verified(self, name):
        """Display user verified message"""
        msg = config.LCD_MSG_USER_VERIFIED.copy()
        msg[0] = msg[0].format(name=name[:12])  # Truncate long names
        self.lcd_display(*msg)

    def lcd_weighing(self):
        """Display weighing message"""
        self.lcd_display(*config.LCD_MSG_WEIGHING)

    def lcd_metal_detected(self):
        """Display metal detected message"""
        self.lcd_display(*config.LCD_MSG_METAL_DETECTED)

    def lcd_weight_invalid(self, weight):
        """Display invalid weight message"""
        msg = config.LCD_MSG_WEIGHT_INVALID.copy()
        msg[1] = msg[1].format(weight=weight)
        self.lcd_display(*msg)

    def lcd_success(self, points, total):
        """Display success message"""
        msg = config.LCD_MSG_SUCCESS.copy()
        msg[0] = msg[0].format(points=points)
        msg[1] = msg[1].format(total=total)
        self.lcd_display(*msg)

    def lcd_rejected(self):
        """Display rejected message"""
        self.lcd_display(*config.LCD_MSG_REJECTED)

    def lcd_error(self):
        """Display error message"""
        self.lcd_display(*config.LCD_MSG_ERROR)

    # ========================================
    # SENSOR READING METHODS
    # ========================================

    def read_rfid(self, timeout=None):
        """
        Read RFID card
        Returns: (tag_id, tag_text) or (None, None) if timeout/error
        """
        if not self.rfid_reader:
            logger.error("RFID reader not available")
            return None, None

        timeout = timeout or config.RFID_TIMEOUT
        logger.info(f"Waiting for RFID card (timeout: {timeout}s)...")

        try:
            # SimpleMFRC522.read() blocks until card detected
            # We'll use a threading timeout
            result = [None, None]

            def read_card():
                try:
                    tag_id, tag_text = self.rfid_reader.read()
                    result[0] = str(tag_id)
                    result[1] = tag_text
                except Exception as e:
                    logger.error(f"RFID read error: {e}")

            read_thread = threading.Thread(target=read_card)
            read_thread.daemon = True
            read_thread.start()
            read_thread.join(timeout)

            if result[0]:
                logger.info(f"RFID card detected: {result[0]}")
                return result[0], result[1]
            else:
                logger.warning("RFID read timeout")
                return None, None

        except Exception as e:
            logger.error(f"RFID read exception: {e}")
            return None, None

    def read_weight(self):
        """
        Read weight from load cell
        Returns: weight in grams (float) or None if error
        """
        if not self.load_cell:
            logger.error("Load cell not available")
            return None

        try:
            # Take multiple readings and average
            readings = []
            for _ in range(5):
                val = self.load_cell.get_weight(5)  # Average of 5 raw readings
                readings.append(val)
                time.sleep(0.1)

            weight = sum(readings) / len(readings)
            logger.info(f"Weight measured: {weight:.2f}g")
            return round(weight, 2)

        except Exception as e:
            logger.error(f"Load cell read error: {e}")
            return None

    def check_paper_inserted(self):
        """
        Check if paper is inserted (IR sensor)
        Returns: True if paper detected, False otherwise
        """
        try:
            # IR sensor outputs HIGH when object detected
            detected = GPIO.input(config.PIN_IR_SENSOR) == GPIO.HIGH
            logger.debug(f"IR sensor: {'DETECTED' if detected else 'NO PAPER'}")
            return detected
        except Exception as e:
            logger.error(f"IR sensor read error: {e}")
            return False

    def check_metal_detected(self):
        """
        Check if metal is detected (inductive sensor)
        Returns: True if metal detected, False otherwise
        """
        try:
            # Inductive sensor outputs HIGH when metal detected
            detected = GPIO.input(config.PIN_INDUCTIVE_SENSOR) == GPIO.HIGH
            logger.debug(f"Inductive sensor: {'METAL DETECTED' if detected else 'NO METAL'}")
            return detected
        except Exception as e:
            logger.error(f"Inductive sensor read error: {e}")
            return False

    # ========================================
    # LED CONTROL METHODS
    # ========================================

    def led_on(self):
        """Turn on red LED (error indicator)"""
        try:
            GPIO.output(config.PIN_LED_RED, GPIO.HIGH)
        except Exception as e:
            logger.error(f"LED control error: {e}")

    def led_off(self):
        """Turn off red LED"""
        try:
            GPIO.output(config.PIN_LED_RED, GPIO.LOW)
        except Exception as e:
            logger.error(f"LED control error: {e}")

    def led_blink(self, times=3, duration=0.5):
        """Blink LED"""
        for _ in range(times):
            self.led_on()
            time.sleep(duration)
            self.led_off()
            time.sleep(duration)

    # ========================================
    # SENSOR HEALTH CHECK
    # ========================================

    def check_sensor_health(self):
        """
        Check health status of all sensors
        Returns: dict with sensor statuses
        """
        health = {
            "rfid": config.SENSOR_OK if self.rfid_reader else config.SENSOR_ERROR,
            "loadCell": config.SENSOR_OK if self.load_cell else config.SENSOR_ERROR,
            "inductiveSensor": config.SENSOR_OK,  # Assume OK if GPIO works
            "irSensor": config.SENSOR_OK,
            "servo": config.SENSOR_OK
        }

        # Test load cell with a dummy reading
        if self.load_cell:
            try:
                self.load_cell.get_weight(1)
            except:
                health["loadCell"] = config.SENSOR_ERROR

        logger.debug(f"Sensor health: {health}")
        return health

    def cleanup(self):
        """Cleanup GPIO and hardware resources"""
        logger.info("Cleaning up hardware...")
        try:
            if self.lcd:
                self.lcd.clear()
                self.lcd_display("System", "Shutting down...")
            GPIO.cleanup()
        except Exception as e:
            logger.error(f"Cleanup error: {e}")

# ============================================
# API COMMUNICATION CLASS
# ============================================

class APIClient:
    """Handles all communication with backend API"""

    def __init__(self):
        """Initialize API client"""
        self.base_url = config.API_BASE_URL
        self.headers = {
            "Content-Type": "application/json",
            "X-Machine-ID": config.MACHINE_ID,
            "X-Machine-Secret": config.MACHINE_SECRET
        }
        logger.info(f"API client initialized for {self.base_url}")

    def _make_request(self, method, endpoint, data=None):
        """
        Make HTTP request to API
        Returns: (success, response_data)
        """
        url = f"{self.base_url}/{endpoint}"

        try:
            if method == "GET":
                response = requests.get(url, headers=self.headers, timeout=config.API_TIMEOUT)
            elif method == "POST":
                response = requests.post(url, headers=self.headers, json=data, timeout=config.API_TIMEOUT)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            if response.status_code == 200:
                return True, response.json()
            else:
                logger.error(f"API error {response.status_code}: {response.text}")
                return False, None

        except requests.exceptions.Timeout:
            logger.error(f"API request timeout: {endpoint}")
            return False, None
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            return False, None

    def verify_rfid(self, rfid_tag):
        """
        Verify RFID tag with backend
        Returns: (success, user_data) or (False, None)
        """
        logger.info(f"Verifying RFID: {rfid_tag}")

        success, data = self._make_request("POST", "rfid/verify", {
            "rfidTag": rfid_tag,
            "machineId": config.MACHINE_ID
        })

        if success and data.get("valid"):
            logger.info(f"RFID verified: User {data.get('userName')}")
            return True, data
        else:
            logger.warning(f"RFID verification failed: {data.get('message') if data else 'No response'}")
            return False, None

    def submit_transaction(self, rfid_tag, weight, metal_detected):
        """
        Submit transaction to backend
        Returns: (success, transaction_data)
        """
        logger.info(f"Submitting transaction: {weight}g, metal={metal_detected}")

        success, data = self._make_request("POST", "transaction/submit", {
            "rfidTag": rfid_tag,
            "weight": weight,
            "metalDetected": metal_detected,
            "timestamp": datetime.now().isoformat()
        })

        if success and data.get("success"):
            logger.info(f"Transaction submitted: {data.get('transaction', {}).get('id')}")
            return True, data
        else:
            logger.error(f"Transaction submission failed: {data.get('message') if data else 'No response'}")
            return False, None

    def send_heartbeat(self, bond_paper_stock, sensor_health):
        """
        Send machine heartbeat to backend
        Returns: success (bool)
        """
        logger.debug("Sending heartbeat...")

        success, data = self._make_request("POST", "machine/heartbeat", {
            "machineId": config.MACHINE_ID,
            "status": "online",
            "bondPaperStock": bond_paper_stock,
            "bondPaperCapacity": config.BOND_PAPER_CAPACITY,
            "sensorHealth": sensor_health,
            "timestamp": datetime.now().isoformat()
        })

        if success:
            logger.debug("Heartbeat sent successfully")
            return True
        else:
            logger.warning("Heartbeat failed")
            return False

# ============================================
# MAIN TRANSACTION PROCESSOR
# ============================================

class TransactionProcessor:
    """Manages complete transaction flow"""

    def __init__(self, hardware, api_client, sync_manager=None):
        """Initialize transaction processor"""
        self.hardware = hardware
        self.api = api_client
        self.sync = sync_manager  # Offline mode sync manager (optional)
        self.state = TransactionState.IDLE
        self.bond_paper_stock = config.BOND_PAPER_INITIAL_STOCK

        if self.sync:
            logger.info("Transaction processor initialized with OFFLINE MODE")
        else:
            logger.info("Transaction processor initialized (ONLINE ONLY)")

    def process_transaction(self):
        """
        Main transaction processing loop
        Returns: success (bool)
        """
        try:
            # State 1: Wait for RFID
            self.state = TransactionState.WAITING_FOR_RFID
            self.hardware.lcd_welcome()
            self.hardware.led_off()

            rfid_tag, _ = self.hardware.read_rfid()
            if not rfid_tag:
                logger.info("No RFID detected, returning to idle")
                return False

            # State 2: Verify user
            self.state = TransactionState.VERIFYING_USER
            self.hardware.lcd_rfid_detected()

            # Use sync manager if available (offline mode), otherwise use direct API
            if self.sync:
                valid, user_data = self.sync.smart_verify_user(rfid_tag)
                if not valid:
                    self.hardware.lcd_error()
                    self.hardware.led_blink(2)
                    time.sleep(3)
                    return False
                user_name = user_data.get("name", "User")
                current_points = user_data.get("current_points", 0)
            else:
                success, user_data = self.api.verify_rfid(rfid_tag)
                if not success:
                    self.hardware.lcd_error()
                    self.hardware.led_blink(2)
                    time.sleep(3)
                    return False
                user_name = user_data.get("userName", "User")
                current_points = user_data.get("currentPoints", 0)

            # State 3: Wait for paper insertion
            self.state = TransactionState.WAITING_FOR_PAPER
            self.hardware.lcd_user_verified(user_name)

            logger.info("Waiting for paper insertion...")
            timeout = time.time() + config.TRANSACTION_TIMEOUT
            while not self.hardware.check_paper_inserted():
                if time.time() > timeout:
                    logger.warning("Paper insertion timeout")
                    self.hardware.lcd_display("Timeout", "Try again")
                    time.sleep(2)
                    return False
                time.sleep(0.5)

            logger.info("Paper detected by IR sensor")

            # State 4: Weigh paper
            self.state = TransactionState.WEIGHING
            self.hardware.lcd_weighing()
            time.sleep(config.LOAD_CELL_SETTLE_TIME)  # Let weight stabilize

            weight = self.hardware.read_weight()
            if weight is None:
                self.hardware.lcd_error()
                self.hardware.led_blink(3)
                time.sleep(3)
                return False

            # State 5: Check metal detection
            self.state = TransactionState.CHECKING_METAL
            metal_detected = self.hardware.check_metal_detected()

            if metal_detected:
                self.hardware.lcd_metal_detected()
                self.hardware.led_on()
                time.sleep(4)
                self.hardware.led_off()
                # Still submit but will be rejected by backend
                logger.warning("Metal detected - transaction will be rejected")

            # State 6: Submit transaction to backend
            self.state = TransactionState.SUBMITTING

            # Use sync manager if available (offline mode), otherwise use direct API
            if self.sync:
                accepted, txn_data = self.sync.smart_submit_transaction(rfid_tag, weight, metal_detected)

                if not accepted:
                    self.state = TransactionState.REJECTED
                    reason = txn_data.get("reason", "Unknown reason")
                    logger.warning(f"Transaction rejected: {reason}")

                    if "weight" in reason.lower():
                        self.hardware.lcd_weight_invalid(weight)
                    elif "metal" in reason.lower():
                        self.hardware.lcd_metal_detected()
                    else:
                        self.hardware.lcd_rejected()

                    self.hardware.led_blink(2)
                    time.sleep(4)
                    return False

                # State 7: Success (online or offline)
                self.state = TransactionState.SUCCESS
                points_awarded = txn_data.get("points_earned", 0)

                # Get updated points from cache
                updated_user = self.sync.db.get_user_by_rfid(rfid_tag)
                total_points = updated_user.get("current_points", current_points + points_awarded) if updated_user else current_points + points_awarded

                # Show offline indicator if transaction was queued
                if txn_data.get("offline"):
                    self.hardware.lcd_display(f"Offline: +{points_awarded}", f"Total: {total_points}pts")
                    logger.info(f"Transaction queued offline! +{points_awarded} points")
                else:
                    self.hardware.lcd_success(points_awarded, total_points)
                    logger.info(f"Transaction successful! +{points_awarded} points")

                self.hardware.led_off()
                time.sleep(5)
                return True

            else:
                # Direct API submission (online only mode)
                success, txn_data = self.api.submit_transaction(rfid_tag, weight, metal_detected)

                if not success:
                    self.state = TransactionState.ERROR
                    self.hardware.lcd_error()
                    self.hardware.led_blink(3)
                    time.sleep(3)
                    return False

                # Check if transaction was accepted
                transaction = txn_data.get("transaction", {})
                accepted = txn_data.get("accepted", False)

                if accepted:
                    # State 7: Success
                    self.state = TransactionState.SUCCESS
                    points_awarded = transaction.get("pointsAwarded", 0)
                    total_points = transaction.get("totalPoints", current_points + points_awarded)

                    self.hardware.lcd_success(points_awarded, total_points)
                    self.hardware.led_off()
                    logger.info(f"Transaction successful! +{points_awarded} points")
                    time.sleep(5)
                    return True

                else:
                    # State 8: Rejected
                    self.state = TransactionState.REJECTED
                    reason = txn_data.get("reason", "Unknown reason")
                    logger.warning(f"Transaction rejected: {reason}")

                    if "weight" in reason.lower():
                        self.hardware.lcd_weight_invalid(weight)
                    elif "metal" in reason.lower():
                        self.hardware.lcd_metal_detected()
                    else:
                        self.hardware.lcd_rejected()

                    self.hardware.led_blink(2)
                    time.sleep(4)
                    return False

        except Exception as e:
            logger.error(f"Transaction processing error: {e}")
            self.state = TransactionState.ERROR
            self.hardware.lcd_error()
            self.hardware.led_blink(5)
            time.sleep(3)
            return False

        finally:
            self.state = TransactionState.IDLE

# ============================================
# HEARTBEAT THREAD
# ============================================

class HeartbeatThread(threading.Thread):
    """Background thread for sending heartbeat to backend"""

    def __init__(self, api_client, hardware):
        """Initialize heartbeat thread"""
        super().__init__(daemon=True)
        self.api = api_client
        self.hardware = hardware
        self.running = True
        self.bond_paper_stock = config.BOND_PAPER_INITIAL_STOCK

    def run(self):
        """Run heartbeat loop"""
        logger.info("Heartbeat thread started")

        while self.running:
            try:
                # Get sensor health
                sensor_health = self.hardware.check_sensor_health()

                # Send heartbeat
                self.api.send_heartbeat(self.bond_paper_stock, sensor_health)

                # Sleep for heartbeat interval
                time.sleep(config.HEARTBEAT_INTERVAL)

            except Exception as e:
                logger.error(f"Heartbeat thread error: {e}")
                time.sleep(config.HEARTBEAT_INTERVAL)

    def stop(self):
        """Stop heartbeat thread"""
        logger.info("Stopping heartbeat thread")
        self.running = False

# ============================================
# SYNC THREAD (OFFLINE MODE)
# ============================================

class SyncThread(threading.Thread):
    """Background thread for syncing offline transactions"""

    def __init__(self, sync_manager):
        """Initialize sync thread"""
        super().__init__(daemon=True)
        self.sync = sync_manager
        self.running = True

    def run(self):
        """Run sync loop"""
        logger.info("Sync thread started")

        while self.running:
            try:
                # Wait for sync interval
                time.sleep(config.SYNC_INTERVAL)

                # Only sync if online
                if self.sync.check_network_status():
                    logger.info("Auto-sync triggered")
                    results = self.sync.full_sync()

                    # Log results
                    if results.get('online'):
                        tx_synced = results.get('transactions', {}).get('synced', 0)
                        tx_failed = results.get('transactions', {}).get('failed', 0)
                        logger.info(f"Sync complete: {tx_synced} synced, {tx_failed} failed")
                else:
                    # Check if we have pending transactions
                    pending_count = self.sync.db.get_pending_transactions_count()
                    if pending_count > 0:
                        logger.info(f"Offline - {pending_count} transactions queued")

            except Exception as e:
                logger.error(f"Sync thread error: {e}")

    def stop(self):
        """Stop sync thread"""
        logger.info("Stopping sync thread")
        self.running = False

# ============================================
# MAIN FUNCTION
# ============================================

def main():
    """Main entry point"""
    logger.info("=" * 60)
    logger.info("R3-CYCLE RASPBERRY PI MAIN PROGRAM")
    logger.info("=" * 60)
    logger.info(f"Machine ID: {config.MACHINE_ID}")
    logger.info(f"API URL: {config.API_BASE_URL}")
    logger.info(f"Offline Mode: {'ENABLED' if config.OFFLINE_MODE_ENABLED else 'DISABLED'}")
    logger.info("=" * 60)

    hardware = None
    heartbeat_thread = None
    sync_thread = None
    db_manager = None
    sync_manager = None

    try:
        # Initialize offline mode database (if enabled)
        if config.OFFLINE_MODE_ENABLED:
            logger.info("Initializing offline mode...")

            # Verify/create database
            logger.info(f"Database path: {config.SQLITE_DB_PATH}")
            if not setup_db.verify_database():
                logger.info("Creating new database...")
                setup_db.create_database()

            # Initialize database manager
            db_manager = DatabaseManager()

            # Show database stats
            stats = db_manager.get_database_stats()
            logger.info(f"Database stats: {stats['cached_users']} users, {stats['pending_transactions']} pending tx")

        # Initialize hardware
        hardware = HardwareManager()

        if not hardware.initialized:
            logger.error("Hardware initialization failed - exiting")
            sys.exit(1)

        # Initialize API client
        api_client = APIClient()

        # Initialize sync manager (if offline mode enabled)
        if config.OFFLINE_MODE_ENABLED and db_manager:
            sync_manager = SyncManager(db_manager, api_client)

            # Perform initial sync on startup (if configured)
            if config.SYNC_ON_STARTUP:
                logger.info("Performing initial sync...")
                if sync_manager.check_network_status(force=True):
                    sync_manager.full_sync()
                else:
                    logger.warning("Starting in OFFLINE mode - no network connection")
                    hardware.lcd_offline()
                    time.sleep(3)

        # Start heartbeat thread
        heartbeat_thread = HeartbeatThread(api_client, hardware)
        heartbeat_thread.start()

        # Start sync thread (if offline mode enabled)
        if config.OFFLINE_MODE_ENABLED and sync_manager:
            sync_thread = SyncThread(sync_manager)
            sync_thread.start()

        # Initialize transaction processor (with sync manager if available)
        processor = TransactionProcessor(hardware, api_client, sync_manager)

        # Main loop
        logger.info("System ready - entering main loop")
        hardware.lcd_welcome()

        while True:
            try:
                # Process one transaction
                processor.process_transaction()

                # Small delay before next transaction
                time.sleep(2)

            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received")
                break

            except Exception as e:
                logger.error(f"Main loop error: {e}")
                hardware.lcd_error()
                time.sleep(5)

    except KeyboardInterrupt:
        logger.info("Shutdown requested by user")

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

    finally:
        # Cleanup
        logger.info("Shutting down...")

        if heartbeat_thread:
            heartbeat_thread.stop()
            heartbeat_thread.join(timeout=5)

        if sync_thread:
            sync_thread.stop()
            sync_thread.join(timeout=5)

        if db_manager:
            # Show final stats
            stats = db_manager.get_database_stats()
            logger.info(f"Final database stats: {stats['pending_transactions']} pending transactions")
            db_manager.close()

        if hardware:
            hardware.cleanup()

        logger.info("Shutdown complete")

if __name__ == "__main__":
    main()
