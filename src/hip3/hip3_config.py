"""
hip3_config.py

Central configuration for HIP-3 deployment and oracle updates.
Edit ONE place, both scripts read from here.
"""

from hyperliquid.utils import constants

# ---- Network ----
API_URL = constants.TESTNET_API_URL   # or constants.TESTNET_API_URL

# ---- Your DEXes (one collateral per DEX) ----
# coin labels are arbitrary strings you’ll keep consistent in oracle updates
DEX_SPECS = [
    {
        "dex": "btcx",                      # <= 6 chars
        "full_name": "BTC Perp Markets",
        "collateral_symbol": "USDC",        # unique collateral for the whole DEX
        "margin_table_id": 10,
        "assets": [
            {"coin": "BTC-FEUSD",  "sz_decimals": 3, "initial_oracle_px": "117688.207", "isolated_only": True},
            {"coin": "BTC-USDHL",  "sz_decimals": 3, "initial_oracle_px": "117099.648", "isolated_only": True},
            {"coin": "BTC-USDT0",  "sz_decimals": 3, "initial_oracle_px": "117029.416", "isolated_only": True},
        ],
    }
]


# ---- HyperEVM token addresses for FX fallbacks (fill these) ----
# Checksummed addresses on HyperEVM for DexScreener lookups
EVM_ADDR = {
    "USDHL": "0xd289c79872a9eace15cc4cadb030661f",
    "FEUSD": "0x88102bea0bbad5f301f6e9e4dacdf979",
    "USDT0": "0x25faedc3f054130dbb4e4203aca63567",
    "USDC":  "0x6d1e7cde53ba9467b783cb7c530ce054"
}

# ---- Perp deploy auction gas cap (testnet often ignores; mainnet matters) ----
MAX_GAS = 1_000_000_000_000
