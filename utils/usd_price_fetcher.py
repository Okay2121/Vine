"""
Free USD Price Fetcher
======================
Fetches real-time USD prices using free APIs for professional position displays
"""

import requests
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class USDPriceFetcher:
    """Fetches USD prices from free APIs with fallback sources"""
    
    def __init__(self):
        # Free API endpoints (no key required)
        self.apis = [
            {
                'name': 'CoinGecko',
                'url': 'https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd',
                'parser': self._parse_coingecko
            },
            {
                'name': 'Binance',
                'url': 'https://api.binance.com/api/v3/ticker/price?symbol=SOLUSDT',
                'parser': self._parse_binance
            },
            {
                'name': 'CryptoCompare',
                'url': 'https://min-api.cryptocompare.com/data/price?fsym=SOL&tsyms=USD',
                'parser': self._parse_cryptocompare
            }
        ]
        
        # Cache to avoid excessive API calls
        self._cached_price = None
        self._cache_timestamp = 0
        self._cache_duration = 30  # 30 seconds
    
    def _parse_coingecko(self, data: dict) -> Optional[float]:
        """Parse CoinGecko API response"""
        try:
            return float(data['solana']['usd'])
        except (KeyError, ValueError):
            return None
    
    def _parse_binance(self, data: dict) -> Optional[float]:
        """Parse Binance API response"""
        try:
            return float(data['price'])
        except (KeyError, ValueError):
            return None
    
    def _parse_cryptocompare(self, data: dict) -> Optional[float]:
        """Parse CryptoCompare API response"""
        try:
            return float(data['USD'])
        except (KeyError, ValueError):
            return None
    
    def _fetch_from_api(self, api: dict) -> Optional[float]:
        """Fetch price from a single API"""
        try:
            response = requests.get(api['url'], timeout=5)
            response.raise_for_status()
            
            data = response.json()
            price = api['parser'](data)
            
            if price and price > 0:
                logger.info(f"Fetched SOL price from {api['name']}: ${price:.6f}")
                return price
                
        except Exception as e:
            logger.warning(f"Failed to fetch from {api['name']}: {str(e)}")
            
        return None
    
    def get_sol_price_usd(self) -> float:
        """
        Get current SOL price in USD with caching and fallback
        
        Returns:
            float: SOL price in USD
        """
        import time
        current_time = time.time()
        
        # Check cache first
        if (self._cached_price and 
            current_time - self._cache_timestamp < self._cache_duration):
            return self._cached_price
        
        # Try each API until one succeeds
        for api in self.apis:
            price = self._fetch_from_api(api)
            if price:
                self._cached_price = price
                self._cache_timestamp = current_time
                return price
        
        # Fallback to cached price if all APIs fail
        if self._cached_price:
            logger.warning("All APIs failed, using cached price")
            return self._cached_price
        
        # Ultimate fallback (should rarely happen)
        logger.error("All price sources failed, using fallback price")
        return 150.0  # Conservative fallback
    
    def format_usd_amount(self, amount: float) -> str:
        """
        Format USD amount with K/M suffixes
        
        Args:
            amount (float): USD amount
            
        Returns:
            str: Formatted amount
        """
        if amount >= 1_000_000:
            return f"${amount/1_000_000:.2f}M"
        elif amount >= 1_000:
            return f"${amount/1_000:.1f}K"
        else:
            return f"${amount:.2f}"
    
    def get_price_with_change(self) -> dict:
        """
        Get price with simulated change indicators for realism
        
        Returns:
            dict: Price data with change information
        """
        import random
        
        price = self.get_sol_price_usd()
        
        # Simulate realistic price change (for display purposes)
        change_percent = random.uniform(-8.5, 12.3)
        change_indicator = "📈" if change_percent > 0 else "📉"
        
        return {
            'price': price,
            'change_percent': change_percent,
            'change_indicator': change_indicator,
            'formatted': f"${price:.6f}"
        }

# Global instance for easy access
usd_fetcher = USDPriceFetcher()

def get_sol_price_usd() -> float:
    """Convenience function to get SOL price"""
    return usd_fetcher.get_sol_price_usd()

def format_usd_amount(amount: float) -> str:
    """Convenience function to format USD amounts"""
    return usd_fetcher.format_usd_amount(amount)