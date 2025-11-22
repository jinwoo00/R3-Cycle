/**
 * Database Initialization Script for R3-Cycle
 *
 * This script initializes or updates the Firestore database schema:
 * 1. Adds new fields to existing users
 * 2. Creates sample machine documents
 * 3. Sets up Firestore indexes (instructions provided)
 *
 * Usage: node scripts/initializeDatabase.js
 *
 * @module scripts/initializeDatabase
 */

import { db } from "../models/firebaseConfig.js";
import {
  collection,
  getDocs,
  updateDoc,
  doc,
  setDoc,
  Timestamp
} from "firebase/firestore";

/**
 * Add new RFID and stats fields to existing users
 * Fields added:
 * - rfidTag: null
 * - rfidRegisteredAt: null
 * - currentPoints: 0
 * - totalPaperRecycled: 0
 * - totalTransactions: 0
 * - bondsEarned: 0
 * - lastTransactionAt: null
 */
async function updateExistingUsers() {
  console.log("📝 Updating existing user documents...");

  try {
    const usersRef = collection(db, "users");
    const querySnapshot = await getDocs(usersRef);

    let updateCount = 0;

    for (const userDoc of querySnapshot.docs) {
      const userData = userDoc.data();

      // Only add fields if they don't exist
      const updates = {};

      if (userData.rfidTag === undefined) {
        updates.rfidTag = null;
      }
      if (userData.rfidRegisteredAt === undefined) {
        updates.rfidRegisteredAt = null;
      }
      if (userData.currentPoints === undefined) {
        updates.currentPoints = 0;
      }
      if (userData.totalPaperRecycled === undefined) {
        updates.totalPaperRecycled = 0;
      }
      if (userData.totalTransactions === undefined) {
        updates.totalTransactions = 0;
      }
      if (userData.bondsEarned === undefined) {
        updates.bondsEarned = 0;
      }
      if (userData.lastTransactionAt === undefined) {
        updates.lastTransactionAt = null;
      }

      // Update only if there are new fields to add
      if (Object.keys(updates).length > 0) {
        await updateDoc(doc(db, "users", userDoc.id), updates);
        updateCount++;
        console.log(`   ✓ Updated user: ${userData.email || userDoc.id}`);
      }
    }

    console.log(`✅ Updated ${updateCount} user(s) with new fields\n`);
  } catch (error) {
    console.error("❌ Error updating users:", error);
    throw error;
  }
}

/**
 * Create sample machine document for testing
 * This creates a default machine "RPI_001" if it doesn't exist
 */
async function createSampleMachine() {
  console.log("🤖 Creating sample machine document...");

  try {
    const machineId = "RPI_001";
    const machineRef = doc(db, "machines", machineId);

    await setDoc(machineRef, {
      id: machineId,
      location: "Building A - 1st Floor (Sample Machine)",
      status: "offline",
      bondPaperStock: 100,
      bondPaperCapacity: 100,
      stockPercentage: 100,
      lastHeartbeat: Timestamp.now(),
      lastMaintenance: null,
      totalTransactions: 0,
      totalPaperCollected: 0,
      sensorHealth: {
        rfid: "ok",
        loadCell: "ok",
        inductiveSensor: "ok",
        irSensor: "ok",
        servo: "ok"
      },
      alerts: []
    });

    console.log(`✅ Created sample machine: ${machineId}\n`);
  } catch (error) {
    console.error("❌ Error creating sample machine:", error);
    throw error;
  }
}

/**
 * Display instructions for creating Firestore indexes
 * These indexes improve query performance
 */
function displayIndexInstructions() {
  console.log("📊 FIRESTORE INDEXES REQUIRED");
  console.log("─────────────────────────────────────────────────────────────");
  console.log("\nTo enable efficient queries, create these composite indexes:");
  console.log("\n1. Go to: https://console.firebase.google.com");
  console.log("2. Select your project: r3-cycle");
  console.log("3. Navigate to: Firestore Database → Indexes");
  console.log("4. Click 'Create Index' for each of the following:\n");

  console.log("INDEX #1: transactions by userId and timestamp");
  console.log("   Collection ID: transactions");
  console.log("   Fields indexed:");
  console.log("   - userId (Ascending)");
  console.log("   - timestamp (Descending)");
  console.log("   Query scope: Collection\n");

  console.log("INDEX #2: transactions by machineId and timestamp");
  console.log("   Collection ID: transactions");
  console.log("   Fields indexed:");
  console.log("   - machineId (Ascending)");
  console.log("   - timestamp (Descending)");
  console.log("   Query scope: Collection\n");

  console.log("INDEX #3: machines by status and lastHeartbeat");
  console.log("   Collection ID: machines");
  console.log("   Fields indexed:");
  console.log("   - status (Ascending)");
  console.log("   - lastHeartbeat (Descending)");
  console.log("   Query scope: Collection\n");

  console.log("INDEX #4: alerts by machineId, status, and createdAt");
  console.log("   Collection ID: alerts");
  console.log("   Fields indexed:");
  console.log("   - machineId (Ascending)");
  console.log("   - status (Ascending)");
  console.log("   - createdAt (Descending)");
  console.log("   Query scope: Collection\n");

  console.log("─────────────────────────────────────────────────────────────");
  console.log("Note: Indexes can take a few minutes to build.");
  console.log("You can also wait for Firestore to auto-create indexes");
  console.log("when you run queries (check console for index URLs).\n");
}

/**
 * Display database schema summary
 */
function displaySchemaSummary() {
  console.log("📋 DATABASE SCHEMA SUMMARY");
  console.log("─────────────────────────────────────────────────────────────");
  console.log("\nCOLLECTIONS:");
  console.log("\n✅ users (existing - updated with new fields)");
  console.log("   - rfidTag: string | null");
  console.log("   - rfidRegisteredAt: Timestamp | null");
  console.log("   - currentPoints: number");
  console.log("   - totalPaperRecycled: number (grams)");
  console.log("   - totalTransactions: number");
  console.log("   - bondsEarned: number");
  console.log("   - lastTransactionAt: Timestamp | null");
  console.log("   + all existing authentication fields\n");

  console.log("⏳ transactions (auto-created on first transaction)");
  console.log("   - userId, rfidTag, machineId");
  console.log("   - weight, weightUnit, weightValid");
  console.log("   - metalDetected, pointsAwarded");
  console.log("   - status, rejectionReason");
  console.log("   - timestamp, syncedAt\n");

  console.log("✅ machines (sample created)");
  console.log("   - id, location, status");
  console.log("   - bondPaperStock, bondPaperCapacity");
  console.log("   - lastHeartbeat, lastMaintenance");
  console.log("   - totalTransactions, totalPaperCollected");
  console.log("   - sensorHealth, alerts\n");

  console.log("⏳ redemptions (auto-created on first redemption)");
  console.log("   Will be implemented in Phase 3\n");

  console.log("⏳ alerts (auto-created on first alert)");
  console.log("   Will be implemented in Phase 4\n");

  console.log("─────────────────────────────────────────────────────────────\n");
}

/**
 * Main initialization function
 */
async function initializeDatabase() {
  console.log("\n🚀 R3-CYCLE DATABASE INITIALIZATION");
  console.log("═══════════════════════════════════════════════════════════════\n");

  try {
    // Step 1: Update existing users
    await updateExistingUsers();

    // Step 2: Create sample machine
    await createSampleMachine();

    // Step 3: Display schema summary
    displaySchemaSummary();

    // Step 4: Display index instructions
    displayIndexInstructions();

    console.log("✅ DATABASE INITIALIZATION COMPLETE!\n");
    console.log("Next steps:");
    console.log("1. Create Firestore indexes (see instructions above)");
    console.log("2. Test API endpoints with Postman or curl");
    console.log("3. Link an RFID card to your user account");
    console.log("4. Start building the Raspberry Pi code\n");

  } catch (error) {
    console.error("\n❌ DATABASE INITIALIZATION FAILED");
    console.error("Error:", error.message);
    process.exit(1);
  }
}

// Run initialization
initializeDatabase()
  .then(() => {
    console.log("Exiting...\n");
    process.exit(0);
  })
  .catch((error) => {
    console.error("Fatal error:", error);
    process.exit(1);
  });
