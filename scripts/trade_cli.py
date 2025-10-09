#!/usr/bin/env python3
"""
Trading CLI for executing synchronized orders across exchanges.

Usage:
    # Open position: limit on exchange1, market on exchange2 after fill
    python trade_cli.py open --exchange1 hyperliquid --side1 long \\
                              --exchange2 mexc --side2 short \\
                              --symbol BTC --size 100 --price 50000

    # Close position
    python trade_cli.py close --exchange1 mexc --side1 close_short \\
                               --exchange2 hyperliquid --side2 close_long \\
                               --symbol BTC --size 100 --price 50000

    # Cancel order
    python trade_cli.py cancel --exchange hyperliquid --order-id 123456 --symbol BTC
"""

import argparse
import asyncio
import time
import sys
from pathlib import Path
from typing import Optional
from colorama import Fore, init
import requests

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import TRADING_CONFIG
from executors import HyperliquidExecutor, MEXCExecutor, AsterExecutor
from executors.base import OrderSide, OrderType, OrderStatus

# Initialize colorama
init(autoreset=True)


def get_executor(exchange_name: str):
    """Get executor instance for exchange.

    Args:
        exchange_name: Exchange name (hyperliquid, mexc, aster)

    Returns:
        Executor instance
    """
    exchange_name = exchange_name.lower()
    config = TRADING_CONFIG.get(exchange_name)

    if not config:
        raise ValueError(f"No configuration found for exchange: {exchange_name}")

    if exchange_name == 'hyperliquid':
        return HyperliquidExecutor(config)
    elif exchange_name == 'mexc':
        return MEXCExecutor(config)
    elif exchange_name == 'aster':
        return AsterExecutor(config)
    else:
        raise ValueError(f"Unsupported exchange: {exchange_name}")


def parse_side(side_str: str) -> OrderSide:
    """Parse side string to OrderSide enum.

    Args:
        side_str: Side string (long, short, close_long, close_short)

    Returns:
        OrderSide enum
    """
    side_map = {
        'long': OrderSide.LONG,
        'short': OrderSide.SHORT,
        'close_long': OrderSide.CLOSE_LONG,
        'close_short': OrderSide.CLOSE_SHORT,
    }
    side = side_map.get(side_str.lower())
    if not side:
        raise ValueError(f"Invalid side: {side_str}. Must be one of: long, short, close_long, close_short")
    return side


async def monitor_order_websocket(exchange_name: str, order_id: str, symbol: str, executor2, side2, args):
    """Monitor order via WebSocket (for Aster/MEXC)

    Args:
        exchange_name: Exchange name
        order_id: Order ID to monitor
        symbol: Symbol
        executor2: Second executor for hedge orders
        side2: Side for hedge orders
        args: CLI arguments

    Returns:
        Total filled quantity
    """
    last_filled_qty = 0.0
    is_complete = asyncio.Event()

    def on_order_update(order):
        nonlocal last_filled_qty

        # Only process updates for our order
        if str(order.order_id) != str(order_id):
            return

        filled_qty = order.filled_quantity

        # New fill detected
        if filled_qty > last_filled_qty:
            new_fill = filled_qty - last_filled_qty
            # Check if fully filled or partial
            is_full = (filled_qty >= order.size)
            fill_type = "Full fill" if is_full else "Partial fill"
            print(f"{Fore.GREEN}✓ {fill_type}: {new_fill:.4f} (Total: {filled_qty:.4f}/{order.size})")

            # Place market order on exchange2 for the filled amount
            print(f"{Fore.YELLOW}[3/3] Placing MARKET order on {args.exchange2} for {new_fill:.4f}...")
            order2 = executor2.place_order(
                symbol=symbol,
                side=side2,
                size=new_fill,
                order_type=OrderType.MARKET
            )
            print(f"{Fore.GREEN}✓ Market order placed: ID={order2.order_id}")
            print()

            last_filled_qty = filled_qty

        # Check if fully filled
        if order.status == OrderStatus.FILLED:
            print(f"{Fore.GREEN}✓ LIMIT order fully filled!")
            print(f"{Fore.GREEN}✓ Position opened successfully")
            print()
            print(f"{Fore.CYAN}Summary:")
            print(f"  Exchange 1 Order ID: {order_id}")
            print(f"  Total Filled: {order.filled_quantity}")
            is_complete.set()

        # Check if cancelled
        elif order.status == OrderStatus.CANCELLED:
            print(f"{Fore.RED}✗ Order was cancelled")
            is_complete.set()

    # Create monitor based on exchange
    if exchange_name == 'aster':
        from executors.aster_order_monitor import AsterOrderMonitor
        config = TRADING_CONFIG['aster']
        monitor = AsterOrderMonitor(
            wallet_address=config['wallet_address'],
            signer_address=config['signer_address'],
            private_key=config['private_key']
        )
    elif exchange_name == 'mexc':
        from executors.mexc_order_monitor import MEXCOrderMonitor
        config = TRADING_CONFIG['mexc']
        monitor = MEXCOrderMonitor(
            api_key=config['api_key'],
            api_secret=config['api_secret']
        )
    else:
        raise ValueError(f"WebSocket monitoring not supported for {exchange_name}")

    monitor.set_callback(on_order_update)

    print(f"{Fore.CYAN}Using WebSocket monitoring for {exchange_name}...")

    # Connect and wait with timeout
    connect_task = asyncio.create_task(monitor.connect())
    complete_task = asyncio.create_task(is_complete.wait())

    tasks = [connect_task, complete_task]

    # Only add timeout if specified
    if args.timeout is not None:
        timeout_task = asyncio.create_task(asyncio.sleep(args.timeout))
        tasks.append(timeout_task)

    done, pending = await asyncio.wait(
        tasks,
        return_when=asyncio.FIRST_COMPLETED
    )

    # Cancel pending tasks
    for task in pending:
        task.cancel()

    # Check if timeout (only if timeout was set)
    if args.timeout is not None and 'timeout_task' in locals() and timeout_task in done:
        print(f"{Fore.RED}✗ Timeout reached ({args.timeout}s)")
        if last_filled_qty > 0:
            print(f"{Fore.YELLOW}⚠ Partial position opened: {last_filled_qty}/{args.size}")

    return last_filled_qty


def handle_interruption(executor, order_id, symbol, exchange_name):
    """Handle order status check and cancellation on interruption.

    Args:
        executor: Exchange executor instance
        order_id: Order ID to check
        symbol: Trading symbol
        exchange_name: Exchange name for display

    Returns:
        bool: True if order was handled successfully
    """
    try:
        print(f"{Fore.CYAN}Checking order status via REST API...")
        status = executor.get_order_status(order_id, symbol)

        print(f"{Fore.CYAN}Order Status: {status.status.value}")
        filled = status.filled_quantity

        if filled > 0:
            print(f"{Fore.YELLOW}⚠ Order partially filled: {filled}/{status.size}")
            print(f"{Fore.YELLOW}⚠ You may have an unhedged position!")
            print(f"{Fore.CYAN}Order ID {order_id} is still active on {exchange_name}")
            print(f"{Fore.CYAN}To cancel: python scripts/trade_cli.py cancel --exchange {exchange_name} --order-id {order_id} --symbol {symbol}")
            return False
        else:
            # No fills, cancel the order
            print(f"{Fore.YELLOW}Cancelling unfilled order {order_id}...")
            if executor.cancel_order(order_id, symbol):
                print(f"{Fore.GREEN}✓ Order cancelled successfully")
                return True
            else:
                print(f"{Fore.RED}✗ Failed to cancel order")
                print(f"{Fore.CYAN}To cancel manually: python scripts/trade_cli.py cancel --exchange {exchange_name} --order-id {order_id} --symbol {symbol}")
                return False
    except Exception as e:
        print(f"{Fore.RED}✗ Error checking/cancelling order: {str(e)}")
        print(f"{Fore.CYAN}To cancel manually: python scripts/trade_cli.py cancel --exchange {exchange_name} --order-id {order_id} --symbol {symbol}")
        return False


def print_position_header(args):
    """Print position opening header."""
    print(f"{Fore.CYAN}Opening position...")
    print(f"Exchange 1: {args.exchange1} ({args.side1})")
    print(f"Exchange 2: {args.exchange2} ({args.side2})")
    print(f"Symbol: {args.symbol}, Size: {args.size}")
    if args.price:
        print(f"Limit Price: {args.price}")
    print()


def open_position_sync(args):
    """Open position with REST polling (for Hyperliquid)"""
    print_position_header(args)

    # Get executors
    executor1 = get_executor(args.exchange1)
    executor2 = get_executor(args.exchange2)

    side1 = parse_side(args.side1)
    side2 = parse_side(args.side2)

    order1 = None

    try:
        # Step 1: Place limit order on exchange1
        print(f"{Fore.YELLOW}[1/3] Placing LIMIT order on {args.exchange1}...")
        order1 = executor1.place_order(
            symbol=args.symbol,
            side=side1,
            size=args.size,
            order_type=OrderType.LIMIT,
            price=args.price
        )
        print(f"{Fore.GREEN}✓ Order placed: ID={order1.order_id}, Status={order1.status.value}")
        print()

        # Step 2: Poll order1 until filled or partially filled
        print(f"{Fore.YELLOW}[2/3] Waiting for LIMIT order to fill...")
        print(f"{Fore.CYAN}Using REST polling for {args.exchange1}...")
        poll_interval = args.poll_interval
        timeout = args.timeout
        elapsed = 0
        last_filled_qty = 0.0

        while timeout is None or elapsed < timeout:
            time.sleep(poll_interval)
            elapsed += poll_interval

            # Check order status with retry on network errors
            try:
                status = executor1.get_order_status(order1.order_id, args.symbol)
            except (requests.exceptions.RequestException, ConnectionError, TimeoutError) as e:
                print(f"{Fore.YELLOW}⚠ Network error, retrying: {str(e)}")
                continue

            filled_qty = status.filled_quantity

            # New fill detected
            if filled_qty > last_filled_qty:
                new_fill = filled_qty - last_filled_qty
                # Check if fully filled or partial
                is_full = (filled_qty >= status.size)
                fill_type = "Full fill" if is_full else "Partial fill"
                print(f"{Fore.GREEN}✓ {fill_type}: {new_fill:.4f} (Total: {filled_qty:.4f}/{status.size})")

                # Step 3: Place market order on exchange2 for the filled amount
                print(f"{Fore.YELLOW}[3/3] Placing MARKET order on {args.exchange2} for {new_fill:.4f}...")
                order2 = executor2.place_order(
                    symbol=args.symbol,
                    side=side2,
                    size=new_fill,
                    order_type=OrderType.MARKET
                )
                print(f"{Fore.GREEN}✓ Market order placed: ID={order2.order_id}")
                print()

                last_filled_qty = filled_qty

            # Check if fully filled
            if status.status == OrderStatus.FILLED:
                print(f"{Fore.GREEN}✓ LIMIT order fully filled!")
                print(f"{Fore.GREEN}✓ Position opened successfully")
                print()
                print(f"{Fore.CYAN}Summary:")
                print(f"  Exchange 1 Order ID: {order1.order_id}")
                print(f"  Total Filled: {status.filled_quantity}")
                break

            # Check if cancelled
            if status.status == OrderStatus.CANCELLED:
                print(f"{Fore.RED}✗ Order was cancelled")
                break

            timeout_str = f"{timeout}s" if timeout is not None else "∞"
            print(f"{Fore.CYAN}Polling... ({elapsed}s/{timeout_str}, Filled: {filled_qty:.4f}/{status.size})")

        else:
            if timeout is not None:
                print(f"{Fore.RED}✗ Timeout reached ({timeout}s)")
                if last_filled_qty > 0:
                    print(f"{Fore.YELLOW}⚠ Partial position opened: {last_filled_qty}/{args.size}")

    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}⚠ Interrupted by user")
        if order1:
            handle_interruption(executor1, order1.order_id, args.symbol, args.exchange1)
        sys.exit(1)

    except Exception as e:
        print(f"{Fore.RED}✗ Error: {str(e)}")
        if order1:
            print(f"{Fore.CYAN}Order ID {order1.order_id} may still be active on {args.exchange1}")
        sys.exit(1)


async def open_position_async(args):
    """Open position with WebSocket monitoring (for Aster/MEXC)"""
    print_position_header(args)

    # Get executors
    executor1 = get_executor(args.exchange1)
    executor2 = get_executor(args.exchange2)

    side1 = parse_side(args.side1)
    side2 = parse_side(args.side2)

    order1 = None

    try:
        # Step 1: Place limit order on exchange1
        print(f"{Fore.YELLOW}[1/3] Placing LIMIT order on {args.exchange1}...")
        order1 = executor1.place_order(
            symbol=args.symbol,
            side=side1,
            size=args.size,
            order_type=OrderType.LIMIT,
            price=args.price
        )
        print(f"{Fore.GREEN}✓ Order placed: ID={order1.order_id}, Status={order1.status.value}")
        print()

        # Step 2: Monitor order via WebSocket
        print(f"{Fore.YELLOW}[2/3] Waiting for LIMIT order to fill...")
        await monitor_order_websocket(
            args.exchange1,
            order1.order_id,
            args.symbol,
            executor2,
            side2,
            args
        )

    except (KeyboardInterrupt, asyncio.CancelledError):
        print(f"\n{Fore.YELLOW}⚠ Interrupted by user")
        if order1:
            handle_interruption(executor1, order1.order_id, args.symbol, args.exchange1)
        raise  # Re-raise to propagate to open_position()

    except Exception as e:
        print(f"{Fore.RED}✗ Error: {str(e)}")
        if order1:
            print(f"{Fore.CYAN}Order ID {order1.order_id} may still be active on {args.exchange1}")
        sys.exit(1)


def open_position(args):
    """Dispatcher: choose WebSocket or polling based on exchange"""
    exchange1 = args.exchange1.lower()

    # Use WebSocket for Aster and MEXC
    if exchange1 in ['aster', 'mexc']:
        try:
            asyncio.run(open_position_async(args))
        except (KeyboardInterrupt, asyncio.CancelledError):
            # Already handled in open_position_async
            sys.exit(1)
    else:
        # Use polling for Hyperliquid and others
        open_position_sync(args)


def close_position(args):
    """Close synchronized position across two exchanges.

    Args:
        args: Command line arguments
    """
    print(f"{Fore.CYAN}Closing position...")
    # Same logic as open_position but with close sides
    open_position(args)


def cancel_order(args):
    """Cancel an order.

    Args:
        args: Command line arguments
    """
    print(f"{Fore.CYAN}Cancelling order...")
    print(f"Exchange: {args.exchange}")
    print(f"Order ID: {args.order_id}")
    print(f"Symbol: {args.symbol}")
    print()

    executor = get_executor(args.exchange)

    try:
        success = executor.cancel_order(args.order_id, args.symbol)
        if success:
            print(f"{Fore.GREEN}✓ Order cancelled successfully")
        else:
            print(f"{Fore.RED}✗ Failed to cancel order")
            sys.exit(1)

    except Exception as e:
        print(f"{Fore.RED}✗ Error: {str(e)}")
        sys.exit(1)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Trading CLI for synchronized order execution',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Open command
    open_parser = subparsers.add_parser('open', help='Open position')
    open_parser.add_argument('--exchange1', required=True, help='First exchange (limit order)')
    open_parser.add_argument('--side1', required=True, help='Side for exchange1 (long/short)')
    open_parser.add_argument('--exchange2', required=True, help='Second exchange (market order)')
    open_parser.add_argument('--side2', required=True, help='Side for exchange2 (long/short)')
    open_parser.add_argument('--symbol', required=True, help='Trading symbol (normalized, e.g., BTC)')
    open_parser.add_argument('--size', type=float, required=True, help='Order size in symbol units (e.g., 1.5 BTC)')
    open_parser.add_argument('--price', type=float, help='Limit price for exchange1')
    open_parser.add_argument('--poll-interval', type=float, default=2.0, help='Poll interval in seconds (default: 2)')
    open_parser.add_argument('--timeout', type=int, default=None, help='Timeout in seconds (default: None - no timeout)')

    # Close command
    close_parser = subparsers.add_parser('close', help='Close position')
    close_parser.add_argument('--exchange1', required=True, help='First exchange (limit order)')
    close_parser.add_argument('--side1', required=True, help='Side for exchange1 (close_long/close_short)')
    close_parser.add_argument('--exchange2', required=True, help='Second exchange (market order)')
    close_parser.add_argument('--side2', required=True, help='Side for exchange2 (close_long/close_short)')
    close_parser.add_argument('--symbol', required=True, help='Trading symbol (normalized, e.g., BTC)')
    close_parser.add_argument('--size', type=float, required=True, help='Order size in symbol units (e.g., 1.5 BTC)')
    close_parser.add_argument('--price', type=float, help='Limit price for exchange1')
    close_parser.add_argument('--poll-interval', type=float, default=2.0, help='Poll interval in seconds (default: 2)')
    close_parser.add_argument('--timeout', type=int, default=None, help='Timeout in seconds (default: None - no timeout)')

    # Cancel command
    cancel_parser = subparsers.add_parser('cancel', help='Cancel order')
    cancel_parser.add_argument('--exchange', required=True, help='Exchange name')
    cancel_parser.add_argument('--order-id', required=True, help='Order ID to cancel')
    cancel_parser.add_argument('--symbol', required=True, help='Trading symbol (normalized, e.g., BTC)')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == 'open':
        open_position(args)
    elif args.command == 'close':
        close_position(args)
    elif args.command == 'cancel':
        cancel_order(args)


if __name__ == '__main__':
    main()
