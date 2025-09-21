#!/usr/bin/env python3
"""
Simple script to update BTC-FEUSD oracle price using HyperEVM contract.
"""

import sys
import os

# Add src to path so we can import our modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

try:
    from src.hip3.hip3_update_oracle_contract import update_btc_feusd_oracle, read_btc_feusd_price
    print("✅ Contract oracle module loaded")
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Missing dependencies? Try: pip install web3 eth_utils")
    sys.exit(1)


def main():
    """Update BTC-FEUSD oracle price"""
    dex = "btcx"  # Change this to your DEX handle
    
    print("🔍 BTC-FEUSD Oracle Updater")
    print("=" * 40)
    
    # First, read the current price from contract
    print("📊 Reading current BTC-FEUSD price from contract...")
    try:
        price_data = read_btc_feusd_price(debug=True)
        btc_data = price_data.get("BTC-FEUSD", {})
        
        if "error" in btc_data:
            print(f"❌ Failed to read price: {btc_data['error']}")
            return 1
        
        price = btc_data['price']
        age_min = btc_data['age_minutes']
        
        print(f"💰 Current BTC-FEUSD price: {price:,.6f}")
        print(f"⏰ Price age: {age_min} minutes")
        
        if age_min > 30:
            print("⚠️  Warning: Price is older than 30 minutes")
        
    except Exception as e:
        print(f"❌ Error reading contract price: {e}")
        return 1
    
    # Now update the oracle
    print(f"\n🔄 Updating oracle for DEX '{dex}'...")
    try:
        result = update_btc_feusd_oracle(dex, debug=True)
        
        if result["status"] == "ok":
            print("✅ Oracle update successful!")
            print(f"💰 Updated price: {result['price']:,.6f} FEUSD per BTC")
            print(f"📍 Mapping: {result['mapping']}")
        elif result["status"] == "noop":
            print(f"ℹ️  No update needed: {result['reason']}")
        else:
            print(f"❌ Oracle update failed: {result['reason']}")
            return 1
            
    except Exception as e:
        print(f"❌ Error updating oracle: {e}")
        return 1
    
    print("\n✅ BTC-FEUSD oracle update completed!")
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
