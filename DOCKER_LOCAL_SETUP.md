# 🐳 Docker Local Development Setup

Complete guide for setting up and running the Crypto Tracker project locally using Docker.

---

## 📋 Prerequisites

1. **Docker Desktop** installed and running
   - Download: https://www.docker.com/products/docker-desktop
   - Minimum version: 20.10.0+
   - RAM allocated to Docker: 4GB+ recommended

2. **Git** (to clone the repository)

3. **Terminal/Command Line** access

---

## 🚀 Quick Start (Automated Setup)

### Option 1: Full Setup with Cleanup

This script will completely clean your Docker environment and set up everything fresh:

```bash
# Make the script executable
chmod +x docker-local-setup.sh

# Run the setup script
./docker-local-setup.sh
```

**What it does:**
- ✅ Stops all running containers
- ✅ Removes all containers, images, volumes, and networks
- ✅ Creates `.env` file if it doesn't exist
- ✅ Creates `docker-compose.local.yml` for local development
- ✅ Builds fresh Docker images
- ✅ Provides next steps

### Option 2: Quick Reset & Start

For a faster cleanup and restart:

```bash
# Make the script executable
chmod +x docker-quick-start.sh

# Run the quick start script
./docker-quick-start.sh
```

---

## 🔧 Manual Setup

If you prefer to set things up manually:

### Step 1: Clean Docker Environment

```bash
# Stop all containers
docker stop $(docker ps -aq)

# Remove all containers
docker rm $(docker ps -aq)

# Remove all images
docker rmi $(docker images -q)

# Remove all volumes
docker volume rm $(docker volume ls -q)

# Clean system
docker system prune -af --volumes
```

### Step 2: Set Up Environment Variables

```bash
# Copy .env.example to backend/.env
cp .env.example backend/.env

# Edit the .env file with your credentials
nano backend/.env
```

**Important variables to update:**
```bash
# Database (for local development)
DATABASE_URL=postgresql://postgres:postgres@db:5432/crypto_tracker_db

# Email configuration (optional for local dev)
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# Stripe keys (optional for local dev)
STRIPE_SECRET_KEY=sk_test_your_key
STRIPE_WEBHOOK_SECRET=whsec_your_secret

# Telegram bot (optional for local dev)
TELEGRAM_BOT_TOKEN=your_bot_token
```

### Step 3: Build and Start Services

```bash
# Build images
docker-compose -f docker-compose.local.yml build --no-cache

# Start services in detached mode
docker-compose -f docker-compose.local.yml up -d

# Or start with logs visible
docker-compose -f docker-compose.local.yml up
```

---

## 📊 Services Overview

The local development setup includes these services:

| Service | Port | Description |
|---------|------|-------------|
| **frontend** | 3000 | Next.js React frontend |
| **backend** | 8000 | Django REST API |
| **db** | 5432 | PostgreSQL database |
| **redis** | 6379 | Redis cache & Celery broker |
| **celery-worker** | - | Background task processor |
| **celery-beat** | - | Task scheduler |

---

## 🌐 Access Your Application

Once services are running:

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **Django Admin**: http://localhost:8000/admin
- **API Documentation**: http://localhost:8000/api/
- **Health Check**: http://localhost:8000/api/healthz/

**Database Connection:**
- Host: `localhost`
- Port: `5432`
- User: `postgres`
- Password: `postgres`
- Database: `crypto_tracker_db`

---

## 🛠️ Common Docker Commands

### View Logs

```bash
# All services
docker-compose -f docker-compose.local.yml logs -f

# Specific service
docker-compose -f docker-compose.local.yml logs -f backend
docker-compose -f docker-compose.local.yml logs -f frontend
docker-compose -f docker-compose.local.yml logs -f celery-worker
```

### Check Service Status

```bash
docker-compose -f docker-compose.local.yml ps
```

### Restart Services

```bash
# Restart all
docker-compose -f docker-compose.local.yml restart

# Restart specific service
docker-compose -f docker-compose.local.yml restart backend
```

### Stop Services

```bash
# Stop all (keeps data)
docker-compose -f docker-compose.local.yml stop

# Stop and remove containers (keeps volumes)
docker-compose -f docker-compose.local.yml down

# Stop and remove everything including volumes
docker-compose -f docker-compose.local.yml down -v
```

### Execute Commands in Containers

```bash
# Django shell
docker-compose -f docker-compose.local.yml exec backend python manage.py shell

# Create superuser
docker-compose -f docker-compose.local.yml exec backend python manage.py createsuperuser

# Run migrations
docker-compose -f docker-compose.local.yml exec backend python manage.py migrate

# Access PostgreSQL
docker-compose -f docker-compose.local.yml exec db psql -U postgres -d crypto_tracker_db

# Access Redis CLI
docker-compose -f docker-compose.local.yml exec redis redis-cli
```

### Rebuild Services

```bash
# Rebuild without cache
docker-compose -f docker-compose.local.yml build --no-cache

# Rebuild and restart
docker-compose -f docker-compose.local.yml up --build -d
```

---

## 🔍 Troubleshooting

### Issue: Port Already in Use

**Error**: `Bind for 0.0.0.0:3000 failed: port is already allocated`

**Solution**:
```bash
# Find what's using the port
lsof -i :3000

# Kill the process
kill -9 <PID>

# Or use a different port in docker-compose.local.yml
ports:
  - "3001:3000"  # Change 3001 to any available port
```

### Issue: Database Connection Failed

**Error**: `django.db.utils.OperationalError: could not connect to server`

**Solution**:
```bash
# Check if database is running
docker-compose -f docker-compose.local.yml ps db

# Check database logs
docker-compose -f docker-compose.local.yml logs db

# Restart database
docker-compose -f docker-compose.local.yml restart db

# Wait for database to be ready
docker-compose -f docker-compose.local.yml exec backend python wait-for-services.sh
```

### Issue: Celery Not Processing Tasks

**Solution**:
```bash
# Check Celery worker logs
docker-compose -f docker-compose.local.yml logs celery-worker

# Restart Celery
docker-compose -f docker-compose.local.yml restart celery-worker celery-beat

# Check if Redis is running
docker-compose -f docker-compose.local.yml exec redis redis-cli ping
```

### Issue: Frontend Not Loading

**Solution**:
```bash
# Check frontend logs
docker-compose -f docker-compose.local.yml logs frontend

# Rebuild frontend
docker-compose -f docker-compose.local.yml build --no-cache frontend
docker-compose -f docker-compose.local.yml up -d frontend

# Check if backend is accessible
curl http://localhost:8000/api/healthz/
```

### Issue: "No space left on device"

**Solution**:
```bash
# Clean Docker system
docker system prune -af --volumes

# Remove unused images
docker image prune -a

# Check Docker disk usage
docker system df
```

### Issue: Migrations Not Applied

**Solution**:
```bash
# Apply migrations manually
docker-compose -f docker-compose.local.yml exec backend python manage.py migrate

# Create new migrations
docker-compose -f docker-compose.local.yml exec backend python manage.py makemigrations

# Check migration status
docker-compose -f docker-compose.local.yml exec backend python manage.py showmigrations
```

---

## 🧪 Testing the Setup

### 1. Check All Services are Running

```bash
docker-compose -f docker-compose.local.yml ps
```

All services should show `Up` status.

### 2. Test Backend API

```bash
curl http://localhost:8000/api/healthz/
```

Should return: `{"status": "healthy", ...}`

### 3. Test Frontend

Open browser: http://localhost:3000

### 4. Test Database Connection

```bash
docker-compose -f docker-compose.local.yml exec backend python manage.py dbshell
```

### 5. Test Celery Worker

```bash
# Check active workers
docker-compose -f docker-compose.local.yml exec celery-worker celery -A project_config inspect active

# Check scheduled tasks
docker-compose -f docker-compose.local.yml exec celery-beat celery -A project_config inspect scheduled
```

---

## 📦 Data Persistence

Docker volumes are used to persist data:

- `postgres_data`: PostgreSQL database files
- `redis_data`: Redis data files

To completely reset the database:

```bash
# Stop and remove everything including volumes
docker-compose -f docker-compose.local.yml down -v

# Restart
docker-compose -f docker-compose.local.yml up -d
```

---

## 🚀 Next Steps After Setup

1. **Create a superuser**:
   ```bash
   docker-compose -f docker-compose.local.yml exec backend python manage.py createsuperuser
   ```

2. **Access Django Admin**: http://localhost:8000/admin

3. **Trigger manual data refresh**:
   ```bash
   curl -X POST http://localhost:8000/api/manual-refresh/ \
     -H "Authorization: Bearer YOUR_JWT_TOKEN"
   ```

4. **View real-time logs**:
   ```bash
   docker-compose -f docker-compose.local.yml logs -f
   ```

---

## 📝 Development Workflow

1. **Start your development day**:
   ```bash
   docker-compose -f docker-compose.local.yml up -d
   ```

2. **Make code changes** (changes are live-reloaded via volumes)

3. **View logs** to debug:
   ```bash
   docker-compose -f docker-compose.local.yml logs -f backend
   ```

4. **Run migrations** after model changes:
   ```bash
   docker-compose -f docker-compose.local.yml exec backend python manage.py makemigrations
   docker-compose -f docker-compose.local.yml exec backend python manage.py migrate
   ```

5. **End your development day**:
   ```bash
   docker-compose -f docker-compose.local.yml stop
   ```

---

## 🔒 Security Notes for Local Development

- Default credentials are used (`postgres/postgres`)
- DEBUG mode is enabled
- CORS is permissive for `localhost`
- This setup is **NOT suitable for production**

For production deployment, use the main `docker-compose.yml` with proper:
- Strong passwords
- DEBUG=0
- Restricted CORS origins
- SSL certificates
- External managed database

---

## 📚 Additional Resources

- [Django Documentation](https://docs.djangoproject.com/)
- [Next.js Documentation](https://nextjs.org/docs)
- [Docker Documentation](https://docs.docker.com/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Celery Documentation](https://docs.celeryproject.org/)

---

## 🆘 Getting Help

If you encounter issues:

1. Check the logs: `docker-compose -f docker-compose.local.yml logs -f`
2. Review the troubleshooting section above
3. Check Docker disk space: `docker system df`
4. Try a fresh setup: `./docker-local-setup.sh`

---

**Happy coding! 🎉**
