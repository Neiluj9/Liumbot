# API Reference

Documentation des APIs internes et endpoints externes.

## 📡 Exchange APIs

### Hyperliquid

**Base URL**: `https://api.hyperliquid.xyz/info`

#### Get Funding Rates
```python
POST /info
{
  "type": "predictedFundings"
}
```

#### Get Funding History
```python
POST /info
{
  "type": "fundingHistory",
  "coin": "BTC",
  "startTime": 1633046400000
}
```

**Funding Interval**: 1 hour

---

### MEXC

**Base URL**: `https://contract.mexc.com/api/v1/contract`

#### Get Current Funding Rate
```python
GET /funding_rate/{symbol}
```

#### Get Funding History
```python
GET /funding_rate/history?symbol={symbol}&page_num=1&page_size=100
```

**Funding Times**: 00:00, 08:00, 16:00 UTC (every 8 hours)

---

### Aster

**Base URL**: `https://fapi.asterdex.com`

#### Get Current Funding Rate
```python
GET /fapi/v1/premiumIndex
```

Returns `lastFundingRate` for all symbols.

#### Get Funding History
```python
GET /fapi/v1/fundingRate?symbol={symbol}&startTime={timestamp}
```

**Funding Interval**: 8 hours for most symbols, some 4h or 1h

---

## 🐍 Python API

### Collectors

#### BaseCollector

Base class for REST API collectors.

```python
from collectors.rest import BaseCollector

class YourCollector(BaseCollector):
    def __init__(self):
        super().__init__("your_exchange")

    async def get_funding_rates(self, symbols: List[str]) -> List[FundingRate]:
        """Fetch current funding rates for symbols"""
        pass

    async def get_funding_history(self, symbol: str, start_time: datetime,
                                   end_time: datetime) -> List[FundingRate]:
        """Fetch historical funding rates"""
        pass
```

#### WebSocketCollector

Base class for WebSocket collectors.

```python
from collectors.websocket.base import WebSocketCollector, OrderbookData

class YourWebSocket(WebSocketCollector):
    async def connect(self, symbol: str):
        """Connect to WebSocket and subscribe to orderbook"""
        pass

    async def disconnect(self):
        """Disconnect from WebSocket"""
        pass

    def set_callback(self, callback):
        """Set callback for orderbook updates"""
        self.callback = callback
```

---

### Models

#### FundingRate

```python
@dataclass
class FundingRate:
    symbol: str                      # Normalized symbol (e.g., "BTC")
    exchange: str                    # Exchange name
    funding_rate: float             # Funding rate as decimal (0.0001 = 0.01%)
    timestamp: datetime             # When the rate was collected
    next_funding_time: Optional[datetime]  # Next funding time
    funding_interval_hours: int     # Funding interval in hours
    maker_fee: Optional[float]      # Maker fee as decimal
    taker_fee: Optional[float]      # Taker fee as decimal
```

#### ArbitrageOpportunity

```python
@dataclass
class ArbitrageOpportunity:
    symbol: str                     # Trading symbol
    long_exchange: str              # Exchange to long on
    short_exchange: str             # Exchange to short on
    long_rate: float               # Long position funding rate
    short_rate: float              # Short position funding rate
    rate_difference: float         # Hourly profit per unit
    annual_return: float           # Annualized return percentage
    long_interval: int             # Long funding interval (hours)
    short_interval: int            # Short funding interval (hours)
    # ... fees and next funding times
```

---

### Analyzer

#### FundingRateAnalyzer

```python
from analyzer import FundingRateAnalyzer

analyzer = FundingRateAnalyzer(min_rate_difference=0.0001)

# Find arbitrage opportunities
opportunities = analyzer.find_arbitrage_opportunities(funding_rates)

# Filter by specific exchanges
opportunities = [opp for opp in opportunities
                 if opp.long_exchange == "hyperliquid"]
```

---

### Configuration

#### Exchange Configuration

```python
from config import EXCHANGES, get_funding_interval, get_fees

# Check if exchange is enabled
if EXCHANGES["hyperliquid"]["enabled"]:
    # Get funding interval for specific symbol
    interval = get_funding_interval("hyperliquid", "BTC")

    # Get maker/taker fees
    maker_fee, taker_fee = get_fees("mexc", "ETH")
```

#### Trading Configuration

```python
from config import TRADING_CONFIG

# Access exchange credentials
hyperliquid_key = TRADING_CONFIG["hyperliquid"]["private_key"]
```

⚠️ **Never commit real credentials to git!**

---

### Executors

#### BaseExecutor

```python
from executors import HyperliquidExecutor
from executors.base import OrderSide, OrderType

executor = HyperliquidExecutor(TRADING_CONFIG["hyperliquid"])

# Place order
order = executor.place_order(
    symbol="BTC",
    side=OrderSide.LONG,
    size=100.0,  # USDT
    order_type=OrderType.LIMIT,
    price=50000.0
)

# Check order status
status = executor.get_order_status(order.order_id, "BTC")

# Cancel order
executor.cancel_order(order.order_id, "BTC")
```

---

## 🔧 Utilities

### Time Utils

```python
from utils import format_time_until_funding, get_countdown_color

# Format time remaining
formatted = format_time_until_funding(next_funding_time)
# Returns: "2h 15m", "45m", or "30s"

# Get color for countdown (uses colorama)
color = get_countdown_color(next_funding_time)
# Returns: Fore.RED (<1h), Fore.YELLOW (<4h), or Fore.GREEN (>4h)
```

---

## 📝 Data Files

### symbols_data.json

Generated by `scripts/update_symbols.py`. Contains:

```json
{
  "last_updated": "2025-10-07T14:00:00Z",
  "symbols": ["BTC", "ETH", "SOL", ...],
  "exchange_data": {
    "hyperliquid": {
      "funding_interval": 1,
      "maker_fee": 0.0002,
      "taker_fee": 0.0005
    },
    "mexc": {
      "funding_interval": 8,
      "symbols": {
        "BTC": {"maker_fee": 0.0002, "taker_fee": 0.0005}
      }
    }
  }
}
```

---

## 🚀 Examples

See [examples.md](examples.md) for practical usage examples.

---

[← Back to Documentation](README.md)
