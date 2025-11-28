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
        
        # Event handlers
        self._setup_handlers()
        
        # Callbacks
        self.on_command_callback: Optional[Callable] = None
        
        logger.info(f"Real-time client initialized for {self.socket_url}")

    def _setup_handlers(self):
        """Setup Socket.io event handlers"""
        
        @self.sio.event
        def connect():
            """Called when connection is established"""
            self.connected = True
            logger.info("[Socket] Connected to backend")
            
            # Register machine
            self.sio.emit("machine:register", {
                "machineId": self.machine_id,
                "machineSecret": self.machine_secret
            })
        
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
            self.sio.connect(self.socket_url)
            
            # Wait for connection and registration
            timeout = time.time() + 10
            while not (self.connected and self.registered) and time.time() < timeout:
                time.sleep(0.5)
            
            if self.connected and self.registered:
                logger.info("[Socket] Successfully connected and registered")
                return True
            else:
                logger.error("[Socket] Connection timeout")
                return False
                
        except Exception as e:
            logger.error(f"[Socket] Connection error: {e}")
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
        return self.send_sensor_data("ir", {
            "detected": detected,
            "state": "paper_inserted" if detected else "no_paper"
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
                    self.client.send_ir_sensor_state(ir_detected)

                    # Metal detection
                    metal_detected = self.hardware.check_metal_detected()
                    self.client.send_metal_detection(metal_detected)

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
