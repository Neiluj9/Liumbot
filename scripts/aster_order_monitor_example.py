#!/usr/bin/env python3
"""Example: Monitor Aster orders in real-time using AsterOrderMonitor"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from executors.aster_order_monitor import AsterOrderMonitor
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
    print("🚀 Aster Order Monitor")
    print("=" * 60)

    # Load config from config.py
    aster_config = TRADING_CONFIG.get('aster')

    # Check if credentials are configured
    if not aster_config:
        print("❌ Error: Aster config not found")
        print("\nPlease add to config.py TRADING_CONFIG['aster']:")
        print('  "wallet_address": "0x...",')
        print('  "signer_address": "0x...",')
        print('  "private_key": "0x...",')
        return

    required_fields = ['wallet_address', 'signer_address', 'private_key']
    missing_fields = [f for f in required_fields if not aster_config.get(f)]

    if missing_fields:
        print(f"❌ Error: Missing Aster config fields: {', '.join(missing_fields)}")
        print("\nPlease ensure all fields are configured in config.py")
        return

    # Create order monitor
    monitor = AsterOrderMonitor(
        wallet_address=aster_config['wallet_address'],
        signer_address=aster_config['signer_address'],
        private_key=aster_config['private_key']
    )

    # Set callback
    monitor.set_callback(on_order_update)

    print(f"Wallet:       {aster_config['wallet_address'][:10]}...")
    print(f"Signer:       {aster_config['signer_address'][:10]}...")
    print(f"Connecting to Aster WebSocket...")
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
