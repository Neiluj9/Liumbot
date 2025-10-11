# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Crypto funding rate arbitrage system that collects funding rates from multiple cryptocurrency exchanges (Hyperliquid, MEXC, Aster) and identifies arbitrage opportunities based on rate differences.

## Running the Application

```bash
# Install dependencies
pip install -r requirements.txt

# Update symbols data (run first to populate symbols_data.json)
python scripts/update_symbols.py

# Run the funding rate analyzer
python scripts/funding_analyzer.py

# Run real-time spread monitor
python scripts/spread_monitor.py --symbol BTC --exchange-a hyperliquid --exchange-b mexc

# Generate spread charts
python scripts/spread_plotter.py

# Execute trades (manual mode with fixed price)
python scripts/trade_cli.py open --exchange1 hyperliquid --side1 long --exchange2 mexc --side2 short --symbol BTC --size 100 --price 50000

# Execute trades (dynamic pricing mode - tracks exchange2 orderbook)
python scripts/trade_cli.py open --exchange1 hyperliquid --side1 short --exchange2 mexc --side2 long --symbol BTC --size 0.1 --dynamic-mode --price-offset-pct -0.5 --price-tolerance-pct 0.3

# Close trades
python scripts/trade_cli.py close --exchange1 hyperliquid --exchange2 mexc --symbol BTC

# Monitor orders (examples)
python scripts/mexc_order_monitor_example.py
python scripts/aster_order_monitor_example.py
python scripts/test_aster_websocket_orders.py
```

## Architecture

### Project Structure

```
liumbot2/
├── config.py                  # Central configuration (API keys, exchanges, trading config)
├── models.py                  # Core dataclasses
├── analyzer.py                # Arbitrage analysis logic
├── symbols_data.json          # Symbol mappings and exchange metadata (generated)
├── collectors/
│   ├── rest/                  # REST API collectors
│   │   ├── base.py            # Abstract base collector
│   │   ├── hyperliquid.py     # Hyperliquid REST API
│   │   ├── mexc.py            # MEXC REST API
│   │   └── aster.py           # Aster REST API
│   └── websocket/             # WebSocket collectors
│       ├── base.py            # Base WebSocket class
│       ├── hyperliquid_ws.py  # Hyperliquid orderbook/trades
│       ├── mexc_spot_ws.py    # MEXC spot orderbook
│       ├── mexc_futures_ws.py # MEXC futures orderbook
│       └── aster_ws.py        # Aster orderbook/trades
├── executors/                 # Trading execution
│   ├── base.py                # Abstract base executor
│   ├── hyperliquid.py         # Hyperliquid trading
│   ├── mexc.py                # MEXC trading
│   ├── aster.py               # Aster trading
│   ├── mexc_order_monitor.py  # MEXC order status monitoring
│   └── aster_order_monitor.py # Aster order status monitoring
├── scripts/                   # CLI scripts
│   ├── funding_analyzer.py    # Main funding rate analysis
│   ├── spread_monitor.py      # Real-time price spread monitoring
│   ├── spread_plotter.py      # Generate spread charts
│   ├── trade_cli.py           # Execute synchronized trades
│   ├── update_symbols.py      # Update symbols data
│   ├── mexc_order_monitor_example.py
│   ├── aster_order_monitor_example.py
│   └── test_aster_websocket_orders.py
├── utils/                     # Shared utilities
│   ├── time_utils.py          # Time/date utilities
│   └── price_tracker.py       # Dynamic price tracking for synchronized trading
├── exports/                   # Analysis outputs
│   ├── funding_rates/         # Historical funding rates JSON
│   ├── arbitrage_opportunities/ # Detected opportunities JSON
│   └── spreads/               # Price spread data
│       ├── csv/               # CSV exports
│       └── png/               # Chart visualizations
└── docs/                      # Documentation
    ├── api-reference.md
    ├── order-monitoring.md
    └── dynamic-pricing.md
```

### Core Components

**Data Flow**: `scripts/` → `collectors/` → `analyzer.py` → Output (JSON files + console)

- **models.py**: Core dataclasses
  - `FundingRate`: Normalized funding rate data from any exchange
  - `ArbitrageOpportunity`: Represents a profitable arbitrage between two exchanges

- **collectors/rest/**: REST API data collectors
  - `base.py`: Abstract `BaseCollector` class with `get_funding_rates()` and `get_funding_history()` methods
  - `hyperliquid.py`: Hyperliquid API (funding every hour)
  - `mexc.py`: MEXC API (funding every 8h: 00:00, 08:00, 16:00 UTC)
  - `aster.py`: Aster API (funding every 8h for most symbols, some 4h or 1h)

- **collectors/websocket/**: WebSocket collectors for real-time data
  - `base.py`: Base WebSocket class
  - Exchange-specific WebSocket implementations for orderbook streaming

- **analyzer.py**: `FundingRateAnalyzer` class
  - Groups funding rates by symbol
  - Finds spread between lowest and highest rates
  - Generates `ArbitrageOpportunity` objects

- **executors/**: Trading execution modules
  - `base.py`: Abstract `BaseExecutor` class with order placement and management
  - `hyperliquid.py`: Hyperliquid trading implementation (EIP-712 signing)
  - `mexc.py`: MEXC Futures trading (cookie-based auth)
  - `aster.py`: Aster trading (EIP-712 with signer delegation)
  - `mexc_order_monitor.py`: Real-time MEXC order status monitoring via WebSocket
  - `aster_order_monitor.py`: Real-time Aster order status monitoring via WebSocket

- **scripts/**: Executable CLI scripts
  - `funding_analyzer.py`: Main funding rate analysis
  - `spread_monitor.py`: Real-time price spread monitoring with WebSocket orderbooks
  - `spread_plotter.py`: Generate spread charts from CSV data
  - `trade_cli.py`: Execute synchronized trades across exchanges (open/close positions)
  - `update_symbols.py`: Update symbols_data.json with exchange metadata
  - Order monitoring examples for testing WebSocket order status tracking

- **config.py**: Central configuration file
  - API endpoints for each exchange
  - `EXCHANGES` dict: enable/disable exchanges and set funding intervals
  - `TRADING_CONFIG`: API keys, private keys, and authentication credentials
  - Dynamic symbol loading from `symbols_data.json`
  - Functions: `get_symbols()`, `get_funding_interval()`, `get_fees()`

- **symbols_data.json**: Generated file containing:
  - List of 225+ normalized symbols tracked across all exchanges
  - Exchange-specific metadata (funding intervals, fees, symbol mappings)
  - Updated by running `python scripts/update_symbols.py`

### Symbol Normalization

All exchanges use different symbol formats (e.g., "BTC-PERP", "BTCUSDT", "BTC"). The `normalize_symbol()` method in `BaseCollector` strips suffixes like "USDT", "USD", "-PERP" to create a unified symbol format across exchanges.

### Adding New Exchanges

1. **REST Collector**: Create `collectors/rest/your_exchange.py` inheriting from `BaseCollector`
   - Implement `get_funding_rates()` and `get_funding_history()` methods
   - Implement `normalize_symbol()` for the exchange's symbol format

2. **WebSocket Collector** (optional): Create `collectors/websocket/your_exchange_ws.py`
   - Inherit from `BaseWebSocket`
   - Implement orderbook streaming for real-time price monitoring

3. **Executor**: Create `executors/your_exchange.py` inheriting from `BaseExecutor`
   - Implement `place_order()`, `cancel_order()`, `get_order_status()`, etc.
   - Handle exchange-specific authentication (API keys, signing, etc.)

4. **Configuration**: Update `config.py`
   - Add exchange to `EXCHANGES` dict with funding interval
   - Add credentials to `TRADING_CONFIG`

5. **Integration**: Import and instantiate in relevant scripts
   - `funding_analyzer.py` for funding rate collection
   - `spread_monitor.py` for price monitoring
   - `trade_cli.py` for trading execution

## API Endpoints Reference

### REST APIs
- **Hyperliquid**:
  - Main API: `https://api.hyperliquid.xyz/info`
  - Funding rates: POST `{"type": "predictedFundings"}`
  - Trading: POST `{"type": "order", "action": {...}}`

- **MEXC**:
  - Base: `https://contract.mexc.com/api/v1/contract`
  - Funding rates: `/funding_rate` and `/funding_rate/detail`
  - Trading: Cookie-based authentication via browser session

- **Aster**:
  - Base: `https://fapi.asterdex.com`
  - Funding rates: `/fapi/v1/premiumIndex`
  - Trading: `/fapi/v1/order` with EIP-712 signing

### WebSocket APIs
- **Hyperliquid**: `wss://api.hyperliquid.xyz/ws`
- **MEXC Spot**: `wss://wbs.mexc.com/ws`
- **MEXC Futures**: `wss://contract.mexc.com/ws`
- **Aster**: `wss://fapi.asterdex.com/stream/ws`

## Key Features

### Funding Rate Arbitrage
- Collects funding rates from 3 exchanges (Hyperliquid, MEXC, Aster)
- Analyzes 225+ symbols across all exchanges
- Identifies arbitrage opportunities based on funding rate spreads
- Exports data to JSON files in `exports/` directory

### Price Spread Monitoring
- Real-time WebSocket orderbook streaming
- Calculates bid/ask spreads and mid-market prices
- Monitors execution costs and slippage
- Exports to CSV and generates PNG charts

### Trading Execution
- Synchronized order placement across exchanges
- Support for opening and closing positions
- **Dynamic pricing mode**: Automatically adjusts limit prices based on real-time orderbook from exchange 2
- Real-time order status monitoring via WebSocket
- Multiple authentication methods (EIP-712, API keys, cookies)

### Symbol Management
- Dynamic symbol loading from `symbols_data.json`
- Automatic symbol normalization across exchanges
- Per-symbol funding intervals and fee tracking
- Easy updates via `update_symbols.py` script

## Authentication Methods

### Hyperliquid
- EIP-712 signature using private key
- Standard Ethereum wallet integration

### MEXC
- Cookie-based authentication (extracted from browser)
- Optional: API key/secret for WebSocket order monitoring

### Aster
- EIP-712 signature with signer delegation
- Wallet address + authorized signer address + signer private key
- "Pro mode" with separate signing key for enhanced security

## Documentation

For detailed information, see:
- **[API Reference](docs/api-reference.md)** - Complete API documentation
- **[Order Monitoring](docs/order-monitoring.md)** - WebSocket order tracking guide
- **[Dynamic Pricing](docs/dynamic-pricing.md)** - Automatic price adjustment based on exchange 2 orderbook
- **[Main README](README.md)** - Project overview and quick start

## Important Notes

- **Security**: Never commit `config.py` with real credentials to git
- **Rate Limits**: Be mindful of exchange API rate limits
- **Testing**: Use small position sizes when testing trading functionality
- **Symbols**: Run `update_symbols.py` periodically to refresh symbol data
- **Funding Times**: Different exchanges have different funding schedules:
  - Hyperliquid: Every hour
  - MEXC: Every 8 hours (00:00, 08:00, 16:00 UTC)
  - Aster: Varies by symbol (1h, 4h, or 8h)
