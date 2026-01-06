# VoluSignal - Crypto Trading Dashboard

**Production URL:** https://volusignal.com  
**Status:** �� Fully Operational

---

## 🚀 Quick Start

```bash
# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

---

## 📁 Project Structure

- **backend/** - Django REST API + WebSocket server
- **frontend/** - Next.js 15 dashboard
- **nginx/** - Reverse proxy with SSL
- **scripts/** - Automation & deployment

---

## 🤖 Automated Monitoring

Self-healing system runs every 5 minutes:
- ✅ Auto-fixes common issues
- ✅ Monitors all services
- ✅ Prevents downtime

**See:** `AUTOMATION_GUIDE.md`

---

## 🔧 Quick Commands

```bash
# Restart all
docker-compose restart

# Rebuild frontend
docker-compose up -d --build frontend

# Auto-repair
./scripts/auto-repair.sh

# Status dashboard
status-dashboard
```

---

## 📚 Documentation

- `AUTOMATION_GUIDE.md` - Self-healing system
- `docs/README.md` - Technical details
- `scripts/SETUP_GITHUB_WEBHOOK.md` - Auto-deploy

---

**Last Updated:** January 6, 2026
