/**
 * Alert Generation and Management Utilities
 * Analyzes machine data and generates appropriate alerts for admin dashboard
 *
 * @module utils/alerts
 */

import { db } from "../models/firebaseConfig.js";
import { collection, addDoc, query, where, getDocs, Timestamp } from "firebase/firestore";

// Alert severity levels
export const AlertSeverity = {
  CRITICAL: "critical",
  WARNING: "warning",
  ERROR: "error",
  INFO: "info"
};

// Alert thresholds
const STOCK_CRITICAL_THRESHOLD = 20; // Below 20% is critical
const STOCK_WARNING_THRESHOLD = 50;  // Below 50% is warning
const HEARTBEAT_OFFLINE_MINUTES = 5;  // No heartbeat for 5 minutes = offline

/**
 * Check machine health and stock levels
 * Returns array of alert objects if issues found
 *
 * @param {Object} machineData - Machine document data
 * @param {string} machineId - Machine ID
 * @returns {Array} Array of alert objects
 */
export function checkMachineHealth(machineData, machineId) {
  const alerts = [];
  const now = new Date();

  // Check heartbeat (offline detection)
  const lastHeartbeat = machineData.lastHeartbeat?.toDate();
  if (lastHeartbeat) {
    const minutesSinceHeartbeat = Math.floor((now - lastHeartbeat) / 1000 / 60);

    if (minutesSinceHeartbeat > HEARTBEAT_OFFLINE_MINUTES) {
      alerts.push({
        machineId,
        severity: AlertSeverity.ERROR,
        title: "Machine Offline",
        description: `No heartbeat received for ${minutesSinceHeartbeat} minutes. Last seen: ${lastHeartbeat.toLocaleString()}`,
        type: "heartbeat_missing"
      });
    }
  }

  // Check stock levels
  const stockPercentage = machineData.stockPercentage ||
    Math.floor((machineData.bondPaperStock / (machineData.bondPaperCapacity || 100)) * 100);

  if (stockPercentage <= STOCK_CRITICAL_THRESHOLD) {
    alerts.push({
      machineId,
      severity: AlertSeverity.CRITICAL,
      title: "Reward Paper Critical Low",
      description: `Bond paper stock at ${stockPercentage}% (${machineData.bondPaperStock}/${machineData.bondPaperCapacity || 100} sheets). Immediate refill required.`,
      type: "stock_critical"
    });
  } else if (stockPercentage <= STOCK_WARNING_THRESHOLD) {
    alerts.push({
      machineId,
      severity: AlertSeverity.WARNING,
      title: "Reward Paper Low",
      description: `Bond paper stock at ${stockPercentage}% (${machineData.bondPaperStock}/${machineData.bondPaperCapacity || 100} sheets). Plan refill soon.`,
      type: "stock_low"
    });
  }

  // Check sensor health
  const sensorHealth = machineData.sensorHealth || {};
  const failedSensors = [];

  Object.entries(sensorHealth).forEach(([sensor, status]) => {
    if (status !== "ok") {
      failedSensors.push(sensor);
    }
  });

  if (failedSensors.length > 0) {
    alerts.push({
      machineId,
      severity: AlertSeverity.ERROR,
      title: "Sensor Failure Detected",
      description: `The following sensors are not responding: ${failedSensors.join(", ")}. Check hardware connections.`,
      type: "sensor_error",
      failedSensors
    });
  }

  return alerts;
}

/**
 * Check stock levels and return alert object if needed
 *
 * @param {Object} machineData - Machine document data
 * @param {string} machineId - Machine ID
 * @returns {Object|null} Alert object or null
 */
export function checkStockLevels(machineData, machineId) {
  const stockPercentage = machineData.stockPercentage ||
    Math.floor((machineData.bondPaperStock / (machineData.bondPaperCapacity || 100)) * 100);

  if (stockPercentage <= STOCK_CRITICAL_THRESHOLD) {
    return {
      machineId,
      severity: AlertSeverity.CRITICAL,
      title: "Reward Paper Critical Low",
      description: `Bond paper stock at ${stockPercentage}% (${machineData.bondPaperStock}/${machineData.bondPaperCapacity || 100} sheets). Immediate refill required.`,
      type: "stock_critical"
    };
  } else if (stockPercentage <= STOCK_WARNING_THRESHOLD) {
    return {
      machineId,
      severity: AlertSeverity.WARNING,
      title: "Reward Paper Low",
      description: `Bond paper stock at ${stockPercentage}% (${machineData.bondPaperStock}/${machineData.bondPaperCapacity || 100} sheets). Plan refill soon.`,
      type: "stock_low"
    };
  }

  return null;
}

/**
 * Create alert document in Firestore
 * Checks for duplicates before creating
 *
 * @param {string} machineId - Machine ID
 * @param {string} severity - Alert severity (critical, warning, error, info)
 * @param {string} title - Alert title
 * @param {string} description - Detailed alert description
 * @param {string} type - Alert type (stock_critical, sensor_error, etc.)
 * @returns {Promise<string|null>} Alert ID or null if duplicate
 */
export async function createAlert(machineId, severity, title, description, type) {
  try {
    // Check if similar alert already exists and is active
    const alertsRef = collection(db, "alerts");
    const q = query(
      alertsRef,
      where("machineId", "==", machineId),
      where("type", "==", type),
      where("status", "==", "active")
    );

    const querySnapshot = await getDocs(q);

    // Don't create duplicate alerts
    if (!querySnapshot.empty) {
      console.log(`Alert of type '${type}' already exists for machine ${machineId}`);
      return null;
    }

    // Create new alert
    const alertData = {
      machineId,
      severity,
      title,
      description,
      type,
      status: "active",
      createdAt: Timestamp.now(),
      resolvedAt: null,
      resolvedBy: null,
      dismissedBy: null
    };

    const docRef = await addDoc(alertsRef, alertData);
    console.log(`Alert created: ${docRef.id} for machine ${machineId}`);

    return docRef.id;

  } catch (error) {
    console.error("Error creating alert:", error);
    return null;
  }
}

/**
 * Process machine heartbeat and auto-generate alerts
 * This function is called by the heartbeat endpoint
 *
 * @param {Object} machineData - Machine data from heartbeat
 * @param {string} machineId - Machine ID
 * @returns {Promise<Array>} Array of created alert IDs
 */
export async function processHeartbeatAlerts(machineData, machineId) {
  const alerts = checkMachineHealth(machineData, machineId);
  const createdAlertIds = [];

  for (const alert of alerts) {
    const alertId = await createAlert(
      alert.machineId,
      alert.severity,
      alert.title,
      alert.description,
      alert.type
    );

    if (alertId) {
      createdAlertIds.push(alertId);
    }
  }

  return createdAlertIds;
}

/**
 * Get severity color for UI display
 *
 * @param {string} severity - Alert severity
 * @returns {string} Tailwind color class
 */
export function getSeverityColor(severity) {
  switch (severity) {
    case AlertSeverity.CRITICAL:
      return "red";
    case AlertSeverity.ERROR:
      return "orange";
    case AlertSeverity.WARNING:
      return "yellow";
    case AlertSeverity.INFO:
      return "blue";
    default:
      return "gray";
  }
}

/**
 * Get severity priority (for sorting)
 *
 * @param {string} severity - Alert severity
 * @returns {number} Priority number (lower = higher priority)
 */
export function getSeverityPriority(severity) {
  switch (severity) {
    case AlertSeverity.CRITICAL:
      return 0;
    case AlertSeverity.ERROR:
      return 1;
    case AlertSeverity.WARNING:
      return 2;
    case AlertSeverity.INFO:
      return 3;
    default:
      return 4;
  }
}

// Export all functions
export default {
  AlertSeverity,
  checkMachineHealth,
  checkStockLevels,
  createAlert,
  processHeartbeatAlerts,
  getSeverityColor,
  getSeverityPriority
};
