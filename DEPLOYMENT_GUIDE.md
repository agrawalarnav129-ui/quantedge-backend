# QuantEdge NSE — Deployment Guide
## Access from any device, anywhere, with password protection

---

## Architecture

```
Your Phone/Laptop (any device, any network)
        ↓  HTTPS
   Vercel CDN  (React frontend — free)
        ↓  API calls
   Render.com  (Flask backend — free)
        ↓  yfinance
   Yahoo Finance / NSE data
```

---

## STEP 1 — Deploy Backend to Render (free)

### 1a. Create a GitHub repo for your backend

```bash
# On your PC, inside your backend folder
cd C:\Arnav\quantedge\src\

git init
git add app.py requirements.txt render.yaml nse_universe.py nse_universe.json
git commit -m "QuantEdge backend"
```

Go to github.com → New Repository → name it `quantedge-backend` → Create
```bash
git remote add origin https://github.com/YOUR_USERNAME/quantedge-backend.git
git push -u origin main
```

### 1b. Deploy on Render

1. Go to **render.com** → Sign up free (use GitHub login)
2. Click **New** → **Web Service**
3. Connect your `quantedge-backend` GitHub repo
4. Settings:
   - Name: `quantedge-nse`
   - Runtime: **Python 3**
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app --workers 2 --timeout 120 --bind 0.0.0.0:$PORT`
5. Click **Create Web Service**
6. Wait ~3 minutes for build
7. Your backend URL will be: `https://quantedge-nse.onrender.com`

### 1c. Test your backend
Open in browser:
```
https://quantedge-nse.onrender.com/api/health
https://quantedge-nse.onrender.com/api/status
```
Both should return JSON responses.

> **Note:** Render free tier sleeps after 15min of inactivity.
> First request after sleep takes ~30 seconds to wake up.
> To keep it always awake: use uptimerobot.com (free) to ping /api/health every 5 minutes.

---

## STEP 2 — Deploy Frontend to Vercel (free)

### 2a. Set your backend URL in the frontend

In `trading_dashboard.jsx`, the line at the top reads:
```js
const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:5000";
```
This automatically uses the env variable when deployed. You'll set it in Vercel.

### 2b. Create a GitHub repo for your frontend

```bash
# Create a new Vite project (if not already done)
npm create vite@latest quantedge-frontend -- --template react
cd quantedge-frontend
npm install
npm install recharts

# Copy your files in
cp path\to\trading_dashboard.jsx src\App.jsx
cp path\to\vercel.json .
cp path\to\vite.config.js .

git init
git add .
git commit -m "QuantEdge frontend"
```

Go to github.com → New Repository → name it `quantedge-frontend` → Create
```bash
git remote add origin https://github.com/YOUR_USERNAME/quantedge-frontend.git
git push -u origin main
```

### 2c. Deploy on Vercel

1. Go to **vercel.com** → Sign up free (use GitHub login)
2. Click **Add New Project**
3. Import your `quantedge-frontend` repo
4. Framework: **Vite** (auto-detected)
5. **Environment Variables** — click Add:
   - Key: `VITE_API_BASE`
   - Value: `https://quantedge-nse.onrender.com`  ← your Render URL
6. Click **Deploy**
7. Your app URL: `https://quantedge-frontend.vercel.app`

---

## STEP 3 — Access from any device

Open your Vercel URL on any device:
```
https://quantedge-frontend.vercel.app
```

You'll see the password gate. Enter your password and you're in.

---

## Password Management

Passwords are defined in `trading_dashboard.jsx`:
```js
const PASSWORDS = ["quantedge2026", "arnav@qe", "trader99"];
```

To add/remove users:
1. Edit the `PASSWORDS` array
2. `git commit -m "update passwords"` and `git push`
3. Vercel auto-redeploys in ~1 minute

To give someone access: share the URL + one of the passwords.
To revoke access: remove their password and redeploy.

> **Security note:** This is frontend-only password protection — suitable for personal use.
> For stronger security (e.g., sharing with many people), add backend JWT auth.

---

## Keep Backend Alive (Optional but Recommended)

Render free tier sleeps after 15 min of inactivity.

**Option A — UptimeRobot (free, easiest):**
1. Go to uptimerobot.com → Create free account
2. New Monitor → HTTP(s)
3. URL: `https://quantedge-nse.onrender.com/api/health`
4. Interval: every 5 minutes
5. Done — backend stays awake 24/7

**Option B — Upgrade Render** to $7/month for always-on.

---

## Updating Your App

### Update frontend:
```bash
# Edit trading_dashboard.jsx locally, then:
git add src/App.jsx
git commit -m "update dashboard"
git push
# Vercel auto-redeploys in ~60 seconds
```

### Update backend:
```bash
# Edit app.py locally, then:
git add app.py
git commit -m "fix indicator"
git push
# Render auto-redeploys in ~2 minutes
```

---

## Your URLs Summary

| What | URL |
|------|-----|
| Your app (share this) | `https://quantedge-frontend.vercel.app` |
| Backend API | `https://quantedge-nse.onrender.com` |
| Health check | `https://quantedge-nse.onrender.com/api/health` |
| Live data check | `https://quantedge-nse.onrender.com/api/status` |
| Indicator validate | `https://quantedge-nse.onrender.com/api/validate/RELIANCE` |

---

## Troubleshooting

**Scan runs but returns 0 results:**
Render might be timing out. Reduce universe to NIFTY 50 first.

**"Failed to fetch" error in browser:**
CORS issue. Make sure your Render backend has flask-cors installed and `CORS(app)` in app.py.

**Backend URL showing as localhost:**
You forgot to set `VITE_API_BASE` in Vercel environment variables. Go to Vercel → Project → Settings → Environment Variables.

**Render build fails:**
Check that `requirements.txt` includes `gunicorn==22.0.0`.
