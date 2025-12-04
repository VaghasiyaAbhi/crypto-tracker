"""
Binance WebSocket Client for Real-Time Crypto Data

This module connects to Binance WebSocket streams and receives real-time updates:
- !ticker@arr: All market tickers (price, volume, 24h change) - updates every 1 second
- <symbol>@kline_1m: Kline/candlestick data for RSI calculations - updates every 2 seconds

Benefits:
- ZERO API rate limits (streaming, not polling)
- Real-time data (1-2 second updates)
- Single connection handles ALL symbols
- Low resource usage
"""

import json
import asyncio
import logging
import time
from decimal import Decimal
from typing import Dict, List, Optional, Callable
import websockets
from django.db import transaction
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)

# Binance WebSocket endpoints
BINANCE_WS_URL = "wss://stream.binance.com:9443/ws"
BINANCE_STREAM_URL = "wss://stream.binance.com:9443/stream"

# Top symbols for kline subscriptions (will be dynamically updated)
TOP_SYMBOLS_FOR_KLINES = []

# Global state
_ws_client = None
_is_running = False


class BinanceWebSocketClient:
    """
    WebSocket client that connects to Binance and receives real-time data.
    Updates the database automatically with fresh prices.
    """
    
    def __init__(self):
        self.ws = None
        self.is_connected = False
        self.reconnect_delay = 5  # seconds
        self.last_ticker_update = 0
        self.last_kline_update = {}
        self.ticker_data_buffer = {}  # Buffer ticker data for batch DB updates
        self.kline_data_buffer = {}   # Buffer kline data
        self.update_interval = 3      # Update DB every 3 seconds
        
        # Statistics
        self.stats = {
            'ticker_messages': 0,
            'kline_messages': 0,
            'db_updates': 0,
            'errors': 0,
            'last_update': None
        }
    
    async def connect(self):
        """Connect to Binance WebSocket streams"""
        try:
            # Use simple single-stream URL for ticker data
            # This is the most reliable and provides ALL symbols every 1 second
            url = f"{BINANCE_WS_URL}/!ticker@arr"
            
            logger.info(f"🔌 Connecting to Binance WebSocket (ticker stream)...")
            logger.info(f"   URL: {url}")
            
            self.ws = await websockets.connect(
                url,
                ping_interval=20,
                ping_timeout=60,
                close_timeout=10
            )
            
            self.is_connected = True
            logger.info(f"✅ Connected to Binance WebSocket successfully!")
            
            # Start background tasks
            asyncio.create_task(self._db_update_loop())
            
            # Listen for messages
            await self._listen()
            
        except Exception as e:
            logger.error(f"❌ WebSocket connection failed: {e}")
            self.is_connected = False
            await self._reconnect()
    
    async def _get_top_symbols(self, count: int = 100) -> List[str]:
        """Get top symbols by volume for kline subscriptions"""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get('https://api.binance.com/api/v3/ticker/24hr', timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        # Filter USDT pairs and sort by volume
                        usdt_pairs = [
                            item for item in data 
                            if item['symbol'].endswith('USDT') and float(item.get('quoteVolume', 0)) > 0
                        ]
                        usdt_pairs.sort(key=lambda x: float(x.get('quoteVolume', 0)), reverse=True)
                        symbols = [item['symbol'] for item in usdt_pairs[:count]]
                        logger.info(f"📊 Got top {len(symbols)} symbols for kline subscriptions")
                        return symbols
        except Exception as e:
            logger.error(f"Failed to get top symbols: {e}")
        
        # Fallback to hardcoded top symbols
        return [
            'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT',
            'DOGEUSDT', 'ADAUSDT', 'TRXUSDT', 'AVAXUSDT', 'SHIBUSDT'
        ]
    
    async def _listen(self):
        """Listen for incoming WebSocket messages"""
        try:
            async for message in self.ws:
                try:
                    data = json.loads(message)
                    await self._handle_message(data)
                except json.JSONDecodeError:
                    logger.warning("Received invalid JSON from Binance WebSocket")
                except Exception as e:
                    logger.error(f"Error handling message: {e}")
                    self.stats['errors'] += 1
                    
        except websockets.exceptions.ConnectionClosed as e:
            logger.warning(f"⚠️ WebSocket connection closed: {e}")
            self.is_connected = False
            await self._reconnect()
        except Exception as e:
            logger.error(f"❌ WebSocket listen error: {e}")
            self.is_connected = False
            await self._reconnect()
    
    async def _handle_message(self, data):
        """Handle incoming WebSocket message"""
        # Single stream endpoint returns list directly
        # Multi-stream endpoint returns {stream: ..., data: ...}
        if isinstance(data, list):
            # Direct ticker array from single stream endpoint
            await self._handle_ticker_update(data)
        elif isinstance(data, dict):
            stream = data.get('stream', '')
            payload = data.get('data', data)
            
            if stream == '!ticker@arr' or isinstance(payload, list):
                await self._handle_ticker_update(payload)
            elif '@kline_' in stream:
                await self._handle_kline_update(payload)
    
    async def _handle_ticker_update(self, tickers: list):
        """Handle ticker updates - buffer for batch DB update"""
        self.stats['ticker_messages'] += 1
        
        for ticker in tickers:
            symbol = ticker.get('s', '')
            if not symbol:
                continue
            
            # Buffer the ticker data
            self.ticker_data_buffer[symbol] = {
                'symbol': symbol,
                'last_price': ticker.get('c', '0'),  # Close price
                'price_change_percent_24h': ticker.get('P', '0'),  # Price change percent
                'high_price_24h': ticker.get('h', '0'),
                'low_price_24h': ticker.get('l', '0'),
                'quote_volume_24h': ticker.get('q', '0'),  # Quote volume
                'bid_price': ticker.get('b', '0'),  # Best bid
                'ask_price': ticker.get('a', '0'),  # Best ask
                'open_price_24h': ticker.get('o', '0'),
                'last_update': time.time()
            }
    
    async def _handle_kline_update(self, kline_data: dict):
        """Handle kline update for RSI calculations"""
        self.stats['kline_messages'] += 1
        
        kline = kline_data.get('k', {})
        symbol = kline.get('s', '')
        if not symbol:
            return
        
        # Buffer kline data
        if symbol not in self.kline_data_buffer:
            self.kline_data_buffer[symbol] = []
        
        self.kline_data_buffer[symbol].append({
            'open_time': kline.get('t'),
            'close_time': kline.get('T'),
            'open': kline.get('o'),
            'high': kline.get('h'),
            'low': kline.get('l'),
            'close': kline.get('c'),
            'volume': kline.get('v'),
            'quote_volume': kline.get('q'),
            'taker_buy_volume': kline.get('V'),
            'taker_buy_quote_volume': kline.get('Q'),
            'is_closed': kline.get('x', False)
        })
        
        # Keep only last 65 klines per symbol (for m60 calculations)
        if len(self.kline_data_buffer[symbol]) > 65:
            self.kline_data_buffer[symbol] = self.kline_data_buffer[symbol][-65:]
    
    async def _db_update_loop(self):
        """Background loop to update database with buffered data"""
        logger.info("🔄 DB update loop started")
        while self.is_connected:
            try:
                await asyncio.sleep(self.update_interval)
                
                buffer_size = len(self.ticker_data_buffer)
                logger.info(f"🔄 DB update loop tick - buffered: {buffer_size} symbols")
                
                if self.ticker_data_buffer:
                    await self._update_database()
                    
            except Exception as e:
                logger.error(f"DB update loop error: {e}")
    
    async def _update_database(self):
        """Update database with buffered ticker and kline data"""
        try:
            from core.models import CryptoData
            
            # Copy the buffers to avoid modification during iteration
            ticker_snapshot = dict(self.ticker_data_buffer)
            kline_snapshot = dict(self.kline_data_buffer)
            
            if not ticker_snapshot:
                return
            
            # Clear buffers immediately to accept new data
            self.ticker_data_buffer.clear()
            
            updated_count = 0
            
            # Use sync_to_async for Django ORM
            @sync_to_async
            def batch_update():
                nonlocal updated_count
                with transaction.atomic():
                    for symbol, data in ticker_snapshot.items():
                        try:
                            # Calculate additional metrics from kline data if available
                            klines = kline_snapshot.get(symbol, [])
                            metrics = self._calculate_metrics(data, klines)
                            
                            # Update or create the record
                            CryptoData.objects.update_or_create(
                                symbol=symbol,
                                defaults=metrics
                            )
                            updated_count += 1
                        except Exception as e:
                            logger.error(f"Failed to update {symbol}: {e}")
                
                return updated_count
            
            updated_count = await batch_update()
            
            self.stats['db_updates'] += 1
            self.stats['last_update'] = time.time()
            
            logger.info(f"💾 DB Updated: {updated_count} symbols (ticker msgs: {self.stats['ticker_messages']})")
            
        except Exception as e:
            logger.error(f"Database update failed: {e}")
            self.stats['errors'] += 1
    
    def _calculate_metrics(self, ticker_data: dict, klines: list) -> dict:
        """Calculate all metrics from ticker and kline data"""
        metrics = {
            'symbol': ticker_data['symbol'],
            'last_price': Decimal(str(ticker_data.get('last_price', '0'))),
            'price_change_percent_24h': Decimal(str(ticker_data.get('price_change_percent_24h', '0'))),
            'high_price_24h': Decimal(str(ticker_data.get('high_price_24h', '0'))),
            'low_price_24h': Decimal(str(ticker_data.get('low_price_24h', '0'))),
            'quote_volume_24h': Decimal(str(ticker_data.get('quote_volume_24h', '0'))),
            'bid_price': Decimal(str(ticker_data.get('bid_price', '0') or '0')),
            'ask_price': Decimal(str(ticker_data.get('ask_price', '0') or '0')),
        }
        
        # Calculate spread
        if metrics['bid_price'] > 0 and metrics['ask_price'] > 0:
            metrics['spread'] = metrics['ask_price'] - metrics['bid_price']
        else:
            metrics['spread'] = Decimal('0')
        
        # If we have kline data, calculate timeframe metrics
        if klines and len(klines) >= 2:
            current_price = float(metrics['last_price'])
            closes = [float(k['close']) for k in klines if k.get('close')]
            
            # Calculate RSI
            if len(closes) >= 15:
                rsi = self._calculate_rsi(closes[-15:], 14)
                if rsi is not None:
                    metrics['rsi_1m'] = Decimal(str(rsi))
            
            # Calculate timeframe price changes
            timeframes = [
                ('m1', 2), ('m2', 3), ('m3', 4), ('m5', 6),
                ('m10', 11), ('m15', 16), ('m60', 61)
            ]
            
            for tf_name, idx_offset in timeframes:
                if len(klines) >= idx_offset:
                    try:
                        tf_price = float(klines[-idx_offset]['close'])
                        if tf_price > 0:
                            pct_change = ((current_price - tf_price) / tf_price) * 100
                            metrics[tf_name] = Decimal(str(round(pct_change, 4)))
                            
                            # Volume for this timeframe
                            tf_volume = sum(float(klines[i].get('quote_volume', 0)) for i in range(-min(idx_offset-1, len(klines)), 0))
                            metrics[f'{tf_name}_vol'] = Decimal(str(round(tf_volume, 2)))
                            
                            # Buy volume
                            buy_vol = sum(float(klines[i].get('taker_buy_quote_volume', 0)) for i in range(-min(idx_offset-1, len(klines)), 0))
                            metrics[f'{tf_name}_bv'] = Decimal(str(round(buy_vol, 2)))
                            metrics[f'{tf_name}_sv'] = Decimal(str(round(tf_volume - buy_vol, 2)))
                            metrics[f'{tf_name}_nv'] = Decimal(str(round(buy_vol - (tf_volume - buy_vol), 2)))
                    except (IndexError, ValueError, TypeError):
                        pass
        
        return metrics
    
    def _calculate_rsi(self, closes: list, period: int = 14) -> Optional[float]:
        """Calculate RSI from closing prices"""
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
    
    async def _reconnect(self):
        """Reconnect to WebSocket after connection loss"""
        logger.info(f"🔄 Reconnecting in {self.reconnect_delay} seconds...")
        await asyncio.sleep(self.reconnect_delay)
        
        # Exponential backoff (max 60 seconds)
        self.reconnect_delay = min(self.reconnect_delay * 2, 60)
        
        await self.connect()
    
    async def disconnect(self):
        """Disconnect from WebSocket"""
        self.is_connected = False
        if self.ws:
            await self.ws.close()
            logger.info("🔌 Disconnected from Binance WebSocket")
    
    def get_stats(self) -> dict:
        """Get current statistics"""
        return {
            **self.stats,
            'is_connected': self.is_connected,
            'buffered_tickers': len(self.ticker_data_buffer),
            'buffered_klines': len(self.kline_data_buffer)
        }


# Global instance management
async def start_binance_ws_client():
    """Start the Binance WebSocket client (singleton)"""
    global _ws_client, _is_running
    
    if _is_running:
        logger.info("Binance WebSocket client already running")
        return _ws_client
    
    _ws_client = BinanceWebSocketClient()
    _is_running = True
    
    logger.info("🚀 Starting Binance WebSocket client...")
    await _ws_client.connect()
    
    return _ws_client


async def stop_binance_ws_client():
    """Stop the Binance WebSocket client"""
    global _ws_client, _is_running
    
    if _ws_client:
        await _ws_client.disconnect()
        _ws_client = None
    
    _is_running = False
    logger.info("🛑 Binance WebSocket client stopped")


def get_ws_client() -> Optional[BinanceWebSocketClient]:
    """Get the current WebSocket client instance"""
    return _ws_client


# For testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    async def test():
        client = BinanceWebSocketClient()
        await client.connect()
    
    asyncio.run(test())
