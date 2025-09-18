# Hyperliquid Utilities (`src/hl_utils/`)

This module provides essential utilities and configuration management for Hyperliquid protocol integration.

## Overview

The `hl_utils` module contains common utilities, configuration templates, and helper functions that are used across the entire HIP-3 deployment system. It handles wallet management, network configuration, and provides reusable setup functions.

## Files

### `example_utils.py`
Core utility functions for Hyperliquid integration.

**Key Functions:**
- `setup()` - Main setup function for wallet and API connections
- `get_secret_key()` - Secure key retrieval from config or keystore
- `setup_multi_sig_wallets()` - Multi-signature wallet configuration

**Features:**
- Support for both private key and keystore authentication
- Multi-signature wallet support
- Account validation and balance checking
- Automatic address resolution

### `config.json`
Active configuration file for wallet and network settings.

**Configuration Structure:**
```json
{
    "account_address": "0x...",
    "secret_key": "0x...",
    "keystore_path": "path/to/keystore.json",
    "multi_sig": {
        "authorized_users": [
            {
                "account_address": "0x...",
                "secret_key": "0x..."
            }
        ]
    }
}
```

### `config_example.json`
Template configuration file with examples and documentation.

**Usage:**
1. Copy `config_example.json` to `config.json`
2. Fill in your actual credentials
3. Update network settings as needed

## Setup Functions

### `setup(base_url=None, skip_ws=False, perp_dexs=None)`
Main setup function that returns configured Hyperliquid objects.

**Parameters:**
- `base_url`: API endpoint URL (defaults to config)
- `skip_ws`: Skip WebSocket connections (default: False)
- `perp_dexs`: Perpetual DEX configurations

**Returns:**
- `address`: Account address
- `info`: Hyperliquid Info instance
- `exchange`: Hyperliquid Exchange instance

**Usage:**
```python
from src.hl_utils.example_utils import setup

# Basic setup
address, info, exchange = setup()

# Custom API URL
address, info, exchange = setup(base_url="https://api.hyperliquid.xyz")

# Skip WebSocket
address, info, exchange = setup(skip_ws=True)
```

### `get_secret_key(config)`
Secure key retrieval with multiple authentication methods.

**Authentication Methods:**
1. **Direct Private Key**: Stored in config file
2. **Keystore File**: Encrypted keystore with password prompt
3. **Environment Variables**: External key management

**Security Features:**
- Password-protected keystore support
- Secure key handling
- Input validation and error handling

### `setup_multi_sig_wallets()`
Configure multi-signature wallet support.

**Features:**
- Multiple authorized users
- Individual key management
- Address validation
- Batch wallet loading

**Usage:**
```python
from src.hl_utils.example_utils import setup_multi_sig_wallets

# Load multi-sig wallets
wallets = setup_multi_sig_wallets()
```

## Configuration Management

### Wallet Configuration
```json
{
    "account_address": "0x1234...",
    "secret_key": "0xabcd...",
    "keystore_path": "keystore.json"
}
```

### Multi-Signature Configuration
```json
{
    "multi_sig": {
        "authorized_users": [
            {
                "account_address": "0x1111...",
                "secret_key": "0xaaaa..."
            },
            {
                "account_address": "0x2222...",
                "secret_key": "0xbbbb..."
            }
        ]
    }
}
```

### Network Configuration
- **Mainnet**: `https://api.hyperliquid.xyz`
- **Testnet**: `https://api.hyperliquid-testnet.xyz`
- **Custom**: Any valid Hyperliquid API endpoint

## Security Features

### Key Management
- **Keystore Support**: Encrypted private key storage
- **Password Protection**: Secure key decryption
- **Environment Variables**: External key management
- **Input Validation**: Secure parameter handling

### Account Validation
- **Balance Checking**: Verifies account has sufficient funds
- **Address Validation**: Ensures correct account addresses
- **Permission Checking**: Validates oracle updater permissions

### Error Handling
- **Secure Error Messages**: No sensitive data in error logs
- **Graceful Failures**: Proper error handling and recovery
- **Input Sanitization**: Prevents injection attacks

## Usage Examples

### Basic Setup
```python
from src.hl_utils.example_utils import setup

# Load configuration and setup
address, info, exchange = setup()
print(f"Connected as: {address}")

# Check account balance
user_state = info.user_state(address)
print(f"Account value: {user_state['marginSummary']['accountValue']}")
```

### Custom Configuration
```python
from src.hl_utils.example_utils import setup

# Use custom API endpoint
address, info, exchange = setup(base_url="https://api.hyperliquid.xyz")

# Skip WebSocket for faster setup
address, info, exchange = setup(skip_ws=True)
```

### Multi-Signature Setup
```python
from src.hl_utils.example_utils import setup_multi_sig_wallets

# Load multi-sig wallets
wallets = setup_multi_sig_wallets()
print(f"Loaded {len(wallets)} authorized wallets")
```

## Error Handling

### Common Errors
1. **Invalid Configuration**: Missing or malformed config file
2. **Authentication Failure**: Invalid private key or keystore
3. **Network Issues**: API endpoint unreachable
4. **Insufficient Funds**: Account has no balance

### Error Recovery
- **Configuration Validation**: Checks config file format
- **Key Validation**: Verifies private key format
- **Network Retry**: Automatic retry for network issues
- **Balance Checking**: Warns about insufficient funds

## Best Practices

### Security
- **Never commit `config.json`**: Use `.gitignore` to exclude
- **Use keystore files**: More secure than direct private keys
- **Rotate keys regularly**: Update private keys periodically
- **Monitor access**: Log all wallet access attempts

### Configuration
- **Use `config_example.json`**: Copy and modify for your setup
- **Validate addresses**: Ensure correct account addresses
- **Test configurations**: Verify setup before production use
- **Backup keys**: Secure backup of private keys and keystores

### Development
- **Environment separation**: Different configs for testnet/mainnet
- **Error logging**: Comprehensive error logging for debugging
- **Input validation**: Validate all configuration parameters
- **Documentation**: Keep configuration examples updated

## Troubleshooting

### Common Issues
1. **Config File Missing**: Copy `config_example.json` to `config.json`
2. **Invalid Private Key**: Check key format and validity
3. **Keystore Issues**: Verify file path and password
4. **Network Errors**: Check API endpoint and connectivity

### Debug Steps
1. Verify configuration file format
2. Test private key validity
3. Check network connectivity
4. Validate account addresses
5. Review error logs for details

### Support
- Check Hyperliquid documentation for API changes
- Verify network status and endpoint availability
- Review configuration examples and templates
- Test with testnet before mainnet deployment
