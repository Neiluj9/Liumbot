"""Configuration for crypto funding rate arbitrage"""

import json
import os
from typing import Optional, Tuple

# API Endpoints
HYPERLIQUID_API = "https://api.hyperliquid.xyz/info"
MEXC_API_BASE = "https://contract.mexc.com/api/v1/contract"
ASTER_API_BASE = "https://fapi.asterdex.com"

# Exchange configuration
EXCHANGES = {
    "hyperliquid": {
        "name": "Hyperliquid",
        "enabled": True,
        "funding_interval_hours": 1  # Hyperliquid pays every hour
    },
    "mexc": {
        "name": "MEXC",
        "enabled": True,
        "funding_interval_hours": 8  # MEXC pays at 00:00, 08:00, 16:00 UTC
    },
    "aster": {
        "name": "Aster",
        "enabled": True,
        "funding_interval_hours": 8  # Default for symbols not in custom intervals
    }
}

# Load symbols data from JSON file
_SYMBOLS_DATA = None

def _load_symbols_data():
    """Load symbols data from JSON file"""
    global _SYMBOLS_DATA
    if _SYMBOLS_DATA is None:
        json_path = os.path.join(os.path.dirname(__file__), "symbols_data.json")
        try:
            with open(json_path, "r") as f:
                _SYMBOLS_DATA = json.load(f)
        except FileNotFoundError:
            print(f"Warning: {json_path} not found. Run update_symbols.py first.")
            _SYMBOLS_DATA = {
                "symbols": [],
                "exchange_data": {
                    "hyperliquid": {"symbols": {}},
                    "aster": {"symbols": {}},
                    "mexc": {"symbols": {}}
                }
            }
    return _SYMBOLS_DATA

# Symbols to track (loaded from JSON)
def get_symbols():
    """Get list of symbols to track"""
    data = _load_symbols_data()
    return data.get("symbols", [])

# Backward compatibility
SYMBOLS = get_symbols()

def get_funding_interval(exchange: str, symbol: str) -> int:
    """Get funding interval for a specific exchange and symbol

    Args:
        exchange: Exchange name (hyperliquid, mexc, aster)
        symbol: Normalized symbol (e.g., BTC, ETH)

    Returns:
        Funding interval in hours
    """
    data = _load_symbols_data()
    exchange_data = data.get("exchange_data", {}).get(exchange, {})

    # Check if symbol has custom interval
    symbol_data = exchange_data.get("symbols", {}).get(symbol, {})
    if "funding_interval" in symbol_data:
        return symbol_data["funding_interval"]

    # Return exchange default
    return exchange_data.get("funding_interval", EXCHANGES.get(exchange, {}).get("funding_interval_hours", 8))

def get_fees(exchange: str, symbol: str) -> Tuple[Optional[float], Optional[float]]:
    """Get maker and taker fees for a specific exchange and symbol

    Args:
        exchange: Exchange name (hyperliquid, mexc, aster)
        symbol: Normalized symbol (e.g., BTC, ETH)

    Returns:
        Tuple of (maker_fee, taker_fee) as decimals (e.g., 0.0002 = 0.02%)
    """
    data = _load_symbols_data()
    exchange_data = data.get("exchange_data", {}).get(exchange, {})

    # Check if symbol has custom fees (MEXC case)
    symbol_data = exchange_data.get("symbols", {}).get(symbol, {})
    if "maker_fee" in symbol_data and "taker_fee" in symbol_data:
        return (symbol_data["maker_fee"], symbol_data["taker_fee"])

    # Return exchange defaults (Hyperliquid, Aster)
    maker_fee = exchange_data.get("maker_fee")
    taker_fee = exchange_data.get("taker_fee")
    return (maker_fee, taker_fee)

# Trading configuration
# IMPORTANT: Fill in your actual credentials before using trade.py
TRADING_CONFIG = {
    "hyperliquid": {
        # Get your private key from your Hyperliquid wallet
        # NEVER commit this file with real credentials!
        "private_key": "YOUR_HYPERLIQUID_PRIVATE_KEY_HERE",
    },
    "mexc": {
        # Get session cookie from browser after logging into MEXC
        # Copy the entire cookie string from browser dev tools
        "session_cookie": "WEB75e76c307937b536bbd96b67ddde36b38d190308a3bd82b8ea8ff982c89b8c35",
    },
    "aster": {
        # Aster Pro mode with ERC20 wallet
        # wallet_address: Your main ERC20 wallet address
        # signer_address: The signer address authorized to trade
        # private_key: Private key of the signer address (NOT the main wallet)
        "wallet_address": "0xFc0eF8487C9DafD29c99Cb40eF7BD5d5EF553f62",
        "signer_address": "0x93019Ec8bDfA0d94e984B53377D2d3751424F4f8",
        "private_key": "0x2e9055b030b5c75ddd5705b4d6a93c3746a4f50586f505e4966343d04b20027a",
    },
}