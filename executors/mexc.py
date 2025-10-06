"""MEXC exchange executor using session cookie authentication."""

import requests
from typing import Dict, Any, Optional
from .base import BaseExecutor, OrderResult, OrderType, OrderSide, OrderStatus


class MEXCExecutor(BaseExecutor):
    """MEXC exchange executor with cookie-based authentication."""

    BASE_URL = "https://contract.mexc.com/api/v1/private"

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
            config: Must contain 'session_cookie' key
        """
        super().__init__(config)
        self.session_cookie = config.get('session_cookie')
        if not self.session_cookie:
            raise ValueError("MEXC executor requires 'session_cookie' in config")

        self.session = requests.Session()
        self.session.headers.update({
            'Cookie': self.session_cookie,
            'Content-Type': 'application/json',
        })

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

    def place_order(
        self,
        symbol: str,
        side: OrderSide,
        size: float,
        order_type: OrderType = OrderType.LIMIT,
        price: Optional[float] = None
    ) -> OrderResult:
        """Place order on MEXC.

        Args:
            symbol: Normalized symbol (e.g., 'BTC')
            side: Order side
            size: Order size in USDT
            order_type: LIMIT or MARKET
            price: Limit price (required for LIMIT orders)

        Returns:
            OrderResult
        """
        exchange_symbol = self.get_exchange_symbol(symbol)
        mexc_side = self._get_mexc_side(side)

        if order_type == OrderType.LIMIT and price is None:
            raise ValueError("Price is required for LIMIT orders")

        # MEXC API payload
        payload = {
            "symbol": exchange_symbol,
            "side": mexc_side,
            "vol": size,
            "type": 1 if order_type == OrderType.LIMIT else 2,  # 1=limit, 2=market
        }

        if order_type == OrderType.LIMIT:
            payload["price"] = price

        try:
            response = self.session.post(
                f"{self.BASE_URL}/order/submit",
                json=payload
            )
            response.raise_for_status()
            data = response.json()

            # Parse MEXC response
            if data.get('success'):
                order_id = str(data.get('data'))
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
                raise Exception(f"MEXC order failed: {data.get('message', 'Unknown error')}")

        except Exception as e:
            raise Exception(f"Failed to place MEXC order: {str(e)}")

    def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancel order on MEXC.

        Args:
            order_id: Order ID
            symbol: Normalized symbol

        Returns:
            True if cancelled successfully
        """
        exchange_symbol = self.get_exchange_symbol(symbol)

        try:
            response = self.session.post(
                f"{self.BASE_URL}/order/cancel",
                json={
                    "symbol": exchange_symbol,
                    "order_id": order_id
                }
            )
            response.raise_for_status()
            data = response.json()

            return data.get('success', False)

        except Exception as e:
            print(f"Failed to cancel MEXC order: {str(e)}")
            return False

    def get_order_status(self, order_id: str, symbol: str) -> OrderResult:
        """Get order status from MEXC.

        Args:
            order_id: Order ID
            symbol: Normalized symbol

        Returns:
            OrderResult with current status
        """
        exchange_symbol = self.get_exchange_symbol(symbol)

        try:
            response = self.session.get(
                f"{self.BASE_URL}/order/get",
                params={
                    "symbol": exchange_symbol,
                    "order_id": order_id
                }
            )
            response.raise_for_status()
            data = response.json()

            if not data.get('success'):
                raise Exception(f"Failed to get order status: {data.get('message')}")

            order_data = data.get('data', {})

            # Parse MEXC status
            # status: 1=pending, 2=partial, 3=filled, 4=cancelled
            mexc_status = order_data.get('status')
            status_map = {
                1: OrderStatus.PENDING,
                2: OrderStatus.PARTIAL,
                3: OrderStatus.FILLED,
                4: OrderStatus.CANCELLED,
            }
            status = status_map.get(mexc_status, OrderStatus.PENDING)

            # Reverse side mapping
            reverse_side_map = {v: k for k, v in self.SIDE_MAPPING.items()}
            side = reverse_side_map.get(order_data.get('side'), OrderSide.LONG)

            return OrderResult(
                order_id=order_id,
                exchange='mexc',
                symbol=symbol,
                side=side,
                order_type=OrderType.LIMIT if order_data.get('type') == 1 else OrderType.MARKET,
                size=order_data.get('vol', 0.0),
                price=order_data.get('price'),
                status=status,
                filled_quantity=order_data.get('deal_vol', 0.0),
                average_price=order_data.get('avg_price'),
                raw_response=data
            )

        except Exception as e:
            raise Exception(f"Failed to get MEXC order status: {str(e)}")
