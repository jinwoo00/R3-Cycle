#!/usr/bin/env python3
"""
R3-Cycle Main Program for Raspberry Pi Zero 2 W
Complete sensor integration and transaction processing

This script handles:
- RFID card scanning (RC522)
- Paper counting (IR sensor - each detection = 1 paper)
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

# Import real-time client (optional - will fail gracefully if not available)
try:
    from realtime_client import RealtimeClient, RealtimeStreamingThread
    REALTIME_AVAILABLE = True
except ImportError:
    REALTIME_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("Real-time client not available. Install: pip3 install python-socketio")

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
    COUNTING_PAPERS = "counting_papers"  # Changed from WEIGHING - now counting papers
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
        
        # Lock for RFID reader to prevent concurrent reads
        self.rfid_lock = threading.Lock()
        
        # Lock for LCD to prevent concurrent writes (prevents freezing)
        self.lcd_lock = threading.Lock()
        
        # Track LCD errors to prevent repeated failures
        self.lcd_error_count = 0
        self.lcd_max_errors = 5  # Disable LCD after 5 consecutive errors

        try:
            # Setup GPIO mode
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)

            # Initialize LCD display
            self._init_lcd()
            
            # Show "Initializing..." message immediately
            if self.lcd:
                try:
                    logger.info("[STARTUP] Showing 'Initializing...' on LCD")
                    self.lcd_display("R3-Cycle", "Initializing...", timeout=2.0)
                    logger.info("[STARTUP] LCD 'Initializing...' message sent")
                except Exception as e:
                    logger.error(f"[STARTUP] Failed to show 'Initializing...' on LCD: {e}")
                    pass  # Ignore LCD errors during init
            else:
                logger.warning("[STARTUP] LCD not available - skipping 'Initializing...' message")

            # Initialize RFID reader
            self._init_rfid()

            # Load cell and metal detection removed - using paper count instead
            # No need to initialize load cell or inductive sensor
            self.load_cell = None
            logger.info("[SYSTEM] Load cell and metal detection disabled - using paper count for points")

            # Initialize IR sensor (for paper detection/counting)
            self._init_ir_sensor()

            # Initialize LED
            self._init_led()
            
            # Inductive sensor removed - using signage warning instead of metal detection
            # No need to initialize inductive sensor

            # Initialize servos (optional for main flow, used in redemption)
            self._init_servos()

            self.initialized = True
            logger.info("Hardware initialization complete")
            
            # Show "System ready" immediately on LCD
            if self.lcd:
                try:
                    logger.info("[STARTUP] Showing 'System Ready' on LCD")
                    self.lcd_display("R3-Cycle Ready", "Scan RFID Card", timeout=2.0)
                    logger.info("[STARTUP] LCD 'System Ready' message sent")
                except Exception as e:
                    logger.error(f"[STARTUP] Failed to show 'System Ready' on LCD: {e}")
                    pass  # Ignore LCD errors
            else:
                logger.warning("[STARTUP] LCD not available - skipping 'System Ready' message")

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

    def _init_load_cell_lazy(self):
        """
        Initialize HX711 load cell on first use (lazy initialization)
        
        This method is called only when load cell is actually needed (first weight read).
        This prevents startup from hanging on load cell issues.
        """
        try:
            logger.info("[LOAD_CELL] Initializing load cell (lazy init)...")
            
            # Create HX711 instance
            self.load_cell = HX711(
                dout_pin=config.PIN_LOAD_CELL_DT,
                pd_sck_pin=config.PIN_LOAD_CELL_SCK
            )
            
            # Check library compatibility
            has_set_reference = hasattr(self.load_cell, 'set_reference_unit')
            has_tare = hasattr(self.load_cell, 'tare')
            has_get_weight = hasattr(self.load_cell, 'get_weight')
            
            # Set reference unit if method exists
            if has_set_reference:
                try:
                    self.load_cell.set_reference_unit(config.LOAD_CELL_REFERENCE_UNIT)
                    logger.debug("[LOAD_CELL] Reference unit set")
                except Exception as e:
                    logger.warning(f"[LOAD_CELL] Failed to set reference unit: {e}")
            
            # Reset load cell
            logger.debug("[LOAD_CELL] Resetting load cell...")
            try:
                self.load_cell.reset()
                logger.debug("[LOAD_CELL] Reset completed")
            except Exception as e:
                logger.warning(f"[LOAD_CELL] Reset failed: {e}")
                raise
            
            # Check if tare method exists (library version compatibility)
            if has_tare:
                logger.debug("[LOAD_CELL] Taring load cell...")
                try:
                    self.load_cell.tare()  # Zero the scale
                    logger.info("[LOAD_CELL] ✅ Load cell initialized and tared")
                except Exception as e:
                    logger.warning(f"[LOAD_CELL] Tare failed: {e}")
                    logger.info("[LOAD_CELL] Load cell initialized (tare failed - using reset only)")
            else:
                logger.info("[LOAD_CELL] Load cell initialized (tare() not available - using reset only)")
                time.sleep(0.5)  # Brief delay for stabilization
                
            # Store compatibility flags for weight calculation
            self.load_cell_use_manual = not has_get_weight or not has_set_reference
            self.load_cell_zero_offset = None  # Will be set during first reading if manual calculation needed
            
            if self.load_cell_use_manual:
                logger.info("[LOAD_CELL] Will use manual weight calculation from raw values")
            
            logger.info("[LOAD_CELL] ✅ Load cell lazy initialization complete")
            
        except Exception as e:
            logger.error(f"[LOAD_CELL] Lazy initialization error: {e}", exc_info=True)
            self.load_cell = None
            self.load_cell_use_manual = False
            raise  # Re-raise so caller knows initialization failed

    def _init_ir_sensor(self):
        """Initialize IR obstacle sensor"""
        try:
            # Setup GPIO - try without pull-up first (sensor may have built-in pull-up)
            # If sensor has built-in pull-up, adding PUD_UP might conflict
            # Test without pull-up first, add if needed for stability
            GPIO.setup(config.PIN_IR_SENSOR, GPIO.IN)
            
            # Small delay to let GPIO stabilize
            time.sleep(0.1)
            
            # Read initial state multiple times for stability
            readings = []
            for _ in range(5):
                readings.append(GPIO.input(config.PIN_IR_SENSOR))
                time.sleep(0.05)
            
            # Use majority reading for initial state
            initial_state = max(set(readings), key=readings.count)
            
            # IR sensor logic: LOW (0) = object detected, HIGH (1) = no object
            object_detected = initial_state == GPIO.LOW
            logger.info(f"[IR] IR sensor initialized on GPIO {config.PIN_IR_SENSOR}")
            logger.info(f"[IR] Initial readings: {readings} -> stable: {initial_state}")
            logger.info(f"[IR] Initial sensor state: {initial_state} ({'LOW' if initial_state == GPIO.LOW else 'HIGH'}) -> {'OBJECT DETECTED' if object_detected else 'NO OBJECT'}")
            logger.info(f"[IR] Note: Sensor setup WITHOUT pull-up resistor (sensor may have built-in pull-up)")
        except Exception as e:
            logger.error(f"[IR] IR sensor initialization failed: {e}", exc_info=True)

    def _init_inductive_sensor(self):
        """Initialize inductive proximity sensor"""
        try:
            GPIO.setup(config.PIN_INDUCTIVE_SENSOR, GPIO.IN)
            logger.info(f"Inductive sensor initialized on GPIO {config.PIN_INDUCTIVE_SENSOR} (Pin 11)")
        except Exception as e:
            logger.error(f"Inductive sensor initialization failed: {e}")

    def _init_led(self):
        """Initialize LED indicator"""
        try:
            # LED indicator (GPIO 22) - only one LED used since GPIO27 is IR sensor
            GPIO.setup(config.PIN_LED_RED, GPIO.OUT)
            GPIO.output(config.PIN_LED_RED, GPIO.LOW)
            logger.info(f"LED initialized on GPIO {config.PIN_LED_RED} (Pin 15)")
        except Exception as e:
            logger.error(f"LED initialization failed: {e}")

    def _init_servos(self):
        """Initialize position servo motors (SG90) with PWM"""
        try:
            GPIO.setup(config.PIN_SERVO_COLLECTION, GPIO.OUT)
            GPIO.setup(config.PIN_SERVO_REWARD, GPIO.OUT)
            
            # Create PWM instances for both servos (50Hz for standard SG90 servos)
            self.servo_collection_pwm = GPIO.PWM(config.PIN_SERVO_COLLECTION, config.SERVO_FREQUENCY)
            self.servo_reward_pwm = GPIO.PWM(config.PIN_SERVO_REWARD, config.SERVO_FREQUENCY)
            
            # Calculate duty cycle for idle position (90 degrees)
            idle_duty_cycle = 2.5 + (config.SERVO_COLLECTION_IDLE / 180.0) * 10.0
            
            # Start PWM with idle position (90 degrees / 7.5% duty cycle)
            self.servo_collection_pwm.start(idle_duty_cycle)
            self.servo_reward_pwm.start(idle_duty_cycle)
            
            # Small delay to allow servos to reach position
            time.sleep(config.SERVO_MOVE_DELAY)
            
            logger.info(f"Position servo motors (SG90) initialized at idle position ({config.SERVO_COLLECTION_IDLE}°)")
        except Exception as e:
            logger.error(f"Servo initialization failed: {e}")
            self.servo_collection_pwm = None
            self.servo_reward_pwm = None
    
    def _set_servo_angle(self, pwm, angle, delay=True):
        """
        Set servo to specific angle (SG90 position servo)
        
        Args:
            pwm: PWM object for the servo
            angle: Angle in degrees (0-180)
                   - 0° = 2.5% duty cycle (fully counter-clockwise)
                   - 90° = 7.5% duty cycle (center/idle)
                   - 180° = 12.5% duty cycle (fully clockwise)
            delay: Whether to add delay after setting angle (default: True)
                   Set to False for faster synchronized movements
        
        Formula: duty_cycle = 2.5 + (angle / 180.0) * 10.0
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
        
        # Small delay for servo to reach position (optional for faster movements)
        if delay:
            time.sleep(config.SERVO_MOVE_DELAY)
    
    def dispense_synchronized(self, cycles=None):
        """
        Synchronized opposite rotation dispensing using SG90 position servos
        
        Physical Setup (SWAPPED ROTATION):
        - Servo #1 (Pin 12/GPIO 18): Rotates from 180° → 0° (counter-clockwise)
        - Servo #2 (Pin 33/GPIO 13): Rotates from 0° → 180° (clockwise)
        
        Both servos move simultaneously in opposite directions for synchronized dispensing.
        After each cycle, servos return to original start positions (180° and 0°), then to idle (90°).
        
        Args:
            cycles: Number of complete cycles (0°↔180°) per dispense (default: config.SERVO_DISPENSE_CYCLES)
        """
        if not self.servo_collection_pwm or not self.servo_reward_pwm:
            logger.error("Servos not initialized - cannot dispense")
            return False
        
        cycles = cycles if cycles is not None else config.SERVO_DISPENSE_CYCLES
        
        logger.info(f"[SERVO] Starting synchronized opposite rotation dispensing ({cycles} cycle(s))")
        
        try:
            # Move to starting positions first
            logger.info("[SERVO] Moving to starting positions...")
            logger.info(f"[SERVO] Servo #1 (Collection) → {config.SERVO_COLLECTION_START}° (from idle {config.SERVO_COLLECTION_IDLE}°)")
            logger.info(f"[SERVO] Servo #2 (Reward) → {config.SERVO_REWARD_START}° (from idle {config.SERVO_REWARD_IDLE}°)")
            self._set_servo_angle(self.servo_collection_pwm, config.SERVO_COLLECTION_START)
            self._set_servo_angle(self.servo_reward_pwm, config.SERVO_REWARD_START)
            time.sleep(config.SERVO_MOVE_DELAY)  # Wait for servos to reach starting positions
            
            # Perform synchronized opposite rotation cycles
            for cycle in range(cycles):
                logger.info(f"[SERVO] Cycle {cycle + 1}/{cycles}: Rotating in opposite directions...")
                
                # Calculate number of steps
                angle_range = abs(config.SERVO_COLLECTION_END - config.SERVO_COLLECTION_START)
                num_steps = int(angle_range / config.SERVO_DISPENSE_ANGLE_STEP)
                
                # Synchronized opposite rotation (SWAPPED): Servo 1 goes 180°→0°, Servo 2 goes 0°→180°
                logger.info(f"[SERVO] Starting synchronized rotation: Servo #1 {config.SERVO_COLLECTION_START}°→{config.SERVO_COLLECTION_END}°, Servo #2 {config.SERVO_REWARD_START}°→{config.SERVO_REWARD_END}°")
                for step in range(num_steps + 1):
                    # Calculate current angles for both servos
                    # Servo #1: 180° → 0° (counter-clockwise - reverse direction)
                    angle1 = config.SERVO_COLLECTION_START - (step * config.SERVO_DISPENSE_ANGLE_STEP)
                    angle1 = max(angle1, config.SERVO_COLLECTION_END)
                    
                    # Servo #2: 0° → 180° (clockwise - forward direction)
                    angle2 = config.SERVO_REWARD_START + (step * config.SERVO_DISPENSE_ANGLE_STEP)
                    angle2 = min(angle2, config.SERVO_REWARD_END)
                    
                    # Set both servos simultaneously (without delay for synchronized movement)
                    self._set_servo_angle(self.servo_collection_pwm, angle1, delay=False)
                    self._set_servo_angle(self.servo_reward_pwm, angle2, delay=False)
                    
                    # Log every 10th step for debugging
                    if step % 10 == 0 or step == num_steps:
                        logger.info(f"[SERVO] Step {step}/{num_steps}: Servo #1={angle1:.1f}°, Servo #2={angle2:.1f}°")
                    
                    # Small delay between steps for smooth movement (both servos move together)
                    if step < num_steps:
                        time.sleep(config.SERVO_DISPENSE_STEP_DELAY)
                
                logger.info(f"[SERVO] Cycle {cycle + 1} rotation complete: Servo #1={config.SERVO_COLLECTION_END}°, Servo #2={config.SERVO_REWARD_END}°")
                
                # After reaching end positions, return to start positions for next cycle
                if cycle < cycles - 1:  # Don't return on last cycle
                    logger.info(f"[SERVO] Cycle {cycle + 1} complete - returning to start positions...")
                    self._set_servo_angle(self.servo_collection_pwm, config.SERVO_COLLECTION_START)
                    self._set_servo_angle(self.servo_reward_pwm, config.SERVO_REWARD_START)
                    time.sleep(config.SERVO_MOVE_DELAY)
            
            # Return to idle position after dispensing
            logger.info("[SERVO] Dispensing complete - returning to idle position...")
            time.sleep(config.SERVO_RETURN_DELAY)
            self._set_servo_angle(self.servo_collection_pwm, config.SERVO_COLLECTION_IDLE)
            self._set_servo_angle(self.servo_reward_pwm, config.SERVO_REWARD_IDLE)
            
            logger.info("[SERVO] ✅ Synchronized opposite rotation dispensing complete")
            return True
            
        except Exception as e:
            logger.error(f"[SERVO] Error during synchronized dispensing: {e}")
            import traceback
            traceback.print_exc()
            # Try to return to idle position even if error occurred
            try:
                self._set_servo_angle(self.servo_collection_pwm, config.SERVO_COLLECTION_IDLE)
                self._set_servo_angle(self.servo_reward_pwm, config.SERVO_REWARD_IDLE)
            except:
                pass
            return False
    
    def servos_stop(self):
        """
        Return both position servos (SG90) to idle position immediately
        """
        if not self.servo_collection_pwm or not self.servo_reward_pwm:
            logger.error("Servos not initialized - cannot stop")
            return False
        
        logger.info("[SERVO] Returning servos to idle position...")
        
        try:
            # Set both servos to idle position (90 degrees)
            self._set_servo_angle(self.servo_collection_pwm, config.SERVO_COLLECTION_IDLE)
            self._set_servo_angle(self.servo_reward_pwm, config.SERVO_REWARD_IDLE)
            
            logger.info("[SERVO] ✅ Servos returned to idle position")
            return True
            
        except Exception as e:
            logger.error(f"[SERVO] Error returning servos to idle: {e}")
            return False

    # ========================================
    # LCD DISPLAY METHODS
    # ========================================

    def lcd_display(self, line1, line2="", timeout=2.0):
        """
        Display message on LCD with thread safety and timeout protection
        
        Args:
            line1: First line of text (max 16 chars)
            line2: Second line of text (max 16 chars, optional)
            timeout: Maximum time to wait for I2C operation (seconds)
        
        This method prevents LCD freezing by:
        - Using a lock to prevent concurrent writes
        - Adding timeout protection for I2C operations
        - Retrying failed operations once
        - Gracefully handling errors without blocking
        """
        if not self.lcd:
            # Check if LCD was disabled due to too many errors
            if self.lcd_error_count >= self.lcd_max_errors:
                logger.warning(f"LCD disabled due to {self.lcd_error_count} consecutive errors")
            else:
                logger.warning("LCD not available")
            return

        # Check if LCD was disabled due to errors
        if self.lcd_error_count >= self.lcd_max_errors:
            logger.warning(f"LCD operations disabled due to {self.lcd_error_count} consecutive errors")
            return

        # Use lock to prevent concurrent writes (prevents I2C bus conflicts)
        if not self.lcd_lock.acquire(timeout=timeout):
            logger.warning(f"LCD lock timeout after {timeout}s - skipping display update")
            return

        try:
            # Truncate lines to fit LCD width
            line1_truncated = str(line1)[:config.LCD_COLS] if line1 else ""
            line2_truncated = str(line2)[:config.LCD_COLS] if line2 else ""
            
            # Retry once if operation fails
            max_retries = 2
            retry_count = 0
            success = False
            
            while retry_count < max_retries and not success:
                try:
                    # Clear screen first
                    self.lcd.clear()
                    time.sleep(0.01)  # Brief delay after clear
                    
                    # Write line 1
                    if line1_truncated:
                        self.lcd.cursor_pos = (0, 0)
                        self.lcd.write_string(line1_truncated)
                    
                    # Write line 2
                    if line2_truncated:
                        self.lcd.cursor_pos = (1, 0)
                        self.lcd.write_string(line2_truncated)
                    
                    # If we get here, operation succeeded
                    success = True
                    self.lcd_error_count = 0  # Reset error count on success
                    
                    # Log LCD updates for debugging (info level so visible in logs)
                    logger.info(f"[LCD] Display: '{line1_truncated}' / '{line2_truncated}'")
                    
                except Exception as e:
                    retry_count += 1
                    if retry_count < max_retries:
                        logger.warning(f"LCD write error (attempt {retry_count}/{max_retries}): {e} - retrying...")
                        time.sleep(0.05)  # Brief delay before retry
                    else:
                        # Final attempt failed
                        self.lcd_error_count += 1
                        logger.error(f"LCD display error after {max_retries} attempts: {e}")
                        
                        # If too many consecutive errors, disable LCD
                        if self.lcd_error_count >= self.lcd_max_errors:
                            logger.error(f"LCD disabled after {self.lcd_error_count} consecutive errors - check I2C connections")
                            self.lcd = None  # Disable LCD to prevent further attempts
                        
        except Exception as e:
            # Lock-related or unexpected error
            self.lcd_error_count += 1
            logger.error(f"LCD operation failed: {e}")
            
            # Disable LCD if too many errors
            if self.lcd_error_count >= self.lcd_max_errors:
                logger.error(f"LCD disabled after {self.lcd_error_count} consecutive errors")
                self.lcd = None
        
        finally:
            # Always release the lock
            try:
                self.lcd_lock.release()
            except:
                pass  # Ignore errors when releasing lock

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

    def lcd_paper_detected(self):
        """Display paper detected message"""
        self.lcd_display(*config.LCD_MSG_PAPER_DETECTED)

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

    def lcd_card_not_registered(self):
        """Display card not registered message"""
        self.lcd_display(*config.LCD_MSG_CARD_NOT_REGISTERED)

    def lcd_offline(self):
        """Display offline mode message"""
        self.lcd_display("OFFLINE MODE", "Check network")

    # ========================================
    # SENSOR READING METHODS
    # ========================================

    def read_rfid(self, timeout=None, check_scan_request=None):
        """
        Read RFID card
        Args:
            timeout: Maximum time to wait (seconds)
            check_scan_request: Function to call to check if scan request is active (returns True if active)
        Returns: (tag_id, tag_text) or (None, None) if timeout/error
        """
        if not self.rfid_reader:
            logger.error("RFID reader not available")
            return None, None

        timeout = timeout if timeout is not None else config.RFID_TIMEOUT
        
        if timeout is None:
            logger.info("Waiting for RFID card (continuous scanning - no timeout)...")
        else:
            logger.info(f"Waiting for RFID card (timeout: {timeout}s)...")

        try:
            # Check initial scan request state - if scan request is active, abort immediately
            scan_was_active_at_start = False
            if check_scan_request:
                try:
                    scan_was_active_at_start = check_scan_request()
                    if scan_was_active_at_start:
                        logger.info("[RFID] Scan request active at start - aborting normal RFID read (exclusive scan mode)")
                        return None, None
                except Exception as e:
                    logger.debug(f"[RFID] Error checking scan request: {e} - continuing")

            # SimpleMFRC522.read() blocks until card detected
            # We'll use a threading timeout with periodic scan request checks
            result = [None, None]
            scan_became_active = [False]

            def read_card():
                max_retries = 3  # Retry up to 3 times on AUTH errors
                retry_count = 0
                
                while retry_count < max_retries:
                    try:
                        # Use lock to ensure only one read operation at a time
                        with self.rfid_lock:
                            if retry_count == 0:
                                logger.debug(f"[RFID] Starting read (will block until card detected)...")
                            else:
                                logger.debug(f"[RFID] Retry attempt {retry_count + 1}/{max_retries}...")
                            # Use the same pattern as working standalone code
                            # This will BLOCK until a card is detected
                            tag_id, tag_text = self.rfid_reader.read()
                            logger.debug(f"[RFID] Read completed: tag_id={tag_id}, text={tag_text}")
                        
                        # Check if scan request became active during read
                        if check_scan_request and check_scan_request() and not scan_was_active_at_start:
                            logger.debug("Scan request became active during RFID read")
                            scan_became_active[0] = True
                        
                        # If scan request interrupted, don't process result
                        if scan_became_active[0]:
                            logger.debug("RFID read interrupted by scan request")
                            result[0] = None
                            result[1] = None
                            return
                        
                        # Check for AUTH errors (tag_id is None)
                        if tag_id is None:
                            retry_count += 1
                            if retry_count < max_retries:
                                logger.debug(f"[RFID] AUTH error (attempt {retry_count}/{max_retries}) - retrying...")
                                time.sleep(0.2)  # Brief delay before retry
                                continue  # Retry the read
                            else:
                                logger.warning(f"[RFID] AUTH error after {max_retries} attempts - returning None")
                                result[0] = None
                                result[1] = None
                                return
                        
                        # Success - got a valid tag
                        result[0] = str(tag_id)
                        result[1] = tag_text if tag_text else ""
                        logger.debug(f"[RFID] Read successful: ID={result[0]}, Text={result[1]}")
                        return  # Success, exit retry loop
                        
                    except Exception as e:
                        error_msg = str(e)
                        # Check if it's an AUTH error
                        if "AUTH" in error_msg.upper() or "status2reg" in error_msg or "auth error" in error_msg.lower():
                            retry_count += 1
                            if retry_count < max_retries:
                                logger.debug(f"[RFID] AUTH exception (attempt {retry_count}/{max_retries}): {error_msg} - retrying...")
                                time.sleep(0.2)  # Brief delay before retry
                                continue  # Retry the read
                            else:
                                logger.warning(f"[RFID] AUTH exception after {max_retries} attempts: {error_msg}")
                                result[0] = None
                                result[1] = None
                                return
                        else:
                            # Other error - log and return (don't retry non-AUTH errors)
                            logger.error(f"[RFID] Read error (non-AUTH): {e}")
                            result[0] = None
                            result[1] = None
                            return

            read_thread = threading.Thread(target=read_card)
            read_thread.daemon = True
            read_thread.start()
            
            # Monitor with periodic scan request checks
            check_interval = 0.5  # Check every 0.5 seconds
            elapsed = 0
            
            # If timeout is None, wait indefinitely (continuous scanning)
            while timeout is None or elapsed < timeout:
                read_thread.join(check_interval)
                if not read_thread.is_alive():
                    break  # Thread finished (either success or error)
                
                # Check if scan request became active during read (only if callback provided)
                if check_scan_request:
                    try:
                        if check_scan_request():
                            if not scan_was_active_at_start:
                                logger.debug("Scan request became active during RFID read - aborting")
                                scan_became_active[0] = True
                                # Don't return immediately - let the read thread finish and check result
                    except Exception as e:
                        logger.debug(f"Error checking scan request: {e} - continuing RFID read")
                
                elapsed += check_interval

            # Only return result if scan request didn't become active
            # If scan request became active, abort immediately to give exclusive access to scan request
            if scan_became_active[0]:
                logger.info("[RFID] RFID read aborted - scan request became active during read (exclusive scan mode)")
                return None, None

            if result[0]:
                logger.info(f"RFID card detected: {result[0]}")
                return result[0], result[1]
            else:
                if timeout is None:
                    logger.debug("RFID read returned no result (interrupted or error)")
                else:
                    logger.warning(f"RFID read timeout after {timeout}s")
                return None, None

        except Exception as e:
            logger.error(f"RFID read exception: {e}")
            return None, None

    def _calculate_weight_from_raw(self, raw_value):
        """Calculate weight from raw value using manual formula"""
        if self.load_cell_zero_offset is None:
            # First reading - establish zero offset
            self.load_cell_zero_offset = raw_value
            logger.info(f"Load cell zero offset established: {self.load_cell_zero_offset:.2f}")
            return 0.0
        
        reference_unit = abs(config.LOAD_CELL_REFERENCE_UNIT)
        if reference_unit <= 0:
            return 0.0
        
        # Detect if load cell is inverted by checking raw value change
        # If we don't have inversion flag yet, try to detect it on first non-zero reading
        if not hasattr(self, 'load_cell_inverted'):
            raw_difference = raw_value - self.load_cell_zero_offset
            # If raw value is significantly lower than zero offset, likely inverted
            # Use a threshold to avoid false positives from noise
            if raw_difference < -1000:  # Significant negative change suggests inversion
                self.load_cell_inverted = True
                logger.warning("Load cell appears to be INVERTED (raw decreases with weight) - using inverted calculation")
            elif raw_difference > 1000:  # Positive change is normal
                self.load_cell_inverted = False
            else:
                # Too close to zero, can't determine yet - assume normal for now
                self.load_cell_inverted = False
        
        # Calculate weight based on inversion state
        if hasattr(self, 'load_cell_inverted') and self.load_cell_inverted:
            # Inverted: weight = (zero_offset - raw_value) / reference_unit
            weight = (self.load_cell_zero_offset - raw_value) / reference_unit
        else:
            # Normal: weight = (raw_value - zero_offset) / reference_unit
            weight = (raw_value - self.load_cell_zero_offset) / reference_unit
        
        return weight

    def read_weight(self, timeout=10.0):
        """
        Read weight from load cell with timeout protection
        
        Args:
            timeout: Maximum time to wait for weight reading (seconds)
        
        Returns: weight in grams (float) or None if error/timeout
        
        This method prevents hanging by running load cell reads in a separate
        thread with timeout protection. If the HX711 doesn't respond, the
        operation will timeout instead of hanging forever.
        
        Uses lazy initialization - load cell is initialized on first use.
        """
        # Lazy initialization - initialize load cell on first use
        if not self.load_cell:
            logger.info("[LOAD_CELL] Load cell not initialized - initializing now...")
            self._init_load_cell_lazy()
            if not self.load_cell:
                logger.error("[LOAD_CELL] Failed to initialize load cell")
                return None

        result = [None]  # Use list to store result (thread-safe mutable)
        exception_occurred = [None]
        
        def read_weight_thread():
            """Read weight in a separate thread"""
            try:
                # Take multiple readings and average
                readings = []
                max_readings = 3  # Reduce to 3 readings for faster response
                
                for i in range(max_readings):
                    try:
                        if self.load_cell_use_manual:
                            # Manual calculation from raw values
                            raw_readings = self.load_cell.get_raw_data(3)  # Reduced from 5 to 3
                            if isinstance(raw_readings, list):
                                raw_value = sum(raw_readings) / len(raw_readings)
                            else:
                                raw_value = raw_readings
                            
                            val = self._calculate_weight_from_raw(raw_value)
                        else:
                            # Use library's get_weight if available
                            val = self.load_cell.get_weight(3)  # Reduced from 5 to 3
                        
                        if val is not None:
                            readings.append(val)
                        
                        time.sleep(0.1)
                        
                    except Exception as e:
                        logger.warning(f"Load cell read attempt {i+1}/{max_readings} failed: {e}")
                        continue  # Continue to next reading
                
                # Calculate average from successful readings
                if len(readings) == 0:
                    logger.error("All load cell readings failed")
                    exception_occurred[0] = Exception("All load cell readings failed")
                    return
                
                weight = sum(readings) / len(readings)
                result[0] = round(weight, 2)
                logger.info(f"Weight measured: {weight:.2f}g (from {len(readings)}/{max_readings} successful readings)")
                
            except Exception as e:
                logger.error(f"Load cell read error: {e}", exc_info=True)
                exception_occurred[0] = e
        
        # Run weight reading in a separate thread with timeout
        logger.info("[LOAD_CELL] Starting weight reading (with timeout protection)...")
        read_thread = threading.Thread(target=read_weight_thread)
        read_thread.daemon = True
        read_thread.start()
        read_thread.join(timeout=timeout)
        
        if read_thread.is_alive():
            logger.error(f"[LOAD_CELL] ⚠️  Weight reading TIMEOUT after {timeout}s - load cell may be unresponsive")
            logger.error(f"[LOAD_CELL] Returning None to prevent transaction hang")
            return None
        
        if exception_occurred[0]:
            logger.error(f"[LOAD_CELL] Weight reading failed: {exception_occurred[0]}")
            return None
        
        if result[0] is None:
            logger.warning("[LOAD_CELL] Weight reading returned None")
            return None
        
        logger.info(f"[LOAD_CELL] ✅ Weight reading successful: {result[0]}g")
        return result[0]

    def check_paper_inserted(self):
        """
        Check if paper is inserted (IR sensor)
        Returns: True if paper detected, False otherwise
        
        Note: IR sensor outputs LOW (0) when object detected, HIGH (1) when clear
        This method only reads the sensor - LED control is handled separately
        """
        try:
            # Read raw GPIO value
            raw_value = GPIO.input(config.PIN_IR_SENSOR)
            
            # IR sensor outputs LOW (0) when object detected, HIGH (1) when clear
            detected = raw_value == GPIO.LOW  # LOW means object detected
            
            # Always log for debugging (will be filtered in transaction loop)
            logger.debug(f"[IR] GPIO {config.PIN_IR_SENSOR} read: {raw_value} ({'HIGH' if raw_value == GPIO.HIGH else 'LOW'}) -> {'PAPER DETECTED' if detected else 'NO PAPER'}")
            
            return detected
        except Exception as e:
            logger.error(f"[IR] IR sensor read error: {e}", exc_info=True)
            return False
    
    def set_ir_leds(self, state):
        """
        Control IR sensor indicator LED (GPIO 22)
        
        Args:
            state (bool): True to turn LED ON, False to turn LED OFF
        
        Note: Only GPIO22 is used for LED since GPIO27 is used by IR sensor
        """
        try:
            if state:
                # Paper detected - turn LED ON
                GPIO.output(config.PIN_LED_RED, GPIO.HIGH)  # GPIO 22
            else:
                # No paper - turn LED OFF
                GPIO.output(config.PIN_LED_RED, GPIO.LOW)   # GPIO 22
        except Exception as e:
            logger.error(f"[IR] LED control error: {e}", exc_info=True)

    def check_metal_detected(self):
        """
        Check if metal is detected (DEPRECATED - not used)
        Returns: False (metal detection removed - using signage warning instead)
        """
        # Metal detection removed - always return False
        # Using signage warning instead of hardware detection
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
        # Sensor health - only sensors we actually use
        health = {
            "rfid": config.SENSOR_OK if self.rfid_reader else config.SENSOR_ERROR,
            "loadCell": config.SENSOR_ERROR,  # Load cell disabled/removed
            "inductiveSensor": config.SENSOR_ERROR,  # Inductive sensor disabled/removed
            "irSensor": config.SENSOR_OK,  # IR sensor for paper detection
            "servo": config.SENSOR_OK  # Servo motors for rewards
        }

        # No testing needed - load cell and inductive sensor are not used
        logger.debug(f"Sensor health: {health}")
        return health

    def cleanup(self):
        """Cleanup GPIO and hardware resources"""
        logger.info("Cleaning up hardware...")
        try:
            if self.lcd:
                self.lcd.clear()
                self.lcd_display("System", "Shutting down...")
            
            # Return servos to idle position before stopping PWM
            if hasattr(self, 'servo_collection_pwm') and self.servo_collection_pwm:
                try:
                    # Return to idle position first
                    self._set_servo_angle(self.servo_collection_pwm, config.SERVO_COLLECTION_IDLE)
                    time.sleep(0.2)
                    self.servo_collection_pwm.stop()
                    logger.info("[SERVO] Collection servo returned to idle and PWM stopped")
                except:
                    pass
            
            if hasattr(self, 'servo_reward_pwm') and self.servo_reward_pwm:
                try:
                    # Return to idle position first
                    self._set_servo_angle(self.servo_reward_pwm, config.SERVO_REWARD_IDLE)
                    time.sleep(0.2)
                    self.servo_reward_pwm.stop()
                    logger.info("[SERVO] Reward servo returned to idle and PWM stopped")
                except:
                    pass
            
            GPIO.cleanup()
            logger.info("Hardware cleanup complete")
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

    def submit_transaction(self, rfid_tag, paper_count):
        """
        Submit transaction to backend
        Returns: (success, transaction_data)
        
        Args:
            rfid_tag: User's RFID tag
            paper_count: Number of papers inserted (points = paper_count * points_per_paper)
        """
        logger.info(f"Submitting transaction: {paper_count} paper(s)")

        success, data = self._make_request("POST", "transaction/submit", {
            "rfidTag": rfid_tag,
            "paperCount": paper_count,
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

        return success

    def get_pending_redemptions(self):
        """
        Get pending redemptions from backend
        Returns: (success, redemptions_list) or (False, None)
        """
        logger.debug("Fetching pending redemptions...")

        success, data = self._make_request("GET", "redemption/pending")

        if success and data.get("success"):
            redemptions = data.get("redemptions", [])
            logger.info(f"Found {len(redemptions)} pending redemption(s)")
            return True, redemptions
        else:
            logger.error(f"Failed to fetch redemptions: {data.get('message') if data else 'No response'}")
            return False, None

    def mark_redemption_dispensed(self, redemption_id):
        """
        Mark redemption as dispensed in backend
        Returns: success (bool)
        
        Args:
            redemption_id: Redemption record ID from backend
        """
        logger.info(f"Marking redemption {redemption_id} as dispensed...")

        success, data = self._make_request("POST", "redemption/dispense", {
            "redemptionId": redemption_id,
            "machineId": config.MACHINE_ID
        })

        if success and data.get("success"):
            logger.info(f"✅ Redemption {redemption_id} marked as dispensed")
            return True
        else:
            logger.error(f"Failed to mark redemption dispensed: {data.get('message') if data else 'No response'}")
            return False

# ============================================
# MAIN TRANSACTION PROCESSOR
# ============================================

class TransactionProcessor:
    """Manages complete transaction flow"""

    def __init__(self, hardware, api_client, sync_manager=None, realtime_client=None):
        """Initialize transaction processor"""
        self.hardware = hardware
        self.api = api_client
        self.sync = sync_manager  # Offline mode sync manager (optional)
        self.realtime = realtime_client  # Real-time client (optional)
        self.state = TransactionState.IDLE
        self.bond_paper_stock = config.BOND_PAPER_INITIAL_STOCK
        self.current_transaction_id = None

        if self.sync:
            logger.info("Transaction processor initialized with OFFLINE MODE")
        else:
            logger.info("Transaction processor initialized (ONLINE ONLY)")
        
        if self.realtime:
            logger.info("Transaction processor initialized with REAL-TIME STREAMING")

    def wait_for_multiple_papers(self):
        """
        Wait for multiple paper insertions with inactivity timeout
        
        Returns: (success, paper_count) - (True, count) if papers detected and timeout reached, 
                                          (False, 0) if timeout or error
        
        Detection pattern:
        - HIGH → LOW (stable for 0.2s) = 1 paper detected
        - After detection, wait for HIGH (paper passed through)
        - Reset for next paper detection
        - Each cycle (HIGH → LOW → HIGH) = 1 paper
        - After 10s inactivity (no new papers), wait for sensor clear (HIGH), then return total
        """
        import RPi.GPIO as GPIO
        
        paper_count = 0
        IR_DETECTION_TIME = 0.2  # Seconds of stable LOW state required for detection
        inactivity_timeout = config.PAPER_INSERTION_INACTIVITY_TIMEOUT
        last_paper_detection_time = None
        check_count = 0
        last_lcd_update_time = 0
        lcd_update_interval = 0.5  # Update LCD every 0.5 seconds
        initial_start_time = time.time()
        
        # State tracking for paper detection
        first_low_time = None  # Timestamp when LOW was first detected
        waiting_for_clear = False  # After detecting paper, wait for HIGH before next detection
        
        logger.info("[IR] ========================================")
        logger.info("[IR] Starting multi-paper insertion detection")
        logger.info(f"[IR] Inactivity timeout: {inactivity_timeout}s")
        logger.info(f"[IR] Detection: 1 LOW read + 0.2s stable = 1 paper")
        logger.info("[IR] ========================================")
        
        # Ensure sensor starts clear (HIGH)
        clear_check_count = 0
        max_clear_checks = 30  # Wait up to 3 seconds
        logger.info("[IR] Ensuring sensor is clear (HIGH) before starting...")
        
        while clear_check_count < max_clear_checks:
            current_state = GPIO.input(config.PIN_IR_SENSOR)
            if current_state == GPIO.HIGH:
                stable_high_count = 0
                for _ in range(5):
                    if GPIO.input(config.PIN_IR_SENSOR) == GPIO.HIGH:
                        stable_high_count += 1
                    time.sleep(0.1)
                
                if stable_high_count >= 4:
                    logger.info("[IR] ✅ Sensor clear - ready for paper detection")
                    break
            clear_check_count += 1
            time.sleep(0.1)
        
        # Update LCD to show waiting state
        self.hardware.lcd_display("Insert paper", f"Count: {paper_count}")
        
        # Main detection loop
        while True:
            check_count += 1
            current_time = time.time()
            raw_gpio_value = GPIO.input(config.PIN_IR_SENSOR)
            
            # If waiting for sensor to clear after paper detection
            if waiting_for_clear:
                if raw_gpio_value == GPIO.HIGH:
                    # Sensor cleared - ready for next paper
                    stable_high_count = 0
                    for _ in range(3):  # Quick check for stability
                        if GPIO.input(config.PIN_IR_SENSOR) == GPIO.HIGH:
                            stable_high_count += 1
                        time.sleep(0.05)
                    
                    if stable_high_count >= 2:
                        waiting_for_clear = False
                        logger.info(f"[IR] Sensor cleared - ready for next paper (Count: {paper_count})")
                        # Reset detection state
                        first_low_time = None
                else:
                    # Still LOW - paper hasn't passed through yet
                    time.sleep(0.1)
                    continue
            
            # Detection logic: Time-based - LOW stable for 0.2s = 1 paper
            if raw_gpio_value == GPIO.LOW:
                # GPIO is LOW - could be paper
                if first_low_time is None:
                    # First LOW detected in this cycle - start timer
                    first_low_time = current_time
                    logger.debug(f"[IR] HIGH → LOW transition detected - starting timer...")
                
                # Check if LOW has been stable for required time (time-based verification)
                elapsed_time = current_time - first_low_time
                if elapsed_time >= IR_DETECTION_TIME:
                    # Paper detected! (LOW state has been stable for 0.2s)
                    paper_count += 1
                    last_paper_detection_time = current_time
                    
                    logger.info(f"[IR] ✅ PAPER #{paper_count} DETECTED! (stable LOW for {elapsed_time:.2f}s)")
                    
                    # Update LCD with new count
                    self.hardware.lcd_display("Insert paper", f"Count: {paper_count}")
                    self.hardware.set_ir_leds(True)
                    
                    # Send real-time update
                    if self.realtime and self.realtime.is_connected():
                        self.realtime.send_transaction_update(self.current_transaction_id, "counting", {
                            "paperCount": paper_count,
                            "status": "paper_inserted"
                        })
                    
                    # Check max papers limit
                    if paper_count >= config.MAX_PAPERS_PER_TRANSACTION:
                        logger.warning(f"[IR] Maximum papers ({config.MAX_PAPERS_PER_TRANSACTION}) reached - stopping detection")
                        break
                    
                    # Now wait for sensor to clear (HIGH) before next detection
                    waiting_for_clear = True
                    logger.debug(f"[IR] Waiting for sensor to clear (paper pass through)...")
                    
                    # Reset for next cycle
                    first_low_time = None
            else:
                # GPIO is HIGH (clear) - reset timer if it was counting
                if first_low_time is not None:
                    # Was counting LOWs but now HIGH - false alarm, reset
                    logger.debug(f"[IR] HIGH detected - resetting timer (LOW was only {current_time - first_low_time:.2f}s)")
                first_low_time = None
            
            # Update LCD periodically
            if current_time - last_lcd_update_time >= lcd_update_interval:
                self.hardware.lcd_display("Insert paper", f"Count: {paper_count}")
                last_lcd_update_time = current_time
            
            # Check inactivity timeout
            if last_paper_detection_time is not None:
                time_since_last_paper = current_time - last_paper_detection_time
                if time_since_last_paper >= inactivity_timeout:
                    # Inactivity timeout reached - wait for sensor to clear, then return
                    logger.info(f"[IR] Inactivity timeout reached ({time_since_last_paper:.1f}s since last paper)")
                    logger.info(f"[IR] Total papers detected: {paper_count}")
                    
                    # Wait for sensor to clear (HIGH) before submitting
                    logger.info("[IR] Waiting for sensor to clear (HIGH) before submitting...")
                    clear_wait_start = time.time()
                    max_clear_wait = 5.0  # Wait up to 5 seconds for sensor to clear
                    
                    while (time.time() - clear_wait_start) < max_clear_wait:
                        if GPIO.input(config.PIN_IR_SENSOR) == GPIO.HIGH:
                            stable_high_count = 0
                            for _ in range(5):
                                if GPIO.input(config.PIN_IR_SENSOR) == GPIO.HIGH:
                                    stable_high_count += 1
                                time.sleep(0.1)
                            
                            if stable_high_count >= 4:
                                logger.info("[IR] ✅ Sensor cleared - ready to submit transaction")
                                break
                        time.sleep(0.1)
                    
                    # Return total paper count
                    if paper_count > 0:
                        logger.info(f"[IR] ✅ Multi-paper detection complete: {paper_count} paper(s) total")
                        return True, paper_count
                    else:
                        logger.warning("[IR] ⚠️  Inactivity timeout but no papers detected")
                        self.hardware.lcd_display("Timeout", "No papers")
                        time.sleep(2)
                        return False, 0
            
            # Check initial timeout (if no paper detected at all)
            if paper_count == 0 and last_paper_detection_time is None:
                if current_time - initial_start_time >= config.PAPER_INSERTION_TIMEOUT:
                    logger.warning(f"[IR] No paper detected within {config.PAPER_INSERTION_TIMEOUT}s - timeout")
                    self.hardware.lcd_display("Timeout", "Try again")
                    time.sleep(2)
                    return False, 0
            
            time.sleep(0.1)  # Small delay between checks

    def process_transaction(self):
        """
        Main transaction processing loop
        Returns: success (bool)
        """
        try:
            # Wait until scan request is not active (polling loop)
            max_wait_time = 60  # Maximum time to wait for scan request to finish
            wait_start = time.time()
            
            wait_logged = False
            while self.realtime and hasattr(self.realtime, 'scan_request_active'):
                with self.realtime.scan_request_lock:
                    if self.realtime.scan_request_active:
                        # Scan request is active - pause normal transactions and wait
                        if not wait_logged:
                            logger.info("⏸️  Scan request active - pausing normal transactions until scan completes")
                            wait_logged = True
                        elapsed = time.time() - wait_start
                        if elapsed > max_wait_time:
                            logger.warning("Waited too long for scan request to finish - continuing anyway")
                            break
                        time.sleep(0.5)  # Check every 0.5 seconds
                        continue
                    else:
                        # Scan request finished or not active - can proceed
                        if wait_logged:
                            logger.info("✅ Scan request finished - resuming normal transactions")
                        break
            
            # Check if we're in cooldown period after successful scan
            # During cooldown, normal transactions are paused to prevent reading the same card
            if self.realtime and hasattr(self.realtime, 'scan_cooldown_until'):
                with self.realtime.scan_request_lock:
                    current_time = time.time()
                    if current_time < self.realtime.scan_cooldown_until:
                        remaining = self.realtime.scan_cooldown_until - current_time
                        logger.info(f"⏸️  Scan cooldown active - waiting {remaining:.1f} more seconds (user should remove card)")
                        logger.info("   This prevents normal transaction from reading the same card immediately after registration scan")
                        time.sleep(remaining)  # Wait for cooldown to expire
            
            # State 1: Wait for RFID
            self.state = TransactionState.WAITING_FOR_RFID
            self.hardware.lcd_welcome()
            self.hardware.led_off()

            # Check one more time before reading (scan request might have started during wait)
            def check_scan_active():
                """Helper to check if scan request is active"""
                if self.realtime and hasattr(self.realtime, 'scan_request_active'):
                    with self.realtime.scan_request_lock:
                        return self.realtime.scan_request_active
                return False
            
            # Final check before reading - if scan request is active, abort immediately
            if check_scan_active():
                logger.debug("Scan request active before RFID read - aborting normal transaction")
                return False
            
            # Read RFID with scan request check callback
            # The read_rfid method will handle scan request checks internally
            # If scan request becomes active during read, read_rfid will return None
            logger.info("Waiting for RFID card... (place card near reader)")
            rfid_tag, _ = self.hardware.read_rfid(timeout=config.RFID_TIMEOUT, check_scan_request=check_scan_active)
            
            # Check if scan request became active during read
            if check_scan_active():
                logger.info("Scan request became active during RFID read - aborting normal transaction")
                return False
            
            # If we got a tag, use it (scan request wasn't interfering)
            # If we got None, it could be timeout OR scan request interference - both mean no card to process
            if not rfid_tag:
                logger.debug("No RFID detected, returning to idle")
                return False

            # IMPORTANT: After scan request cooldown expires, check if card was just scanned for registration
            # If cooldown just expired (within last 3 seconds), skip this card to prevent duplicate processing
            # This ensures "Card not found" message doesn't appear after registration scan
            if self.realtime and hasattr(self.realtime, 'scan_cooldown_until'):
                with self.realtime.scan_request_lock:
                    current_time = time.time()
                    time_since_cooldown = current_time - self.realtime.scan_cooldown_until
                    # If cooldown just expired (within last 3 seconds), skip to prevent duplicate
                    if -1 < time_since_cooldown < 3:
                        logger.info(f"[RFID] ⚠️  Cooldown just expired ({time_since_cooldown:.1f}s ago) - skipping card to prevent duplicate after registration scan")
                        logger.info(f"[RFID] This prevents 'Card not found' message from appearing after registration scan")
                        logger.info(f"[RFID] User should have removed card during cooldown - waiting for next card")
                        return False

            # Generate transaction ID
            self.current_transaction_id = f"txn_{int(time.time())}_{rfid_tag[-4:]}"
            
            # Send real-time update: RFID detected
            if self.realtime and self.realtime.is_connected():
                self.realtime.send_rfid_detected(rfid_tag)
                self.realtime.send_transaction_update(self.current_transaction_id, "started", {
                    "rfidTag": rfid_tag
                })

            # State 2: Verify user
            self.state = TransactionState.VERIFYING_USER
            self.hardware.lcd_rfid_detected()

            # Use sync manager if available (offline mode), otherwise use direct API
            if self.sync:
                valid, user_data = self.sync.smart_verify_user(rfid_tag)
                if not valid:
                    # Show specific message for unregistered cards
                    self.hardware.lcd_card_not_registered()
                    logger.warning(f"RFID card not registered (offline mode): {rfid_tag}")
                    self.hardware.led_blink(2)
                    time.sleep(5)  # Show message longer
                    return False
                user_name = user_data.get("name", "User")
                current_points = user_data.get("current_points", 0)
            else:
                success, user_data = self.api.verify_rfid(rfid_tag)
                if not success or not user_data.get("valid", False):
                    # Check if card is not registered (different from other errors)
                    if success and user_data.get("message", "").lower().find("not registered") != -1:
                        self.hardware.lcd_card_not_registered()
                        logger.warning(f"RFID card not registered: {rfid_tag}")
                    else:
                        self.hardware.lcd_error()
                        logger.error(f"RFID verification failed: {user_data.get('message', 'Unknown error')}")
                    self.hardware.led_blink(2)
                    time.sleep(5)  # Show message longer for unregistered cards
                    return False
                user_name = user_data.get("userName", "User")
                current_points = user_data.get("currentPoints", 0)

            # State 3: Wait for paper insertion (multi-paper with inactivity timeout)
            self.state = TransactionState.WAITING_FOR_PAPER
            self.hardware.lcd_user_verified(user_name)
            
            # Ensure LEDs are OFF initially (waiting for paper)
            self.hardware.set_ir_leds(False)
            
            # State 4: Wait for multiple papers with inactivity timeout
            self.state = TransactionState.COUNTING_PAPERS
            
            # Use new multi-paper detection method
            success, paper_count = self.wait_for_multiple_papers()
            
            if not success or paper_count == 0:
                # Timeout or error - return False
                return False
            
            logger.info(f"[PAPER] ✅ Multi-paper detection complete: {paper_count} paper(s)")
            
            # Send final real-time update
            if self.realtime and self.realtime.is_connected():
                self.realtime.send_transaction_update(self.current_transaction_id, "counting", {
                    "paperCount": paper_count,
                    "status": "counting_complete"
                })

            # State 5: Submit transaction to backend
            self.state = TransactionState.SUBMITTING

            # Use sync manager if available (offline mode), otherwise use direct API
            if self.sync:
                accepted, txn_data = self.sync.smart_submit_transaction(rfid_tag, paper_count)

                if not accepted:
                    self.state = TransactionState.REJECTED
                    reason = txn_data.get("reason", "Unknown reason")
                    logger.warning(f"Transaction rejected: {reason}")
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

                # Send real-time update: Transaction completed
                if self.realtime and self.realtime.is_connected():
                    self.realtime.send_transaction_update(self.current_transaction_id, "completed", {
                        "pointsAwarded": points_awarded,
                        "totalPoints": total_points,
                        "offline": txn_data.get("offline", False)
                    })

                self.hardware.led_off()  # Turn off red error LED
                self.hardware.set_ir_leds(False)  # Turn off IR sensor LEDs
                time.sleep(5)
                return True

            else:
                # Direct API submission (online only mode)
                success, txn_data = self.api.submit_transaction(rfid_tag, paper_count)

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
                    # State 6: Success
                    self.state = TransactionState.SUCCESS
                    points_awarded = transaction.get("pointsAwarded", 0)
                    total_points = transaction.get("totalPoints", current_points + points_awarded)

                    self.hardware.lcd_success(points_awarded, total_points)
                    self.hardware.led_off()
                    logger.info(f"Transaction successful! +{points_awarded} points")
                    
                    # Send real-time update: Transaction completed
                    if self.realtime and self.realtime.is_connected():
                        transaction_id = transaction.get("id", self.current_transaction_id)
                        self.realtime.send_transaction_update(transaction_id, "completed", {
                            "pointsAwarded": points_awarded,
                            "totalPoints": total_points
                        })
                    
                    time.sleep(5)
                    return True

                else:
                    # State 7: Rejected
                    self.state = TransactionState.REJECTED
                    reason = txn_data.get("reason", "Unknown reason")
                    logger.warning(f"Transaction rejected: {reason}")
                    self.hardware.lcd_rejected()

                    # Send real-time update: Transaction rejected
                    if self.realtime and self.realtime.is_connected():
                        transaction_id = txn_data.get("transactionId", self.current_transaction_id)
                        self.realtime.send_transaction_update(transaction_id, "rejected", {
                            "reason": reason
                        })

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
# HELPER FUNCTIONS
# ============================================

def extract_paper_count_from_reward_type(reward_type):
    """
    Extract number of papers from reward type string
    
    Args:
        reward_type: Reward type string (e.g., "Yellow Paper (1 sheet)", "Yellow Paper (5 sheets)")
    
    Returns:
        Number of papers (1 or 5), default 1 if cannot be determined
    """
    if not reward_type:
        logger.warning("Empty reward type - defaulting to 1 paper")
        return 1
    
    # Convert to lowercase for case-insensitive matching
    reward_lower = reward_type.lower()
    
    # Check for "5 sheets" or "5" patterns
    if "5 sheet" in reward_lower or " 5 " in reward_lower:
        return 5
    # Check for "1 sheet" or "1" patterns (default)
    elif "1 sheet" in reward_lower or " 1 " in reward_lower:
        return 1
    else:
        # Default to 1 if unclear
        logger.warning(f"Could not determine paper count from '{reward_type}' - defaulting to 1")
        return 1

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
                
                # Check IR sensor state periodically (log every 5 heartbeats)
                if not hasattr(self, '_heartbeat_count'):
                    self._heartbeat_count = 0
                self._heartbeat_count += 1
                
                # Log IR sensor state every 5 heartbeats (approximately every 25 seconds with default 5s interval)
                if self._heartbeat_count % 5 == 0:
                    try:
                        ir_state = self.hardware.check_paper_inserted()
                        logger.info(f"[IR] Periodic check - Paper detected: {ir_state}")
                    except Exception as e:
                        logger.error(f"[IR] Periodic check error: {e}")

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
# REDEMPTION HANDLER THREAD
# ============================================

class RedemptionHandlerThread(threading.Thread):
    """Background thread for processing redemption requests and dispensing papers"""

    def __init__(self, api_client, hardware):
        """Initialize redemption handler thread"""
        super().__init__(daemon=True)
        self.api = api_client
        self.hardware = hardware
        self.running = True
        # Thread-safe set to track currently processing redemptions (prevents double processing)
        self.processing_redemptions = set()
        self.processing_lock = threading.Lock()

    def run(self):
        """Run redemption polling loop"""
        logger.info("Redemption handler thread started")
        logger.info(f"Polling interval: {config.REDEMPTION_POLL_INTERVAL} seconds")
        
        poll_count = 0

        while self.running:
            try:
                poll_count += 1
                # Log polling activity every 10 polls (approximately every 50 seconds with 5s interval)
                if poll_count % 10 == 0:
                    logger.info(f"[REDEMPTION] Polling for pending redemptions... (poll #{poll_count})")
                
                # Poll for pending redemptions
                success, redemptions = self.api.get_pending_redemptions()

                if success and redemptions:
                    logger.info(f"[REDEMPTION] Processing {len(redemptions)} pending redemption(s)")

                    # Process each redemption (FIFO order)
                    for redemption in redemptions:
                        if not self.running:
                            break

                        redemption_id = redemption.get("id")
                        reward_type = redemption.get("rewardType", "")
                        user_id = redemption.get("userId", "")

                        # Check if this redemption is already being processed (thread-safe)
                        with self.processing_lock:
                            if redemption_id in self.processing_redemptions:
                                logger.warning(f"[REDEMPTION] ⚠️  Redemption {redemption_id} is already being processed - skipping to prevent double processing")
                                continue
                            # Mark as processing before starting
                            self.processing_redemptions.add(redemption_id)
                            logger.info(f"[REDEMPTION] 🔒 Locked redemption {redemption_id} for processing")

                        logger.info(f"[REDEMPTION] Processing redemption ID: {redemption_id}")
                        logger.info(f"[REDEMPTION] Reward: {reward_type}")
                        logger.info(f"[REDEMPTION] User: {user_id}")

                        # Extract paper count from reward type
                        paper_count = extract_paper_count_from_reward_type(reward_type)
                        logger.info(f"[REDEMPTION] Paper count: {paper_count}")

                        # Display redemption pending message on LCD
                        self.hardware.lcd_display(*config.LCD_MSG_REDEMPTION_PENDING)
                        time.sleep(1)

                        # Display dispensing message on LCD
                        msg = config.LCD_MSG_REDEMPTION_DISPENSING.copy()
                        msg[1] = msg[1].format(count=paper_count)
                        self.hardware.lcd_display(*msg)

                        # Dispense papers using synchronized servo rotation
                        # Run cycles based on paper count (1 paper = 1 cycle, 5 papers = 5 cycles)
                        success = self.hardware.dispense_synchronized(cycles=paper_count)

                        try:
                            if success:
                                # Mark redemption as dispensed in backend
                                if self.api.mark_redemption_dispensed(redemption_id):
                                    logger.info(f"[REDEMPTION] ✅ Successfully dispensed {paper_count} paper(s) for redemption {redemption_id}")
                                    # Display completion message
                                    msg = config.LCD_MSG_REDEMPTION_COMPLETE.copy()
                                    msg[1] = msg[1].format(count=paper_count)
                                    self.hardware.lcd_display(*msg)
                                    time.sleep(3)
                                    # Return to normal state (welcome screen)
                                    logger.info("[REDEMPTION] Returning to normal transaction state...")
                                    self.hardware.lcd_welcome()
                                else:
                                    logger.error(f"[REDEMPTION] Failed to mark redemption {redemption_id} as dispensed")
                                    self.hardware.lcd_error()
                                    time.sleep(2)
                                    # Return to normal state even on error
                                    self.hardware.lcd_welcome()
                            else:
                                logger.error(f"[REDEMPTION] Failed to dispense papers for redemption {redemption_id}")
                                self.hardware.lcd_error()
                                time.sleep(2)
                                # Return to normal state even on error
                                self.hardware.lcd_welcome()
                        finally:
                            # Always remove from processing set when done (thread-safe)
                            with self.processing_lock:
                                self.processing_redemptions.discard(redemption_id)
                                logger.info(f"[REDEMPTION] 🔓 Unlocked redemption {redemption_id}")

                        # Brief delay between redemptions
                        if self.running:
                            time.sleep(2)

                elif success and not redemptions:
                    # No pending redemptions - this is normal, don't log every time
                    # Only log periodically
                    if poll_count % 20 == 0:  # Log every 20 polls (~100 seconds)
                        logger.debug(f"[REDEMPTION] No pending redemptions (poll #{poll_count})")

                # Wait before next poll
                time.sleep(config.REDEMPTION_POLL_INTERVAL)

            except Exception as e:
                logger.error(f"[REDEMPTION] Redemption handler thread error: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(config.REDEMPTION_POLL_INTERVAL)

    def process_redemption_immediate(self, redemption_id, reward_type, user_id):
        """
        Process redemption immediately (called from Socket.io event)
        
        Args:
            redemption_id: Redemption record ID
            reward_type: Reward type string
            user_id: User ID
        """
        # Check if this redemption is already being processed (thread-safe)
        with self.processing_lock:
            if redemption_id in self.processing_redemptions:
                logger.warning(f"[REDEMPTION] ⚠️  Redemption {redemption_id} is already being processed - skipping to prevent double processing")
                return False
            # Mark as processing before starting
            self.processing_redemptions.add(redemption_id)
            logger.info(f"[REDEMPTION] 🔒 Locked redemption {redemption_id} for immediate processing")

        logger.info(f"[REDEMPTION] Processing immediate redemption ID: {redemption_id}")
        logger.info(f"[REDEMPTION] Reward: {reward_type}")
        logger.info(f"[REDEMPTION] User: {user_id}")

        # Extract paper count from reward type
        paper_count = extract_paper_count_from_reward_type(reward_type)
        logger.info(f"[REDEMPTION] Paper count: {paper_count}")

        # Display redemption pending message on LCD
        self.hardware.lcd_display(*config.LCD_MSG_REDEMPTION_PENDING)
        time.sleep(1)

        # Display dispensing message on LCD
        msg = config.LCD_MSG_REDEMPTION_DISPENSING.copy()
        msg[1] = msg[1].format(count=paper_count)
        self.hardware.lcd_display(*msg)

        try:
            # Dispense papers using synchronized servo rotation
            # Run cycles based on paper count (1 paper = 1 cycle, 5 papers = 5 cycles)
            success = self.hardware.dispense_synchronized(cycles=paper_count)

            if success:
                # Mark redemption as dispensed in backend
                if self.api.mark_redemption_dispensed(redemption_id):
                    logger.info(f"[REDEMPTION] ✅ Successfully dispensed {paper_count} paper(s) for redemption {redemption_id}")
                    # Display completion message
                    msg = config.LCD_MSG_REDEMPTION_COMPLETE.copy()
                    msg[1] = msg[1].format(count=paper_count)
                    self.hardware.lcd_display(*msg)
                    time.sleep(3)
                    # Return to normal state (welcome screen)
                    logger.info("[REDEMPTION] Returning to normal transaction state...")
                    self.hardware.lcd_welcome()
                    return True
                else:
                    logger.error(f"[REDEMPTION] Failed to mark redemption {redemption_id} as dispensed")
                    self.hardware.lcd_error()
                    time.sleep(2)
                    # Return to normal state even on error
                    self.hardware.lcd_welcome()
                    return False
            else:
                logger.error(f"[REDEMPTION] Failed to dispense papers for redemption {redemption_id}")
                self.hardware.lcd_error()
                time.sleep(2)
                # Return to normal state even on error
                self.hardware.lcd_welcome()
                return False
        finally:
            # Always remove from processing set when done (thread-safe)
            with self.processing_lock:
                self.processing_redemptions.discard(redemption_id)
                logger.info(f"[REDEMPTION] 🔓 Unlocked redemption {redemption_id}")

    def stop(self):
        """Stop redemption handler thread"""
        logger.info("Stopping redemption handler thread")
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
    redemption_thread = None
    db_manager = None
    sync_manager = None
    realtime_client = None
    realtime_stream_thread = None

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

            # Show database stats (with error handling)
            try:
                stats = db_manager.get_database_stats()
                if stats:
                    logger.info(f"Database stats: {stats.get('cached_users', 0)} users, {stats.get('pending_transactions', 0)} pending tx")
                else:
                    logger.warning("Could not retrieve database stats, continuing anyway...")
            except Exception as e:
                logger.error(f"Failed to get database stats: {e}")
                logger.info("Continuing with startup anyway...")

        # Initialize hardware
        hardware = HardwareManager()

        if not hardware.initialized:
            logger.error("Hardware initialization failed - exiting")
            sys.exit(1)

        # Initialize API client
        api_client = APIClient()

        # Initialize real-time client (if enabled)
        if REALTIME_AVAILABLE and config.REALTIME_ENABLED:
            logger.info("Initializing real-time WebSocket client...")
            try:
                realtime_client = RealtimeClient(hardware)
                
                # Set command callback
                def handle_admin_command(command, params, from_admin):
                    logger.info(f"Received admin command: {command} from {from_admin}")
                    # TODO: Implement command handling (restart, calibrate, etc.)
                    if command == "restart":
                        logger.warning("Restart command received - will restart after current transaction")
                    elif command == "calibrate":
                        logger.info("Calibration command received")
                        # TODO: Trigger calibration
                
                realtime_client.set_command_callback(handle_admin_command)
                
                # Note: Redemption callback will be set after redemption_thread is created
                
                # Connect
                if realtime_client.connect():
                    logger.info("[Realtime] Connected to backend WebSocket server")
                    
                    # Start streaming thread
                    realtime_stream_thread = RealtimeStreamingThread(
                        realtime_client,
                        hardware,
                        enabled=True
                    )
                    realtime_stream_thread.start()
                    logger.info("[Realtime] Streaming thread started")
                else:
                    logger.warning("[Realtime] Failed to connect - continuing without real-time features")
                    realtime_client = None
                    
            except Exception as e:
                logger.error(f"[Realtime] Initialization error: {e}")
                logger.warning("Continuing without real-time features")
                realtime_client = None

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

        # Start redemption handler thread
        logger.info("[REDEMPTION] Initializing redemption handler thread...")
        try:
            redemption_thread = RedemptionHandlerThread(api_client, hardware)
            logger.info("[REDEMPTION] RedemptionHandlerThread instance created")
            redemption_thread.start()
            logger.info("[REDEMPTION] ✅ Redemption handler thread started successfully")
            logger.info(f"[REDEMPTION] Thread name: {redemption_thread.name}, Thread ID: {redemption_thread.ident}")
        except Exception as e:
            logger.error(f"[REDEMPTION] ❌ Failed to start redemption handler thread: {e}")
            import traceback
            traceback.print_exc()
            redemption_thread = None
        
        # Set redemption callback for immediate processing via Socket.io (if realtime client is available)
        if realtime_client:
            logger.info("[REDEMPTION] Real-time client is available - setting up Socket.io callback...")
            if redemption_thread:
                def handle_immediate_redemption(redemption_id, reward_type, user_id):
                    """Handle immediate redemption dispense via Socket.io"""
                    logger.info(f"[REDEMPTION] ⚡ Immediate redemption received via Socket.io")
                    logger.info(f"[REDEMPTION] Processing redemption ID: {redemption_id}")
                    logger.info(f"[REDEMPTION] Reward: {reward_type}, User: {user_id}")
                    redemption_thread.process_redemption_immediate(redemption_id, reward_type, user_id)
                
                realtime_client.set_redemption_callback(handle_immediate_redemption)
                logger.info("[REDEMPTION] ✅ Redemption callback set for immediate processing via Socket.io")
                logger.info(f"[REDEMPTION] Callback function: {handle_immediate_redemption}")
            else:
                logger.error("[REDEMPTION] ❌ Cannot set callback - redemption thread is None!")
        else:
            logger.warning("[REDEMPTION] ⚠️  Real-time client not available - redemption will only work via polling")

        # Initialize transaction processor (with sync manager and realtime client if available)
        processor = TransactionProcessor(hardware, api_client, sync_manager, realtime_client)

        # Main loop
        logger.info("System ready - entering main loop")
        hardware.lcd_welcome()

        while True:
            try:
                # Process one transaction
                processor.process_transaction()

                # No delay - return immediately to RFID scanning (idle state)
                # The read_rfid() call will block until next card is detected

            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received")
                break

            except Exception as e:
                logger.error(f"Main loop error: {e}")
                hardware.lcd_error()
                time.sleep(2)  # Brief error display, then return to scanning

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

        if redemption_thread:
            redemption_thread.stop()
            redemption_thread.join(timeout=5)

        if realtime_stream_thread:
            realtime_stream_thread.stop()
            realtime_stream_thread.join(timeout=5)

        if realtime_client:
            realtime_client.disconnect()

        if db_manager:
            # Show final stats
            try:
                stats = db_manager.get_database_stats()
                if stats:
                    logger.info(f"Final database stats: {stats.get('pending_transactions', 0)} pending transactions")
            except Exception as e:
                logger.warning(f"Could not retrieve final database stats: {e}")
            db_manager.close()

        if hardware:
            hardware.cleanup()

        logger.info("Shutdown complete")

if __name__ == "__main__":
    main()
