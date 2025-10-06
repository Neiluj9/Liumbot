"""Funding rate analyzer for arbitrage opportunities"""

from typing import List, Dict
from datetime import datetime
from models import FundingRate, ArbitrageOpportunity


class FundingRateAnalyzer:
    """Analyze funding rates across exchanges for arbitrage"""

    def __init__(self, min_rate_diff: float = 0.0):
        self.min_rate_diff = min_rate_diff

    def find_arbitrage_opportunities(
        self,
        funding_rates: List[FundingRate]
    ) -> List[ArbitrageOpportunity]:
        """Find arbitrage opportunities from funding rate data"""
        opportunities = []

        # Group by symbol
        by_symbol: Dict[str, List[FundingRate]] = {}
        for rate in funding_rates:
            if rate.symbol not in by_symbol:
                by_symbol[rate.symbol] = []
            by_symbol[rate.symbol].append(rate)

        # Compare rates for each symbol across exchanges
        for symbol, rates in by_symbol.items():
            if len(rates) < 2:
                continue

            # Sort by HOURLY funding rate for fair comparison
            sorted_rates = sorted(rates, key=lambda x: x.hourly_rate)

            # Check difference between lowest and highest (in hourly terms)
            lowest = sorted_rates[0]
            highest = sorted_rates[-1]

            rate_diff = highest.hourly_rate - lowest.hourly_rate

            if abs(rate_diff) >= self.min_rate_diff:
                # Arbitrage: Long on exchange with lowest rate, short on highest
                opportunities.append(ArbitrageOpportunity(
                    symbol=symbol,
                    long_exchange=lowest.exchange,
                    long_rate=lowest.hourly_rate,
                    long_rate_interval=lowest.funding_rate,
                    short_exchange=highest.exchange,
                    short_rate=highest.hourly_rate,
                    short_rate_interval=highest.funding_rate,
                    rate_difference=rate_diff,
                    timestamp=datetime.now(),
                    long_interval=lowest.funding_interval_hours,
                    short_interval=highest.funding_interval_hours,
                    long_maker_fee=lowest.maker_fee,
                    long_taker_fee=lowest.taker_fee,
                    short_maker_fee=highest.maker_fee,
                    short_taker_fee=highest.taker_fee,
                    long_next_funding_time=lowest.next_funding_time,
                    short_next_funding_time=highest.next_funding_time
                ))

        return opportunities
