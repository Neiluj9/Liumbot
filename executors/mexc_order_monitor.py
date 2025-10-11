"""MEXC Futures WebSocket order monitor

Integrates with MEXCExecutor to provide real-time order status updates.
This is a companion module to executors/mexc.py
"""

import asyncio
import json
import hashlib
import time
import hmac
from typing import Optional, Callable, Dict, Any
from datetime import datetime
from .base import OrderResult, OrderStatus, OrderSide, OrderType


class MEXCOrderMonitor:
    """WebSocket monitor for MEXC Futures orders

    Usage:
        >>> from executors.mexc import MEXCExecutor
        >>> from executors.mexc_order_monitor import MEXCOrderMonitor
        >>>
        >>> executor = MEXCExecutor(config)
        >>> monitor = MEXCOrderMonitor(api_key="...", api_secret="...")
        >>>
        >>> def on_order(order_result: OrderResult):
        >>>     print(f"Order {order_result.order_id}: {order_result.status.name}")
        >>>
        >>> monitor.set_callback(on_order)
        >>> await monitor.connect()
    """

    WS_URL = "wss://contract.mexc.com/edge"

    # MEXC state to OrderStatus mapping
    # Based on actual MEXC WebSocket responses:
    # state=1: Partial fill
    # state=2: New/Open (not yet executed)
    # state=3: Completely filled
    # state=4: Cancelled
    # state=5: Rejected
    STATE_MAPPING = {
        1: OrderStatus.PARTIAL,      # PARTIAL_FILLED
        2: OrderStatus.PENDING,      # NEW/OPEN
        3: OrderStatus.FILLED,       # FILLED
        4: OrderStatus.CANCELLED,    # CANCELLED
        5: OrderStatus.REJECTED,     # REJECTED
    }

    # MEXC side to OrderSide mapping (reverse of executor)
    SIDE_MAPPING = {
        1: OrderSide.LONG,         # Open LONG
        2: OrderSide.CLOSE_SHORT,  # Close SHORT
        3: OrderSide.SHORT,        # Open SHORT
        4: OrderSide.CLOSE_LONG,   # Close LONG
    }

    def __init__(self, api_key: str, api_secret: str):
        """Initialize MEXC order monitor

        Args:
            api_key: MEXC API key
            api_secret: MEXC API secret
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.ws = None
        self.callback: Optional[Callable[[OrderResult], None]] = None
        self._heartbeat_task = None

    def set_callback(self, callback: Callable[[OrderResult], None]):
        """Set callback function to be called on order updates

        Args:
            callback: Function that receives OrderResult
        """
        self.callback = callback

    def _generate_ws_auth_message(self) -> dict:
        """Generate WebSocket authentication message"""
        req_time = str(int(time.time() * 1000))
        signature = hmac.new(
            self.api_secret.encode(),
            (self.api_key + req_time).encode(),
            hashlib.sha256
        ).hexdigest()
        return {
            "method": "login",
            "param": {
                "apiKey": self.api_key,
                "reqTime": req_time,
                "signature": signature
            }
        }

    async def _authenticate(self):
        """Authenticate WebSocket connection"""
        msg = self._generate_ws_auth_message()
        await self.ws.send(json.dumps(msg))

        # Wait for login response
        while True:
            resp = json.loads(await self.ws.recv())
            if resp.get("channel") == "rs.login":
                if resp.get("data") == "success":
                    return
                else:
                    raise RuntimeError(f"MEXC auth failed: {resp}")

    async def _subscribe(self):
        """Subscribe to personal order updates"""
        req = {"method": "sub.personal.order", "param": {}}
        await self.ws.send(json.dumps(req))

    async def _heartbeat_loop(self, interval: int = 30):
        """Send periodic pings"""
        try:
            while True:
                await asyncio.sleep(interval)
                if self.ws:
                    await self.ws.send(json.dumps({"method": "ping"}))
        except asyncio.CancelledError:
            pass

    def _parse_order_update(self, data: Dict[str, Any]) -> Optional[OrderResult]:
        """Parse MEXC order data to OrderResult

        Args:
            data: Raw order data from WebSocket

        Returns:
            OrderResult or None if parsing fails
        """
        try:
            # Extract data
            order_id = str(data.get("orderId"))
            symbol_raw = data.get("symbol", "")  # e.g., "BTC_USDT"
            symbol = symbol_raw.replace("_USDT", "")  # Normalize to "BTC"

            mexc_state = data.get("state")
            mexc_side = data.get("side")
            mexc_type = data.get("type")

            # Debug: Print raw MEXC data
            print(f"[DEBUG] Raw MEXC order data: state={mexc_state}, side={mexc_side}, type={mexc_type}, dealVol={data.get('dealVol')}, vol={data.get('vol')}")

            # Map to our enums
            status = self.STATE_MAPPING.get(mexc_state, OrderStatus.PENDING)
            side = self.SIDE_MAPPING.get(mexc_side, OrderSide.LONG)
            order_type = OrderType.LIMIT if mexc_type == 1 else OrderType.MARKET

            # Create OrderResult
            return OrderResult(
                order_id=order_id,
                exchange='mexc',
                symbol=symbol,
                side=side,
                order_type=order_type,
                size=float(data.get("vol", 0)),
                price=float(data.get("price", 0)) if data.get("price") else None,
                status=status,
                filled_quantity=float(data.get("dealVol", 0)),
                average_price=float(data.get("dealAvgPrice", 0)) if data.get("dealAvgPrice") else None,
                raw_response=data
            )
        except Exception as e:
            print(f"[MEXC-Monitor] Parse error: {e}")
            return None

    async def connect(self, heartbeat_interval: int = 30):
        """Connect to MEXC WebSocket and start monitoring

        Args:
            heartbeat_interval: Ping interval in seconds
        """
        import websockets

        self.ws = await websockets.connect(self.WS_URL)

        try:
            # Authenticate
            await self._authenticate()

            # Start heartbeat
            self._heartbeat_task = asyncio.create_task(
                self._heartbeat_loop(interval=heartbeat_interval)
            )

            # Subscribe to orders
            await self._subscribe()

            # Process messages
            while True:
                raw = await self.ws.recv()
                msg = json.loads(raw)

                # Filter order updates
                if msg.get("channel") == "push.personal.order":
                    order_data = msg.get("data")
                    if order_data:
                        # Print full raw message for debugging
                        print(f"[DEBUG] Full WebSocket message: {json.dumps(msg, indent=2)}")
                        order_result = self._parse_order_update(order_data)
                        if order_result and self.callback:
                            self.callback(order_result)

        finally:
            if self._heartbeat_task:
                self._heartbeat_task.cancel()
            if self.ws:
                await self.ws.close()

    async def disconnect(self):
        """Disconnect from WebSocket and cleanup resources"""
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

        if self.ws:
            await self.ws.close()
            self.ws = None
