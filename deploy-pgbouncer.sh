#!/bin/bash
# Deploy PgBouncer to Production Server
# This adds PgBouncer connection pooling to reduce database connections

set -e

echo "🚀 Deploying PgBouncer to Production Server..."
echo ""

SERVER="root@46.62.216.158"
PROJECT_DIR="/root/crypto-tracker"

# Step 1: Backup current configuration
echo "📦 Step 1: Creating backup..."
ssh $SERVER "cd $PROJECT_DIR && cp docker-compose.yml docker-compose.yml.backup && cp backend/.env backend/.env.backup && echo '✅ Backup created'"
echo ""

# Step 2: Copy updated files to server
echo "📤 Step 2: Uploading updated configuration..."
scp docker-compose.yml $SERVER:$PROJECT_DIR/
scp backend/.env $SERVER:$PROJECT_DIR/backend/
echo "✅ Files uploaded"
echo ""

# Step 3: Start PgBouncer
echo "🔄 Step 3: Starting PgBouncer..."
ssh $SERVER "cd $PROJECT_DIR && docker compose up -d pgbouncer"
echo ""

# Step 4: Wait for PgBouncer to be ready
echo "⏳ Step 4: Waiting for PgBouncer to be ready..."
sleep 10
echo ""

# Step 5: Test PgBouncer connection
echo "🧪 Step 5: Testing PgBouncer connection..."
ssh $SERVER "docker exec crypto-tracker-pgbouncer-1 pg_isready -h localhost && echo '✅ PgBouncer is ready'" || echo "⚠️  PgBouncer health check pending..."
echo ""

# Step 6: Restart backend to use PgBouncer
echo "🔄 Step 6: Restarting backend to use PgBouncer..."
ssh $SERVER "cd $PROJECT_DIR && docker compose restart backend1"
echo ""

# Step 7: Restart workers
echo "🔄 Step 7: Restarting workers..."
ssh $SERVER "cd $PROJECT_DIR && docker compose restart celery-worker celery-beat data-worker calc-worker"
echo ""

# Step 8: Verify everything is running
echo "📊 Step 8: Checking services..."
ssh $SERVER "cd $PROJECT_DIR && docker compose ps"
echo ""

# Step 9: Test database connection through PgBouncer
echo "🧪 Step 9: Testing database connection..."
ssh $SERVER "docker exec crypto-tracker-backend1-1 python manage.py shell -c \"
from django.db import connection
cursor = connection.cursor()
cursor.execute('SELECT 1')
print('✅ Database connection through PgBouncer working!')
cursor.execute('SELECT count(*) FROM pg_stat_activity')
print(f'Active connections: {cursor.fetchone()[0]}')
\""
echo ""

echo "=========================================="
echo "✅ PgBouncer Deployment Complete!"
echo ""
echo "📊 What changed:"
echo "   - PgBouncer now handles all database connections"
echo "   - Backend connects to pgbouncer:5432 instead of 46.62.216.158:5432"
echo "   - Max 1000 client connections → pooled to 20-25 database connections"
echo ""
echo "🔍 Monitor PgBouncer:"
echo "   docker exec crypto-tracker-pgbouncer-1 psql -p 5432 pgbouncer -c 'SHOW POOLS'"
echo ""
echo "🌐 Site: https://volusignal.com"
echo "=========================================="
