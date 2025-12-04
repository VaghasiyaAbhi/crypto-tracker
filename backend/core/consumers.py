import json
import asyncio
import time
from decimal import Decimal
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from rest_framework_simplejwt.tokens import AccessToken
from django.contrib.auth.models import AnonymousUser
from core.models import User, CryptoData
from core.serializers import (
    CryptoDataSerializer,
    CryptoDataBasicSerializer,
    CryptoDataFreeSerializer,
)
import concurrent.futures
import requests
import logging

logger = logging.getLogger(__name__)

# ========================================
# GLOBAL CACHE FOR ACTIVE TRADING SYMBOLS
# ========================================
# This cache prevents delisted symbols from being shown
# Refreshed every 5 minutes automatically
_active_symbols_cache = {
    'symbols': set(),
    'last_updated': 0,
    'cache_ttl': 300  # 5 minutes
}

# ========================================
# GLOBAL CACHE FOR LIVE KLINES DATA
# ========================================
# Caches klines data per currency to avoid refetching on every currency switch
# TTL: 10 seconds (matches the frontend refresh interval for real-time accuracy)
_klines_cache = {
    'USDT': {'data': None, 'last_updated': 0},
    'USDC': {'data': None, 'last_updated': 0},
    'FDUSD': {'data': None, 'last_updated': 0},
    'BNB': {'data': None, 'last_updated': 0},
    'BTC': {'data': None, 'last_updated': 0},
}
KLINES_CACHE_TTL = 10  # 10 seconds - matches frontend refresh for real-time prices

def get_active_trading_symbols():
    """
    Get actively trading symbols from Binance with caching.
    This permanently filters out delisted/BREAK status symbols.
    """
    global _active_symbols_cache
    current_time = time.time()
    
    # Return cached if still valid
    if (_active_symbols_cache['symbols'] and 
        current_time - _active_symbols_cache['last_updated'] < _active_symbols_cache['cache_ttl']):
        return _active_symbols_cache['symbols']
    
    try:
        response = requests.get('https://api.binance.com/api/v3/exchangeInfo', timeout=15)
        response.raise_for_status()
        exchange_info = response.json()
        
        active_symbols = set()
        for symbol_info in exchange_info.get('symbols', []):
            if symbol_info.get('status') == 'TRADING':
                active_symbols.add(symbol_info['symbol'])
        
        _active_symbols_cache['symbols'] = active_symbols
        _active_symbols_cache['last_updated'] = current_time
        logger.info(f"🔄 Refreshed active trading symbols cache: {len(active_symbols)} symbols")
        return active_symbols
        
    except Exception as e:
        logger.error(f"Failed to fetch active symbols: {e}")
        # Return existing cache if available, even if stale
        if _active_symbols_cache['symbols']:
            return _active_symbols_cache['symbols']
        return set()

class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle Decimal objects"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

@database_sync_to_async
def get_user(token_key):
    try:
        token = AccessToken(token_key)
        user_id = token['user_id']
        return User.objects.get(id=user_id)
    except Exception:
        return AnonymousUser()

class CryptoConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = AnonymousUser()
        self.room_group_name = None

        # Extract token from query string if provided (?token=...)
        try:
            raw_qs = self.scope.get('query_string', b'').decode()
            # Debug log (remove later): scope path & query string
            if raw_qs.startswith('token='):
                token = raw_qs.split('token=')[1].split('&')[0]
                self.user = await get_user(token)
        except Exception:  # Broad except is fine here; fallback to AnonymousUser
            pass

        # Determine group based on subscription plan. Align with broadcaster groups.
        if self.user.is_authenticated:
            plan = getattr(self.user, 'subscription_plan', 'free') or 'free'
        else:
            plan = 'free'

        plan_to_group = {
            'free': 'crypto_free',
            'basic': 'crypto_premium',  # Assuming basic maps to premium data tier
            'enterprise': 'crypto_enterprise'
        }
        self.room_group_name = plan_to_group.get(plan, 'crypto_free')

        # Always allow connection; authorization can be further enforced in data payload if needed
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        user_id = getattr(self.user, 'id', None)
        user_plan = getattr(self.user, 'subscription_plan', 'free')
        is_auth = bool(getattr(self.user, 'is_authenticated', False))
        # Send an immediate ack so the client can confirm handshake and auth status.
        await self.send(text_data=json.dumps({
            "type": "ws_ack",
            "group": self.room_group_name,
            "plan": user_plan,
            "is_authenticated": is_auth,
            "reason": None if is_auth else "unauthorized"
        }, cls=DecimalEncoder))
        # Start heartbeat pings (every 20s) so we can see if connection silently dies.
        try:
            loop = asyncio.get_running_loop()
            self.heartbeat_task = loop.create_task(self._heartbeat())
        except RuntimeError:
            self.heartbeat_task = None

    async def disconnect(self, close_code):
        if self.room_group_name:
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
        if hasattr(self, 'heartbeat_task') and self.heartbeat_task:
            self.heartbeat_task.cancel()

    async def crypto_update(self, event):
        # Send data to client; event['data'] expected to be JSON-serializable list or dict
        try:
            # Wrap as delta for clients that understand types; legacy clients still accept arrays
            payload = event.get('data')
            if isinstance(payload, (list, dict)):
                await self.send(text_data=json.dumps({"type": "delta", "data": payload}, cls=DecimalEncoder))
            else:
                await self.send(text_data=json.dumps(payload, cls=DecimalEncoder))
        except Exception:
            # Fallback to raw payload
            await self.send(text_data=json.dumps(event['data'], cls=DecimalEncoder))

    async def receive(self, text_data=None, bytes_data=None):
        """Handle incoming messages from clients (e.g., request full snapshot)."""
        if not text_data:
            return
        try:
            message = json.loads(text_data)
        except Exception:
            return

        msg_type = message.get('type')
        if msg_type == 'request_snapshot':
            sort_by = message.get('sort_by', 'profit')
            sort_order = message.get('sort_order', 'desc')
            # Get quote currency preference (USDT, USDC, FDUSD, BNB, BTC, or ALL)
            quote_currency = message.get('quote_currency', 'USDT').upper()
            # Validate quote currency - support 'ALL' for fetching all currencies at once
            valid_currencies = ['USDT', 'USDC', 'FDUSD', 'BNB', 'BTC', 'ALL']
            if quote_currency not in valid_currencies:
                quote_currency = 'USDT'
            
            # If 'ALL', fetch all currencies for instant client-side filtering
            fetch_all_currencies = (quote_currency == 'ALL')
            
            page_size = int(message.get('page_size') or 100)
            
            # ALWAYS send cached database data first for fast initial load
            # Determine sorting field
            sort_field = '-price_change_percent_24h'
            if sort_by == 'volume':
                sort_field = '-quote_volume_24h'
            elif sort_by == 'latest':
                sort_field = '-id'
            elif sort_by == 'price':
                sort_field = '-last_price'
            if sort_order == 'asc':
                sort_field = sort_field.lstrip('-')

            # Determine serializer based on plan
            user_plan = getattr(self.user, 'subscription_plan', 'free')
            logger.info(f"📊 User plan: {user_plan} for user {getattr(self.user, 'email', 'unknown')}")
            if user_plan == 'enterprise':
                serializer_class = CryptoDataSerializer
            elif user_plan == 'basic':
                serializer_class = CryptoDataBasicSerializer
            else:
                serializer_class = CryptoDataFreeSerializer

            # ========================================
            # OPTIMIZATION: Send cached data immediately to prevent flickering,
            # then ALWAYS fetch fresh data in background for real-time accuracy
            # ========================================
            cache_entry = _klines_cache.get(quote_currency) if not fetch_all_currencies else None
            has_cache = (cache_entry and cache_entry['data'] and len(cache_entry['data']) > 0)
            cache_age = (time.time() - cache_entry['last_updated']) if has_cache else float('inf')
            
            if has_cache and user_plan in ['basic', 'enterprise']:
                # FAST PATH: Send cached data immediately (prevents flickering)
                logger.info(f"⚡ FAST PATH: Sending cached data for {quote_currency} (age: {cache_age:.1f}s)")
                
                await self.send(text_data=json.dumps({
                    'type': 'live_update',
                    'total_count': len(cache_entry['data'][:page_size]),
                    'quote_currency': quote_currency,
                    'live': True,
                    'cached_live': True,
                    'data': cache_entry['data'][:page_size],
                }, cls=DecimalEncoder))
                
                # ALWAYS fetch fresh data in background (for real-time 10s updates)
                # Only skip if cache is very fresh (< 5 seconds) to prevent duplicate fetches
                if cache_age > 5:
                    logger.info(f"🔄 Fetching fresh data in background (cache age: {cache_age:.1f}s)")
                    asyncio.create_task(self._send_live_update(quote_currency, 500))
                else:
                    logger.info(f"⏭️ Cache is fresh enough ({cache_age:.1f}s < 5s), skipping background fetch")
                return  # Skip database snapshot entirely
            
            # SLOW PATH: No cache available, send database snapshot first
            # If fetching ALL currencies, don't filter by quote_currency
            if fetch_all_currencies:
                total_count = await database_sync_to_async(
                    lambda: CryptoData.objects.count()
                )()
                data_chunk = await self._get_snapshot_chunk_all(serializer_class, sort_field, 0, min(page_size, 2000))
            else:
                total_count = await database_sync_to_async(
                    lambda: CryptoData.objects.filter(symbol__endswith=quote_currency).count()
                )()
                data_chunk = await self._get_snapshot_chunk(serializer_class, sort_field, 0, min(page_size, 1000), quote_currency)
            
            await self.send(text_data=json.dumps({
                'type': 'snapshot',
                'chunk': 1,
                'total_chunks': 1,
                'total_count': len(data_chunk),
                'quote_currency': quote_currency,
                'cached': True,
                'data': data_chunk,
            }, cls=DecimalEncoder))
            
            # For premium users, fetch live updates in background (non-blocking)
            if user_plan in ['basic', 'enterprise'] and not fetch_all_currencies:
                # Start background task to fetch live data (only for single currency)
                # IMPORTANT: Always fetch enough symbols for proper live updates
                # For BTC/BNB, we need more symbols due to lower volume thresholds
                live_page_size = 500  # Always fetch up to 500 symbols for live updates
                logger.info(f"🚀 Starting live_update background task for {user_plan} user (currency: {quote_currency}, live_page_size: {live_page_size})")
                asyncio.create_task(self._send_live_update(quote_currency, live_page_size))
            else:
                logger.info(f"⏭️ Skipping live_update for {user_plan} user (fetch_all={fetch_all_currencies})")

    async def _send_live_update(self, quote_currency: str, page_size: int):
        """Fetch live data from Binance and send as update (background task)"""
        try:
            logger.info(f"📡 Fetching live Binance data for {quote_currency} (page_size={page_size})")
            live_data = await self._fetch_live_binance_data(quote_currency, page_size)
            if live_data:
                logger.info(f"✅ Sending live_update with {len(live_data)} items")
                await self.send(text_data=json.dumps({
                    'type': 'live_update',
                    'total_count': len(live_data),
                    'quote_currency': quote_currency,
                    'live': True,
                    'data': live_data,
                }, cls=DecimalEncoder))
            else:
                logger.warning(f"⚠️ No live data received from Binance")
        except Exception as e:
            logger.error(f"Failed to send live update: {e}")

    async def _fetch_live_binance_data(self, quote_currency: str, page_size: int):
        """Fetch LIVE data from Binance API with calculated columns using klines"""
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._sync_fetch_live_data, quote_currency, page_size)
        except Exception as e:
            logger.error(f"Failed to fetch live Binance data: {e}")
            return None
    
    def _sync_fetch_live_data(self, quote_currency: str, page_size: int):
        """Synchronous helper to fetch live data from Binance - OPTIMIZED with CACHING"""
        global _klines_cache
        
        try:
            current_time = time.time()
            
            # CHECK CACHE FIRST - instant response for recent data
            cache_entry = _klines_cache.get(quote_currency)
            if cache_entry and cache_entry['data']:
                cache_age = current_time - cache_entry['last_updated']
                if cache_age < KLINES_CACHE_TTL:
                    logger.info(f"⚡ CACHE HIT for {quote_currency} (age: {cache_age:.1f}s) - returning {len(cache_entry['data'])} symbols instantly")
                    return cache_entry['data'][:page_size]
                else:
                    logger.info(f"🔄 Cache expired for {quote_currency} (age: {cache_age:.1f}s) - fetching fresh data")
            else:
                logger.info(f"📡 No cache for {quote_currency} - fetching fresh data")
            
            # Step 0: Get active trading symbols from cache (filters out delisted)
            active_trading_symbols = get_active_trading_symbols()
            
            if not active_trading_symbols:
                logger.error("❌ No active trading symbols available")
                return None
            
            # Step 1: Fetch 24hr ticker data (this is fast - single API call)
            response = requests.get('https://api.binance.com/api/v3/ticker/24hr', timeout=10)
            response.raise_for_status()
            binance_data = response.json()
            
            # Filter by quote currency, active trading status, and volume
            filtered_data = []
            for item in binance_data:
                symbol = item.get('symbol', '')
                if not symbol.endswith(quote_currency):
                    continue
                # Skip delisted/non-trading symbols (PERMANENT FIX)
                if symbol not in active_trading_symbols:
                    continue
                quote_volume = float(item.get('quoteVolume', 0))
                if quote_volume <= 0:
                    continue
                filtered_data.append(item)
            
            # Sort by 24h volume (highest volume first)
            filtered_data.sort(key=lambda x: float(x.get('quoteVolume', 0)), reverse=True)
            
            # Get symbols up to page_size
            all_symbols = filtered_data[:min(page_size, 500)]
            
            # Fetch klines for ALL symbols with high parallelism
            # Using 50 workers to handle ~440 symbols quickly (should complete in ~10-12 seconds)
            logger.info(f"📊 Fetching klines for ALL {len(all_symbols)} symbols with 50 workers")
            
            # Fetch klines for ALL symbols in parallel
            def fetch_klines_for_symbol(ticker_item):
                symbol = ticker_item['symbol']
                current_price = float(ticker_item['lastPrice'])
                
                try:
                    # Fetch 65 candles to properly calculate 60-minute metrics
                    klines_url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1m&limit=65"
                    klines_response = requests.get(klines_url, timeout=3)  # Fast timeout
                    
                    if klines_response.status_code == 429:
                        # Rate limited - skip instead of retry to keep it fast
                        return self._basic_ticker_data_with_zeros(ticker_item)
                    
                    if klines_response.status_code != 200:
                        return self._basic_ticker_data_with_zeros(ticker_item)
                    
                    klines = klines_response.json()
                    if len(klines) < 2:
                        return self._basic_ticker_data_with_zeros(ticker_item)
                    
                    # Build metrics
                    metrics = {
                        'symbol': symbol,
                        'last_price': ticker_item['lastPrice'],
                        'price_change_percent_24h': ticker_item['priceChangePercent'],
                        'high_price_24h': ticker_item['highPrice'],
                        'low_price_24h': ticker_item['lowPrice'],
                        'quote_volume_24h': ticker_item['quoteVolume'],
                        'bid_price': ticker_item.get('bidPrice'),
                        'ask_price': ticker_item.get('askPrice'),
                    }
                    
                    # Calculate spread (handle zero bid price)
                    bid = float(ticker_item.get('bidPrice') or 0)
                    ask = float(ticker_item.get('askPrice') or 0)
                    if bid > 0 and ask > 0:
                        metrics['spread'] = str(round(ask - bid, 10))
                    else:
                        metrics['spread'] = '0'
                    
                    # Helper function to calculate RSI
                    def calculate_rsi(closes, period=14):
                        if len(closes) < period + 1:
                            return None
                        gains, losses = [], []
                        for i in range(1, len(closes)):
                            change = closes[i] - closes[i-1]
                            gains.append(change if change > 0 else 0)
                            losses.append(abs(change) if change < 0 else 0)
                        if len(gains) < period:
                            return None
                        avg_gain = sum(gains[-period:]) / period
                        avg_loss = sum(losses[-period:]) / period
                        if avg_loss == 0:
                            return 100.0
                        rs = avg_gain / avg_loss
                        return round(100 - (100 / (1 + rs)), 2)
                    
                    # Get closing prices for RSI
                    closes = [float(k[4]) for k in klines]
                    
                    # Calculate RSI for different periods
                    if len(closes) >= 15:
                        rsi = calculate_rsi(closes[-15:], 14)
                        if rsi is not None:
                            metrics['rsi_1m'] = str(rsi)
                    if len(closes) >= 17:
                        rsi = calculate_rsi(closes[-17:], 14)
                        if rsi is not None:
                            metrics['rsi_3m'] = str(rsi)
                    if len(closes) >= 19:
                        rsi = calculate_rsi(closes[-19:], 14)
                        if rsi is not None:
                            metrics['rsi_5m'] = str(rsi)
                    if len(closes) >= 29:
                        rsi = calculate_rsi(closes[-29:], 14)
                        if rsi is not None:
                            metrics['rsi_15m'] = str(rsi)
                    
                    # Calculate timeframe price changes
                    timeframes = [
                        ('m1', 2), ('m2', 3), ('m3', 4), ('m5', 6),
                        ('m10', 11), ('m15', 16), ('m60', 61)
                    ]
                    
                    for tf_name, idx_offset in timeframes:
                        if len(klines) >= idx_offset:
                            tf_price = float(klines[-idx_offset][4])
                            metrics[tf_name] = str(round(((current_price - tf_price) / tf_price) * 100, 4)) if tf_price > 0 else '0'
                            metrics[f'{tf_name}_r_pct'] = metrics[tf_name]
                            
                            # Calculate minutes for volume/range
                            tf_minutes = idx_offset - 1
                            
                            # Volume
                            tf_volume = sum(float(klines[i][7]) for i in range(-tf_minutes, 0))
                            metrics[f'{tf_name}_vol'] = str(round(tf_volume, 2))
                            
                            # High/Low/Range
                            tf_highs = [float(klines[i][2]) for i in range(-tf_minutes, 0)]
                            tf_lows = [float(klines[i][3]) for i in range(-tf_minutes, 0)]
                            metrics[f'{tf_name}_low'] = str(min(tf_lows))
                            metrics[f'{tf_name}_high'] = str(max(tf_highs))
                            if min(tf_lows) > 0:
                                metrics[f'{tf_name}_range_pct'] = str(round(((max(tf_highs) - min(tf_lows)) / min(tf_lows)) * 100, 4))
                            
                            # Buy/Sell volumes
                            buy_vol = sum(float(klines[j][10]) for j in range(-tf_minutes, 0))
                            sell_vol = tf_volume - buy_vol
                            metrics[f'{tf_name}_bv'] = str(round(buy_vol, 2))
                            metrics[f'{tf_name}_sv'] = str(round(sell_vol, 2))
                            metrics[f'{tf_name}_nv'] = str(round(buy_vol - sell_vol, 2))
                    
                    # Volume percentages
                    total_vol_24h = float(ticker_item['quoteVolume'])
                    if total_vol_24h > 0:
                        for tf_name, _ in timeframes:
                            vol_key = f'{tf_name}_vol'
                            if vol_key in metrics:
                                metrics[f'{tf_name}_vol_pct'] = str(round((float(metrics[vol_key]) / total_vol_24h) * 100, 4))
                    
                    return metrics
                    
                except Exception as e:
                    return self._basic_ticker_data_with_zeros(ticker_item)
            
            # Fetch klines for ALL symbols with high parallelism
            # Limit to 300 symbols max to ensure completion within timeout
            symbols_to_fetch = all_symbols[:300]
            logger.info(f"📊 Fetching klines for {len(symbols_to_fetch)} symbols (capped at 300) with 50 workers")
            
            live_data = []
            try:
                with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
                    futures = {executor.submit(fetch_klines_for_symbol, item): item for item in symbols_to_fetch}
                    for future in concurrent.futures.as_completed(futures, timeout=20):
                        try:
                            result = future.result()
                            if result:
                                live_data.append(result)
                        except Exception:
                            pass
            except concurrent.futures.TimeoutError:
                # Timeout occurred, but we still have partial data - use it
                logger.warning(f"⚠️ Timeout after 20s, using {len(live_data)} symbols that completed")
            
            logger.info(f"✅ Prepared {len(live_data)} symbols with klines data")
            
            # Sort by price change
            live_data.sort(key=lambda x: float(x.get('price_change_percent_24h', 0)), reverse=True)
            
            # UPDATE CACHE even with partial data (better than nothing)
            if len(live_data) >= 50:  # Only cache if we got meaningful data
                _klines_cache[quote_currency] = {
                    'data': live_data,
                    'last_updated': time.time()
                }
                logger.info(f"💾 Cached {len(live_data)} symbols for {quote_currency}")
            else:
                logger.warning(f"⚠️ Only {len(live_data)} symbols - not caching (need at least 50)")
            
            return live_data
            
        except Exception as e:
            logger.error(f"Sync fetch failed: {e}")
            return None
    
    def _basic_ticker_data(self, ticker_item):
        """Return basic data without klines calculations"""
        return {
            'symbol': ticker_item['symbol'],
            'last_price': ticker_item['lastPrice'],
            'price_change_percent_24h': ticker_item['priceChangePercent'],
            'high_price_24h': ticker_item['highPrice'],
            'low_price_24h': ticker_item['lowPrice'],
            'quote_volume_24h': ticker_item['quoteVolume'],
            'bid_price': ticker_item.get('bidPrice'),
            'ask_price': ticker_item.get('askPrice'),
        }

    def _basic_ticker_data_with_zeros(self, ticker_item):
        """
        Return ticker data with zero values for klines fields instead of N/A.
        This prevents N/A flickering in the UI.
        """
        data = {
            'symbol': ticker_item['symbol'],
            'last_price': ticker_item['lastPrice'],
            'price_change_percent_24h': ticker_item['priceChangePercent'],
            'high_price_24h': ticker_item['highPrice'],
            'low_price_24h': ticker_item['lowPrice'],
            'quote_volume_24h': ticker_item['quoteVolume'],
            'bid_price': ticker_item.get('bidPrice'),
            'ask_price': ticker_item.get('askPrice'),
            'spread': '0',
        }
        
        # Add zero values for all timeframe fields to prevent N/A
        timeframes = ['m1', 'm2', 'm3', 'm5', 'm10', 'm15', 'm60']
        for tf in timeframes:
            data[tf] = '0'
            data[f'{tf}_r_pct'] = '0'
            data[f'{tf}_vol'] = '0'
            data[f'{tf}_vol_pct'] = '0'
            data[f'{tf}_low'] = ticker_item['lowPrice']
            data[f'{tf}_high'] = ticker_item['highPrice']
            data[f'{tf}_range_pct'] = '0'
            data[f'{tf}_bv'] = '0'
            data[f'{tf}_sv'] = '0'
            data[f'{tf}_nv'] = '0'
        
        # RSI fields
        data['rsi_1m'] = '50'
        data['rsi_3m'] = '50'
        data['rsi_5m'] = '50'
        data['rsi_15m'] = '50'
        
        return data

    @database_sync_to_async
    def _get_snapshot_chunk(self, serializer_class, sort_field: str, offset: int, limit: int, quote_currency: str = 'USDT'):
        # Filter to pairs with selected quote currency and only active trading symbols
        active_symbols = get_active_trading_symbols()
        qs = CryptoData.objects.filter(
            symbol__endswith=quote_currency,
            symbol__in=active_symbols
        ).order_by(sort_field)[offset:offset + limit]
        return serializer_class(qs, many=True).data

    @database_sync_to_async
    def _get_snapshot_chunk_all(self, serializer_class, sort_field: str, offset: int, limit: int):
        """Get all currency pairs (USDT, USDC, FDUSD, BNB, BTC) in one query for instant client-side filtering"""
        from django.db.models import Q
        # Get active trading symbols to filter out delisted
        active_symbols = get_active_trading_symbols()
        # Filter to only valid quote currencies AND active trading symbols
        valid_currencies = ['USDT', 'USDC', 'FDUSD', 'BNB', 'BTC']
        q_filter = Q()
        for currency in valid_currencies:
            q_filter |= Q(symbol__endswith=currency)
        qs = CryptoData.objects.filter(q_filter, symbol__in=active_symbols).order_by(sort_field)[offset:offset + limit]
        return serializer_class(qs, many=True).data

    async def _heartbeat(self):
        try:
            while True:
                await asyncio.sleep(10)  # ⚡ Faster: 20s → 10s for more responsive updates
                try:
                    await self.send(text_data=json.dumps({"type": "heartbeat", "ts": time.time()}, cls=DecimalEncoder))
                except Exception as e:
                    break
        except Exception as e:
            pass