# 🎬 VAULTSTREAM — Your Local Video Platform

## How to Run (Windows)

### Step 1 — Install Python
1. Go to https://python.org
2. Click "Download Python"
3. Run the installer
4. ✅ IMPORTANT: Check "Add Python to PATH" before clicking Install

### Step 2 — Start the app
Double-click **START.bat**
That's it! It will install everything and start the server.

### Step 3 — Open your browser
Go to: **http://localhost:5000**

---

## What you can do
- 📁 Upload videos (drag & drop or click)
- ▶️  Watch any video in your browser
- 🗑  Delete videos
- 💾 Download videos

## Supported formats
MP4, MKV, MOV, AVI, WEBM

## Where are my videos stored?
In the `videos/` folder next to app.py

---

## Project Structure
```
vaultstream/
├── app.py              ← Main server (Python)
├── requirements.txt    ← Libraries needed
├── START.bat           ← Double-click to run on Windows
├── videos/             ← Your videos go here
└── templates/
    ├── index.html      ← Home page
    └── watch.html      ← Video player page
```
