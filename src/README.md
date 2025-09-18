# Source Code (`src/`)

This directory contains the core implementation modules for the HL-HIP3-Deploy toolkit.

## Module Overview

### 📁 `hip3/` - HIP-3 Deployment & Management
Core functionality for deploying and managing HIP-3 DEXes on Hyperliquid.

**Key Files:**
- `hip3_config.py` - Central configuration for DEX specifications
- `hip3_deploy.py` - DEX deployment and asset registration
- `hip3_update_oracle.py` - Oracle price update execution
- `token_ids.py` - Token resolution and mapping utilities

### 📁 `compute/` - Price Computation
Advanced price calculation and stablecoin FX resolution logic.

**Key Files:**
- `stable_fx.py` - Stablecoin-to-USD factor resolution with fallback strategies

### 📁 `prices/` - Price Data Sources
Integration with multiple price data providers and market sources.

**Key Files:**
- `redstone_prices.py` - RedStone oracle integration
- `hl_spot_prices.py` - Hyperliquid spot market integration
- `hyper_evm_prices.py` - DexScreener integration for HyperEVM

### 📁 `hl_utils/` - Hyperliquid Utilities
Common utilities and configuration management for Hyperliquid integration.

**Key Files:**
- `example_utils.py` - Wallet setup and connection utilities
- `config.json` - Wallet and network configuration
- `config_example.json` - Configuration template

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Price Sources │    │   Computation   │    │   HIP-3 Mgmt    │
│                 │    │                 │    │                 │
│ • RedStone      │───▶│ • Stable FX     │───▶│ • DEX Deploy    │
│ • HL Spot       │    │ • Price Calc    │    │ • Oracle Update │
│ • DexScreener   │    │ • Fallbacks     │    │ • Config Mgmt   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Data Flow

1. **Price Fetching**: Multiple sources provide price data
2. **FX Resolution**: Stablecoin factors calculated with fallbacks
3. **Price Computation**: BTC prices converted to stablecoin pairs
4. **Oracle Updates**: Prices pushed to HIP-3 DEX oracles

## Dependencies

- `hyperliquid` - Official Hyperliquid Python SDK
- `requests` - HTTP client for API calls
- `eth_account` - Ethereum account management
- `json` - Configuration and data serialization

## Error Handling

Each module implements:
- Retry logic with exponential backoff
- Graceful fallback mechanisms
- Comprehensive error logging
- Input validation and sanitization

## Configuration

All modules read from centralized configuration:
- `hip3_config.py` - DEX and network settings
- `hl_utils/config.json` - Wallet credentials and API endpoints

## Testing

Use `main.py` in the root directory to test individual modules:
- Token resolution testing
- Price feed validation
- FX factor calculation
- End-to-end deployment flows
