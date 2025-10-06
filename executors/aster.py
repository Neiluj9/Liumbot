"""Aster exchange executor."""

import requests
import json
import math
import time
from typing import Dict, Any, Optional
from eth_abi import encode
from eth_account import Account
from eth_account.messages import encode_defunct
from web3 import Web3
from .base import BaseExecutor, OrderResult, OrderType, OrderSide, OrderStatus


class AsterExecutor(BaseExecutor):
    """Aster exchange executor with ERC20 wallet authentication (Pro mode)."""

    BASE_URL = "https://fapi.asterdex.com"

    def __init__(self, config: Dict[str, Any]):
        """Initialize Aster executor.

        Args:
            config: Must contain 'wallet_address', 'signer_address', and 'private_key'
        """
        super().__init__(config)
        self.wallet_address = config.get('wallet_address')
        self.signer_address = config.get('signer_address')
        self.private_key = config.get('private_key')

        if not all([self.wallet_address, self.signer_address, self.private_key]):
            raise ValueError("Aster executor requires 'wallet_address', 'signer_address', and 'private_key' in config")

    def get_exchange_symbol(self, normalized_symbol: str) -> str:
        """Convert normalized symbol to Aster format.

        Args:
            normalized_symbol: e.g., 'BTC'

        Returns:
            Aster format: e.g., 'BTCUSDT'
        """
        return f"{normalized_symbol}USDT"

    def _sign_request(self, params: Dict[str, Any], user: str, signer: str, private_key: str, nonce: int) -> Dict[str, Any]:
        """Sign request with EVM-style signature for Aster API.

        Args:
            params: Request parameters
            user: Wallet address
            signer: Signer address
            private_key: Private key for signing
            nonce: Nonce (timestamp in microseconds)

        Returns:
            Signed parameters dict
        """
        # Remove None values
        params = {key: value for key, value in params.items() if value is not None}

        # Add required fields
        params["recvWindow"] = 50000
        params["timestamp"] = int(round(time.time() * 1000))

        # Convert all params to strings
        for key in params:
            params[key] = str(params[key])

        # Create JSON string (sorted, no spaces)
        json_str = json.dumps(params, sort_keys=True).replace(" ", "")

        # Encode with ABI
        encoded = encode(
            ["string", "address", "address", "uint256"],
            [json_str, user, signer, nonce]
        )

        # Keccak hash
        keccak_hex = Web3.keccak(encoded).hex()

        # Sign the message
        signable_msg = encode_defunct(hexstr=keccak_hex)
        signed_message = Account.sign_message(signable_message=signable_msg, private_key=private_key)

        # Add signature fields to params
        params["nonce"] = nonce
        params["user"] = user
        params["signer"] = signer
        params["signature"] = "0x" + signed_message.signature.hex()

        return params

    def _signed_request(self, method: str, endpoint: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make a signed request to Aster API.

        Args:
            method: HTTP method (GET, POST, DELETE)
            endpoint: API endpoint
            payload: Request payload

        Returns:
            Response JSON
        """
        if payload is None:
            payload = {}

        # Generate nonce (timestamp in microseconds)
        nonce = math.trunc(time.time() * 1000000)

        # Sign the request
        signed_params = self._sign_request(
            payload,
            self.wallet_address,
            self.signer_address,
            self.private_key,
            nonce
        )

        url = f"{self.BASE_URL}{endpoint}"

        if method == 'GET':
            response = requests.get(url, params=signed_params)
        elif method == 'POST':
            response = requests.post(url, params=signed_params)
        elif method == 'DELETE':
            response = requests.delete(url, params=signed_params)
        else:
            raise ValueError(f"Unsupported method: {method}")

        response.raise_for_status()
        return response.json()

    def place_order(
        self,
        symbol: str,
        side: OrderSide,
        size: float,
        order_type: OrderType = OrderType.LIMIT,
        price: Optional[float] = None
    ) -> OrderResult:
        """Place order on Aster.

        Args:
            symbol: Normalized symbol (e.g., 'BTC')
            side: Order side
            size: Order size in contracts
            order_type: LIMIT or MARKET
            price: Limit price (required for LIMIT orders)

        Returns:
            OrderResult
        """
        exchange_symbol = self.get_exchange_symbol(symbol)

        if order_type == OrderType.LIMIT and price is None:
            raise ValueError("Price is required for LIMIT orders")

        # Determine side (BUY/SELL) and reduce_only
        if side == OrderSide.LONG:
            aster_side = "BUY"
            reduce_only = False
        elif side == OrderSide.SHORT:
            aster_side = "SELL"
            reduce_only = False
        elif side == OrderSide.CLOSE_LONG:
            aster_side = "SELL"
            reduce_only = True
        else:  # CLOSE_SHORT
            aster_side = "BUY"
            reduce_only = True

        payload = {
            'symbol': exchange_symbol,
            'side': aster_side,
            'type': 'LIMIT' if order_type == OrderType.LIMIT else 'MARKET',
            'quantity': size,
        }

        if order_type == OrderType.LIMIT:
            payload['price'] = price
            payload['timeInForce'] = 'GTC'

        if reduce_only:
            payload['reduceOnly'] = True

        try:
            data = self._signed_request('POST', '/fapi/v3/order', payload)

            # Parse Aster response
            order_id = str(data.get('orderId'))
            status = OrderStatus.PENDING

            if data.get('status') == 'FILLED':
                status = OrderStatus.FILLED
            elif data.get('status') == 'PARTIALLY_FILLED':
                status = OrderStatus.PARTIAL

            return OrderResult(
                order_id=order_id,
                exchange='aster',
                symbol=symbol,
                side=side,
                order_type=order_type,
                size=size,
                price=price,
                status=status,
                filled_quantity=float(data.get('executedQty', 0)),
                average_price=float(data.get('avgPrice', 0)) if data.get('avgPrice') else None,
                raw_response=data
            )

        except Exception as e:
            raise Exception(f"Failed to place Aster order: {str(e)}")

    def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancel order on Aster.

        Args:
            order_id: Order ID
            symbol: Normalized symbol

        Returns:
            True if cancelled successfully
        """
        exchange_symbol = self.get_exchange_symbol(symbol)

        payload = {
            'symbol': exchange_symbol,
            'orderId': order_id
        }

        try:
            self._signed_request('DELETE', '/fapi/v3/order', payload)
            return True

        except Exception as e:
            print(f"Failed to cancel Aster order: {str(e)}")
            return False

    def get_order_status(self, order_id: str, symbol: str) -> OrderResult:
        """Get order status from Aster.

        Args:
            order_id: Order ID
            symbol: Normalized symbol

        Returns:
            OrderResult with current status
        """
        exchange_symbol = self.get_exchange_symbol(symbol)

        payload = {
            'symbol': exchange_symbol,
            'orderId': order_id
        }

        try:
            data = self._signed_request('GET', '/fapi/v3/order', payload)

            # Parse status
            aster_status = data.get('status')
            status_map = {
                'NEW': OrderStatus.PENDING,
                'PARTIALLY_FILLED': OrderStatus.PARTIAL,
                'FILLED': OrderStatus.FILLED,
                'CANCELED': OrderStatus.CANCELLED,
                'REJECTED': OrderStatus.REJECTED,
            }
            status = status_map.get(aster_status, OrderStatus.PENDING)

            # Determine side
            aster_side = data.get('side')
            reduce_only = data.get('reduceOnly', False)

            if aster_side == 'BUY' and not reduce_only:
                side = OrderSide.LONG
            elif aster_side == 'SELL' and not reduce_only:
                side = OrderSide.SHORT
            elif aster_side == 'SELL' and reduce_only:
                side = OrderSide.CLOSE_LONG
            else:
                side = OrderSide.CLOSE_SHORT

            return OrderResult(
                order_id=order_id,
                exchange='aster',
                symbol=symbol,
                side=side,
                order_type=OrderType.LIMIT if data.get('type') == 'LIMIT' else OrderType.MARKET,
                size=float(data.get('origQty', 0)),
                price=float(data.get('price', 0)) if data.get('price') else None,
                status=status,
                filled_quantity=float(data.get('executedQty', 0)),
                average_price=float(data.get('avgPrice', 0)) if data.get('avgPrice') else None,
                raw_response=data
            )

        except Exception as e:
            raise Exception(f"Failed to get Aster order status: {str(e)}")
