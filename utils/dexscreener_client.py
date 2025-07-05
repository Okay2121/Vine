"""
DEX Screener API Client
======================
Fetches real-time token data from DEX Screener API for authentic position displays
"""

import requests
import time
import logging
from typing import Dict, Optional, Any
import json

logger = logging.getLogger(__name__)

class DexScreenerClient:
    """Client for fetching token data from DEX Screener API"""
    
    def __init__(self):
        self.base_url = "https://api.dexscreener.com"
        self.cache = {}
        self.cache_duration = 30  # 30 seconds cache for prices
        self.rate_limit_delay = 0.5  # 500ms between requests
        self.last_request_time = 0
        
    def _rate_limit(self):
        """Implement rate limiting to avoid API throttling"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - time_since_last)
        
        self.last_request_time = time.time()
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid"""
        if cache_key not in self.cache:
            return False
        
        cached_data = self.cache[cache_key]
        current_time = time.time()
        
        return (current_time - cached_data['timestamp']) < self.cache_duration
    
    def _cache_data(self, cache_key: str, data: Any):
        """Cache data with timestamp"""
        self.cache[cache_key] = {
            'data': data,
            'timestamp': time.time()
        }
    
    def get_token_data(self, contract_address: str, chain_id: str = "solana") -> Optional[Dict]:
        """
        Fetch token data from DEX Screener API
        
        Args:
            contract_address (str): Token contract address
            chain_id (str): Blockchain identifier (default: solana)
            
        Returns:
            dict: Token data or None if not found
        """
        cache_key = f"{chain_id}_{contract_address}"
        
        # Check cache first
        if self._is_cache_valid(cache_key):
            logger.info(f"Using cached data for token {contract_address}")
            return self.cache[cache_key]['data']
        
        try:
            # Rate limiting
            self._rate_limit()
            
            # Make API request
            url = f"{self.base_url}/tokens/v1/{chain_id}/{contract_address}"
            logger.info(f"Fetching token data from: {url}")
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract the first pair data (most liquid pair)
            if data.get('pairs') and len(data['pairs']) > 0:
                pair_data = data['pairs'][0]  # Use most liquid pair
                
                # Cache the data
                self._cache_data(cache_key, pair_data)
                
                logger.info(f"Successfully fetched data for token {contract_address}")
                return pair_data
            else:
                logger.warning(f"No pairs found for token {contract_address}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching token data for {contract_address}: {str(e)}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON response for {contract_address}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching token data for {contract_address}: {str(e)}")
            return None
    
    def format_price(self, price: float) -> str:
        """Format price with appropriate decimal places like DEX Screener"""
        if price >= 1:
            return f"${price:.6f}"
        elif price >= 0.01:
            return f"${price:.8f}"
        elif price >= 0.0001:
            return f"${price:.10f}"
        else:
            # Count leading zeros for very small prices
            price_str = f"{price:.20f}"
            if '.' in price_str:
                decimal_part = price_str.split('.')[1]
                leading_zeros = 0
                for char in decimal_part:
                    if char == '0':
                        leading_zeros += 1
                    else:
                        break
                
                if leading_zeros >= 4:
                    significant_digits = decimal_part[leading_zeros:leading_zeros+4]
                    return f"$0.0({leading_zeros}){significant_digits}"
                else:
                    return f"${price:.10f}"
            else:
                return f"${price:.10f}"
    
    def format_market_cap(self, market_cap: float) -> str:
        """Format market cap like DEX Screener (e.g., $2.78K, $384.7K)"""
        if market_cap >= 1_000_000_000:
            return f"${market_cap / 1_000_000_000:.1f}B"
        elif market_cap >= 1_000_000:
            return f"${market_cap / 1_000_000:.1f}M"
        elif market_cap >= 1_000:
            return f"${market_cap / 1_000:.1f}K"
        else:
            return f"${market_cap:.0f}"
    
    def format_amount(self, amount: float) -> str:
        """Format token amounts like DEX Screener (e.g., 45.32K)"""
        if amount >= 1_000_000_000:
            return f"{amount / 1_000_000_000:.1f}B"
        elif amount >= 1_000_000:
            return f"{amount / 1_000_000:.1f}M"
        elif amount >= 1_000:
            return f"{amount / 1_000:.1f}K"
        else:
            return f"{amount:.0f}"
    
    def calculate_ownership_percentage(self, token_amount: float, total_supply: float) -> float:
        """Calculate realistic ownership percentage"""
        if total_supply <= 0:
            return 0.0
        
        ownership = (token_amount / total_supply) * 100
        return round(ownership, 6)  # Round to 6 decimal places for realistic display
    
    def get_realistic_exit_data(self, entry_price: float, roi_percentage: float, total_supply: float) -> Dict:
        """Calculate realistic exit price and market cap data"""
        exit_price = entry_price * (1 + roi_percentage / 100)
        
        # Calculate average exit (typically 8x-15x from entry for memecoins)
        import random
        avg_exit_multiplier = random.uniform(8, 15)
        avg_exit_price = entry_price * avg_exit_multiplier
        
        # Calculate market caps
        entry_market_cap = total_supply * entry_price
        exit_market_cap = total_supply * exit_price
        avg_exit_market_cap = total_supply * avg_exit_price
        
        return {
            'exit_price': exit_price,
            'avg_exit_price': avg_exit_price,
            'entry_market_cap': entry_market_cap,
            'exit_market_cap': exit_market_cap,
            'avg_exit_market_cap': avg_exit_market_cap
        }

# Global instance
dex_client = DexScreenerClient()