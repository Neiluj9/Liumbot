"""Base executor class for exchange trading operations."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import Enum


class OrderType(Enum):
    """Order type enumeration."""
    LIMIT = "limit"
    MARKET = "market"


class OrderSide(Enum):
    """Order side enumeration."""
    LONG = "long"
    SHORT = "short"
    CLOSE_LONG = "close_long"
    CLOSE_SHORT = "close_short"


class OrderStatus(Enum):
    """Order status enumeration."""
    PENDING = "pending"
    PARTIAL = "partial"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass
class OrderResult:
    """Result of an order placement."""
    order_id: str
    exchange: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    size: float
    price: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: float = 0.0
    average_price: Optional[float] = None
    raw_response: Optional[Dict[str, Any]] = None


class BaseExecutor(ABC):
    """Abstract base class for exchange executors."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize executor with configuration.

        Args:
            config: Exchange-specific configuration (API keys, cookies, etc.)
        """
        self.config = config

    @abstractmethod
    def place_order(
        self,
        symbol: str,
        side: OrderSide,
        size: float,
        order_type: OrderType = OrderType.LIMIT,
        price: Optional[float] = None
    ) -> OrderResult:
        """Place an order on the exchange.

        Args:
            symbol: Trading symbol (normalized format, e.g., 'BTC')
            side: Order side (LONG, SHORT, CLOSE_LONG, CLOSE_SHORT)
            size: Order size in USDT
            order_type: LIMIT or MARKET
            price: Limit price (required for LIMIT orders)

        Returns:
            OrderResult with order details
        """
        pass

    @abstractmethod
    def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancel an order.

        Args:
            order_id: Order ID to cancel
            symbol: Trading symbol

        Returns:
            True if cancelled successfully, False otherwise
        """
        pass

    @abstractmethod
    def get_order_status(self, order_id: str, symbol: str) -> OrderResult:
        """Get order status and details.

        Args:
            order_id: Order ID to query
            symbol: Trading symbol

        Returns:
            OrderResult with current order status
        """
        pass

    @abstractmethod
    def get_exchange_symbol(self, normalized_symbol: str) -> str:
        """Convert normalized symbol to exchange-specific format.

        Args:
            normalized_symbol: Normalized symbol (e.g., 'BTC')

        Returns:
            Exchange-specific symbol format
        """
        pass
