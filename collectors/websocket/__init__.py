"""WebSocket collectors for real-time crypto market data"""

from .base import WebSocketCollector, OrderbookData, SymbolMetadata
from .hyperliquid_ws import HyperliquidWebSocket
from .mexc_spot_ws import MEXCWebSocket
from .mexc_futures_ws import MEXCFuturesWebSocket
from .aster_ws import AsterWebSocket

__all__ = [
    "WebSocketCollector",
    "OrderbookData",
    "SymbolMetadata",
    "HyperliquidWebSocket",
    "MEXCWebSocket",
    "MEXCFuturesWebSocket",
    "AsterWebSocket",
]
