"""Main script for funding rate arbitrage"""

import asyncio
import json
import os
import sys
from pathlib import Path
from datetime import datetime
from colorama import Fore, Style, init

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from collectors import HyperliquidCollector, MEXCCollector, AsterCollector
from analyzer import FundingRateAnalyzer
from config import SYMBOLS, EXCHANGES
from utils import format_time_until_funding, get_countdown_color

# Initialize colorama
init(autoreset=True)


async def collect_all_funding_rates():
    """Collect funding rates from all enabled exchanges"""
    all_rates = []

    collectors = []
    if EXCHANGES["hyperliquid"]["enabled"]:
        collectors.append(HyperliquidCollector())
    if EXCHANGES["mexc"]["enabled"]:
        collectors.append(MEXCCollector())
    if EXCHANGES["aster"]["enabled"]:
        collectors.append(AsterCollector())

    # Collect from all exchanges concurrently
    async def collect_with_progress(collector):
        """Wrapper to show progress for each exchange"""
        exchange = collector.exchange_name
        print(f"{Fore.YELLOW}  → Starting {exchange}...")
        try:
            result = await collector.get_funding_rates(SYMBOLS)
            print(f"{Fore.GREEN}  ✓ {exchange}: {len(result)} rates collected")
            return result
        except Exception as e:
            print(f"{Fore.RED}  ✗ {exchange}: Error - {e}")
            return e

    tasks = [collect_with_progress(collector) for collector in collectors]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for result in results:
        if isinstance(result, Exception):
            pass  # Already printed in collect_with_progress
        else:
            all_rates.extend(result)

    return all_rates


async def main():
    """Main execution"""
    print(f"{Fore.CYAN}{Style.BRIGHT}{'=' * 60}")
    print(f"{Fore.CYAN}{Style.BRIGHT}CRYPTO FUNDING RATE ARBITRAGE ANALYZER")
    print(f"{Fore.CYAN}{Style.BRIGHT}{'=' * 60}")
    timestamp = datetime.now()
    print(f"{Fore.WHITE}Timestamp: {Fore.CYAN}{timestamp.isoformat()}")
    symbols_count = len(SYMBOLS)
    print(f"{Fore.WHITE}Tracking {Fore.CYAN}{symbols_count}{Fore.WHITE} symbols")
    print()

    # Create exports directories and timestamp for files
    timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")
    rates_dir = "exports/funding_rates"
    opportunities_dir = "exports/arbitrage_opportunities"
    os.makedirs(rates_dir, exist_ok=True)
    os.makedirs(opportunities_dir, exist_ok=True)

    # Collect funding rates
    print(f"{Fore.CYAN}📊 Collecting funding rates...")
    funding_rates = await collect_all_funding_rates()

    if not funding_rates:
        print(f"{Fore.RED}❌ No funding rates collected")
        return

    print(f"{Fore.GREEN}✅ Collected {len(funding_rates)} funding rates")
    print()

    # Export current rates to file
    rates_file = f"{rates_dir}/current_funding_rates_{timestamp_str}.json"
    with open(rates_file, "w") as f:
        rates_data = [
            {
                "symbol": rate.symbol,
                "exchange": rate.exchange,
                "funding_rate": rate.funding_rate,
                "funding_rate_percent": f"{rate.funding_rate*100:.4f}%",
                "timestamp": rate.timestamp.isoformat(),
                "next_funding_time": rate.next_funding_time.isoformat() if rate.next_funding_time else None
            }
            for rate in sorted(funding_rates, key=lambda x: (x.symbol, x.exchange))
        ]
        json.dump(rates_data, f, indent=2)
    print(f"{Fore.CYAN}💾 Saved: {Fore.WHITE}{rates_file}")
    print()

    # Analyze for arbitrage
    analyzer = FundingRateAnalyzer()
    opportunities = analyzer.find_arbitrage_opportunities(funding_rates)

    if opportunities:
        print(f"{Fore.GREEN}{Style.BRIGHT}🎯 ARBITRAGE OPPORTUNITIES FOUND")
        print(f"{Fore.CYAN}{'=' * 98}")

        # Sort by rate difference and show top 5
        top_opportunities = sorted(opportunities, key=lambda x: x.rate_difference, reverse=True)[:5]

        print(f"{Fore.WHITE}Top {Fore.CYAN}5{Fore.WHITE} opportunities (of {Fore.CYAN}{len(opportunities)}{Fore.WHITE} total)")
        print(f"{Fore.YELLOW}Note: Rates as received for each exchange's funding interval\n")

        # Table header
        print(f"{Fore.CYAN}{Style.BRIGHT}{'#':<3} {'Symbol':<9} {'Exch':<13} {'Maker':<9} {'Taker':<9} {'Int':<5} {'Rate':<11} {'Next Funding':<13} {'Spread/h':<11} {'Annual':<9}")
        print(f"{Fore.CYAN}{'-' * 98}")

        # Table rows - showing rates as received for each interval with fees
        for idx, opp in enumerate(top_opportunities, 1):
            long_rate_pct = f"{opp.long_rate_interval*100:.4f}%"
            short_rate_pct = f"{opp.short_rate_interval*100:.4f}%"
            spread_pct = f"{opp.rate_difference*100:.4f}%"
            annual_return = f"{opp.annual_return:.2%}"
            long_interval = f"{opp.long_interval}h"
            short_interval = f"{opp.short_interval}h"

            # Format fees
            long_maker = f"{opp.long_maker_fee*100:.3f}%" if opp.long_maker_fee is not None else "N/A"
            long_taker = f"{opp.long_taker_fee*100:.3f}%" if opp.long_taker_fee is not None else "N/A"
            short_maker = f"{opp.short_maker_fee*100:.3f}%" if opp.short_maker_fee is not None else "N/A"
            short_taker = f"{opp.short_taker_fee*100:.3f}%" if opp.short_taker_fee is not None else "N/A"

            # Format countdowns
            long_countdown = format_time_until_funding(opp.long_next_funding_time)
            short_countdown = format_time_until_funding(opp.short_next_funding_time)
            long_countdown_color = get_countdown_color(opp.long_next_funding_time)
            short_countdown_color = get_countdown_color(opp.short_next_funding_time)

            # Color for spread/annual based on magnitude
            spread_color = Fore.GREEN if opp.rate_difference > 0.001 else Fore.YELLOW
            annual_color = Fore.GREEN if opp.annual_return > 0.05 else Fore.YELLOW

            # First line: Long position
            print(f"{Fore.WHITE}{idx:<3} {Fore.YELLOW}{opp.symbol:<9} {Fore.GREEN}L:{opp.long_exchange:<11} {Fore.WHITE}{long_maker:<9} {long_taker:<9} {long_interval:<5} {long_rate_pct:<11} {long_countdown_color}{long_countdown:<13} {spread_color}{spread_pct:<11} {annual_color}{annual_return:<9}")
            # Second line: Short position
            print(f"{Fore.WHITE}{'':3} {'':9} {Fore.RED}S:{opp.short_exchange:<11} {Fore.WHITE}{short_maker:<9} {short_taker:<9} {short_interval:<5} {short_rate_pct:<11} {short_countdown_color}{short_countdown:<13}")

        print(f"{Fore.CYAN}{'=' * 98}")
        print()

        # Save to JSON
        opp_file = f"{opportunities_dir}/arbitrage_opportunities_{timestamp_str}.json"
        with open(opp_file, "w") as f:
            json.dump([opp.to_dict() for opp in opportunities], f, indent=2)
        print(f"{Fore.CYAN}💾 Saved: {Fore.WHITE}{opp_file}")
    else:
        print(f"{Fore.YELLOW}ℹ️  No arbitrage opportunities found (rate difference < threshold)")


if __name__ == "__main__":
    asyncio.run(main())
