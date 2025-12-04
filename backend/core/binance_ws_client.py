"""
Binance WebSocket Client for Real-Time Crypto Data

This module connects to Binance WebSocket streams and receives real-time updates:
- !ticker@arr: All market tickers (price, volume, 24h change) - updates every 1 second

Benefits:
- ZERO API rate limits (streaming, not polling)
- Real-time data (1-2 second updates)
- Single connection handles ALL symbols
- Low resource usage
"""

import json
import asyncio
import logging
import os
import time
from decimal import Decimal
from typing import Dict, List, Optional
import websockets

logger = logging.getLogger(__name__)

# Binance WebSocket endpoints
BINANCE_WS_URL = "wss://stream.binance.com:9443/ws"

# Global state
_ws_client = None
_is_running = False

# Async DB connection pool (using asyncpg)
_db_pool = None


class BinanceWebSocketClient:
    """
    WebSocket client that connects to Binance and receives real-time data.
    Updates the database automatically with fresh prices.
    """
    
    def __init__(self):
        self.ws = None
        self.is_connected = False
        self.reconnect_delay = 5  # seconds
        self.ticker_data_buffer = {}  # Buffer ticker data for batch DB updates
        self.kline_data_buffer = {}   # Buffer kline data
        self.update_interval = 3      # Update DB every 3 seconds
        self.db_pool = None           # Async database pool
        
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
            # Initialize database pool first
            await self._init_db_pool()
            
            # Use simple single-stream URL for ticker data
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
    
    async def _init_db_pool(self):
        """Initialize asyncpg connection pool"""
        try:
            import asyncpg
            from urllib.parse import urlparse, unquote
            
            # Get database settings from environment
            db_host = os.getenv('DB_HOST', 'localhost')
            db_name = os.getenv('DB_NAME', 'crypto_tracker')
            db_user = os.getenv('DB_USER', 'postgres')
            db_password = os.getenv('DB_PASSWORD', 'postgres')
            db_port = os.getenv('DB_PORT', '5432')
            
            # Check for DATABASE_URL first (Heroku style)
            database_url = os.getenv('DATABASE_URL')
            
            if database_url:
                # Parse DATABASE_URL manually to handle special characters
                parsed = urlparse(database_url)
                db_host = parsed.hostname or 'localhost'
                db_port = str(parsed.port or 5432)
                db_name = parsed.path.lstrip('/') if parsed.path else 'crypto_tracker'
                db_user = unquote(parsed.username) if parsed.username else 'postgres'
                db_password = unquote(parsed.password) if parsed.password else ''
                
                logger.info(f"📦 Parsed DATABASE_URL: {db_user}@{db_host}:{db_port}/{db_name}")
            
            logger.info(f"📦 Creating asyncpg pool: {db_user}@{db_host}:{db_port}/{db_name}")
            self.db_pool = await asyncpg.create_pool(
                host=db_host,
                database=db_name,
                user=db_user,
                password=db_password,
                port=int(db_port),
                min_size=1,
                max_size=3,
                command_timeout=120,  # Increase timeout to 2 minutes
                statement_cache_size=0  # Disable statement caching for dynamic queries
            )
            
            logger.info(f"✅ Database pool created successfully!")
            
        except Exception as e:
            logger.error(f"❌ Failed to create database pool: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise
    
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
        if isinstance(data, list):
            await self._handle_ticker_update(data)
        elif isinstance(data, dict):
            stream = data.get('stream', '')
            payload = data.get('data', data)
            if stream == '!ticker@arr' or isinstance(payload, list):
                await self._handle_ticker_update(payload)
    
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
                'price_change_percent_24h': ticker.get('P', '0'),
                'high_price_24h': ticker.get('h', '0'),
                'low_price_24h': ticker.get('l', '0'),
                'quote_volume_24h': ticker.get('q', '0'),
                'bid_price': ticker.get('b', '0'),
                'ask_price': ticker.get('a', '0'),
                'open_price_24h': ticker.get('o', '0'),
                'last_update': time.time()
            }
    
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
        """Update database with buffered ticker data using asyncpg - UNNEST for fast batch upsert"""
        try:
            # Copy and clear buffers immediately
            ticker_snapshot = dict(self.ticker_data_buffer)
            self.ticker_data_buffer.clear()
            
            if not ticker_snapshot:
                return
            
            logger.info(f"📝 Starting DB update for {len(ticker_snapshot)} symbols...")
            
            # Support ALL quote currencies (USDT, USDC, FDUSD, BNB, BTC, EUR, etc.)
            # Sort alphabetically to prevent deadlocks
            quote_currencies = ('USDT', 'USDC', 'FDUSD', 'BNB', 'BTC', 'EUR', 'TRY', 'DAI', 'TUSD', 'ETH')
            symbols_list = sorted([s for s in ticker_snapshot.keys() if any(s.endswith(q) for q in quote_currencies)])
            logger.info(f"   Found {len(symbols_list)} pairs for supported quote currencies...")
            
            if not self.db_pool:
                logger.warning("   No database pool available!")
                return
            
            if not symbols_list:
                return
            
            start_time = time.time()
            
            # Prepare arrays for UNNEST (sort order preserved)
            symbols = []
            last_prices = []
            changes = []
            highs = []
            lows = []
            volumes = []
            bids = []
            asks = []
            spreads = []
            
            for symbol in symbols_list[:500]:  # Update 500 pairs per cycle (all currencies)
                data = ticker_snapshot.get(symbol)
                if not data:
                    continue
                
                try:
                    metrics = self._calculate_metrics(data)
                    symbols.append(symbol)
                    last_prices.append(float(metrics['last_price']))
                    changes.append(float(metrics['price_change_percent_24h']))
                    highs.append(float(metrics['high_price_24h']))
                    lows.append(float(metrics['low_price_24h']))
                    volumes.append(float(metrics['quote_volume_24h']))
                    bids.append(float(metrics['bid_price']))
                    asks.append(float(metrics['ask_price']))
                    spreads.append(float(metrics['spread']))
                except Exception as e:
                    logger.error(f"   Failed to prepare {symbol}: {e}")
            
            if not symbols:
                return
            
            logger.info(f"   Prepared {len(symbols)} records, using UNNEST batch upsert...")
            
            # Retry loop for deadlocks
            for attempt in range(3):
                try:
                    async with self.db_pool.acquire() as conn:
                        result = await conn.execute('''
                            INSERT INTO core_cryptodata (symbol, last_price, price_change_percent_24h, 
                                high_price_24h, low_price_24h, quote_volume_24h, bid_price, ask_price, spread)
                            SELECT * FROM UNNEST($1::varchar[], $2::decimal[], $3::decimal[], 
                                $4::decimal[], $5::decimal[], $6::decimal[], $7::decimal[], $8::decimal[], $9::decimal[])
                            ON CONFLICT (symbol) DO UPDATE SET
                                last_price = EXCLUDED.last_price,
                                price_change_percent_24h = EXCLUDED.price_change_percent_24h,
                                high_price_24h = EXCLUDED.high_price_24h,
                                low_price_24h = EXCLUDED.low_price_24h,
                                quote_volume_24h = EXCLUDED.quote_volume_24h,
                                bid_price = EXCLUDED.bid_price,
                                ask_price = EXCLUDED.ask_price,
                                spread = EXCLUDED.spread
                        ''', symbols, last_prices, changes, highs, lows, volumes, bids, asks, spreads)
                        
                        elapsed = time.time() - start_time
                        self.stats['db_updates'] += 1
                        self.stats['last_update'] = time.time()
                        
                        logger.info(f"✅ Upserted {len(symbols)} symbols in {elapsed:.2f}s ({result})")
                        break  # Success, exit retry loop
                        
                except Exception as e:
                    error_msg = str(e).lower()
                    if 'deadlock' in error_msg and attempt < 2:
                        logger.warning(f"   Deadlock detected, retrying ({attempt + 1}/3)...")
                        await asyncio.sleep(0.5 * (attempt + 1))  # Backoff
                        continue
                    else:
                        logger.error(f"   UNNEST upsert failed: {e}")
                        import traceback
                        logger.error(traceback.format_exc())
                        break
            
        except Exception as e:
            import traceback
            logger.error(f"Database update failed: {e}")
            logger.error(traceback.format_exc())
            self.stats['errors'] += 1
    
    def _calculate_metrics(self, ticker_data: dict) -> dict:
        """Calculate all metrics from ticker data"""
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
        
        return metrics
    
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
        if self.db_pool:
            await self.db_pool.close()
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
