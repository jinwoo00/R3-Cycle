/**
 * IoT Controller for R3-Cycle Hardware Integration
 *
 * Handles all API endpoints for Raspberry Pi communication:
 * - RFID verification
 * - Transaction submission
 * - Machine heartbeat
 * - User statistics
 *
 * @module controllers/iotController
 */

import { db } from "../models/firebaseConfig.js";
import {
  doc,
  getDoc,
  setDoc,
  updateDoc,
  addDoc,
  collection,
  increment,
  Timestamp,
  query,
  where,
  getDocs,
  orderBy,
  limit
} from "firebase/firestore";
import {
  calculatePoints,
  validateRfidTag,
  validateMachineId,
  validateTimestamp,
  validateSensorHealth,
  checkRedemptionEligibility
} from "../utils/validation.js";

/**
 * POST /api/rfid/verify
 * Verify RFID tag and return user information
 * Called by Raspberry Pi when user taps card
 *
 * @param {object} req.body.rfidTag - RFID tag ID from RC522 reader
 * @param {object} req.body.machineId - Machine identifier
 * @returns {object} User data or error
 */
export const verifyRfid = async (req, res) => {
  try {
    const { rfidTag, machineId } = req.body;

    // Validate inputs
    const rfidValidation = validateRfidTag(rfidTag);
    if (!rfidValidation.valid) {
      return res.status(400).json({
        success: false,
        valid: false,
        message: rfidValidation.reason
      });
    }

    const machineValidation = validateMachineId(machineId);
    if (!machineValidation.valid) {
      return res.status(400).json({
        success: false,
        valid: false,
        message: machineValidation.reason
      });
    }

    // Query Firestore for user with this RFID tag
    const usersRef = collection(db, "users");
    const q = query(usersRef, where("rfidTag", "==", rfidTag));
    const querySnapshot = await getDocs(q);

    if (querySnapshot.empty) {
      // RFID not registered
      return res.json({
        success: true,
        valid: false,
        message: "Card not registered. Please link your RFID card via the web dashboard."
      });
    }

    // Get user data
    const userDoc = querySnapshot.docs[0];
    const userData = userDoc.data();
    const userId = userDoc.id;

    // Check if account is active
    if (userData.role === "disabled") {
      return res.json({
        success: true,
        valid: false,
        message: "Account disabled. Please contact support."
      });
    }

    // Return user information
    // Note: sync.py expects a 'user' object, but main.py expects flat structure
    // Return both formats for compatibility
    return res.json({
      success: true,
      valid: true,
      userId: userId,
      userName: userData.name,
      currentPoints: userData.currentPoints || 0,
      totalTransactions: userData.totalTransactions || 0,
      message: `Welcome, ${userData.name}!`,
      // Also include nested user object for sync.py compatibility
      user: {
        userId: userId,
        name: userData.name,
        current_points: userData.currentPoints || 0,
        currentPoints: userData.currentPoints || 0,
        total_transactions: userData.totalTransactions || 0,
        totalTransactions: userData.totalTransactions || 0
      }
    });

  } catch (error) {
    console.error("Error verifying RFID:", error);
    return res.status(500).json({
      success: false,
      valid: false,
      message: "Server error verifying RFID"
    });
  }
};

/**
 * POST /api/transaction/submit
 * Record paper deposit transaction from Raspberry Pi
 * Awards points based on paper count
 *
 * @param {string} req.body.rfidTag - User's RFID tag
 * @param {number} req.body.paperCount - Number of papers inserted
 * @param {string} req.body.timestamp - ISO timestamp
 * @returns {object} Transaction result
 */
export const submitTransaction = async (req, res) => {
  try {
    const { rfidTag, paperCount, timestamp } = req.body;
    const machineId = req.headers['x-machine-id'];

    // Validate inputs
    const rfidValidation = validateRfidTag(rfidTag);
    if (!rfidValidation.valid) {
      return res.status(400).json({
        success: false,
        accepted: false,
        message: rfidValidation.reason
      });
    }

    if (!validateTimestamp(timestamp)) {
      return res.status(400).json({
        success: false,
        accepted: false,
        message: "Invalid timestamp format"
      });
    }

    // Validate paper count
    if (typeof paperCount !== 'number' || paperCount < 1 || paperCount > 50) {
      return res.status(400).json({
        success: false,
        accepted: false,
        message: "Invalid paper count (must be 1-50)"
      });
    }

    // Find user by RFID
    const usersRef = collection(db, "users");
    const q = query(usersRef, where("rfidTag", "==", rfidTag));
    const querySnapshot = await getDocs(q);

    if (querySnapshot.empty) {
      return res.status(404).json({
        success: false,
        accepted: false,
        message: "RFID not found in system"
      });
    }

    const userDoc = querySnapshot.docs[0];
    const userId = userDoc.id;

    // Calculate points based on paper count
    const pointsAwarded = calculatePoints(paperCount);

    // Create successful transaction record
    const transactionRef = await addDoc(collection(db, "transactions"), {
      userId: userId,
      rfidTag: rfidTag,
      machineId: machineId,
      paperCount: paperCount,
      pointsAwarded: pointsAwarded,
      status: "completed",
      rejectionReason: null,
      timestamp: Timestamp.fromDate(new Date(timestamp)),
      syncedAt: Timestamp.now()
    });

    // Update user statistics
    await updateDoc(doc(db, "users", userId), {
      currentPoints: increment(pointsAwarded),
      totalPaperRecycled: increment(paperCount),  // Count papers instead of weight
      totalTransactions: increment(1),
      lastTransactionAt: Timestamp.now()
    });

    // Get updated user data
    const updatedUserDoc = await getDoc(doc(db, "users", userId));
    const updatedUserData = updatedUserDoc.data();
    const newTotalPoints = updatedUserData.currentPoints || 0;

    // Emit real-time transaction update to the user
    try {
      const io = req.app?.locals?.io;
      if (io) {
        // Emit to user's room
        io.to(`user:${userId}`).emit("transaction:new", {
          transactionId: transactionRef.id,
          userId: userId,
          paperCount: paperCount,
          pointsAwarded: pointsAwarded,
          totalPoints: newTotalPoints,
          status: "completed",
          timestamp: new Date().toISOString()
        });
        
        // Also emit stats update
        io.to(`user:${userId}`).emit("stats:update", {
          currentPoints: newTotalPoints,
          totalPaperRecycled: updatedUserData.totalPaperRecycled || 0,
          totalTransactions: updatedUserData.totalTransactions || 0
        });
        
        console.log(`[Socket] Emitted transaction:new to user:${userId}`);
      }
    } catch (socketError) {
      console.error("Error emitting socket event:", socketError);
      // Don't fail the transaction if socket emit fails
    }

    return res.json({
      success: true,
      accepted: true,
      transaction: {
        id: transactionRef.id,
        pointsAwarded: pointsAwarded,
        totalPoints: newTotalPoints,
        paperCount: paperCount,
        message: `Paper accepted! +${pointsAwarded} point${pointsAwarded > 1 ? 's' : ''}. Total: ${newTotalPoints}`
      }
    });

  } catch (error) {
    console.error("Error submitting transaction:", error);
    return res.status(500).json({
      success: false,
      accepted: false,
      message: "Server error processing transaction"
    });
  }
};

/**
 * POST /api/machine/heartbeat
 * Receive machine status update from Raspberry Pi
 * Updates machine document and checks for alerts
 *
 * @param {string} req.body.machineId - Machine identifier
 * @param {string} req.body.status - "online" or "offline"
 * @param {number} req.body.bondPaperStock - Stock level (percentage or count)
 * @param {object} req.body.sensorHealth - Health status of all sensors
 * @param {string} req.body.timestamp - ISO timestamp
 * @returns {object} Success confirmation
 */
export const machineHeartbeat = async (req, res) => {
  try {
    const { machineId, status, bondPaperStock, sensorHealth, timestamp } = req.body;

    // Validate inputs
    const machineValidation = validateMachineId(machineId);
    if (!machineValidation.valid) {
      return res.status(400).json({
        success: false,
        message: machineValidation.reason
      });
    }

    if (!validateTimestamp(timestamp)) {
      return res.status(400).json({
        success: false,
        message: "Invalid timestamp format"
      });
    }

    const sensorValidation = validateSensorHealth(sensorHealth);
    if (!sensorValidation.valid) {
      return res.status(400).json({
        success: false,
        message: sensorValidation.reason,
        errors: sensorValidation.errors
      });
    }

    // Check if machine document exists
    const machineRef = doc(db, "machines", machineId);
    const machineDoc = await getDoc(machineRef);

    const machineData = {
      id: machineId,
      status: status,
      bondPaperStock: bondPaperStock,
      bondPaperCapacity: 100, // Default capacity
      stockPercentage: bondPaperStock,
      lastHeartbeat: Timestamp.fromDate(new Date(timestamp)),
      sensorHealth: sensorHealth
    };

    if (machineDoc.exists()) {
      // Update existing machine
      await updateDoc(machineRef, {
        status: status,
        bondPaperStock: bondPaperStock,
        stockPercentage: bondPaperStock,
        lastHeartbeat: Timestamp.fromDate(new Date(timestamp)),
        sensorHealth: sensorHealth
      });
    } else {
      // Create new machine document
      await setDoc(machineRef, {
        ...machineData,
        location: "Unknown - Please set via admin dashboard",
        lastMaintenance: null,
        totalTransactions: 0,
        totalPaperCollected: 0,
        alerts: []
      });
    }

    // Auto-generate alerts based on machine health
    try {
      const { processHeartbeatAlerts } = await import("../utils/alerts.js");
      const alertIds = await processHeartbeatAlerts(machineData, machineId);

      if (alertIds.length > 0) {
        console.log(`Generated ${alertIds.length} alert(s) for machine ${machineId}`);
      }
    } catch (alertError) {
      console.error("Error processing alerts:", alertError);
      // Don't fail the heartbeat if alert generation fails
    }

    return res.json({
      success: true,
      message: "Heartbeat received"
    });

  } catch (error) {
    console.error("Error processing heartbeat:", error);
    return res.status(500).json({
      success: false,
      message: "Server error processing heartbeat"
    });
  }
};

/**
 * GET /api/user/stats/:userId
 * Get user statistics for dashboard
 *
 * @param {string} req.params.userId - User Firebase UID
 * @returns {object} User statistics
 */
export const getUserStats = async (req, res) => {
  try {
    const { userId } = req.params;

    // Check if user is requesting their own stats or is admin
    const isOwnStats = req.session?.userId === userId;
    const isAdmin = req.session?.userRole === "admin";

    if (!isOwnStats && !isAdmin) {
      return res.status(403).json({
        success: false,
        message: "Unauthorized to view these statistics"
      });
    }

    // Get user document
    const userDoc = await getDoc(doc(db, "users", userId));

    if (!userDoc.exists()) {
      return res.status(404).json({
        success: false,
        message: "User not found"
      });
    }

    const userData = userDoc.data();

    return res.json({
      success: true,
      stats: {
        currentPoints: userData.currentPoints || 0,
        totalPaperRecycled: userData.totalPaperRecycled || 0,
        totalTransactions: userData.totalTransactions || 0,
        bondsEarned: userData.bondsEarned || 0,
        lastTransactionAt: userData.lastTransactionAt || null
      }
    });

  } catch (error) {
    console.error("Error getting user stats:", error);
    return res.status(500).json({
      success: false,
      message: "Server error fetching statistics"
    });
  }
};

/**
 * POST /api/rfid/register
 * Link RFID tag to user account (called from web dashboard)
 *
 * @param {string} req.body.rfidTag - RFID tag to link
 * @returns {object} Success or error
 */
export const registerRfid = async (req, res) => {
  try {
    // Check if user is authenticated
    if (!req.session?.userId) {
      return res.status(401).json({
        success: false,
        message: "Authentication required"
      });
    }

    const { rfidTag } = req.body;
    const userId = req.session.userId;

    // Validate RFID format
    const rfidValidation = validateRfidTag(rfidTag);
    if (!rfidValidation.valid) {
      return res.status(400).json({
        success: false,
        message: rfidValidation.reason
      });
    }

    // Check if RFID is already registered to another user
    const usersRef = collection(db, "users");
    const q = query(usersRef, where("rfidTag", "==", rfidTag));
    const querySnapshot = await getDocs(q);

    if (!querySnapshot.empty) {
      const existingUser = querySnapshot.docs[0];
      if (existingUser.id !== userId) {
        return res.status(409).json({
          success: false,
          message: "This RFID card is already registered to another account"
        });
      }
    }

    // Link RFID to user account
    await updateDoc(doc(db, "users", userId), {
      rfidTag: rfidTag,
      rfidRegisteredAt: Timestamp.now()
    });

    return res.json({
      success: true,
      message: "RFID card successfully linked to your account"
    });

  } catch (error) {
    console.error("Error registering RFID:", error);
    return res.status(500).json({
      success: false,
      message: "Server error linking RFID card"
    });
  }
};

/**
 * POST /api/rfid/unlink
 * Remove RFID tag from user account
 *
 * @returns {object} Success confirmation
 */
export const unlinkRfid = async (req, res) => {
  try {
    // Check if user is authenticated
    if (!req.session?.userId) {
      return res.status(401).json({
        success: false,
        message: "Authentication required"
      });
    }

    const userId = req.session.userId;

    // Remove RFID from user account
    await updateDoc(doc(db, "users", userId), {
      rfidTag: null,
      rfidRegisteredAt: null
    });

    return res.json({
      success: true,
      message: "RFID card unlinked from your account"
    });

  } catch (error) {
    console.error("Error unlinking RFID:", error);
    return res.status(500).json({
      success: false,
      message: "Server error unlinking RFID card"
    });
  }
};

/**
 * GET /api/transaction/user/:userId
 * Get transaction history for a user
 *
 * @param {string} req.params.userId - User Firebase UID
 * @param {number} req.query.limit - Max results (default: 50)
 * @param {number} req.query.offset - Skip results (default: 0)
 * @returns {object} Array of transactions
 */
export const getUserTransactions = async (req, res) => {
  try {
    const { userId } = req.params;
    const limitCount = parseInt(req.query.limit) || 50;

    // Check authorization
    const isOwnTransactions = req.session?.userId === userId;
    const isAdmin = req.session?.userRole === "admin";

    if (!isOwnTransactions && !isAdmin) {
      return res.status(403).json({
        success: false,
        message: "Unauthorized to view these transactions"
      });
    }

    // Query transactions
    const transactionsRef = collection(db, "transactions");
    const q = query(
      transactionsRef,
      where("userId", "==", userId),
      orderBy("timestamp", "desc"),
      limit(limitCount)
    );

    const querySnapshot = await getDocs(q);
    const transactions = [];

    querySnapshot.forEach((doc) => {
      transactions.push({
        id: doc.id,
        ...doc.data(),
        timestamp: doc.data().timestamp?.toDate().toISOString()
      });
    });

    return res.json({
      success: true,
      transactions: transactions,
      count: transactions.length
    });

  } catch (error) {
    console.error("Error fetching transactions:", error);
    return res.status(500).json({
      success: false,
      message: "Server error fetching transactions"
    });
  }
};

/**
 * POST /api/redemption/submit
 * Submit a redemption request (web dashboard)
 * Deducts points and creates redemption record
 *
 * @param {string} req.body.rewardType - Type of reward (bond_paper_1, bond_paper_5)
 * @param {number} req.body.pointsCost - Points required for redemption
 * @returns {object} Redemption confirmation
 */
export const submitRedemption = async (req, res) => {
  try {
    // Check authentication
    if (!req.session?.userId) {
      return res.status(401).json({
        success: false,
        message: "Authentication required"
      });
    }

    const { rewardType, pointsCost } = req.body;
    const userId = req.session.userId;

    // Validate inputs
    if (!rewardType || !pointsCost) {
      return res.status(400).json({
        success: false,
        message: "Reward type and points cost are required"
      });
    }

    // Get user document
    const userDocRef = doc(db, "users", userId);
    const userDoc = await getDoc(userDocRef);

    if (!userDoc.exists()) {
      return res.status(404).json({
        success: false,
        message: "User not found"
      });
    }

    const userData = userDoc.data();
    const currentPoints = userData.currentPoints || 0;

    // Check if user has enough points
    const eligibility = checkRedemptionEligibility(currentPoints, pointsCost);
    if (!eligibility.eligible) {
      return res.status(400).json({
        success: false,
        message: `Insufficient points. You need ${eligibility.remaining} more points.`,
        currentPoints: currentPoints,
        required: pointsCost,
        shortage: eligibility.remaining
      });
    }

    // Create redemption record (will be marked as "completed" after dispensing)
    const redemptionData = {
      userId: userId,
      rewardType: rewardType,
      pointsCost: pointsCost,
      status: "processing", // Will be "completed" after servo dispenses
      requestedAt: Timestamp.now(),
      dispensedAt: null,
      machineId: null
    };

    const redemptionRef = await addDoc(collection(db, "redemptions"), redemptionData);

    // Deduct points from user
    const newPoints = currentPoints - pointsCost;
    await updateDoc(userDocRef, {
      currentPoints: newPoints,
      bondsEarned: increment(1)
    });

    // Emit immediate redemption dispense event via Socket.io
    try {
      const io = req.app?.locals?.io;
      console.log(`[Socket] Checking Socket.io availability...`);
      console.log(`[Socket] req.app exists: ${!!req.app}`);
      console.log(`[Socket] req.app.locals exists: ${!!req.app?.locals}`);
      console.log(`[Socket] req.app.locals.io exists: ${!!req.app?.locals?.io}`);
      
      if (io) {
        const redemptionEvent = {
          redemptionId: redemptionRef.id,
          rewardType: rewardType,
          userId: userId,
          pointsCost: pointsCost
        };
        
        // Emit to all machines in "machines" room
        io.to("machines").emit("redemption:dispense", redemptionEvent);
        
        // Also emit to specific machine room (RPI_001) as backup
        io.to("machine:RPI_001").emit("redemption:dispense", redemptionEvent);
        
        console.log(`[Socket] ✅ Emitted immediate redemption dispense: ${redemptionRef.id}`);
        console.log(`[Socket] Event data:`, JSON.stringify(redemptionEvent));
        console.log(`[Socket] Emitted to rooms: "machines" and "machine:RPI_001"`);
        
        // Log connected machines for debugging
        const machinesRoom = io.sockets.adapter.rooms.get("machines");
        const specificRoom = io.sockets.adapter.rooms.get("machine:RPI_001");
        
        if (machinesRoom) {
          console.log(`[Socket] Machines room has ${machinesRoom.size} socket(s)`);
        } else {
          console.warn(`[Socket] ⚠️  Machines room is empty - no machines connected!`);
        }
        
        if (specificRoom) {
          console.log(`[Socket] Machine:RPI_001 room has ${specificRoom.size} socket(s)`);
        } else {
          console.warn(`[Socket] ⚠️  Machine:RPI_001 room is empty`);
        }
      } else {
        console.warn("[Socket] ⚠️  Socket.io not available (req.app?.locals?.io is null) - redemption will be processed via polling");
      }
    } catch (socketError) {
      console.error("[Socket] ❌ Error emitting redemption event:", socketError);
      console.error("[Socket] Error stack:", socketError.stack);
      // Don't fail the redemption if socket emit fails - polling will handle it
    }

    return res.json({
      success: true,
      message: "Redemption request submitted successfully",
      redemption: {
        id: redemptionRef.id,
        rewardType: rewardType,
        pointsDeducted: pointsCost,
        remainingPoints: newPoints,
        status: "processing" // Changed from "pending" - will be "completed" after dispensing
      }
    });

  } catch (error) {
    console.error("Error submitting redemption:", error);
    console.error("Error stack:", error.stack);
    console.error("Error details:", {
      message: error.message,
      code: error.code,
      name: error.name
    });
    return res.status(500).json({
      success: false,
      message: "Server error processing redemption",
      error: process.env.NODE_ENV === 'development' ? error.message : undefined
    });
  }
};

/**
 * POST /api/redemption/dispense
 * Machine endpoint to mark redemption as dispensed
 * Called by Raspberry Pi after servo motor dispenses paper
 *
 * @param {string} req.body.redemptionId - Redemption record ID
 * @param {string} req.body.machineId - Machine that dispensed the reward
 * @returns {object} Confirmation
 */
export const markRedemptionDispensed = async (req, res) => {
  try {
    const { redemptionId, machineId } = req.body;

    if (!redemptionId || !machineId) {
      return res.status(400).json({
        success: false,
        message: "Redemption ID and Machine ID required"
      });
    }

    // Update redemption record
    const redemptionRef = doc(db, "redemptions", redemptionId);
    await updateDoc(redemptionRef, {
      status: "completed",
      dispensedAt: Timestamp.now(),
      machineId: machineId
    });

    return res.json({
      success: true,
      message: "Redemption marked as dispensed"
    });

  } catch (error) {
    console.error("Error marking redemption dispensed:", error);
    return res.status(500).json({
      success: false,
      message: "Server error updating redemption"
    });
  }
};

/**
 * GET /api/redemption/pending
 * Get pending redemptions (for machine to check)
 * Raspberry Pi polls this to see if it needs to dispense rewards
 *
 * @param {string} req.query.machineId - Machine ID
 * @returns {array} Pending redemptions
 */
export const getPendingRedemptions = async (req, res) => {
  try {
    const redemptionsRef = collection(db, "redemptions");
    
    // Try query with orderBy (requires index)
    let querySnapshot;
    let redemptions = [];
    
    try {
      // Check for "processing" status (immediate redemption flow)
      // Polling serves as backup if Socket.io fails
      const q = query(
        redemptionsRef,
        where("status", "==", "processing"),
        orderBy("requestedAt", "asc"),
        limit(10)
      );

      querySnapshot = await getDocs(q);
      querySnapshot.forEach((doc) => {
        redemptions.push({
          id: doc.id,
          ...doc.data()
        });
      });
    } catch (queryError) {
      // Fallback: If index is missing, fetch more documents and sort in memory
      console.warn("[REDEMPTION] Composite query index missing, fetching all redemptions and sorting in memory");
      console.warn("[REDEMPTION] Error:", queryError.message);
      
      // Fetch all redemptions with "processing" status (no orderBy)
      const fallbackQuery = query(
        redemptionsRef,
        where("status", "==", "processing"),
        limit(50) // Fetch more to ensure we get all processing redemptions
      );
      
      querySnapshot = await getDocs(fallbackQuery);
      
      // Sort in memory by requestedAt
      querySnapshot.forEach((doc) => {
        const data = doc.data();
        redemptions.push({
          id: doc.id,
          ...data
        });
      });
      
      // Sort by requestedAt ascending (oldest first - FIFO)
      redemptions.sort((a, b) => {
        const aTime = a.requestedAt?.toMillis?.() || a.requestedAt?.seconds || 0;
        const bTime = b.requestedAt?.toMillis?.() || b.requestedAt?.seconds || 0;
        return aTime - bTime;
      });
      
      // Limit to 10 after sorting
      redemptions = redemptions.slice(0, 10);
      
      console.log(`[REDEMPTION] Fetched ${redemptions.length} redemptions (sorted in memory)`);
    }

    return res.json({
      success: true,
      count: redemptions.length,
      redemptions: redemptions
    });

  } catch (error) {
    console.error("Error fetching pending redemptions:", error);
    console.error("Error stack:", error.stack);
    console.error("Error details:", {
      message: error.message,
      code: error.code,
      name: error.name
    });
    return res.status(500).json({
      success: false,
      message: "Server error fetching redemptions",
      error: process.env.NODE_ENV === 'development' ? error.message : undefined
    });
  }
};

export default {
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
};
