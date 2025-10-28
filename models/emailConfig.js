/*
  Email Configuration for R3-Cycle
  Uses Nodemailer with Gmail SMTP
*/

import nodemailer from "nodemailer";
import dotenv from "dotenv";

// Load environment variables
dotenv.config();

// Determine if we're in development or production
const isDevelopment = process.env.NODE_ENV !== "production";

// Create reusable transporter with environment-aware configuration
const transporter = nodemailer.createTransport({
  host: "smtp.gmail.com",
  port: 587, // Use 587 for STARTTLS (more compatible)
  secure: false, // false for port 587, true for port 465
  auth: {
    user: process.env.EMAIL_USER,
    pass: process.env.EMAIL_PASSWORD,
  },
  tls: {
    // For development/testing: allow self-signed certificates
    // For production: enforce strict certificate validation
    rejectUnauthorized: !isDevelopment,
    // Minimum TLS version for security
    minVersion: "TLSv1.2",
  },
  // Additional debugging for troubleshooting
  logger: isDevelopment, // Enable logging in development
  debug: isDevelopment,  // Enable debug output in development
});

/**
 * Send verification code email
 * @param {string} to - Recipient email address
 * @param {string} code - 6-digit verification code
 * @param {string} userName - User's name
 * @returns {Promise}
 */
export async function sendVerificationCodeEmail(to, code, userName) {
  const mailOptions = {
    from: `${process.env.EMAIL_FROM_NAME} <${process.env.EMAIL_FROM_ADDRESS}>`,
    to: to,
    subject: "Your R3-Cycle Login Verification Code",
    html: `
      <!DOCTYPE html>
      <html>
      <head>
        <style>
          body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
          }
          .container {
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
          }
          .header {
            background: linear-gradient(135deg, #16a34a 0%, #15803d 100%);
            color: white;
            padding: 30px;
            text-align: center;
            border-radius: 10px 10px 0 0;
          }
          .content {
            background: #f9fafb;
            padding: 30px;
            border-radius: 0 0 10px 10px;
          }
          .code-box {
            background: white;
            border: 3px dashed #16a34a;
            padding: 20px;
            text-align: center;
            margin: 30px 0;
            border-radius: 10px;
          }
          .code {
            font-size: 36px;
            font-weight: bold;
            color: #16a34a;
            letter-spacing: 8px;
            font-family: 'Courier New', monospace;
          }
          .footer {
            text-align: center;
            color: #6b7280;
            font-size: 12px;
            margin-top: 20px;
          }
          .warning {
            background: #fef3c7;
            border-left: 4px solid #f59e0b;
            padding: 15px;
            margin: 20px 0;
            border-radius: 5px;
          }
        </style>
      </head>
      <body>
        <div class="container">
          <div class="header">
            <h1>🔐 Login Verification</h1>
          </div>
          <div class="content">
            <p>Hello <strong>${userName}</strong>,</p>

            <p>We received a login request for your R3-Cycle account. Please use the verification code below to complete your login:</p>

            <div class="code-box">
              <div class="code">${code}</div>
              <p style="margin-top: 10px; color: #6b7280;">Enter this code on the verification page</p>
            </div>

            <div class="warning">
              <strong>⏱️ This code expires in 10 minutes</strong><br>
              If you didn't request this code, please ignore this email and secure your account.
            </div>

            <p>For security reasons:</p>
            <ul>
              <li>Never share this code with anyone</li>
              <li>R3-Cycle staff will never ask for this code</li>
              <li>This code can only be used once</li>
            </ul>

            <p>Thank you for helping us keep your account secure!</p>

            <p>Best regards,<br>
            <strong>The R3-Cycle Team</strong></p>
          </div>
          <div class="footer">
            <p>This is an automated email from R3-Cycle. Please do not reply to this email.</p>
            <p>&copy; 2025 R3-Cycle. All rights reserved.</p>
          </div>
        </div>
      </body>
      </html>
    `,
    text: `
Hello ${userName},

We received a login request for your R3-Cycle account.

Your verification code is: ${code}

This code expires in 10 minutes.

If you didn't request this code, please ignore this email and secure your account.

For security reasons:
- Never share this code with anyone
- R3-Cycle staff will never ask for this code
- This code can only be used once

Thank you for helping us keep your account secure!

Best regards,
The R3-Cycle Team

---
This is an automated email from R3-Cycle. Please do not reply to this email.
    `,
  };

  try {
    const info = await transporter.sendMail(mailOptions);
    console.log("✅ Verification code email sent successfully!");
    console.log("   Message ID:", info.messageId);
    console.log("   To:", to);
    console.log("   Code:", code);
    return { success: true, messageId: info.messageId };
  } catch (error) {
    console.error("❌ Failed to send verification code email:", error.message);
    throw error;
  }
}

/**
 * Verify email configuration on startup
 */
export async function verifyEmailConfig() {
  try {
    await transporter.verify();
    console.log("✅ Email server is ready to send messages");
    return true;
  } catch (error) {
    console.error("❌ Email configuration error:", error.message);
    console.error("   Please check your .env file settings");
    return false;
  }
}

export default transporter;
