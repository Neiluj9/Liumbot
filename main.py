"""Main script for funding rate arbitrage"""

import asyncio
import json
import os
from datetime import datetime
from collectors import HyperliquidCollector, MEXCCollector, AsterCollector
from analyzer import FundingRateAnalyzer
from config import SYMBOLS, EXCHANGES


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
        print(f"  → Starting {exchange}...")
        try:
            result = await collector.get_funding_rates(SYMBOLS)
            print(f"  ✓ {exchange}: {len(result)} rates collected")
            return result
        except Exception as e:
            print(f"  ✗ {exchange}: Error - {e}")
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
    print("=" * 60)
    print("CRYPTO FUNDING RATE ARBITRAGE ANALYZER")
    print("=" * 60)
    timestamp = datetime.now()
    print(f"Timestamp: {timestamp.isoformat()}")
    print(f"Tracking symbols: {', '.join(SYMBOLS)}")
    print()

    # Create exports directory and timestamp for files
    timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")
    export_dir = "exports"
    os.makedirs(export_dir, exist_ok=True)

    # Collect funding rates
    print("📊 Collecting funding rates...")
    funding_rates = await collect_all_funding_rates()

    if not funding_rates:
        print("❌ No funding rates collected")
        return

    print(f"✅ Collected {len(funding_rates)} funding rates")
    print()

    # Export current rates to file
    rates_file = f"{export_dir}/current_funding_rates_{timestamp_str}.json"
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
    print(f"💾 Saved current rates to {rates_file}")
    print()

    # Analyze for arbitrage
    analyzer = FundingRateAnalyzer()
    opportunities = analyzer.find_arbitrage_opportunities(funding_rates)

    if opportunities:
        print("🎯 ARBITRAGE OPPORTUNITIES FOUND")
        print("=" * 100)

        # Sort by rate difference and show top 5
        top_opportunities = sorted(opportunities, key=lambda x: x.rate_difference, reverse=True)[:5]

        print(f"\nTop 5 opportunities out of {len(opportunities)} total")
        print("Note: Rates shown are as received for each exchange's funding interval\n")

        # Table header
        print(f"{'#':<3} {'Symbol':<10} {'Exchange':<15} {'Int':<6} {'Rate':<12} {'Maker':<10} {'Taker':<10} {'Spread/h':<12} {'Annual':<10}")
        print("-" * 90)

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

            # First line: Long position
            print(f"{idx:<3} {opp.symbol:<10} Long:{opp.long_exchange:<11} {long_interval:<6} {long_rate_pct:<12} {long_maker:<10} {long_taker:<10} {spread_pct:<12} {annual_return:<10}")
            # Second line: Short position
            print(f"{'':3} {'':10} Short:{opp.short_exchange:<10} {short_interval:<6} {short_rate_pct:<12} {short_maker:<10} {short_taker:<10}")

        print("=" * 90)
        print()

        # Save to JSON
        opp_file = f"{export_dir}/arbitrage_opportunities_{timestamp_str}.json"
        with open(opp_file, "w") as f:
            json.dump([opp.to_dict() for opp in opportunities], f, indent=2)
        print(f"💾 Saved opportunities to {opp_file}")
    else:
        print("ℹ️  No arbitrage opportunities found (rate difference < threshold)")


if __name__ == "__main__":
    asyncio.run(main())
