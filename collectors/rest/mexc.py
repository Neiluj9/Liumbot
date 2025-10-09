"""MEXC exchange collector"""

import asyncio
import aiohttp
from datetime import datetime
from typing import List
from collectors.rest.base import BaseCollector
from models import FundingRate
from config import MEXC_API_BASE, get_fees


class MEXCCollector(BaseCollector):
    """Collector for MEXC exchange"""

    def __init__(self):
        super().__init__("mexc")
        self.api_base = MEXC_API_BASE

    def _normalize_mexc_symbol(self, symbol: str) -> str:
        """Convert standard symbol to MEXC format (e.g., BTC -> BTC_USDT)"""
        return f"{symbol}_USDT"

    async def get_funding_rates(self, symbols: List[str]) -> List[FundingRate]:
        """Get current funding rates for symbols"""
        # Fetch all funding rates and ticker data (for volume)
        funding_url = f"{self.api_base}/funding_rate"
        ticker_url = f"{self.api_base}/ticker"

        try:
            async with aiohttp.ClientSession() as session:
                # Fetch funding rates and ticker data concurrently
                funding_task = session.get(funding_url, timeout=aiohttp.ClientTimeout(total=10))
                ticker_task = session.get(ticker_url, timeout=aiohttp.ClientTimeout(total=10))

                funding_response, ticker_response = await asyncio.gather(funding_task, ticker_task, return_exceptions=True)

                # Process funding rates
                if isinstance(funding_response, Exception):
                    print(f"    ⚠ MEXC: Failed to fetch funding rates - {funding_response}")
                    return []

                async with funding_response:
                    funding_data = await funding_response.json()

                    if not funding_data.get("success") or not funding_data.get("data"):
                        print(f"    ⚠ MEXC: Failed to fetch funding rates")
                        return []

                    # Create a dict of all funding rates from MEXC
                    all_rates = {}
                    for item in funding_data["data"]:
                        symbol = item.get("symbol", "")
                        # Only keep USDT perpetuals
                        if symbol.endswith("_USDT"):
                            normalized = symbol.replace("_USDT", "")
                            all_rates[normalized] = item

                # Get volume data from ticker response
                volumes = {}
                if not isinstance(ticker_response, Exception):
                    async with ticker_response:
                        ticker_data = await ticker_response.json()
                        if ticker_data.get("success") and ticker_data.get("data"):
                            for item in ticker_data["data"]:
                                symbol = item.get("symbol", "")
                                if symbol.endswith("_USDT"):
                                    normalized = symbol.replace("_USDT", "")
                                    # amount24 is the 24h volume in USDT (quote currency)
                                    volume_24h = float(item.get("amount24", 0))
                                    if volume_24h > 0:
                                        volumes[normalized] = volume_24h

                # Combine funding rates with fee information from config
                funding_rates = []
                for symbol in symbols:
                    if symbol in all_rates:
                        rate_data = all_rates[symbol]

                        # Get fees from config (symbol-specific for MEXC)
                        maker_fee, taker_fee = get_fees("mexc", symbol)

                        funding_rates.append(FundingRate(
                            exchange=self.exchange_name,
                            symbol=symbol,
                            funding_rate=float(rate_data.get("fundingRate", 0)),
                            timestamp=datetime.now(),
                            funding_interval_hours=int(rate_data.get("collectCycle", 8)),
                            next_funding_time=datetime.fromtimestamp(
                                rate_data["nextSettleTime"] / 1000
                            ) if rate_data.get("nextSettleTime") else None,
                            maker_fee=maker_fee,
                            taker_fee=taker_fee,
                            volume_24h=volumes.get(symbol)
                        ))

                return funding_rates

        except Exception as e:
            print(f"    ✗ MEXC: Error fetching funding rates - {e}")
            return []

    async def get_funding_history(
        self,
        symbol: str,
        start_time: int,
        end_time: int = None,
        page_size: int = 100
    ) -> List[FundingRate]:
        """Get historical funding rates for a symbol"""
        funding_rates = []
        mexc_symbol = self._normalize_mexc_symbol(symbol)
        url = f"{self.api_base}/funding_rate/history"

        # Get current funding info to retrieve collectCycle
        funding_interval = 8  # default
        async with aiohttp.ClientSession() as session:
            try:
                current_url = f"{self.api_base}/funding_rate/{mexc_symbol}"
                async with session.get(current_url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    current_data = await response.json()
                    if current_data.get("success") and current_data.get("data"):
                        funding_interval = int(current_data["data"].get("collectCycle", 8))
            except:
                pass  # Use default if API call fails

        async with aiohttp.ClientSession() as session:
            page_num = 1

            while True:
                params = {
                    "symbol": mexc_symbol,
                    "page_num": page_num,
                    "page_size": page_size
                }

                try:
                    async with session.get(url, params=params) as response:
                        data = await response.json()

                        if not data.get("success") or not data.get("data"):
                            break

                        result_list = data["data"].get("resultList", [])
                        if not result_list:
                            break

                        for item in result_list:
                            timestamp = datetime.fromtimestamp(item["settleTime"] / 1000)

                            # Filter by start_time and end_time
                            if timestamp.timestamp() * 1000 < start_time:
                                return funding_rates
                            if end_time and timestamp.timestamp() * 1000 > end_time:
                                continue

                            funding_rates.append(FundingRate(
                                exchange=self.exchange_name,
                                symbol=symbol,
                                funding_rate=float(item["fundingRate"]),
                                timestamp=timestamp,
                                funding_interval_hours=funding_interval
                            ))

                        # Check if we've reached the last page
                        if page_num >= data["data"].get("totalPageNum", 0):
                            break

                        page_num += 1

                except Exception as e:
                    print(f"Error fetching history for {symbol} from MEXC: {e}")
                    break

        return funding_rates
