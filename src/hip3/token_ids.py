"""
token_ids.py

Reusable functions to fetch Hyperliquid spot token IDs.
"""

from typing import Dict, Any, List, Tuple, Optional
from hyperliquid.info import Info
from hyperliquid.utils import constants


def get_api_url(network: str = "testnet", api_url_override: Optional[str] = None) -> str:
    """Resolve the API URL based on flags (custom overrides default)."""
    if api_url_override:
        return api_url_override
    if network.lower() == "mainnet":
        return constants.MAINNET_API_URL
    print(constants.TESTNET_API_URL)
    return constants.TESTNET_API_URL


def build_token_index_map(info: Info) -> Dict[str, Tuple[str, int]]:
    """
    Returns a dict mapping lowercased token NAME -> (exact_name, index).
    Uses `info.spot_meta()`.
    """
    spot = info.spot_meta()
    mapping: Dict[str, Tuple[str, int]] = {}
    for t in spot.get("tokens", []):
        name = t.get("name")
        idx = t.get("index")
        if name is None or idx is None:
            continue
        mapping[name.lower()] = (name, idx)
    return mapping


def resolve_tokens(
    token_map: Dict[str, Tuple[str, int]],
    wanted: List[str],
    aliases: Optional[Dict[str, List[str]]] = None,
) -> Tuple[Dict[str, Dict[str, Any]], List[str]]:
    """
    Resolve a list of desired token names to their (exact_name, index).
    - Case-insensitive
    - Optional aliases (e.g., {"feUSD": ["FEUSD"]})

    Returns:
      resolved: {wanted_input: {"exact_name": str, "index": int}}
      not_found: [wanted_input, ...]
    """
    if aliases is None:
        aliases = {}

    resolved: Dict[str, Dict[str, Any]] = {}
    not_found: List[str] = []

    for w in wanted:
        keys_to_try = [w.lower()]
        for a in aliases.get(w, []):
            keys_to_try.append(a.lower())

        hit = None
        for k in keys_to_try:
            if k in token_map:
                exact, idx = token_map[k]
                hit = {"exact_name": exact, "index": idx}
                break

        if hit is None:
            not_found.append(w)
        else:
            resolved[w] = hit

    return resolved, not_found
