"""Script to update symbols_data.json with latest exchange data"""

import asyncio
import aiohttp
import json
from datetime import datetime, timezone
from typing import Set, Dict, Tuple


async def get_hyperliquid_symbols() -> Set[str]:
    """Get available symbols from Hyperliquid"""
    symbols = set()
    url = "https://api.hyperliquid.xyz/info"

    async with aiohttp.ClientSession() as session:
        try:
            payload = {"type": "meta"}
            async with session.post(url, json=payload) as response:
                data = await response.json()

                if "universe" in data:
                    for asset in data["universe"]:
                        if "name" in asset:
                            # Remove USDT suffix if present
                            symbol = asset["name"].replace("-PERP", "").replace("USDT", "").replace("USD", "")
                            symbols.add(symbol)
        except Exception as e:
            print(f"Error fetching Hyperliquid symbols: {e}")

    return symbols


async def get_mexc_symbols() -> Set[str]:
    """Get available symbols from MEXC"""
    symbols = set()
    url = "https://contract.mexc.com/api/v1/contract/detail"

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                data = await response.json()

                if data.get("success") and data.get("data"):
                    for contract in data["data"]:
                        symbol = contract.get("symbol", "")
                        # Remove MEXC suffixes (handle _ separator)
                        for suffix in ["_USDT", "_USD", "_USDC"]:
                            symbol = symbol.replace(suffix, "")
                        if symbol and not symbol.startswith("_"):
                            symbols.add(symbol)
        except Exception as e:
            print(f"Error fetching MEXC symbols: {e}")

    return symbols


async def get_aster_symbols() -> Set[str]:
    """Get available symbols from Aster"""
    symbols = set()
    url = "https://fapi.asterdex.com/fapi/v1/exchangeInfo"

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                data = await response.json()

                if "symbols" in data:
                    for symbol_info in data["symbols"]:
                        symbol = symbol_info.get("symbol", "")
                        # Remove USDT suffix
                        symbol = symbol.replace("USDT", "").replace("USD", "")
                        if symbol and symbol_info.get("status") == "TRADING":
                            symbols.add(symbol)
        except Exception as e:
            print(f"Error fetching Aster symbols: {e}")

    return symbols


async def get_aster_funding_intervals(symbols: Set[str]) -> Dict[str, int]:
    """Detect funding intervals for Aster symbols by analyzing funding history"""
    intervals = {}
    url = "https://fapi.asterdex.com/fapi/v1/fundingRate"

    async with aiohttp.ClientSession() as session:
        print(f"  Detecting Aster funding intervals for {len(symbols)} symbols...")

        # Process symbols in batches to avoid overwhelming the API
        for i, symbol in enumerate(sorted(symbols), 1):
            aster_symbol = f"{symbol}USDT"

            try:
                params = {"symbol": aster_symbol, "limit": 5}
                async with session.get(url, params=params) as response:
                    data = await response.json()

                    if len(data) >= 2:
                        # Calculate time difference between consecutive funding times
                        timestamps = [item["fundingTime"] for item in data[:2]]
                        time_diff_ms = abs(timestamps[0] - timestamps[1])
                        time_diff_hours = time_diff_ms / (1000 * 60 * 60)

                        # Round to nearest hour
                        interval = round(time_diff_hours)

                        # Only store if different from default (8h)
                        if interval != 8:
                            intervals[symbol] = interval

                if i % 50 == 0:
                    print(f"    Processed {i}/{len(symbols)} symbols...")

            except Exception as e:
                # Skip symbols with errors
                pass

    print(f"  Found {len(intervals)} symbols with non-default intervals")
    return intervals


async def get_mexc_fees(symbols: Set[str]) -> Dict[str, Dict[str, float]]:
    """Get maker/taker fees for each MEXC symbol (must query individually)"""
    fees = {}
    url = "https://contract.mexc.com/api/v1/contract/detail"

    async with aiohttp.ClientSession() as session:
        print(f"  Fetching MEXC fees for {len(symbols)} symbols...")

        # First, fetch all contract details
        try:
            async with session.get(url) as response:
                data = await response.json()

                if data.get("success") and data.get("data"):
                    # Build a mapping from normalized symbol to fees
                    for contract in data["data"]:
                        mexc_symbol = contract.get("symbol", "")
                        if mexc_symbol.endswith("_USDT"):
                            normalized = mexc_symbol.replace("_USDT", "")
                            if normalized in symbols:
                                fees[normalized] = {
                                    "maker_fee": float(contract.get("makerFeeRate", 0)),
                                    "taker_fee": float(contract.get("takerFeeRate", 0))
                                }

        except Exception as e:
            print(f"    Error fetching MEXC fees: {e}")

    print(f"  Retrieved fees for {len(fees)} MEXC symbols")
    return fees


async def main():
    """Main function to update symbols_data.json"""
    print("=" * 60)
    print("UPDATING SYMBOLS DATA")
    print("=" * 60)
    print()

    # Fetch symbols from all exchanges
    print("📊 Fetching symbols from exchanges...")
    hyperliquid_symbols, mexc_symbols, aster_symbols = await asyncio.gather(
        get_hyperliquid_symbols(),
        get_mexc_symbols(),
        get_aster_symbols()
    )

    print(f"  Hyperliquid: {len(hyperliquid_symbols)} symbols")
    print(f"  MEXC:        {len(mexc_symbols)} symbols")
    print(f"  Aster:       {len(aster_symbols)} symbols")
    print()

    # Find common symbols (at least 2 exchanges)
    common_hl_mexc = hyperliquid_symbols & mexc_symbols
    common_hl_aster = hyperliquid_symbols & aster_symbols
    common_mexc_aster = mexc_symbols & aster_symbols
    common_symbols = common_hl_mexc | common_hl_aster | common_mexc_aster

    print(f"✅ Found {len(common_symbols)} symbols on at least 2 exchanges")
    print()

    # Get Aster funding intervals (only for Aster symbols)
    aster_common = common_symbols & aster_symbols
    print("⏱️  Detecting Aster funding intervals...")
    aster_intervals = await get_aster_funding_intervals(aster_common)
    print()

    # Get MEXC fees (only for MEXC symbols)
    mexc_common = common_symbols & mexc_symbols
    print("💰 Fetching MEXC fees...")
    mexc_fees = await get_mexc_fees(mexc_common)
    print()

    # Build the data structure
    symbols_data = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "symbols": sorted(list(common_symbols)),
        "exchange_data": {
            "hyperliquid": {
                "funding_interval": 1,
                "maker_fee": 0.00020,
                "taker_fee": 0.00050,
                "symbols": {}
            },
            "aster": {
                "funding_interval": 8,  # Default
                "maker_fee": 0.00010,
                "taker_fee": 0.00035,
                "symbols": {
                    symbol: {"funding_interval": interval}
                    for symbol, interval in aster_intervals.items()
                }
            },
            "mexc": {
                "funding_interval": 8,
                "symbols": mexc_fees
            }
        }
    }

    # Save to file
    with open("symbols_data.json", "w") as f:
        json.dump(symbols_data, f, indent=2)

    print("=" * 60)
    print(f"✅ Updated symbols_data.json")
    print(f"   - {len(common_symbols)} symbols tracked")
    print(f"   - {len(aster_intervals)} Aster symbols with custom intervals")
    print(f"   - {len(mexc_fees)} MEXC symbols with fees")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
