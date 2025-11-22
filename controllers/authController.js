
      /*
    MIT License
    
    Copyright (c) 2025 Christian I. Cabrera || XianFire Framework
    Mindoro State University - Philippines

    Permission is hereby granted, free of charge, to any person obtaining a copy
    of this software and associated documentation files (the "Software"), to deal
    in the Software without restriction, including without limitation the rights
    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
    copies of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in all
    copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
    SOFTWARE.
    */
    
import { auth, db, sendPasswordResetEmail, sendEmailVerification } from "../models/firebaseConfig.js";
import {
  createUserWithEmailAndPassword,
  signInWithEmailAndPassword,
  signOut
} from "firebase/auth";
import { doc, setDoc, getDoc, updateDoc } from "firebase/firestore";
import crypto from "crypto";
import { sendVerificationCodeEmail as sendCodeEmail } from "../models/emailConfig.js";

// ============================================
// HELPER FUNCTIONS FOR VERIFICATION CODES
// ============================================

/**
 * Generate a random 6-digit verification code
 */
function generateVerificationCode() {
  return crypto.randomInt(100000, 999999).toString();
}

/**
 * Send verification code via email using Nodemailer
 */
async function sendVerificationCodeEmail(email, code, userName) {
  try {
    // Use the real email sender from emailConfig.js
    await sendCodeEmail(email, code, userName);

    // Also log to console for debugging
    console.log("=".repeat(50));
    console.log("📧 VERIFICATION CODE EMAIL SENT");
    console.log("=".repeat(50));
    console.log(`To: ${email}`);
    console.log(`User: ${userName}`);
    console.log(`Code: ${code}`);
    console.log(`Expires: 10 minutes`);
    console.log("=".repeat(50));
  } catch (error) {
    console.error("❌ Failed to send verification email:", error.message);
    // Still log the code to console as fallback
    console.log("⚠️ FALLBACK - Code logged to console (email failed):");
    console.log(`   To: ${email}`);
    console.log(`   Code: ${code}`);
    throw error; // Re-throw so caller knows it failed
  }
}

// ============================================
// PAGE CONTROLLERS
// ============================================

export const loginPage = (req, res) => res.render("login", { title: "Login" });
export const registerPage = (req, res) => res.render("register", { title: "Register" });
export const forgotPasswordPage = (req, res) => {
  res.render("forgotpassword", {
    title: "Forgot Password",
    success_msg: req.flash("success_msg"),
    error_msg: req.flash("error_msg")
  });
};
export const dashboardPage = async (req, res) => {
  if (!req.session.userId) return res.redirect("/login");

  try {
    // Get current user from Firebase Auth
    const currentUser = auth.currentUser;

    // Get user data from Firestore
    const userDoc = await getDoc(doc(db, "users", req.session.userId));

    if (userDoc.exists()) {
      const userData = userDoc.data();

      // Check if email is verified
      const emailVerified = currentUser ? currentUser.emailVerified : false;

      // Redirect to verification page if email is not verified
      if (!emailVerified) {
        return res.redirect("/verification-required");
      }

      // Extract first name from full name
      const firstName = userData.name.split(' ')[0];

      // Prepare user data with defaults
      const user = {
        email: userData.email,
        name: userData.name,
        firstName: firstName,
        rfidTag: userData.rfidTag || null,
        rfidRegisteredAt: userData.rfidRegisteredAt || null,
        points: userData.currentPoints || 0
      };

      // Prepare stats with defaults
      const stats = {
        totalWeight: userData.totalPaperRecycled || 0,
        totalRedeemed: userData.bondsEarned || 0
      };

      // Mock rewards data (will be replaced with real data in Phase 3)
      const rewards = [
        { name: "Bond Paper (1 sheet)", cost: 20 },
        { name: "Bond Paper (5 sheets)", cost: 100 },
        { name: "Notebook", cost: 200 }
      ];

      res.render("user/dashboard", {
        title: "Dashboard",
        emailVerified: emailVerified,
        userEmail: userData.email,
        userName: userData.name,
        userFirstName: firstName,
        user: user,
        stats: stats,
        rewards: rewards
      });
    } else {
      res.redirect("/login");
    }
  } catch (error) {
    console.error("Dashboard error:", error.message);
    res.redirect("/login");
  }
};

export const verificationRequiredPage = async (req, res) => {
  if (!req.session.userId) return res.redirect("/login");

  try {
    // Get current user from Firebase Auth
    const currentUser = auth.currentUser;

    // If already verified, redirect to dashboard
    if (currentUser && currentUser.emailVerified) {
      return res.redirect("/dashboard");
    }

    // Get user data from Firestore
    const userDoc = await getDoc(doc(db, "users", req.session.userId));

    if (userDoc.exists()) {
      const userData = userDoc.data();

      res.render("verification-required", {
        title: "Email Verification Required",
        userEmail: userData.email,
        userName: userData.name,
        success_msg: req.flash("success_msg"),
        error_msg: req.flash("error_msg")
      });
    } else {
      res.redirect("/login");
    }
  } catch (error) {
    console.error("Verification page error:", error.message);
    res.redirect("/login");
  }
};

export const loginUser = async (req, res) => {
  const { email, password } = req.body;
  console.log("Login attempt:", email);

  try {
    const userCredential = await signInWithEmailAndPassword(auth, email, password);
    const user = userCredential.user;
    console.log("Firebase login success:", user.uid);
    console.log("Email verified:", user.emailVerified);

    const userDoc = await getDoc(doc(db, "users", user.uid));

    if (userDoc.exists()) {
      const userData = userDoc.data();
      console.log("User role:", userData.role);

      // Store basic session info
      req.session.userId = user.uid;
      req.session.userRole = userData.role;
      req.session.emailVerified = user.emailVerified;

      // ============================================
      // DUAL VERIFICATION LOGIC
      // ============================================

      console.log("📋 User data from Firestore:", {
        email: userData.email,
        initialEmailVerificationComplete: userData.initialEmailVerificationComplete,
        emailVerified: userData.emailVerified
      });

      // NEW USER: First-time registration - needs email link verification
      if (!userData.initialEmailVerificationComplete) {
        console.log("🆕 New user detected - redirecting to email verification page");
        console.log("   Reason: initialEmailVerificationComplete =", userData.initialEmailVerificationComplete);
        return res.redirect("/dashboard");  // Will auto-redirect to verification-required
      }

      // RETURNING USER: Completed initial verification - needs login code
      console.log("🔁 Returning user detected - sending verification code");
      console.log("   Reason: initialEmailVerificationComplete =", userData.initialEmailVerificationComplete);

      // Generate 6-digit code
      const verificationCode = generateVerificationCode();
      const expiresAt = new Date(Date.now() + 10 * 60 * 1000); // 10 minutes

      // Store code in Firestore
      await updateDoc(doc(db, "users", user.uid), {
        loginVerificationCode: verificationCode,
        loginVerificationExpiry: expiresAt,
        loginVerificationAttempts: 0
      });

      // Send code via email
      await sendVerificationCodeEmail(userData.email, verificationCode, userData.name);

      // Store pending verification in session
      req.session.pendingVerification = true;
      req.session.verificationEmail = userData.email;

      // Redirect to code entry page
      req.flash("success_msg", "Verification code sent to your email!");
      return res.redirect("/verify-login-code");

    } else {
      console.log("User Firestore doc not found");
      req.flash("error_msg", "User account not found. Please check your credentials or register.");
      return res.redirect("/login");
    }
  } catch (error) {
    console.error("Login error:", error.code, error.message);

    // Handle specific Firebase auth errors
    let errorMessage = "Login failed. Please try again.";

    if (error.code === "auth/invalid-credential" || error.code === "auth/wrong-password") {
      errorMessage = "Invalid email or password. Please try again.";
    } else if (error.code === "auth/user-not-found") {
      errorMessage = "No account found with this email. Please register first.";
    } else if (error.code === "auth/invalid-email") {
      errorMessage = "Invalid email address format.";
    } else if (error.code === "auth/too-many-requests") {
      errorMessage = "Too many failed login attempts. Please try again later.";
    } else if (error.code === "auth/user-disabled") {
      errorMessage = "This account has been disabled. Please contact support.";
    }

    req.flash("error_msg", errorMessage);
    return res.redirect("/login");
  }
};


export const registerUser = async (req, res) => {
  const { name, email, password, role } = req.body;
  try {
    // Create user account
    const userCredential = await createUserWithEmailAndPassword(auth, email, password);
    const user = userCredential.user;

    // Save user info to Firestore
    await setDoc(doc(db, "users", user.uid), {
      name,
      email,
      role: role || "user",
      emailVerified: false,
      initialEmailVerificationComplete: false,  // Track if they completed first-time verification
      createdAt: new Date(),
      lastVerificationSent: new Date()
    });

    // Send verification email
    try {
      await sendEmailVerification(user, {
        url: 'http://localhost:3000/dashboard',
        handleCodeInApp: false
      });

      console.log("Verification email sent to:", email);

      // Create session
      req.session.userId = user.uid;
      req.session.emailVerified = false;

      // Set success message
      req.flash("success_msg", "Registration successful! Please check your email to verify your account.");

      // Redirect to dashboard (they'll see verification banner)
      res.redirect("/dashboard");

    } catch (emailError) {
      console.error("Failed to send verification email:", emailError);

      // Still allow registration to complete
      req.session.userId = user.uid;
      req.flash("error_msg", "Account created but verification email failed to send. You can resend it from your dashboard.");
      res.redirect("/dashboard");
    }

  } catch (error) {
    console.error("Registration error:", error.code, error.message);

    // Handle specific Firebase auth errors
    let errorMessage = "Registration failed. Please try again.";

    if (error.code === "auth/email-already-in-use") {
      errorMessage = "This email is already registered. Please login instead.";
    } else if (error.code === "auth/invalid-email") {
      errorMessage = "Invalid email address format.";
    } else if (error.code === "auth/weak-password") {
      errorMessage = "Password is too weak. Please use at least 6 characters.";
    } else if (error.code === "auth/operation-not-allowed") {
      errorMessage = "Email/password registration is not enabled. Please contact support.";
    }

    req.flash("error_msg", errorMessage);
    return res.redirect("/register");
  }
};


export const logoutUser = async (req, res) => {
  try {
    // Sign out from Firebase first
    await signOut(auth);

    // Destroy session and redirect immediately
    req.session.destroy((err) => {
      if (err) {
        console.error("Session destruction error:", err);
      }
      // Clear session cookie
      res.clearCookie('connect.sid', { path: '/' });
      // Direct redirect - no intermediate page
      res.redirect(302, '/login');
    });
  } catch (error) {
    console.error("Logout error:", error.message);
    // Even on error, clear session and redirect
    res.clearCookie('connect.sid', { path: '/' });
    res.redirect(302, '/login');
  }
};

export const handleForgotPassword = async (req, res) => {
  const { email } = req.body;

  try {
    // Send password reset email using Firebase
    await sendPasswordResetEmail(auth, email);

    // Set success message
    req.flash("success_msg", "Password reset email sent! Check your inbox.");
    res.redirect("/forgot-password");
  } catch (error) {
    console.error("Password reset error:", error.code, error.message);

    // Handle specific error cases
    let errorMessage = "Failed to send reset email. Please try again.";

    if (error.code === "auth/user-not-found") {
      errorMessage = "No account found with this email address.";
    } else if (error.code === "auth/invalid-email") {
      errorMessage = "Invalid email address format.";
    } else if (error.code === "auth/too-many-requests") {
      errorMessage = "Too many requests. Please try again later.";
    }

    req.flash("error_msg", errorMessage);
    res.redirect("/forgot-password");
  }
};

export const resendVerificationEmail = async (req, res) => {
  if (!req.session.userId) {
    return res.status(401).json({ success: false, message: "Not authenticated" });
  }

  try {
    const currentUser = auth.currentUser;

    if (!currentUser) {
      return res.status(401).json({ success: false, message: "No user logged in" });
    }

    // Check if already verified
    if (currentUser.emailVerified) {
      return res.status(400).json({ success: false, message: "Email is already verified" });
    }

    // Check rate limiting (prevent spam)
    const userDoc = await getDoc(doc(db, "users", req.session.userId));
    if (userDoc.exists()) {
      const userData = userDoc.data();
      const lastSent = userData.lastVerificationSent?.toDate();

      if (lastSent) {
        const minutesSinceLastSent = (Date.now() - lastSent.getTime()) / 1000 / 60;

        if (minutesSinceLastSent < 2) {  // 2 minute cooldown
          return res.status(429).json({
            success: false,
            message: "Please wait 2 minutes before requesting another verification email"
          });
        }
      }
    }

    // Send verification email
    await sendEmailVerification(currentUser, {
      url: 'http://localhost:3000/dashboard',
      handleCodeInApp: false
    });

    // Update last sent time
    await updateDoc(doc(db, "users", req.session.userId), {
      lastVerificationSent: new Date()
    });

    console.log("Verification email resent to:", currentUser.email);

    res.json({
      success: true,
      message: "Verification email sent! Please check your inbox."
    });

  } catch (error) {
    console.error("Resend verification error:", error);

    let errorMessage = "Failed to send verification email. Please try again.";

    if (error.code === "auth/too-many-requests") {
      errorMessage = "Too many requests. Please try again later.";
    }

    res.status(500).json({ success: false, message: errorMessage });
  }
};

export const checkVerificationStatus = async (req, res) => {
  if (!req.session.userId) {
    return res.status(401).json({ success: false, verified: false });
  }

  try {
    const currentUser = auth.currentUser;

    if (!currentUser) {
      return res.status(401).json({ success: false, verified: false });
    }

    // Reload user to get fresh emailVerified status
    await currentUser.reload();

    const isVerified = currentUser.emailVerified;

    // Update session
    req.session.emailVerified = isVerified;

    // Update Firestore
    if (isVerified) {
      console.log("✅ Email verified! Updating Firestore with initialEmailVerificationComplete = true");
      await updateDoc(doc(db, "users", req.session.userId), {
        emailVerified: true,
        emailVerifiedAt: new Date(),
        initialEmailVerificationComplete: true  // Mark that initial verification is done
      });
      console.log("✅ Firestore updated successfully");
    } else {
      console.log("⚠️ Email not yet verified by Firebase");
    }

    res.json({
      success: true,
      verified: isVerified
    });

  } catch (error) {
    console.error("Check verification error:", error);
    res.status(500).json({ success: false, verified: false });
  }
};

// ============================================
// LOGIN CODE VERIFICATION CONTROLLERS
// ============================================

export const verifyLoginCodePage = (req, res) => {
  // Must have pending verification in session
  if (!req.session.pendingVerification || !req.session.userId) {
    return res.redirect("/login");
  }

  res.render("verify-login-code", {
    title: "Verify Login",
    userEmail: req.session.verificationEmail,
    success_msg: req.flash("success_msg"),
    error_msg: req.flash("error_msg")
  });
};

export const submitLoginCode = async (req, res) => {
  const { code } = req.body;

  // Must have pending verification in session
  if (!req.session.pendingVerification || !req.session.userId) {
    return res.redirect("/login");
  }

  try {
    const userDoc = await getDoc(doc(db, "users", req.session.userId));

    if (!userDoc.exists()) {
      req.flash("error_msg", "User not found.");
      return res.redirect("/login");
    }

    const userData = userDoc.data();

    // Check if code exists
    if (!userData.loginVerificationCode) {
      req.flash("error_msg", "No verification code found. Please try logging in again.");
      return res.redirect("/login");
    }

    // Check if code expired
    const expiryTime = userData.loginVerificationExpiry?.toDate();
    if (!expiryTime || new Date() > expiryTime) {
      req.flash("error_msg", "Verification code expired. Please request a new one.");
      return res.redirect("/verify-login-code");
    }

    // Check attempts (max 5 attempts)
    const attempts = userData.loginVerificationAttempts || 0;
    if (attempts >= 5) {
      req.flash("error_msg", "Too many failed attempts. Please request a new code.");
      return res.redirect("/verify-login-code");
    }

    // Verify code
    if (code !== userData.loginVerificationCode) {
      // Increment attempts
      await updateDoc(doc(db, "users", req.session.userId), {
        loginVerificationAttempts: attempts + 1
      });

      const remainingAttempts = 5 - (attempts + 1);
      req.flash("error_msg", `Invalid code. ${remainingAttempts} attempts remaining.`);
      return res.redirect("/verify-login-code");
    }

    // ✅ CODE IS VALID - Complete login
    console.log("✅ Login code verified successfully");

    // Clear verification data
    await updateDoc(doc(db, "users", req.session.userId), {
      loginVerificationCode: null,
      loginVerificationExpiry: null,
      loginVerificationAttempts: 0,
      lastSuccessfulLogin: new Date()
    });

    // Clear pending verification flag
    req.session.pendingVerification = false;
    delete req.session.verificationEmail;

    // Redirect to appropriate dashboard
    if (req.session.userRole === "admin") {
      return res.redirect("/adminDashboard.xian");
    } else {
      return res.redirect("/dashboard");
    }

  } catch (error) {
    console.error("Submit login code error:", error);
    req.flash("error_msg", "An error occurred. Please try again.");
    res.redirect("/verify-login-code");
  }
};

export const resendLoginCode = async (req, res) => {
  // Must have pending verification in session
  if (!req.session.pendingVerification || !req.session.userId) {
    return res.status(401).json({ success: false, message: "Not authenticated" });
  }

  try {
    const userDoc = await getDoc(doc(db, "users", req.session.userId));

    if (!userDoc.exists()) {
      return res.status(404).json({ success: false, message: "User not found" });
    }

    const userData = userDoc.data();

    // Generate new code
    const verificationCode = generateVerificationCode();
    const expiresAt = new Date(Date.now() + 10 * 60 * 1000); // 10 minutes

    // Update code in Firestore
    await updateDoc(doc(db, "users", req.session.userId), {
      loginVerificationCode: verificationCode,
      loginVerificationExpiry: expiresAt,
      loginVerificationAttempts: 0
    });

    // Send code via email
    await sendVerificationCodeEmail(userData.email, verificationCode, userData.name);

    console.log("🔁 Login verification code resent");

    res.json({
      success: true,
      message: "New verification code sent to your email!"
    });

  } catch (error) {
    console.error("Resend login code error:", error);
    res.status(500).json({ success: false, message: "Failed to resend code. Please try again." });
  }
};
