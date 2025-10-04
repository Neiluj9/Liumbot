"""Script to fetch and compare available symbols across exchanges"""

import asyncio
import aiohttp
from typing import Set


async def get_hyperliquid_symbols() -> Set[str]:
    """Get available symbols from Hyperliquid"""
    symbols = set()
    url = "https://api.hyperliquid.xyz/info"

    async with aiohttp.ClientSession() as session:
        try:
            payload = {"type": "meta"}
            async with session.post(url, json=payload) as response:
                data = await response.json()

                # Extract universe of assets
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


async def main():
    """Main function to compare symbols across exchanges"""
    print("Fetching symbols from exchanges...\n")

    # Fetch symbols concurrently
    hyperliquid_symbols, mexc_symbols, aster_symbols = await asyncio.gather(
        get_hyperliquid_symbols(),
        get_mexc_symbols(),
        get_aster_symbols()
    )

    print(f"Hyperliquid: {len(hyperliquid_symbols)} symbols")
    print(f"MEXC:        {len(mexc_symbols)} symbols")
    print(f"Aster:       {len(aster_symbols)} symbols")
    print()

    # Find common symbols (at least 2 exchanges)
    common_all_3 = hyperliquid_symbols & mexc_symbols & aster_symbols
    common_hl_mexc = hyperliquid_symbols & mexc_symbols
    common_hl_aster = hyperliquid_symbols & aster_symbols
    common_mexc_aster = mexc_symbols & aster_symbols

    # Union of all pairs (any symbol on at least 2 exchanges)
    common_symbols = common_hl_mexc | common_hl_aster | common_mexc_aster

    print(f"Common symbols across all 3 exchanges: {len(common_all_3)}")
    print(f"Common symbols (Hyperliquid + MEXC): {len(common_hl_mexc)}")
    print(f"Common symbols (Hyperliquid + Aster): {len(common_hl_aster)}")
    print(f"Common symbols (MEXC + Aster): {len(common_mexc_aster)}")
    print(f"Total symbols on at least 2 exchanges: {len(common_symbols)}")
    print()

    # Sort and display
    common_list = sorted(list(common_symbols))

    print("Symbols available on at least 2 exchanges:")
    print("=" * 60)
    for i, symbol in enumerate(common_list, 1):
        # Show which exchanges have this symbol
        exchanges = []
        if symbol in hyperliquid_symbols:
            exchanges.append("HL")
        if symbol in mexc_symbols:
            exchanges.append("MEXC")
        if symbol in aster_symbols:
            exchanges.append("Aster")
        print(f"{i:3d}. {symbol:12} [{', '.join(exchanges)}]")

    print()
    print("Python list format:")
    print("=" * 60)
    print(f"SYMBOLS = {common_list}")

    # Save to file
    with open("common_symbols.txt", "w") as f:
        f.write(f"SYMBOLS = {common_list}\n")

    print()
    print("Saved to common_symbols.txt")


if __name__ == "__main__":
    asyncio.run(main())
