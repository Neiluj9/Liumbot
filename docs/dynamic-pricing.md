# Dynamic Pricing Mode

## Overview

The dynamic pricing mode allows you to place limit orders on exchange 1 with a price that automatically adjusts based on real-time orderbook data from exchange 2. This is useful for arbitrage strategies where you want to maintain a specific price relationship between two exchanges.

## How It Works

### Price Reference Selection

The system intelligently selects which price to use from exchange 2's orderbook based on your trading direction on exchange 1:

- **SHORT on exchange 1** → Uses **BID** price from exchange 2
- **LONG on exchange 1** → Uses **ASK** price from exchange 2

This ensures that the reference price reflects the actual execution price you would get on exchange 2.

### Price Calculation

The target price for your limit order on exchange 1 is calculated as:

```
target_price = reference_price × (1 + price_offset_pct / 100)
```

**Examples:**
- Reference price: $50,000, offset: +0.5% → Target: $50,250
- Reference price: $50,000, offset: -0.5% → Target: $49,750

### Order Renewal

The system continuously monitors the orderbook of exchange 2 via WebSocket. When the reference price moves beyond your specified tolerance threshold, the system:

1. Cancels the current limit order on exchange 1
2. Checks for any partial fills and hedges them immediately on exchange 2
3. Places a new limit order at the updated price
4. Adjusts the order size for any previously filled quantities

**Example:**
- Tolerance: 0.3%
- Current order price: $50,000
- New reference price moves to $50,200 (0.4% change)
- System automatically cancels and replaces the order at new calculated price

## Usage

### Basic Syntax

```bash
python scripts/trade_cli.py open \
  --exchange1 <EXCHANGE> --side1 <SIDE> \
  --exchange2 <EXCHANGE> --side2 <SIDE> \
  --symbol <SYMBOL> --size <SIZE> \
  --dynamic-mode \
  --price-offset-pct <PERCENTAGE> \
  --price-tolerance-pct <PERCENTAGE>
```

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `--dynamic-mode` | flag | No | False | Enables dynamic pricing mode |
| `--price-offset-pct` | float | No | 0.0 | Price offset from exchange 2 reference (%) |
| `--price-tolerance-pct` | float | No | 0.3 | Variation threshold to trigger order renewal (%) |

### Example 1: Short on Hyperliquid, Long on MEXC

```bash
python scripts/trade_cli.py open \
  --exchange1 hyperliquid --side1 short \
  --exchange2 mexc --side2 long \
  --symbol BTC --size 0.1 \
  --dynamic-mode \
  --price-offset-pct -0.5 \
  --price-tolerance-pct 0.3
```

**What happens:**
1. System connects to MEXC orderbook via WebSocket
2. Reads the **BID** price from MEXC (since we're shorting on Hyperliquid)
3. Calculates limit price: `MEXC_BID × 0.995` (0.5% below)
4. Places limit sell order on Hyperliquid
5. If MEXC bid moves ±0.3%, cancels and replaces order at new price
6. When filled (partially or fully), immediately hedges on MEXC with market buy

### Example 2: Long on Aster, Short on Hyperliquid

```bash
python scripts/trade_cli.py open \
  --exchange1 aster --side1 long \
  --exchange2 hyperliquid --side2 short \
  --symbol ETH --size 1.0 \
  --dynamic-mode \
  --price-offset-pct 0.5 \
  --price-tolerance-pct 0.2
```

**What happens:**
1. System connects to Hyperliquid orderbook via WebSocket
2. Reads the **ASK** price from Hyperliquid (since we're going long on Aster)
3. Calculates limit price: `Hyperliquid_ASK × 1.005` (0.5% above)
4. Places limit buy order on Aster
5. If Hyperliquid ask moves ±0.2%, cancels and replaces order at new price
6. When filled, immediately hedges on Hyperliquid with market sell

## Features

### Real-Time Monitoring

- WebSocket connections to exchange 2 for sub-millisecond orderbook updates
- Automatic reconnection with exponential backoff
- Graceful handling of connection issues

### Partial Fill Handling

The system automatically handles partial fills:
- Tracks cumulative filled quantity
- Only places hedge orders for new fills
- Adjusts remaining order size when renewing
- Prevents double-hedging

### Order Monitoring

For exchange 1, the system uses:
- **WebSocket monitoring** for Aster and MEXC (real-time updates)
- **REST polling** for Hyperliquid (configurable interval)

### Safety Features

- Automatic order cancellation on interrupt (Ctrl+C)
- Partial fill detection before cancellation
- Immediate hedging of any partial fills
- Detailed logging of all actions

## Output

The system provides detailed real-time information:

```
Opening position...
Exchange 1: hyperliquid (short)
Exchange 2: mexc (long)
Symbol: BTC, Size: 0.1
Dynamic pricing mode enabled
  Price offset: -0.50%
  Price tolerance: ±0.30%

[1/3] Placing initial LIMIT order on hyperliquid @ 49750.00...
✓ Order placed: ID=0x123abc...

[2/3] Monitoring mexc orderbook...
Using REST polling for hyperliquid

Price moved: 49750.00 → 49800.00 (+0.10%)
Cancelling order 0x123abc...
Placing new LIMIT order @ 49800.00 (size: 0.1000)...
✓ Order placed: ID=0x456def...

✓ Partial fill: 0.05 (Total: 0.05/0.1)
Placing MARKET order on mexc for 0.05...
✓ Market order placed: ID=987654

✓ Full fill: 0.05 (Total: 0.10/0.1)
✓ All orders filled!
✓ Position opened successfully

Trading Statistics:
  Total filled: 0.1000/0.1
  Price updates: 523
  Orders renewed: 2
  Final order price: 49800.00
```

## Best Practices

### Choosing Offset Percentage

- **Arbitrage**: Set offset to capture funding rate difference minus fees
- **Market making**: Use small offsets (0.1% - 0.5%)
- **Directional**: Larger offsets (0.5% - 2.0%) for desired entry points

### Choosing Tolerance Percentage

- **High volatility**: Use larger tolerance (0.5% - 1.0%) to reduce order churn
- **Low volatility**: Smaller tolerance (0.1% - 0.3%) for tighter tracking
- **Consider**: Exchange fees and rate limits when choosing tolerance

### Exchange Selection

Works with any combination of supported exchanges:
- Hyperliquid (REST polling for order monitoring)
- MEXC (WebSocket order monitoring)
- Aster (WebSocket order monitoring)

## Limitations

- Requires WebSocket support on exchange 2 for orderbook streaming
- Currently supports: Hyperliquid, MEXC, Aster
- Minimum order sizes and tick sizes vary by exchange
- Rate limits apply for order placement and cancellation

## Troubleshooting

### "WebSocket not supported for exchange"

The exchange does not have a WebSocket collector implemented. Add one following the pattern in `collectors/websocket/`.

### Orders being renewed too frequently

Increase `--price-tolerance-pct` to reduce sensitivity to price movements.

### Orders not being renewed

Check that:
1. WebSocket connection to exchange 2 is active
2. `--price-tolerance-pct` is not too high
3. Price is actually moving on exchange 2

### Partial fills not being hedged

Check that:
1. Order monitoring is working (WebSocket or REST polling)
2. Exchange 2 has sufficient liquidity
3. No API errors in the logs

## Implementation Details

### Architecture

```
trade_cli.py (open_position_dynamic)
    │
    ├─> DynamicPriceTracker (utils/price_tracker.py)
    │   ├─ Tracks reference price changes
    │   ├─ Calculates target prices
    │   └─ Triggers order renewal
    │
    ├─> WebSocketCollector (exchange 2)
    │   ├─ Streams orderbook updates
    │   └─ Provides bid/ask prices
    │
    ├─> OrderMonitor (exchange 1, optional)
    │   ├─ WebSocket for Aster/MEXC
    │   └─ REST polling for Hyperliquid
    │
    └─> Executors (both exchanges)
        ├─ Place orders
        ├─ Cancel orders
        └─ Query order status
```

### Key Classes

- **`DynamicPriceTracker`**: Core logic for price tracking and renewal decisions
- **`WebSocketCollector`**: Base class for orderbook streaming
- **`PriceUpdate`**: Data container for bid/ask prices
- **`OrderResult`**: Order execution results

### Threading Model

All operations use Python's `asyncio` for concurrent execution:
- Multiple WebSocket connections run in parallel
- Order monitoring and orderbook tracking happen simultaneously
- Blocking operations (REST calls) are minimized

## See Also

- [API Reference](api-reference.md) - Complete API documentation
- [Order Monitoring](order-monitoring.md) - WebSocket order tracking
- [Main README](../README.md) - Project overview
