#!/usr/bin/env python3
"""Example: Monitor MEXC orders in real-time using MEXCExecutor"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from executors.mexc_order_monitor import MEXCOrderMonitor
from executors.base import OrderResult, OrderStatus
from config import TRADING_CONFIG


def on_order_update(order: OrderResult):
    """Callback function for order updates

    Args:
        order: OrderResult object with current order status
    """
    print(f"\n{'='*60}")
    print(f"📥 ORDER UPDATE")
    print(f"{'='*60}")
    print(f"Order ID:     {order.order_id}")
    print(f"Exchange:     {order.exchange}")
    print(f"Symbol:       {order.symbol}")
    print(f"Side:         {order.side.name}")
    print(f"Type:         {order.order_type.name}")
    print(f"Status:       {order.status.name}")
    print(f"Size:         {order.size}")
    print(f"Price:        {order.price}")
    print(f"Filled:       {order.filled_quantity}")
    print(f"Avg Price:    {order.average_price}")
    print(f"{'='*60}\n")

    # Example: Trigger actions based on status
    if order.status == OrderStatus.FILLED:
        print(f"✅ Order {order.order_id} FILLED - Trigger hedge or position update")
    elif order.status == OrderStatus.PARTIAL:
        print(f"⏳ Order {order.order_id} PARTIALLY FILLED - Monitor progress")
    elif order.status == OrderStatus.CANCELLED:
        print(f"❌ Order {order.order_id} CANCELLED")
    elif order.status == OrderStatus.REJECTED:
        print(f"🚫 Order {order.order_id} REJECTED")


async def main():
    """Main function"""
    print("🚀 MEXC Order Monitor")
    print("=" * 60)

    # Load config from config.py
    mexc_config = TRADING_CONFIG['mexc']

    # Check if API credentials are configured
    if not mexc_config.get('api_key') or not mexc_config.get('api_secret'):
        print("❌ Error: MEXC API credentials not configured")
        print("\nPlease add to config.py TRADING_CONFIG['mexc']:")
        print('  "api_key": "your_api_key",')
        print('  "api_secret": "your_api_secret",')
        print("\nGet your credentials from:")
        print("  MEXC > Account > API Management")
        return

    # Create order monitor
    monitor = MEXCOrderMonitor(
        api_key=mexc_config['api_key'],
        api_secret=mexc_config['api_secret']
    )

    # Set callback
    monitor.set_callback(on_order_update)

    print(f"API Key:      {mexc_config['api_key'][:8]}...")
    print(f"Connecting to MEXC WebSocket...")
    print(f"Listening for order updates...\n")

    try:
        # Start monitoring
        await monitor.connect()

    except KeyboardInterrupt:
        print("\n⏹️  Stopping monitor...")

    except Exception as e:
        print(f"\n❌ Error: {e}")

    finally:
        print("✅ Monitor stopped")


if __name__ == "__main__":
    asyncio.run(main())
