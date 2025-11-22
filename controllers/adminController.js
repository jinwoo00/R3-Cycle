/**
 * Admin Controller for R3-Cycle System
 * Handles admin-only endpoints for monitoring, management, and analytics
 *
 * @module controllers/adminController
 */

import { db } from "../models/firebaseConfig.js";
import {
  collection,
  query,
  where,
  getDocs,
  getDoc,
  doc,
  updateDoc,
  orderBy,
  limit,
  startAfter,
  Timestamp,
  increment
} from "firebase/firestore";

/**
 * GET /api/admin/machines
 * Get all machines with their current status
 * Requires: Admin role
 */
export const getAllMachines = async (req, res) => {
  try {
    // Check admin authorization
    if (req.session?.userRole !== "admin") {
      return res.status(403).json({
        success: false,
        message: "Admin access required"
      });
    }

    const machinesRef = collection(db, "machines");
    const querySnapshot = await getDocs(machinesRef);

    const machines = [];
    const now = new Date();

    querySnapshot.forEach((doc) => {
      const machineData = doc.data();

      // Calculate if machine is offline (no heartbeat in last 5 minutes)
      const lastHeartbeat = machineData.lastHeartbeat?.toDate();
      const minutesSinceHeartbeat = lastHeartbeat
        ? Math.floor((now - lastHeartbeat) / 1000 / 60)
        : 999;

      // Determine actual status based on heartbeat
      const actualStatus = minutesSinceHeartbeat > 5 ? "offline" : machineData.status;

      // Calculate stock status
      const stockPercentage = machineData.stockPercentage ||
        Math.floor((machineData.bondPaperStock / (machineData.bondPaperCapacity || 100)) * 100);

      machines.push({
        id: doc.id,
        ...machineData,
        status: actualStatus,
        stockPercentage,
        minutesSinceHeartbeat,
        lastHeartbeat: lastHeartbeat?.toISOString() || null
      });
    });

    // Sort by status priority (offline > critical > warning > ok)
    machines.sort((a, b) => {
      const statusPriority = { offline: 0, critical: 1, warning: 2, online: 3 };
      return (statusPriority[a.status] || 3) - (statusPriority[b.status] || 3);
    });

    return res.json({
      success: true,
      count: machines.length,
      machines
    });

  } catch (error) {
    console.error("Error fetching machines:", error);
    return res.status(500).json({
      success: false,
      message: "Failed to retrieve machines",
      error: error.message
    });
  }
};

/**
 * GET /api/admin/transactions
 * Get transaction logs with optional filters
 * Query params: userId, machineId, limit, offset, startDate, endDate, status
 * Requires: Admin role
 */
export const getAllTransactions = async (req, res) => {
  try {
    // Check admin authorization
    if (req.session?.userRole !== "admin") {
      return res.status(403).json({
        success: false,
        message: "Admin access required"
      });
    }

    const {
      userId,
      machineId,
      status,
      startDate,
      endDate,
      limit: limitParam = 50,
      offset = 0
    } = req.query;

    let transactionsRef = collection(db, "transactions");
    let q = query(transactionsRef);

    // Apply filters
    const constraints = [];

    if (userId) {
      constraints.push(where("userId", "==", userId));
    }

    if (machineId) {
      constraints.push(where("machineId", "==", machineId));
    }

    if (status) {
      constraints.push(where("status", "==", status));
    }

    if (startDate) {
      const start = Timestamp.fromDate(new Date(startDate));
      constraints.push(where("timestamp", ">=", start));
    }

    if (endDate) {
      const end = Timestamp.fromDate(new Date(endDate));
      constraints.push(where("timestamp", "<=", end));
    }

    // Always order by timestamp descending
    constraints.push(orderBy("timestamp", "desc"));
    constraints.push(limit(parseInt(limitParam)));

    q = query(transactionsRef, ...constraints);

    const querySnapshot = await getDocs(q);
    const transactions = [];

    // Fetch user names for each transaction
    for (const docSnap of querySnapshot.docs) {
      const txnData = docSnap.data();

      // Get user name
      let userName = "Unknown User";
      try {
        const userDoc = await getDoc(doc(db, "users", txnData.userId));
        if (userDoc.exists()) {
          userName = userDoc.data().name;
        }
      } catch (err) {
        console.error(`Failed to fetch user ${txnData.userId}:`, err);
      }

      transactions.push({
        id: docSnap.id,
        ...txnData,
        userName,
        timestamp: txnData.timestamp?.toDate()?.toISOString() || null
      });
    }

    return res.json({
      success: true,
      count: transactions.length,
      total: querySnapshot.size,
      transactions
    });

  } catch (error) {
    console.error("Error fetching transactions:", error);
    return res.status(500).json({
      success: false,
      message: "Failed to retrieve transactions",
      error: error.message
    });
  }
};

/**
 * GET /api/admin/stats
 * Get system-wide statistics
 * Requires: Admin role
 */
export const getSystemStats = async (req, res) => {
  try {
    // Check admin authorization
    if (req.session?.userRole !== "admin") {
      return res.status(403).json({
        success: false,
        message: "Admin access required"
      });
    }

    // Get all users count
    const usersRef = collection(db, "users");
    const usersSnapshot = await getDocs(usersRef);
    const totalUsers = usersSnapshot.size;

    // Calculate active users (with at least 1 transaction)
    let activeUsers = 0;
    let totalPoints = 0;
    let totalPaperRecycled = 0;
    let totalBondsEarned = 0;

    usersSnapshot.forEach((doc) => {
      const userData = doc.data();
      if ((userData.totalTransactions || 0) > 0) {
        activeUsers++;
      }
      totalPoints += userData.currentPoints || 0;
      totalPaperRecycled += userData.totalPaperRecycled || 0;
      totalBondsEarned += userData.bondsEarned || 0;
    });

    // Get total transactions
    const transactionsRef = collection(db, "transactions");
    const transactionsSnapshot = await getDocs(transactionsRef);
    const totalTransactions = transactionsSnapshot.size;

    // Calculate completed vs rejected
    let completedTransactions = 0;
    let rejectedTransactions = 0;

    transactionsSnapshot.forEach((doc) => {
      const txnData = doc.data();
      if (txnData.status === "completed") {
        completedTransactions++;
      } else if (txnData.status === "rejected") {
        rejectedTransactions++;
      }
    });

    // Get pending redemptions count
    const redemptionsRef = collection(db, "redemptions");
    const pendingRedemptionsQuery = query(
      redemptionsRef,
      where("status", "==", "pending")
    );
    const pendingRedemptionsSnapshot = await getDocs(pendingRedemptionsQuery);
    const pendingRedemptions = pendingRedemptionsSnapshot.size;

    // Get machines status
    const machinesRef = collection(db, "machines");
    const machinesSnapshot = await getDocs(machinesRef);
    const totalMachines = machinesSnapshot.size;

    let onlineMachines = 0;
    let offlineMachines = 0;
    const now = new Date();

    machinesSnapshot.forEach((doc) => {
      const machineData = doc.data();
      const lastHeartbeat = machineData.lastHeartbeat?.toDate();
      const minutesSinceHeartbeat = lastHeartbeat
        ? Math.floor((now - lastHeartbeat) / 1000 / 60)
        : 999;

      if (minutesSinceHeartbeat <= 5) {
        onlineMachines++;
      } else {
        offlineMachines++;
      }
    });

    // Get alerts count (if alerts collection exists)
    let activeAlerts = 0;
    try {
      const alertsRef = collection(db, "alerts");
      const activeAlertsQuery = query(
        alertsRef,
        where("status", "==", "active")
      );
      const activeAlertsSnapshot = await getDocs(activeAlertsQuery);
      activeAlerts = activeAlertsSnapshot.size;
    } catch (err) {
      // Alerts collection doesn't exist yet
      activeAlerts = 0;
    }

    // Calculate today's stats for growth percentage
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const todayTimestamp = Timestamp.fromDate(today);

    const todayTransactionsQuery = query(
      transactionsRef,
      where("timestamp", ">=", todayTimestamp)
    );
    const todayTransactionsSnapshot = await getDocs(todayTransactionsQuery);
    const todayTransactions = todayTransactionsSnapshot.size;

    // Mock growth percentages (would need historical data for real calculation)
    const growth = {
      users: "+12%",
      transactions: "+8%",
      paper: "+15%"
    };

    return res.json({
      success: true,
      stats: {
        users: {
          total: totalUsers,
          active: activeUsers,
          growth: growth.users
        },
        transactions: {
          total: totalTransactions,
          completed: completedTransactions,
          rejected: rejectedTransactions,
          today: todayTransactions,
          growth: growth.transactions
        },
        paper: {
          totalRecycled: totalPaperRecycled,
          unit: "grams",
          growth: growth.paper
        },
        rewards: {
          totalBondsEarned: totalBondsEarned,
          pendingRedemptions: pendingRedemptions,
          availablePoints: totalPoints
        },
        machines: {
          total: totalMachines,
          online: onlineMachines,
          offline: offlineMachines
        },
        alerts: {
          active: activeAlerts
        }
      }
    });

  } catch (error) {
    console.error("Error fetching system stats:", error);
    return res.status(500).json({
      success: false,
      message: "Failed to retrieve system statistics",
      error: error.message
    });
  }
};

/**
 * POST /api/admin/adjust-points
 * Manually adjust user points (for corrections, bonuses, etc.)
 * Requires: Admin role
 */
export const adjustUserPoints = async (req, res) => {
  try {
    // Check admin authorization
    if (req.session?.userRole !== "admin") {
      return res.status(403).json({
        success: false,
        message: "Admin access required"
      });
    }

    const { userId, adjustment, reason } = req.body;

    // Validate inputs
    if (!userId || adjustment === undefined || !reason) {
      return res.status(400).json({
        success: false,
        message: "Missing required fields: userId, adjustment, reason"
      });
    }

    if (typeof adjustment !== "number") {
      return res.status(400).json({
        success: false,
        message: "Adjustment must be a number"
      });
    }

    // Get user document
    const userRef = doc(db, "users", userId);
    const userDoc = await getDoc(userRef);

    if (!userDoc.exists()) {
      return res.status(404).json({
        success: false,
        message: "User not found"
      });
    }

    const userData = userDoc.data();
    const currentPoints = userData.currentPoints || 0;
    const newBalance = currentPoints + adjustment;

    // Prevent negative points
    if (newBalance < 0) {
      return res.status(400).json({
        success: false,
        message: "Adjustment would result in negative points",
        currentPoints,
        adjustment,
        wouldBe: newBalance
      });
    }

    // Update user points
    await updateDoc(userRef, {
      currentPoints: newBalance
    });

    // Log the adjustment as a special transaction
    const adjustmentRecord = {
      userId,
      type: "admin_adjustment",
      adjustment,
      reason,
      previousBalance: currentPoints,
      newBalance,
      adjustedBy: req.session.userId,
      adjustedByEmail: req.session.userEmail,
      timestamp: Timestamp.now()
    };

    // Store in adjustments collection (audit log)
    try {
      await collection(db, "adjustments").doc().set(adjustmentRecord);
    } catch (err) {
      console.error("Failed to log adjustment:", err);
      // Continue anyway, points were updated
    }

    return res.json({
      success: true,
      message: "Points adjusted successfully",
      adjustment: {
        userId,
        previousBalance: currentPoints,
        adjustment,
        newBalance,
        reason
      }
    });

  } catch (error) {
    console.error("Error adjusting points:", error);
    return res.status(500).json({
      success: false,
      message: "Failed to adjust points",
      error: error.message
    });
  }
};

/**
 * POST /api/admin/dismiss-alert
 * Dismiss an active alert
 * Requires: Admin role
 */
export const dismissAlert = async (req, res) => {
  try {
    // Check admin authorization
    if (req.session?.userRole !== "admin") {
      return res.status(403).json({
        success: false,
        message: "Admin access required"
      });
    }

    const { alertId } = req.body;

    if (!alertId) {
      return res.status(400).json({
        success: false,
        message: "Alert ID required"
      });
    }

    // Get alert document
    const alertRef = doc(db, "alerts", alertId);
    const alertDoc = await getDoc(alertRef);

    if (!alertDoc.exists()) {
      return res.status(404).json({
        success: false,
        message: "Alert not found"
      });
    }

    // Update alert status
    await updateDoc(alertRef, {
      status: "dismissed",
      dismissedAt: Timestamp.now(),
      dismissedBy: req.session.userId
    });

    return res.json({
      success: true,
      message: "Alert dismissed successfully"
    });

  } catch (error) {
    console.error("Error dismissing alert:", error);
    return res.status(500).json({
      success: false,
      message: "Failed to dismiss alert",
      error: error.message
    });
  }
};

// Export all functions
export default {
  getAllMachines,
  getAllTransactions,
  getSystemStats,
  adjustUserPoints,
  dismissAlert
};
