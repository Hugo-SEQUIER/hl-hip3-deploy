# HL-HIP3-Deploy

A comprehensive toolkit for deploying and managing HIP-3 (Hyperliquid Improvement Proposal 3) DEXes and executing oracle price updates on the Hyperliquid protocol.

## Overview

This repository provides tools to:
- Deploy HIP-3 DEXes with custom collateral tokens
- Execute oracle price updates using multiple price sources
- Manage stablecoin price factors and cross-currency conversions
- Integrate with RedStone oracles and Hyperliquid spot markets

## Repository Structure

```
├── main.py                    # Example scripts and testing utilities
├── src/
│   ├── hip3/                 # HIP-3 deployment and configuration
│   ├── compute/              # Price computation and stablecoin FX resolution
│   ├── prices/               # Price data sources (RedStone, HL Spot, DexScreener)
│   └── hl_utils/             # Hyperliquid utilities and configuration
└── README.md                 # This file
```

## Key Features

### 🚀 HIP-3 DEX Deployment
- Deploy multiple DEXes with different collateral tokens
- Register assets with custom configurations
- Manage oracle updater permissions

### 📊 Multi-Source Price Data
- **RedStone Integration**: Robust price feeds with fallback endpoints
- **Hyperliquid Spot**: Direct integration with HL spot markets
- **DexScreener**: HyperEVM price data via DexScreener API

### 💱 Stablecoin FX Resolution
- Automatic stablecoin-to-USD factor resolution
- Fallback strategies: HL Spot → DexScreener → Peg (1.0)
- Support for multiple stablecoins (FEUSD, USDHL, USDT0, USDC)

### 🔄 Oracle Management
- Automated oracle price updates
- BTC price conversion across different stablecoin pairs
- Configurable update intervals and retry logic

## Quick Start

### Prerequisites
- Python 3.8+
- Hyperliquid account with API access
- Required Python packages (see requirements)

### Configuration
1. Copy `src/hl_utils/config_example.json` to `src/hl_utils/config.json`
2. Configure your wallet credentials and network settings
3. Update `src/hip3/hip3_config.py` with your DEX specifications

### Basic Usage

#### Deploy HIP-3 DEXes
```bash
python src/hip3/hip3_deploy.py
```

#### Update Oracle Prices
```bash
python src/hip3/hip3_update_oracle.py
```

#### Test Price Feeds
```bash
python main.py
```

## Configuration

### DEX Configuration (`src/hip3/hip3_config.py`)
- Define DEX specifications with collateral tokens
- Set margin table IDs and asset parameters
- Configure HyperEVM token addresses for fallback pricing

### Wallet Configuration (`src/hl_utils/config.json`)
- Set up API credentials
- Configure network endpoints (mainnet/testnet)
- Manage multi-sig wallet settings

## Price Sources

### 1. RedStone Oracle
- Primary BTC/USD price source
- Multiple endpoint fallbacks for reliability
- Real-time price updates

### 2. Hyperliquid Spot Markets
- Direct integration with HL spot trading pairs
- Real-time order book data
- Mid-price calculation from best bid/ask

### 3. DexScreener (HyperEVM)
- Fallback pricing for stablecoins
- HyperEVM token address integration
- Liquidity-based pool selection

## Supported Assets

### Base Assets
- **BTC**: Bitcoin (primary trading asset)

### Collateral Tokens
- **FEUSD**: First Exchange USD
- **USDHL**: Hyperliquid USD
- **USDT0**: Tether USD
- **USDC**: USD Coin

## Error Handling

- Exponential backoff for API failures
- Multiple endpoint fallbacks
- Graceful degradation to peg values
- Comprehensive error logging

## Development

### Testing
Run example scripts in `main.py` to test different components:
- Token ID resolution
- Price feed fetching
- Spot pair discovery
- FX factor calculation

### Adding New Price Sources
1. Implement in `src/prices/`
2. Add to `src/compute/stable_fx.py`
3. Update configuration as needed

## Security Considerations

- Private keys stored securely in configuration
- API rate limiting and retry logic
- Input validation for all price data
- Fallback mechanisms for price failures

## License

This project is provided as-is for educational and development purposes. Please review all code before use in production environments.

## Support

For issues and questions:
1. Check the configuration files
2. Review error logs and console output
3. Test individual components using `main.py`
4. Verify network connectivity and API access
