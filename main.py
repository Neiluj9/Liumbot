"""Main script for funding rate arbitrage"""

import asyncio
import json
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
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Tracking symbols: {', '.join(SYMBOLS)}")
    print()

    # Collect funding rates
    print("📊 Collecting funding rates...")
    funding_rates = await collect_all_funding_rates()

    if not funding_rates:
        print("❌ No funding rates collected")
        return

    print(f"✅ Collected {len(funding_rates)} funding rates")
    print()

    # Export current rates to file
    with open("current_funding_rates.json", "w") as f:
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
    print("💾 Saved current rates to current_funding_rates.json")
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
        print(f"{'#':<3} {'Symbol':<8} {'Long Exch':<12} {'Int':<5} {'Rate':<10} {'Maker':<8} {'Taker':<8} {'Short Exch':<12} {'Int':<5} {'Rate':<10} {'Maker':<8} {'Taker':<8} {'Spread/h':<10} {'Annual':<10}")
        print("-" * 135)

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

            print(f"{idx:<3} {opp.symbol:<8} {opp.long_exchange:<12} {long_interval:<5} {long_rate_pct:<10} {long_maker:<8} {long_taker:<8} {opp.short_exchange:<12} {short_interval:<5} {short_rate_pct:<10} {short_maker:<8} {short_taker:<8} {spread_pct:<10} {annual_return:<10}")

        print("=" * 135)
        print()

        # Save to JSON
        with open("arbitrage_opportunities.json", "w") as f:
            json.dump([opp.to_dict() for opp in opportunities], f, indent=2)
        print("💾 Saved opportunities to arbitrage_opportunities.json")
    else:
        print("ℹ️  No arbitrage opportunities found (rate difference < threshold)")


if __name__ == "__main__":
    asyncio.run(main())
