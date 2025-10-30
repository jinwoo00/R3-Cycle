# R3-Cycle Setup Instructions for Team Members

## 🚀 Quick Start Guide

Follow these steps to set up the R3-Cycle project on your local machine.

---

## 📋 Prerequisites

Before you begin, make sure you have:

- **Node.js** (v14 or higher) - [Download here](https://nodejs.org/)
- **Git** - [Download here](https://git-scm.com/)
- **Gmail Account** (for email sending functionality)
- **Firebase Account** - [Create here](https://firebase.google.com/)

---

## 📥 Step 1: Clone the Repository

```bash
git clone <your-repository-url>
cd R3-Cycle
```

---

## 📦 Step 2: Install Dependencies

```bash
npm install
```

This will install all packages listed in `package.json` (takes 2-5 minutes).

---

## 🔧 Step 3: Configure Environment Variables

### 3.1 Create `.env` File

Copy the example file and create your own:

```bash
# On Windows:
copy .env.example .env

# On Mac/Linux:
cp .env.example .env
```

### 3.2 Set Up Gmail for Email Sending

1. **Enable 2-Factor Authentication** on your Gmail account:
   - Go to https://myaccount.google.com/security
   - Enable "2-Step Verification"

2. **Generate App Password**:
   - Go to https://myaccount.google.com/apppasswords
   - Select "Mail" and "Other (Custom name)"
   - Name it "R3-Cycle"
   - Copy the 16-character password (example: `abcd efgh ijkl mnop`)

3. **Update `.env` file**:
   ```env
   EMAIL_USER=your-email@gmail.com
   EMAIL_PASSWORD=your-16-char-app-password
   EMAIL_FROM_ADDRESS=your-email@gmail.com
   ```

### 3.3 Configure Firebase

1. **Create Firebase Project**:
   - Go to https://console.firebase.google.com/
   - Create new project named "R3-Cycle" (or similar)
   - Enable Authentication → Email/Password
   - Enable Firestore Database

2. **Get Firebase Config**:
   - Go to Project Settings → General
   - Scroll to "Your apps" → Web app
   - Copy the Firebase configuration

3. **Update `models/firebaseConfig.js`**:
   ```javascript
   const firebaseConfig = {
     apiKey: "your-api-key",
     authDomain: "your-app.firebaseapp.com",
     projectId: "your-project-id",
     storageBucket: "your-app.appspot.com",
     messagingSenderId: "your-sender-id",
     appId: "your-app-id"
   };
   ```

4. **Configure Firebase Email Templates**:
   - Go to Authentication → Templates
   - Customize "Email address verification" template
   - Add your domain to "Authorized domains" if needed

---

## ▶️ Step 4: Run the Application

```bash
npm start
```

The application will start at: **http://localhost:3000**

You should see:
```
✅ Email server is ready to send messages
XianFire running at http://localhost:3000
```

---

## 🧪 Step 5: Test the System

### Register a New User
1. Navigate to http://localhost:3000/register
2. Create an account with your email
3. Check your email for verification link
4. Verify your email and login

### Test Login Verification
1. Logout and login again
2. You should receive a 6-digit code via email
3. Enter the code to access dashboard

---

## 📁 Project Structure

```
R3-Cycle/
├── controllers/       # Business logic
├── models/           # Firebase & email config
├── routes/           # Express routes
├── views/            # Frontend templates (.xian)
├── public/           # Static files
├── .env              # Your local config (DO NOT COMMIT)
├── .env.example      # Template (committed to Git)
├── package.json      # Dependencies
└── index.js          # Main server file
```

---

## 🔒 Security Best Practices

### ✅ DO:
- Keep `.env` file private (never commit it)
- Use app passwords, not your Gmail password
- Use different credentials for development/production
- Rotate passwords periodically

### ❌ DON'T:
- Commit `.env` to Git
- Share your app password
- Use the same password across environments
- Disable 2FA on email accounts

---

## 🐛 Troubleshooting

### Email Not Sending

**Error: "self-signed certificate"**
- Make sure `NODE_ENV=development` in `.env`
- Check antivirus isn't blocking SMTP

**Error: "Invalid credentials"**
- Verify you're using Gmail App Password (not regular password)
- Check 2FA is enabled
- Regenerate app password if needed

### Firebase Errors

**Error: "Firebase not initialized"**
- Check `models/firebaseConfig.js` has correct credentials
- Ensure Firebase project is created

### Port Already in Use

**Error: "Port 3000 already in use"**
```bash
# Windows:
netstat -ano | findstr :3000
taskkill /PID <process-id> /F

# Mac/Linux:
lsof -ti:3000 | xargs kill
```

---

## 📞 Getting Help

If you encounter issues:

1. Check console logs for error messages
2. Verify all environment variables are set
3. Ensure Firebase is properly configured
4. Ask team lead for help

---

## 🎓 Additional Resources

- [Firebase Docs](https://firebase.google.com/docs)
- [Nodemailer Docs](https://nodemailer.com/)
- [Express.js Guide](https://expressjs.com/)
- [Gmail App Passwords](https://support.google.com/accounts/answer/185833)

---

**Last Updated:** 2025-10-28
**Maintainer:** R3-Cycle Development Team
