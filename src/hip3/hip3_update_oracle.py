#!/usr/bin/env python3
"""
hip3_update_oracle.py

Importable module to update HIP-3 perp oracle prices.

Exports:
    update_oracle_for_dex(dex: str, strict: bool = False, debug: bool = False) -> dict

Behavior:
- Only pushes prices for assets that are ALREADY deployed (read from meta.universe).
- Optional strict mode fails if some configured assets aren't deployed yet.
- Includes retry handling for the common "missing perp" propagation issue.

"""

from __future__ import annotations

import json
import time
from typing import Dict, List, Any

from hyperliquid.info import Info
# Your local helper that returns (address, info, exchange)
import src.hl_utils.example_utils as example_utils

from src.hip3.hip3_config import API_URL, DEX_SPECS, EVM_ADDR
from src.prices.redstone_prices import fetch_redstone_prices
from src.compute.stable_fx import resolve_stable_usd_factor


# ----------------------- internal helpers ----------------------- #

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


# ----------------------- public API ----------------------- #

def update_oracle_for_dex(dex: str, strict: bool = False, debug: bool = False) -> Dict[str, Any]:
    """
    Update oracle prices for a given DEX.
    - Reads configured assets from DEX_SPECS.
    - Filters to assets that actually exist on-chain (meta.universe).
    - Computes BTC/<stable> prices and pushes them via set_oracle.
    - Returns a structured result dict.

    Args:
        dex: DEX handle (e.g. 'btcx').
        strict: If True, fail if any configured asset isn't deployed yet.
        debug: If True, print extra info.

    Returns:
        {
          "status": "ok" | "err" | "noop",
          "pushed_coins": [ ... ],
          "mapping": { "btcx:BTC-FEUSD": "12345.000000000000", ... },
          "raw_result": { ... },   # RPC response (if any)
          "missing": [ ... ]       # configured-but-not-deployed (strict or debug)
        }
    """
    # 0) Setup connections
    address, info, exchange = example_utils.setup(API_URL, skip_ws=True)  # noqa: F841

    # 1) Find DEX spec
    spec = next((s for s in DEX_SPECS if s["dex"] == dex), None)
    if not spec:
        raise ValueError(f"DEX '{dex}' not found in DEX_SPECS")

    # 2) Determine deployed vs configured assets
    deployed = set(_coins_deployed_in_universe(info, dex))
    configured = [a["coin"] for a in spec["assets"]]
    target_coins = [c for c in configured if c in deployed]
    missing = [c for c in configured if c not in deployed]

    if debug:
        print(f"[debug] configured: {configured}")
        print(f"[debug] deployed  : {sorted(deployed)}")
        print(f"[debug] target    : {target_coins}")
        if missing:
            print(f"[debug] missing   : {missing}")

    if strict and missing:
        return {
            "status": "err",
            "reason": "strict mode: some configured assets are not deployed",
            "missing": missing,
            "pushed_coins": [],
            "mapping": {},
            "raw_result": None,
        }

    if not target_coins:
        return {
            "status": "noop",
            "reason": "no deployed assets for this DEX",
            "missing": missing,
            "pushed_coins": [],
            "mapping": {},
            "raw_result": None,
        }

    # 3) Fetch BTC and stable reference prices
    rs = fetch_redstone_prices(["BTC", "USDT0", "USDC"])
    btc_usd = float(rs["BTC"]["value"])
    if debug:
        print(f"[debug] BTC/USD from RedStone: {btc_usd}")

    fx_syms = {c.split("-", 1)[1] for c in target_coins}  # quotes for the deployed coins
    hl_info = Info(API_URL, skip_ws=True)
    fx_cache: Dict[str, float] = {}
    for sym in fx_syms:
        fx_cache[sym] = resolve_stable_usd_factor(
            hl_info, sym, evm_addresses=EVM_ADDR, evm_usd_reference="USDC"
        )
        if debug:
            print(f"[debug] {sym}/USD factor: {fx_cache[sym]}")

    # 4) Compute BTC/QUOTE = (BTC/USD) / (QUOTE/USD)
    prices: Dict[str, float] = {}
    for coin in target_coins:
        base, quote = coin.split("-", 1)
        if base != "BTC":
            raise ValueError(f"Only BTC-* supported by this example; got {coin}")
        fx = fx_cache.get(quote) or 1.0
        prices[coin] = btc_usd / fx

    mapping = _build_price_map_for_dex(dex, prices)

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
        "pushed_coins": target_coins,
        "mapping": mapping,
        "raw_result": res,
        "missing": missing,
    }
