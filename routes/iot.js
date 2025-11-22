/**
 * IoT API Routes for R3-Cycle Raspberry Pi Integration
 *
 * All routes are prefixed with /api
 * Example: /api/rfid/verify, /api/transaction/submit
 *
 * @module routes/iot
 */

import express from "express";
import {
  verifyRfid,
  submitTransaction,
  machineHeartbeat,
  getUserStats,
  registerRfid,
  unlinkRfid,
  getUserTransactions,
  submitRedemption,
  markRedemptionDispensed,
  getPendingRedemptions
} from "../controllers/iotController.js";

import {
  getAllMachines,
  getAllTransactions,
  getSystemStats,
  adjustUserPoints,
  dismissAlert
} from "../controllers/adminController.js";

const router = express.Router();

// ============================================
// MACHINE AUTHENTICATION MIDDLEWARE
// ============================================

/**
 * Middleware to authenticate Raspberry Pi machines
 * Checks X-Machine-ID and X-Machine-Secret headers
 *
 * TODO: Implement proper machine authentication in Phase 6
 * For now, just validates headers are present
 */
const authenticateMachine = (req, res, next) => {
  const machineId = req.headers['x-machine-id'];
  const machineSecret = req.headers['x-machine-secret'];

  if (!machineId) {
    return res.status(401).json({
      success: false,
      message: "Machine ID required in X-Machine-ID header"
    });
  }

  // TODO: Validate machineSecret against database
  // For Phase 1, just check it exists
  if (!machineSecret) {
    return res.status(401).json({
      success: false,
      message: "Machine secret required in X-Machine-Secret header"
    });
  }

  // Machine is authenticated
  next();
};

/**
 * Middleware to check if user is authenticated (has session)
 */
const requireAuth = (req, res, next) => {
  if (!req.session?.userId) {
    return res.status(401).json({
      success: false,
      message: "Authentication required"
    });
  }
  next();
};

/**
 * Middleware to check if user is admin
 */
const requireAdmin = (req, res, next) => {
  if (!req.session?.userId || req.session?.userRole !== "admin") {
    return res.status(403).json({
      success: false,
      message: "Admin access required"
    });
  }
  next();
};

// ============================================
// RFID ENDPOINTS
// ============================================

/**
 * POST /api/rfid/verify
 * Verify RFID tag and get user info
 * Called by: Raspberry Pi
 * Auth: Machine credentials
 */
router.post("/rfid/verify", authenticateMachine, verifyRfid);

/**
 * POST /api/rfid/register
 * Link RFID tag to user account
 * Called by: Web dashboard
 * Auth: User session required
 */
router.post("/rfid/register", requireAuth, registerRfid);

/**
 * POST /api/rfid/unlink
 * Remove RFID tag from user account
 * Called by: Web dashboard
 * Auth: User session required
 */
router.post("/rfid/unlink", requireAuth, unlinkRfid);

// ============================================
// TRANSACTION ENDPOINTS
// ============================================

/**
 * POST /api/transaction/submit
 * Record paper deposit transaction
 * Called by: Raspberry Pi
 * Auth: Machine credentials
 */
router.post("/transaction/submit", authenticateMachine, submitTransaction);

/**
 * GET /api/transaction/user/:userId
 * Get transaction history for a user
 * Called by: Web dashboard
 * Auth: User session (own transactions) or admin
 */
router.get("/transaction/user/:userId", requireAuth, getUserTransactions);

// ============================================
// MACHINE MONITORING ENDPOINTS
// ============================================

/**
 * POST /api/machine/heartbeat
 * Receive machine status update
 * Called by: Raspberry Pi (every 60 seconds)
 * Auth: Machine credentials
 */
router.post("/machine/heartbeat", authenticateMachine, machineHeartbeat);

// ============================================
// USER STATS ENDPOINTS
// ============================================

/**
 * GET /api/user/stats/:userId
 * Get user statistics (points, transactions, etc.)
 * Called by: Web dashboard
 * Auth: User session (own stats) or admin
 */
router.get("/user/stats/:userId", requireAuth, getUserStats);

// ============================================
// REDEMPTION ENDPOINTS
// ============================================

/**
 * POST /api/redemption/submit
 * Submit redemption request (user redeems points for bond paper)
 * Called by: Web dashboard
 * Auth: User session required
 */
router.post("/redemption/submit", requireAuth, submitRedemption);

/**
 * GET /api/redemption/pending
 * Get list of pending redemptions (for Raspberry Pi to process)
 * Called by: Raspberry Pi (polls every 5 seconds)
 * Auth: Machine credentials
 */
router.get("/redemption/pending", authenticateMachine, getPendingRedemptions);

/**
 * POST /api/redemption/dispense
 * Mark redemption as dispensed after servo motor completes
 * Called by: Raspberry Pi (after successful dispensing)
 * Auth: Machine credentials
 */
router.post("/redemption/dispense", authenticateMachine, markRedemptionDispensed);

// ============================================
// ADMIN ENDPOINTS
// ============================================

/**
 * GET /api/admin/machines
 * Get all machines with their status
 * Called by: Admin dashboard
 * Auth: Admin role required
 */
router.get("/admin/machines", requireAdmin, getAllMachines);

/**
 * GET /api/admin/transactions
 * Get transaction logs with filters
 * Called by: Admin dashboard
 * Auth: Admin role required
 * Query params: userId, machineId, limit, offset, startDate, endDate, status
 */
router.get("/admin/transactions", requireAdmin, getAllTransactions);

/**
 * GET /api/admin/stats
 * Get system-wide statistics
 * Called by: Admin dashboard
 * Auth: Admin role required
 */
router.get("/admin/stats", requireAdmin, getSystemStats);

/**
 * POST /api/admin/adjust-points
 * Manually adjust user points
 * Called by: Admin dashboard
 * Auth: Admin role required
 */
router.post("/admin/adjust-points", requireAdmin, adjustUserPoints);

/**
 * POST /api/admin/dismiss-alert
 * Dismiss an active alert
 * Called by: Admin dashboard
 * Auth: Admin role required
 */
router.post("/admin/dismiss-alert", requireAdmin, dismissAlert);

// ============================================
// HEALTH CHECK ENDPOINT
// ============================================

/**
 * GET /api/health
 * Simple health check for Raspberry Pi to test connectivity
 * No authentication required
 */
router.get("/health", (req, res) => {
  res.json({
    success: true,
    status: "online",
    timestamp: new Date().toISOString(),
    message: "R3-Cycle API is running"
  });
});

// ============================================
// 404 HANDLER FOR /api/* ROUTES
// ============================================

router.use("*", (req, res) => {
  res.status(404).json({
    success: false,
    message: "API endpoint not found",
    path: req.originalUrl
  });
});

export default router;
