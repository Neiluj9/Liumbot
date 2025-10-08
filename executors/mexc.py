"""MEXC exchange executor using session cookie authentication."""

import time
import hashlib
import json
try:
    from curl_cffi import requests
except ImportError:
    import requests
    print("Warning: curl_cffi not installed. Using standard requests (may be blocked by MEXC)")
from typing import Dict, Any, Optional, Callable
from .base import BaseExecutor, OrderResult, OrderType, OrderSide, OrderStatus


class MEXCExecutor(BaseExecutor):
    """MEXC exchange executor with cookie-based authentication."""

    BASE_URL = "https://futures.mexc.com/api/v1/private"

    # MEXC side mapping
    # 1 = Ouvrir position LONG
    # 2 = Fermer position SHORT
    # 3 = Ouvrir position SHORT
    # 4 = Fermer position LONG
    SIDE_MAPPING = {
        OrderSide.LONG: 1,
        OrderSide.CLOSE_SHORT: 2,
        OrderSide.SHORT: 3,
        OrderSide.CLOSE_LONG: 4,
    }

    def __init__(self, config: Dict[str, Any]):
        """Initialize MEXC executor.

        Args:
            config: Must contain 'cookie_key' key
                   Optional: 'api_key' and 'api_secret' for order monitoring
        """
        super().__init__(config)
        self.cookie_key = config.get('cookie_key')
        if not self.cookie_key:
            raise ValueError("MEXC executor requires 'cookie_key' in config")

        # Optional: API credentials for WebSocket order monitoring
        self.api_key = config.get('api_key')
        self.api_secret = config.get('api_secret')

        # Note: curl_cffi doesn't use Session the same way
        # We'll use direct requests calls instead

    def get_exchange_symbol(self, normalized_symbol: str) -> str:
        """Convert normalized symbol to MEXC format.

        Args:
            normalized_symbol: e.g., 'BTC'

        Returns:
            MEXC format: e.g., 'BTC_USDT'
        """
        return f"{normalized_symbol}_USDT"

    def _get_mexc_side(self, side: OrderSide) -> int:
        """Convert OrderSide to MEXC side integer.

        Args:
            side: OrderSide enum

        Returns:
            MEXC side integer (1-4)
        """
        return self.SIDE_MAPPING[side]

    def _generate_signature(self, payload: dict) -> tuple[str, str]:
        """Generate MEXC cookie signature.

        Args:
            payload: Request payload dict

        Returns:
            Tuple of (timestamp, signature)
        """
        timestamp = str(int(time.time() * 1000))
        # Generate intermediate hash from cookie_key + timestamp, take chars from position 7 onwards
        g = hashlib.md5((self.cookie_key + timestamp).encode()).hexdigest()[7:]
        # Compact JSON (no spaces)
        body = json.dumps(payload, separators=(",", ":"))
        # Final signature
        sign = hashlib.md5((timestamp + body + g).encode()).hexdigest()
        return timestamp, sign

    def _get_signed_headers(self, payload: dict) -> dict:
        """Get headers with MEXC signature for authenticated requests.

        Args:
            payload: Request payload dict

        Returns:
            Headers dict with signature
        """
        timestamp, sign = self._generate_signature(payload)
        return {
            "Content-Type": "application/json",
            "x-mxc-sign": sign,
            "x-mxc-nonce": timestamp,
            "Authorization": self.cookie_key,
        }

    def place_order(
        self,
        symbol: str,
        side: OrderSide,
        size: float,
        order_type: OrderType = OrderType.LIMIT,
        price: Optional[float] = None,
        leverage: int = 1,
        open_type: int = 2,
        position_mode: int = 1,
        price_protect: int = 0,
        external: int = 2
    ) -> OrderResult:
        """Place order on MEXC.

        Args:
            symbol: Normalized symbol (e.g., 'BTC')
            side: Order side
            size: Order size in contracts (volume)
            order_type: LIMIT or MARKET
            price: Limit price (required for LIMIT orders)
            leverage: Leverage (default: 1)
            open_type: Margin mode - 1=Isolated, 2=Cross (default: 2)
            position_mode: Position mode - 1=One-way, 2=Hedge (default: 1)
            price_protect: Price protection - 0=Disabled, 1=Enabled (default: 0)
            external: External flag - 2 (default: 2)

        Returns:
            OrderResult
        """
        exchange_symbol = self.get_exchange_symbol(symbol)
        mexc_side = self._get_mexc_side(side)

        if order_type == OrderType.LIMIT and price is None:
            raise ValueError("Price is required for LIMIT orders")

        # MEXC API payload with ALL required fields
        # Note: All fields must be present as per MEXC API requirements
        payload = {
            "symbol": exchange_symbol,
            "side": mexc_side,
            "vol": size,
            "leverage": leverage,
            "openType": open_type,
            "positionMode": position_mode,
            "priceProtect": price_protect,
            "external": external,  # Required field
        }

        # Add type and price based on order type
        if order_type == OrderType.LIMIT:
            payload["type"] = 1
            payload["price"] = price
        else:  # MARKET
            payload["type"] = 5

        headers = self._get_signed_headers(payload)

        # Use curl_cffi to avoid anti-bot detection
        response = requests.post(
            f"{self.BASE_URL}/order/create",
            json=payload,
            headers=headers,
            timeout=30,
            impersonate="chrome110"
        )

        # Check HTTP status
        if response.status_code != 200:
            raise Exception(f"HTTP {response.status_code}: {response.text}")

        data = response.json()

        # Parse MEXC response
        if data.get('success'):
            # Extract orderId from response data dict
            order_data = data.get('data', {})
            order_id = str(order_data.get('orderId')) if isinstance(order_data, dict) else str(order_data)

            return OrderResult(
                order_id=order_id,
                exchange='mexc',
                symbol=symbol,
                side=side,
                order_type=order_type,
                size=size,
                price=price,
                status=OrderStatus.PENDING,
                raw_response=data
            )
        else:
            # MEXC uses 'msg' field for error messages
            error_msg = data.get('msg') or data.get('message', 'Unknown error')
            raise Exception(f"MEXC order failed (code {data.get('code')}): {error_msg}")

    def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancel order on MEXC.

        Args:
            order_id: Order ID
            symbol: Normalized symbol (not used by MEXC cancel endpoint)

        Returns:
            True if cancelled successfully
        """
        # MEXC cancel expects a list of order IDs
        payload = [order_id]

        headers = self._get_signed_headers(payload)
        response = requests.post(
            f"{self.BASE_URL}/order/cancel",
            json=payload,
            headers=headers,
            timeout=30,
            impersonate="chrome110"
        )

        if response.status_code != 200:
            print(f"Failed to cancel MEXC order: HTTP {response.status_code}")
            return False

        data = response.json()
        return data.get('success', False)

    def get_order_status(self, order_id: str, symbol: str) -> OrderResult:
        """Get order status from MEXC.

        NOTE: MEXC's REST API for order status is not reliable.
        Use MEXCOrderMonitor for real-time order tracking instead.

        Args:
            order_id: Order ID
            symbol: Normalized symbol

        Returns:
            OrderResult with current status

        Raises:
            NotImplementedError: Always (use WebSocket monitoring instead)

        Example:
            >>> from executors.mexc_order_monitor import MEXCOrderMonitor
            >>> monitor = MEXCOrderMonitor(api_key="...", api_secret="...")
            >>> def on_order(order: OrderResult):
            >>>     if order.status == OrderStatus.FILLED:
            >>>         print(f"Order {order.order_id} filled!")
            >>> monitor.set_callback(on_order)
            >>> await monitor.connect()
        """
        raise NotImplementedError(
            "MEXC order status via REST is not reliable. "
            "Use MEXCOrderMonitor separately for real-time tracking."
        )
