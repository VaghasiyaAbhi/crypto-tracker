# 🚀 LOCAL DEV QUICK REFERENCE

## Start/Stop
```bash
./local-dev.sh start          # Start all services
./local-dev.sh start:rebuild  # Rebuild & start
./local-dev.sh stop           # Stop all services
./local-dev.sh status         # Check status
```

## View Logs
```bash
./local-dev.sh logs           # All logs
./local-dev.sh logs backend   # Backend only
./local-dev.sh logs frontend  # Frontend only
```

## Restart Services
```bash
./local-dev.sh restart backend
./local-dev.sh restart frontend
./local-dev.sh restart celery-worker
```

## Database
```bash
./local-dev.sh migrate        # Run migrations
./local-dev.sh superuser      # Create admin user
./local-dev.sh dbshell        # PostgreSQL shell
```

## Development
```bash
./local-dev.sh shell          # Django shell
./local-dev.sh backend-shell  # Backend container
./local-dev.sh frontend-shell # Frontend container
```

## URLs
- Frontend:  http://localhost:3000
- Backend:   http://localhost:8000
- Admin:     http://localhost:8000/admin/

## Workflow
1. `./local-dev.sh start` - Start local environment
2. Make code changes
3. Test at http://localhost:3000
4. `git add . && git commit -m "..." && git push` - Deploy to production

## Help
```bash
./local-dev.sh help
```
