# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Crypto funding rate arbitrage system that collects funding rates from multiple cryptocurrency exchanges (Hyperliquid, MEXC, Aster) and identifies arbitrage opportunities based on rate differences.

## Running the Application

```bash
# Run the main analyzer
python main.py

# Install dependencies
pip install -r requirements.txt
```

The main script will:
1. Collect current funding rates from all enabled exchanges
2. Analyze and identify arbitrage opportunities
3. Export results to `arbitrage_opportunities.json` and `current_funding_rates.json`

## Architecture

### Core Components

**Data Flow**: `main.py` → `collectors/` → `analyzer.py` → Output (JSON files + console)

- **models.py**: Two core dataclasses
  - `FundingRate`: Normalized funding rate data from any exchange
  - `ArbitrageOpportunity`: Represents a profitable arbitrage between two exchanges

- **collectors/**: Exchange-specific data collectors
  - `base.py`: Abstract `BaseCollector` class with `get_funding_rates()` and `get_funding_history()` methods
  - `hyperliquid.py`: Hyperliquid API (funding every hour)
  - `mexc.py`: MEXC API (funding every 8h: 00:00, 08:00, 16:00 UTC)
  - `aster.py`: Aster API (funding every 8h for most symbols, some 4h or 1h)

- **analyzer.py**: `FundingRateAnalyzer` class
  - Groups funding rates by symbol
  - Finds spread between lowest and highest rates
  - Generates `ArbitrageOpportunity` objects

- **config.py**: Configuration including:
  - API endpoints for each exchange
  - `EXCHANGES` dict: enable/disable exchanges and set funding intervals
  - `SYMBOLS`: List of 225+ normalized symbols to track

### Symbol Normalization

All exchanges use different symbol formats (e.g., "BTC-PERP", "BTCUSDT", "BTC"). The `normalize_symbol()` method in `BaseCollector` strips suffixes like "USDT", "USD", "-PERP" to create a unified symbol format across exchanges.

### Adding New Exchanges

1. Create new collector in `collectors/your_exchange.py` that inherits from `BaseCollector`
2. Implement `get_funding_rates()` and `get_funding_history()` methods
3. Add exchange config to `EXCHANGES` dict in `config.py`
4. Import and instantiate in `main.py`

## API Endpoints Reference

- **Hyperliquid**: `https://api.hyperliquid.xyz/info` - POST with `{"type": "predictedFundings"}`
- **MEXC**: `https://contract.mexc.com/api/v1/contract/funding_rate` and `/detail`
- **Aster**: `https://fapi.asterdex.com/fapi/v1/premiumIndex`
