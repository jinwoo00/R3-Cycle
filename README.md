# R3-Cycle

**IoT-Enabled Smart Recycling Management System**

An innovative recycling solution that incentivizes paper recycling through automated rewards. Built with the XianFire Framework, R3-Cycle connects to smart IoT vending machines that weigh paper, detect contaminants, and instantly award points to users' accounts.

---

## Overview

R3-Cycle is a web-based application designed to promote environmental sustainability through gamification and IoT technology. The system allows users to recycle paper using smart vending machines and earn reward points that can be redeemed for coupon bonds.

**Conversion Rate:** 3 Used Papers = 1 Coupon Bond

### Key Features

- **IoT Integration**: Smart vending machines with weight sensors and contaminant detection
- **Automated Rewards**: Instant point allocation based on paper weight and quality
- **User Dashboard**: Track recycling activity, view points, and redeem rewards
- **Admin Dashboard**: Monitor machine status, manage user points, and view system metrics
- **Role-Based Access**: Separate interfaces for users and administrators
- **Password Recovery**: Firebase-powered email-based password reset
- **Real-Time Monitoring**: Machine status, supply levels, and alert system
- **Activity Logging**: Complete transaction history and user activity tracking

### Target Users

- **Students**: Recycle paper and earn rewards (coupon bonds)
- **Administrators**: Monitor machines, manage users, and track system metrics
- **General Public**: Anyone with a registered card can participate

---

## Technology Stack

### Backend
- **Node.js** with ES6 Modules
- **Express.js** v4.19.2 - Web framework
- **Firebase SDK** v10.12.0
  - Firebase Authentication (email/password)
  - Cloud Firestore (NoSQL database)
  - Password reset emails
- **Express Session** v1.17.3 - Session management
- **Connect Flash** v0.1.1 - Flash messages
- **Bcrypt** v5.1.0 - Password hashing

### Frontend
- **Custom .xian View Engine** - Built on Handlebars (hbs v4.2.0)
- **Tailwind CSS** - Modern, responsive styling
- **Responsive Design** - Mobile-first approach

### Database
- **Cloud Firestore** (NoSQL)
  - `users` collection: name, email, role, createdAt
  - Collections auto-created on first write

---

## Installation & Setup

### Prerequisites

- **Node.js** (v14 or higher recommended)
- **npm** (comes with Node.js)
- **Firebase Account** (free tier sufficient)
- **Git** (for version control)

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd R3-Cycle
```

### Step 2: Install Dependencies

```bash
npm install
```

### Step 3: Configure Firebase

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Create a new project or use an existing one
3. Enable **Authentication**:
   - Go to Authentication → Sign-in method
   - Enable **Email/Password** provider
4. Enable **Firestore Database**:
   - Go to Firestore Database
   - Create database (start in test mode or configure security rules)
5. Get your Firebase configuration:
   - Go to Project Settings → General → Your apps
   - Copy the Firebase config object
6. Update `models/firebaseConfig.js` with your credentials:

```javascript
const firebaseConfig = {
  apiKey: "YOUR_API_KEY",
  authDomain: "YOUR_PROJECT.firebaseapp.com",
  projectId: "YOUR_PROJECT_ID",
  storageBucket: "YOUR_PROJECT.appspot.com",
  messagingSenderId: "YOUR_SENDER_ID",
  appId: "YOUR_APP_ID"
};
```

### Step 4: Configure Firebase Email Settings (for Password Reset)

1. Go to Firebase Console → Authentication → Templates
2. Configure **Password reset** email template
3. Set the redirect URL to your application domain
4. Add authorized domains:
   - Go to Authentication → Settings → Authorized domains
   - Add `localhost` (for testing)
   - Add your production domain

### Step 5: Start the Application

**Development mode (with auto-restart):**
```bash
npm run xian
```
*Note: Requires nodemon to be installed globally or as a dev dependency*

**Production mode:**
```bash
npm run xian-start
```

The application will be available at: **http://localhost:3000**

---

## Usage

### Available NPM Scripts

- `npm run xian-start` - Start the server
- `npm run xian` - Start with nodemon (auto-restart on changes)
- `npm run migrate` - Run migrations (no-op for Firebase)
- `npm run create:model` - Generate a new model file
- `npm run create:controller` - Generate a new controller file

### Access Points

| Route | Description | Access Level |
|-------|-------------|--------------|
| `/` | Landing page | Public |
| `/login` | Login page | Public |
| `/register` | Registration page | Public |
| `/forgot-password` | Password reset | Public |
| `/dashboard` | User dashboard | Authenticated users |
| `/adminDashboard.xian` | Admin control panel | Admin role only |
| `/logout` | Logout | Authenticated users |

### Creating User Accounts

**Regular User:**
1. Navigate to `/register`
2. Fill in name, email, and password
3. Submit the form
4. Role defaults to "user"

**Admin User:**
1. Register a regular account first
2. Go to Firebase Console → Firestore Database
3. Find the user document in the `users` collection
4. Edit the document and change `role` from `"user"` to `"admin"`
5. Log out and log back in

---

## Project Structure

```
R3-Cycle/
├── controllers/              # Business logic
│   ├── authController.js     # Authentication (login, register, logout, password reset)
│   └── homeController.js     # Home page controller
├── models/                   # Data layer
│   └── firebaseConfig.js     # Firebase initialization and configuration
├── routes/                   # Route definitions
│   └── index.js              # All application routes
├── views/                    # View templates (.xian files)
│   ├── partials/             # Reusable components
│   │   ├── head.xian         # HTML head with Tailwind CDN
│   │   ├── footer.xian       # Simple footer
│   │   └── myFooter.xian     # Main footer with university info
│   ├── user/                 # User-specific views
│   │   └── dashboard.xian    # User dashboard
│   ├── adminDashboard.xian   # Admin control panel
│   ├── forgotpassword.xian   # Password reset page
│   ├── home.xian             # Landing page
│   ├── login.xian            # Login page
│   └── register.xian         # Registration page
├── public/                   # Static assets
│   └── tailwind.css          # Tailwind directives
├── create.js                 # CLI tool for generating models/controllers
├── migrate.js                # Migration script (no-op for Firebase)
├── index.js                  # Application entry point
├── package.json              # Dependencies and scripts
└── README.md                 # This file
```

---

## Features in Detail

### User Dashboard

- **Points Balance**: View current reward points
- **Recycling Stats**: Total paper recycled (in grams)
- **Rewards Counter**: Track coupon bonds earned
- **Redemption Interface**: Browse and redeem available rewards
- **Transaction History**: Complete log of recycling activities with:
  - Date and time
  - Weight contributed
  - Points earned
  - Transaction status
- **Progress Tracker**: Papers toward next coupon bond (X/3)

### Admin Dashboard

- **System Metrics**:
  - Total papers recycled
  - Coupon bonds issued
  - Active users
  - Pending alerts
  - Growth indicators for each metric

- **Active Alerts System**:
  - Reward paper low warnings
  - Printer ink low alerts
  - Machine offline notifications
  - Dismissible badges with timestamps

- **Machine Activity Monitoring**:
  - Machine ID tracking
  - Online/offline status
  - Coupon paper stock levels (visual progress bars)
  - Printer ink levels (color-coded indicators)
  - Last activity timestamps

- **User Points Management**:
  - Search users by ID
  - View current points and progress
  - Add/remove points with reason logging
  - Real-time updates

- **User Activity Logs**:
  - User ID and name
  - Papers recycled count
  - Coupon bonds earned
  - Total weight (kg)
  - Transaction timestamps

- **Real-Time Clock Display**

### Password Reset

- Email-based password reset via Firebase
- Secure token generation (1-hour expiration)
- User-friendly error messages
- Success/error feedback with flash messages
- Handles:
  - Non-existent email addresses
  - Invalid email formats
  - Rate limiting (too many requests)

### IoT Integration

- **Smart Vending Machines** with:
  - Weight sensors for paper measurement
  - Contaminant detection technology
  - Real-time status reporting
  - Supply level monitoring
  - Alert generation for maintenance
  - Activity logging

---

## API Routes

### Authentication Routes

| Method | Route | Handler | Description |
|--------|-------|---------|-------------|
| GET | `/` | `homeController.homePage` | Landing page |
| GET | `/login` | `authController.loginPage` | Login page |
| POST | `/login` | `authController.loginUser` | Process login |
| GET | `/register` | `authController.registerPage` | Registration page |
| POST | `/register` | `authController.registerUser` | Process registration |
| GET | `/forgot-password` | `authController.forgotPasswordPage` | Forgot password page |
| POST | `/forgot-password` | `authController.handleForgotPassword` | Send reset email |
| GET | `/logout` | `authController.logoutUser` | Logout user |

### Dashboard Routes

| Method | Route | Protection | Description |
|--------|-------|------------|-------------|
| GET | `/dashboard` | Session required | User dashboard |
| GET | `/adminDashboard.xian` | Admin role required | Admin control panel |

### Route Protection

- **User Routes**: Check `req.session.userId`
- **Admin Routes**: Check `req.session.userRole === "admin"`
- Unauthorized access redirects to `/login`

---

## CLI Tools

### Code Generator (`create.js`)

Generate controllers and models with pre-configured templates:

**Generate a controller:**
```bash
npm run create:controller userController
```

**Generate a model:**
```bash
npm run create:model User
```

Features:
- Auto-creates directories if needed
- Includes MIT license header
- Named exports format
- Proper case conversion (PascalCase for models, camelCase for controllers)

### Migration Tool (`migrate.js`)

```bash
npm run migrate
```

Displays: "Firebase doesn't require migrations"

Firebase creates collections automatically on first document write, so traditional migrations are not needed.

---

## Configuration

### Firebase Security Rules (Recommended)

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /users/{userId} {
      allow read, write: if request.auth != null && request.auth.uid == userId;
    }
  }
}
```

### Session Configuration

- **Secret**: `"xianfire-secret-key"` (change in production)
- **Store**: In-memory (use Redis/MongoDB for production)
- **Resave**: false
- **SaveUninitialized**: false

### Port Configuration

- **Default**: 3000
- **Environment Variable**: `PORT`
- **Electron Mode**: Supported via `process.env.ELECTRON`

### Environment Variables (Recommended for Production)

Create a `.env` file:

```env
PORT=3000
SESSION_SECRET=your-secret-key-here
NODE_ENV=production
```

---

## Custom View Engine (.xian)

R3-Cycle uses a custom view engine built on Handlebars:

- **File Extension**: `.xian`
- **Template Engine**: Handlebars
- **Partials Support**: `{{> partialName}}`
- **Auto-Registration**: Partials from `views/partials/` are auto-loaded
- **Conditional Rendering**: `{{#if}}`, `{{#unless}}`, `{{#each}}`
- **Flash Messages**: `{{error_msg}}`, `{{success_msg}}`

---

## Security Considerations

- Firebase handles password hashing automatically
- Session secret should be an environment variable in production
- HTTPS recommended for production deployment
- Input validation should be added for forms
- CORS configuration not included (add if building REST API)
- Rate limiting handled partially by Firebase (consider express-rate-limit)
- Firebase security rules should be configured for production

---

## Deployment

### Recommended Platforms

- **Heroku**: Node.js hosting with easy deployment
- **Vercel**: Serverless deployment for Node.js
- **Google Cloud Run**: Container-based deployment
- **Railway**: Simple deployment with auto-scaling
- **Render**: Free tier available for web services

### Pre-Deployment Checklist

- [ ] Change session secret to environment variable
- [ ] Configure Firebase security rules
- [ ] Set up production Firebase authorized domains
- [ ] Use external session store (Redis/MongoDB)
- [ ] Enable HTTPS
- [ ] Set NODE_ENV=production
- [ ] Configure proper error handling
- [ ] Add logging middleware
- [ ] Set up monitoring and alerts
- [ ] Configure CORS if needed

---

## Credits

### Author
**Christian I. Cabrera**
Creator of the XianFire Framework

### Institution
**Mindoro State University**
College of Information Technology
Philippines

### Framework
**XianFire Framework**
An IoT-Enabled Recycling Solution built with ❤️ at Mindoro State University

### License
MIT License
Copyright (c) 2025 Christian I. Cabrera

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

---

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

### Development Guidelines

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## Support

For support, please contact:
- **Email**: [Your contact email]
- **Institution**: Mindoro State University - College of Information Technology

---

## Roadmap

### Future Enhancements

- [ ] REST API for mobile application integration
- [ ] Multi-language support (internationalization)
- [ ] Advanced analytics dashboard with charts
- [ ] QR code generation for user cards
- [ ] Email notifications for rewards and updates
- [ ] Social features (leaderboards, achievements)
- [ ] Integration with more IoT devices
- [ ] Mobile application (React Native/Flutter)
- [ ] Export reports (PDF/CSV)
- [ ] Two-factor authentication
- [ ] Reward marketplace expansion
- [ ] Carbon footprint calculator

---

## Acknowledgments

- Built with the XianFire Framework
- Powered by Firebase
- Styled with Tailwind CSS
- Inspired by environmental sustainability initiatives
- Special thanks to Mindoro State University

---

**Made with ❤️ for a greener future**
