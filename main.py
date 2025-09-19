#!/usr/bin/env python3
"""
main.py

Example executable script to fetch token IDs from Hyperliquid.
"""

import json
from hyperliquid.info import Info
from src.prices.redstone_prices import fetch_redstone_prices
from src.prices.hl_spot_prices import get_spot_mid, get_stable_usd_factors, debug_spot_catalog
from src.prices.hl_spot_prices import list_spot_pairs_for_token, get_spot_mid_any
from src.hip3.token_ids import get_api_url, build_token_index_map, resolve_tokens
from src.compute.stable_fx import resolve_stable_usd_factor_with_usdc_reference
import src.hl_utils.example_utils as example_utils
from src.hip3.hip3_config import DEX_SPECS, API_URL
from src.hip3.hip3_deploy import get_collateral_index, register_first_asset_and_create_dex, register_extra_assets, deploy_missing_assets_only
from src.hip3.hip3_update_oracle import update_oracle_for_dex
from src.hip3.get_dex_info import get_info_dex
import time


def main_token_ids():
    # Configuration
    network = "mainnet"  # change to "mainnet" if needed
    tokens_to_resolve = ["feUSD", "USDHL", "USDT0"]
    aliases = {"feUSD": ["FEUSD"]}  # optional

    # Connect to API
    api_url = get_api_url(network)
    info = Info(api_url, skip_ws=True)

    # Build token map
    token_map = build_token_index_map(info)

    # Resolve
    resolved, not_found = resolve_tokens(token_map, tokens_to_resolve, aliases)

    # Print results
    result = {
        "network": network,
        "api_url": api_url,
        "resolved": resolved,
        "not_found": not_found,
    }

    print(json.dumps(result, indent=2))

def main_redstone_prices():
    symbols = ["BTC", "ETH", "feUSD", "USDHL", "USDT0", "USDC"]
    try:
        prices = fetch_redstone_prices(
            symbols,
        )
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}))
        return

    print(json.dumps({"ok": True, "prices": prices} , indent=2))

def main_debug_spot_pairs(network: str = "mainnet"):
    
    api_url = get_api_url(network)
    info = Info(api_url, skip_ws=True)

    tokens = ["FEUSD", "USDHL", "USDT0"]  # respect the exact casing you saw in TOKENS
    out = {"network": network, "pairs_by_token": {}, "sample_fx": {}}

    # List all spot pairs that involve each token
    for t in tokens:
        pairs = list_spot_pairs_for_token(info, t)
        out["pairs_by_token"][t] = [
            {"base": b, "quote": q, "pair_index": idx} for (b, q, idx) in pairs
        ]

    # Try to get a usable USD factor for FEUSD and USDHL using USDT0 first, then the other stable
    try:
        out["sample_fx"]["FEUSD_vs_USD_like"] = get_spot_mid_any(info, "FEUSD", ["USDT0", "USDHL"])
    except Exception as e:
        out["sample_fx"]["FEUSD_vs_USD_like_error"] = str(e)

    try:
        out["sample_fx"]["USDHL_vs_USD_like"] = get_spot_mid_any(info, "USDHL", ["USDT0", "FEUSD"])
    except Exception as e:
        out["sample_fx"]["USDHL_vs_USD_like_error"] = str(e)

    print(json.dumps(out, indent=2))


def main_hl_stables(network: str = "mainnet"):
    """
    Print mid-prices for feUSD/USDT0 and USDHL/USDT0 (fallback to USDC),
    and a dict of USD factors for each stable.
    """
    api_url = get_api_url(network)
    info = Info(api_url, skip_ws=True)
    debug_spot_catalog(info, limit=10000)
    out = {"network": network, "api_url": api_url, "pairs": {}, "usd_factors": {}}

    # Try feUSD/USDT0 and USDHL/USDT0; fallback to .../USDC if missing
    pairs_to_try = [("USDC", "feUSD"), ("feUSD", "USDC"),
                    ("USDHL", "USDC"), ("USDHL", "USDC"),
                    ("USDT0", "USDC")]

    for base, quote in pairs_to_try:
        try:
            mid = get_spot_mid(info, base, quote)
            out["pairs"][f"{base}/{quote}"] = mid
        except Exception as e:
            out["pairs"][f"{base}/{quote}"] = f"error: {e}"

    try:
        out["usd_factors"] = get_stable_usd_factors(info)
    except Exception as e:
        out["usd_factors_error"] = str(e)

    print(json.dumps(out, indent=2))

def main_build_btc_quotes_for_dexes():
    """
    Build BTC/<stable> quotes using:
      - BTC/USD from RedStone,
      - USDC/USD from RedStone,
      - <stable>/USD from HL Spot or DexScreener (HyperEVM) with proper USDC reference,
      - fallback peg=1.0 if needed.

    Prints a compact JSON you can turn into HIP-3 oracle maps.
    """

    # ---- Fill these with your HyperEVM addresses (checksummed) ----
    EVM_ADDR = {
        "USDHL": "0xd289c79872a9eace15cc4cadb030661f",
        "FEUSD": "0x88102bea0bbad5f301f6e9e4dacdf979",
        "USDT0": "0x25faedc3f054130dbb4e4203aca63567",
        "USDC":  "0x6d1e7cde53ba9467b783cb7c530ce054"
    }

    # 1) RedStone BTC/USD and USDC/USD
    rs = fetch_redstone_prices(["BTC", "USDC"])
    btc_usd = float(rs["BTC"]["value"])
    usdc_usd = float(rs["USDC"]["value"])

    # 2) Resolve stables vs USD using proper USDC reference
    info = Info(get_api_url("mainnet"), skip_ws=True)
    fx_feusd  = resolve_stable_usd_factor_with_usdc_reference(info, "FEUSD", usdc_usd, evm_addresses=EVM_ADDR, evm_usd_reference="USDC")
    fx_usdhl  = resolve_stable_usd_factor_with_usdc_reference(info, "USDHL", usdc_usd, evm_addresses=EVM_ADDR, evm_usd_reference="USDC")
    fx_usdt0  = resolve_stable_usd_factor_with_usdc_reference(info, "USDT0", usdc_usd, evm_addresses=EVM_ADDR, evm_usd_reference="USDC")

    # 3) Convert BTC/USD -> BTC/<stable>
    # BTC/X = (BTC/USD) / (X/USD)
    out = {
        "inputs": {
            "btc_usd_redstone": btc_usd,
            "usdc_usd_redstone": usdc_usd,
            "fx_feusd_usd": fx_feusd,
            "fx_usdhl_usd": fx_usdhl,
            "fx_usdt0_usd": fx_usdt0,
        },
        "quotes": {
            "BTC-FEUSD": btc_usd / (fx_feusd  if fx_feusd  else 1.0),
            "BTC-USDHL": btc_usd / (fx_usdhl  if fx_usdhl  else 1.0),
            "BTC-USDT0": btc_usd / (fx_usdt0  if fx_usdt0  else 1.0),
        }
    }

    print(json.dumps(out, indent=2))


def main_hip3_deploy():
        # 0) Wallet + connections (via example_utils from HL examples)
    address, info, exchange = example_utils.setup(API_URL, skip_ws=True)
    print("perp deploy auction:", info.query_perp_deploy_auction_status())

    # 1) Deploy each DEX
    for spec in DEX_SPECS:
        print(f"\n=== Deploy DEX {spec['dex']} (collateral={spec['collateral_symbol']}) ===")
        coll_index = get_collateral_index(info, spec["collateral_symbol"])
        res1 = register_first_asset_and_create_dex(exchange, address, spec, coll_index)
        print("[create dex + register 1st asset] ->", res1)
        time.sleep(1)

        register_extra_assets(exchange, spec)

        # 2) Inspect meta
        meta = info.meta(dex=spec["dex"])
        print("[meta]", spec["dex"], "->", json.dumps(meta, indent=2))

    print("\nAll done.")

def main_oracle_update():
    result = update_oracle_for_dex("btcx", strict=False, debug=True)
    print("Oracle update result:", result["status"], "coins:", result["pushed_coins"])

def main_deploy_missing_assets():
    """Deploy only missing assets for existing DEXes."""
    deploy_missing_assets_only()

def main_get_dex_info():
    meta = get_info_dex("btcx")
    print(json.dumps(meta, indent=2))

if __name__ == "__main__":
    main_oracle_update()
