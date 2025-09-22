#!/usr/bin/env python3
"""
BTC-FEUSD Oracle Loop Script

A VM-ready script that continuously updates BTC-FEUSD oracle prices.
Designed to run as a long-running service with proper error handling,
logging, and graceful shutdown capabilities.

Usage:
    python btc_feusd_oracle_loop.py [options]

Features:
- Configurable update intervals
- Comprehensive logging
- Error handling with exponential backoff
- Graceful shutdown on SIGTERM/SIGINT
- Price staleness detection
- Rate limiting protection
"""

import sys
import os
import time
import signal
import logging
import argparse
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

# Add src to path so we can import our modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

try:
    from src.hip3.hip3_update_oracle_contract import update_btc_feusd_oracle, read_btc_feusd_price
    print("✅ Contract oracle module loaded")
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Missing dependencies? Try: pip install web3 eth_utils")
    sys.exit(1)


class BTCFeusdOracleLoop:
    """Main class for the BTC-FEUSD oracle update loop"""
    
    def __init__(self, dex: str = "btcx", interval: int = 60, max_price_age: int = 30, 
                 log_level: str = "INFO", log_file: Optional[str] = None):
        """
        Initialize the oracle loop
        
        Args:
            dex: DEX handle (e.g., 'btcx')
            interval: Update interval in seconds
            max_price_age: Maximum acceptable price age in minutes
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
            log_file: Optional log file path
        """
        self.dex = dex
        self.interval = interval
        self.max_price_age = max_price_age
        self.running = True
        self.update_count = 0
        self.error_count = 0
        self.last_successful_update = None
        self.consecutive_errors = 0
        self.max_consecutive_errors = 5
        
        # Setup logging
        self._setup_logging(log_level, log_file)
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        self.logger.info(f"🚀 BTC-FEUSD Oracle Loop initialized")
        self.logger.info(f"   DEX: {dex}")
        self.logger.info(f"   Update interval: {interval}s")
        self.logger.info(f"   Max price age: {max_price_age}min")
        self.logger.info(f"   Log level: {log_level}")
    
    def _setup_logging(self, log_level: str, log_file: Optional[str]):
        """Setup logging configuration"""
        # Create logger
        self.logger = logging.getLogger('btc_feusd_oracle')
        self.logger.setLevel(getattr(logging, log_level.upper()))
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # File handler (if specified)
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
            self.logger.info(f"📝 Logging to file: {log_file}")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        self.logger.info(f"🛑 Received signal {signum}, initiating graceful shutdown...")
        self.running = False
    
    def _check_price_staleness(self, price_data: Dict[str, Any]) -> bool:
        """Check if the current price is stale"""
        btc_data = price_data.get("BTC-FEUSD", {})
        
        if "error" in btc_data:
            return True
        
        age_minutes = btc_data.get('age_minutes', 999)
        return age_minutes > self.max_price_age
    
    def _calculate_backoff_delay(self, consecutive_errors: int) -> float:
        """Calculate exponential backoff delay"""
        base_delay = 5.0
        max_delay = 300.0  # 5 minutes max
        delay = min(base_delay * (2 ** consecutive_errors), max_delay)
        return delay
    
    def _update_oracle(self) -> Dict[str, Any]:
        """Perform a single oracle update"""
        try:
            self.logger.info(f"🔄 Starting oracle update #{self.update_count + 1}")
            
            # First, check current price from contract
            self.logger.debug("📊 Reading current BTC-FEUSD price from contract...")
            price_data = read_btc_feusd_price(debug=False)
            btc_data = price_data.get("BTC-FEUSD", {})
            
            if "error" in btc_data:
                error_msg = f"Failed to read contract price: {btc_data['error']}"
                self.logger.error(f"❌ {error_msg}")
                return {"status": "error", "reason": error_msg}
            
            price = btc_data['price']
            age_min = btc_data['age_minutes']
            
            self.logger.info(f"💰 Current BTC-FEUSD price: {price:,.6f} FEUSD per BTC")
            self.logger.info(f"⏰ Price age: {age_min} minutes")
            
            # Check if price is stale
            if self._check_price_staleness(price_data):
                warning_msg = f"Price is {age_min} minutes old (max: {self.max_price_age}min)"
                self.logger.warning(f"⚠️  {warning_msg}")
                return {"status": "stale", "reason": warning_msg, "price": price, "age": age_min}
            
            # Update the oracle
            self.logger.info(f"🔄 Updating oracle for DEX '{self.dex}'...")
            result = update_btc_feusd_oracle(self.dex, debug=False)
            
            if result["status"] == "ok":
                self.logger.info("✅ Oracle update successful!")
                self.logger.info(f"💰 Updated price: {result['price']:,.6f} FEUSD per BTC")
                self.logger.info(f"📍 Mapping: {result['mapping']}")
                return {"status": "success", "result": result}
                
            elif result["status"] == "noop":
                self.logger.info(f"ℹ️  No update needed: {result['reason']}")
                return {"status": "noop", "reason": result['reason']}
                
            else:
                error_msg = f"Oracle update failed: {result['reason']}"
                self.logger.error(f"❌ {error_msg}")
                return {"status": "error", "reason": error_msg}
                
        except Exception as e:
            error_msg = f"Unexpected error during oracle update: {e}"
            self.logger.error(f"❌ {error_msg}")
            return {"status": "error", "reason": error_msg}
    
    def _log_statistics(self):
        """Log current statistics"""
        uptime = datetime.now() - self.start_time
        success_rate = (self.update_count - self.error_count) / max(self.update_count, 1) * 100
        
        self.logger.info("📊 Statistics:")
        self.logger.info(f"   Uptime: {uptime}")
        self.logger.info(f"   Total updates: {self.update_count}")
        self.logger.info(f"   Errors: {self.error_count}")
        self.logger.info(f"   Success rate: {success_rate:.1f}%")
        self.logger.info(f"   Consecutive errors: {self.consecutive_errors}")
        
        if self.last_successful_update:
            time_since_success = datetime.now() - self.last_successful_update
            self.logger.info(f"   Last successful update: {time_since_success} ago")
    
    def run(self):
        """Main loop"""
        self.start_time = datetime.now()
        self.logger.info("🎯 Starting BTC-FEUSD Oracle Loop")
        self.logger.info("=" * 60)
        
        while self.running:
            try:
                # Perform oracle update
                result = self._update_oracle()
                self.update_count += 1
                
                # Handle result
                if result["status"] == "success":
                    self.consecutive_errors = 0
                    self.last_successful_update = datetime.now()
                    self.logger.info("✅ Update completed successfully")
                    
                elif result["status"] == "noop":
                    self.consecutive_errors = 0
                    self.logger.info("ℹ️  No update needed")
                    
                elif result["status"] == "stale":
                    self.consecutive_errors += 1
                    self.error_count += 1
                    self.logger.warning(f"⚠️  Price is stale, will retry")
                    
                else:  # error
                    self.consecutive_errors += 1
                    self.error_count += 1
                    self.logger.error(f"❌ Update failed: {result['reason']}")
                
                # Check for too many consecutive errors
                if self.consecutive_errors >= self.max_consecutive_errors:
                    self.logger.error(f"🚨 Too many consecutive errors ({self.consecutive_errors}), stopping loop")
                    break
                
                # Log statistics every 10 updates
                if self.update_count % 10 == 0:
                    self._log_statistics()
                
                # Wait for next update
                if self.running:
                    self.logger.debug(f"⏳ Waiting {self.interval} seconds until next update...")
                    
                    # Sleep in small chunks to allow for graceful shutdown
                    sleep_chunks = self.interval // 5
                    for _ in range(sleep_chunks):
                        if not self.running:
                            break
                        time.sleep(5)
                    
                    # Sleep remaining time
                    remaining = self.interval % 5
                    if remaining > 0 and self.running:
                        time.sleep(remaining)
                
            except KeyboardInterrupt:
                self.logger.info("🛑 Keyboard interrupt received")
                break
            except Exception as e:
                self.logger.error(f"💥 Unexpected error in main loop: {e}")
                self.consecutive_errors += 1
                self.error_count += 1
                
                if self.consecutive_errors >= self.max_consecutive_errors:
                    self.logger.error("🚨 Too many consecutive errors, stopping loop")
                    break
                
                # Exponential backoff on errors
                backoff_delay = self._calculate_backoff_delay(self.consecutive_errors)
                self.logger.info(f"⏳ Backing off for {backoff_delay:.1f} seconds...")
                time.sleep(backoff_delay)
        
        # Final statistics
        self.logger.info("🏁 Oracle loop stopped")
        self._log_statistics()
        self.logger.info("=" * 60)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="BTC-FEUSD Oracle Loop - Continuous price updates",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage with default settings
  python btc_feusd_oracle_loop.py
  
  # Custom interval and DEX
  python btc_feusd_oracle_loop.py --dex btcx --interval 30
  
  # With logging to file
  python btc_feusd_oracle_loop.py --log-file oracle.log --log-level DEBUG
  
  # Run as background service
  nohup python btc_feusd_oracle_loop.py --log-file oracle.log > /dev/null 2>&1 &
        """
    )
    
    parser.add_argument(
        '--dex', 
        default='btcx',
        help='DEX handle (default: btcx)'
    )
    
    parser.add_argument(
        '--interval', 
        type=int, 
        default=60,
        help='Update interval in seconds (default: 60)'
    )
    
    parser.add_argument(
        '--max-price-age', 
        type=int, 
        default=30,
        help='Maximum acceptable price age in minutes (default: 30)'
    )
    
    parser.add_argument(
        '--log-level', 
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level (default: INFO)'
    )
    
    parser.add_argument(
        '--log-file', 
        help='Log file path (optional)'
    )
    
    parser.add_argument(
        '--version', 
        action='version', 
        version='BTC-FEUSD Oracle Loop v1.0'
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.interval < 10:
        print("❌ Error: Update interval must be at least 10 seconds")
        sys.exit(1)
    
    if args.max_price_age < 5:
        print("❌ Error: Max price age must be at least 5 minutes")
        sys.exit(1)
    
    # Create and run the oracle loop
    try:
        oracle_loop = BTCFeusdOracleLoop(
            dex=args.dex,
            interval=args.interval,
            max_price_age=args.max_price_age,
            log_level=args.log_level,
            log_file=args.log_file
        )
        
        oracle_loop.run()
        
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
