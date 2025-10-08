"""MEXC exchange executor using session cookie authentication."""

import time
import hashlib
import hmac
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

    def _generate_api_signature(self, timestamp: str, params: str = "") -> str:
        """Generate HMAC SHA256 signature for MEXC API authentication.

        Args:
            timestamp: Request timestamp in milliseconds
            params: Query parameters string (for GET) or empty (for GET without params)

        Returns:
            Hex-encoded HMAC SHA256 signature
        """
        # Signature string: api_key + timestamp + params
        sign_str = self.api_key + timestamp + params
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            sign_str.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature

    def _get_api_headers(self, params: str = "") -> dict:
        """Get headers with API key authentication for MEXC official API.

        Args:
            params: Query parameters string (sorted alphabetically for GET)

        Returns:
            Headers dict with API authentication
        """
        timestamp = str(int(time.time() * 1000))
        signature = self._generate_api_signature(timestamp, params)
        return {
            "Content-Type": "application/json",
            "ApiKey": self.api_key,
            "Request-Time": timestamp,
            "Signature": signature,
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
        """Get order status from MEXC using official API.

        Args:
            order_id: Order ID (e.g., '730992108428455552')
            symbol: Normalized symbol (e.g., 'BTC')

        Returns:
            OrderResult with current status

        Raises:
            ValueError: If API credentials are not configured
            Exception: If API request fails

        MEXC Order States:
            1: Uninformed
            2: Uncompleted (partially filled)
            3: Completed (fully filled)
            4: Cancelled
            5: Invalid
        """
        if not self.api_key or not self.api_secret:
            raise ValueError(
                "API key and secret are required for get_order_status. "
                "Provide 'api_key' and 'api_secret' in config."
            )

        # Official MEXC API endpoint
        url = f"https://contract.mexc.com/api/v1/private/order/get/{order_id}"

        # GET request with no query params, so params string is empty
        headers = self._get_api_headers(params="")

        response = requests.get(
            url,
            headers=headers,
            timeout=30,
            impersonate="chrome110"
        )

        if response.status_code != 200:
            raise Exception(f"HTTP {response.status_code}: {response.text}")

        data = response.json()

        if not data.get('success'):
            error_msg = data.get('msg') or data.get('message', 'Unknown error')
            raise Exception(f"MEXC API error (code {data.get('code')}): {error_msg}")

        # Parse order data
        order_data = data.get('data', {})

        # Map MEXC state to OrderStatus
        state = order_data.get('state')
        status_map = {
            1: OrderStatus.PENDING,      # Uninformed
            2: OrderStatus.PARTIAL,      # Uncompleted
            3: OrderStatus.FILLED,       # Completed
            4: OrderStatus.CANCELLED,    # Cancelled
            5: OrderStatus.REJECTED,     # Invalid
        }
        status = status_map.get(state, OrderStatus.PENDING)

        # Reverse map MEXC side to OrderSide
        mexc_side = order_data.get('side')
        side_reverse_map = {v: k for k, v in self.SIDE_MAPPING.items()}
        side = side_reverse_map.get(mexc_side, OrderSide.LONG)

        # Map order type
        order_type_code = order_data.get('type')
        order_type = OrderType.LIMIT if order_type_code == 1 else OrderType.MARKET

        return OrderResult(
            order_id=str(order_data.get('orderId')),
            exchange='mexc',
            symbol=symbol,
            side=side,
            order_type=order_type,
            size=float(order_data.get('vol', 0)),
            price=float(order_data.get('price', 0)) if order_data.get('price') else None,
            filled_quantity=float(order_data.get('dealVol', 0)),
            average_price=float(order_data.get('dealAvgPrice', 0)) if order_data.get('dealAvgPrice') else None,
            status=status,
            raw_response=data
        )
