"""Real-time price spread monitor between two exchanges"""

import asyncio
import csv
import argparse
import os
import subprocess
from datetime import datetime
from typing import Optional, Dict
from colorama import Fore, Style, init
from collectors.hyperliquid_ws import HyperliquidWebSocket
from collectors.aster_ws import AsterWebSocket
from collectors.mexc_futures_ws import MEXCFuturesWebSocket
from collectors.websocket_base import OrderbookData

# Initialize colorama
init(autoreset=True)


class SpreadMonitor:
    """Monitor price spread between two exchanges"""

    def __init__(self, symbol: str, exchange_a: str, exchange_b: str, update_interval_ms: int = 100):
        self.symbol = symbol.upper()
        self.exchange_a = exchange_a.lower()
        self.exchange_b = exchange_b.lower()
        self.update_interval = update_interval_ms / 1000  # Convert to seconds

        # Store latest orderbook data
        self.orderbook_a: Optional[OrderbookData] = None
        self.orderbook_b: Optional[OrderbookData] = None

        # CSV file for logging
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_dir = "exports/spreads/csv"
        os.makedirs(csv_dir, exist_ok=True)
        self.csv_filename = os.path.join(csv_dir, f"spreads_log_{timestamp}.csv")
        self._init_csv()

        # WebSocket collectors
        self.ws_a = self._create_collector(exchange_a)
        self.ws_b = self._create_collector(exchange_b)

        # Set callbacks
        self.ws_a.set_callback(self._on_orderbook_a)
        self.ws_b.set_callback(self._on_orderbook_b)

        # Last update time for throttling
        self.last_update = datetime.now()

        # Track last values to detect changes
        self.last_bid_a = None
        self.last_ask_b = None

        # Price precision (will be determined from exchange metadata)
        self.price_precision = 2  # Default fallback

    def _create_collector(self, exchange: str):
        """Create WebSocket collector for exchange"""
        exchange = exchange.lower()
        if exchange == "hyperliquid":
            return HyperliquidWebSocket()
        elif exchange == "aster":
            return AsterWebSocket()
        elif exchange == "mexc":
            return MEXCFuturesWebSocket()
        else:
            raise ValueError(f"Unsupported exchange: {exchange}")

    def _init_csv(self):
        """Initialize CSV file with headers"""
        with open(self.csv_filename, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "timestamp",
                "exchange_a",
                "exchange_b",
                "symbol",
                "bid_a",
                "ask_b",
                "spread",
                "spread_pct"
            ])

    def _on_orderbook_a(self, orderbook: OrderbookData):
        """Callback for exchange A orderbook updates"""
        self.orderbook_a = orderbook
        self._check_and_update()

    def _on_orderbook_b(self, orderbook: OrderbookData):
        """Callback for exchange B orderbook updates"""
        self.orderbook_b = orderbook
        self._check_and_update()

    def _check_and_update(self):
        """Check if we should update display and log data"""
        # Only update if we have data from both exchanges
        if not self.orderbook_a or not self.orderbook_b:
            return

        # Calculate spread: bid_A - ask_B
        # Positive spread means you can buy on B (ask_B) and sell on A (bid_A) for profit
        bid_a = self.orderbook_a.best_bid
        ask_b = self.orderbook_b.best_ask

        # Only update if prices have changed
        if self.last_bid_a == bid_a and self.last_ask_b == ask_b:
            return

        # Throttle updates based on interval (even when prices change)
        now = datetime.now()
        time_since_last = (now - self.last_update).total_seconds()
        if time_since_last < self.update_interval:
            return

        self.last_update = now

        # Update last values
        self.last_bid_a = bid_a
        self.last_ask_b = ask_b

        spread = bid_a - ask_b
        spread_pct = (spread / ask_b) * 100 if ask_b > 0 else 0

        # Display to console
        self._display_spread(bid_a, ask_b, spread, spread_pct)

        # Log to CSV
        self._log_to_csv(bid_a, ask_b, spread, spread_pct)

    def _display_spread(self, bid_a: float, ask_b: float, spread: float, spread_pct: float):
        """Display spread information to console"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

        # Color based on spread
        if spread > 0:
            spread_color = Fore.GREEN
            spread_sign = "+"
        elif spread < 0:
            spread_color = Fore.RED
            spread_sign = ""
        else:
            spread_color = Fore.YELLOW
            spread_sign = ""

        # Format exchange names
        exchange_a_short = self.exchange_a[0].upper()
        exchange_b_short = self.exchange_b[0].upper()

        # Dynamic formatting based on precision
        prec = self.price_precision
        print(
            f"{Fore.CYAN}[{timestamp}] "
            f"{Fore.YELLOW}{self.symbol:<6} "
            f"{Fore.WHITE}{exchange_a_short}:{Fore.GREEN}{bid_a:>10.{prec}f} "
            f"{Fore.WHITE}↔ "
            f"{Fore.WHITE}{exchange_b_short}:{Fore.RED}{ask_b:>10.{prec}f}  "
            f"{spread_color}Spread: {spread_sign}{spread:>8.{prec}f} ({spread_sign}{spread_pct:>7.4f}%)"
        )

    def _log_to_csv(self, bid_a: float, ask_b: float, spread: float, spread_pct: float):
        """Log spread data to CSV file"""
        timestamp = datetime.now().isoformat()

        # Dynamic formatting based on precision
        prec = self.price_precision
        with open(self.csv_filename, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                timestamp,
                self.exchange_a,
                self.exchange_b,
                self.symbol,
                f"{bid_a:.{prec}f}",
                f"{ask_b:.{prec}f}",
                f"{spread:.{prec}f}",
                f"{spread_pct:.4f}"
            ])

    def _generate_plot(self):
        """Generate plot from CSV file using plot_spread.py"""
        try:
            print(f"\n{Fore.CYAN}Generating spread plot...")
            result = subprocess.run(
                ["python", "plot_spread.py", self.csv_filename],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                print(f"{Fore.GREEN}✓ Plot generated successfully")
                # Print the output which contains the PNG filename
                if result.stdout:
                    for line in result.stdout.strip().split('\n'):
                        if 'Plot saved to:' in line or 'Spread Statistics:' in line or line.strip().startswith(('Average:', 'Maximum:', 'Minimum:', 'Data points:')):
                            print(f"{Fore.WHITE}{line}")
            else:
                print(f"{Fore.RED}✗ Failed to generate plot")
                if result.stderr:
                    print(f"{Fore.RED}{result.stderr}")
        except subprocess.TimeoutExpired:
            print(f"{Fore.RED}✗ Plot generation timed out")
        except FileNotFoundError:
            print(f"{Fore.RED}✗ plot_spread.py not found")
        except Exception as e:
            print(f"{Fore.RED}✗ Error generating plot: {e}")

    async def start(self):
        """Start monitoring"""
        print(f"{Fore.CYAN}{Style.BRIGHT}{'=' * 80}")
        print(f"{Fore.CYAN}{Style.BRIGHT}PRICE SPREAD MONITOR")
        print(f"{Fore.CYAN}{Style.BRIGHT}{'=' * 80}")
        print(f"{Fore.WHITE}Symbol: {Fore.YELLOW}{self.symbol}")
        print(f"{Fore.WHITE}Exchange A: {Fore.GREEN}{self.exchange_a.upper()}")
        print(f"{Fore.WHITE}Exchange B: {Fore.RED}{self.exchange_b.upper()}")
        print(f"{Fore.WHITE}Update interval: {Fore.CYAN}{int(self.update_interval * 1000)}ms")
        print(f"{Fore.WHITE}Logging to: {Fore.CYAN}{self.csv_filename}")
        print()
        print(f"{Fore.CYAN}{Style.DIM}📊 Price Terminology:")
        print(f"{Fore.GREEN}  • BID {Fore.WHITE}= Highest price buyers are willing to pay (you can SELL at this price)")
        print(f"{Fore.RED}  • ASK {Fore.WHITE}= Lowest price sellers are asking for (you can BUY at this price)")
        print(f"{Fore.YELLOW}  • Spread calculation: BID_A - ASK_B")
        print(f"{Fore.WHITE}  • Positive spread = profit opportunity (buy on B, sell on A)")

        # Fetch metadata to determine price precision
        print(f"{Fore.CYAN}Fetching symbol metadata...")
        metadata_a = await self.ws_a.get_metadata(self.symbol)
        metadata_b = await self.ws_b.get_metadata(self.symbol)

        # Use the maximum precision between both exchanges
        if metadata_a and metadata_b:
            self.price_precision = max(metadata_a.price_precision, metadata_b.price_precision)
            print(f"{Fore.GREEN}✓ Using {self.price_precision} decimal places for price formatting")
        elif metadata_a:
            self.price_precision = metadata_a.price_precision
            print(f"{Fore.YELLOW}⚠ Only exchange A metadata available, using {self.price_precision} decimals")
        elif metadata_b:
            self.price_precision = metadata_b.price_precision
            print(f"{Fore.YELLOW}⚠ Only exchange B metadata available, using {self.price_precision} decimals")
        else:
            print(f"{Fore.YELLOW}⚠ Metadata not available, using default {self.price_precision} decimals")

        print(f"{Fore.CYAN}{Style.BRIGHT}{'=' * 80}")
        print()

        # Connect to both exchanges
        try:
            await asyncio.gather(
                self.ws_a.connect(self.symbol),
                self.ws_b.connect(self.symbol)
            )
        finally:
            print(f"\n{Fore.YELLOW}Stopping monitor...")
            await self.ws_a.disconnect()
            await self.ws_b.disconnect()
            print(f"{Fore.GREEN}Monitor stopped. Data saved to {self.csv_filename}")

            # Auto-generate plot
            self._generate_plot()


async def main():
    """Main execution"""
    parser = argparse.ArgumentParser(description="Monitor price spread between two exchanges")
    parser.add_argument("--symbol", type=str, required=True, help="Symbol to monitor (e.g., BTC)")
    parser.add_argument("--exchange-a", type=str, required=True,
                       choices=["hyperliquid", "aster", "mexc"],
                       help="First exchange")
    parser.add_argument("--exchange-b", type=str, required=True,
                       choices=["hyperliquid", "aster", "mexc"],
                       help="Second exchange")
    parser.add_argument("--interval", type=int, default=100,
                       help="Update interval in milliseconds (default: 100)")

    args = parser.parse_args()

    # Validate exchanges are different
    if args.exchange_a.lower() == args.exchange_b.lower():
        print(f"{Fore.RED}Error: exchange-a and exchange-b must be different")
        return

    # Create and start monitor
    monitor = SpreadMonitor(
        symbol=args.symbol,
        exchange_a=args.exchange_a,
        exchange_b=args.exchange_b,
        update_interval_ms=args.interval
    )

    await monitor.start()


if __name__ == "__main__":
    import sys
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # Suppress traceback on Ctrl+C
        sys.exit(0)
