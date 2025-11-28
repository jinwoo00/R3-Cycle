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
    
import express from "express";
import http from "http";
import path from "path";
import session from "express-session";
import flash from "connect-flash";
import router from "./routes/index.js";
import iotRouter from "./routes/iot.js";
import fs from 'fs';
import hbs from "hbs";
import { fileURLToPath } from "url";
import { dirname } from "path";
import { initializeSocket } from "./socket/socketServer.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const app = express();
const server = http.createServer(app);
const PORT = process.env.PORT || 3000;

// Initialize Socket.io for real-time communication
const io = initializeSocket(server);

app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(express.static(path.join(process.cwd(), "public")));

app.use(session({
  secret: "xianfire-secret-key",
  resave: false,
  saveUninitialized: false
}));
app.use(flash());

app.engine("xian", async (filePath, options, callback) => {
  try {
     const originalPartialsDir = hbs.partialsDir;
    hbs.partialsDir = path.join(__dirname, 'views');

    const result = await new Promise((resolve, reject) => {
      hbs.__express(filePath, options, (err, html) => {
        if (err) return reject(err);
        resolve(html);
      });
    });

    hbs.partialsDir = originalPartialsDir;
    callback(null, result);
  } catch (err) {
    callback(err);
  }
});
app.use((req, res, next) => {
  res.locals.success_msg = req.flash("success_msg");
  res.locals.error_msg = req.flash("error_msg");
  next();
});


app.set("views", path.join(__dirname, "views"));
app.set("view engine", "xian");

// Register Handlebars helpers
hbs.registerHelper("substring", function(str, start, length) {
  if (!str) return "";
  str = String(str);
  
  // Handle negative start (from the end)
  if (start < 0) {
    if (length) {
      // If length is provided, take that many characters from the end
      // start=-4 means last 4 characters
      return str.slice(start);
    }
    // Just return from start position to end
    return str.slice(start);
  }
  
  // Positive start
  if (length && length > 0) {
    return str.substring(start, start + length);
  } else if (length && length < 0) {
    // Negative length means end position from the end
    return str.substring(start, str.length + length);
  }
  
  return str.substring(start);
});

const partialsDir = path.join(__dirname, "views/partials");
fs.readdir(partialsDir, (err, files) => {
  if (err) {
    console.error("❌ Could not read partials directory:", err);
    return;
  }

   files
    .filter(file => file.endsWith('.xian'))
    .forEach(file => {
      const partialName = file.replace('.xian', ''); 
      const fullPath = path.join(partialsDir, file);

      fs.readFile(fullPath, 'utf8', (err, content) => {
        if (err) {
          console.error(`❌ Failed to read partial: ${file}`, err);
          return;
        }
        hbs.registerPartial(partialName, content);
        
      });
    });
});

// Web routes (authentication, dashboards, etc.)
app.use("/", router);

// IoT API routes (Raspberry Pi communication)
app.use("/api", iotRouter);

export default app;

// Make io available to routes if needed
app.locals.io = io;

if (!process.env.ELECTRON) {
  server.listen(PORT, '0.0.0.0', () => {
    console.log(`🔥 XianFire running at http://0.0.0.0:${PORT}`);
    console.log(`🔌 Socket.io server ready for real-time connections`);
    console.log(`🌐 Access from network: http://192.168.1.18:${PORT}`);
  });
}
