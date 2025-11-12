# 🚀 Local Development Guide

Complete guide for testing code changes locally with Docker before deploying to production.

---

## 📋 Prerequisites

- ✅ Docker Desktop installed and running
- ✅ Git installed
- ✅ Terminal access (macOS Terminal/iTerm2)
- ✅ Code editor (VS Code, etc.)

---

## 🎯 Quick Start

### Step 1: Setup Environment Variables

```bash
# Copy the example environment file
cp .env.local.example .env.local

# Edit with your settings (optional - defaults work fine)
nano .env.local
```

**Default settings work out of the box!** The local environment includes:
- PostgreSQL database in Docker
- Redis in Docker
- All services configured automatically

### Step 2: Start Local Environment

```bash
# Make script executable (first time only)
chmod +x local-dev.sh

# Start everything
./local-dev.sh start
```

**That's it!** Your local environment is running:
- 📊 Frontend: http://localhost:3000
- 🔧 Backend API: http://localhost:8000
- 🔴 Redis: localhost:6379
- 🐘 PostgreSQL: localhost:5432

---

## 🛠️ Common Commands

### Starting & Stopping

```bash
# Start local development environment
./local-dev.sh start

# Start with rebuild (after code changes)
./local-dev.sh start:rebuild

# Stop all services
./local-dev.sh stop

# Check status
./local-dev.sh status
```

### Viewing Logs

```bash
# View all logs
./local-dev.sh logs

# View specific service logs
./local-dev.sh logs backend
./local-dev.sh logs frontend
./local-dev.sh logs celery-worker

# Follow logs in real-time (Ctrl+C to exit)
./local-dev.sh logs backend
```

### Restarting Services

```bash
# Restart backend after code changes
./local-dev.sh restart backend

# Restart frontend
./local-dev.sh restart frontend

# Restart specific worker
./local-dev.sh restart celery-worker
```

### Database Operations

```bash
# Run migrations
./local-dev.sh migrate

# Create superuser for admin access
./local-dev.sh superuser

# Access database shell
./local-dev.sh dbshell
```

### Development Tools

```bash
# Open Django shell
./local-dev.sh shell

# Access backend container
./local-dev.sh backend-shell

# Access frontend container
./local-dev.sh frontend-shell

# Collect static files
./local-dev.sh static

# Run tests
./local-dev.sh test
```

### Cleanup

```bash
# Remove all containers and volumes
./local-dev.sh cleanup
```

---

## 🔄 Development Workflow

### 1. **Start Local Environment**

```bash
./local-dev.sh start
```

### 2. **Make Code Changes**

Edit your code in:
- `backend/` - Django backend code
- `frontend/` - Next.js frontend code

**Changes are auto-detected!**
- Backend: Volume mounted, restart backend to apply changes
- Frontend: Hot reload enabled, changes appear immediately

### 3. **Test Changes Locally**

```bash
# View logs to see if changes work
./local-dev.sh logs backend

# Restart backend if needed
./local-dev.sh restart backend

# Test in browser
open http://localhost:3000
```

### 4. **Verify Everything Works**

- ✅ Frontend loads correctly
- ✅ API calls work
- ✅ Database operations work
- ✅ No errors in logs
- ✅ Features work as expected

### 5. **Push to Production**

```bash
# Add your changes
git add .

# Commit with descriptive message
git commit -m "fix: your change description"

# Push to trigger auto-deployment
git push origin main

# Monitor deployment
open https://github.com/VaghasiyaAbhi/crypto-tracker/actions
```

---

## 📊 Testing Specific Features

### Test N/A Values Fix

```bash
# 1. Start local environment
./local-dev.sh start

# 2. Check backend logs
./local-dev.sh logs backend

# 3. Run calculation task manually
./local-dev.sh backend-shell
python manage.py shell
>>> from core.tasks import calculate_crypto_metrics_task
>>> calculate_crypto_metrics_task()
>>> exit()

# 4. Open frontend and check dashboard
open http://localhost:3000/dashboard
```

### Test Session Timeout

```bash
# 1. Login at http://localhost:3000
# 2. Wait 2-3 minutes
# 3. Click something - should NOT logout
# 4. Wait 15+ minutes - should logout
```

### Test Database Changes

```bash
# 1. Make model changes in backend/core/models.py
# 2. Create migrations
./local-dev.sh backend-shell
python manage.py makemigrations
exit

# 3. Run migrations
./local-dev.sh migrate

# 4. Verify in database
./local-dev.sh dbshell
\dt  # List tables
SELECT * FROM core_cryptodata LIMIT 5;
\q
```

---

## 🔍 Troubleshooting

### Port Already in Use

```bash
# Check what's using the port
lsof -i :3000  # Frontend
lsof -i :8000  # Backend

# Kill the process
kill -9 <PID>

# Or stop local environment and restart
./local-dev.sh stop
./local-dev.sh start
```

### Container Won't Start

```bash
# View logs for specific container
./local-dev.sh logs backend

# Rebuild from scratch
./local-dev.sh stop
docker-compose -f docker-compose.local.yml build --no-cache backend
./local-dev.sh start
```

### Database Connection Issues

```bash
# Check if postgres is running
./local-dev.sh status

# Restart postgres
./local-dev.sh restart postgres

# Check database logs
./local-dev.sh logs postgres
```

### Redis Connection Issues

```bash
# Check redis status
docker-compose -f docker-compose.local.yml exec redis redis-cli ping

# Should return "PONG"

# Restart redis
./local-dev.sh restart redis
```

### Frontend Build Errors

```bash
# Access frontend container
./local-dev.sh frontend-shell

# Reinstall dependencies
rm -rf node_modules package-lock.json
npm install
exit

# Restart frontend
./local-dev.sh restart frontend
```

### Backend Import Errors

```bash
# Access backend container
./local-dev.sh backend-shell

# Reinstall requirements
pip install -r requirements.txt
exit

# Restart backend
./local-dev.sh restart backend
```

---

## 🎨 Environment Differences

### Local vs Production

| Feature | Local | Production |
|---------|-------|------------|
| **Database** | PostgreSQL in Docker | External PostgreSQL |
| **Debug Mode** | `DEBUG=True` | `DEBUG=False` |
| **HTTPS** | HTTP only | HTTPS with SSL |
| **Domain** | localhost:3000 | volusignal.com |
| **Auto-reload** | ✅ Enabled | ❌ Disabled |
| **Volume mounts** | ✅ Code mounted | ❌ Copied in image |

---

## 📂 File Structure

```
Archive 2/
├── docker-compose.local.yml    # Local Docker Compose config
├── .env.local.example           # Environment variables template
├── .env.local                   # Your local environment (git ignored)
├── local-dev.sh                 # Development helper script
├── docker-compose.prod.yml      # Production config (DO NOT USE LOCALLY)
├── docker-compose.yml           # Production config
├── backend/
│   ├── core/
│   │   ├── models.py           # Database models
│   │   ├── views.py            # API endpoints
│   │   ├── tasks.py            # Celery tasks
│   │   └── ...
│   ├── project_config/
│   │   ├── settings.py         # Django settings
│   │   └── ...
│   └── requirements.txt
└── frontend/
    ├── src/
    │   ├── app/
    │   │   ├── dashboard/
    │   │   └── ...
    │   └── components/
    └── package.json
```

---

## 🚦 Complete Example Workflow

### Scenario: Fix a bug in dashboard

```bash
# 1. Start local environment
./local-dev.sh start

# 2. Open in browser
open http://localhost:3000/dashboard

# 3. Identify issue in logs
./local-dev.sh logs backend

# 4. Edit code
# Open frontend/src/app/dashboard/page.tsx in VS Code
# Make your changes

# 5. Frontend auto-reloads - check browser
# Changes appear immediately

# 6. Edit backend code if needed
# Open backend/core/tasks.py in VS Code
# Make your changes

# 7. Restart backend to apply changes
./local-dev.sh restart backend

# 8. Check logs for errors
./local-dev.sh logs backend

# 9. Test in browser
# Verify fix works at http://localhost:3000/dashboard

# 10. If working, commit and push
git add .
git commit -m "fix: dashboard bug description"
git push origin main

# 11. Monitor production deployment
open https://github.com/VaghasiyaAbhi/crypto-tracker/actions

# 12. Stop local environment when done
./local-dev.sh stop
```

---

## 💡 Pro Tips

### 1. **Keep Local Environment Running**
```bash
# Start once in the morning
./local-dev.sh start

# Make changes throughout the day
# Frontend auto-reloads
# Backend just needs restart

# Stop when done for the day
./local-dev.sh stop
```

### 2. **Quick Backend Testing**
```bash
# After code changes
./local-dev.sh restart backend && ./local-dev.sh logs backend
```

### 3. **Use Multiple Terminals**
- Terminal 1: Keep logs running (`./local-dev.sh logs`)
- Terminal 2: Run commands, restart services
- Terminal 3: Git operations

### 4. **Database Reset (if needed)**
```bash
./local-dev.sh stop
docker volume rm archive-2_postgres_data_local
./local-dev.sh start
./local-dev.sh migrate
```

### 5. **Compare with Production**
```bash
# Local
curl http://localhost:8000/api/cryptos/ | jq

# Production
curl https://volusignal.com/api/cryptos/ | jq
```

---

## 🎯 Next Steps

1. ✅ **Setup**: Run `./local-dev.sh start`
2. ✅ **Test**: Make a small change, verify it works locally
3. ✅ **Deploy**: Push to git, let CI/CD deploy to production
4. ✅ **Monitor**: Check production logs and functionality

---

## 📞 Need Help?

### View Available Commands
```bash
./local-dev.sh help
```

### Check Service Health
```bash
./local-dev.sh status
```

### View All Logs
```bash
./local-dev.sh logs
```

---

**Happy Coding! 🚀**

Your local environment is now ready for testing changes before production deployment!
