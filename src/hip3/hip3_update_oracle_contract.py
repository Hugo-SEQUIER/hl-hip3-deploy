#!/usr/bin/env python3
"""
hip3_update_oracle_contract.py

Contract-based oracle updater for HIP-3 perp oracle prices using HyperEVM testnet.

Exports:
    update_oracle_for_dex(dex: str, strict: bool = False, debug: bool = False) -> dict

Behavior:
- Reads prices from HyperEVM testnet contract instead of RedStone API
- Only pushes prices for assets that are ALREADY deployed (read from meta.universe)
- Optional strict mode fails if some configured assets aren't deployed yet
- Includes retry handling for the common "missing perp" propagation issue

"""

from __future__ import annotations

import json
import time
from datetime import datetime
from typing import Dict, List, Any

from web3 import Web3
from eth_utils import keccak
from hyperliquid.info import Info

# Your local helper that returns (address, info, exchange)
import src.hl_utils.example_utils as example_utils

from src.hip3.hip3_config import API_URL, DEX_SPECS, EVM_ADDR
from src.compute.stable_fx import resolve_stable_usd_factor


# ----------------------- Contract Configuration ----------------------- #

# HyperEVM testnet configuration
CONTRACT_ADDRESS = "0x492f4913E411691807c53b178c1E36F4144E9889"
RPC_URL = "https://evmrpc-jp.hyperpc.app/adae36120cb94b9984f348314cdca711"
CHAIN_ID = 998

# Contract ABI for the functions we need
CONTRACT_ABI = [
    {
        "inputs": [{"internalType": "bytes32", "name": "dataFeedId", "type": "bytes32"}],
        "name": "getValueForDataFeed",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "bytes32", "name": "dataFeedId", "type": "bytes32"}],
        "name": "getTimestampForDataFeed",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "admin",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    }
]

# Symbol mapping for contract data feeds - focused on BTC-FEUSD only
SYMBOL_TO_CONTRACT_FEED = {
    "BTC-FEUSD": "BTC-FEUSD",
}


# ----------------------- Contract Helpers ----------------------- #

def get_data_feed_id(symbol: str) -> bytes:
    """Generate data feed ID for a symbol (keccak256 hash)"""
    return keccak(text=symbol)


def read_contract_price(symbol: str, debug: bool = False) -> Dict[str, Any]:
    """
    Read price data from the HyperEVM testnet contract
    
    Args:
        symbol: Trading pair symbol (e.g., "BTC-FEUSD")
        debug: Enable debug output
        
    Returns:
        dict: {
            'symbol': str,
            'price': float,
            'raw_price': int,
            'timestamp': int,
            'last_update': datetime,
            'age_seconds': int,
            'age_minutes': int,
            'contract': str,
            'network': str,
            'data_feed_id': str
        }
    """
    try:
        # Map symbol to contract feed name if needed
        contract_symbol = SYMBOL_TO_CONTRACT_FEED.get(symbol, symbol)
        
        if debug:
            print(f"🔗 Connecting to HyperEVM testnet for {symbol} -> {contract_symbol}...")
        
        # Connect to HyperEVM testnet
        w3 = Web3(Web3.HTTPProvider(RPC_URL))
        
        if not w3.is_connected():
            raise Exception("Failed to connect to HyperEVM testnet")
        
        if debug:
            print(f"✅ Connected to chain ID: {w3.eth.chain_id}")
        
        # Load contract
        contract = w3.eth.contract(
            address=Web3.to_checksum_address(CONTRACT_ADDRESS),
            abi=CONTRACT_ABI
        )
        
        # Generate data feed ID
        data_feed_id = get_data_feed_id(contract_symbol)
        if debug:
            print(f"📋 Data Feed ID for {contract_symbol}: {data_feed_id.hex()}")
        
        # Read price and timestamp
        if debug:
            print(f"📊 Reading price data from contract...")
        
        raw_price = contract.functions.getValueForDataFeed(data_feed_id).call()
        timestamp = contract.functions.getTimestampForDataFeed(data_feed_id).call()
        
        # Convert raw price (scaled by 10^8) to decimal
        price_decimal = raw_price / 1e8
        
        # Calculate age
        last_update = datetime.fromtimestamp(timestamp)
        current_time = datetime.now()
        age_seconds = int((current_time - last_update).total_seconds())
        age_minutes = age_seconds // 60
        
        result = {
            'symbol': symbol,
            'price': price_decimal,
            'raw_price': raw_price,
            'timestamp': timestamp,
            'last_update': last_update,
            'age_seconds': age_seconds,
            'age_minutes': age_minutes,
            'contract': CONTRACT_ADDRESS,
            'network': f'HyperEVM Testnet (Chain ID: {CHAIN_ID})',
            'data_feed_id': data_feed_id.hex()
        }
        
        if debug:
            print(f"💰 {symbol}: {price_decimal:,.6f} (age: {age_minutes}min)")
        
        return result
        
    except Exception as e:
        if debug:
            print(f"❌ Error reading contract price for {symbol}: {e}")
        raise Exception(f"Failed to read price for {symbol} from contract: {e}")


def check_contract_admin(debug: bool = False) -> str:
    """Check who is the admin of the contract"""
    try:
        w3 = Web3(Web3.HTTPProvider(RPC_URL))
        contract = w3.eth.contract(
            address=Web3.to_checksum_address(CONTRACT_ADDRESS),
            abi=CONTRACT_ABI
        )
        admin = contract.functions.admin().call()
        if debug:
            print(f"👤 Contract Admin: {admin}")
        return admin
    except Exception as e:
        if debug:
            print(f"❌ Error reading admin: {e}")
        return None


# ----------------------- Internal Helpers ----------------------- #

def _build_price_map_for_dex(dex: str, coin_to_price: Dict[str, float]) -> Dict[str, str]:
    """{'BTC-FEUSD': 65234.12} -> {'btcx:BTC-FEUSD': '65234.120000000000'}"""
    return {f"{dex}:{coin}": f"{float(px):.12f}" for coin, px in coin_to_price.items()}


def _coins_deployed_in_universe(info: Info, dex: str) -> List[str]:
    """Return the list of 'coin' strings (e.g., 'BTC-FEUSD') currently deployed on this DEX."""
    meta = info.meta(dex=dex)
    deployed: List[str] = []
    for a in meta.get("universe", []):
        name = a.get("name", "")
        if name.startswith(f"{dex}:"):
            deployed.append(name.split(":", 1)[1])  # keep only the coin part
    return deployed


def _set_oracle_with_retry(exchange, dex: str, mapping: Dict[str, str], tries: int = 5, debug: bool = False) -> Dict[str, Any]:
    """
    Call perp_deploy_set_oracle with a small retry loop for propagation:
    - If we see "missing perp" in the response, wait and retry.
    - For any other error, return immediately.
    """
    last_res: Dict[str, Any] = {}
    for i in range(tries):
        try:
            res = exchange.perp_deploy_set_oracle(dex, mapping, [], mapping)
            last_res = res if isinstance(res, dict) else {"status": "err", "response": res}
        except Exception as e:
            last_res = {"status": "err", "response": str(e)}
            if debug:
                print(f"[debug] Exception during oracle set: {e}")

        # Print the full response for debugging
        if debug:
            print(f"[debug] Attempt {i+1} - Full response: {last_res}")
            print(f"[debug] Response type: {type(last_res)}")
            if isinstance(last_res, dict):
                print(f"[debug] Keys: {list(last_res.keys())}")

        status = last_res.get("status")
        if status == "ok":
            return last_res

        msg = str(last_res.get("response", "")).lower()
        if "missing perp" in msg:
            wait = 2.0 * (i + 1)
            if debug:
                print(f"[retry {i+1}/{tries}] oracle set: missing perp, waiting {wait:.1f}s...")
            time.sleep(wait)
            continue

        if "oracle price update too often" in msg:
            wait = 3.0  # Wait 3 seconds for rate limit
            if debug:
                print(f"[retry {i+1}/{tries}] oracle set: rate limited, waiting {wait:.1f}s...")
            time.sleep(wait)
            continue

        # Different error -> bail out early
        if debug:
            print(f"[debug] Different error, stopping retries: {msg}")
        return last_res

    return last_res


# ----------------------- Public API ----------------------- #

def update_btc_feusd_oracle(dex: str, debug: bool = False) -> Dict[str, Any]:
    """
    Update oracle price for BTC-FEUSD specifically using HyperEVM contract data.
    - Only handles BTC-FEUSD symbol
    - Reads price from HyperEVM contract and pushes via set_oracle
    - Returns a structured result dict

    Args:
        dex: DEX handle (e.g. 'btcx').
        debug: If True, print extra info.

    Returns:
        {
          "status": "ok" | "err" | "noop",
          "symbol": "BTC-FEUSD",
          "price": float,
          "mapping": { "btcx:BTC-FEUSD": "12345.000000000000" },
          "raw_result": { ... },   # RPC response (if any)
          "contract_data": { ... } # contract price details
        }
    """
    # 0) Setup connections
    address, info, exchange = example_utils.setup(API_URL, skip_ws=True)  # noqa: F841

    # 1) Check if BTC-FEUSD is deployed on this DEX
    deployed = set(_coins_deployed_in_universe(info, dex))
    target_symbol = "BTC-FEUSD"
    
    if debug:
        print(f"[debug] deployed assets: {sorted(deployed)}")
        print(f"[debug] target symbol: {target_symbol}")

    if target_symbol not in deployed:
        return {
            "status": "noop",
            "reason": f"BTC-FEUSD not deployed on DEX '{dex}'",
            "symbol": target_symbol,
            "price": None,
            "mapping": {},
            "raw_result": None,
            "contract_data": {},
        }

    # 2) Check contract admin if debug
    if debug:
        check_contract_admin(debug=True)

    # 3) Read BTC-FEUSD price from HyperEVM contract
    try:
        if debug:
            print(f"[debug] Reading contract price for {target_symbol}...")
        
        price_info = read_contract_price(target_symbol, debug=debug)
        price = price_info['price']
        
        # Check if price is stale (older than 30 minutes)
        if price_info['age_minutes'] > 30:
            print(f"⚠️  Warning: {target_symbol} price is {price_info['age_minutes']} minutes old")
        
    except Exception as e:
        error_msg = f"Failed to read contract price for {target_symbol}: {e}"
        if debug:
            print(f"[debug] {error_msg}")
        
        return {
            "status": "err",
            "reason": error_msg,
            "symbol": target_symbol,
            "price": None,
            "mapping": {},
            "raw_result": None,
            "contract_data": {},
        }

    # 4) Build mapping for oracle
    mapping = {f"{dex}:{target_symbol}": f"{float(price):.12f}"}

    if debug:
        # What the backend sees right now
        meta_now = Info(API_URL, skip_ws=True).meta(dex=dex)
        universe_names = [a.get("name") for a in meta_now.get("universe", [])]
        print("[debug] universe now:", universe_names)
        print("[debug] mapping:", json.dumps(mapping, indent=2))

    # 5) Push oracle with retry handling
    res = _set_oracle_with_retry(exchange, dex, mapping, tries=5, debug=debug)

    status = "ok" if isinstance(res, dict) and res.get("status") == "ok" else "err"

    return {
        "status": status,
        "symbol": target_symbol,
        "price": price,
        "mapping": mapping,
        "raw_result": res,
        "contract_data": {target_symbol: price_info},
    }


def update_oracle_for_dex(dex: str, strict: bool = False, debug: bool = False) -> Dict[str, Any]:
    """
    Update oracle prices for a given DEX using HyperEVM contract data.
    - FOCUSED ON BTC-FEUSD ONLY
    - Reads price from HyperEVM contract and pushes via set_oracle
    - Returns a structured result dict

    Args:
        dex: DEX handle (e.g. 'btcx').
        strict: If True, fail if BTC-FEUSD isn't deployed yet.
        debug: If True, print extra info.

    Returns:
        {
          "status": "ok" | "err" | "noop",
          "pushed_coins": [ "BTC-FEUSD" ],
          "mapping": { "btcx:BTC-FEUSD": "12345.000000000000" },
          "raw_result": { ... },   # RPC response (if any)
          "missing": [ ... ],      # empty for BTC-FEUSD focus
          "contract_data": { ... } # contract price details
        }
    """
    # Simply delegate to the focused BTC-FEUSD function
    result = update_btc_feusd_oracle(dex, debug=debug)
    
    # Convert result format to match original interface
    if result["status"] == "ok":
        return {
            "status": "ok",
            "pushed_coins": [result["symbol"]],
            "mapping": result["mapping"],
            "raw_result": result["raw_result"],
            "missing": [],
            "contract_data": result["contract_data"],
        }
    elif result["status"] == "noop":
        missing = [] if result.get("reason", "").startswith("BTC-FEUSD not deployed") else ["BTC-FEUSD"]
        if strict and missing:
            return {
                "status": "err",
                "reason": "strict mode: BTC-FEUSD is not deployed",
                "missing": missing,
                "pushed_coins": [],
                "mapping": {},
                "raw_result": None,
                "contract_data": {},
            }
        return {
            "status": "noop",
            "reason": result["reason"],
            "missing": missing,
            "pushed_coins": [],
            "mapping": {},
            "raw_result": None,
            "contract_data": {},
        }
    else:  # error
        return {
            "status": "err",
            "reason": result["reason"],
            "missing": ["BTC-FEUSD"] if strict else [],
            "pushed_coins": [],
            "mapping": {},
            "raw_result": result["raw_result"],
            "contract_data": result["contract_data"],
        }


# ----------------------- Direct Contract Reading Functions ----------------------- #

def read_btc_feusd_price(debug: bool = False) -> Dict[str, Any]:
    """
    Read BTC-FEUSD price from the contract.
    Simplified version focused on single symbol.
    
    Returns:
        Dict with BTC-FEUSD price data or error
    """
    if debug:
        print("🔍 Reading BTC-FEUSD price from contract...")
        check_contract_admin(debug=True)
    
    try:
        price_data = read_contract_price("BTC-FEUSD", debug=debug)
        return {"BTC-FEUSD": price_data}
    except Exception as e:
        if debug:
            print(f"❌ Failed to read BTC-FEUSD: {e}")
        return {"BTC-FEUSD": {"error": str(e)}}


def read_all_configured_prices(debug: bool = False) -> Dict[str, Any]:
    """
    Read prices for all configured symbols from the contract.
    Currently only BTC-FEUSD is configured.
    
    Returns:
        Dict with symbol -> price data mapping
    """
    return read_btc_feusd_price(debug=debug)


def main():
    """Test function - read and display BTC-FEUSD price"""
    print("🔍 Testing HyperEVM contract oracle reader for BTC-FEUSD...")
    
    try:
        prices = read_btc_feusd_price(debug=True)
        
        print("\n" + "="*60)
        print("📊 BTC-FEUSD CONTRACT PRICE")
        print("="*60)
        
        data = prices.get("BTC-FEUSD", {})
        if "error" in data:
            print(f"❌ BTC-FEUSD: Error - {data['error']}")
        else:
            age_str = f"{data['age_minutes']}min"
            status = "🟢" if data['age_minutes'] < 10 else "🟡" if data['age_minutes'] < 30 else "🔴"
            print(f"{status} BTC-FEUSD: {data['price']:,.6f} FEUSD per BTC ({age_str} old)")
            print(f"📅 Last Updated: {data['last_update'].strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"🔢 Raw Price: {data['raw_price']:,} (scaled by 10^8)")
            print(f"📍 Contract: {data['contract']}")
        
        print("="*60)
        
        return prices
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return None


if __name__ == "__main__":
    result = main()
