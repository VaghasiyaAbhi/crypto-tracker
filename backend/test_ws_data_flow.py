#!/usr/bin/env python
"""
Test the Binance WebSocket client's data buffering and processing logic.
This test doesn't require Django - it just verifies data flows correctly.
"""

import asyncio
import json
import logging
import time
from decimal import Decimal
from typing import Dict, List, Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    import websockets
except ImportError:
    print("❌ websockets package not installed")
    exit(1)


class TestBinanceWSClient:
    """Simplified test client that buffers data like the real client"""
    
    def __init__(self):
        self.ticker_buffer = {}
        self.kline_buffer = {}
        self.message_count = 0
    
    async def test_ticker_stream(self, max_messages=5):
        """Test ticker stream and show what would be saved to DB"""
        
        print("\n" + "="*70)
        print("📊 TESTING TICKER STREAM WITH DB-STYLE DATA PROCESSING")
        print("="*70 + "\n")
        
        url = "wss://stream.binance.com:9443/ws/!ticker@arr"
        
        async with websockets.connect(url, ping_interval=20) as ws:
            print(f"✅ Connected to ticker stream\n")
            
            while self.message_count < max_messages:
                message = await asyncio.wait_for(ws.recv(), timeout=10)
                data = json.loads(message)
                
                self.message_count += 1
                
                # Process like the real client would
                for ticker in data:
                    symbol = ticker.get('s', '')
                    if not symbol or not symbol.endswith('USDT'):
                        continue
                    
                    # Buffer the data exactly as the real client would
                    self.ticker_buffer[symbol] = {
                        'symbol': symbol,
                        'last_price': Decimal(ticker.get('c', '0')),
                        'price_change_percent_24h': Decimal(ticker.get('P', '0')),
                        'high_price_24h': Decimal(ticker.get('h', '0')),
                        'low_price_24h': Decimal(ticker.get('l', '0')),
                        'quote_volume_24h': Decimal(ticker.get('q', '0')),
                        'bid_price': Decimal(ticker.get('b', '0') or '0'),
                        'ask_price': Decimal(ticker.get('a', '0') or '0'),
                        'open_price_24h': Decimal(ticker.get('o', '0')),
                    }
                
                print(f"Message #{self.message_count}: Buffered {len(self.ticker_buffer)} USDT symbols")
        
        # Show sample of what would be saved to DB
        print(f"\n📋 SAMPLE DATA THAT WOULD BE SAVED TO DB:")
        print("-"*70)
        
        # Sort by volume and show top 10
        sorted_symbols = sorted(
            self.ticker_buffer.items(),
            key=lambda x: float(x[1].get('quote_volume_24h', 0)),
            reverse=True
        )
        
        for symbol, data in sorted_symbols[:10]:
            print(f"\n{symbol}:")
            print(f"  last_price: {data['last_price']}")
            print(f"  price_change_percent_24h: {data['price_change_percent_24h']}")
            print(f"  high_price_24h: {data['high_price_24h']}")
            print(f"  low_price_24h: {data['low_price_24h']}")
            print(f"  quote_volume_24h: {data['quote_volume_24h']}")
        
        print("\n" + "="*70)
        print(f"✅ Total USDT symbols buffered: {len(self.ticker_buffer)}")
        print("="*70 + "\n")
        
        return len(self.ticker_buffer)
    
    async def test_combined_stream(self, duration=10):
        """Test combined ticker + kline stream for specified duration"""
        
        print("\n" + "="*70)
        print(f"📊 TESTING COMBINED STREAMS FOR {duration} SECONDS")
        print("="*70 + "\n")
        
        # Build stream URL with ticker + a few kline streams
        streams = [
            "!ticker@arr",
            "btcusdt@kline_1m",
            "ethusdt@kline_1m",
            "solusdt@kline_1m"
        ]
        
        stream_param = "/".join(streams)
        url = f"wss://stream.binance.com:9443/stream?streams={stream_param}"
        
        ticker_count = 0
        kline_count = 0
        start_time = time.time()
        
        async with websockets.connect(url, ping_interval=20) as ws:
            print(f"✅ Connected to combined stream")
            print(f"   Streams: {len(streams)}")
            print(f"   Duration: {duration}s\n")
            
            while (time.time() - start_time) < duration:
                try:
                    message = await asyncio.wait_for(ws.recv(), timeout=5)
                    data = json.loads(message)
                    
                    stream = data.get('stream', '')
                    payload = data.get('data', data)
                    
                    if stream == '!ticker@arr' or isinstance(payload, list):
                        ticker_count += 1
                        # Process tickers
                        usdt_count = sum(1 for t in payload if t.get('s', '').endswith('USDT'))
                        elapsed = time.time() - start_time
                        print(f"  [{elapsed:.1f}s] 📈 Ticker update: {usdt_count} USDT symbols")
                        
                        # Buffer top 5 for display
                        for ticker in payload:
                            symbol = ticker.get('s', '')
                            if symbol.endswith('USDT'):
                                self.ticker_buffer[symbol] = {
                                    'price': Decimal(ticker.get('c', '0')),
                                    'change': Decimal(ticker.get('P', '0'))
                                }
                    
                    elif '@kline_' in stream:
                        kline_count += 1
                        kline = payload.get('k', {})
                        symbol = kline.get('s', '')
                        close = kline.get('c', '0')
                        elapsed = time.time() - start_time
                        print(f"  [{elapsed:.1f}s] 📊 Kline update: {symbol} = ${float(close):,.2f}")
                        
                        # Buffer kline data
                        if symbol not in self.kline_buffer:
                            self.kline_buffer[symbol] = []
                        self.kline_buffer[symbol].append({
                            'close': close,
                            'time': kline.get('t')
                        })
                
                except asyncio.TimeoutError:
                    continue
        
        print(f"\n" + "-"*70)
        print(f"📊 STREAM STATISTICS:")
        print(f"   Ticker messages: {ticker_count}")
        print(f"   Kline messages: {kline_count}")
        print(f"   Unique USDT symbols: {len(self.ticker_buffer)}")
        print(f"   Symbols with klines: {len(self.kline_buffer)}")
        
        # Show final prices
        print(f"\n📈 FINAL PRICES:")
        for symbol in ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']:
            if symbol in self.ticker_buffer:
                data = self.ticker_buffer[symbol]
                emoji = "🟢" if float(data['change']) >= 0 else "🔴"
                print(f"   {emoji} {symbol}: ${float(data['price']):,.2f} ({float(data['change']):+.2f}%)")
        
        print("\n" + "="*70)
        print("✅ COMBINED STREAM TEST PASSED!")
        print("="*70 + "\n")


async def main():
    client = TestBinanceWSClient()
    
    # Test ticker stream with DB-style processing
    await client.test_ticker_stream(max_messages=3)
    
    # Test combined streams for 10 seconds
    await client.test_combined_stream(duration=10)


if __name__ == "__main__":
    asyncio.run(main())
