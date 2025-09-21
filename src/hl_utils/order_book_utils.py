#!/usr/bin/env python3
"""
order_book_utils.py

Utility functions for reading order book data using the Info API.
Implements robust order book reading with proper error handling and fallbacks.
"""

from hyperliquid.info import Info
from src.hip3.hip3_config import API_URL


def read_order_book(coin, n_sig_figs=None, mantissa=None):
    """
    Read order book data for a given coin using the Info API.
    
    Args:
        coin (str): The coin symbol (e.g., "btcx:BTC-FEUSD")
        n_sig_figs (int, optional): Number of significant figures for price precision
        mantissa (int, optional): Mantissa for size precision
    
    Returns:
        dict: Result dictionary with success status, data, and metadata
        {
            "success": bool,
            "data": dict,  # Order book data
            "metadata": dict,  # Request metadata
            "error": str  # Error message if failed
        }
    """
    try:
        info = Info(API_URL, skip_ws=True)
        payload = {
            "type": "l2Book",
            "coin": coin,
        }
        if n_sig_figs is not None:
            payload["nSigFigs"] = n_sig_figs
        if mantissa is not None:
            payload["mantissa"] = mantissa

        # Current SDKs: post(path, payload). Fallback for older SDKs: post(payload)
        try:
            ob = info.post("/info", payload)
        except TypeError:
            ob = info.post(payload)

        return {
            "success": True, 
            "data": ob, 
            "metadata": {"coin": coin, "nSigFigs": n_sig_figs, "mantissa": mantissa}
        }
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "metadata": {"coin": coin, "nSigFigs": n_sig_figs, "mantissa": mantissa},
            "error": str(e)
        }


def get_order_book_levels(coin, n_sig_figs=None, mantissa=None):
    """
    Get order book levels (bids and asks) for a given coin.
    
    Args:
        coin (str): The coin symbol
        n_sig_figs (int, optional): Number of significant figures for price precision
        mantissa (int, optional): Mantissa for size precision
    
    Returns:
        dict: Result with bids, asks, and metadata
        {
            "success": bool,
            "bids": list,  # List of [price, size] tuples
            "asks": list,  # List of [price, size] tuples
            "metadata": dict,
            "error": str  # Error message if failed
        }
    """
    result = read_order_book(coin, n_sig_figs, mantissa)
    
    if not result["success"]:
        return {
            "success": False,
            "bids": [],
            "asks": [],
            "metadata": result["metadata"],
            "error": result["error"]
        }
    
    try:
        # Extract bids and asks from the order book data
        levels = result["data"].get("levels", [])
        if not levels:
            return {
                "success": True,
                "bids": [],
                "asks": [],
                "metadata": result["metadata"],
                "error": "No levels found in order book"
            }
        
        # The structure is: levels = [bids_list, asks_list]
        # Each level is a list of order objects with {px, sz, n}
        bids_raw = levels[0] if len(levels) > 0 else []
        asks_raw = levels[1] if len(levels) > 1 else []
        
        # Convert to [price, size] format for consistency with existing code
        bids = [[order["px"], order["sz"]] for order in bids_raw]
        asks = [[order["px"], order["sz"]] for order in asks_raw]
        
        return {
            "success": True,
            "bids": bids,
            "asks": asks,
            "metadata": result["metadata"]
        }
        
    except Exception as e:
        return {
            "success": False,
            "bids": [],
            "asks": [],
            "metadata": result["metadata"],
            "error": f"Error parsing order book data: {str(e)}"
        }


def get_best_bid_ask(coin, n_sig_figs=None, mantissa=None):
    """
    Get the best bid and ask prices for a given coin.
    
    Args:
        coin (str): The coin symbol
        n_sig_figs (int, optional): Number of significant figures for price precision
        mantissa (int, optional): Mantissa for size precision
    
    Returns:
        dict: Result with best bid/ask and spread information
        {
            "success": bool,
            "best_bid": dict,  # {"price": float, "size": float}
            "best_ask": dict,  # {"price": float, "size": float}
            "spread": float,   # Absolute spread
            "spread_percent": float,  # Spread as percentage
            "metadata": dict,
            "error": str  # Error message if failed
        }
    """
    result = get_order_book_levels(coin, n_sig_figs, mantissa)
    
    if not result["success"]:
        return {
            "success": False,
            "best_bid": None,
            "best_ask": None,
            "spread": None,
            "spread_percent": None,
            "metadata": result["metadata"],
            "error": result["error"]
        }
    
    bids = result["bids"]
    asks = result["asks"]
    
    if not bids or not asks:
        return {
            "success": False,
            "best_bid": None,
            "best_ask": None,
            "spread": None,
            "spread_percent": None,
            "metadata": result["metadata"],
            "error": "No bids or asks available"
        }
    
    try:
        # Best bid is the highest price (first in sorted descending order)
        best_bid_price = float(bids[0][0])
        best_bid_size = float(bids[0][1])
        
        # Best ask is the lowest price (first in sorted ascending order)
        best_ask_price = float(asks[0][0])
        best_ask_size = float(asks[0][1])
        
        spread = best_ask_price - best_bid_price
        spread_percent = (spread / best_bid_price) * 100
        
        return {
            "success": True,
            "best_bid": {"price": best_bid_price, "size": best_bid_size},
            "best_ask": {"price": best_ask_price, "size": best_ask_size},
            "spread": spread,
            "spread_percent": spread_percent,
            "metadata": result["metadata"]
        }
        
    except (ValueError, IndexError) as e:
        return {
            "success": False,
            "best_bid": None,
            "best_ask": None,
            "spread": None,
            "spread_percent": None,
            "metadata": result["metadata"],
            "error": f"Error parsing bid/ask data: {str(e)}"
        }


def check_order_book_liquidity(coin, min_bids=1, min_asks=1):
    """
    Check if the order book has sufficient liquidity.
    
    Args:
        coin (str): The coin symbol
        min_bids (int): Minimum number of bids required
        min_asks (int): Minimum number of asks required
    
    Returns:
        dict: Liquidity check result
        {
            "success": bool,
            "has_liquidity": bool,
            "bid_count": int,
            "ask_count": int,
            "metadata": dict,
            "error": str  # Error message if failed
        }
    """
    result = get_order_book_levels(coin)
    
    if not result["success"]:
        return {
            "success": False,
            "has_liquidity": False,
            "bid_count": 0,
            "ask_count": 0,
            "metadata": result["metadata"],
            "error": result["error"]
        }
    
    bid_count = len(result["bids"])
    ask_count = len(result["asks"])
    has_liquidity = bid_count >= min_bids and ask_count >= min_asks
    
    return {
        "success": True,
        "has_liquidity": has_liquidity,
        "bid_count": bid_count,
        "ask_count": ask_count,
        "metadata": result["metadata"]
    }


# Example usage and testing functions
def example_usage():
    """Example of how to use the order book utilities."""
    coin = "btcx:BTC-FEUSD"
    
    print(f"=== Order Book Utilities Example ===")
    print(f"Coin: {coin}")
    
    # Read full order book
    print(f"\n1. Reading full order book...")
    ob_result = read_order_book(coin)
    if ob_result["success"]:
        print(f"✓ Order book data retrieved")
        print(f"Data keys: {list(ob_result['data'].keys())}")
    else:
        print(f"✗ Failed to read order book: {ob_result['error']}")
    
    # Get order book levels
    print(f"\n2. Getting order book levels...")
    levels_result = get_order_book_levels(coin)
    if levels_result["success"]:
        print(f"✓ Found {len(levels_result['bids'])} bids and {len(levels_result['asks'])} asks")
    else:
        print(f"✗ Failed to get levels: {levels_result['error']}")
    
    # Get best bid/ask
    print(f"\n3. Getting best bid/ask...")
    best_result = get_best_bid_ask(coin)
    if best_result["success"]:
        print(f"✓ Best bid: {best_result['best_bid']['price']} @ {best_result['best_bid']['size']}")
        print(f"✓ Best ask: {best_result['best_ask']['price']} @ {best_result['best_ask']['size']}")
        print(f"✓ Spread: {best_result['spread']:.2f} ({best_result['spread_percent']:.2f}%)")
    else:
        print(f"✗ Failed to get best bid/ask: {best_result['error']}")
    
    # Check liquidity
    print(f"\n4. Checking liquidity...")
    liquidity_result = check_order_book_liquidity(coin)
    if liquidity_result["success"]:
        print(f"✓ Liquidity check: {liquidity_result['has_liquidity']}")
        print(f"  Bids: {liquidity_result['bid_count']}, Asks: {liquidity_result['ask_count']}")
    else:
        print(f"✗ Failed to check liquidity: {liquidity_result['error']}")


if __name__ == "__main__":
    example_usage()
