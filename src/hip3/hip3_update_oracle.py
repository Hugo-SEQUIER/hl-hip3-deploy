#!/usr/bin/env python3
"""
hip3_update_oracle.py

Fetch BTC/USD from RedStone, compute BTC/<stable> using FX factors,
then push to HIP-3 oracle for each configured DEX.

- RedStone: robust HTTP gateways
- FX: tries HL Spot (if pairs exist) else DexScreener (HyperEVM), else peg=1.0
- Push: exchange.perp_deploy_set_oracle(dex, mapping, [], {})

Run frequently (cron/systemd) or on demand.
"""

import sys
import time
from typing import Dict

from hyperliquid.info import Info
# example_utils provides (address, info, exchange) ready to use
import src.hl_utils.example_utils as example_utils

from src.hip3.hip3_config import API_URL, DEX_SPECS, EVM_ADDR
from src.prices.redstone_prices import fetch_redstone_prices
from src.compute.stable_fx import resolve_stable_usd_factor


def build_price_map_for_dex(dex: str, coin_to_price: Dict[str, float]) -> Dict[str, str]:
    """Convert {'BTC-FEUSD': 65234.12, ...} -> {'DEX:BTC-FEUSD': '65234.12', ...}."""
    out = {}
    for coin, px in coin_to_price.items():
        out[f"{dex}:{coin}"] = f"{float(px):.12f}"   # stringify with precision
    return out


def main():
    # 0) Wallet + connections
    address, info, exchange = example_utils.setup(API_URL, skip_ws=True)

    # 1) Fetch BTC/USD (and optionally USDT0/USDC sanity) from RedStone
    rs = fetch_redstone_prices(["BTC", "USDT0", "USDC"])
    btc_usd = float(rs["BTC"]["value"])

    # 2) Resolve stable->USD factors
    #    Uses HL Spot where possible, else DexScreener via EVM_ADDR, else peg=1.0
    hl_info = Info(API_URL, skip_ws=True)
    fx_cache: Dict[str, float] = {}
    for symbol in {"FEUSD", "USDHL", "USDT0"}:
        fx_cache[symbol] = resolve_stable_usd_factor(
            hl_info,
            symbol,
            evm_addresses=EVM_ADDR,
            evm_usd_reference="USDC",
        )

    # 3) For each DEX, compute the price for its asset(s) and push
    for spec in DEX_SPECS:
        dex = spec["dex"]
        prices: Dict[str, float] = {}
        for a in spec["assets"]:
            coin = a["coin"]         # e.g., "BTC-FEUSD"
            base, quote = coin.split("-", 1)
            if base != "BTC":
                raise ValueError(f"Only BTC-* supported in this quick example; got {coin}")
            if quote not in fx_cache:
                raise ValueError(f"Missing FX for quote {quote}; have {list(fx_cache.keys())}")

            fx = fx_cache[quote] or 1.0
            prices[coin] = btc_usd / fx  # BTC/QUOTE = (BTC/USD) / (QUOTE/USD)

        mapping = build_price_map_for_dex(dex, prices)
        try:
            res = exchange.perp_deploy_set_oracle(dex, mapping, [], {})
            print(f"[oracle set] {dex} ->", res)
        except Exception as e:
            print(f"[error] set_oracle for {dex}: {e}", file=sys.stderr)

        time.sleep(1)  # small spacing between pushes

    print("Oracle updates done.")


if __name__ == "__main__":
    main()
