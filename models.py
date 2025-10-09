"""Data models for funding rate arbitrage"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class SymbolMetadata:
    """Market metadata for a trading symbol"""
    symbol: str
    exchange: str
    tick_size: float  # Minimum price increment (e.g., 0.01)
    price_precision: int  # Number of decimal places for price
    quantity_precision: int = 8  # Number of decimal places for quantity (default 8)

    def format_price(self, price: float) -> str:
        """Format price according to exchange precision"""
        return f"{price:.{self.price_precision}f}"

    def format_quantity(self, quantity: float) -> str:
        """Format quantity according to exchange precision"""
        return f"{quantity:.{self.quantity_precision}f}"


@dataclass
class FundingRate:
    """Normalized funding rate data structure"""
    exchange: str
    symbol: str
    funding_rate: float  # Rate for the funding interval (as provided by exchange)
    timestamp: datetime
    funding_interval_hours: int = 8  # How often funding is paid (default 8h)
    next_funding_time: Optional[datetime] = None
    premium: Optional[float] = None
    maker_fee: Optional[float] = None  # Maker fee rate (e.g., 0.0002 = 0.02%)
    taker_fee: Optional[float] = None  # Taker fee rate (e.g., 0.0006 = 0.06%)
    volume_24h: Optional[float] = None  # 24-hour trading volume in USD

    def __post_init__(self):
        """Validate data after initialization"""
        if not isinstance(self.funding_rate, (int, float)):
            raise ValueError(f"funding_rate must be numeric, got {type(self.funding_rate)}")
        if not isinstance(self.timestamp, datetime):
            raise ValueError(f"timestamp must be datetime, got {type(self.timestamp)}")

    @property
    def hourly_rate(self) -> float:
        """Convert funding rate to hourly equivalent for comparison"""
        return self.funding_rate / self.funding_interval_hours

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "exchange": self.exchange,
            "symbol": self.symbol,
            "funding_rate": self.funding_rate,
            "timestamp": self.timestamp.isoformat(),
            "next_funding_time": self.next_funding_time.isoformat() if self.next_funding_time else None,
            "premium": self.premium,
            "volume_24h": self.volume_24h
        }


@dataclass
class ArbitrageOpportunity:
    """Arbitrage opportunity between exchanges"""
    symbol: str
    long_exchange: str
    long_rate: float  # Hourly rate
    long_rate_interval: float  # Rate for the funding interval
    short_exchange: str
    short_rate: float  # Hourly rate
    short_rate_interval: float  # Rate for the funding interval
    rate_difference: float  # Hourly rate difference
    timestamp: datetime
    long_interval: int = 8  # Funding interval hours for long position
    short_interval: int = 8  # Funding interval hours for short position
    long_maker_fee: Optional[float] = None  # Maker fee for long exchange
    long_taker_fee: Optional[float] = None  # Taker fee for long exchange
    short_maker_fee: Optional[float] = None  # Maker fee for short exchange
    short_taker_fee: Optional[float] = None  # Taker fee for short exchange
    long_next_funding_time: Optional[datetime] = None  # Next funding time for long position
    short_next_funding_time: Optional[datetime] = None  # Next funding time for short position
    long_volume_24h: Optional[float] = None  # 24h volume in USD for long exchange
    short_volume_24h: Optional[float] = None  # 24h volume in USD for short exchange

    @property
    def daily_return(self) -> float:
        """Calculate daily return (24h)"""
        return self.rate_difference * 24

    @property
    def annual_return(self) -> float:
        """Calculate annualized return estimate"""
        return self.daily_return * 365

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "symbol": self.symbol,
            "long_exchange": self.long_exchange,
            "long_rate_hourly": self.long_rate,
            "long_rate_interval": self.long_rate_interval,
            "long_funding_interval_hours": self.long_interval,
            "long_maker_fee": self.long_maker_fee,
            "long_taker_fee": self.long_taker_fee,
            "long_volume_24h": self.long_volume_24h,
            "short_exchange": self.short_exchange,
            "short_rate_hourly": self.short_rate,
            "short_rate_interval": self.short_rate_interval,
            "short_funding_interval_hours": self.short_interval,
            "short_maker_fee": self.short_maker_fee,
            "short_taker_fee": self.short_taker_fee,
            "short_volume_24h": self.short_volume_24h,
            "rate_difference": self.rate_difference,
            "annual_return_estimate": f"{self.annual_return:.2%}",
            "timestamp": self.timestamp.isoformat()
        }
