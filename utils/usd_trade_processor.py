"""
USD Trade Processor
==================
Processes trade broadcasts using USD prices with automatic SOL conversion
Uses free APIs for real-time USD/SOL conversion
"""

import logging
import requests
import time
from typing import Dict, Optional, Tuple
from datetime import datetime
from utils.dexscreener_client import dex_client

logger = logging.getLogger(__name__)

class USDTradeProcessor:
    """Processes trades with USD prices and converts to SOL for user calculations"""
    
    def __init__(self):
        self.sol_price_cache = {
            'price': None,
            'timestamp': 0,
            'cache_duration': 30  # 30 seconds cache
        }
    
    def get_sol_price_usd(self) -> float:
        """
        Get current SOL price in USD from free APIs
        
        Returns:
            float: Current SOL price in USD
        """
        current_time = time.time()
        
        # Return cached price if still valid
        if (self.sol_price_cache['price'] is not None and 
            current_time - self.sol_price_cache['timestamp'] < self.sol_price_cache['cache_duration']):
            return self.sol_price_cache['price']
        
        # Try multiple free APIs for SOL price
        price_sources = [
            {
                'name': 'CoinGecko',
                'url': 'https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd',
                'parser': lambda data: data['solana']['usd']
            },
            {
                'name': 'Binance',
                'url': 'https://api.binance.com/api/v3/ticker/price?symbol=SOLUSDT',
                'parser': lambda data: float(data['price'])
            },
            {
                'name': 'CoinCap',
                'url': 'https://api.coincap.io/v2/assets/solana',
                'parser': lambda data: float(data['data']['priceUsd'])
            }
        ]
        
        for source in price_sources:
            try:
                response = requests.get(
                    source['url'],
                    headers={'User-Agent': 'ThriveQuantBot/1.0'},
                    timeout=5
                )
                
                if response.status_code == 200:
                    data = response.json()
                    price = source['parser'](data)
                    
                    # Validate price is reasonable ($50-$500)
                    if 50 <= price <= 500:
                        self.sol_price_cache['price'] = price
                        self.sol_price_cache['timestamp'] = current_time
                        logger.info(f"Fetched SOL price from {source['name']}: ${price:.2f}")
                        return price
                    else:
                        logger.warning(f"Invalid SOL price from {source['name']}: ${price}")
                        
            except Exception as e:
                logger.warning(f"Failed to fetch SOL price from {source['name']}: {e}")
                continue
        
        # Fallback to reasonable estimate
        fallback_price = 200.0  # Conservative SOL price fallback
        logger.warning(f"Using fallback SOL price: ${fallback_price}")
        self.sol_price_cache['price'] = fallback_price
        self.sol_price_cache['timestamp'] = current_time
        return fallback_price
    
    def usd_to_sol(self, usd_amount: float) -> float:
        """
        Convert USD amount to SOL
        
        Args:
            usd_amount (float): Amount in USD
            
        Returns:
            float: Equivalent amount in SOL
        """
        sol_price = self.get_sol_price_usd()
        return usd_amount / sol_price
    
    def sol_to_usd(self, sol_amount: float) -> float:
        """
        Convert SOL amount to USD
        
        Args:
            sol_amount (float): Amount in SOL
            
        Returns:
            float: Equivalent amount in USD
        """
        sol_price = self.get_sol_price_usd()
        return sol_amount * sol_price
    
    def parse_trade_message(self, message: str) -> Optional[Dict]:
        """
        Parse trade message in USD format: CONTRACT_ADDRESS ENTRY_PRICE_USD EXIT_PRICE_USD TX_LINK
        
        Args:
            message (str): Trade message to parse
            
        Returns:
            dict: Parsed trade data with USD and SOL prices
        """
        try:
            parts = message.strip().split()
            if len(parts) != 4:
                return None
            
            contract_address = parts[0]
            entry_price_usd = float(parts[1])
            exit_price_usd = float(parts[2])
            tx_link = parts[3]
            
            # Validate contract address format (Solana addresses are 32-44 chars)
            if len(contract_address) < 32:
                return None
            
            # Validate USD prices are reasonable for memecoins
            if entry_price_usd <= 0 or exit_price_usd <= 0:
                return None
            
            if entry_price_usd > 10 or exit_price_usd > 10:  # Max $10 for memecoins
                return None
            
            # Convert USD prices to SOL
            entry_price_sol = self.usd_to_sol(entry_price_usd)
            exit_price_sol = self.usd_to_sol(exit_price_usd)
            
            # Calculate ROI
            roi_percentage = ((exit_price_usd - entry_price_usd) / entry_price_usd) * 100
            
            return {
                'contract_address': contract_address,
                'entry_price_usd': entry_price_usd,
                'exit_price_usd': exit_price_usd,
                'entry_price_sol': entry_price_sol,
                'exit_price_sol': exit_price_sol,
                'roi_percentage': roi_percentage,
                'tx_link': tx_link,
                'sol_price_used': self.get_sol_price_usd(),
                'trade_type': 'exit'
            }
            
        except (ValueError, IndexError) as e:
            logger.error(f"Error parsing trade message: {e}")
            return None
    
    def fetch_token_data(self, contract_address: str) -> Optional[Dict]:
        """
        Fetch token data from DEX Screener (already in USD)
        
        Args:
            contract_address (str): Token contract address
            
        Returns:
            dict: Token data with USD prices
        """
        try:
            market_data = dex_client.get_token_data(contract_address)
            
            if not market_data:
                logger.warning(f"No market data found for contract {contract_address}")
                return None
            
            # Extract token data (DEX Screener provides USD prices)
            token_data = {
                'symbol': market_data.get('baseToken', {}).get('symbol', 'UNKNOWN'),
                'name': market_data.get('baseToken', {}).get('name', 'Unknown Token'),
                'current_price_usd': float(market_data.get('priceUsd', 0)),
                'market_cap': float(market_data.get('marketCap', 0)) if market_data.get('marketCap') else 0,
                'volume_24h': float(market_data.get('volume', {}).get('h24', 0)),
                'liquidity_usd': float(market_data.get('liquidity', {}).get('usd', 0)),
                'dex_name': market_data.get('dexId', 'Unknown DEX'),
                'pair_address': market_data.get('pairAddress', ''),
            }
            
            # Convert current price to SOL for calculations
            token_data['current_price_sol'] = self.usd_to_sol(token_data['current_price_usd'])
            
            return token_data
            
        except Exception as e:
            logger.error(f"Error fetching token data: {e}")
            return None
    
    def calculate_user_profits(self, trade_data: Dict, users: list) -> list:
        """
        Calculate user profits based on USD trade data
        
        Args:
            trade_data (dict): Parsed trade data
            users (list): List of users to calculate profits for
            
        Returns:
            list: Users with calculated profits in SOL
        """
        results = []
        roi_percentage = trade_data['roi_percentage']
        
        for user in users:
            try:
                # Calculate profit allocation (5-15% of balance)
                allocation_percentage = min(user.balance / 100, 0.15)
                
                # Calculate profit in SOL (user balances are in SOL)
                profit_sol = user.balance * allocation_percentage * (roi_percentage / 100)
                
                # Convert profit to USD for display
                profit_usd = self.sol_to_usd(profit_sol)
                
                results.append({
                    'user': user,
                    'profit_sol': profit_sol,
                    'profit_usd': profit_usd,
                    'new_balance_sol': user.balance + profit_sol,
                    'roi_percentage': roi_percentage
                })
                
            except Exception as e:
                logger.error(f"Error calculating profit for user {user.id}: {e}")
                continue
        
        return results
    
    def format_user_notification(self, token_data: Dict, trade_data: Dict, user_profit: Dict) -> str:
        """
        Format user notification message with USD prices
        
        Args:
            token_data (dict): Token information
            trade_data (dict): Trade data
            user_profit (dict): User profit calculation
            
        Returns:
            str: Formatted notification message
        """
        symbol = token_data.get('symbol', 'TOKEN')
        roi = trade_data['roi_percentage']
        
        # Format profit display
        profit_display = f"+${user_profit['profit_usd']:.4f} (+{user_profit['profit_sol']:.6f} SOL)"
        balance_display = f"{user_profit['new_balance_sol']:.6f} SOL"
        
        message = f"""🎯 LIVE EXIT ALERT

{symbol} 🟢 +{roi:.1f}%

Entry: ${trade_data['entry_price_usd']:.6f}
Exit: ${trade_data['exit_price_usd']:.6f}

Your Profit: {profit_display}
New Balance: {balance_display}

🔗 {trade_data['tx_link']}"""
        
        return message

# Global instance
usd_processor = USDTradeProcessor()