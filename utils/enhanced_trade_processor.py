"""
Enhanced Trade Processor with DEX Screener Integration
=====================================================
Processes admin trade broadcasts with real market data for authentic position displays
"""

import re
import random
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from app import app, db
from models import User, TradingPosition, Transaction, Profit
from utils.dexscreener_client import dex_client

logger = logging.getLogger(__name__)

class EnhancedTradeProcessor:
    """Processes admin trades with DEX Screener market data integration"""
    
    def __init__(self):
        # Enhanced regex patterns to include contract address
        self.buy_pattern = re.compile(
            r'^Buy\s+\$([A-Za-z0-9_]+)\s+([A-Za-z0-9_]+)\s+([0-9.]+)\s+([0-9.]+)\s+(https?://[^\s]+)', 
            re.IGNORECASE
        )
        self.sell_pattern = re.compile(
            r'^Sell\s+\$([A-Za-z0-9_]+)\s+([A-Za-z0-9_]+)\s+([0-9.]+)\s+([0-9.]+)\s+(https?://[^\s]+)', 
            re.IGNORECASE
        )
    
    def parse_trade_message(self, message: str) -> Optional[Dict]:
        """
        Parse admin trade message in enhanced format
        Format: Buy $SYMBOL CONTRACT_ADDRESS PRICE AMOUNT TX_LINK
        
        Args:
            message (str): Admin trade message
            
        Returns:
            dict: Parsed trade data or None if invalid
        """
        message = message.strip()
        
        # Try buy pattern
        buy_match = self.buy_pattern.match(message)
        if buy_match:
            symbol, contract_address, price_str, amount_str, tx_link = buy_match.groups()
            return {
                'trade_type': 'buy',
                'symbol': symbol,
                'contract_address': contract_address,
                'price': float(price_str),
                'reference_amount': float(amount_str),
                'tx_link': tx_link,
                'tx_hash': tx_link.split('/')[-1] if '/' in tx_link else tx_link
            }
        
        # Try sell pattern
        sell_match = self.sell_pattern.match(message)
        if sell_match:
            symbol, contract_address, price_str, amount_str, tx_link = sell_match.groups()
            return {
                'trade_type': 'sell',
                'symbol': symbol,
                'contract_address': contract_address,
                'price': float(price_str),
                'reference_amount': float(amount_str),
                'tx_link': tx_link,
                'tx_hash': tx_link.split('/')[-1] if '/' in tx_link else tx_link
            }
        
        return None
    
    def fetch_market_data(self, contract_address: str) -> Optional[Dict]:
        """
        Fetch market data from DEX Screener
        
        Args:
            contract_address (str): Token contract address
            
        Returns:
            dict: Market data or None if not available
        """
        try:
            market_data = dex_client.get_token_data(contract_address)
            
            if not market_data:
                logger.warning(f"No market data found for contract {contract_address}")
                return None
            
            # Extract relevant data
            extracted_data = {
                'price_usd': float(market_data.get('priceUsd', 0)),
                'market_cap': float(market_data.get('marketCap', 0)) if market_data.get('marketCap') else 0,
                'volume_24h': float(market_data.get('volume', {}).get('h24', 0)),
                'liquidity_usd': float(market_data.get('liquidity', {}).get('usd', 0)),
                'txns_24h': market_data.get('txns', {}).get('h24', {'buys': 0, 'sells': 0}),
                'pair_created_at': market_data.get('pairCreatedAt', int(datetime.utcnow().timestamp())),
                'fdv': float(market_data.get('fdv', 0)) if market_data.get('fdv') else 0
            }
            
            # Calculate total supply from market cap and price
            if extracted_data['price_usd'] > 0 and extracted_data['market_cap'] > 0:
                extracted_data['total_supply'] = extracted_data['market_cap'] / extracted_data['price_usd']
            else:
                # Fallback to FDV calculation or default
                if extracted_data['fdv'] > 0 and extracted_data['price_usd'] > 0:
                    extracted_data['total_supply'] = extracted_data['fdv'] / extracted_data['price_usd']
                else:
                    extracted_data['total_supply'] = 1_000_000_000  # Default memecoin supply
            
            return extracted_data
            
        except Exception as e:
            logger.error(f"Error fetching market data for {contract_address}: {str(e)}")
            return None
    
    def calculate_user_allocation(self, user_balance: float) -> Dict:
        """
        Calculate realistic user allocation based on balance
        
        Args:
            user_balance (float): User's current balance
            
        Returns:
            dict: Allocation data including risk percentage and amounts
        """
        # Risk allocation based on balance tiers (existing logic)
        if user_balance >= 10:
            risk_percent = random.uniform(5, 15)  # Whales: 5-15%
        elif user_balance >= 5:
            risk_percent = random.uniform(8, 25)  # Medium: 8-25%
        elif user_balance >= 2:
            risk_percent = random.uniform(15, 35)  # Small: 15-35%
        elif user_balance >= 0.5:
            risk_percent = random.uniform(25, 50)  # Tiny: 25-50%
        else:
            risk_percent = random.uniform(40, 70)  # Micro: 40-70%
        
        spent_sol = round(user_balance * (risk_percent / 100), 4)
        
        return {
            'risk_percentage': risk_percent,
            'spent_sol': spent_sol,
            'position_size_percent': risk_percent
        }
    
    def generate_realistic_metrics(self) -> Dict:
        """Generate realistic execution metrics"""
        return {
            'execution_speed': round(random.uniform(1.2, 2.8), 2),  # 1.2-2.8 seconds
            'gas_cost': round(random.uniform(0.0008, 0.0015), 5),   # Gas cost in SOL
            'entry_reason': random.choice([
                "New launch snipe",
                "Volume spike detection", 
                "Whale wallet alert",
                "Social sentiment trigger",
                "Price breakout signal"
            ]),
            'exit_reason': random.choice([
                "Take profit target (200%+ from entry)",
                "Volume exhaustion signal",
                "Stop loss triggered",
                "Profit taking at resistance",
                "Risk management exit"
            ])
        }
    
    def process_buy_trade(self, trade_data: Dict, admin_id: str, custom_timestamp: Optional[datetime] = None) -> Tuple[bool, str, int]:
        """
        Process BUY trade with DEX Screener integration
        
        Args:
            trade_data (dict): Parsed trade data
            admin_id (str): Admin user ID
            custom_timestamp (datetime): Custom timestamp for the trade
            
        Returns:
            tuple: (success, message, affected_users_count)
        """
        try:
            with app.app_context():
                # Fetch market data
                market_data = self.fetch_market_data(trade_data['contract_address'])
                
                if not market_data:
                    return False, f"Could not fetch market data for {trade_data['symbol']}", 0
                
                # Get active users
                users = User.query.filter(User.balance > 0).all()
                created_count = 0
                trade_timestamp = custom_timestamp or datetime.utcnow()
                
                logger.info(f"Processing BUY trade for {trade_data['symbol']} with {len(users)} users")
                
                for user in users:
                    try:
                        # Calculate user allocation
                        allocation = self.calculate_user_allocation(user.balance)
                        
                        if allocation['spent_sol'] <= 0:
                            continue
                        
                        # Calculate token amount from user's SOL allocation
                        token_amount = allocation['spent_sol'] / trade_data['price']
                        
                        # Calculate ownership percentage using real market data
                        ownership_pct = dex_client.calculate_ownership_percentage(
                            token_amount, market_data['total_supply']
                        )
                        
                        # Generate realistic metrics
                        metrics = self.generate_realistic_metrics()
                        
                        # Create enhanced trading position
                        position = TradingPosition()
                        position.user_id = user.id
                        position.token_name = trade_data['symbol']
                        position.amount = token_amount
                        position.entry_price = trade_data['price']
                        position.current_price = trade_data['price']
                        position.timestamp = trade_timestamp
                        position.buy_timestamp = trade_timestamp
                        position.status = 'open'
                        position.trade_type = 'snipe'
                        position.buy_tx_hash = trade_data['tx_hash']
                        position.admin_id = admin_id
                        
                        # DEX Screener market data
                        position.contract_address = trade_data['contract_address']
                        position.market_cap_entry = market_data['market_cap']
                        position.volume_24h = market_data['volume_24h']
                        position.liquidity_usd = market_data['liquidity_usd']
                        position.ownership_percentage = ownership_pct
                        position.total_supply = market_data['total_supply']
                        position.buy_count_24h = market_data['txns_24h'].get('buys', 0)
                        position.sell_count_24h = market_data['txns_24h'].get('sells', 0)
                        position.execution_speed = metrics['execution_speed']
                        position.gas_cost = metrics['gas_cost']
                        position.entry_reason = metrics['entry_reason']
                        position.price_usd_entry = market_data['price_usd']
                        
                        db.session.add(position)
                        created_count += 1
                        
                        logger.info(f"Created BUY position for user {user.id}: {token_amount:.0f} {trade_data['symbol']}")
                        
                    except Exception as user_error:
                        logger.error(f"Error creating position for user {user.id}: {str(user_error)}")
                        continue
                
                db.session.commit()
                logger.info(f"Successfully created {created_count} BUY positions for {trade_data['symbol']}")
                
                return True, f"Created {created_count} BUY positions for {trade_data['symbol']}", created_count
                
        except Exception as e:
            logger.error(f"Error processing BUY trade: {str(e)}")
            db.session.rollback()
            return False, f"Error processing BUY trade: {str(e)}", 0
    
    def process_sell_trade(self, trade_data: Dict, admin_id: str, custom_timestamp: Optional[datetime] = None) -> Tuple[bool, str, int]:
        """
        Process SELL trade with DEX Screener integration
        
        Args:
            trade_data (dict): Parsed trade data
            admin_id (str): Admin user ID
            custom_timestamp (datetime): Custom timestamp for the trade
            
        Returns:
            tuple: (success, message, affected_users_count)
        """
        try:
            with app.app_context():
                # Fetch current market data
                market_data = self.fetch_market_data(trade_data['contract_address'])
                
                if not market_data:
                    return False, f"Could not fetch market data for {trade_data['symbol']}", 0
                
                # Find open positions for this token
                open_positions = TradingPosition.query.filter_by(
                    token_name=trade_data['symbol'],
                    status='open'
                ).all()
                
                if not open_positions:
                    return False, f"No open positions found for {trade_data['symbol']}", 0
                
                updated_count = 0
                trade_timestamp = custom_timestamp or datetime.utcnow()
                
                logger.info(f"Processing SELL trade for {trade_data['symbol']} with {len(open_positions)} positions")
                
                for position in open_positions:
                    try:
                        user = User.query.get(position.user_id)
                        if not user:
                            continue
                        
                        # Calculate ROI
                        roi_percentage = ((trade_data['price'] - position.entry_price) / position.entry_price) * 100
                        
                        # Calculate profit/loss
                        profit_amount = position.amount * (trade_data['price'] - position.entry_price)
                        
                        # Calculate exit market data
                        exit_data = dex_client.get_realistic_exit_data(
                            position.entry_price, roi_percentage, position.total_supply or market_data['total_supply']
                        )
                        
                        # Generate realistic exit metrics
                        metrics = self.generate_realistic_metrics()
                        
                        # Update position with SELL data
                        position.current_price = trade_data['price']
                        position.exit_price = trade_data['price']
                        position.sell_timestamp = trade_timestamp
                        position.sell_tx_hash = trade_data['tx_hash']
                        position.roi_percentage = roi_percentage
                        position.status = 'closed'
                        
                        # Update market data for exit
                        position.market_cap_exit = exit_data['exit_market_cap']
                        position.market_cap_avg_exit = exit_data['avg_exit_market_cap']
                        position.price_usd_exit = market_data['price_usd']
                        position.exit_reason = metrics['exit_reason']
                        
                        # Update user balance
                        user.balance += profit_amount
                        
                        # Create profit record
                        if abs(profit_amount) > 0.001:  # Only for significant amounts
                            profit_record = Profit()
                            profit_record.user_id = user.id
                            profit_record.amount = profit_amount
                            profit_record.percentage = roi_percentage
                            profit_record.date = trade_timestamp.date()
                            db.session.add(profit_record)
                        
                        # Create transaction record
                        transaction = Transaction()
                        transaction.user_id = user.id
                        transaction.transaction_type = 'trade_profit' if profit_amount >= 0 else 'trade_loss'
                        transaction.amount = profit_amount
                        transaction.token_name = trade_data['symbol']
                        transaction.timestamp = trade_timestamp
                        transaction.status = 'completed'
                        transaction.notes = f"Trade exit: {trade_data['symbol']} - ROI: {roi_percentage:.2f}%"
                        transaction.tx_hash = f"{trade_data['tx_hash']}_u{user.id}"
                        transaction.processed_at = trade_timestamp
                        transaction.related_trade_id = position.id
                        
                        db.session.add(transaction)
                        updated_count += 1
                        
                        logger.info(f"Updated SELL position for user {user.id}: ROI {roi_percentage:.2f}%, P/L {profit_amount:.4f} SOL")
                        
                    except Exception as user_error:
                        logger.error(f"Error updating position for user {position.user_id}: {str(user_error)}")
                        continue
                
                db.session.commit()
                logger.info(f"Successfully processed {updated_count} SELL positions for {trade_data['symbol']}")
                
                return True, f"Processed {updated_count} SELL positions for {trade_data['symbol']}", updated_count
                
        except Exception as e:
            logger.error(f"Error processing SELL trade: {str(e)}")
            db.session.rollback()
            return False, f"Error processing SELL trade: {str(e)}", 0

# Global instance
enhanced_trade_processor = EnhancedTradeProcessor()