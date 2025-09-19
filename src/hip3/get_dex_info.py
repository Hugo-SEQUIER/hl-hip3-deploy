#!/usr/bin/env python3
"""
get_dex_info.py — Inspect a HIP-3 perp DEX in detail.

What it prints:
- Perp deploy auction status (so you know if you can register assets now)
- Raw meta for the DEX (JSON)
- A condensed summary of the universe (assets, isolation, leverage, margin table)
- Margin table details
- Expected oracle mapping keys (exact strings you must use when pushing prices)
- Spot tokens (to confirm your collateral symbol exists)

"""

import json
from typing import List, Dict, Any

# Your local helper that sets up wallet + clients
import src.hl_utils.example_utils as example_utils
from src.hip3.hip3_config import API_URL


def print_json(title: str, obj: Any) -> None:
    print(f"\n=== {title} ===")
    try:
        print(json.dumps(obj, indent=2))
    except Exception:
        print(obj)


def summarize_universe(meta: Dict[str, Any], dex: str) -> None:
    uni: List[Dict[str, Any]] = meta.get("universe", []) or []
    if not uni:
        print("\n[summary] No assets deployed yet on this DEX.")
        return

    print("\n[summary] Assets deployed on this DEX:")
    for a in uni:
        name = a.get("name")
        only_iso = a.get("onlyIsolated")
        max_lev = a.get("maxLeverage")
        sz_dec = a.get("szDecimals")
        mtable  = a.get("marginTableId")
        print(f"  - {name} | isolated={only_iso} | maxLev={max_lev} | szDecimals={sz_dec} | marginTableId={mtable}")

    # Expected oracle mapping keys
    mapping_keys = [a["name"] for a in uni if "name" in a]
    print("\n[summary] Oracle mapping keys to use in set_oracle():")
    for k in mapping_keys:
        print(f"  - {k}")

    # Helpful split (coin names)
    coins = [n.split(":", 1)[1] for n in mapping_keys if n and n.startswith(f"{dex}:")]
    print("\n[summary] Coin symbols (base-quote) detected:")
    for c in coins:
        print(f"  - {c}")


def summarize_margin_tables(meta: Dict[str, Any]) -> None:
    mtables = meta.get("marginTables", []) or []
    if not mtables:
        print("\n[summary] No margin tables found.")
        return

    print("\n[summary] Margin tables (id -> tiers):")
    # On many deployments, marginTables are represented as [id, {description, marginTiers: [...] }]
    for entry in mtables:
        try:
            table_id, body = entry
            desc = (body or {}).get("description", "")
            tiers = (body or {}).get("marginTiers", []) or []
            print(f"  - id={table_id} description='{desc}'")
            for t in tiers:
                lb = t.get("lowerBound")
                maxlev = t.get("maxLeverage")
                print(f"      tier: lowerBound={lb} maxLeverage={maxlev}")
        except Exception:
            print(f"  - raw entry: {entry}")


def get_info_dex(dex: str):
    # You can use example_utils.setup if you want wallet & exchange too,
    # but for read-only inspection Info is enough.
    # Keeping example_utils.setup so you also see the wallet address you’re using.
    address, info, exchange = example_utils.setup(API_URL, skip_ws=True)  # noqa: F841
    print(f"Running with account address: {address}")

    # Auction status (tells you if you can register new assets right now)
    auction = info.query_perp_deploy_auction_status()
    print_json("Perp deploy auction status", auction)

    # DEX meta (the core source of truth for deployed assets / margin tables)
    meta = info.meta(dex=dex)
    print_json(f"Raw meta for DEX '{dex}'", meta)

    # Condensed summaries
    summarize_universe(meta, dex)
    summarize_margin_tables(meta)

    print("\n[hint] If you plan to push oracle prices, your mapping keys must match the "
          "exact strings shown above (e.g., 'btcx:BTC-FEUSD').")
    return meta

