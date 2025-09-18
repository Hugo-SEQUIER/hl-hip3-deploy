# HIP-3 Management (`src/hip3/`)

This module handles all aspects of HIP-3 (Hyperliquid Improvement Proposal 3) DEX deployment and oracle management on the Hyperliquid protocol.

## Overview

HIP-3 enables the creation of custom DEXes with different collateral tokens, allowing for more flexible trading pairs and risk management. This module provides the tools to deploy, configure, and maintain these DEXes.

## Files

### `hip3_config.py`
Central configuration file for all HIP-3 operations.

**Key Configuration:**
- **Network Settings**: API URLs for mainnet/testnet
- **DEX Specifications**: Collateral tokens, margin tables, asset parameters
- **HyperEVM Addresses**: Token addresses for fallback pricing
- **Gas Limits**: Perp deploy auction gas caps

**Example DEX Configuration:**
```python
DEX_SPECS = [
    {
        "dex": "FEUSDx",
        "full_name": "BTC vs FEUSD",
        "collateral_symbol": "FEUSD",
        "margin_table_id": 10,
        "assets": [
            {"coin": "BTC-FEUSD", "sz_decimals": 3, "initial_oracle_px": "65000.0"}
        ]
    }
]
```

### `hip3_deploy.py`
Deploy HIP-3 DEXes and register assets.

**Features:**
- Create new DEXes with custom collateral tokens
- Register trading assets with specified parameters
- Handle retry logic for API failures
- Validate collateral token availability

**Usage:**
```bash
python src/hip3/hip3_deploy.py
```

**Process:**
1. Connect to Hyperliquid API
2. Resolve collateral token indices
3. Create DEX via first asset registration
4. Register additional assets
5. Verify deployment success

### `hip3_update_oracle.py`
Execute oracle price updates for deployed DEXes.

**Features:**
- Fetch BTC/USD prices from RedStone
- Calculate stablecoin FX factors
- Convert BTC prices to stablecoin pairs
- Push updates to DEX oracles

**Usage:**
```bash
python src/hip3/hip3_update_oracle.py
```

**Process:**
1. Fetch BTC/USD from RedStone
2. Resolve stablecoin/USD factors
3. Calculate BTC/stablecoin prices
4. Update each DEX oracle
5. Handle errors and retries

### `token_ids.py`
Token resolution and mapping utilities.

**Functions:**
- `get_api_url()` - Resolve API endpoints by network
- `build_token_index_map()` - Create token name to index mapping
- `resolve_tokens()` - Resolve token names with aliases

**Features:**
- Case-insensitive token resolution
- Alias support for token variations
- Integration with Hyperliquid spot metadata

## DEX Lifecycle

### 1. Configuration
- Define DEX specifications in `hip3_config.py`
- Set collateral tokens and asset parameters
- Configure HyperEVM addresses for fallbacks

### 2. Deployment
- Run `hip3_deploy.py` to create DEXes
- First asset registration creates the DEX
- Additional assets registered separately

### 3. Oracle Management
- Run `hip3_update_oracle.py` for price updates
- Supports multiple price sources
- Automatic fallback mechanisms

### 4. Monitoring
- Check DEX metadata via `info.meta(dex=dex_name)`
- Monitor oracle prices and updates
- Validate collateral token availability

## Supported Collateral Tokens

- **FEUSD**: First Exchange USD
- **USDHL**: Hyperliquid USD  
- **USDT0**: Tether USD
- **USDC**: USD Coin

## Error Handling

- **API Failures**: Exponential backoff with retries
- **Token Resolution**: Graceful handling of missing tokens
- **Oracle Updates**: Individual DEX error isolation
- **Network Issues**: Automatic endpoint fallbacks

## Security Considerations

- **Oracle Updater**: Only configured address can update prices
- **Gas Limits**: Configurable gas caps for deployment
- **Input Validation**: All parameters validated before submission
- **Error Logging**: Comprehensive logging for debugging

## Configuration Examples

### Basic DEX Setup
```python
DEX_SPECS = [
    {
        "dex": "BTCx",
        "full_name": "BTC Trading DEX",
        "collateral_symbol": "USDC",
        "margin_table_id": 10,
        "assets": [
            {"coin": "BTC-USDC", "sz_decimals": 3, "initial_oracle_px": "65000.0"}
        ]
    }
]
```

### Multi-Asset DEX
```python
DEX_SPECS = [
    {
        "dex": "MULTIx",
        "full_name": "Multi-Asset DEX",
        "collateral_symbol": "USDT0",
        "margin_table_id": 10,
        "assets": [
            {"coin": "BTC-USDT0", "sz_decimals": 3, "initial_oracle_px": "65000.0"},
            {"coin": "ETH-USDT0", "sz_decimals": 2, "initial_oracle_px": "3000.0"}
        ]
    }
]
```

## Troubleshooting

### Common Issues
1. **Token Not Found**: Verify token exists in spot metadata
2. **Deployment Fails**: Check gas limits and network status
3. **Oracle Updates Fail**: Verify price sources and FX factors
4. **Permission Denied**: Ensure correct oracle updater address

### Debug Steps
1. Check DEX metadata: `info.meta(dex="DEX_NAME")`
2. Verify token indices: `info.spot_meta()`
3. Test price sources individually
4. Review error logs and console output
