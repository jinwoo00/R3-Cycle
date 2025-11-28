#!/usr/bin/env python3
"""
R3-Cycle Real-time WebSocket Client for Raspberry Pi
Connects to backend Socket.io server for real-time bidirectional communication

This module provides:
- Real-time sensor data streaming
- Bidirectional communication with backend
- Automatic reconnection handling
- Event-based messaging

Author: R3-Cycle Team
Last Updated: 2025-01-15
"""

import sys
import time
import logging
import threading
from datetime import datetime
from typing import Optional, Callable, Dict, Any

try:
    import socketio
except ImportError:
    print("[ERROR] python-socketio not installed. Run: pip3 install python-socketio")
    sys.exit(1)

# Import configuration
import config

logger = logging.getLogger(__name__)

# ============================================
# REAL-TIME CLIENT CLASS
# ============================================

class RealtimeClient:
    """
    WebSocket client for real-time communication with backend
    Uses Socket.io protocol for bidirectional messaging
    """

    def __init__(self, hardware_manager=None):
        """
        Initialize real-time client
        
        Args:
            hardware_manager: HardwareManager instance (optional)
        """
        self.hardware = hardware_manager
        self.machine_id = config.MACHINE_ID
        self.machine_secret = config.MACHINE_SECRET
        
        # Extract base URL (remove /api suffix if present)
        base_url = config.API_BASE_URL.replace("/api", "").replace("http://", "").replace("https://", "")
        self.socket_url = f"http://{base_url}"
        
        # Create Socket.io client
        self.sio = socketio.Client(
            logger=False,
            engineio_logger=False,
            reconnection=True,
            reconnection_attempts=10,
            reconnection_delay=1,
            reconnection_delay_max=5
        )
        
        self.connected = False
        self.registered = False
        
        # Scan request flag - when True, normal transaction loop should skip RFID reading
        self.scan_request_active = False
        self.scan_request_lock = threading.Lock()
        
        # Cooldown after successful scan to prevent spam
        self.scan_cooldown_until = 0  # Timestamp when cooldown expires
        
        # Event handlers
        self._setup_handlers()
        
        # Callbacks
        self.on_command_callback: Optional[Callable] = None
        self.on_redemption_callback: Optional[Callable] = None
        
        logger.info(f"Real-time client initialized for {self.socket_url}")

    def _setup_handlers(self):
        """Setup Socket.io event handlers"""
        
        @self.sio.event
        def connect():
            """Called when connection is established"""
            self.connected = True
            logger.info("[Socket] Connected to backend")
            
            # Wait a moment for connection to stabilize before registering
            time.sleep(0.5)
            
            # Register machine (with retry)
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    logger.info(f"[Socket] Registering machine: {self.machine_id} (attempt {attempt + 1}/{max_retries})")
                    self.sio.emit("machine:register", {
                        "machineId": self.machine_id,
                        "machineSecret": self.machine_secret
                    })
                    break  # Success, exit retry loop
                except Exception as e:
                    logger.warning(f"[Socket] Registration emit attempt {attempt + 1} failed: {e}")
                    if attempt < max_retries - 1:
                        time.sleep(1)  # Wait before retry
                    else:
                        logger.error(f"[Socket] Failed to emit registration after {max_retries} attempts")
        
        @self.sio.event
        def disconnect():
            """Called when disconnected"""
            self.connected = False
            self.registered = False
            logger.warning("[Socket] Disconnected from backend")
        
        @self.sio.on("machine:register:success")
        def on_register_success(data):
            """Called when machine registration succeeds"""
            self.registered = True
            logger.info(f"[Socket] Machine registered: {data.get('machineId')}")
        
        @self.sio.on("machine:register:error")
        def on_register_error(data):
            """Called when machine registration fails"""
            self.registered = False
            logger.error(f"[Socket] Registration failed: {data.get('message')}")
        
        @self.sio.on("machine:command")
        def on_command(data):
            """Called when admin sends command to machine"""
            command = data.get("command")
            params = data.get("params", {})
            from_admin = data.get("fromAdmin")
            
            logger.info(f"[Socket] Received command: {command} from admin {from_admin}")
            
            # Call callback if set
            if self.on_command_callback:
                try:
                    self.on_command_callback(command, params, from_admin)
                except Exception as e:
                    logger.error(f"[Socket] Command callback error: {e}")
        
        @self.sio.on("redemption:dispense")
        def on_redemption_dispense(data):
            """Called when redemption needs to be dispensed immediately"""
            logger.info("=" * 60)
            logger.info("[Socket] ⚡ REDEMPTION DISPENSE EVENT RECEIVED!")
            logger.info("=" * 60)
            logger.info(f"[Socket] Event data: {data}")
            logger.info(f"[Socket] Event data type: {type(data)}")
            
            redemption_id = data.get("redemptionId") if isinstance(data, dict) else None
            reward_type = data.get("rewardType", "") if isinstance(data, dict) else ""
            user_id = data.get("userId", "") if isinstance(data, dict) else ""
            
            logger.info(f"[Socket] ✅ Received immediate redemption dispense request")
            logger.info(f"[Socket] Redemption ID: {redemption_id}")
            logger.info(f"[Socket] Reward: {reward_type}")
            logger.info(f"[Socket] User: {user_id}")
            
            # Call redemption callback if set
            if self.on_redemption_callback:
                logger.info(f"[Socket] ✅ Redemption callback IS SET - calling handler...")
                logger.info(f"[Socket] Callback function: {self.on_redemption_callback}")
                try:
                    self.on_redemption_callback(redemption_id, reward_type, user_id)
                    logger.info(f"[Socket] ✅ Redemption callback executed successfully")
                    logger.info("=" * 60)
                except Exception as e:
                    logger.error(f"[Socket] ❌ Redemption callback error: {e}")
                    import traceback
                    logger.error(f"[Socket] Callback error traceback:\n{traceback.format_exc()}")
                    logger.info("=" * 60)
                    # Send error response
                    self.sio.emit("redemption:dispense:error", {
                        "redemptionId": redemption_id,
                        "error": str(e)
                    })
            else:
                logger.error("[Socket] ❌ NO REDEMPTION CALLBACK SET!")
                logger.error("[Socket] Callback status: on_redemption_callback is None")
                logger.error("[Socket] This means the redemption handler was not properly initialized")
                logger.info("=" * 60)
                self.sio.emit("redemption:dispense:error", {
                    "redemptionId": redemption_id,
                    "error": "No redemption handler configured"
                })
        
        @self.sio.on("rfid:scan_request")
        def on_rfid_scan_request(data):
            """Handle RFID scan request from web registration"""
            request_id = data.get("requestId")
            timeout = data.get("timeout", 30000) / 1000  # Convert milliseconds to seconds
            source = data.get("source", "unknown")
            
            logger.info(f"[Socket] RFID scan requested: requestId={request_id}, source={source}, timeout={timeout}s")
            logger.info("[Socket] ⚠️  SCAN REQUEST ACTIVE - Normal transaction flow will pause")
            
            # Set scan request flag to pause normal transaction loop
            with self.scan_request_lock:
                self.scan_request_active = True
            
            # Run scan in separate thread to avoid blocking
            def scan_thread():
                try:
                    if not self.hardware or not self.hardware.rfid_reader:
                        logger.error("[Socket] RFID reader not available")
                        with self.scan_request_lock:
                            self.scan_request_active = False
                        self.sio.emit("rfid:scan_result", {
                            "requestId": request_id,
                            "success": False,
                            "message": "RFID reader not available"
                        })
                        return
                    
                    logger.info(f"[Socket] ⚠️  SCAN REQUEST ACTIVE - Normal transactions paused")
                    logger.info(f"[Socket] Starting RFID scan for registration (timeout: {timeout}s)...")
                    logger.info("[Socket] Place your RFID card near the reader NOW...")
                    
                    # Wait a brief moment to ensure normal transaction loop has aborted
                    # This prevents race condition where normal transaction might be reading
                    time.sleep(0.5)
                    
                    # Show message on LCD that scan is active
                    if self.hardware:
                        try:
                            self.hardware.lcd_display("Scanning for", "Registration...")
                            time.sleep(0.3)  # Give LCD time to update
                        except:
                            pass
                    
                    # Read RFID with timeout (using same pattern as working standalone code)
                    # Don't pass check_scan_request - we want exclusive access during scan
                    # The normal transaction loop will check the flag and abort
                    logger.info(f"[Socket] Calling read_rfid with timeout {timeout}s (exclusive scan mode)")
                    rfid_tag, rfid_text = self.hardware.read_rfid(timeout=timeout, check_scan_request=None)
                    logger.info(f"[Socket] read_rfid returned: tag={rfid_tag}, text={rfid_text}")
                    
                    # Clear scan request flag
                    with self.scan_request_lock:
                        self.scan_request_active = False
                    
                    # Check if card was detected (matching working code pattern)
                    if rfid_tag and rfid_tag != "None":
                        logger.info(f"[Socket] ✅ RFID detected for registration: {rfid_tag}")
                        
                        # Show success message on LCD - ONLY "Card detected" message
                        # NO "Card not found" message should appear after this
                        if self.hardware:
                            try:
                                self.hardware.lcd_display("Scan success", "Card detected")
                                time.sleep(3)  # Show message for 3 seconds - user should remove card
                            except:
                                pass
                        
                        # Set cooldown period to prevent normal transaction from reading same card immediately
                        # Longer cooldown ensures card is removed before normal transaction resumes
                        # This prevents "Card not found" message from appearing after registration scan
                        cooldown_duration = 6  # 6 seconds cooldown
                        with self.scan_request_lock:
                            self.scan_cooldown_until = time.time() + cooldown_duration
                        logger.info(f"[Socket] Cooldown set for {cooldown_duration} seconds - prevents normal transaction from reading same card")
                        logger.info(f"[Socket] This ensures NO 'Card not found' message appears after registration scan")
                        
                        # Send result to web
                        self.sio.emit("rfid:scan_result", {
                            "requestId": request_id,
                            "rfidTag": str(rfid_tag),
                            "success": True,
                            "message": "RFID card scanned successfully"
                        })
                        
                        logger.info(f"[Socket] ✅ Scan result sent to web - registration scan complete")
                        logger.info(f"[Socket] Normal transaction will NOT process this card (cooldown active)")
                    else:
                        logger.warning("[Socket] No RFID card detected or AUTH error")
                        
                        # Show error message on LCD
                        if self.hardware:
                            try:
                                self.hardware.lcd_display("Scan Failed", "Try again...")
                                time.sleep(2)  # Show error message for 2 seconds
                            except:
                                pass
                        
                        self.sio.emit("rfid:scan_result", {
                            "requestId": request_id,
                            "success": False,
                            "message": "No RFID card detected. Please hold card closer and try again."
                        })
                    
                    # Return to welcome message after showing result
                    # Wait longer to ensure card is removed before normal transaction resumes
                    if self.hardware:
                        try:
                            time.sleep(2)  # Wait 2 seconds before returning to welcome
                            logger.info("[Socket] Returning to welcome screen - normal transactions will resume after cooldown")
                            self.hardware.lcd_welcome()
                        except:
                            pass
                        
                except Exception as e:
                    logger.error(f"[Socket] RFID scan error: {e}", exc_info=True)
                    # Clear scan request flag on error
                    with self.scan_request_lock:
                        self.scan_request_active = False
                    self.sio.emit("rfid:scan_result", {
                        "requestId": request_id,
                        "success": False,
                        "message": f"Scan failed: {str(e)}"
                    })
            
            # Start scan in background thread
            threading.Thread(target=scan_thread, daemon=True).start()
        
        @self.sio.on("rfid:scan_cancel")
        def on_rfid_scan_cancel(data):
            """Handle RFID scan cancellation"""
            request_id = data.get("requestId")
            logger.info(f"[Socket] RFID scan cancelled: requestId={request_id}")
            # Clear scan request flag
            with self.scan_request_lock:
                self.scan_request_active = False
            logger.info("[Socket] Scan request cancelled - normal transaction flow resumed")
        
        @self.sio.on("pong")
        def on_pong(data):
            """Called when server responds to ping"""
            logger.debug("[Socket] Received pong")

    def connect(self):
        """
        Connect to backend Socket.io server
        
        Returns:
            bool: True if connected, False otherwise
        """
        try:
            logger.info(f"[Socket] Connecting to {self.socket_url}...")
            
            # Check if already connected
            if self.sio.connected:
                logger.warning("[Socket] Already connected, disconnecting first...")
                self.sio.disconnect()
                time.sleep(1)
            
            # Try to connect with error handling
            try:
                self.sio.connect(self.socket_url, wait_timeout=10)
                logger.info("[Socket] Socket.io connection attempt completed")
            except Exception as conn_err:
                error_msg = str(conn_err)
                logger.error(f"[Socket] Connection error: {error_msg}")
                
                # If it's a namespace error, the connection might still be partially established
                if "namespace" in error_msg.lower() or "failed to connect" in error_msg.lower():
                    logger.warning("[Socket] Namespace connection issue detected, checking connection status...")
                    # Wait a bit and check if we're actually connected
                    time.sleep(2)
                    if hasattr(self.sio, 'connected') and self.sio.connected:
                        logger.info("[Socket] Connection is active despite namespace error")
                    else:
                        logger.error("[Socket] Connection failed completely")
                        return False
                else:
                    return False
            
            # Wait for connection and registration (increased timeout)
            timeout = time.time() + 15
            while time.time() < timeout:
                if self.connected:
                    if self.registered:
                        logger.info("[Socket] Successfully connected and registered")
                        return True
                    else:
                        # Connected but not registered yet - wait a bit more
                        logger.debug("[Socket] Connected, waiting for registration...")
                time.sleep(0.5)
            
            if self.connected and self.registered:
                logger.info("[Socket] Successfully connected and registered")
                return True
            else:
                if self.connected:
                    logger.error("[Socket] Connected but registration timeout - machine not registered")
                else:
                    logger.error("[Socket] Connection timeout - not connected")
                return False
                
        except Exception as e:
            logger.error(f"[Socket] Connection error: {e}", exc_info=True)
            return False

    def disconnect(self):
        """Disconnect from server"""
        try:
            if self.sio.connected:
                self.sio.disconnect()
            self.connected = False
            self.registered = False
            logger.info("[Socket] Disconnected")
        except Exception as e:
            logger.error(f"[Socket] Disconnect error: {e}")

    def is_connected(self):
        """Check if connected and registered"""
        return self.connected and self.registered

    # ========================================
    # SENSOR DATA STREAMING
    # ========================================

    def send_sensor_data(self, sensor_type: str, value: Any, timestamp: Optional[str] = None):
        """
        Send real-time sensor data to backend
        
        Args:
            sensor_type: Type of sensor ("rfid", "loadCell", "ir", "inductive", "servo")
            value: Sensor reading value
            timestamp: ISO timestamp (optional, auto-generated if None)
        """
        if not self.is_connected():
            logger.warning("[Socket] Not connected, cannot send sensor data")
            return False

        try:
            data = {
                "machineId": self.machine_id,
                "sensorType": sensor_type,
                "value": value,
                "timestamp": timestamp or datetime.now().isoformat()
            }
            
            self.sio.emit("sensor:data", data)
            logger.debug(f"[Socket] Sent sensor data: {sensor_type} = {value}")
            return True
            
        except Exception as e:
            logger.error(f"[Socket] Error sending sensor data: {e}")
            return False

    def send_rfid_detected(self, rfid_tag: str):
        """Send RFID card detected event"""
        return self.send_sensor_data("rfid", {
            "tag": rfid_tag,
            "event": "detected"
        })

    def send_weight_reading(self, weight: float):
        """Send load cell weight reading"""
        return self.send_sensor_data("loadCell", {
            "weight": weight,
            "unit": "grams"
        })

    def send_ir_sensor_state(self, detected: bool):
        """Send IR sensor state (paper detected/not detected)"""
        state = "paper_inserted" if detected else "no_paper"
        logger.info(f"[IR] Sending IR sensor state to backend: {state} (detected={detected})")
        return self.send_sensor_data("ir", {
            "detected": detected,
            "state": state
        })

    def send_metal_detection(self, detected: bool):
        """Send inductive sensor metal detection"""
        return self.send_sensor_data("inductive", {
            "detected": detected,
            "state": "metal_detected" if detected else "no_metal"
        })

    # ========================================
    # TRANSACTION UPDATES
    # ========================================

    def send_transaction_update(self, transaction_id: str, status: str, details: Dict[str, Any] = None):
        """
        Send transaction status update
        
        Args:
            transaction_id: Transaction identifier
            status: Status ("started", "weighing", "checking", "completed", "rejected")
            details: Additional transaction details
        """
        if not self.is_connected():
            return False

        try:
            data = {
                "machineId": self.machine_id,
                "transactionId": transaction_id,
                "status": status,
                "details": details or {},
                "timestamp": datetime.now().isoformat()
            }
            
            self.sio.emit("transaction:update", data)
            logger.debug(f"[Socket] Sent transaction update: {transaction_id} - {status}")
            return True
            
        except Exception as e:
            logger.error(f"[Socket] Error sending transaction update: {e}")
            return False

    # ========================================
    # MACHINE STATUS
    # ========================================

    def send_machine_status(self, status: str, sensor_health: Dict[str, str] = None, bond_paper_stock: int = None):
        """
        Send machine status update
        
        Args:
            status: Machine status ("online", "offline", "error")
            sensor_health: Sensor health status dictionary
            bond_paper_stock: Current bond paper stock level
        """
        if not self.is_connected():
            return False

        try:
            data = {
                "machineId": self.machine_id,
                "status": status,
                "sensorHealth": sensor_health or {},
                "bondPaperStock": bond_paper_stock,
                "timestamp": datetime.now().isoformat()
            }
            
            self.sio.emit("machine:status", data)
            logger.debug(f"[Socket] Sent machine status: {status}")
            return True
            
        except Exception as e:
            logger.error(f"[Socket] Error sending machine status: {e}")
            return False

    # ========================================
    # COMMAND HANDLING
    # ========================================

    def set_command_callback(self, callback: Callable):
        """
        Set callback function for handling admin commands
        
        Args:
            callback: Function that takes (command, params, from_admin) as arguments
        """
        self.on_command_callback = callback

    def set_redemption_callback(self, callback: Callable):
        """
        Set callback function for handling immediate redemption dispense
        
        Args:
            callback: Function that takes (redemption_id, reward_type, user_id) as arguments
        """
        logger.info("[Socket] Setting redemption callback...")
        logger.info(f"[Socket] Callback function: {callback}")
        self.on_redemption_callback = callback
        logger.info(f"[Socket] ✅ Redemption callback set successfully")
        logger.info(f"[Socket] Callback verification: {self.on_redemption_callback is not None}")

    def send_ping(self):
        """Send ping to server for connection health check"""
        if self.is_connected():
            try:
                self.sio.emit("ping")
            except Exception as e:
                logger.error(f"[Socket] Ping error: {e}")

# ============================================
# REALTIME STREAMING THREAD
# ============================================

class RealtimeStreamingThread(threading.Thread):
    """
    Background thread for streaming sensor data in real-time
    Continuously reads sensors and sends data via WebSocket
    """

    def __init__(self, realtime_client: RealtimeClient, hardware_manager, enabled: bool = True):
        """
        Initialize streaming thread
        
        Args:
            realtime_client: RealtimeClient instance
            hardware_manager: HardwareManager instance
            enabled: Whether streaming is enabled
        """
        super().__init__(daemon=True)
        self.client = realtime_client
        self.hardware = hardware_manager
        self.enabled = enabled
        self.running = False
        self.stream_interval = 2.0  # Stream every 2 seconds

    def run(self):
        """Run streaming loop"""
        logger.info("[RealtimeStream] Streaming thread started")
        self.running = True

        while self.running and self.enabled:
            try:
                # Wait for connection
                if not self.client.is_connected():
                    time.sleep(5)
                    continue

                # Send sensor health status
                if self.hardware:
                    sensor_health = self.hardware.check_sensor_health()
                    self.client.send_machine_status(
                        status="online",
                        sensor_health=sensor_health
                    )

                # Stream sensor readings if hardware available
                if self.hardware:
                    # IR sensor state
                    ir_detected = self.hardware.check_paper_inserted()
                    logger.debug(f"[IR] Stream check - Paper detected: {ir_detected}")
                    self.client.send_ir_sensor_state(ir_detected)

                    # Metal detection removed - using signage warning instead
                    # No need to check metal detection

                # Sleep before next stream
                time.sleep(self.stream_interval)

            except Exception as e:
                logger.error(f"[RealtimeStream] Streaming error: {e}")
                time.sleep(self.stream_interval)

        logger.info("[RealtimeStream] Streaming thread stopped")

    def stop(self):
        """Stop streaming thread"""
        logger.info("[RealtimeStream] Stopping streaming thread")
        self.running = False

# ============================================
# USAGE EXAMPLE
# ============================================

if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    client = RealtimeClient()
    
    # Connect
    if client.connect():
        print("Connected! Sending test data...")
        
        # Send test sensor data
        client.send_rfid_detected("1234567890")
        time.sleep(1)
        client.send_weight_reading(5.5)
        time.sleep(1)
        client.send_ir_sensor_state(True)
        time.sleep(1)
        client.send_metal_detection(False)
        time.sleep(1)
        client.send_transaction_update("txn_123", "completed", {"points": 5})
        
        # Keep connection alive
        time.sleep(10)
        
        client.disconnect()
    else:
        print("Failed to connect")
