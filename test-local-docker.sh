#!/bin/bash

# Comprehensive Local Docker Environment Test Script
# Tests all components and verifies they're working correctly

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🧪 Testing Local Docker Environment${NC}"
echo "=========================================="
echo ""

# Test 1: Check Docker is running
echo -e "${BLUE}Test 1: Docker Service${NC}"
if docker ps > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Docker is running${NC}"
else
    echo -e "${RED}❌ Docker is not running. Please start Docker first.${NC}"
    exit 1
fi
echo ""

# Test 2: Check all required containers
echo -e "${BLUE}Test 2: Container Status${NC}"
REQUIRED_CONTAINERS=(
    "crypto-tracker-postgres-local"
    "crypto-tracker-redis-local"
    "crypto-tracker-backend-local"
    "crypto-tracker-celery-worker-local"
    "crypto-tracker-celery-beat-local"
    "crypto-tracker-data-worker-local"
    "crypto-tracker-calc-worker-local"
)

ALL_RUNNING=true
for container in "${REQUIRED_CONTAINERS[@]}"; do
    if docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
        STATUS=$(docker inspect -f '{{.State.Status}}' "$container" 2>/dev/null || echo "unknown")
        HEALTH=$(docker inspect -f '{{.State.Health.Status}}' "$container" 2>/dev/null || echo "no healthcheck")
        if [ "$STATUS" == "running" ]; then
            echo -e "${GREEN}✅ $container: $STATUS ($HEALTH)${NC}"
        else
            echo -e "${YELLOW}⚠️  $container: $STATUS ($HEALTH)${NC}"
        fi
    else
        echo -e "${RED}❌ $container: NOT FOUND${NC}"
        ALL_RUNNING=false
    fi
done
echo ""

# Test 3: Check Frontend (optional)
echo -e "${BLUE}Test 3: Frontend Status${NC}"
if docker ps --format '{{.Names}}' | grep -q "crypto-tracker-frontend-local"; then
    echo -e "${GREEN}✅ Frontend container is running${NC}"
else
    echo -e "${YELLOW}⚠️  Frontend container not running (this is optional for backend testing)${NC}"
fi
echo ""

# Test 4: Test Backend API
echo -e "${BLUE}Test 4: Backend API Health${NC}"
sleep 2  # Give backend time to start
BACKEND_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/health/ 2>/dev/null || echo "000")
if [ "$BACKEND_RESPONSE" == "200" ]; then
    echo -e "${GREEN}✅ Backend API is responding (HTTP 200)${NC}"
elif [ "$BACKEND_RESPONSE" == "404" ]; then
    echo -e "${YELLOW}⚠️  Backend is running but /api/health/ endpoint not found (HTTP 404)${NC}"
    echo "   Trying alternative endpoint..."
    ALT_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/crypto/ 2>/dev/null || echo "000")
    if [ "$ALT_RESPONSE" == "200" ] || [ "$ALT_RESPONSE" == "401" ]; then
        echo -e "${GREEN}✅ Backend API is accessible (HTTP $ALT_RESPONSE)${NC}"
    else
        echo -e "${RED}❌ Backend API not accessible (HTTP $ALT_RESPONSE)${NC}"
    fi
else
    echo -e "${RED}❌ Backend not responding (HTTP $BACKEND_RESPONSE)${NC}"
fi
echo ""

# Test 5: Test Database Connection
echo -e "${BLUE}Test 5: Database Connection${NC}"
DB_TEST=$(docker exec crypto-tracker-postgres-local psql -U postgres -d postgres -c "SELECT 1;" 2>&1 || echo "FAILED")
if echo "$DB_TEST" | grep -q "1 row"; then
    echo -e "${GREEN}✅ PostgreSQL database is accessible${NC}"
else
    echo -e "${RED}❌ PostgreSQL database connection failed${NC}"
fi
echo ""

# Test 6: Test Redis Connection
echo -e "${BLUE}Test 6: Redis Connection${NC}"
REDIS_TEST=$(docker exec crypto-tracker-redis-local redis-cli ping 2>&1 || echo "FAILED")
if [ "$REDIS_TEST" == "PONG" ]; then
    echo -e "${GREEN}✅ Redis is responding${NC}"
else
    echo -e "${RED}❌ Redis connection failed${NC}"
fi
echo ""

# Test 7: Check Celery Workers
echo -e "${BLUE}Test 7: Celery Workers Status${NC}"
CELERY_CHECK=$(docker exec crypto-tracker-celery-worker-local celery -A project_config inspect active 2>&1 || echo "FAILED")
if echo "$CELERY_CHECK" | grep -q "active"; then
    echo -e "${GREEN}✅ Celery worker is active${NC}"
elif echo "$CELERY_CHECK" | grep -q "Error"; then
    echo -e "${RED}❌ Celery worker error${NC}"
    echo "   $CELERY_CHECK"
else
    echo -e "${YELLOW}⚠️  Celery worker status unknown (might still be starting)${NC}"
fi
echo ""

# Test 8: Check Database Tables
echo -e "${BLUE}Test 8: Database Tables${NC}"
TABLES_CHECK=$(docker exec crypto-tracker-postgres-local psql -U postgres -d postgres -c "\dt" 2>&1 || echo "FAILED")
if echo "$TABLES_CHECK" | grep -q "core_cryptodata"; then
    echo -e "${GREEN}✅ Django tables exist (migrations applied)${NC}"
elif echo "$TABLES_CHECK" | grep -q "No relations found"; then
    echo -e "${YELLOW}⚠️  No tables found - migrations may not have run yet${NC}"
    echo "   Run: ./local-dev.sh migrate"
else
    echo -e "${YELLOW}⚠️  Database status unknown${NC}"
fi
echo ""

# Test 9: Check Logs for Errors
echo -e "${BLUE}Test 9: Recent Error Logs${NC}"
BACKEND_ERRORS=$(docker logs crypto-tracker-backend-local --tail 50 2>&1 | grep -i "error\|exception\|failed" | head -5 || echo "")
if [ -z "$BACKEND_ERRORS" ]; then
    echo -e "${GREEN}✅ No recent errors in backend logs${NC}"
else
    echo -e "${YELLOW}⚠️  Found potential errors in backend:${NC}"
    echo "$BACKEND_ERRORS" | sed 's/^/   /'
fi
echo ""

# Summary
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}📊 Test Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

if $ALL_RUNNING && [ "$BACKEND_RESPONSE" != "000" ] && [ "$DB_TEST" != "FAILED" ] && [ "$REDIS_TEST" == "PONG" ]; then
    echo -e "${GREEN}✅ LOCAL DOCKER ENVIRONMENT IS WORKING!${NC}"
    echo ""
    echo -e "${BLUE}Access Points:${NC}"
    echo "  📊 Frontend:  http://localhost:3000 (if running)"
    echo "  🔧 Backend:   http://localhost:8000"
    echo "  🔴 Redis:     localhost:6379"
    echo "  🐘 Postgres:  localhost:5432"
    echo ""
    echo -e "${BLUE}Useful Commands:${NC}"
    echo "  View logs:       ./local-dev.sh logs backend -f"
    echo "  Run migrations:  ./local-dev.sh migrate"
    echo "  Create superuser: ./local-dev.sh superuser"
    echo "  Django shell:    ./local-dev.sh shell"
    echo "  Stop all:        ./local-dev.sh stop"
    echo ""
else
    echo -e "${YELLOW}⚠️  SOME ISSUES DETECTED${NC}"
    echo ""
    echo -e "${BLUE}Troubleshooting:${NC}"
    echo "  1. View detailed logs: ./local-dev.sh logs"
    echo "  2. Restart services:   ./local-dev.sh restart"
    echo "  3. Rebuild from scratch: ./local-dev.sh stop && ./local-dev.sh rebuild"
    echo "  4. Check environment:    cat .env.local"
    echo ""
fi

echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${GREEN}✅ Test Complete!${NC}"
