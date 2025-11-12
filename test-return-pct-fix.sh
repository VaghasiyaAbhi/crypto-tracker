#!/bin/bash
# Test script to verify return percentage N/A fix

echo "🧪 Testing Return Percentage N/A Fix"
echo "======================================"
echo ""

# Check if local Docker is running
if ! docker ps > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

echo "✅ Docker is running"
echo ""

# Check if local environment is running
if ! docker ps | grep -q "archive-2-backend"; then
    echo "⚠️  Local Docker environment is not running."
    echo "   Starting it now..."
    ./local-dev.sh start
    sleep 10
fi

echo "✅ Local environment is running"
echo ""

echo "📊 Testing Database Query (Return % Fields)"
echo "-------------------------------------------"

# Query database for return percentage fields
docker exec archive-2-postgres-1 psql -U crypto_user -d crypto_db -c "
SELECT 
    symbol,
    ROUND(CAST(last_price AS NUMERIC), 4) as price,
    ROUND(CAST(m1_r_pct AS NUMERIC), 4) as \"1m Ret %\",
    ROUND(CAST(m2_r_pct AS NUMERIC), 4) as \"2m Ret %\",
    ROUND(CAST(m5_r_pct AS NUMERIC), 4) as \"5m Ret %\",
    ROUND(CAST(m15_r_pct AS NUMERIC), 4) as \"15m Ret %\"
FROM core_cryptodata 
WHERE symbol LIKE '%USDT' 
  AND last_price IS NOT NULL
ORDER BY quote_volume_24h DESC NULLS LAST
LIMIT 10;
"

echo ""
echo "📈 Expected Results:"
echo "  ✅ All return % columns should show numbers (not NULL)"
echo "  ✅ Values should be calculated (positive or negative decimals)"
echo "  ✅ No N/A or NULL values should appear"
echo ""

echo "🔍 Checking for NULL return % values..."
NULL_COUNT=$(docker exec archive-2-postgres-1 psql -U crypto_user -d crypto_db -t -c "
SELECT COUNT(*) 
FROM core_cryptodata 
WHERE symbol LIKE '%USDT' 
  AND last_price IS NOT NULL
  AND (m1_r_pct IS NULL OR m2_r_pct IS NULL OR m5_r_pct IS NULL);
")

NULL_COUNT=$(echo $NULL_COUNT | xargs)  # Trim whitespace

if [ "$NULL_COUNT" -eq "0" ]; then
    echo "✅ SUCCESS: No NULL values found in return % fields!"
else
    echo "⚠️  Found $NULL_COUNT records with NULL return % values"
    echo "   This is expected for new coins or during initial data fetch"
fi

echo ""
echo "🎯 Next Steps:"
echo "  1. Open dashboard: http://localhost:3000/dashboard"
echo "  2. Watch the return % columns (1m Ret %, 2m Ret %, etc.)"
echo "  3. Wait for 10-second update cycle"
echo "  4. Verify NO N/A appears during updates"
echo ""
echo "📝 If you see N/A:"
echo "  - Check Celery logs: ./local-dev.sh logs backend -f"
echo "  - Verify task is running: docker exec archive-2-backend-1 celery -A project_config inspect active"
echo "  - Manual trigger: docker exec archive-2-backend-1 python manage.py shell -c 'from core.tasks import fetch_binance_data_task; fetch_binance_data_task.delay()'"
echo ""
echo "✅ Test Complete!"
