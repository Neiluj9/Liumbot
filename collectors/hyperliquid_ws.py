"""Hyperliquid WebSocket collector for orderbook data"""

import json
import aiohttp
from typing import Optional
from datetime import datetime
from collectors.websocket_base import WebSocketCollector, OrderbookData
from models import SymbolMetadata


class HyperliquidWebSocket(WebSocketCollector):
    """WebSocket collector for Hyperliquid exchange"""

    def __init__(self):
        super().__init__("Hyperliquid")
        self.ws_url = "wss://api.hyperliquid.xyz/ws"
        self.api_url = "https://api.hyperliquid.xyz/info"

    async def get_ws_url(self, symbol: str) -> str:
        """Get WebSocket URL for Hyperliquid"""
        return self.ws_url

    async def get_subscribe_message(self, symbol: str) -> str:
        """Get subscription message for orderbook

        Hyperliquid subscription format:
        {
            "method": "subscribe",
            "subscription": {
                "type": "l2Book",
                "coin": "BTC"
            }
        }
        """
        subscribe_msg = {
            "method": "subscribe",
            "subscription": {
                "type": "l2Book",
                "coin": symbol
            }
        }
        return json.dumps(subscribe_msg)

    def parse_orderbook(self, message: str, symbol: str) -> Optional[OrderbookData]:
        """Parse Hyperliquid orderbook message

        Hyperliquid orderbook format:
        {
            "channel": "l2Book",
            "data": {
                "coin": "BTC",
                "levels": [
                    [  # Single snapshot
                        [{"px": "125497.0", "sz": "0.025", "n": 2}, ...],  # bids (descending)
                        [{"px": "125498.0", "sz": "0.020", "n": 1}, ...]   # asks (ascending)
                    ]
                ],
                "time": 1759780168345
            }
        }
        """
        try:
            msg = json.loads(message)

            # Check if it's an orderbook update
            if msg.get("channel") != "l2Book":
                return None

            data = msg.get("data", {})
            if data.get("coin") != symbol:
                return None

            levels = data.get("levels", [])
            if not levels or len(levels) < 2:
                return None

            # levels = [bids_list, asks_list]
            bids = levels[0]  # List of bid levels (sorted descending by price)
            asks = levels[1]  # List of ask levels (sorted ascending by price)

            if not bids or not asks:
                return None

            # Get best bid (highest buy price) and best ask (lowest sell price)
            best_bid = float(bids[0]["px"])
            best_ask = float(asks[0]["px"])

            timestamp = datetime.fromtimestamp(data.get("time", 0) / 1000)

            return OrderbookData(
                symbol=symbol,
                best_bid=best_bid,
                best_ask=best_ask,
                timestamp=timestamp
            )

        except (json.JSONDecodeError, KeyError, IndexError, ValueError) as e:
            # Silently ignore parsing errors (could be heartbeat or other messages)
            return None

    async def fetch_symbol_metadata(self, symbol: str) -> Optional[SymbolMetadata]:
        """Fetch symbol metadata from Hyperliquid API

        Returns:
            SymbolMetadata with tick size and price precision
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url,
                    json={"type": "meta"},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status != 200:
                        print(f"[{self.exchange_name}] Failed to fetch metadata: HTTP {response.status}")
                        return None

                    data = await response.json()
                    universe = data.get("universe", [])

                    # Find the symbol in the universe
                    for asset in universe:
                        if asset.get("name") == symbol:
                            # Hyperliquid uses szDecimals for both price and quantity precision
                            sz_decimals = asset.get("szDecimals", 2)

                            # Calculate tick size from decimals
                            tick_size = 10 ** (-sz_decimals)

                            return SymbolMetadata(
                                symbol=symbol,
                                exchange=self.exchange_name,
                                tick_size=tick_size,
                                price_precision=sz_decimals,
                                quantity_precision=sz_decimals
                            )

                    print(f"[{self.exchange_name}] Symbol {symbol} not found in metadata")
                    return None

        except Exception as e:
            print(f"[{self.exchange_name}] Error fetching metadata: {e}")
            return None
