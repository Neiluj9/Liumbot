"""MEXC WebSocket collector for orderbook data using Protocol Buffers (Aug 2025+)"""

import json
import sys
import os
import aiohttp
from typing import Optional
from datetime import datetime
from collectors.websocket_base import WebSocketCollector, OrderbookData
from models import SymbolMetadata

# Add protobuf path
proto_dir = os.path.join(os.path.dirname(__file__), "mexc-websocket-proto")
if proto_dir not in sys.path:
    sys.path.insert(0, proto_dir)

try:
    from PushDataV3ApiWrapper_pb2 import PushDataV3ApiWrapper
    PROTOBUF_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ MEXC Protobuf not available: {e}")
    print("Run: cd collectors/mexc-websocket-proto && protoc --python_out=. *.proto")
    PROTOBUF_AVAILABLE = False


class MEXCWebSocket(WebSocketCollector):
    """WebSocket collector for MEXC Spot exchange using Protobuf"""

    def __init__(self):
        super().__init__("MEXC")
        # MEXC Spot WebSocket (new API since Aug 2025)
        self.ws_url = "wss://wbs-api.mexc.com/ws"
        self.api_url = "https://api.mexc.com/api/v3/exchangeInfo"

        if not PROTOBUF_AVAILABLE:
            raise ImportError("MEXC Protobuf files not compiled. See error above.")

    def _normalize_symbol(self, symbol: str) -> str:
        """Convert standard symbol to MEXC format (e.g., BTC -> BTCUSDT)"""
        return f"{symbol.upper()}USDT"

    async def get_ws_url(self, symbol: str) -> str:
        """Get WebSocket URL for MEXC"""
        return self.ws_url

    async def get_subscribe_message(self, symbol: str) -> str:
        """Get subscription message for orderbook

        MEXC Protobuf format:
        {
            "method": "SUBSCRIPTION",
            "params": ["spot@public.aggre.bookTicker.v3.api.pb@10ms@BTCUSDT"]
        }
        """
        mexc_symbol = self._normalize_symbol(symbol)
        channel = f"spot@public.aggre.bookTicker.v3.api.pb@10ms@{mexc_symbol}"

        subscribe_msg = {
            "method": "SUBSCRIPTION",
            "params": [channel]
        }
        return json.dumps(subscribe_msg)

    def parse_orderbook(self, message: str, symbol: str) -> Optional[OrderbookData]:
        """Parse MEXC Protobuf orderbook message

        MEXC sends:
        - JSON messages for subscription confirmation
        - Binary Protobuf messages for data
        """
        # Handle JSON messages (subscription confirmations)
        if isinstance(message, str):
            try:
                msg = json.loads(message)
                # Ignore confirmation messages
                return None
            except json.JSONDecodeError:
                return None

        # Handle Protobuf messages (actual data)
        if isinstance(message, bytes):
            try:
                wrapper = PushDataV3ApiWrapper()
                wrapper.ParseFromString(message)

                # Check message type
                body_type = wrapper.WhichOneof("body")

                if body_type == "publicAggreBookTicker":
                    ticker = wrapper.publicAggreBookTicker

                    # Extract best bid and ask
                    best_bid = float(ticker.bidPrice)
                    best_ask = float(ticker.askPrice)

                    # Use send time or current time
                    if wrapper.sendTime:
                        timestamp = datetime.fromtimestamp(wrapper.sendTime / 1000)
                    else:
                        timestamp = datetime.now()

                    return OrderbookData(
                        symbol=symbol,
                        best_bid=best_bid,
                        best_ask=best_ask,
                        timestamp=timestamp
                    )

            except Exception as e:
                # Silently ignore parsing errors
                return None

        return None

    async def fetch_symbol_metadata(self, symbol: str) -> Optional[SymbolMetadata]:
        """Fetch symbol metadata from MEXC API

        Returns:
            SymbolMetadata with tick size and price precision
        """
        try:
            mexc_symbol = self._normalize_symbol(symbol)

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.api_url}?symbol={mexc_symbol}",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status != 200:
                        print(f"[{self.exchange_name}] Failed to fetch metadata: HTTP {response.status}")
                        return None

                    data = await response.json()
                    symbols_data = data.get("symbols", [])

                    if not symbols_data:
                        print(f"[{self.exchange_name}] No symbol data found for {mexc_symbol}")
                        return None

                    symbol_info = symbols_data[0]

                    # Extract price precision from PRICE_FILTER
                    tick_size = None
                    price_precision = 2  # Default

                    for filter_obj in symbol_info.get("filters", []):
                        if filter_obj.get("filterType") == "PRICE_FILTER":
                            tick_size_str = filter_obj.get("tickSize", "0.01")
                            tick_size = float(tick_size_str)

                            # Calculate precision from tick size
                            # e.g., 0.01 -> 2 decimals, 0.0001 -> 4 decimals
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
