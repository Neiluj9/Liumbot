"""Hyperliquid exchange collector"""

import aiohttp
from datetime import datetime
from typing import List
from collectors.rest.base import BaseCollector
from models import FundingRate
from config import HYPERLIQUID_API, get_fees, get_funding_interval


class HyperliquidCollector(BaseCollector):
    """Collector for Hyperliquid exchange"""

    def __init__(self):
        super().__init__("hyperliquid")
        self.api_url = HYPERLIQUID_API

    async def get_funding_rates(self, symbols: List[str]) -> List[FundingRate]:
        """Get current/predicted funding rates for symbols"""
        funding_rates = []

        async with aiohttp.ClientSession() as session:
            try:
                # Get predicted fundings
                payload = {"type": "predictedFundings"}
                async with session.post(
                    self.api_url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    data = await response.json()

                    # Data format: [[coin, [[exchange, {data}], ...]], ...]
                    if not isinstance(data, list):
                        print(f"Hyperliquid API returned unexpected format: {type(data)}")
                        return funding_rates

                    for symbol in symbols:
                        # Look for the symbol in the data
                        for item in data:
                            if not isinstance(item, list) or len(item) < 2:
                                continue

                            coin = item[0]
                            exchanges_data = item[1]

                            if coin == symbol and isinstance(exchanges_data, list):
                                # Find HlPerp data
                                for exchange_item in exchanges_data:
                                    if not isinstance(exchange_item, list) or len(exchange_item) < 2:
                                        continue

                                    exchange_name = exchange_item[0]
                                    exchange_data = exchange_item[1]

                                    if exchange_name == "HlPerp" and isinstance(exchange_data, dict):
                                        # Get fees from config
                                        maker_fee, taker_fee = get_fees("hyperliquid", symbol)

                                        funding_rates.append(FundingRate(
                                            exchange=self.exchange_name,
                                            symbol=symbol,
                                            funding_rate=float(exchange_data.get("fundingRate", 0)),
                                            timestamp=datetime.now(),
                                            funding_interval_hours=int(exchange_data.get("fundingIntervalHours", 1)),
                                            next_funding_time=datetime.fromtimestamp(
                                                exchange_data["nextFundingTime"] / 1000
                                            ) if exchange_data.get("nextFundingTime") else None,
                                            maker_fee=maker_fee,
                                            taker_fee=taker_fee
                                        ))
                                        break
                                break
            except Exception as e:
                print(f"Error fetching funding rates from Hyperliquid: {e}")
                import traceback
                traceback.print_exc()

        return funding_rates

    async def get_funding_history(
        self,
        symbol: str,
        start_time: int,
        end_time: int = None
    ) -> List[FundingRate]:
        """Get historical funding rates for a symbol"""
        funding_rates = []

        payload = {
            "type": "fundingHistory",
            "coin": symbol,
            "startTime": start_time
        }
        if end_time:
            payload["endTime"] = end_time

        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.api_url,
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                data = await response.json()

                for item in data:
                    funding_rates.append(FundingRate(
                        exchange=self.exchange_name,
                        symbol=item["coin"],
                        funding_rate=float(item["fundingRate"]),
                        timestamp=datetime.fromtimestamp(item["time"] / 1000),
                        funding_interval_hours=1,  # Hyperliquid pays every hour
                        premium=float(item.get("premium", 0))
                    ))

        return funding_rates
