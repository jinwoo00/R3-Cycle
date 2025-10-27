
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
    
import { auth, db } from "../models/firebaseConfig.js";
import {
  createUserWithEmailAndPassword,
  signInWithEmailAndPassword,
  signOut
} from "firebase/auth";
import { doc, setDoc, getDoc } from "firebase/firestore";

export const loginPage = (req, res) => res.render("login", { title: "Login" });
export const registerPage = (req, res) => res.render("register", { title: "Register" });
export const forgotPasswordPage = (req, res) => res.render("forgotpassword", { title: "Forgot Password" });
export const dashboardPage = (req, res) => {
  if (!req.session.userId) return res.redirect("/login");
  res.render("user/dashboard", { title: "Dashboard" });
};

export const loginUser = async (req, res) => {
  const { email, password } = req.body;
  console.log("Login attempt:", email, password); // 👈 check if these appear in console

  try {
    const userCredential = await signInWithEmailAndPassword(auth, email, password);
    const user = userCredential.user;
    console.log("Firebase login success:", user.uid);

    const userDoc = await getDoc(doc(db, "users", user.uid));

    if (userDoc.exists()) {
      const userData = userDoc.data();
      console.log("User role:", userData.role);

      req.session.userId = user.uid;
      req.session.userRole = userData.role;

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
  const { name, email, password, role } = req.body; // include role (optional)
  try {
    const userCredential = await createUserWithEmailAndPassword(auth, email, password);
    const user = userCredential.user;

    // Save user info with role (default: 'user')
    await setDoc(doc(db, "users", user.uid), {
      name,
      email,
      role: role || "user", // defaults to user if not specified
      createdAt: new Date()
    });

    req.session.userId = user.uid;
    res.redirect("/dashboard");
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
