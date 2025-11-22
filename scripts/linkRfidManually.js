/**
 * Manual RFID Linking Script
 * Links an RFID tag to a user account directly in Firebase
 * Usage: node scripts/linkRfidManually.js [email] [rfidTag]
 */

import { db } from "../models/firebaseConfig.js";
import { collection, query, where, getDocs, updateDoc, doc, Timestamp } from "firebase/firestore";

const userEmail = process.argv[2];
const rfidTag = process.argv[3] || "A1B2C3D4";

if (!userEmail) {
  console.error("\n❌ Error: Email required");
  console.log("\nUsage: node scripts/linkRfidManually.js [email] [rfidTag]");
  console.log("Example: node scripts/linkRfidManually.js user@example.com A1B2C3D4\n");
  process.exit(1);
}

async function linkRfid() {
  try {
    console.log("\n🔍 Searching for user with email:", userEmail);

    // Find user by email
    const usersRef = collection(db, "users");
    const q = query(usersRef, where("email", "==", userEmail));
    const querySnapshot = await getDocs(q);

    if (querySnapshot.empty) {
      console.error("\n❌ User not found with email:", userEmail);
      console.log("\nTip: Check Firebase Console for existing user emails\n");
      process.exit(1);
    }

    const userDoc = querySnapshot.docs[0];
    const userId = userDoc.id;
    const userData = userDoc.data();

    console.log("\n✅ User found:");
    console.log("   Name:", userData.name);
    console.log("   Email:", userData.email);
    console.log("   User ID:", userId);

    // Check if RFID already linked
    if (userData.rfidTag) {
      console.log("\n⚠️  Warning: User already has RFID linked:", userData.rfidTag);
      console.log("   Updating to new RFID:", rfidTag);
    }

    // Link RFID to user
    await updateDoc(doc(db, "users", userId), {
      rfidTag: rfidTag,
      rfidRegisteredAt: Timestamp.now()
    });

    console.log("\n✅ RFID successfully linked!");
    console.log("   RFID Tag:", rfidTag);
    console.log("   User:", userData.name);
    console.log("\n🎉 You can now test the API with this RFID tag!\n");

  } catch (error) {
    console.error("\n❌ Error linking RFID:", error.message);
    process.exit(1);
  }
}

linkRfid();
