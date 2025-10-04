"""Base collector class for exchange data"""

from abc import ABC, abstractmethod
from typing import List
from models import FundingRate


class BaseCollector(ABC):
    """Abstract base class for exchange collectors"""

    def __init__(self, exchange_name: str):
        self.exchange_name = exchange_name

    @abstractmethod
    async def get_funding_rates(self, symbols: List[str]) -> List[FundingRate]:
        """Get current funding rates for given symbols"""
        pass

    @abstractmethod
    async def get_funding_history(self, symbol: str, start_time: int, end_time: int = None) -> List[FundingRate]:
        """Get historical funding rates for a symbol"""
        pass

    def normalize_symbol(self, symbol: str) -> str:
        """Normalize symbol name across exchanges"""
        # Remove common suffixes and standardize
        symbol = symbol.upper().replace("USDT", "").replace("USD", "").replace("-PERP", "")
        return symbol
