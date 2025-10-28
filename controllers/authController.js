
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

      res.render("user/dashboard", {
        title: "Dashboard",
        emailVerified: emailVerified,
        userEmail: userData.email,
        userName: userData.name
      });
    } else {
      res.redirect("/login");
    }
  } catch (error) {
    console.error("Dashboard error:", error.message);
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

      req.session.userId = user.uid;
      req.session.userRole = userData.role;
      req.session.emailVerified = user.emailVerified;

      if (userData.role === "admin") {
        return res.redirect("/adminDashboard.xian");
      } else {
        return res.redirect("/dashboard");
      }
    } else {
      console.log("User Firestore doc not found");
      res.send("User data not found.");
    }
  } catch (error) {
    console.error("Login error:", error.code, error.message);
    res.send("Login failed: " + error.message);
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
    console.error("Registration error:", error.message);
    res.send("Registration failed: " + error.message);
  }
};


export const logoutUser = async (req, res) => {
  try {
    await signOut(auth);
    req.session.destroy();
    res.redirect("/login");
  } catch (error) {
    console.error("Logout error:", error.message);
    res.send("Logout failed");
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
      await updateDoc(doc(db, "users", req.session.userId), {
        emailVerified: true,
        emailVerifiedAt: new Date()
      });
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
