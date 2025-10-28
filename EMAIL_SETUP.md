# Email Configuration Guide for R3-Cycle

## Issue: Self-Signed Certificate Error

### Problem
You may encounter this error when sending emails:
```
❌ Failed to send verification email: self-signed certificate in certificate chain
```

### Root Cause
This error occurs when:
1. **Corporate Firewall/Proxy**: Your network intercepts SSL connections and adds its own certificate
2. **Antivirus Software**: Programs like Avast, AVG, Kaspersky intercept HTTPS traffic
3. **Network Configuration**: Some ISPs or networks use SSL inspection
4. **Windows Certificate Issues**: Missing or outdated root certificates

---

## ✅ Best Practice Solution Implemented

### 1. **Environment-Aware Configuration**
The system now automatically adjusts based on environment:

**Development Mode** (NODE_ENV=development):
- Allows self-signed certificates (`rejectUnauthorized: false`)
- Enables detailed logging for debugging
- Uses port 587 with STARTTLS (more compatible)

**Production Mode** (NODE_ENV=production):
- Enforces strict certificate validation (`rejectUnauthorized: true`)
- Disables debug logging
- Maximum security

### 2. **Port 587 vs 465**
We use **port 587 with STARTTLS** instead of port 465 because:
- ✅ Better compatibility with firewalls
- ✅ More widely supported
- ✅ Explicit TLS upgrade (STARTTLS)
- ✅ Easier to debug

### 3. **Configuration Details**
```javascript
{
  host: "smtp.gmail.com",
  port: 587,                    // STARTTLS port
  secure: false,                // false for 587, true for 465
  auth: { user, pass },
  tls: {
    rejectUnauthorized: !isDevelopment,  // Flexible in dev, strict in prod
    minVersion: "TLSv1.2"                 // Security baseline
  }
}
```

---

## 🔧 Additional Troubleshooting

If emails still don't work after the fix, try these solutions:

### Solution 1: Check Gmail App Password
```bash
# Verify in .env file:
EMAIL_USER=r3cycleiot@gmail.com
EMAIL_PASSWORD=ojelxrjoyisckaao    # Must be 16-char app password, not regular password
```

### Solution 2: Disable Antivirus SSL Scanning (Temporarily)
Many antivirus programs intercept SSL connections:
- **Avast**: Settings → Protection → Core Shields → Web Shield → Customize → Uncheck "Enable HTTPS scanning"
- **AVG**: Similar to Avast
- **Kaspersky**: Settings → Additional → Network → Do not scan encrypted connections
- **Windows Defender**: Usually doesn't cause this issue

### Solution 3: Check Windows Certificates
Update Windows root certificates:
```bash
# Run as Administrator
certutil -generateSSTFromWU roots.sst
```

### Solution 4: Use Alternative Port (465)
If port 587 is blocked, modify `models/emailConfig.js`:
```javascript
const transporter = nodemailer.createTransport({
  host: "smtp.gmail.com",
  port: 465,              // Change to 465
  secure: true,           // Change to true for 465
  // ... rest of config
});
```

### Solution 5: Whitelist Gmail SMTP
If behind a corporate firewall, ask IT to whitelist:
- `smtp.gmail.com:587` (STARTTLS)
- `smtp.gmail.com:465` (SSL/TLS)

---

## 🧪 Testing the Fix

### Step 1: Restart Server
```bash
# Stop current server (Ctrl+C)
npm start
```

### Step 2: Watch Startup Logs
You should see:
```
✅ Email server is ready to send messages
XianFire running at http://localhost:3000
```

### Step 3: Test Login
1. Login with existing user (returning user)
2. Should see in console:
   ```
   🔁 Returning user detected - sending verification code
   ✅ Verification code email sent successfully!
      Message ID: <...>
      To: sophiadechosa12@gmail.com
      Code: 123456
   ```
3. **Check email inbox** for verification code

### Step 4: Verify Email Received
- Check **r3cycleiot@gmail.com** inbox
- Email should arrive within 5-30 seconds
- Check spam folder if not in inbox

---

## 📊 Understanding the Logs

### Success Logs:
```
✅ Email server is ready to send messages
✅ Verification code email sent successfully!
   Message ID: <abc123@gmail.com>
   To: user@example.com
   Code: 123456
```

### Error Logs:
```
❌ Failed to send verification email: [error message]
⚠️ FALLBACK - Code logged to console
```

If you see error logs, check:
1. Gmail app password is correct
2. Gmail account has 2FA enabled
3. App password was generated correctly
4. No antivirus blocking connection
5. Internet connection is stable

---

## 🚀 Deployment to Production

When deploying to production:

### 1. Update .env for Production
```env
NODE_ENV=production    # This enforces strict SSL validation
EMAIL_USER=r3cycleiot@gmail.com
EMAIL_PASSWORD=your-app-password
```

### 2. Use Environment Variables on Hosting Platform
Don't commit `.env` to Git. Instead, set environment variables on your hosting:

**Vercel/Netlify:**
```
Dashboard → Settings → Environment Variables
```

**Heroku:**
```bash
heroku config:set NODE_ENV=production
heroku config:set EMAIL_USER=r3cycleiot@gmail.com
heroku config:set EMAIL_PASSWORD=ojelxrjoyisckaao
```

**AWS/Azure/GCP:**
Use their respective environment variable systems

---

## 📧 Gmail Limits

Be aware of Gmail sending limits:

| Account Type | Daily Limit |
|--------------|-------------|
| Free Gmail   | ~500 emails/day |
| Google Workspace | ~2000 emails/day |

For high-volume production use, consider:
- **SendGrid** (100 emails/day free, then $15/month for 40k)
- **AWS SES** ($0.10 per 1000 emails)
- **Mailgun** (5000 emails/month free)

---

## 🔒 Security Best Practices

✅ **Do:**
- Use Gmail App Password (not regular password)
- Keep `.env` file in `.gitignore`
- Set `NODE_ENV=production` in production
- Use `rejectUnauthorized: true` in production
- Rotate app passwords periodically

❌ **Don't:**
- Commit `.env` to Git
- Share app passwords
- Use `rejectUnauthorized: false` in production
- Use regular Gmail password
- Disable 2FA on email account

---

## 📞 Support

If you continue having issues:
1. Check the console logs carefully
2. Verify Gmail app password
3. Try temporarily disabling antivirus
4. Test with a different network
5. Contact your network administrator if behind corporate firewall

---

**Last Updated:** 2025-10-28
**Status:** ✅ Fixed - Self-signed certificate issue resolved
