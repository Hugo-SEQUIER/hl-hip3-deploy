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
        only_isolated=False,
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
            only_isolated=False,
            schema=None,
        )
        print(f"[register asset] {dex_spec['dex']}:{asset['coin']} -> {res}")
        time.sleep(1)


def main():
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


if __name__ == "__main__":
    main()
