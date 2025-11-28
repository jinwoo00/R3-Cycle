/**
 * Validation Utility Functions for R3-Cycle IoT System
 *
 * This module provides validation logic for:
 * - Paper weight measurements
 * - Metal detection
 * - Points calculation
 * - RFID tag format
 *
 * @module utils/validation
 */

/**
 * Validates paper weight from load cell sensor
 * Valid range: 1-20 grams (typical paper weight)
 *
 * @param {number} weight - Weight in grams from HX711 sensor
 * @returns {object} Validation result
 * @returns {boolean} result.valid - Whether weight is valid
 * @returns {string} result.reason - Reason if invalid
 *
 * @example
 * validatePaperWeight(5.2)  // { valid: true, reason: null }
 * validatePaperWeight(0.5)  // { valid: false, reason: "Paper too light - minimum 1g" }
 * validatePaperWeight(25)   // { valid: false, reason: "Item too heavy - maximum 20g, likely not paper" }
 */
export function validatePaperWeight(weight) {
  const MIN_WEIGHT = 1;    // grams
  const MAX_WEIGHT = 20;   // grams

  // Check if weight is a valid number
  if (typeof weight !== 'number' || isNaN(weight)) {
    return {
      valid: false,
      reason: "Invalid weight measurement"
    };
  }

  // Check minimum weight
  if (weight < MIN_WEIGHT) {
    return {
      valid: false,
      reason: `Paper too light - minimum ${MIN_WEIGHT}g`
    };
  }

  // Check maximum weight
  if (weight > MAX_WEIGHT) {
    return {
      valid: false,
      reason: `Item too heavy - maximum ${MAX_WEIGHT}g, likely not paper`
    };
  }

  // Weight is valid
  return {
    valid: true,
    reason: null
  };
}

/**
 * Checks metal detection status from inductive proximity sensor
 * If metal is detected, paper is contaminated (staples, clips, etc.)
 *
 * @param {boolean} metalDetected - Reading from LJ12A3-4-ZBX sensor
 * @returns {object} Check result
 * @returns {boolean} result.accepted - Whether paper can be accepted
 * @returns {string} result.reason - Reason if rejected
 *
 * @example
 * checkMetalDetection(false)  // { accepted: true, reason: null }
 * checkMetalDetection(true)   // { accepted: false, reason: "Metal detected - remove staples, clips, or binders" }
 */
export function checkMetalDetection(metalDetected) {
  if (metalDetected === true) {
    return {
      accepted: false,
      reason: "Metal detected - remove staples, clips, or binders"
    };
  }

  return {
    accepted: true,
    reason: null
  };
}

/**
 * Calculates points to award based on paper count
 * Current system: 10 points per paper
 *
 * @param {number} paperCount - Number of papers inserted
 * @returns {number} Points to award
 *
 * @example
 * calculatePoints(1)   // 10
 * calculatePoints(3)   // 30
 */
export function calculatePoints(paperCount) {
  const POINTS_PER_PAPER = 10;  // Points per paper (matches Raspberry Pi config)

  // Validate paper count
  if (typeof paperCount !== 'number' || paperCount < 1 || paperCount > 50) {
    return 0;  // No points for invalid count
  }

  // Calculate points: paperCount × POINTS_PER_PAPER
  return paperCount * POINTS_PER_PAPER;
}

/**
 * Validates RFID tag format
 * RC522 RFID tags are typically 8-10 character hexadecimal strings
 *
 * @param {string} rfidTag - RFID tag from RC522 reader
 * @returns {object} Validation result
 * @returns {boolean} result.valid - Whether RFID format is valid
 * @returns {string} result.reason - Reason if invalid
 *
 * @example
 * validateRfidTag("A1B2C3D4")     // { valid: true, reason: null }
 * validateRfidTag("12345678")     // { valid: true, reason: null }
 * validateRfidTag("")             // { valid: false, reason: "RFID tag is required" }
 * validateRfidTag("XYZ")          // { valid: false, reason: "Invalid RFID format" }
 */
export function validateRfidTag(rfidTag) {
  // Check if RFID is provided
  if (!rfidTag || typeof rfidTag !== 'string') {
    return {
      valid: false,
      reason: "RFID tag is required"
    };
  }

  // Trim whitespace
  rfidTag = rfidTag.trim();

  // Check minimum length (typically 8 characters)
  if (rfidTag.length < 4) {
    return {
      valid: false,
      reason: "Invalid RFID format - too short"
    };
  }

  // Check maximum length (typically 10 characters, allow some flexibility)
  if (rfidTag.length > 20) {
    return {
      valid: false,
      reason: "Invalid RFID format - too long"
    };
  }

  // Validate hexadecimal format (alphanumeric)
  const hexPattern = /^[A-Fa-f0-9]+$/;
  if (!hexPattern.test(rfidTag)) {
    return {
      valid: false,
      reason: "Invalid RFID format - must be alphanumeric"
    };
  }

  return {
    valid: true,
    reason: null
  };
}

/**
 * Validates machine ID format
 * Format: Alphanumeric with optional underscores/hyphens
 *
 * @param {string} machineId - Machine identifier (e.g., "RPI_001")
 * @returns {object} Validation result
 *
 * @example
 * validateMachineId("RPI_001")  // { valid: true, reason: null }
 * validateMachineId("")         // { valid: false, reason: "Machine ID is required" }
 */
export function validateMachineId(machineId) {
  if (!machineId || typeof machineId !== 'string') {
    return {
      valid: false,
      reason: "Machine ID is required"
    };
  }

  machineId = machineId.trim();

  if (machineId.length < 3 || machineId.length > 20) {
    return {
      valid: false,
      reason: "Machine ID must be 3-20 characters"
    };
  }

  // Allow alphanumeric, underscores, and hyphens
  const pattern = /^[A-Za-z0-9_-]+$/;
  if (!pattern.test(machineId)) {
    return {
      valid: false,
      reason: "Machine ID must be alphanumeric with optional underscores/hyphens"
    };
  }

  return {
    valid: true,
    reason: null
  };
}

/**
 * Checks if user has enough points to redeem reward
 *
 * @param {number} currentPoints - User's current point balance
 * @param {number} rewardCost - Points required for reward (default: 20)
 * @returns {object} Eligibility result
 * @returns {boolean} result.eligible - Whether user can redeem
 * @returns {number} result.remaining - Points needed if not eligible
 *
 * @example
 * checkRedemptionEligibility(25, 20)  // { eligible: true, remaining: 0 }
 * checkRedemptionEligibility(15, 20)  // { eligible: false, remaining: 5 }
 */
export function checkRedemptionEligibility(currentPoints, rewardCost = 20) {
  if (currentPoints >= rewardCost) {
    return {
      eligible: true,
      remaining: 0
    };
  }

  return {
    eligible: false,
    remaining: rewardCost - currentPoints
  };
}

/**
 * Validates timestamp format (ISO 8601)
 *
 * @param {string} timestamp - ISO timestamp from Raspberry Pi
 * @returns {boolean} Whether timestamp is valid
 *
 * @example
 * validateTimestamp("2025-11-18T14:35:00Z")  // true
 * validateTimestamp("invalid")               // false
 */
export function validateTimestamp(timestamp) {
  if (!timestamp || typeof timestamp !== 'string') {
    return false;
  }

  const date = new Date(timestamp);
  return !isNaN(date.getTime());
}

/**
 * Validates sensor health status object
 *
 * @param {object} sensorHealth - Sensor status from Raspberry Pi
 * @returns {object} Validation result
 *
 * @example
 * validateSensorHealth({
 *   rfid: "ok",
 *   loadCell: "ok",
 *   inductiveSensor: "error"
 * })  // { valid: true, errors: ["inductiveSensor"] }
 */
export function validateSensorHealth(sensorHealth) {
  const requiredSensors = ['rfid', 'loadCell', 'inductiveSensor', 'irSensor', 'servo'];
  const validStatuses = ['ok', 'error'];

  if (!sensorHealth || typeof sensorHealth !== 'object') {
    return {
      valid: false,
      reason: "Sensor health data is required",
      errors: []
    };
  }

  const errors = [];

  for (const sensor of requiredSensors) {
    const status = sensorHealth[sensor];

    if (!status) {
      errors.push(`Missing status for ${sensor}`);
    } else if (!validStatuses.includes(status)) {
      errors.push(`Invalid status for ${sensor}: ${status}`);
    }
  }

  return {
    valid: errors.length === 0,
    reason: errors.length > 0 ? "Invalid sensor health data" : null,
    errors
  };
}

// Export all functions as default object
export default {
  validatePaperWeight,
  checkMetalDetection,
  calculatePoints,
  validateRfidTag,
  validateMachineId,
  checkRedemptionEligibility,
  validateTimestamp,
  validateSensorHealth
};
