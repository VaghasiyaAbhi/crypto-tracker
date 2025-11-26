#!/bin/bash

# Fix 502 Bad Gateway by restarting all containers properly

echo "🔧 Fixing 502 Bad Gateway Error..."
echo "=================================="

SERVER="root@46.62.216.158"
PROJECT_DIR="/root/crypto-tracker"

echo ""
echo "📡 Connecting to server..."
ssh -o ConnectTimeout=10 $SERVER << 'ENDSSH'
set -e

echo "📂 Navigating to project directory..."
cd /root/crypto-tracker

echo "⏬ Pulling latest code from GitHub..."
git fetch origin main
git reset --hard origin/main

echo "🛑 Stopping all containers..."
docker-compose down

echo "🏗️  Rebuilding containers (this may take a few minutes)..."
docker-compose build --no-cache

echo "🚀 Starting all containers..."
docker-compose up -d

echo "⏳ Waiting 30 seconds for containers to start..."
sleep 30

echo ""
echo "📊 Container Status:"
docker-compose ps

echo ""
echo "🔍 Checking frontend container..."
FRONTEND_STATUS=$(docker-compose ps frontend | grep -c "Up" || echo "0")

if [ "$FRONTEND_STATUS" -eq "0" ]; then
    echo "❌ Frontend container not running!"
    echo "📋 Frontend logs:"
    docker-compose logs --tail=50 frontend
    exit 1
else
    echo "✅ Frontend container is running!"
fi

echo ""
echo "🔍 Checking backend container..."
BACKEND_STATUS=$(docker-compose ps backend1 | grep -c "Up" || echo "0")

if [ "$BACKEND_STATUS" -eq "0" ]; then
    echo "❌ Backend container not running!"
    echo "📋 Backend logs:"
    docker-compose logs --tail=50 backend1
    exit 1
else
    echo "✅ Backend container is running!"
fi

echo ""
echo "🔍 Checking nginx container..."
NGINX_STATUS=$(docker-compose ps nginx | grep -c "Up" || echo "0")

if [ "$NGINX_STATUS" -eq "0" ]; then
    echo "❌ Nginx container not running!"
    echo "📋 Nginx logs:"
    docker-compose logs --tail=50 nginx
    exit 1
else
    echo "✅ Nginx container is running!"
fi

echo ""
echo "✅ All critical containers are running!"
echo ""
echo "🌐 Testing website..."
sleep 5
curl -I https://volusignal.com 2>&1 | head -5

ENDSSH

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "=================================="
    echo "✅ 502 Error Fixed!"
    echo "=================================="
    echo ""
    echo "Your website should now be accessible at:"
    echo "👉 https://volusignal.com"
    echo ""
    echo "⚠️  IMPORTANT: Set up GitHub webhook to prevent this in the future!"
    echo "See SETUP_GITHUB_WEBHOOK.md for instructions."
else
    echo ""
    echo "=================================="
    echo "❌ Fix Failed!"
    echo "=================================="
    echo ""
    echo "The server may be experiencing issues."
    echo "Please check your hosting provider's dashboard."
fi

exit $EXIT_CODE
