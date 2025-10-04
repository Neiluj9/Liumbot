"""Data models for funding rate arbitrage"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


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

    @property
    def daily_rate(self) -> float:
        """Convert funding rate to daily equivalent"""
        return self.hourly_rate * 24

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "exchange": self.exchange,
            "symbol": self.symbol,
            "funding_rate": self.funding_rate,
            "timestamp": self.timestamp.isoformat(),
            "next_funding_time": self.next_funding_time.isoformat() if self.next_funding_time else None,
            "premium": self.premium
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
            "short_exchange": self.short_exchange,
            "short_rate_hourly": self.short_rate,
            "short_rate_interval": self.short_rate_interval,
            "short_funding_interval_hours": self.short_interval,
            "short_maker_fee": self.short_maker_fee,
            "short_taker_fee": self.short_taker_fee,
            "rate_difference": self.rate_difference,
            "annual_return_estimate": f"{self.annual_return:.2%}",
            "timestamp": self.timestamp.isoformat()
        }
