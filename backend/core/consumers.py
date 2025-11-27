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
            # Get quote currency preference (USDT, USDC, FDUSD, BNB, BTC)
            quote_currency = message.get('quote_currency', 'USDT').upper()
            # Validate quote currency
            valid_currencies = ['USDT', 'USDC', 'FDUSD', 'BNB', 'BTC']
            if quote_currency not in valid_currencies:
                quote_currency = 'USDT'
            
            page_size = int(message.get('page_size') or 100)
            
            # For premium/enterprise users, fetch LIVE data from Binance
            user_plan = getattr(self.user, 'subscription_plan', 'free')
            if user_plan in ['basic', 'enterprise']:
                # Fetch live Binance data with calculated columns
                live_data = await self._fetch_live_binance_data(quote_currency, page_size)
                if live_data:
                    await self.send(text_data=json.dumps({
                        'type': 'snapshot',
                        'chunk': 1,
                        'total_chunks': 1,
                        'total_count': len(live_data),
                        'quote_currency': quote_currency,
                        'live': True,
                        'data': live_data,
                    }, cls=DecimalEncoder))
                    return
            
            # Fallback: fetch from database for free users or if live fetch fails
            # Determine sorting field similar to REST view
            sort_field = '-price_change_percent_24h'
            if sort_by == 'volume':
                sort_field = '-quote_volume_24h'
            elif sort_by == 'latest':
                sort_field = '-id'
            elif sort_by == 'price':
                sort_field = '-last_price'
            # Apply sort order
            if sort_order == 'asc':
                sort_field = sort_field.lstrip('-')

            # Determine serializer based on plan
            if getattr(self.user, 'subscription_plan', 'free') == 'enterprise':
                serializer_class = CryptoDataSerializer
            elif getattr(self.user, 'subscription_plan', 'free') == 'basic':
                serializer_class = CryptoDataBasicSerializer
            else:
                serializer_class = CryptoDataFreeSerializer

            # Chunk and send snapshot to avoid giant frames
            # Count pairs for selected quote currency
            total_count = await database_sync_to_async(
                lambda: CryptoData.objects.filter(symbol__endswith=quote_currency).count()
            )()
            total_pages = (total_count + page_size - 1) // page_size if page_size > 0 else 1

            for page in range(total_pages):
                offset = page * page_size
                data_chunk = await self._get_snapshot_chunk(serializer_class, sort_field, offset, page_size, quote_currency)
                await self.send(text_data=json.dumps({
                    'type': 'snapshot',
                    'chunk': page + 1,
                    'total_chunks': total_pages,
                    'total_count': total_count,
                    'quote_currency': quote_currency,
                    'data': data_chunk,
                }, cls=DecimalEncoder))

    async def _fetch_live_binance_data(self, quote_currency: str, page_size: int):
        """Fetch LIVE data from Binance API with calculated columns using klines"""
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._sync_fetch_live_data, quote_currency, page_size)
        except Exception as e:
            logger.error(f"Failed to fetch live Binance data: {e}")
            return None
    
    def _sync_fetch_live_data(self, quote_currency: str, page_size: int):
        """Synchronous helper to fetch live data from Binance"""
        try:
            # Step 1: Fetch 24hr ticker data
            response = requests.get('https://api.binance.com/api/v3/ticker/24hr', timeout=10)
            response.raise_for_status()
            binance_data = response.json()
            
            # Filter by quote currency and sort by volume
            filtered_data = []
            for item in binance_data:
                symbol = item.get('symbol', '')
                if not symbol.endswith(quote_currency):
                    continue
                quote_volume = float(item.get('quoteVolume', 0))
                if quote_volume <= 0:
                    continue
                filtered_data.append(item)
            
            # Sort by 24h price change (most profitable first)
            filtered_data.sort(key=lambda x: float(x.get('priceChangePercent', 0)), reverse=True)
            top_symbols = filtered_data[:page_size]
            
            # Step 2: Fetch klines for top symbols in parallel
            def fetch_klines_for_symbol(ticker_item):
                symbol = ticker_item['symbol']
                current_price = float(ticker_item['lastPrice'])
                
                try:
                    # Fetch 65 candles to properly calculate 60-minute metrics
                    klines_url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1m&limit=65"
                    klines_response = requests.get(klines_url, timeout=5)
                    
                    if klines_response.status_code != 200:
                        return self._basic_ticker_data(ticker_item)
                    
                    klines = klines_response.json()
                    if len(klines) < 2:
                        return self._basic_ticker_data(ticker_item)
                    
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
                    return self._basic_ticker_data(ticker_item)
            
            # Use ThreadPoolExecutor for parallel klines fetching
            live_data = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = {executor.submit(fetch_klines_for_symbol, item): item for item in top_symbols}
                for future in concurrent.futures.as_completed(futures):
                    try:
                        result = future.result()
                        if result:
                            live_data.append(result)
                    except Exception:
                        pass
            
            # Sort by price change
            live_data.sort(key=lambda x: float(x.get('price_change_percent_24h', 0)), reverse=True)
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

    @database_sync_to_async
    def _get_snapshot_chunk(self, serializer_class, sort_field: str, offset: int, limit: int, quote_currency: str = 'USDT'):
        # Filter to pairs with selected quote currency
        qs = CryptoData.objects.filter(symbol__endswith=quote_currency).order_by(sort_field)[offset:offset + limit]
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