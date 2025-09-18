# Price Data Sources (`src/prices/`)

This module provides integration with multiple price data sources to ensure reliable and accurate price feeds for HIP-3 oracle updates.

## Overview

The prices module implements robust integrations with various price data providers, each offering different advantages and use cases. The system is designed with redundancy and fallback mechanisms to ensure continuous price availability.

## Files

### `redstone_prices.py`
Integration with RedStone oracle network for BTC/USD and other major asset prices.

**Features:**
- Multiple endpoint fallbacks for high availability
- Batch and individual symbol queries
- Automatic payload normalization
- Exponential backoff retry logic

**Key Functions:**
- `fetch_redstone_prices()` - Main function for price fetching
- `_try_redstone_endpoint()` - Single endpoint attempt
- `_normalize_rs_payload()` - Payload format normalization

**Endpoints:**
```python
REDSTONE_PRICE_ENDPOINTS = [
    "https://api.redstone.finance/prices",
    "https://oracle-gateway-1.a.redstone.finance/prices",
    "https://oracle-gateway-2.a.redstone.finance/prices"
]
```

### `hl_spot_prices.py`
Direct integration with Hyperliquid spot markets for real-time price data.

**Features:**
- Real-time order book data
- Mid-price calculation from best bid/ask
- Token pair discovery and mapping
- Debug utilities for market inspection

**Key Functions:**
- `get_spot_mid()` - Calculate mid price for base/quote pair
- `find_spot_pair_index()` - Locate pair index in spot universe
- `get_stable_usd_factors()` - Convenience function for stablecoin factors
- `list_spot_pairs_for_token()` - Discover available pairs for a token

**Usage:**
```python
from src.prices.hl_spot_prices import get_spot_mid

# Get BTC/USDC mid price
btc_usdc_price = get_spot_mid(info, "BTC", "USDC")

# Get stablecoin USD factors
factors = get_stable_usd_factors(info)
```

### `hyper_evm_prices.py`
Integration with DexScreener for HyperEVM token price data.

**Features:**
- HyperEVM token address integration
- Liquidity-based pool selection
- Support for direct and inverted price orientations
- Fallback to highest liquidity pools

**Key Functions:**
- `get_pair_mid_from_dexscreener()` - Get mid price for token pair
- `_load_pairs_for_token()` - Load all pairs for a token

**Usage:**
```python
from src.prices.hyper_evm_prices import get_pair_mid_from_dexscreener

# Get FEUSD/USDC price on HyperEVM
feusd_usdc_price = get_pair_mid_from_dexscreener(
    "0x88102bea0bbad5f301f6e9e4dacdf979",  # FEUSD address
    "0x6d1e7cde53ba9467b783cb7c530ce054"   # USDC address
)
```

## Price Source Hierarchy

### 1. RedStone Oracle (Primary for BTC/USD)
- **Advantages**: High reliability, multiple endpoints, real-time updates
- **Use Case**: Primary BTC/USD price source
- **Fallback**: Multiple gateway endpoints with retry logic

### 2. Hyperliquid Spot (Primary for Stablecoins)
- **Advantages**: Native integration, real-time data, high accuracy
- **Use Case**: Stablecoin/USD factors when pairs exist
- **Fallback**: DexScreener for missing pairs

### 3. DexScreener HyperEVM (Fallback)
- **Advantages**: Broad coverage, HyperEVM integration
- **Use Case**: Fallback for stablecoin pricing
- **Fallback**: Peg value (1.0) if all sources fail

## Data Flow

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   RedStone      │    │   HL Spot       │    │   DexScreener   │
│                 │    │                 │    │                 │
│ • BTC/USD       │    │ • Stable/USD    │    │ • Stable/USD    │
│ • Multiple      │    │ • Real-time     │    │ • HyperEVM      │
│   Endpoints     │    │ • Order Book    │    │ • Fallback      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   Price         │
                    │   Resolution    │
                    │                 │
                    │ • Fallback      │
                    │ • Validation    │
                    │ • Conversion    │
                    └─────────────────┘
```

## Error Handling

### RedStone Integration
- **Multiple Endpoints**: Automatic failover between gateways
- **Retry Logic**: Exponential backoff with configurable attempts
- **Payload Normalization**: Handles different response formats
- **Timeout Handling**: Configurable timeouts per request

### Hyperliquid Spot
- **Pair Discovery**: Validates pair existence before querying
- **Order Book Validation**: Checks for sufficient liquidity
- **Token Resolution**: Handles case-sensitive token names
- **API Errors**: Graceful handling of API failures

### DexScreener Integration
- **Pool Selection**: Chooses highest liquidity pools
- **Orientation Handling**: Supports both direct and inverted prices
- **Address Validation**: Verifies token addresses before querying
- **Rate Limiting**: Respects API rate limits

## Configuration

### RedStone Settings
```python
REDSTONE_PRICE_ENDPOINTS = [
    "https://api.redstone.finance/prices",
    "https://oracle-gateway-1.a.redstone.finance/prices",
    "https://oracle-gateway-2.a.redstone.finance/prices"
]

# Retry configuration
retries = 4
retry_base_delay = 0.5
timeout_secs = 4.0
```

### HyperEVM Addresses
```python
EVM_ADDR = {
    "USDHL": "0xd289c79872a9eace15cc4cadb030661f",
    "FEUSD": "0x88102bea0bbad5f301f6e9e4dacdf979",
    "USDT0": "0x25faedc3f054130dbb4e4203aca63567",
    "USDC": "0x6d1e7cde53ba9467b783cb7c530ce054"
}
```

## Performance Optimization

### Caching
- Price data can be cached for short intervals
- Reduces API calls and improves response times
- Consider 30-60 second cache intervals

### Parallel Requests
- Multiple endpoints can be queried simultaneously
- Reduces total latency for price resolution
- Improves overall system responsiveness

### Rate Limiting
- Respects API rate limits for all providers
- Implements intelligent retry strategies
- Prioritizes most reliable sources

## Testing

### Unit Tests
```python
# Test RedStone integration
def test_redstone_prices():
    prices = fetch_redstone_prices(["BTC", "ETH"])
    assert "BTC" in prices
    assert "ETH" in prices
    assert prices["BTC"]["value"] > 0

# Test HL Spot integration
def test_hl_spot_prices():
    price = get_spot_mid(info, "BTC", "USDC")
    assert price > 0
```

### Integration Tests
- Test with real API endpoints
- Verify fallback behavior
- Monitor accuracy and reliability

## Monitoring

### Key Metrics
- **Success Rate**: Percentage of successful price fetches
- **Latency**: Response times for each source
- **Fallback Usage**: Frequency of fallback source usage
- **Accuracy**: Price accuracy compared to reference sources

### Alerts
- API endpoint failures
- Frequent fallback usage
- Price anomalies or outliers
- Network connectivity issues

## Troubleshooting

### Common Issues
1. **RedStone Failures**: Check network connectivity and endpoint status
2. **HL Spot Errors**: Verify token names and pair existence
3. **DexScreener Issues**: Validate token addresses and API access
4. **Price Anomalies**: Check for market manipulation or API errors

### Debug Steps
1. Enable detailed logging for all sources
2. Test individual price sources separately
3. Verify network connectivity and API keys
4. Check for rate limiting or quota issues
5. Monitor error logs and retry patterns
