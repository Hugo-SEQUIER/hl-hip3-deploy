# Price Computation (`src/compute/`)

This module handles advanced price computation and stablecoin FX resolution logic for converting BTC/USD prices into BTC/stablecoin pairs.

## Overview

The computation module provides sophisticated algorithms for resolving stablecoin-to-USD conversion factors using multiple data sources and fallback strategies. This is essential for accurate price conversion when direct trading pairs are not available.

## Files

### `stable_fx.py`
Core stablecoin FX resolution with intelligent fallback strategies.

## Key Functions

### `resolve_stable_usd_factor()`
Main function for resolving stablecoin-to-USD conversion factors.

**Parameters:**
- `info`: Hyperliquid Info instance
- `symbol`: Stablecoin symbol (e.g., "FEUSD", "USDHL")
- `preferred_quotes`: List of preferred quote currencies
- `evm_addresses`: HyperEVM token addresses for DexScreener fallback
- `evm_usd_reference`: Reference token for USD conversion

**Returns:** `float` - Conversion factor (stablecoin/USD)

## Fallback Strategy

The resolution follows a three-tier fallback approach:

### 1. Hyperliquid Spot Markets (Primary)
- Attempts to find direct trading pairs on HL spot
- Tries preferred quotes in order: USDT0 → USDHL → FEUSD
- Uses real-time order book mid-prices
- Most accurate when pairs exist

### 2. DexScreener HyperEVM (Secondary)
- Falls back to DexScreener API for HyperEVM pairs
- Uses provided token addresses for lookup
- Selects highest liquidity pools
- Handles both direct and inverted price orientations

### 3. Peg Value (Tertiary)
- Defaults to 1.0 (peg assumption)
- Used when all other sources fail
- Logged for monitoring purposes
- Ensures system continues operating

## Usage Example

```python
from src.compute.stable_fx import resolve_stable_usd_factor
from hyperliquid.info import Info

# Setup
info = Info(API_URL, skip_ws=True)
evm_addresses = {
    "USDHL": "0xd289c79872a9eace15cc4cadb030661f",
    "FEUSD": "0x88102bea0bbad5f301f6e9e4dacdf979",
    "USDC": "0x6d1e7cde53ba9467b783cb7c530ce054"
}

# Resolve FX factors
feusd_factor = resolve_stable_usd_factor(
    info, 
    "FEUSD", 
    evm_addresses=evm_addresses,
    evm_usd_reference="USDC"
)

usdhl_factor = resolve_stable_usd_factor(
    info, 
    "USDHL", 
    evm_addresses=evm_addresses,
    evm_usd_reference="USDC"
)
```

## Price Conversion Logic

### BTC Price Conversion
```python
# Given: BTC/USD price and stablecoin/USD factor
btc_usd_price = 65000.0
stable_usd_factor = 0.9998  # FEUSD/USD

# Calculate: BTC/stablecoin price
btc_stable_price = btc_usd_price / stable_usd_factor
# Result: 65013.0 BTC/FEUSD
```

### Supported Stablecoins
- **FEUSD**: First Exchange USD
- **USDHL**: Hyperliquid USD
- **USDT0**: Tether USD
- **USDC**: USD Coin (reference)

## Error Handling

### Graceful Degradation
- Each fallback level handles its own errors
- System continues operating even with partial failures
- Comprehensive error logging for debugging

### Common Error Scenarios
1. **No HL Spot Pairs**: Falls back to DexScreener
2. **DexScreener Unavailable**: Uses peg value (1.0)
3. **Invalid Token Addresses**: Skips DexScreener, uses peg
4. **Network Timeouts**: Retries with exponential backoff

### Monitoring
- Log all fallback decisions
- Track accuracy of different sources
- Monitor peg usage frequency

## Configuration

### Preferred Quotes Order
```python
preferred_quotes = ["USDT0", "USDHL", "FEUSD"]
```
- USDT0: Most liquid and stable
- USDHL: Native Hyperliquid stablecoin
- FEUSD: Alternative stablecoin option

### HyperEVM Addresses
```python
EVM_ADDR = {
    "USDHL": "0xd289c79872a9eace15cc4cadb030661f",
    "FEUSD": "0x88102bea0bbad5f301f6e9e4dacdf979",
    "USDT0": "0x25faedc3f054130dbb4e4203aca63567",
    "USDC": "0x6d1e7cde53ba9467b783cb7c530ce054"
}
```

## Performance Considerations

### Caching
- FX factors can be cached for short periods
- Reduces API calls and improves performance
- Consider 30-60 second cache intervals

### Rate Limiting
- Respects API rate limits for all sources
- Implements retry logic with backoff
- Prioritizes most accurate sources

### Reliability
- Multiple fallback sources ensure uptime
- Graceful handling of individual source failures
- Maintains price updates even with degraded accuracy

## Testing

### Unit Tests
```python
# Test with known values
def test_fx_resolution():
    factor = resolve_stable_usd_factor(info, "USDC")
    assert abs(factor - 1.0) < 0.01  # Should be close to 1.0
```

### Integration Tests
- Test with real API endpoints
- Verify fallback behavior
- Monitor accuracy across sources

## Troubleshooting

### Common Issues
1. **All Sources Fail**: Check network connectivity and API keys
2. **Inaccurate Prices**: Verify token addresses and preferred quotes
3. **Frequent Peg Usage**: May indicate missing trading pairs

### Debug Steps
1. Enable detailed logging
2. Test individual price sources
3. Verify token addresses and configurations
4. Check network connectivity and API status
