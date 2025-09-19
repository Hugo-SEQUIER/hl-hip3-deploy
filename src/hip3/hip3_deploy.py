#!/usr/bin/env python3
"""
hip3_deploy.py

Deploy a HIP-3 DEX (one collateral per DEX) and register its assets.
- Reads config from hip3_config.py
- Resolves collateralToken index via spot_meta()
- First register_asset call with `schema` creates the DEX
- Subsequent register_asset calls (schema=None) add more assets
"""

import time
import json
import sys
from typing import Dict

from hyperliquid.info import Info
from hyperliquid.utils.error import ServerError

# your local helpers
from src.hip3.hip3_config import API_URL, DEX_SPECS, MAX_GAS

# NOTE: example_utils is from HL examples. Replace with your own setup if needed.
import src.hl_utils.example_utils as example_utils


def create_info_with_retry(api_url: str, retries: int = 6, base_delay: float = 0.8) -> Info:
    """Instantiate Info with exponential backoff on transient 5xx."""
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            return Info(api_url, skip_ws=True)
        except ServerError as e:
            status = getattr(e, "status_code", None)
            if status and 500 <= int(status) < 600:
                wait = base_delay * (2 ** (attempt - 1))
                print(f"[warn] HL API {status} attempt {attempt}/{retries}; sleep {wait:.1f}s", file=sys.stderr)
                time.sleep(wait)
                last_err = e
                continue
            raise
        except Exception as e:
            wait = base_delay * (2 ** (attempt - 1))
            print(f"[warn] {e} attempt {attempt}/{retries}; sleep {wait:.1f}s", file=sys.stderr)
            time.sleep(wait)
            last_err = e
            continue
    raise last_err  # type: ignore


def get_collateral_index(info: Info, symbol: str) -> int:
    """Return spot token index for `symbol` (exact case) from spot_meta()."""
    spot = info.spot_meta()
    for t in spot.get("tokens", []):
        if t.get("name") == symbol:
            return int(t["index"])
    raise RuntimeError(f"Collateral symbol not found in spot_meta tokens: {symbol}")


def register_first_asset_and_create_dex(exchange, address: str, dex_spec: Dict, collateral_index: int):
    """Create DEX via first register_asset (with schema)."""
    first = dex_spec["assets"][0]
    return exchange.perp_deploy_register_asset(
        dex=dex_spec["dex"],
        max_gas=MAX_GAS,
        coin=f'{dex_spec["dex"]}:{first["coin"]}',
        sz_decimals=int(first["sz_decimals"]),
        oracle_px=str(first["initial_oracle_px"]),
        margin_table_id=int(dex_spec["margin_table_id"]),
        only_isolated=first["isolated_only"],
        schema={
            "fullName": dex_spec["full_name"],
            "collateralToken": collateral_index,
            "oracleUpdater": address,  # this wallet can update the oracle later
        },
    )


def register_extra_assets(exchange, dex_spec: Dict):
    """Add remaining assets (no schema)."""
    for asset in dex_spec["assets"][1:]:
        res = exchange.perp_deploy_register_asset(
            dex=dex_spec["dex"],
            max_gas=MAX_GAS,
            coin=f'{dex_spec["dex"]}:{asset["coin"]}',
            sz_decimals=int(asset["sz_decimals"]),
            oracle_px=str(asset["initial_oracle_px"]),
            margin_table_id=int(dex_spec["margin_table_id"]),
            only_isolated=True,
            schema=None,
        )
        print(f"[register asset] {dex_spec['dex']}:{asset['coin']} -> {res}")
        time.sleep(1)


def get_missing_assets(info: Info, dex_spec: Dict) -> list:
    """Return list of assets that are missing from the DEX."""
    try:
        meta = info.meta(dex=dex_spec["dex"])
        deployed_assets = set()
        
        # Get list of deployed assets from meta
        if "universe" in meta:
            for asset in meta["universe"]:
                asset_name = asset.get("name", "")
                if asset_name.startswith(f"{dex_spec['dex']}:"):
                    coin_name = asset_name.split(":", 1)[1]
                    deployed_assets.add(coin_name)
        
        # Find missing assets
        missing_assets = []
        for asset in dex_spec["assets"]:
            if asset["coin"] not in deployed_assets:
                missing_assets.append(asset)
        
        return missing_assets
    except Exception as e:
        print(f"[warn] Could not check existing assets for {dex_spec['dex']}: {e}")
        # If we can't check, assume all assets are missing
        return dex_spec["assets"]


def register_missing_assets(exchange, dex_spec: dict, missing_assets: list, max_retries: int = 3):
    for asset in missing_assets:
        retries = 0
        while retries < max_retries:
            try:
                res = exchange.perp_deploy_register_asset(
                    dex=dex_spec["dex"],                 # e.g. "btcx"
                    max_gas=None,                        # <-- ensure SDK omits maxGas in JSON
                    coin=str(asset["coin"]),             # e.g. "BTC-USDHL" (NO "dex:" prefix)
                    sz_decimals=int(asset["sz_decimals"]),
                    oracle_px=str(asset["initial_oracle_px"]),
                    margin_table_id=int(dex_spec["margin_table_id"]),
                    only_isolated=bool(asset.get("isolated_only", False)),
                    schema=None,                         # adding to existing DEX
                )

                status = (res or {}).get("status", "").lower()
                err = (res or {}).get("response", "") or (res or {}).get("error", "")

                if status == "ok":
                    print(f"[success] {dex_spec['dex']}:{asset['coin']} registered")
                    break

                if any(s in (err or "").lower() for s in ["already exists", "duplicate", "asset exists"]):
                    print(f"[ok-idempotent] {dex_spec['dex']}:{asset['coin']} already registered")
                    break

                if any(s in (err or "").lower() for s in ["auction", "gas auction", "temporarily", "busy", "try again"]):
                    retries += 1
                    sleep = 1.5 * retries
                    print(f"[retry {retries}/{max_retries}] transient: {err} -> sleep {sleep:.1f}s")
                    time.sleep(sleep)
                    continue

                print(f"[failed] {dex_spec['dex']}:{asset['coin']} - {err or 'Unknown error'}")
                break

            except Exception as e:
                retries += 1
                if retries < max_retries:
                    sleep = 1.5 * retries
                    print(f"[retry {retries}/{max_retries}] exception: {e} -> sleep {sleep:.1f}s")
                    time.sleep(sleep)
                else:
                    print(f"[failed] {dex_spec['dex']}:{asset['coin']} - exception after max retries: {e}")
                    break

        time.sleep(0.5)

def deploy_missing_assets_only():
    """Deploy only the assets that are missing from existing DEXes."""
    # 0) Wallet + connections
    address, info, exchange = example_utils.setup(API_URL, skip_ws=True)
    print("perp deploy auction:", info.query_perp_deploy_auction_status())

    # 1) Check each DEX for missing assets
    for spec in DEX_SPECS:
        print(f"\n=== Checking DEX {spec['dex']} for missing assets ===")
        
        missing_assets = get_missing_assets(info, spec)
        
        if not missing_assets:
            print(f"[info] All assets already deployed for {spec['dex']}")
            continue
            
        print(f"[info] Found {len(missing_assets)} missing assets for {spec['dex']}:")
        for asset in missing_assets:
            print(f"  - {asset['coin']}")
        
        # Deploy missing assets
        register_missing_assets(exchange, spec, missing_assets)
        
        # 2) Show final meta
        meta = info.meta(dex=spec["dex"])
        print("[meta]", spec["dex"], "->", json.dumps(meta, indent=2))

    print("\nMissing assets deployment completed.")
