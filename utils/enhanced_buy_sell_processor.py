"""
Enhanced Buy/Sell Trade Processor
=================================
Unified processing system for both buy and sell trades with admin time control
Supports format: ACTION TOKEN_SYMBOL CONTRACT_ADDRESS PRICE TX_LINK
"""

import logging
import re
import time
import random
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, List
from app import app, db
from models import User, TradingPosition, Transaction, Profit
from utils.dexscreener_client import dex_client
from utils.usd_trade_processor import usd_processor

logger = logging.getLogger(__name__)

class EnhancedBuySellProcessor:
    """Processes both buy and sell trades with unified format and time control"""
    
    def __init__(self):
        self.sol_price_cache = {
            'price': None,
            'timestamp': 0,
            'cache_duration': 30  # 30 seconds cache
        }
    
    def parse_trade_message(self, message: str) -> Optional[Dict]:
        """
        Parse trade message in format: ACTION TOKEN_SYMBOL CONTRACT_ADDRESS PRICE TX_LINK
        
        Examples:
        - Buy $PEPE E2NEYtNToYjoytGUzgp8Yd7Rz2WAroMZ1QRkLESypump 0.00045 https://solscan.io/tx/abc123
        - Sell $PEPE E2NEYtNToYjoytGUzgp8Yd7Rz2WAroMZ1QRkLESypump 0.062 https://solscan.io/tx/def456
        
        Returns:
            Dict with parsed trade data or None if invalid
        """
        try:
            # Enhanced regex pattern for buy/sell format
            pattern = r'^(Buy|Sell)\s+\$([A-Za-z0-9_]+)\s+([A-Za-z0-9]{40,50})\s+([0-9.]+)\s+(https?://[^\s]+)$'
            match = re.match(pattern, message.strip(), re.IGNORECASE)
            
            if not match:
                logger.warning(f"Trade message format invalid: {message}")
                return None
            
            action, token_symbol, contract_address, price_str, tx_link = match.groups()
            
            # Validate inputs
            try:
                price_usd = float(price_str)
                if price_usd <= 0:
                    logger.warning(f"Invalid price: {price_usd}")
                    return None
            except ValueError:
                logger.warning(f"Invalid price format: {price_str}")
                return None
            
            # Get current SOL price for conversion
            sol_price = self.get_sol_price_usd()
            if sol_price <= 0:
                logger.warning("Failed to get SOL price")
                return None
            
            # Convert USD to SOL
            price_sol = price_usd / sol_price
            
            # Get token info from DEX Screener
            token_info = self.get_token_info(contract_address)
            
            return {
                'action': action.lower(),
                'token_symbol': token_symbol.upper(),
                'contract_address': contract_address,
                'price_usd': price_usd,
                'price_sol': price_sol,
                'tx_link': tx_link,
                'sol_price_used': sol_price,
                'token_info': token_info,
                'timestamp': datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Error parsing trade message: {e}")
            return None
    
    def get_sol_price_usd(self) -> float:
        """Get current SOL price in USD using the existing USD processor"""
        try:
            return usd_processor.get_sol_price_usd()
        except Exception as e:
            logger.error(f"Error getting SOL price: {e}")
            return 250.0  # Fallback price
    
    def get_token_info(self, contract_address: str, timestamp: Optional[datetime] = None) -> Dict:
        """Get token information with optional historical data"""
        try:
            if timestamp and timestamp < datetime.utcnow() - timedelta(minutes=5):
                # Use historical data for trades older than 5 minutes
                from utils.historical_market_fetcher import historical_fetcher
                return historical_fetcher.get_historical_market_data(contract_address, timestamp)
            else:
                # Use current data for recent trades
                import requests
                url = f"https://api.dexscreener.com/latest/dex/tokens/{contract_address}"
                response = requests.get(url, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('pairs') and len(data['pairs']) > 0:
                        pair = data['pairs'][0]
                        return {
                            'name': pair.get('baseToken', {}).get('name', 'Unknown Token'),
                            'symbol': pair.get('baseToken', {}).get('symbol', 'UNK'),
                            'market_cap': float(pair.get('fdv', 850000)),
                            'liquidity': float(pair.get('liquidity', {}).get('usd', 0)),
                            'volume_24h': float(pair.get('volume', {}).get('h24', 45000)),
                            'price_usd': float(pair.get('priceUsd', 0)),
                            'is_historical': False,
                            'data_source': 'dexscreener_live'
                        }
        except Exception as e:
            logger.error(f"Error getting token info: {e}")
        
        return {
            'name': 'Unknown Token',
            'symbol': 'UNK',
            'market_cap': 850000,
            'liquidity': 0,
            'volume_24h': 45000,
            'price_usd': 0,
            'is_historical': False,
            'data_source': 'fallback'
        }
    
    def process_buy_trade(self, trade_data: Dict, admin_id: str, custom_timestamp: Optional[datetime] = None) -> Tuple[bool, str, int]:
        """
        Process a BUY trade - creates open positions for all eligible users
        
        Args:
            trade_data: Parsed trade data
            admin_id: Admin user ID
            custom_timestamp: Optional custom timestamp for the trade
            
        Returns:
            Tuple of (success, message, affected_users_count)
        """
        try:
            with app.app_context():
                # Use custom timestamp or current time
                trade_timestamp = custom_timestamp or datetime.utcnow()
                
                # Update token info with historical data if custom timestamp provided
                if custom_timestamp and custom_timestamp < datetime.utcnow() - timedelta(minutes=5):
                    historical_token_info = self.get_token_info(trade_data['contract_address'], custom_timestamp)
                    trade_data['token_info'] = historical_token_info
                    # Also update market cap in notifications
                    trade_data['historical_market_cap'] = historical_token_info.get('market_cap', 850000)
                    trade_data['historical_volume'] = historical_token_info.get('volume_24h', 45000)
                    trade_data['data_source'] = historical_token_info.get('data_source', 'current')
                
                # Get eligible users (active users with balance > 0)
                eligible_users = User.query.filter(
                    User.balance > 0,
                    User.status == 'active'
                ).all()
                
                if not eligible_users:
                    return False, "No eligible users found", 0
                
                created_positions = 0
                total_allocated = 0
                
                for user in eligible_users:
                    try:
                        # Calculate position size based on user balance
                        position_size = self.calculate_position_size(user.balance, trade_data['price_sol'])
                        
                        if position_size <= 0:
                            continue
                        
                        # Create trading position
                        position = TradingPosition(
                            user_id=user.id,
                            token_name=trade_data['token_symbol'],
                            contract_address=trade_data['contract_address'],
                            amount=position_size,
                            entry_price=trade_data['price_sol'],
                            current_price=trade_data['price_sol'],
                            timestamp=trade_timestamp,
                            buy_timestamp=trade_timestamp,
                            status='open',
                            trade_type='snipe',
                            buy_tx_hash=self.extract_tx_hash(trade_data['tx_link']),
                            admin_id=admin_id
                        )
                        
                        db.session.add(position)
                        created_positions += 1
                        total_allocated += position_size * trade_data['price_sol']
                        
                        # Send notification to user
                        self.send_buy_notification(user, trade_data, position_size)
                        
                    except Exception as e:
                        logger.error(f"Error creating position for user {user.id}: {e}")
                        continue
                
                # Commit all positions
                db.session.commit()
                
                success_message = (
                    f"✅ BUY Order Executed\n\n"
                    f"🎯 Token: {trade_data['token_symbol']}\n"
                    f"💰 Price: ${trade_data['price_usd']:.6f} ({trade_data['price_sol']:.8f} SOL)\n"
                    f"👥 Users: {created_positions}\n"
                    f"📊 Total Allocated: {total_allocated:.4f} SOL\n"
                    f"⏰ Executed: {trade_timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}"
                )
                
                return True, success_message, created_positions
                
        except Exception as e:
            logger.error(f"Error processing buy trade: {e}")
            return False, f"Error processing buy trade: {str(e)}", 0
    
    def process_sell_trade(self, trade_data: Dict, admin_id: str, custom_timestamp: Optional[datetime] = None) -> Tuple[bool, str, int]:
        """
        Process a SELL trade - matches existing positions and calculates profits
        
        Args:
            trade_data: Parsed trade data
            admin_id: Admin user ID
            custom_timestamp: Optional custom timestamp for the trade
            
        Returns:
            Tuple of (success, message, affected_users_count)
        """
        try:
            with app.app_context():
                # Use custom timestamp or current time
                trade_timestamp = custom_timestamp or datetime.utcnow()
                
                # Update token info with historical data if custom timestamp provided
                if custom_timestamp and custom_timestamp < datetime.utcnow() - timedelta(minutes=5):
                    historical_token_info = self.get_token_info(trade_data['contract_address'], custom_timestamp)
                    trade_data['token_info'] = historical_token_info
                    trade_data['historical_market_cap'] = historical_token_info.get('market_cap', 850000)
                    trade_data['historical_volume'] = historical_token_info.get('volume_24h', 45000)
                    trade_data['data_source'] = historical_token_info.get('data_source', 'current')
                
                # Find matching open positions
                open_positions = TradingPosition.query.filter(
                    TradingPosition.token_name == trade_data['token_symbol'],
                    TradingPosition.status == 'open'
                ).all()
                
                if not open_positions:
                    return False, f"No open positions found for {trade_data['token_symbol']}", 0
                
                closed_positions = 0
                total_profit = 0
                
                for position in open_positions:
                    try:
                        # Calculate profit/loss
                        entry_price = position.entry_price
                        exit_price = trade_data['price_sol']
                        roi_percentage = ((exit_price - entry_price) / entry_price) * 100
                        profit_amount = position.amount * (exit_price - entry_price)
                        
                        # Update position
                        position.current_price = exit_price
                        position.exit_price = exit_price
                        position.sell_timestamp = trade_timestamp
                        position.sell_tx_hash = self.extract_tx_hash(trade_data['tx_link'])
                        position.roi_percentage = roi_percentage
                        position.status = 'closed'
                        
                        # Update user balance
                        user = User.query.get(position.user_id)
                        if user:
                            user.balance += profit_amount
                            
                            # Create profit record
                            profit_record = Profit(
                                user_id=user.id,
                                amount=profit_amount,
                                percentage=roi_percentage,
                                date=trade_timestamp.date(),
                                source=f"trade_{trade_data['token_symbol']}"
                            )
                            db.session.add(profit_record)
                            
                            # Create transaction record
                            transaction = Transaction(
                                user_id=user.id,
                                transaction_type="trade_profit" if profit_amount > 0 else "trade_loss",
                                amount=abs(profit_amount),
                                token_name=trade_data['token_symbol'],
                                timestamp=trade_timestamp,
                                status="completed",
                                notes=f"Exit: {trade_data['token_symbol']} - ROI: {roi_percentage:.2f}%",
                                tx_hash=self.extract_tx_hash(trade_data['tx_link']),
                                processed_at=trade_timestamp
                            )
                            db.session.add(transaction)
                            
                            # Send notification to user
                            self.send_sell_notification(user, trade_data, position, profit_amount, roi_percentage)
                            
                            closed_positions += 1
                            total_profit += profit_amount
                        
                    except Exception as e:
                        logger.error(f"Error closing position {position.id}: {e}")
                        continue
                
                # Commit all changes
                db.session.commit()
                
                success_message = (
                    f"✅ SELL Order Executed\n\n"
                    f"🎯 Token: {trade_data['token_symbol']}\n"
                    f"💰 Price: ${trade_data['price_usd']:.6f} ({trade_data['price_sol']:.8f} SOL)\n"
                    f"👥 Positions Closed: {closed_positions}\n"
                    f"📈 Total Profit: {total_profit:.4f} SOL\n"
                    f"⏰ Executed: {trade_timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}"
                )
                
                return True, success_message, closed_positions
                
        except Exception as e:
            logger.error(f"Error processing sell trade: {e}")
            return False, f"Error processing sell trade: {str(e)}", 0
    
    def calculate_position_size(self, user_balance: float, token_price: float) -> float:
        """Calculate realistic position size based on user balance"""
        try:
            # Risk allocation based on balance tiers
            if user_balance >= 10:
                risk_percent = random.uniform(5, 15)
            elif user_balance >= 5:
                risk_percent = random.uniform(8, 25)
            elif user_balance >= 2:
                risk_percent = random.uniform(15, 35)
            elif user_balance >= 0.5:
                risk_percent = random.uniform(25, 50)
            else:
                risk_percent = random.uniform(40, 70)
            
            # Calculate SOL amount to spend
            sol_to_spend = user_balance * (risk_percent / 100)
            
            # Calculate token amount (with some randomization for realism)
            base_amount = sol_to_spend / token_price
            variation = random.uniform(0.9, 1.1)  # ±10% variation
            
            return max(0, base_amount * variation)
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return 0
    
    def extract_tx_hash(self, tx_link: str) -> str:
        """Extract transaction hash from Solscan link"""
        try:
            if '/' in tx_link:
                return tx_link.split('/')[-1]
            return tx_link
        except Exception:
            return tx_link
    
    def send_buy_notification(self, user, trade_data: Dict, position_size: float):
        """Send buy notification to user (placeholder - implement with actual bot)"""
        # Include historical market data in notifications
        token_info = trade_data.get('token_info', {})
        market_cap = trade_data.get('historical_market_cap', token_info.get('market_cap', 850000))
        data_source = trade_data.get('data_source', 'current')
        
        logger.info(f"BUY notification for {user.telegram_id}: {trade_data['token_symbol']} "
                   f"Position: {position_size:.6f} SOL, Market Cap: ${market_cap:,.0f} "
                   f"(Data: {data_source})")
    
    def send_sell_notification(self, user, trade_data: Dict, position, profit_amount: float, roi_percentage: float):
        """Send sell notification to user (placeholder - implement with actual bot)"""
        # Include historical market data in notifications
        token_info = trade_data.get('token_info', {})
        market_cap = trade_data.get('historical_market_cap', token_info.get('market_cap', 850000))
        data_source = trade_data.get('data_source', 'current')
        
        logger.info(f"SELL notification for {user.telegram_id}: {trade_data['token_symbol']} "
                   f"Profit: {profit_amount:.6f} SOL ({roi_percentage:.1f}%), "
                   f"Market Cap: ${market_cap:,.0f} (Data: {data_source})")

# Global instance
enhanced_processor = EnhancedBuySellProcessor()