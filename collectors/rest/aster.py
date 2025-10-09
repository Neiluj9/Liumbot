"""Aster exchange collector"""

import aiohttp
import asyncio
from datetime import datetime
from typing import List
from collectors.rest.base import BaseCollector
from models import FundingRate
from config import get_fees, get_funding_interval, ASTER_API_BASE


class AsterCollector(BaseCollector):
    """Collector for Aster exchange"""

    def __init__(self):
        super().__init__("aster")
        self.api_base = ASTER_API_BASE

    def _normalize_aster_symbol(self, symbol: str) -> str:
        """Convert standard symbol to Aster format (e.g., BTC -> BTCUSDT)"""
        return f"{symbol}USDT"

    def _get_funding_interval(self, symbol: str) -> int:
        """Get funding interval for a symbol (4h or 8h depending on symbol)"""
        return get_funding_interval("aster", symbol)

    async def get_funding_rates(self, symbols: List[str]) -> List[FundingRate]:
        """Get current funding rates for symbols using premiumIndex endpoint"""
        funding_rates = []

        async with aiohttp.ClientSession() as session:
            # Get all premium index data (includes funding rates) and 24h ticker data (includes volumes)
            premium_url = f"{self.api_base}/fapi/v1/premiumIndex"
            ticker_url = f"{self.api_base}/fapi/v1/ticker/24hr"

            try:
                # Fetch both endpoints concurrently
                premium_task = session.get(premium_url)
                ticker_task = session.get(ticker_url)

                premium_response, ticker_response = await asyncio.gather(premium_task, ticker_task, return_exceptions=True)

                # Get volume data from ticker response
                volumes = {}
                if not isinstance(ticker_response, Exception):
                    async with ticker_response:
                        ticker_data = await ticker_response.json()
                        # Convert single object to list for uniform processing
                        if isinstance(ticker_data, dict):
                            ticker_data = [ticker_data]

                        for item in ticker_data:
                            aster_symbol = item.get("symbol", "")
                            # Match with our symbols
                            for symbol in symbols:
                                if aster_symbol == self._normalize_aster_symbol(symbol):
                                    # Volume is in quote currency (USDT)
                                    volume_24h = float(item.get("quoteVolume", 0))
                                    if volume_24h > 0:
                                        volumes[symbol] = volume_24h
                                    break

                # Process premium index data
                if isinstance(premium_response, Exception):
                    raise premium_response

                async with premium_response:
                    data = await premium_response.json()

                    # Convert single object to list for uniform processing
                    if isinstance(data, dict):
                        data = [data]

                    # Filter for our symbols
                    for item in data:
                        aster_symbol = item.get("symbol", "")

                        # Try to match with our symbols
                        for symbol in symbols:
                            if aster_symbol == self._normalize_aster_symbol(symbol):
                                # Get fees from config
                                maker_fee, taker_fee = get_fees("aster", symbol)

                                funding_rates.append(FundingRate(
                                    exchange=self.exchange_name,
                                    symbol=symbol,
                                    funding_rate=float(item.get("lastFundingRate", 0)),
                                    timestamp=datetime.fromtimestamp(item["time"] / 1000),
                                    funding_interval_hours=self._get_funding_interval(symbol),
                                    next_funding_time=datetime.fromtimestamp(
                                        item["nextFundingTime"] / 1000
                                    ) if item.get("nextFundingTime") else None,
                                    maker_fee=maker_fee,
                                    taker_fee=taker_fee,
                                    volume_24h=volumes.get(symbol)
                                ))
                                break

            except Exception as e:
                print(f"Error fetching funding rates from Aster: {e}")

        return funding_rates

    async def get_funding_history(
        self,
        symbol: str,
        start_time: int,
        end_time: int = None,
        limit: int = 100
    ) -> List[FundingRate]:
        """Get historical funding rates for a symbol"""
        funding_rates = []
        aster_symbol = self._normalize_aster_symbol(symbol)
        url = f"{self.api_base}/fapi/v1/fundingRate"

        params = {
            "symbol": aster_symbol,
            "limit": min(limit, 1000)  # Max 1000
        }

        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, params=params) as response:
                    data = await response.json()

                    for item in data:
                        funding_rates.append(FundingRate(
                            exchange=self.exchange_name,
                            symbol=symbol,
                            funding_rate=float(item["fundingRate"]),
                            timestamp=datetime.fromtimestamp(item["fundingTime"] / 1000),
                            funding_interval_hours=self._get_funding_interval(symbol)
                        ))

            except Exception as e:
                print(f"Error fetching history for {symbol} from Aster: {e}")

        return funding_rates
