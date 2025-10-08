"""Aster Futures WebSocket order monitor

Integrates with AsterExecutor to provide real-time order status updates.
This is a companion module to executors/aster.py
"""

import asyncio
import json
import math
import time
import requests
from typing import Optional, Callable, Dict, Any
from datetime import datetime
from eth_abi import encode
from eth_account import Account
from eth_account.messages import encode_defunct
from web3 import Web3
from .base import OrderResult, OrderStatus, OrderSide, OrderType


class AsterOrderMonitor:
    """WebSocket monitor for Aster Futures orders

    Usage:
        >>> from executors.aster import AsterExecutor
        >>> from executors.aster_order_monitor import AsterOrderMonitor
        >>>
        >>> executor = AsterExecutor(config)
        >>> monitor = AsterOrderMonitor(
        >>>     wallet_address="0x...",
        >>>     signer_address="0x...",
        >>>     private_key="0x..."
        >>> )
        >>>
        >>> def on_order(order_result: OrderResult):
        >>>     print(f"Order {order_result.order_id}: {order_result.status.name}")
        >>>
        >>> monitor.set_callback(on_order)
        >>> await monitor.connect()
    """

    BASE_URL = "https://fapi.asterdex.com"
    WS_BASE_URL = "wss://fstream.asterdex.com/ws"

    # Aster status to OrderStatus mapping
    # Based on Aster API documentation
    STATUS_MAPPING = {
        'NEW': OrderStatus.PENDING,
        'PARTIALLY_FILLED': OrderStatus.PARTIAL,
        'FILLED': OrderStatus.FILLED,
        'CANCELED': OrderStatus.CANCELLED,
        'EXPIRED': OrderStatus.CANCELLED,
        'REJECTED': OrderStatus.REJECTED,
        'NEW_INSURANCE': OrderStatus.FILLED,  # Liquidation with insurance
        'NEW_ADL': OrderStatus.FILLED,        # ADL liquidation
    }

    def __init__(self, wallet_address: str, signer_address: str, private_key: str):
        """Initialize Aster order monitor

        Args:
            wallet_address: Main wallet address
            signer_address: Authorized signer address
            private_key: Private key of signer address
        """
        self.wallet_address = wallet_address
        self.signer_address = signer_address
        self.private_key = private_key
        self.ws = None
        self.listen_key = None
        self.callback: Optional[Callable[[OrderResult], None]] = None
        self._keepalive_task = None

    def set_callback(self, callback: Callable[[OrderResult], None]):
        """Set callback function to be called on order updates

        Args:
            callback: Function that receives OrderResult
        """
        self.callback = callback

    def _sign_request(self, params: Dict[str, Any], user: str, signer: str, private_key: str, nonce: int) -> Dict[str, Any]:
        """Sign request with EVM-style signature for Aster API"""
        # Remove None values
        params = {key: value for key, value in params.items() if value is not None}

        # Add required fields
        params["recvWindow"] = 50000
        params["timestamp"] = int(round(time.time() * 1000))

        # Convert all params to strings
        for key in params:
            params[key] = str(params[key])

        # Create JSON string (sorted, no spaces)
        json_str = json.dumps(params, sort_keys=True).replace(" ", "")

        # Encode with ABI
        encoded = encode(
            ["string", "address", "address", "uint256"],
            [json_str, user, signer, nonce]
        )

        # Keccak hash
        keccak_hex = Web3.keccak(encoded).hex()

        # Sign the message
        signable_msg = encode_defunct(hexstr=keccak_hex)
        signed_message = Account.sign_message(signable_message=signable_msg, private_key=private_key)

        # Add signature fields to params
        params["nonce"] = nonce
        params["user"] = user
        params["signer"] = signer
        params["signature"] = "0x" + signed_message.signature.hex()

        return params

    def _signed_request(self, method: str, endpoint: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make a signed request to Aster API"""
        if payload is None:
            payload = {}

        # Generate nonce
        nonce = math.trunc(time.time() * 1000000)

        # Sign the request
        signed_params = self._sign_request(
            payload,
            self.wallet_address,
            self.signer_address,
            self.private_key,
            nonce
        )

        url = f"{self.BASE_URL}{endpoint}"

        if method == 'GET':
            response = requests.get(url, params=signed_params)
        elif method == 'POST':
            response = requests.post(url, params=signed_params)
        elif method == 'PUT':
            response = requests.put(url, params=signed_params)
        elif method == 'DELETE':
            response = requests.delete(url, params=signed_params)
        else:
            raise ValueError(f"Unsupported method: {method}")

        response.raise_for_status()
        return response.json()

    def _create_listen_key(self) -> str:
        """Create a listenKey for WebSocket user data stream"""
        data = self._signed_request('POST', '/fapi/v3/listenKey', {})
        return data.get('listenKey')

    def _keepalive_listen_key(self) -> bool:
        """Keep the listenKey alive (must be called every 30 minutes)"""
        if not self.listen_key:
            return False
        try:
            self._signed_request('PUT', '/fapi/v3/listenKey', {})
            return True
        except Exception as e:
            print(f"[Aster-Monitor] Keepalive failed: {e}")
            return False

    def _close_listen_key(self) -> bool:
        """Close the listenKey"""
        if not self.listen_key:
            return False
        try:
            self._signed_request('DELETE', '/fapi/v3/listenKey', {})
            return True
        except Exception as e:
            print(f"[Aster-Monitor] Failed to close listenKey: {e}")
            return False

    async def _keepalive_loop(self, interval: int = 1800):
        """Send periodic keepalive for listenKey (every 30 minutes)"""
        try:
            while True:
                await asyncio.sleep(interval)
                if not self._keepalive_listen_key():
                    print("[Aster-Monitor] Keepalive failed, reconnecting...")
                    # Attempt to reconnect
                    break
        except asyncio.CancelledError:
            pass

    def _parse_order_update(self, data: Dict[str, Any]) -> Optional[OrderResult]:
        """Parse Aster order data to OrderResult

        Args:
            data: Raw order data from WebSocket

        Returns:
            OrderResult or None if parsing fails
        """
        try:
            # Extract event type
            event_type = data.get("e")
            if event_type != "ORDER_TRADE_UPDATE":
                return None

            # Extract order object
            order = data.get("o", {})

            # Extract data
            order_id = str(order.get("i"))
            symbol_raw = order.get("s", "")  # e.g., "BTCUSDT"
            symbol = symbol_raw.replace("USDT", "")  # Normalize to "BTC"

            aster_status = order.get("X")  # Order Status
            aster_side = order.get("S")    # BUY/SELL
            reduce_only = order.get("R", False)
            order_type_str = order.get("o", "LIMIT")  # Order Type

            # Debug: Print raw Aster data
            print(f"[DEBUG] Raw Aster order data: status={aster_status}, side={aster_side}, "
                  f"reduceOnly={reduce_only}, type={order_type_str}, z={order.get('z')}, q={order.get('q')}")

            # Map to our enums
            status = self.STATUS_MAPPING.get(aster_status, OrderStatus.PENDING)

            # Determine OrderSide based on side and reduceOnly
            if aster_side == 'BUY' and not reduce_only:
                side = OrderSide.LONG
            elif aster_side == 'SELL' and not reduce_only:
                side = OrderSide.SHORT
            elif aster_side == 'SELL' and reduce_only:
                side = OrderSide.CLOSE_LONG
            else:  # BUY and reduce_only
                side = OrderSide.CLOSE_SHORT

            # Map order type
            order_type = OrderType.LIMIT if order_type_str in ['LIMIT', 'STOP', 'TAKE_PROFIT'] else OrderType.MARKET

            # Create OrderResult
            return OrderResult(
                order_id=order_id,
                exchange='aster',
                symbol=symbol,
                side=side,
                order_type=order_type,
                size=float(order.get("q", 0)),  # Original quantity
                price=float(order.get("p", 0)) if order.get("p") else None,  # Original price
                status=status,
                filled_quantity=float(order.get("z", 0)),  # Filled accumulated quantity
                average_price=float(order.get("ap", 0)) if order.get("ap") else None,  # Average price
                raw_response=data
            )
        except Exception as e:
            print(f"[Aster-Monitor] Parse error: {e}")
            return None

    async def connect(self):
        """Connect to Aster WebSocket and start monitoring"""
        import websockets

        # Create listenKey
        try:
            self.listen_key = self._create_listen_key()
        except Exception as e:
            raise RuntimeError(f"Failed to create listenKey: {e}")

        # Connect to WebSocket
        ws_url = f"{self.WS_BASE_URL}/{self.listen_key}"

        try:
            self.ws = await websockets.connect(ws_url)

            # Start keepalive task
            self._keepalive_task = asyncio.create_task(
                self._keepalive_loop(interval=1800)  # 30 minutes
            )

            # Process messages
            while True:
                raw = await self.ws.recv()
                msg = json.loads(raw)

                # Print full raw message for debugging
                print(f"[DEBUG] Full WebSocket message: {json.dumps(msg, indent=2)}")

                # Parse order updates
                order_result = self._parse_order_update(msg)
                if order_result and self.callback:
                    self.callback(order_result)

        finally:
            if self._keepalive_task:
                self._keepalive_task.cancel()
            if self.ws:
                await self.ws.close()
            self._close_listen_key()
