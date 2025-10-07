"""MEXC Futures WebSocket collector for orderbook data"""

import json
import aiohttp
from typing import Optional
from datetime import datetime
from collectors.websocket.base import WebSocketCollector, OrderbookData
from models import SymbolMetadata


class MEXCFuturesWebSocket(WebSocketCollector):
    """WebSocket collector for MEXC Futures (perpetual contracts)"""

    def __init__(self):
        super().__init__("MEXC-Futures")
        # MEXC Futures WebSocket
        self.ws_url = "wss://contract.mexc.com/edge"
        self.api_url = "https://contract.mexc.com/api/v1/contract/detail"
        self._debug_messages = False  # Set to True to debug unknown messages

    def _normalize_symbol(self, symbol: str) -> str:
        """Convert standard symbol to MEXC futures format (e.g., BTC -> BTC_USDT)"""
        return f"{symbol.upper()}_USDT"

    async def get_ws_url(self, symbol: str) -> str:
        """Get WebSocket URL for MEXC Futures"""
        return self.ws_url

    async def get_subscribe_message(self, symbol: str) -> str:
        """Get subscription message for ticker (best bid/ask)

        MEXC Futures format:
        {
            "method": "sub.ticker",
            "param": {
                "symbol": "BTC_USDT"
            }
        }
        """
        mexc_symbol = self._normalize_symbol(symbol)

        subscribe_msg = {
            "method": "sub.ticker",
            "param": {
                "symbol": mexc_symbol
            }
        }
        return json.dumps(subscribe_msg)

    async def send_application_ping(self) -> Optional[str]:
        """Send MEXC-specific ping to keep connection alive

        MEXC requires application-level pings every <60s
        """
        return json.dumps({"method": "ping"})

    def parse_orderbook(self, message: str, symbol: str) -> Optional[OrderbookData]:
        """Parse MEXC Futures ticker message

        MEXC sends JSON messages like:
        {
            "channel": "push.ticker",
            "data": {
                "symbol": "BTC_USDT",
                "lastPrice": 6865.5,
                "bid1": 6865,
                "ask1": 6866.5,
                "volume24": 164586129
            }
        }

        Also handles ping/pong:
        {"channel": "pong"} or {"msg": "PONG"}
        """
        try:
            if isinstance(message, bytes):
                message = message.decode('utf-8')

            msg = json.loads(message)

            # Handle ping/pong messages
            channel = msg.get("channel", "")
            method = msg.get("method", "")
            if channel in ("ping", "pong", "rs.pong") or method in ("ping", "pong") or msg.get("msg") in ("PING", "PONG"):
                # Ping/pong handled by websockets library or application
                return None

            # Handle subscription confirmation
            if msg.get("channel") == "rs.sub.ticker":
                # Subscription confirmation, no need to log
                return None

            # Handle error messages
            if "error" in msg or msg.get("channel") == "rs.error":
                print(f"[{self.exchange_name}] Error message: {msg}")
                return None

            # Check if it's a ticker update
            if msg.get("channel") == "push.ticker" and "data" in msg:
                data = msg["data"]

                # Extract best bid and ask
                best_bid = float(data.get("bid1", 0))
                best_ask = float(data.get("ask1", 0))

                # Skip if invalid prices
                if best_bid <= 0 or best_ask <= 0:
                    return None

                return OrderbookData(
                    symbol=symbol,
                    best_bid=best_bid,
                    best_ask=best_ask,
                    timestamp=datetime.now()
                )

            # Debug unknown messages
            if self._debug_messages:
                print(f"[{self.exchange_name}] Unknown message: {msg}")

            return None

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            # Log parsing errors for debugging
            if self._debug_messages:
                print(f"[{self.exchange_name}] Parse error: {e}, message: {message[:100]}")
            return None

    async def fetch_symbol_metadata(self, symbol: str) -> Optional[SymbolMetadata]:
        """Fetch symbol metadata from MEXC Futures API

        Returns:
            SymbolMetadata with tick size and price precision
        """
        try:
            mexc_symbol = self._normalize_symbol(symbol)

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.api_url,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status != 200:
                        print(f"[{self.exchange_name}] Failed to fetch metadata: HTTP {response.status}")
                        return None

                    data = await response.json()

                    if not data.get("success") or not data.get("data"):
                        print(f"[{self.exchange_name}] No data in response")
                        return None

                    # Find the contract for our symbol
                    contracts = data["data"]
                    contract = None
                    for c in contracts:
                        if c.get("symbol") == mexc_symbol:
                            contract = c
                            break

                    if not contract:
                        print(f"[{self.exchange_name}] Symbol {mexc_symbol} not found")
                        return None

                    # Extract price precision from priceScale
                    # priceScale is the number of decimal places
                    price_precision = int(contract.get("priceScale", 2))

                    # Calculate tick size from precision
                    # e.g., priceScale=2 -> tick_size=0.01
                    tick_size = 10 ** (-price_precision)

                    # Extract quantity precision from volumeScale
                    quantity_precision = int(contract.get("volumeScale", 0))

                    return SymbolMetadata(
                        symbol=symbol,
                        exchange=self.exchange_name,
                        tick_size=tick_size,
                        price_precision=price_precision,
                        quantity_precision=quantity_precision
                    )

        except Exception as e:
            print(f"[{self.exchange_name}] Error fetching metadata: {e}")
            return None
