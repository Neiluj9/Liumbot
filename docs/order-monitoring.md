# Order Monitoring

Guide for monitoring orders in real-time across exchanges.

## Overview

Order monitors use WebSocket connections to receive real-time updates about order status changes. This is more efficient and reliable than polling REST APIs.

## Architecture

All order monitors follow the same pattern:
1. **Separate module** - Independent from executors for flexibility
2. **Callback-based** - Register a callback function to handle updates
3. **WebSocket streaming** - Real-time updates without polling
4. **Automatic reconnection** - Handles keepalive and reconnection

## Supported Exchanges

### ✅ MEXC - WebSocket

**Module:** `executors/mexc_order_monitor.py`
**Requirements:** API key + API secret
**Protocol:** WebSocket with HMAC authentication

```python
from executors.mexc_order_monitor import MEXCOrderMonitor
from executors.base import OrderResult
from config import TRADING_CONFIG

def on_order(order: OrderResult):
    print(f"Order {order.order_id}: {order.status.name}")

monitor = MEXCOrderMonitor(
    api_key=TRADING_CONFIG['mexc']['api_key'],
    api_secret=TRADING_CONFIG['mexc']['api_secret']
)
monitor.set_callback(on_order)
await monitor.connect()
```

**Notes:**
- Requires API credentials (different from cookie_key used for trading)
- Get credentials from: MEXC > Account > API Management
- WebSocket endpoint: `wss://contract.mexc.com/edge`
- Authentication: HMAC-SHA256 signature

---

### ✅ Aster - WebSocket

**Module:** `executors/aster_order_monitor.py`
**Requirements:** Wallet address + Signer address + Private key
**Protocol:** WebSocket with listenKey

```python
from executors.aster_order_monitor import AsterOrderMonitor
from executors.base import OrderResult
from config import TRADING_CONFIG

def on_order(order: OrderResult):
    print(f"Order {order.order_id}: {order.status.name}")

monitor = AsterOrderMonitor(
    wallet_address=TRADING_CONFIG['aster']['wallet_address'],
    signer_address=TRADING_CONFIG['aster']['signer_address'],
    private_key=TRADING_CONFIG['aster']['private_key']
)
monitor.set_callback(on_order)
await monitor.connect()
```

**How it works:**
1. Create listenKey via REST: `POST /fapi/v3/listenKey` (signed with EVM signature)
2. Connect to WebSocket: `wss://fstream.asterdex.com/ws/{listenKey}`
3. Receive ORDER_TRADE_UPDATE events automatically
4. Keepalive listenKey every 30-60 minutes (done automatically)

**Notes:**
- ListenKey expires after 60 minutes without keepalive
- WebSocket connection expires after 24 hours
- Uses same EVM signature as trading endpoints

---

### ⚠️ Hyperliquid - Polling Only

**Module:** `executors/hyperliquid.py`
**Method:** `get_order_status(order_id, symbol)`
**Protocol:** REST API polling

```python
from executors.hyperliquid import HyperliquidExecutor
from config import TRADING_CONFIG

executor = HyperliquidExecutor(TRADING_CONFIG['hyperliquid'])

# Poll for status
order_result = executor.get_order_status(order_id="123456", symbol="BTC")
print(f"Status: {order_result.status.name}")
```

**Notes:**
- No WebSocket user data stream available (as of now)
- Must poll `get_order_status()` periodically
- Less efficient than WebSocket monitoring

---

## Example Scripts

- **MEXC:** `scripts/mexc_order_monitor_example.py`
- **Aster:** `scripts/aster_order_monitor_example.py`
- **Aster Test:** `scripts/test_aster_websocket_orders.py` (diagnostic tool)

Run examples:
```bash
# MEXC
python scripts/mexc_order_monitor_example.py

# Aster
python scripts/aster_order_monitor_example.py

# Aster diagnostic (connects for 5 minutes, logs all messages)
python scripts/test_aster_websocket_orders.py
```

## OrderResult Format

All monitors return standardized `OrderResult` objects:

```python
@dataclass
class OrderResult:
    order_id: str              # Exchange order ID
    exchange: str              # 'mexc', 'aster', 'hyperliquid'
    symbol: str                # Normalized symbol (e.g., 'BTC')
    side: OrderSide            # LONG, SHORT, CLOSE_LONG, CLOSE_SHORT
    order_type: OrderType      # LIMIT, MARKET
    size: float                # Order size
    price: Optional[float]     # Limit price (None for market orders)
    status: OrderStatus        # PENDING, PARTIAL, FILLED, CANCELLED, REJECTED
    filled_quantity: float     # Amount filled
    average_price: Optional[float]  # Average fill price
    raw_response: Dict         # Raw exchange response
```

## Event Types

### MEXC WebSocket Events

```json
{
  "channel": "push.personal.order",
  "data": {
    "orderId": 123456,
    "symbol": "BTC_USDT",
    "state": 3,        // 2=PENDING, 1=PARTIAL, 3=FILLED, 4=CANCELLED, 5=REJECTED
    "side": 1,         // 1=LONG, 2=CLOSE_SHORT, 3=SHORT, 4=CLOSE_LONG
    "vol": "1.0",
    "dealVol": "1.0",
    "dealAvgPrice": "50000"
  }
}
```

### Aster WebSocket Events

```json
{
  "e": "ORDER_TRADE_UPDATE",
  "E": 1568879465651,
  "o": {
    "i": 8886774,      // Order ID
    "s": "BTCUSDT",
    "S": "BUY",        // BUY/SELL
    "X": "FILLED",     // NEW, PARTIALLY_FILLED, FILLED, CANCELED, REJECTED
    "R": false,        // Reduce only
    "q": "1.0",        // Original quantity
    "z": "1.0",        // Filled quantity
    "p": "50000",      // Price
    "ap": "50000"      // Average price
  }
}
```

## Callback Pattern

All monitors use the same callback pattern:

```python
def on_order_update(order: OrderResult):
    # Handle order update
    if order.status == OrderStatus.FILLED:
        print(f"✅ Order {order.order_id} filled at {order.average_price}")
    elif order.status == OrderStatus.PARTIAL:
        print(f"⏳ Order {order.order_id} partially filled: {order.filled_quantity}/{order.size}")
    elif order.status == OrderStatus.CANCELLED:
        print(f"❌ Order {order.order_id} cancelled")
    elif order.status == OrderStatus.REJECTED:
        print(f"🚫 Order {order.order_id} rejected")

monitor.set_callback(on_order_update)
await monitor.connect()
```

## Troubleshooting

### No messages received
**Normal behavior** - Order monitors only send updates when there's order activity. Place a test order to verify the connection works.

### MEXC: Authentication failed
- Verify `api_key` and `api_secret` in `config.py`
- These are different from `cookie_key` used for trading
- Get credentials from MEXC website > Account > API Management

### Aster: 401 Unauthorized
- Verify wallet credentials in `config.py`
- Ensure `signer_address` has trading permissions
- Test with: `python scripts/test_aster_websocket_orders.py`

### Connection drops
- **MEXC:** Sends ping every 30 seconds automatically
- **Aster:** Keepalive listenKey every 30 minutes automatically
- Both WebSockets expire after 24 hours - implement reconnection logic

## Integration with trade_cli.py

The `trade_cli.py` script automatically uses WebSocket monitoring for Aster and MEXC, and falls back to REST polling for Hyperliquid.

**Automatic detection:**
```bash
# Aster → WebSocket (real-time)
python scripts/trade_cli.py open --exchange1 aster --side1 long \
  --exchange2 mexc --side2 short --symbol BTC --size 100 --price 50000

# Hyperliquid → Polling (fallback)
python scripts/trade_cli.py open --exchange1 hyperliquid --side1 long \
  --exchange2 mexc --side2 short --symbol BTC --size 100 --price 50000
```

No configuration needed - the script detects the exchange and chooses the best monitoring method.

## Best Practices

1. **Error handling:** Always wrap monitor in try/except
2. **Reconnection:** Implement exponential backoff for reconnects
3. **Logging:** Log all order updates for audit trail
4. **Testing:** Use test scripts before production
5. **Credentials:** Never commit real credentials to git

## Future Improvements

- [ ] Add automatic reconnection with exponential backoff
- [ ] Implement Hyperliquid WebSocket if/when available
- [ ] Add position monitoring (separate from orders)
- [ ] Add balance monitoring
- [ ] Create unified monitor interface for all exchanges
