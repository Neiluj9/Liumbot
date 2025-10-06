"""Hyperliquid exchange executor."""

import requests
import json
from typing import Dict, Any, Optional
from eth_account import Account
from eth_account.signers.local import LocalAccount
import time
from .base import BaseExecutor, OrderResult, OrderType, OrderSide, OrderStatus


class HyperliquidExecutor(BaseExecutor):
    """Hyperliquid exchange executor with API key authentication."""

    BASE_URL = "https://api.hyperliquid.xyz"

    def __init__(self, config: Dict[str, Any]):
        """Initialize Hyperliquid executor.

        Args:
            config: Must contain 'private_key' or 'wallet_address' and 'api_secret'
        """
        super().__init__(config)
        self.private_key = config.get('private_key')
        self.wallet: Optional[LocalAccount] = None

        if self.private_key:
            self.wallet = Account.from_key(self.private_key)
        else:
            raise ValueError("Hyperliquid executor requires 'private_key' in config")

    def get_exchange_symbol(self, normalized_symbol: str) -> str:
        """Convert normalized symbol to Hyperliquid format.

        Args:
            normalized_symbol: e.g., 'BTC'

        Returns:
            Hyperliquid format: e.g., 'BTC'
        """
        # Hyperliquid uses simple symbol names
        return normalized_symbol

    def _sign_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Sign request with wallet private key.

        Args:
            payload: Request payload

        Returns:
            Signed payload with signature
        """
        if not self.wallet:
            raise ValueError("Wallet not initialized")

        # Create message to sign
        message = json.dumps(payload, separators=(',', ':'))
        message_hash = Account._hash_eip191_message(message.encode())
        signature = self.wallet.signHash(message_hash)

        return {
            **payload,
            "signature": {
                "r": hex(signature.r),
                "s": hex(signature.s),
                "v": signature.v
            }
        }

    def place_order(
        self,
        symbol: str,
        side: OrderSide,
        size: float,
        order_type: OrderType = OrderType.LIMIT,
        price: Optional[float] = None
    ) -> OrderResult:
        """Place order on Hyperliquid.

        Args:
            symbol: Normalized symbol (e.g., 'BTC')
            side: Order side
            size: Order size in contracts/coins
            order_type: LIMIT or MARKET
            price: Limit price (required for LIMIT orders)

        Returns:
            OrderResult
        """
        exchange_symbol = self.get_exchange_symbol(symbol)

        if order_type == OrderType.LIMIT and price is None:
            raise ValueError("Price is required for LIMIT orders")

        # Determine is_buy based on side
        is_buy = side in [OrderSide.LONG, OrderSide.CLOSE_SHORT]

        # Hyperliquid order payload
        order_payload = {
            "coin": exchange_symbol,
            "is_buy": is_buy,
            "sz": size,
            "limit_px": price if order_type == OrderType.LIMIT else None,
            "order_type": {"limit": {"tif": "Gtc"}} if order_type == OrderType.LIMIT else {"market": {}},
            "reduce_only": side in [OrderSide.CLOSE_LONG, OrderSide.CLOSE_SHORT]
        }

        payload = {
            "action": {
                "type": "order",
                "orders": [order_payload],
                "grouping": "na"
            },
            "nonce": int(time.time() * 1000),
            "vaultAddress": None
        }

        try:
            signed_payload = self._sign_request(payload)

            response = requests.post(
                f"{self.BASE_URL}/exchange",
                json=signed_payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            data = response.json()

            # Parse Hyperliquid response
            if data.get('status') == 'ok':
                statuses = data.get('response', {}).get('data', {}).get('statuses', [])
                if statuses and statuses[0].get('filled'):
                    order_id = str(statuses[0].get('oid'))
                    return OrderResult(
                        order_id=order_id,
                        exchange='hyperliquid',
                        symbol=symbol,
                        side=side,
                        order_type=order_type,
                        size=size,
                        price=price,
                        status=OrderStatus.PENDING,
                        raw_response=data
                    )
                else:
                    raise Exception(f"Hyperliquid order rejected: {statuses}")
            else:
                raise Exception(f"Hyperliquid order failed: {data}")

        except Exception as e:
            raise Exception(f"Failed to place Hyperliquid order: {str(e)}")

    def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancel order on Hyperliquid.

        Args:
            order_id: Order ID
            symbol: Normalized symbol

        Returns:
            True if cancelled successfully
        """
        exchange_symbol = self.get_exchange_symbol(symbol)

        payload = {
            "action": {
                "type": "cancel",
                "cancels": [{
                    "coin": exchange_symbol,
                    "oid": int(order_id)
                }]
            },
            "nonce": int(time.time() * 1000),
            "vaultAddress": None
        }

        try:
            signed_payload = self._sign_request(payload)

            response = requests.post(
                f"{self.BASE_URL}/exchange",
                json=signed_payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            data = response.json()

            return data.get('status') == 'ok'

        except Exception as e:
            print(f"Failed to cancel Hyperliquid order: {str(e)}")
            return False

    def get_order_status(self, order_id: str, symbol: str) -> OrderResult:
        """Get order status from Hyperliquid.

        Args:
            order_id: Order ID
            symbol: Normalized symbol

        Returns:
            OrderResult with current status
        """
        if not self.wallet:
            raise ValueError("Wallet not initialized")

        try:
            # Query user's open orders
            response = requests.post(
                f"{self.BASE_URL}/info",
                json={
                    "type": "openOrders",
                    "user": self.wallet.address
                }
            )
            response.raise_for_status()
            orders = response.json()

            # Find the order
            for order in orders:
                if str(order.get('oid')) == order_id:
                    # Order still open
                    filled_sz = float(order.get('filledSz', 0))
                    total_sz = float(order.get('sz', 0))

                    if filled_sz == 0:
                        status = OrderStatus.PENDING
                    elif filled_sz < total_sz:
                        status = OrderStatus.PARTIAL
                    else:
                        status = OrderStatus.FILLED

                    return OrderResult(
                        order_id=order_id,
                        exchange='hyperliquid',
                        symbol=symbol,
                        side=OrderSide.LONG if order.get('side') == 'B' else OrderSide.SHORT,
                        order_type=OrderType.LIMIT,
                        size=total_sz,
                        price=float(order.get('limitPx', 0)),
                        status=status,
                        filled_quantity=filled_sz,
                        raw_response=order
                    )

            # Order not found in open orders, might be filled or cancelled
            # Query user fills
            response = requests.post(
                f"{self.BASE_URL}/info",
                json={
                    "type": "userFills",
                    "user": self.wallet.address
                }
            )
            response.raise_for_status()
            fills = response.json()

            for fill in fills:
                if str(fill.get('oid')) == order_id:
                    return OrderResult(
                        order_id=order_id,
                        exchange='hyperliquid',
                        symbol=symbol,
                        side=OrderSide.LONG if fill.get('side') == 'B' else OrderSide.SHORT,
                        order_type=OrderType.LIMIT,
                        size=float(fill.get('sz', 0)),
                        price=float(fill.get('px', 0)),
                        status=OrderStatus.FILLED,
                        filled_quantity=float(fill.get('sz', 0)),
                        average_price=float(fill.get('px', 0)),
                        raw_response=fill
                    )

            # Order not found anywhere, assume cancelled
            raise Exception(f"Order {order_id} not found")

        except Exception as e:
            raise Exception(f"Failed to get Hyperliquid order status: {str(e)}")
