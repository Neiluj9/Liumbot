"""Dynamic price tracking for synchronized trading across exchanges."""

import asyncio
from typing import Optional, Callable
from dataclasses import dataclass
from datetime import datetime
from executors.base import OrderSide


@dataclass
class PriceUpdate:
    """Price update from exchange orderbook."""
    symbol: str
    bid: float
    ask: float
    timestamp: datetime

    def get_reference_price(self, side: OrderSide) -> float:
        """Get reference price based on trade side.

        Args:
            side: Order side on exchange 1

        Returns:
            BID if SHORT on exchange 1, ASK if LONG on exchange 1
        """
        if side in [OrderSide.SHORT, OrderSide.CLOSE_LONG]:
            return self.bid
        else:  # LONG or CLOSE_SHORT
            return self.ask


class DynamicPriceTracker:
    """Tracks exchange 2 price and manages dynamic pricing for exchange 1 orders."""

    def __init__(
        self,
        exchange1_side: OrderSide,
        price_offset_pct: float,
        price_tolerance_pct: float,
        on_price_update: Optional[Callable[[float, float], None]] = None
    ):
        """Initialize price tracker.

        Args:
            exchange1_side: Order side on exchange 1 (determines which price to use)
            price_offset_pct: Percentage offset from exchange 2 reference price
            price_tolerance_pct: Variation threshold to trigger order renewal (%)
            on_price_update: Callback(new_price, old_price) when price should be updated
        """
        self.exchange1_side = exchange1_side
        self.price_offset_pct = price_offset_pct
        self.price_tolerance_pct = price_tolerance_pct
        self.on_price_update = on_price_update

        self.current_reference_price: Optional[float] = None
        self.current_target_price: Optional[float] = None
        self.last_order_price: Optional[float] = None

        self.price_updates_count = 0
        self.orders_renewed_count = 0

    def calculate_target_price(self, reference_price: float) -> float:
        """Calculate target price for exchange 1 order.

        Args:
            reference_price: Reference price from exchange 2 (bid or ask)

        Returns:
            Target price with offset applied
        """
        return reference_price * (1 + self.price_offset_pct / 100)

    def should_renew_order(self, new_reference_price: float) -> bool:
        """Check if order should be renewed based on price movement.

        Args:
            new_reference_price: New reference price from exchange 2

        Returns:
            True if price has moved beyond tolerance threshold
        """
        if self.last_order_price is None:
            return False

        new_target_price = self.calculate_target_price(new_reference_price)
        price_change_pct = abs((new_target_price - self.last_order_price) / self.last_order_price * 100)

        return price_change_pct >= self.price_tolerance_pct

    def process_price_update(self, price_update: PriceUpdate) -> Optional[float]:
        """Process new price update from exchange 2.

        Args:
            price_update: Price update from orderbook

        Returns:
            New target price if order should be renewed, None otherwise
        """
        self.price_updates_count += 1

        # Get reference price based on exchange 1 side
        reference_price = price_update.get_reference_price(self.exchange1_side)
        self.current_reference_price = reference_price

        # Calculate new target price
        new_target_price = self.calculate_target_price(reference_price)
        self.current_target_price = new_target_price

        # First update - always return price for initial order
        if self.last_order_price is None:
            self.last_order_price = new_target_price
            if self.on_price_update:
                self.on_price_update(new_target_price, None)
            return new_target_price

        # Check if price has moved beyond tolerance
        if self.should_renew_order(reference_price):
            old_price = self.last_order_price
            self.last_order_price = new_target_price
            self.orders_renewed_count += 1

            if self.on_price_update:
                self.on_price_update(new_target_price, old_price)

            return new_target_price

        return None

    def get_stats(self) -> dict:
        """Get tracking statistics.

        Returns:
            Dictionary with tracking stats
        """
        return {
            'price_updates_count': self.price_updates_count,
            'orders_renewed_count': self.orders_renewed_count,
            'current_reference_price': self.current_reference_price,
            'current_target_price': self.current_target_price,
            'last_order_price': self.last_order_price,
        }
