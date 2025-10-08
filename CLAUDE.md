# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Crypto funding rate arbitrage system that collects funding rates from multiple cryptocurrency exchanges (Hyperliquid, MEXC, Aster) and identifies arbitrage opportunities based on rate differences.

## Running the Application

```bash
# Run the funding rate analyzer
python scripts/funding_analyzer.py

# Run real-time spread monitor
python scripts/spread_monitor.py --symbol BTC --exchange-a hyperliquid --exchange-b mexc

# Update symbols data
python scripts/update_symbols.py

# Execute trades
python scripts/trade_cli.py open --exchange1 hyperliquid --side1 long --exchange2 mexc --side2 short --symbol BTC --size 100 --price 50000

# Install dependencies
pip install -r requirements.txt
```

## Architecture

### Project Structure

```
liumbot2/
├── config.py              # Central configuration
├── models.py              # Core dataclasses
├── analyzer.py            # Arbitrage analysis logic
├── collectors/
│   ├── rest/              # REST API collectors
│   │   ├── base.py
│   │   ├── hyperliquid.py
│   │   ├── mexc.py
│   │   └── aster.py
│   └── websocket/         # WebSocket collectors
│       ├── base.py
│       ├── hyperliquid_ws.py
│       ├── mexc_spot_ws.py
│       ├── mexc_futures_ws.py
│       └── aster_ws.py
├── executors/             # Trading execution
│   ├── base.py
│   ├── hyperliquid.py
│   ├── mexc.py
│   └── aster.py
├── scripts/               # CLI scripts
│   ├── funding_analyzer.py
│   ├── spread_monitor.py
│   ├── spread_plotter.py
│   ├── trade_cli.py
│   └── update_symbols.py
└── utils/                 # Shared utilities
    └── time_utils.py
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

- **scripts/**: Executable CLI scripts
  - `funding_analyzer.py`: Main funding rate analysis
  - `spread_monitor.py`: Real-time price spread monitoring
  - `spread_plotter.py`: Generate charts from spread data
  - `trade_cli.py`: Execute synchronized trades
  - `update_symbols.py`: Update symbols data

- **config.py**: Configuration including:
  - API endpoints for each exchange
  - `EXCHANGES` dict: enable/disable exchanges and set funding intervals
  - `SYMBOLS`: List of 225+ normalized symbols to track

### Symbol Normalization

All exchanges use different symbol formats (e.g., "BTC-PERP", "BTCUSDT", "BTC"). The `normalize_symbol()` method in `BaseCollector` strips suffixes like "USDT", "USD", "-PERP" to create a unified symbol format across exchanges.

### Adding New Exchanges

1. Create new REST collector in `collectors/rest/your_exchange.py` that inherits from `BaseCollector`
2. Implement `get_funding_rates()` and `get_funding_history()` methods
3. (Optional) Create WebSocket collector in `collectors/websocket/your_exchange_ws.py`
4. Add exchange config to `EXCHANGES` dict in `config.py`
5. Import and instantiate in relevant scripts

## API Endpoints Reference

- **Hyperliquid**: `https://api.hyperliquid.xyz/info` - POST with `{"type": "predictedFundings"}`
- **MEXC**: `https://contract.mexc.com/api/v1/contract/funding_rate` and `/detail`
- **Aster**: `https://fapi.asterdex.com/fapi/v1/premiumIndex`

## Documentation

For detailed information, see:
- **[Installation Guide](docs/installation.md)** - Complete installation instructions
- **[Usage Examples](docs/examples.md)** - Practical examples and use cases
- **[Spread Monitor Guide](docs/spread-monitor.md)** - Real-time monitoring documentation
- **[Main README](README.md)** - Project overview and quick start
