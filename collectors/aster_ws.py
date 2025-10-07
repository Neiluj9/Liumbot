"""Aster WebSocket collector for orderbook data"""

import json
import aiohttp
from typing import Optional
from datetime import datetime
from collectors.websocket_base import WebSocketCollector, OrderbookData
from models import SymbolMetadata


class AsterWebSocket(WebSocketCollector):
    """WebSocket collector for Aster exchange"""

    def __init__(self):
        super().__init__("Aster")
        self.ws_url = "wss://fstream.asterdex.com/ws"
        self.api_url = "https://fapi.asterdex.com/fapi/v3/exchangeInfo"

    def _normalize_symbol(self, symbol: str) -> str:
        """Convert standard symbol to Aster format (e.g., BTC -> btcusdt)"""
        return f"{symbol.lower()}usdt"

    async def get_ws_url(self, symbol: str) -> str:
        """Get WebSocket URL for Aster

        Aster uses generic WebSocket endpoint, subscription via message
        """
        return self.ws_url

    async def get_subscribe_message(self, symbol: str) -> str:
        """Get subscription message for orderbook

        Aster subscription format:
        {
            "method": "SUBSCRIBE",
            "params": ["btcusdt@depth20@100ms"],
            "id": 1
        }
        """
        aster_symbol = self._normalize_symbol(symbol)
        subscribe_msg = {
            "method": "SUBSCRIBE",
            "params": [f"{aster_symbol}@depth20@100ms"],
            "id": 1
        }
        return json.dumps(subscribe_msg)

    def parse_orderbook(self, message: str, symbol: str) -> Optional[OrderbookData]:
        """Parse Aster orderbook message

        Aster orderbook format (Binance-like depth20):
        {
            "e": "depthUpdate",
            "E": 1234567890123,
            "T": 1234567890123,
            "s": "BTCUSDT",
            "U": 1234,
            "u": 1235,
            "pu": 1233,
            "b": [["65000.0", "1.5"], ["64999.0", "2.0"], ...],  # bids
            "a": [["65001.0", "2.0"], ["65002.0", "1.5"], ...]   # asks
        }
        """
        try:
            msg = json.loads(message)

            # Check if it's a depth update
            event_type = msg.get("e")
            if event_type != "depthUpdate":
                # Ignore subscription confirmations and other messages
                return None

            bids = msg.get("b", [])
            asks = msg.get("a", [])

            if not bids or not asks:
                return None

            # Get best bid and ask (first in list)
            best_bid = float(bids[0][0])
            best_ask = float(asks[0][0])

            timestamp = datetime.fromtimestamp(msg.get("E", 0) / 1000)

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
        """Fetch symbol metadata from Aster API

        Returns:
            SymbolMetadata with tick size and price precision
        """
        try:
            aster_symbol = self._normalize_symbol(symbol).upper()  # Aster API uses uppercase

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.api_url,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status != 200:
                        print(f"[{self.exchange_name}] Failed to fetch metadata: HTTP {response.status}")
                        return None

                    data = await response.json()
                    symbols_data = data.get("symbols", [])

                    # Find the symbol in the list
                    symbol_info = None
                    for sym in symbols_data:
                        if sym.get("symbol") == aster_symbol:
                            symbol_info = sym
                            break

                    if not symbol_info:
                        print(f"[{self.exchange_name}] Symbol {aster_symbol} not found in metadata")
                        return None

                    # Extract price precision from PRICE_FILTER
                    tick_size = None
                    price_precision = 2  # Default

                    for filter_obj in symbol_info.get("filters", []):
                        if filter_obj.get("filterType") == "PRICE_FILTER":
                            tick_size_str = filter_obj.get("tickSize", "0.01")
                            tick_size = float(tick_size_str)

                            # Calculate precision from tick size
                            tick_size_str = tick_size_str.rstrip('0')
                            if '.' in tick_size_str:
                                price_precision = len(tick_size_str.split('.')[1])
                            else:
                                price_precision = 0
                            break

                    if tick_size is None:
                        tick_size = 0.01

                    # Extract quantity precision from LOT_SIZE filter
                    quantity_precision = 8  # Default
                    for filter_obj in symbol_info.get("filters", []):
                        if filter_obj.get("filterType") == "LOT_SIZE":
                            step_size_str = filter_obj.get("stepSize", "0.00000001")
                            step_size_str = step_size_str.rstrip('0')
                            if '.' in step_size_str:
                                quantity_precision = len(step_size_str.split('.')[1])
                            else:
                                quantity_precision = 0
                            break

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
