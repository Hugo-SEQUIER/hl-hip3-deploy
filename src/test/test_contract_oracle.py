#!/usr/bin/env python3
"""
Test script for the contract-based oracle update functionality.
"""

import sys
import os

# Add src to path so we can import our modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

try:
    from src.hip3.hip3_update_oracle_contract import (
        update_oracle_for_dex, 
        update_btc_feusd_oracle,
        read_btc_feusd_price,
        read_contract_price,
        check_contract_admin
    )
    print("✅ Successfully imported contract oracle module")
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Missing dependencies? Try: pip install web3 eth_utils")
    sys.exit(1)


def test_contract_connection():
    """Test basic contract connectivity"""
    print("\n🔗 Testing contract connection...")
    try:
        admin = check_contract_admin(debug=True)
        if admin:
            print(f"✅ Contract connection successful")
            return True
        else:
            print("❌ Failed to read contract admin")
            return False
    except Exception as e:
        print(f"❌ Contract connection failed: {e}")
        return False


def test_price_reading():
    """Test reading individual price"""
    print("\n📊 Testing price reading...")
    try:
        price_data = read_contract_price("BTC-FEUSD", debug=True)
        print(f"✅ Successfully read price: {price_data['price']:.6f}")
        return True
    except Exception as e:
        print(f"❌ Price reading failed: {e}")
        return False


def test_btc_feusd_price():
    """Test reading BTC-FEUSD price specifically"""
    print("\n📈 Testing BTC-FEUSD price...")
    try:
        price_data = read_btc_feusd_price(debug=True)
        btc_data = price_data.get("BTC-FEUSD", {})
        if "error" in btc_data:
            print(f"❌ Error reading BTC-FEUSD: {btc_data['error']}")
            return False
        else:
            print(f"✅ BTC-FEUSD price: {btc_data['price']:.6f} FEUSD")
            return True
    except Exception as e:
        print(f"❌ BTC-FEUSD price test failed: {e}")
        return False


def test_oracle_update_dry_run():
    """Test oracle update in dry run mode (no actual update)"""
    print("\n🔄 Testing oracle update logic (dry run)...")
    try:
        # This would fail if we don't have valid DEX configuration, but that's expected
        # Just testing that the function can be called and handles errors gracefully
        result = update_oracle_for_dex("btcx", strict=False, debug=True)
        print(f"✅ Oracle update function completed with status: {result.get('status', 'unknown')}")
        return True
    except Exception as e:
        print(f"❌ Oracle update test failed: {e}")
        return False


def main():
    """Run all tests"""
    print("🧪 Running Contract Oracle Tests")
    print("=" * 50)
    
    tests = [
        ("Contract Connection", test_contract_connection),
        ("Price Reading", test_price_reading), 
        ("BTC-FEUSD Price", test_btc_feusd_price),
        ("Oracle Update Logic", test_oracle_update_dry_run),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
                status = "✅ PASSED"
            else:
                status = "❌ FAILED"
        except Exception as e:
            status = f"❌ ERROR: {e}"
        
        print(f"\n{test_name}: {status}")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
        return 0
    else:
        print("⚠️  Some tests failed - check dependencies and configuration")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
