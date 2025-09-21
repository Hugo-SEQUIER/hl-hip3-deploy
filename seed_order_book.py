#!/usr/bin/env python3
"""
seed_order_book.py

Script to seed an empty order book with initial orders.
This will place both buy and sell orders to create liquidity.
Enhanced with loop and random spreads for better market simulation.
"""

import json
import time
import random
import requests
from decimal import Decimal, ROUND_DOWN
from hyperliquid.utils import constants
from src.hl_utils.example_utils import setup
from src.hip3.hip3_config import DEX_SPECS, API_URL
from src.hl_utils.order_book_utils import get_order_book_levels, check_order_book_liquidity

DUMMY_DEX = "btcx"
COIN = f"{DUMMY_DEX}:BTC-FEUSD"
BASE_COIN = "BTC-FEUSD"  # Without DEX prefix for SDK calls

def fmt(val: Decimal, decs: int) -> str:
    """Format decimal to string with specified decimal places."""
    q = Decimal(10) ** -decs
    return str(val.quantize(q, rounding=ROUND_DOWN))

def get_market_meta(info, dex: str, coin: str):
    """Get market metadata for a specific coin."""
    meta = info.meta(dex=dex)
    universe = meta.get("universe", [])
    name = f"{dex}:{coin}"
    
    for i, asset in enumerate(universe):
        if asset.get("name") == name:
            return meta, asset, i
    
    raise RuntimeError(f"Market {name} not found in {dex} universe.")

def place_seed_orders_loop(exchange, info, reference_price: float = 117000.0, num_iterations: int = 5):
    """Place multiple rounds of buy and sell orders with random spreads."""
    print(f"=== Seeding Order Book for {COIN} with {num_iterations} iterations ===")
    
    # Get market metadata
    try:
        meta, market_asset, asset_idx = get_market_meta(info, DUMMY_DEX, "BTC-FEUSD")
        sz_decimals = market_asset.get("szDecimals", 3)
        print(f"Market asset: {json.dumps(market_asset, indent=2)}")
        print(f"Size decimals: {sz_decimals}")
        print(f"Asset index: {asset_idx}")
    except Exception as e:
        print(f"Error getting market meta: {e}")
        return False
    
    def format_size(size: float) -> str:
        """Format size with correct decimal places."""
        return fmt(Decimal(str(size)), sz_decimals)
    
    print(f"Reference price: {reference_price}")
    
    successful_orders = 0
    total_orders = 0
    
    for iteration in range(num_iterations):
        print(f"\n--- Iteration {iteration + 1}/{num_iterations} ---")
        
        # Generate random spread between 0.5% and 5%
        spread_percent = random.uniform(0.005, 0.05)
        
        # Generate random order size between 0.001 and 0.005
        order_size = random.uniform(0.001, 0.005)
        order_size = round(order_size, 3)  # Round to 3 decimal places
        
        # Add some price variation (±2% around reference)
        price_variation = random.uniform(-0.02, 0.02)
        current_price = reference_price * (1 + price_variation)
        
        bid_price = current_price * (1 - spread_percent / 2)
        ask_price = current_price * (1 + spread_percent / 2)
        
        # Round prices to 2 decimal places
        bid_price = round(bid_price, 2)
        ask_price = round(ask_price, 2)
        
        print(f"Spread: {spread_percent*100:.2f}%, Size: {order_size}")
        print(f"Current price: {current_price:.2f}")
        print(f"Bid price: {bid_price}, Ask price: {ask_price}")
        
        # Place orders using the same method that works
        try:
            # Place buy order (bid)
            print(f"Placing BID: {order_size} @ {bid_price}")
            bid_resp = exchange.order(
                COIN, 
                True,  # is_buy
                order_size, 
                bid_price, 
                {"limit": {"tif": "Gtc"}},  # Good till cancel
            )
            total_orders += 1
            if bid_resp.get("status") == "ok":
                print(f"✓ BID placed successfully")
                successful_orders += 1
            else:
                print(f"✗ BID failed: {bid_resp}")
                
        except Exception as e:
            print(f"✗ BID failed with error: {e}")
            total_orders += 1
        
        # Wait between bid and askAPI_URL=http://localhost:8000
        time.sleep(2)
        
        try:
            # Place sell order (ask)
            print(f"Placing ASK: {order_size} @ {ask_price}")
            ask_resp = exchange.order(
                COIN, 
                False,  # is_buy
                order_size, 
                ask_price, 
                {"limit": {"tif": "Gtc"}},  # Good till cancel
            )
            total_orders += 1
            if ask_resp.get("status") == "ok":
                print(f"✓ ASK placed successfully")
                successful_orders += 1
            else:
                print(f"✗ ASK failed: {ask_resp}")
                
        except Exception as e:
            print(f"✗ ASK failed with error: {e}")
            total_orders += 1
        
        # Wait between iterations
        if iteration < num_iterations - 1:
            wait_time = random.uniform(3, 6)
            print(f"Waiting {wait_time:.1f} seconds before next iteration...")
            time.sleep(wait_time)
    
    print(f"\n=== Order Placement Summary ===")
    print(f"Total orders attempted: {total_orders}")
    print(f"Successful orders: {successful_orders}")
    print(f"Success rate: {(successful_orders/total_orders)*100:.1f}%")
    
    return successful_orders > 0

def place_seed_orders(exchange, info, reference_price: float = 117000.0):
    """Place initial buy and sell orders to seed the order book (original method)."""
    print(f"=== Seeding Order Book for {COIN} ===")
    
    # Get market metadata
    try:
        meta, market_asset, asset_idx = get_market_meta(info, DUMMY_DEX, "BTC-FEUSD")
        sz_decimals = market_asset.get("szDecimals", 3)
        print(f"Market asset: {json.dumps(market_asset, indent=2)}")
        print(f"Size decimals: {sz_decimals}")
        print(f"Asset index: {asset_idx}")
    except Exception as e:
        print(f"Error getting market meta: {e}")
        return False
    
    def format_size(size: float) -> str:
        """Format size with correct decimal places."""
        return fmt(Decimal(str(size)), sz_decimals)
    
    # Define order parameters
    order_size = 0.001  # Small size for testing
    spread_percent = 0.02  # 2% spread
    
    bid_price = reference_price * (1 - spread_percent / 2)
    ask_price = reference_price * (1 + spread_percent / 2)
    
    print(f"Reference price: {reference_price}")
    print(f"Bid price: {bid_price}")
    print(f"Ask price: {ask_price}")
    print(f"Order size: {order_size}")
    
    orders_placed = []
    
    # Method 1: Try SDK order helper with dex parameter
    try:
        print("\nTrying SDK order helper with dex parameter...")
        
        # Place buy order (bid)
        bid_resp = exchange.order(
            COIN, 
            True,  # is_buy
            order_size, 
            bid_price, 
            {"limit": {"tif": "Gtc"}},  # Good till cancel
        )
        print(f"BID order result: {json.dumps(bid_resp, indent=2)}")
        orders_placed.append(("BID", bid_resp))
        
        # Place sell order (ask)
        ask_resp = exchange.order(
            COIN, 
            False,  # is_buy
            order_size, 
            ask_price, 
            {"limit": {"tif": "Gtc"}},  # Good till cancel
        )
        print(f"ASK order result: {json.dumps(ask_resp, indent=2)}")
        orders_placed.append(("ASK", ask_resp))
        
        return True
        
    except TypeError as e:
        print(f"dex parameter not supported: {e}")
    except Exception as e:
        print(f"SDK order helper failed: {e}")
    
    # Method 2: Try SDK order helper without dex parameter
    try:
        print("\nTrying SDK order helper without dex parameter...")
        
        bid_resp = exchange.order(
            COIN, 
            True, 
            order_size, 
            bid_price, 
            {"limit": {"tif": "Gtc"}}
        )
        print(f"BID order result: {json.dumps(bid_resp, indent=2)}")
        orders_placed.append(("BID", bid_resp))
        
        ask_resp = exchange.order(
            COIN, 
            False, 
            order_size, 
            ask_price, 
            {"limit": {"tif": "Gtc"}}
        )
        print(f"ASK order result: {json.dumps(ask_resp, indent=2)}")
        orders_placed.append(("ASK", ask_resp))
        
        return True
        
    except Exception as e:
        print(f"SDK order helper without dex failed: {e}")
    
    # Method 3: Use the working SDK method but with proper error handling
    print("\nUsing working SDK method with proper error handling...")
    
    try:
        # Place buy order (bid) - this worked before
        bid_resp = exchange.order(
            COIN, 
            True,  # is_buy
            order_size, 
            bid_price, 
            {"limit": {"tif": "Gtc"}},  # Good till cancel
        )
        print(f"BID order result: {json.dumps(bid_resp, indent=2)}")
        orders_placed.append(("BID", bid_resp))
        
        # Place sell order (ask) - use the same method
        ask_resp = exchange.order(
            COIN, 
            False,  # is_buy
            order_size, 
            ask_price, 
            {"limit": {"tif": "Gtc"}},  # Good till cancel
        )
        print(f"ASK order result: {json.dumps(ask_resp, indent=2)}")
        orders_placed.append(("ASK", ask_resp))
        
        return True
        
    except Exception as e:
        print(f"SDK order method failed: {e}")
        return False

def check_order_book_after_seeding(info):
    """Check the order book after placing seed orders."""
    print(f"\n=== Checking Order Book After Seeding ===")
    
    # Use the new robust order book reading method
    levels_result = get_order_book_levels(COIN)
    
    if not levels_result["success"]:
        print(f"Error checking order book: {levels_result['error']}")
        return False
    
    bids = levels_result["bids"]
    asks = levels_result["asks"]
    
    print(f"Order book now has {len(bids)} bids and {len(asks)} asks")
    
    if bids:
        print(f"Best bid: {bids[0]}")
    if asks:
        print(f"Best ask: {asks[0]}")
        
    if bids and asks:
        spread = float(asks[0][0]) - float(bids[0][0])
        spread_percent = (spread / float(bids[0][0])) * 100
        print(f"Spread: {spread:.2f} ({spread_percent:.2f}%)")
        
    return len(bids) > 0 and len(asks) > 0

def main():
    """Main function to seed the order book with enhanced loop method."""
    print("HIP-3 Order Book Seeding Tool (Enhanced)")
    print("=" * 50)
    
    # Setup connection
    address, info, exchange = setup(
        base_url=constants.TESTNET_API_URL, skip_ws=True, perp_dexs=[DUMMY_DEX]
    )
    
    print(f"Account: {address}")
    print(f"Target coin: {COIN}")
    
    # Check current order book state using the new robust method
    liquidity_result = check_order_book_liquidity(COIN)
    
    if liquidity_result["success"]:
        print(f"Current order book: {liquidity_result['bid_count']} bids, {liquidity_result['ask_count']} asks")
        
    else:
        print(f"Error checking current order book: {liquidity_result['error']}")
    
    # Ask user for number of iterations
    try:
        num_iterations = int(input("\nHow many iterations of orders to place? (default 5): ") or "5")
    except ValueError:
        num_iterations = 5
    
    print(f"Will place {num_iterations} iterations of bid/ask pairs with random spreads")
    
    # Place seed orders using the enhanced loop method
    success = place_seed_orders_loop(exchange, info, num_iterations=num_iterations)
    
    if success:
        print("\n✓ Seed orders placed successfully!")
        
        # Wait a moment for orders to be processed
        print("Waiting 5 seconds for orders to be processed...")
        time.sleep(5)
        
        # Check order book after seeding
        book_ok = check_order_book_after_seeding(info)
        
        if book_ok:
            print("\n✓ Order book successfully seeded with liquidity!")
            print("You can now run your market making script.")
        else:
            print("\n✗ Order book still appears empty. Check for errors above.")
            
            # Try the original method as fallback
            print("\nTrying original single-order method as fallback...")
            fallback_success = place_seed_orders(exchange, info)
            if fallback_success:
                print("✓ Fallback method succeeded!")
                time.sleep(3)
                check_order_book_after_seeding(info)
    else:
        print("\n✗ Failed to place seed orders. Check errors above.")

if __name__ == "__main__":
    main()
