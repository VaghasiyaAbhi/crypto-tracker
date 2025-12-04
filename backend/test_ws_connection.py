#!/usr/bin/env python
"""
Simple test script to verify Binance WebSocket connection works.
Run this to test WebSocket connectivity before integrating with Django.
"""

import asyncio
import json
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    import websockets
except ImportError:
    print("❌ websockets package not installed. Install with: pip install websockets")
    exit(1)


BINANCE_WS_URL = "wss://stream.binance.com:9443/ws/!ticker@arr"


async def test_binance_websocket():
    """Test connection to Binance WebSocket and print some ticker data"""
    
    print("\n" + "="*60)
    print("🔌 BINANCE WEBSOCKET CONNECTION TEST")
    print("="*60 + "\n")
    
    print(f"Connecting to: {BINANCE_WS_URL}")
    print("This stream sends ALL market tickers every 1 second\n")
    
    message_count = 0
    max_messages = 5  # Receive 5 messages then stop
    
    try:
        async with websockets.connect(
            BINANCE_WS_URL,
            ping_interval=20,
            ping_timeout=60
        ) as ws:
            print("✅ Connected to Binance WebSocket successfully!\n")
            
            while message_count < max_messages:
                message = await asyncio.wait_for(ws.recv(), timeout=10)
                data = json.loads(message)
                
                message_count += 1
                
                # Show summary
                print(f"\n📊 Message #{message_count}:")
                print(f"   Total symbols received: {len(data)}")
                
                # Show a few sample symbols
                usdt_pairs = [t for t in data if t['s'].endswith('USDT')]
                usdt_pairs.sort(key=lambda x: float(x.get('q', 0)), reverse=True)
                
                print(f"   USDT pairs: {len(usdt_pairs)}")
                print("\n   Top 5 by volume:")
                
                for ticker in usdt_pairs[:5]:
                    symbol = ticker['s']
                    price = float(ticker['c'])
                    change = float(ticker['P'])
                    volume = float(ticker['q'])
                    
                    emoji = "🟢" if change >= 0 else "🔴"
                    print(f"   {emoji} {symbol}: ${price:,.2f} ({change:+.2f}%) - Vol: ${volume/1e6:.1f}M")
                
                print()
        
        print("\n" + "="*60)
        print("✅ TEST PASSED - WebSocket connection works!")
        print("="*60)
        print("\nThe WebSocket received real-time data from Binance.")
        print("Next step: Integrate with Django to update database.\n")
        
    except asyncio.TimeoutError:
        print("❌ Timeout waiting for WebSocket message")
    except websockets.exceptions.ConnectionClosed as e:
        print(f"❌ WebSocket connection closed: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")


async def test_kline_stream():
    """Test kline stream for a single symbol"""
    
    print("\n" + "="*60)
    print("📈 BINANCE KLINE STREAM TEST (BTCUSDT)")
    print("="*60 + "\n")
    
    url = "wss://stream.binance.com:9443/ws/btcusdt@kline_1m"
    print(f"Connecting to: {url}")
    print("This stream sends kline updates every 2 seconds\n")
    
    message_count = 0
    max_messages = 3
    
    try:
        async with websockets.connect(url, ping_interval=20) as ws:
            print("✅ Connected to kline stream!\n")
            
            while message_count < max_messages:
                message = await asyncio.wait_for(ws.recv(), timeout=10)
                data = json.loads(message)
                
                message_count += 1
                
                kline = data.get('k', {})
                print(f"📊 Kline #{message_count}:")
                print(f"   Symbol: {kline.get('s')}")
                print(f"   Open: {kline.get('o')}")
                print(f"   High: {kline.get('h')}")
                print(f"   Low: {kline.get('l')}")
                print(f"   Close: {kline.get('c')}")
                print(f"   Volume: {kline.get('v')}")
                print(f"   Is Closed: {kline.get('x')}")
                print()
        
        print("✅ Kline stream test passed!\n")
        
    except Exception as e:
        print(f"❌ Kline test error: {e}")


async def main():
    """Run all tests"""
    await test_binance_websocket()
    await test_kline_stream()


if __name__ == "__main__":
    asyncio.run(main())
