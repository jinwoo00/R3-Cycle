/**
 * Socket.io Real-time Server for R3-Cycle
 * 
 * Handles real-time bidirectional communication between:
 * - Raspberry Pi devices (hardware sensors)
 * - Web dashboard (admin monitoring)
 * 
 * @module socket/socketServer
 */

import { Server } from "socket.io";

/**
 * Initialize Socket.io server
 * @param {Object} httpServer - HTTP server instance from Express
 * @returns {Object} Socket.io server instance
 */
export function initializeSocket(httpServer) {
  const io = new Server(httpServer, {
    cors: {
      origin: "*", // TODO: Restrict in production
      methods: ["GET", "POST"],
      credentials: true
    },
    transports: ["websocket", "polling"]
  });

  // Store connected machines and admins
  const connectedMachines = new Map(); // machineId -> socketId
  const connectedAdmins = new Set(); // socketIds

  io.on("connection", (socket) => {
    console.log(`[Socket] New connection: ${socket.id} from ${socket.handshake.address}`);
    console.log(`[DEBUG] Setting up handlers for socket ${socket.id}`);
    
    // Debug: Log all events received (temporary for debugging)
    socket.onAny((eventName, ...args) => {
      console.log(`[DEBUG] Socket ${socket.id} received event: ${eventName}`, args.length > 0 ? JSON.stringify(args[0]) : '');
    });
    
    // Test connection handler (for debugging)
    socket.on("test_connection", (data) => {
      console.log(`[DEBUG] Test connection received from ${socket.id}:`, data);
      socket.emit("test_connection_response", { 
        message: "Connection test successful",
        socketId: socket.id,
        timestamp: new Date().toISOString()
      });
    });

    // ============================================
    // MACHINE REGISTRATION (Raspberry Pi)
    // ============================================
    socket.on("machine:register", (data) => {
      try {
        const { machineId, machineSecret } = data;

        // TODO: Validate machineSecret against database
        if (!machineId || !machineSecret) {
          socket.emit("machine:register:error", {
            message: "Machine ID and Secret required"
          });
          return;
        }

        // Register machine
        socket.machineId = machineId;
        connectedMachines.set(machineId, socket.id);
        socket.join(`machine:${machineId}`);
        socket.join("machines"); // Broadcast room

        console.log(`[Socket] Machine registered: ${machineId} (${socket.id})`);

        socket.emit("machine:register:success", {
          machineId: machineId,
          message: "Machine registered successfully"
        });

        // Notify admins about new machine connection
        io.to("admins").emit("machine:connected", {
          machineId: machineId,
          timestamp: new Date().toISOString()
        });

      } catch (error) {
        console.error("[Socket] Machine registration error:", error);
        socket.emit("machine:register:error", {
          message: "Registration failed"
        });
      }
    });

    // ============================================
    // REAL-TIME SENSOR DATA (Raspberry Pi → Backend)
    // ============================================
    socket.on("sensor:data", (data) => {
      try {
        const { machineId, sensorType, value, timestamp } = data;

        if (!machineId || !sensorType) {
          return;
        }

        // Validate machine is registered
        if (!socket.machineId || socket.machineId !== machineId) {
          socket.emit("sensor:data:error", {
            message: "Machine not registered"
          });
          return;
        }

        // Broadcast sensor data to admins
        io.to("admins").emit("sensor:data:update", {
          machineId: machineId,
          sensorType: sensorType, // "rfid", "loadCell", "ir", "inductive", "servo"
          value: value,
          timestamp: timestamp || new Date().toISOString()
        });

        console.log(`[Socket] Sensor data from ${machineId}: ${sensorType} = ${value}`);

      } catch (error) {
        console.error("[Socket] Sensor data error:", error);
      }
    });

    // ============================================
    // TRANSACTION UPDATE (Raspberry Pi → Backend)
    // ============================================
    socket.on("transaction:update", (data) => {
      try {
        const { machineId, transactionId, status, details } = data;

        if (!machineId || !transactionId) {
          return;
        }

        // Broadcast transaction update to admins
        io.to("admins").emit("transaction:update:real-time", {
          machineId: machineId,
          transactionId: transactionId,
          status: status, // "started", "weighing", "checking", "completed", "rejected"
          details: details,
          timestamp: new Date().toISOString()
        });

        console.log(`[Socket] Transaction update from ${machineId}: ${transactionId} - ${status}`);

      } catch (error) {
        console.error("[Socket] Transaction update error:", error);
      }
    });

    // ============================================
    // MACHINE STATUS UPDATE (Raspberry Pi → Backend)
    // ============================================
    socket.on("machine:status", (data) => {
      try {
        const { machineId, status, sensorHealth, bondPaperStock } = data;

        if (!machineId) {
          return;
        }

        // Broadcast machine status to admins
        io.to("admins").emit("machine:status:update", {
          machineId: machineId,
          status: status, // "online", "offline", "error"
          sensorHealth: sensorHealth,
          bondPaperStock: bondPaperStock,
          timestamp: new Date().toISOString()
        });

      } catch (error) {
        console.error("[Socket] Machine status error:", error);
      }
    });

    // ============================================
    // USER REGISTRATION (Web Dashboard - User)
    // ============================================
    socket.on("user:register", (data) => {
      try {
        const { userId } = data;

        if (!userId) {
          socket.emit("user:register:error", {
            message: "User ID required"
          });
          return;
        }

        socket.userId = userId;
        socket.join(`user:${userId}`);

        console.log(`[Socket] User registered: ${userId} (${socket.id})`);

        socket.emit("user:register:success", {
          userId: userId,
          message: "User registered successfully"
        });

      } catch (error) {
        console.error("[Socket] User registration error:", error);
        socket.emit("user:register:error", {
          message: "Registration failed"
        });
      }
    });

    // ============================================
    // ADMIN REGISTRATION (Web Dashboard)
    // ============================================
    socket.on("admin:register", (data) => {
      try {
        // TODO: Validate admin session/token
        const { adminId } = data;

        if (!adminId) {
          socket.emit("admin:register:error", {
            message: "Admin ID required"
          });
          return;
        }

        socket.adminId = adminId;
        socket.join("admins");
        connectedAdmins.add(socket.id);

        console.log(`[Socket] Admin registered: ${adminId} (${socket.id})`);

        socket.emit("admin:register:success", {
          adminId: adminId,
          message: "Admin registered successfully"
        });

        // Send list of connected machines
        const machines = Array.from(connectedMachines.keys());
        socket.emit("machine:list", {
          machines: machines
        });

      } catch (error) {
        console.error("[Socket] Admin registration error:", error);
        socket.emit("admin:register:error", {
          message: "Registration failed"
        });
      }
    });

    // ============================================
    // ADMIN COMMANDS (Web Dashboard → Raspberry Pi)
    // ============================================
    socket.on("admin:command", (data) => {
      try {
        const { machineId, command, params } = data;

        if (!socket.adminId) {
          socket.emit("admin:command:error", {
            message: "Admin not authenticated"
          });
          return;
        }

        if (!machineId || !command) {
          socket.emit("admin:command:error", {
            message: "Machine ID and command required"
          });
          return;
        }

        // Forward command to specific machine
        const machineSocketId = connectedMachines.get(machineId);
        if (machineSocketId) {
          io.to(machineSocketId).emit("machine:command", {
            command: command, // "restart", "calibrate", "test_sensor", etc.
            params: params,
            fromAdmin: socket.adminId
          });

          socket.emit("admin:command:success", {
            machineId: machineId,
            command: command,
            message: "Command sent to machine"
          });
        } else {
          socket.emit("admin:command:error", {
            message: `Machine ${machineId} not connected`
          });
        }

      } catch (error) {
        console.error("[Socket] Admin command error:", error);
        socket.emit("admin:command:error", {
          message: "Command failed"
        });
      }
    });

    // ============================================
    // DISCONNECTION HANDLING
    // ============================================
    socket.on("disconnect", () => {
      console.log(`[Socket] Disconnected: ${socket.id}`);

      // Remove machine from connected list
      if (socket.machineId) {
        connectedMachines.delete(socket.machineId);
        io.to("admins").emit("machine:disconnected", {
          machineId: socket.machineId,
          timestamp: new Date().toISOString()
        });
        console.log(`[Socket] Machine disconnected: ${socket.machineId}`);
      }

      // Remove admin from connected list
      if (socket.adminId) {
        connectedAdmins.delete(socket.id);
        console.log(`[Socket] Admin disconnected: ${socket.adminId}`);
      }

      // Remove user room (automatic on disconnect)
      if (socket.userId) {
        console.log(`[Socket] User disconnected: ${socket.userId}`);
      }
    });

    // ============================================
    // RFID SCAN REQUEST (Web Registration → Backend → Raspberry Pi)
    // ============================================
    console.log(`[DEBUG] Registering request_rfid_scan handler for socket ${socket.id}`);
    
    // Test handler registration immediately
    socket.on("request_rfid_scan", async (data) => {
      console.log("[DEBUG] ============================================================");
      console.log("[DEBUG] request_rfid_scan HANDLER TRIGGERED!");
      console.log("[DEBUG] ============================================================");
      console.log("=".repeat(60));
      console.log("[DEBUG] request_rfid_scan EVENT RECEIVED!");
      console.log("[DEBUG] Socket ID:", socket.id);
      console.log("[DEBUG] Data received:", JSON.stringify(data));
      console.log("[DEBUG] Connected machines:", connectedMachines.size);
      console.log("[DEBUG] Machine entries:", Array.from(connectedMachines.entries()));
      console.log("=".repeat(60));
      
      try {
        const { source, timeout } = data || {};
        
        console.log(`[Socket] RFID scan requested from ${socket.id} (source: ${source || 'unknown'})`);
        console.log(`[Socket] Connected machines: ${connectedMachines.size}`);

        // Check if any machine is connected
        console.log(`[DEBUG] Checking connected machines: ${connectedMachines.size} total`);
        console.log(`[DEBUG] Connected machine IDs: ${Array.from(connectedMachines.keys()).join(', ') || 'none'}`);
        console.log(`[DEBUG] Connected machine entries:`, Array.from(connectedMachines.entries()));
        
        if (connectedMachines.size === 0) {
          console.warn(`[Socket] No machines connected. Available machines: ${Array.from(connectedMachines.keys()).join(', ') || 'none'}`);
          socket.emit("rfid_scan_result", {
            success: false,
            message: "No Raspberry Pi machines are connected. Please ensure a machine is online."
          });
          return;
        }

        // Get first available machine (or can be improved to select specific machine)
        const firstMachineId = connectedMachines.keys().next().value;
        const machineSocketId = connectedMachines.get(firstMachineId);

        if (!machineSocketId) {
          socket.emit("rfid_scan_result", {
            success: false,
            message: "Machine is not available for scanning"
          });
          return;
        }

        // Forward scan request to Raspberry Pi
        console.log(`[Socket] Forwarding RFID scan request to machine ${firstMachineId} (socket: ${machineSocketId})`);
        io.to(machineSocketId).emit("rfid:scan_request", {
          requestId: socket.id,
          source: source || "web",
          timeout: timeout || 30000
        });

        // Store pending scan request
        socket.pendingRfidScan = {
          requestId: socket.id,
          machineId: firstMachineId,
          timestamp: Date.now(),
          timeout: setTimeout(() => {
            console.warn(`[Socket] RFID scan timeout for request ${socket.id}`);
            socket.emit("rfid_scan_result", {
              success: false,
              message: "RFID scan timeout. Please try again."
            });
            delete socket.pendingRfidScan;
          }, timeout || 30000)
        };

        console.log(`[Socket] RFID scan request forwarded to machine ${firstMachineId}, waiting for response...`);

      } catch (error) {
        console.error("[Socket] RFID scan request error:", error);
        socket.emit("rfid_scan_result", {
          success: false,
          message: "Failed to request RFID scan"
        });
      }
    });

    // ============================================
    // RFID SCAN RESULT (Raspberry Pi → Backend → Web)
    // ============================================
    socket.on("rfid:scan_result", (data) => {
      try {
        const { requestId, rfidTag, success, message } = data;

        if (!requestId) {
          console.error("[Socket] RFID scan result missing requestId");
          return;
        }

        // Find the requesting socket and send result
        const requestingSocket = io.sockets.sockets.get(requestId);
        if (requestingSocket) {
          // Clear timeout
          if (requestingSocket.pendingRfidScan && requestingSocket.pendingRfidScan.timeout) {
            clearTimeout(requestingSocket.pendingRfidScan.timeout);
          }

          requestingSocket.emit("rfid_scan_result", {
            success: success || false,
            rfidTag: rfidTag || null,
            message: message || (success ? "RFID card scanned successfully" : "RFID scan failed")
          });

          delete requestingSocket.pendingRfidScan;

          console.log(`[Socket] RFID scan result sent to ${requestId}: ${rfidTag || 'none'}`);
        } else {
          console.warn(`[Socket] Requesting socket ${requestId} not found for RFID scan result`);
        }

      } catch (error) {
        console.error("[Socket] RFID scan result error:", error);
      }
    });

    // ============================================
    // CANCEL RFID SCAN
    // ============================================
    socket.on("cancel_rfid_scan", () => {
      if (socket.pendingRfidScan) {
        if (socket.pendingRfidScan.timeout) {
          clearTimeout(socket.pendingRfidScan.timeout);
        }

        // Notify machine to cancel scan
        const machineSocketId = connectedMachines.get(socket.pendingRfidScan.machineId);
        if (machineSocketId) {
          io.to(machineSocketId).emit("rfid:scan_cancel", {
            requestId: socket.id
          });
        }

        delete socket.pendingRfidScan;
        console.log(`[Socket] RFID scan cancelled for ${socket.id}`);
      }
    });

    // ============================================
    // PING/PONG for connection health
    // ============================================
    socket.on("ping", () => {
      socket.emit("pong", {
        timestamp: new Date().toISOString()
      });
    });
  });

  // Log server status
  console.log("[Socket] Socket.io server initialized");

  return io;
}

export default initializeSocket;
