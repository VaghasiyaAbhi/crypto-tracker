# 🔍 HOW TO VERIFY KLINES API IS WORKING

**Created:** November 20, 2025  
**Purpose:** Guide to verify real historical data fetching from Binance klines API

---

## 📊 Quick Verification Commands

### **1. Check Real-Time Klines Fetching (LIVE):**

```bash
ssh root@46.62.216.158 "docker logs -f crypto-tracker_calc-worker_1 | grep -E 'FETCHING|API SUCCESS|REAL DATA|CACHED'"
```

**What You'll See:**
```
🌐 FETCHING REAL DATA: BTCUSDT from Binance klines API
✅ API SUCCESS: BTCUSDT - received 65 candles
📊 REAL DATA EXTRACTED for BTCUSDT:
   1m ago: $91,535.0000
   5m ago: $91,480.0000
   15m ago: $91,420.0000
   60m ago: $91,350.0000
💾 CACHED: BTCUSDT data cached for 30 seconds
✅ USING REAL DATA for BTCUSDT
   1m%: +0.0546% (current: $91,585, 1m ago: $91,535)
```

---

### **2. Check Cache Hit Rate:**

```bash
ssh root@46.62.216.158 "docker logs --tail 500 crypto-tracker_calc-worker_1 | grep -E 'CACHE HIT|FETCHING' | head -30"
```

**Expected Output:**
- First fetch: `🌐 FETCHING REAL DATA`
- Next 30 seconds: `📦 CACHE HIT: BTCUSDT klines from cache`
- After 30 sec: `🌐 FETCHING REAL DATA` (cache expired, new fetch)

**Good Cache Rate:** Should see ~97% CACHE HITs, only ~3% API fetches

---

### **3. Check for API Failures:**

```bash
ssh root@46.62.216.158 "docker logs --tail 500 crypto-tracker_calc-worker_1 | grep -E 'KLINES API FAILED|FALLBACK'"
```

**Expected:**
- **No output** = All klines API calls successful ✅
- **Any output** = Some API failures, system using fallback ⚠️

**Example Fallback Log (if API fails):**
```
❌ KLINES API FAILED for BTCUSDT: HTTPError 429
   Will use FALLBACK calculation (24h estimates)
⚠️ USING FALLBACK (24h estimates) for BTCUSDT
   Reason: Klines API unavailable or rate limited
```

---

### **4. Verify Specific Coin (e.g., BTC):**

```bash
ssh root@46.62.216.158 "docker logs --tail 1000 crypto-tracker_calc-worker_1 | grep -A 10 'BTCUSDT' | grep -E 'FETCHING|SUCCESS|EXTRACTED|1m ago|1m%' | head -20"
```

**What to Look For:**
- ✅ `FETCHING REAL DATA: BTCUSDT`
- ✅ `API SUCCESS: BTCUSDT - received 65 candles`
- ✅ `1m ago: $[price]` (shows real historical price)
- ✅ `1m%: [percentage]` (calculated from real data)

---

### **5. Count Total API Calls vs Cache Hits:**

```bash
ssh root@46.62.216.158 "docker logs --tail 1000 crypto-tracker_calc-worker_1 > /tmp/logs.txt && echo 'API Fetches:' && grep -c 'FETCHING REAL DATA' /tmp/logs.txt && echo 'Cache Hits:' && grep -c 'CACHE HIT' /tmp/logs.txt && rm /tmp/logs.txt"
```

**Good Ratio:**
- API Fetches: ~10-20
- Cache Hits: ~500-600
- **Cache Hit Rate:** 95-98% ✅

---

## 📈 What Indicates Real Data is Working

### ✅ **Positive Indicators:**

1. **Logs Show API Calls:**
   ```
   🌐 FETCHING REAL DATA: [SYMBOL] from Binance klines API
   ```

2. **Receive 65 Candles:**
   ```
   ✅ API SUCCESS: [SYMBOL] - received 65 candles
   ```

3. **Extract Historical Prices:**
   ```
   📊 REAL DATA EXTRACTED for [SYMBOL]:
      1m ago: $X.XXXX
      5m ago: $X.XXXX
   ```

4. **Use Real Data for Calculations:**
   ```
   ✅ USING REAL DATA for [SYMBOL]
      1m%: X.XXXX% (current: $Y, 1m ago: $X)
   ```

5. **Data is Cached:**
   ```
   💾 CACHED: [SYMBOL] data cached for 30 seconds
   ```

### ⚠️ **Warning Indicators:**

1. **API Failures:**
   ```
   ❌ KLINES API FAILED for [SYMBOL]: [error]
   ```

2. **Fallback to Estimates:**
   ```
   ⚠️ USING FALLBACK (24h estimates) for [SYMBOL]
   ```

3. **Rate Limit Errors:**
   ```
   HTTPError 429: Too Many Requests
   ```

---

## 🎯 Verification Checklist

### **Daily Health Check:**

**Run this command:**
```bash
ssh root@46.62.216.158 "docker logs --tail 500 crypto-tracker_calc-worker_1 | grep -E 'FETCHING|API SUCCESS|FALLBACK|FAILED' | tail -50"
```

**Check For:**
- [ ] See `FETCHING REAL DATA` messages
- [ ] See `API SUCCESS` with "received 65 candles"
- [ ] See `USING REAL DATA` messages
- [ ] **DO NOT** see `KLINES API FAILED`
- [ ] **DO NOT** see `USING FALLBACK`

**If all checkboxes pass:** ✅ System is fetching real data from Binance!

---

## 🔬 Deep Verification: Compare with Binance

### **Manual Verification:**

1. **Check our dashboard:**
   ```bash
   ssh root@46.62.216.158 "docker exec crypto-tracker_backend1_1 python manage.py shell -c \"
   from core.models import CryptoData
   btc = CryptoData.objects.filter(symbol='BTCUSDT').first()
   print(f'1m: {btc.m1}%, 5m: {btc.m5}%, 15m: {btc.m15}%')
   \""
   ```

2. **Open Binance chart:**
   - Go to: https://www.binance.com/en/trade/BTC_USDT
   - Look at 1m, 5m, 15m candles
   - Calculate the % changes manually

3. **Compare:**
   - Our 1m% should match Binance 1-minute candle
   - Our 5m% should match Binance 5-minute candle
   - Difference should be < 0.01% (rounding only)

---

## 📊 Example: Real Data Working Perfectly

```
=== CALC WORKER LOGS - KLINES API TRACKING ===

🌐 FETCHING REAL DATA: BTCUSDT from Binance klines API
✅ API SUCCESS: BTCUSDT - received 65 candles
📊 REAL DATA EXTRACTED for BTCUSDT:
   1m ago: $91,535.0000
   5m ago: $91,480.0000
   15m ago: $91,420.0000
   60m ago: $91,350.0000
💾 CACHED: BTCUSDT data cached for 30 seconds
✅ USING REAL DATA for BTCUSDT
   1m%: +0.0546% (current: $91,585, 1m ago: $91,535)

[30 seconds later...]

📦 CACHE HIT: BTCUSDT klines from cache
✅ USING REAL DATA for BTCUSDT
   1m%: +0.0328% (current: $91,595, 1m ago: $91,565)

[30 seconds later...]

🌐 FETCHING REAL DATA: BTCUSDT from Binance klines API
✅ API SUCCESS: BTCUSDT - received 65 candles
...
```

**Analysis:**
- ✅ First fetch: Gets real data from API
- ✅ Within 30 seconds: Uses cached data (efficient!)
- ✅ After 30 seconds: Fetches fresh data again
- ✅ Always using REAL DATA, never FALLBACK
- ✅ Percentage changes match actual market movements

---

## 🚨 Troubleshooting

### **Problem: No logs appearing**

**Solution:**
```bash
# Check if calc-worker is running
ssh root@46.62.216.158 "docker ps | grep calc-worker"

# Restart if needed
ssh root@46.62.216.158 "cd /root/crypto-tracker && docker-compose restart calc-worker"
```

### **Problem: Seeing FALLBACK messages**

**Possible Causes:**
1. **Rate Limiting:** Too many API calls
   - Check: Reduce frequency of calculations
   - Check: Increase cache duration

2. **Binance API Down:** Temporary outage
   - Wait 5-10 minutes
   - Check Binance status: https://www.binancestatus.com

3. **Network Issues:** Server connectivity
   - Test: `ssh root@46.62.216.158 "curl https://api.binance.com/api/v3/ping"`
   - Should return: `{}`

### **Problem: ContainerConfig error**

**Solution:**
```bash
# Find corrupted container
ssh root@46.62.216.158 "docker ps -a | grep backend"

# Force remove it (use the container ID)
ssh root@46.62.216.158 "docker rm -f [container_id]"

# Recreate fresh container
ssh root@46.62.216.158 "cd /root/crypto-tracker && docker-compose up -d backend1"
```

---

## 📌 Summary

**To verify klines API is working:**

1. **Quick Check (30 seconds):**
   ```bash
   ssh root@46.62.216.158 "docker logs --tail 100 crypto-tracker_calc-worker_1 | grep -E '🌐|✅|📊|💾' | tail -20"
   ```

2. **Look For:**
   - 🌐 FETCHING REAL DATA
   - ✅ API SUCCESS
   - 📊 REAL DATA EXTRACTED
   - 💾 CACHED

3. **Avoid Seeing:**
   - ❌ KLINES API FAILED
   - ⚠️ USING FALLBACK

**If you see the good indicators:** ✅ **System is using 100% REAL data from Binance!**

---

**Last Verified:** November 20, 2025 @ 10:28 UTC  
**Status:** ✅ Real klines data fetching confirmed working  
**API Calls:** Active and successful  
**Cache:** Working (30-second TTL)  
**Fallback:** Not triggered (API stable)
