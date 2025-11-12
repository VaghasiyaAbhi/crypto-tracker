# 🎯 Quick Start - Test Your Setup Now!

## Step 1: Setup (One-time)

```bash
# Navigate to your project
cd /Users/virajsavaliya/Desktop/project/Archive\ 2

# Copy environment file (uses defaults, no editing needed)
cp .env.local.example .env.local

# Make script executable (already done, but just in case)
chmod +x local-dev.sh
```

## Step 2: Start Local Environment

```bash
./local-dev.sh start
```

**Wait 30-60 seconds** for all services to start. You'll see:
```
✅ Local environment started!
Services running:
  📊 Frontend:  http://localhost:3000
  🔧 Backend:   http://localhost:8000
  🔴 Redis:     localhost:6379
  🐘 Postgres:  localhost:5432
```

## Step 3: Test It's Working

```bash
# Check if all services are running
./local-dev.sh status

# Should show 8 services running:
# - postgres
# - redis
# - backend
# - celery-worker
# - celery-beat
# - data-worker
# - calc-worker
# - frontend
```

## Step 4: Open in Browser

```bash
# Open frontend
open http://localhost:3000

# Or manually visit:
# http://localhost:3000 - Your app
# http://localhost:8000 - API
# http://localhost:8000/admin/ - Django admin
```

## Step 5: View Logs

```bash
# View all logs
./local-dev.sh logs

# Or view specific service
./local-dev.sh logs backend
./local-dev.sh logs frontend

# Press Ctrl+C to stop viewing logs
```

## Step 6: Make a Test Change

### Test Frontend Hot Reload

1. Open `frontend/src/app/page.tsx` in your editor
2. Find any text (e.g., "Welcome")
3. Change it to "Welcome - TEST LOCAL"
4. Save the file
5. **Refresh browser** - change appears immediately! ✨

### Test Backend Change

1. Open `backend/core/views.py` in your editor
2. Make a small change
3. Save the file
4. Restart backend:
   ```bash
   ./local-dev.sh restart backend
   ```
5. Check logs:
   ```bash
   ./local-dev.sh logs backend
   ```

## Step 7: Stop When Done

```bash
./local-dev.sh stop
```

---

## 🎉 Success Checklist

- ✅ All 8 services running (`./local-dev.sh status`)
- ✅ Frontend accessible at http://localhost:3000
- ✅ Backend accessible at http://localhost:8000
- ✅ Can view logs (`./local-dev.sh logs`)
- ✅ Frontend hot reload works (change text, see update)
- ✅ Backend restart works (`./local-dev.sh restart backend`)

---

## 🚀 Now You Can:

### 1. **Test N/A Fix**
```bash
# Start environment
./local-dev.sh start

# Open dashboard
open http://localhost:3000/dashboard

# Check if AERGOUSDT shows values (not N/A)
# View backend logs
./local-dev.sh logs backend
```

### 2. **Test Session Timeout**
```bash
# Login at http://localhost:3000
# Wait 2-3 minutes
# Click something - should NOT logout (we fixed this!)
```

### 3. **Make Changes Safely**
```bash
# 1. Edit code
# 2. Test locally (http://localhost:3000)
# 3. If working: git push
# 4. If broken: fix locally, no production impact!
```

---

## ⚡ Common Commands

```bash
# Start everything
./local-dev.sh start

# View logs (all)
./local-dev.sh logs

# View backend logs only
./local-dev.sh logs backend

# Restart backend after code change
./local-dev.sh restart backend

# Check status
./local-dev.sh status

# Stop everything
./local-dev.sh stop

# Get help
./local-dev.sh help
```

---

## 🆘 Troubleshooting

### "Port 3000 already in use"
```bash
# Kill the process using port 3000
lsof -i :3000
kill -9 <PID>

# Then restart
./local-dev.sh start
```

### "Service won't start"
```bash
# View logs to see error
./local-dev.sh logs backend

# Try rebuilding
./local-dev.sh stop
./local-dev.sh start:rebuild
```

### "Can't connect to database"
```bash
# Check postgres is running
./local-dev.sh status

# Restart postgres
./local-dev.sh restart postgres
```

---

## 📚 Full Documentation

- **Complete Guide**: `LOCAL_DEVELOPMENT.md`
- **Quick Reference**: `LOCAL_DEV_CHEATSHEET.md`
- **Help Command**: `./local-dev.sh help`

---

## 🎯 Your Workflow Now

```
┌─────────────────────────────────────────┐
│  1. ./local-dev.sh start                │
│     ↓                                   │
│  2. Make code changes                   │
│     ↓                                   │
│  3. Test at http://localhost:3000       │
│     ↓                                   │
│  4. If working:                         │
│     git add . && git commit && git push │
│     ↓                                   │
│  5. Auto-deploy to production ✨        │
│     https://volusignal.com              │
└─────────────────────────────────────────┘
```

**No more breaking production!** 🎊

Test locally first, then deploy with confidence!
