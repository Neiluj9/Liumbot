"""Base WebSocket collector class for orderbook data"""

import asyncio
import json
from abc import ABC, abstractmethod
from typing import Optional, Callable, Dict
from datetime import datetime
from models import SymbolMetadata


class OrderbookData:
    """Container for orderbook snapshot"""
    def __init__(self, symbol: str, best_bid: float, best_ask: float, timestamp: datetime):
        self.symbol = symbol
        self.best_bid = best_bid
        self.best_ask = best_ask
        self.timestamp = timestamp


class WebSocketCollector(ABC):
    """Abstract base class for WebSocket orderbook collectors"""

    def __init__(self, exchange_name: str):
        self.exchange_name = exchange_name
        self.ws = None
        self.running = False
        self.reconnect_delay = 5  # seconds
        self.max_reconnect_delay = 60  # Max backoff delay
        self.callback: Optional[Callable[[OrderbookData], None]] = None
        self._metadata_cache: Dict[str, SymbolMetadata] = {}  # Cache for symbol metadata
        self._ping_task = None
        self._connection_start_time = None

    @abstractmethod
    async def get_ws_url(self, symbol: str) -> str:
        """Get WebSocket URL for the exchange"""
        pass

    @abstractmethod
    async def get_subscribe_message(self, symbol: str) -> str:
        """Get subscription message for orderbook"""
        pass

    @abstractmethod
    def parse_orderbook(self, message: str, symbol: str) -> Optional[OrderbookData]:
        """Parse WebSocket message and extract best bid/ask

        Returns:
            OrderbookData if message contains orderbook update, None otherwise
        """
        pass

    @abstractmethod
    async def fetch_symbol_metadata(self, symbol: str) -> Optional[SymbolMetadata]:
        """Fetch symbol metadata including tick size and price precision

        Returns:
            SymbolMetadata if successful, None otherwise
        """
        pass

    async def send_application_ping(self) -> Optional[str]:
        """Send application-level ping message (exchange-specific)

        Override this method if the exchange requires application-level pings.
        Return the ping message to send, or None if not needed.
        """
        return None

    def set_callback(self, callback: Callable[[OrderbookData], None]):
        """Set callback function to be called on orderbook updates"""
        self.callback = callback

    async def get_metadata(self, symbol: str) -> Optional[SymbolMetadata]:
        """Get symbol metadata, using cache if available"""
        if symbol not in self._metadata_cache:
            metadata = await self.fetch_symbol_metadata(symbol)
            if metadata:
                self._metadata_cache[symbol] = metadata
        return self._metadata_cache.get(symbol)

    async def _ping_loop(self):
        """Send periodic pings to keep connection alive"""
        try:
            while self.running and self.ws:
                await asyncio.sleep(20)  # Ping every 20 seconds
                if self.ws:
                    try:
                        # Check if connection is still open
                        if hasattr(self.ws, 'closed') and self.ws.closed:
                            break

                        # Try exchange-specific application ping first
                        app_ping = await self.send_application_ping()
                        if app_ping:
                            await self.ws.send(app_ping)
                        else:
                            # Fallback to WebSocket protocol ping
                            await self.ws.ping()
                    except Exception:
                        # Connection likely closed, will be handled by main loop
                        break
        except asyncio.CancelledError:
            pass

    async def connect(self, symbol: str):
        """Connect to WebSocket and start receiving orderbook data"""
        import websockets

        self.running = True
        current_delay = self.reconnect_delay

        while self.running:
            try:
                url = await self.get_ws_url(symbol)

                async with websockets.connect(url) as ws:
                    self.ws = ws
                    self._connection_start_time = datetime.now()
                    print(f"[{self.exchange_name}] Connected to WebSocket")

                    # Send subscription message
                    subscribe_msg = await self.get_subscribe_message(symbol)
                    if subscribe_msg:  # Some exchanges don't need explicit subscription
                        await ws.send(subscribe_msg)
                    print(f"[{self.exchange_name}] Subscribed to {symbol} orderbook")

                    # Start ping task
                    self._ping_task = asyncio.create_task(self._ping_loop())

                    # Receive messages
                    async for message in ws:
                        if not self.running:
                            break

                        orderbook = self.parse_orderbook(message, symbol)
                        if orderbook and self.callback:
                            self.callback(orderbook)

                    # Connection closed normally
                    if self._ping_task:
                        self._ping_task.cancel()
                        try:
                            await self._ping_task
                        except asyncio.CancelledError:
                            pass

            except websockets.exceptions.ConnectionClosed as e:
                if self._ping_task:
                    self._ping_task.cancel()

                # Check if connection was stable (>5 minutes), reset delay
                if self._connection_start_time:
                    uptime = (datetime.now() - self._connection_start_time).total_seconds()
                    if uptime > 300:  # 5 minutes
                        current_delay = self.reconnect_delay

                print(f"[{self.exchange_name}] Connection closed, reconnecting in {current_delay}s...")
                await asyncio.sleep(current_delay)

                # Exponential backoff
                current_delay = min(current_delay * 2, self.max_reconnect_delay)

            except Exception as e:
                if self._ping_task:
                    self._ping_task.cancel()

                print(f"[{self.exchange_name}] Error: {e}, reconnecting in {current_delay}s...")
                await asyncio.sleep(current_delay)

                # Exponential backoff
                current_delay = min(current_delay * 2, self.max_reconnect_delay)

    async def disconnect(self):
        """Disconnect from WebSocket"""
        self.running = False
        if self._ping_task:
            self._ping_task.cancel()
        if self.ws:
            await self.ws.close()
