"""Test script to understand Aster WebSocket API for order monitoring

This script tests:
1. Creating a listenKey via REST API
2. Connecting to WebSocket with listenKey
3. Receiving and logging ORDER_TRADE_UPDATE messages
"""

import asyncio
import json
import math
import time
import requests
from typing import Dict, Any
from eth_abi import encode
from eth_account import Account
from eth_account.messages import encode_defunct
from web3 import Web3
import websockets

# Import config
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import TRADING_CONFIG


class AsterWebSocketTest:
    """Test class for Aster WebSocket order monitoring"""

    BASE_URL = "https://fapi.asterdex.com"
    WS_BASE_URL = "wss://fstream.asterdex.com/ws"

    def __init__(self, config: Dict[str, Any]):
        self.wallet_address = config['wallet_address']
        self.signer_address = config['signer_address']
        self.private_key = config['private_key']
        self.listen_key = None

    def _sign_request(self, params: Dict[str, Any], user: str, signer: str, private_key: str, nonce: int) -> Dict[str, Any]:
        """Sign request with EVM-style signature"""
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

    def _signed_request(self, method: str, endpoint: str, payload: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make a signed request to Aster API"""
        if payload is None:
            payload = {}

        # Generate nonce
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
        elif method == 'PUT':
            response = requests.put(url, params=signed_params)
        elif method == 'DELETE':
            response = requests.delete(url, params=signed_params)
        else:
            raise ValueError(f"Unsupported method: {method}")

        response.raise_for_status()
        return response.json()

    def create_listen_key(self) -> str:
        """Create a listenKey for WebSocket user data stream"""
        print("Creating listenKey...")
        try:
            data = self._signed_request('POST', '/fapi/v3/listenKey', {})
            listen_key = data.get('listenKey')
            print(f"✓ ListenKey created: {listen_key}")
            return listen_key
        except Exception as e:
            print(f"✗ Failed to create listenKey: {e}")
            raise

    def keepalive_listen_key(self, listen_key: str) -> bool:
        """Keep the listenKey alive"""
        print("Sending keepalive for listenKey...")
        try:
            self._signed_request('PUT', '/fapi/v3/listenKey', {})
            print("✓ Keepalive successful")
            return True
        except Exception as e:
            print(f"✗ Keepalive failed: {e}")
            return False

    def close_listen_key(self, listen_key: str) -> bool:
        """Close the listenKey"""
        print("Closing listenKey...")
        try:
            self._signed_request('DELETE', '/fapi/v3/listenKey', {})
            print("✓ ListenKey closed")
            return True
        except Exception as e:
            print(f"✗ Failed to close listenKey: {e}")
            return False

    async def listen_to_orders(self, listen_key: str, duration: int = 300):
        """Connect to WebSocket and listen for order updates

        Args:
            listen_key: The listenKey from create_listen_key()
            duration: How long to listen in seconds (default: 5 minutes)
        """
        ws_url = f"{self.WS_BASE_URL}/{listen_key}"
        print(f"\nConnecting to WebSocket: {ws_url}")

        try:
            async with websockets.connect(ws_url) as ws:
                print("✓ WebSocket connected!")
                print("\nListening for order updates...")
                print("=" * 80)
                print("NOTE: You need to place orders manually to see updates here!")
                print("=" * 80)

                # Set a timeout
                end_time = time.time() + duration

                while time.time() < end_time:
                    try:
                        # Wait for message with timeout
                        message = await asyncio.wait_for(ws.recv(), timeout=10)
                        data = json.loads(message)

                        # Print all messages
                        print(f"\n[{time.strftime('%H:%M:%S')}] WebSocket message received:")
                        print(json.dumps(data, indent=2))

                        # Highlight order updates
                        if data.get("e") == "ORDER_TRADE_UPDATE":
                            print("\n" + "!" * 80)
                            print("ORDER UPDATE DETECTED!")
                            print("!" * 80)
                            order = data.get("o", {})
                            print(f"Symbol: {order.get('s')}")
                            print(f"Order ID: {order.get('i')}")
                            print(f"Side: {order.get('S')}")
                            print(f"Status: {order.get('X')}")
                            print(f"Quantity: {order.get('q')}")
                            print(f"Filled: {order.get('z')}")
                            print(f"Price: {order.get('p')}")
                            print(f"Avg Price: {order.get('ap')}")
                            print("!" * 80)

                    except asyncio.TimeoutError:
                        # No message received, continue listening
                        continue
                    except json.JSONDecodeError as e:
                        print(f"✗ Failed to parse JSON: {e}")
                        print(f"Raw message: {message}")

                print(f"\n✓ Listening completed after {duration} seconds")

        except Exception as e:
            print(f"\n✗ WebSocket error: {e}")
            raise


async def main():
    """Main test function"""
    print("=" * 80)
    print("Aster WebSocket Order Monitor Test")
    print("=" * 80)

    # Load config
    config = TRADING_CONFIG.get('aster')
    if not config:
        print("✗ Aster config not found in config.py")
        return

    # Create tester
    tester = AsterWebSocketTest(config)

    # Step 1: Create listenKey
    try:
        listen_key = tester.create_listen_key()
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        return

    # Step 2: Test keepalive (optional)
    # tester.keepalive_listen_key(listen_key)

    # Step 3: Listen to WebSocket
    try:
        await tester.listen_to_orders(listen_key, duration=300)  # Listen for 5 minutes
    except KeyboardInterrupt:
        print("\n\n✓ Test interrupted by user")
    except Exception as e:
        print(f"\n✗ WebSocket test failed: {e}")
    finally:
        # Step 4: Clean up
        tester.close_listen_key(listen_key)

    print("\n" + "=" * 80)
    print("Test completed!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
