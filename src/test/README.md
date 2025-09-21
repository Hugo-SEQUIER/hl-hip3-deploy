# Test Module

This module contains test scripts for testing HIP-3 deployed markets.

## Files

- `test_btcx_order.py` - Test script for placing orders on the BTCX:BTC-FEUSD market

## Usage

### Testing BTCX:BTC-FEUSD Orders

To test placing orders on your deployed BTCX:BTC-FEUSD market:

```bash
# From the project root directory
python src/test/test_btcx_order.py
```

This script will:

1. **Connect to Hyperliquid Testnet** using your configured wallet
2. **Find the BTC-FEUSD asset ID** in the BTCX DEX
3. **Place a test limit order** (buy 0.001 BTC at $50,000 - should rest since price is low)
4. **Query the order status** to confirm it was placed
5. **Cancel the test order** after 5 seconds
6. **Place a small market order** (buy 0.0001 BTC at market price)

### Prerequisites

1. **Configure your wallet** in `src/hl_utils/config.json`:
   ```json
   {
       "account_address": "0x...",
       "secret_key": "0x...",
       "keystore_path": "",
       "multi_sig": {
           "authorized_users": []
       }
   }
   ```

2. **Ensure you have testnet funds** in your wallet for testing

3. **Make sure your BTCX DEX is deployed** and the BTC-FEUSD asset is registered

### Order Types Tested

- **Limit Orders**: Orders that rest on the book at a specific price
- **Market Orders**: Orders that execute immediately at the best available price

### Time-in-Force (TIF) Options

The script uses `GTC` (Good Till Canceled) for limit orders, but you can modify it to test:
- `ALO` (Add Liquidity Only) - Post-only, cancels if it would match immediately
- `IOC` (Immediate or Cancel) - Cancels unfilled portion instead of resting
- `GTC` (Good Till Canceled) - No special behavior, stays on book until filled or canceled

### Customization

You can modify the test parameters in the script:
- `test_price`: Price for limit orders
- `test_size`: Order size
- `asset_id`: Asset to trade (automatically detected for BTC-FEUSD)

### Error Handling

The script includes comprehensive error handling and will show:
- Connection status
- Asset ID resolution
- Order placement results
- Order status queries
- Cancel results

### Example Output

```
=== BTCX:BTC-FEUSD Order Testing ===
Connected with address: 0x...
BTC-FEUSD asset ID: 123

Placing test order:
  Asset: BTC-FEUSD (ID: 123)
  Side: BUY
  Size: 0.001
  Price: 50000.0
  TIF: GTC (Good Till Canceled)

Order placed successfully! Order ID: 77738308
```
