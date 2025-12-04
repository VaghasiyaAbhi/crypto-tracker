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
import time
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from typing import Dict, List, Optional
import websockets

logger = logging.getLogger(__name__)

# Binance WebSocket endpoints
BINANCE_WS_URL = "wss://stream.binance.com:9443/ws"

# Global state
_ws_client = None
_is_running = False

# Thread pool for database operations
_db_executor = ThreadPoolExecutor(max_workers=2)


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
        """Update database with buffered ticker data"""
        try:
            # Copy and clear buffers immediately
            ticker_snapshot = dict(self.ticker_data_buffer)
            self.ticker_data_buffer.clear()
            
            if not ticker_snapshot:
                return
            
            logger.info(f"📝 Starting DB update for {len(ticker_snapshot)} symbols...")
            
            # Run the database update in a thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                _db_executor,
                self._do_db_update,
                ticker_snapshot
            )
            
            updated_count, created_count = result
            
            self.stats['db_updates'] += 1
            self.stats['last_update'] = time.time()
            
            logger.info(f"💾 DB Updated: {updated_count} updated, {created_count} created")
            
        except Exception as e:
            import traceback
            logger.error(f"Database update failed: {e}")
            logger.error(traceback.format_exc())
            self.stats['errors'] += 1
    
    def _do_db_update(self, ticker_snapshot):
        """Synchronous database update - runs in thread pool"""
        # Import Django models inside the thread
        import django
        django.setup()
        from core.models import CryptoData
        from django.db import connection as db_conn
        
        import time as sync_time
        start = sync_time.time()
        
        # Only update USDT pairs for now
        symbols_list = [s for s in ticker_snapshot.keys() if s.endswith('USDT')]
        logger.info(f"   Filtering to {len(symbols_list)} USDT pairs...")
        
        # Use raw SQL for faster updates
        updated_count = 0
        created_count = 0
        
        try:
            with db_conn.cursor() as cursor:
                for symbol in symbols_list[:100]:  # Limit to top 100 for now
                    data = ticker_snapshot.get(symbol)
                    if not data:
                        continue
                    
                    try:
                        metrics = self._calculate_metrics(data)
                        
                        # Use UPSERT (INSERT ... ON CONFLICT UPDATE)
                        cursor.execute("""
                            INSERT INTO core_cryptodata (symbol, last_price, price_change_percent_24h, 
                                high_price_24h, low_price_24h, quote_volume_24h, bid_price, ask_price, spread)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (symbol) DO UPDATE SET
                                last_price = EXCLUDED.last_price,
                                price_change_percent_24h = EXCLUDED.price_change_percent_24h,
                                high_price_24h = EXCLUDED.high_price_24h,
                                low_price_24h = EXCLUDED.low_price_24h,
                                quote_volume_24h = EXCLUDED.quote_volume_24h,
                                bid_price = EXCLUDED.bid_price,
                                ask_price = EXCLUDED.ask_price,
                                spread = EXCLUDED.spread
                        """, [
                            symbol,
                            float(metrics['last_price']),
                            float(metrics['price_change_percent_24h']),
                            float(metrics['high_price_24h']),
                            float(metrics['low_price_24h']),
                            float(metrics['quote_volume_24h']),
                            float(metrics['bid_price']),
                            float(metrics['ask_price']),
                            float(metrics['spread'])
                        ])
                        updated_count += 1
                    except Exception as e:
                        logger.error(f"   Failed to upsert {symbol}: {e}")
                
                db_conn.commit()
        except Exception as e:
            logger.error(f"   Database error: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        logger.info(f"   Upserted {updated_count} records ({sync_time.time() - start:.1f}s)")
        
        # Close the database connection for this thread
        db_conn.close()
        
        return updated_count, 0
    
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
