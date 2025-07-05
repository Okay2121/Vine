"""
Simplified Trade Processor with DEX Screener Integration
=======================================================
Processes admin trades using simplified format: CONTRACT_ADDRESS ENTRY_PRICE EXIT_PRICE TX_LINK
"""

import re
import random
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from app import app, db
from models import User, TradingPosition, Transaction, Profit, UserStatus
from utils.dexscreener_client import dex_client

logger = logging.getLogger(__name__)

class SimplifiedTradeProcessor:
    """Processes admin trades with simplified format and full DEX Screener automation"""
    
    def __init__(self):
        # Simplified pattern: CONTRACT_ADDRESS ENTRY_PRICE EXIT_PRICE TX_LINK
        self.trade_pattern = re.compile(
            r'^([A-Za-z0-9_]{32,44})\s+([0-9.]+)\s+([0-9.]+)(?:\s+(https?://[^\s]+))?$'
        )
        
        # Import USD price fetcher
        from utils.usd_price_fetcher import get_sol_price_usd
        self.get_sol_price = get_sol_price_usd
    
    def parse_trade_message(self, message: str) -> Optional[Dict]:
        """
        Parse admin trade message in simplified format
        Format: CONTRACT_ADDRESS ENTRY_PRICE EXIT_PRICE TX_LINK
        
        Args:
            message (str): Admin trade message
            
        Returns:
            dict: Parsed trade data or None if invalid
        """
        message = message.strip()
        
        match = self.trade_pattern.match(message)
        if not match:
            return None
        
        contract_address, entry_price_str, exit_price_str, tx_link = match.groups()
        
        try:
            entry_price = float(entry_price_str)
            exit_price = float(exit_price_str)
            
            # Calculate ROI
            roi_percentage = ((exit_price - entry_price) / entry_price) * 100
            
            return {
                'contract_address': contract_address,
                'entry_price': entry_price,
                'exit_price': exit_price,
                'roi_percentage': roi_percentage,
                'tx_link': tx_link or f"https://solscan.io/tx/generated_{int(datetime.utcnow().timestamp())}",
                'trade_type': 'exit'  # Always an exit since we have both entry and exit
            }
            
        except ValueError:
            return None
    
    def fetch_token_data(self, contract_address: str) -> Optional[Dict]:
        """
        Fetch comprehensive token data from DEX Screener
        
        Args:
            contract_address (str): Token contract address
            
        Returns:
            dict: Complete token and market data
        """
        try:
            market_data = dex_client.get_token_data(contract_address)
            
            if not market_data:
                logger.warning(f"No market data found for contract {contract_address}")
                return None
            
            # Extract comprehensive token data
            token_data = {
                # Basic token info (auto-discovered)
                'symbol': market_data.get('baseToken', {}).get('symbol', 'UNKNOWN'),
                'name': market_data.get('baseToken', {}).get('name', 'Unknown Token'),
                
                # Current market metrics
                'current_price_usd': float(market_data.get('priceUsd', 0)),
                'market_cap': float(market_data.get('marketCap', 0)) if market_data.get('marketCap') else 0,
                'volume_24h': float(market_data.get('volume', {}).get('h24', 0)),
                'liquidity_usd': float(market_data.get('liquidity', {}).get('usd', 0)),
                'fdv': float(market_data.get('fdv', 0)) if market_data.get('fdv') else 0,
                
                # Transaction metrics
                'txns_24h_buys': market_data.get('txns', {}).get('h24', {}).get('buys', 0),
                'txns_24h_sells': market_data.get('txns', {}).get('h24', {}).get('sells', 0),
                
                # Price changes
                'price_change_1h': market_data.get('priceChange', {}).get('h1', 0),
                'price_change_24h': market_data.get('priceChange', {}).get('h24', 0),
                
                # Pair info
                'pair_created_at': market_data.get('pairCreatedAt', int(datetime.utcnow().timestamp())),
                'dex_url': market_data.get('url', ''),
            }
            
            # Calculate total supply from market cap
            if token_data['current_price_usd'] > 0 and token_data['market_cap'] > 0:
                token_data['total_supply'] = token_data['market_cap'] / token_data['current_price_usd']
            elif token_data['fdv'] > 0 and token_data['current_price_usd'] > 0:
                token_data['total_supply'] = token_data['fdv'] / token_data['current_price_usd']
            else:
                # Default memecoin supply
                token_data['total_supply'] = 1_000_000_000
            
            return token_data
            
        except Exception as e:
            logger.error(f"Error fetching token data for {contract_address}: {str(e)}")
            return None
    
    def calculate_market_caps(self, token_data: Dict, entry_price: float, exit_price: float) -> Dict:
        """
        Calculate realistic market caps at entry and exit prices
        
        Args:
            token_data (dict): Token data from DEX Screener
            entry_price (float): Entry price
            exit_price (float): Exit price
            
        Returns:
            dict: Market cap calculations
        """
        total_supply = token_data['total_supply']
        
        return {
            'entry_market_cap': total_supply * entry_price,
            'exit_market_cap': total_supply * exit_price,
            'avg_exit_market_cap': total_supply * ((entry_price + exit_price) / 2)
        }
    
    def calculate_user_allocation(self, user_balance: float, roi_percentage: float) -> Dict:
        """
        Calculate user profit allocation based on existing balance system
        
        Args:
            user_balance (float): User's current balance
            roi_percentage (float): ROI from the trade
            
        Returns:
            dict: User allocation data
        """
        # Calculate profit using existing proportional system
        profit_amount = round(user_balance * (roi_percentage / 100), 4)
        
        # Risk allocation based on balance tiers (maintain existing logic)
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
        
        # Calculate SOL amounts spent
        spent_sol = round(user_balance * (risk_percent / 100), 4)
        
        return {
            'profit_amount': profit_amount,
            'risk_percentage': risk_percent,
            'spent_sol': spent_sol,
            'new_balance': user_balance + profit_amount
        }
    
    def calculate_token_amount(self, allocation: Dict, entry_price: float, exit_price: float) -> float:
        """
        Calculate realistic token amount based on user allocation
        
        Args:
            allocation (dict): User allocation data
            entry_price (float): Entry price
            exit_price (float): Exit price
            
        Returns:
            float: Token amount for the position
        """
        # Calculate token amount from spent SOL at entry price
        return allocation['spent_sol'] / entry_price
    
    def calculate_ownership_percentage(self, token_amount: float, total_supply: float, exit_market_cap: float) -> float:
        """
        Calculate realistic ownership percentage
        
        Args:
            token_amount (float): User's token amount
            total_supply (float): Total token supply
            exit_market_cap (float): Market cap at exit
            
        Returns:
            float: Ownership percentage
        """
        if total_supply <= 0:
            return 0.001  # Fallback
        
        ownership_pct = (token_amount / total_supply) * 100
        
        # Cap at realistic maximum ownership for retail traders
        return min(ownership_pct, 0.1)  # Max 0.1% ownership
    
    def generate_execution_metrics(self) -> Dict:
        """Generate realistic execution metrics"""
        return {
            'execution_speed': round(random.uniform(1.2, 2.8), 2),  # seconds
            'gas_cost': round(random.uniform(0.0008, 0.0015), 5),   # SOL
            'exit_reason': random.choice([
                "Take profit target (200%+ from entry)",
                "Volume exhaustion signal", 
                "Stop loss triggered",
                "Profit taking at resistance",
                "Risk management exit",
                "Market reversal detected"
            ])
        }
    
    def format_position_display(self, position: TradingPosition, token_data: Dict) -> str:
        """
        Format position in professional display format matching the example
        
        Args:
            position (TradingPosition): Trading position
            token_data (dict): Token data from DEX Screener
            
        Returns:
            str: Formatted position display
        """
        try:
            # Get current SOL price in USD
            sol_price_usd = self.get_sol_price()
            
            # Calculate USD values
            spent_usd = (position.entry_price * position.amount) * sol_price_usd
            exit_usd = (position.exit_price * position.amount) * sol_price_usd if position.exit_price else spent_usd
            
            # Calculate PNL
            pnl_sol = (position.exit_price - position.entry_price) * position.amount if position.exit_price else 0
            pnl_usd = pnl_sol * sol_price_usd
            pnl_percentage = position.roi_percentage if position.roi_percentage else 0
            
            # Format price display
            entry_price_display = f"${position.entry_price:.10f}".rstrip('0').rstrip('.')
            if position.entry_price < 0.0001:
                entry_price_display = f"$0.0(5){int(position.entry_price * 100000)}"
            
            exit_price_display = f"${position.exit_price:.6f}" if position.exit_price else "—"
            
            # Format market caps
            entry_mc = f"${position.market_cap_entry/1000:.1f}K" if position.market_cap_entry < 1000000 else f"${position.market_cap_entry/1000000:.1f}M"
            exit_mc = f"${position.market_cap_exit/1000:.1f}K" if position.market_cap_exit and position.market_cap_exit < 1000000 else f"${position.market_cap_exit/1000000:.1f}M"
            
            # PNL indicators
            pnl_indicator = "🟢" if pnl_percentage > 0 else "🔴"
            trend_indicator = "📈" if pnl_percentage > 0 else "📉"
            
            # Position display
            display = f"""${token_data['symbol']} - {trend_indicator} - {pnl_sol:.4f} SOL (${pnl_usd:.2f}) [Hide]
{position.contract_address}

• Price & MC: {entry_price_display} — {entry_mc}
• Avg Exit: {exit_price_display} — {exit_mc}
• Balance: {position.amount:.0f} ({position.ownership_percentage:.3f}%)
• Buys: {(position.entry_price * position.amount):.4f} SOL (${spent_usd:.2f}) • (1 buys)
• Sells: {(position.exit_price * position.amount):.4f} SOL (${exit_usd:.2f}) • (1 sells)
• PNL USD: {pnl_percentage:+.2f}% (${pnl_usd:+.2f}) {pnl_indicator}
• PNL SOL: {pnl_percentage:+.2f}% ({pnl_sol:+.4f} SOL) {pnl_indicator}

🔗 Sell TX: {position.sell_tx_hash or position.buy_tx_hash}
💰 Sold: 85% position ({position.amount * 0.85:.0f} tokens)
⚡ Speed: {position.execution_speed} seconds | Gas: {position.gas_cost:.5f} SOL
🎯 Exit Reason: {position.exit_reason}

💡 Click a token symbol to access the token's buy menu."""
            
            return display
            
        except Exception as e:
            logger.error(f"Error formatting position display: {str(e)}")
            return f"Error displaying position for {token_data.get('symbol', 'UNKNOWN')}"
    
    def process_trade(self, trade_data: Dict, admin_id: str, custom_timestamp: Optional[datetime] = None) -> Dict:
        """
        Process complete trade with DEX Screener integration and user allocation
        
        Args:
            trade_data (dict): Parsed trade data
            admin_id (str): Admin user ID
            custom_timestamp (datetime): Custom timestamp for the trade
            
        Returns:
            dict: Processing result
        """
        try:
            with app.app_context():
                # Fetch token data from DEX Screener
                token_data = self.fetch_token_data(trade_data['contract_address'])
                
                if not token_data:
                    return {
                        'success': False,
                        'error': f"Could not fetch token data for contract {trade_data['contract_address']}"
                    }
                
                # Calculate market caps
                market_caps = self.calculate_market_caps(
                    token_data, trade_data['entry_price'], trade_data['exit_price']
                )
                
                # Get active users with balance
                users = User.query.filter(
                    User.status == UserStatus.ACTIVE,
                    User.balance > 0
                ).all()
                
                if not users:
                    return {
                        'success': False,
                        'error': "No active users with balance found"
                    }
                
                processed_count = 0
                total_profit_distributed = 0
                trade_timestamp = custom_timestamp or datetime.utcnow()
                
                logger.info(f"Processing trade for {token_data['symbol']} with {len(users)} users")
                
                for user in users:
                    try:
                        # Calculate user allocation
                        allocation = self.calculate_user_allocation(
                            user.balance, trade_data['roi_percentage']
                        )
                        
                        if abs(allocation['profit_amount']) < 0.001:
                            continue  # Skip tiny allocations
                        
                        # Calculate token amount
                        token_amount = self.calculate_token_amount(
                            allocation, trade_data['entry_price'], trade_data['exit_price']
                        )
                        
                        # Calculate ownership percentage
                        ownership_pct = self.calculate_ownership_percentage(
                            token_amount, token_data['total_supply'], market_caps['exit_market_cap']
                        )
                        
                        # Generate execution metrics
                        metrics = self.generate_execution_metrics()
                        
                        # Create comprehensive trading position
                        position = TradingPosition(
                            user_id=user.id,
                            token_name=token_data['symbol'],
                            amount=token_amount,
                            entry_price=trade_data['entry_price'],
                            current_price=trade_data['exit_price'],
                            exit_price=trade_data['exit_price'],
                            timestamp=trade_timestamp,
                            buy_timestamp=trade_timestamp,
                            sell_timestamp=trade_timestamp,
                            status='closed',
                            trade_type='exit',
                            roi_percentage=trade_data['roi_percentage'],
                            buy_tx_hash=trade_data['tx_link'].split('/')[-1] if trade_data['tx_link'] else f"buy_{int(trade_timestamp.timestamp())}",
                            sell_tx_hash=trade_data['tx_link'].split('/')[-1] if trade_data['tx_link'] else f"sell_{int(trade_timestamp.timestamp())}",
                            admin_id=admin_id,
                            
                            # DEX Screener market data
                            contract_address=trade_data['contract_address'],
                            market_cap_entry=market_caps['entry_market_cap'],
                            market_cap_exit=market_caps['exit_market_cap'],
                            market_cap_avg_exit=market_caps['avg_exit_market_cap'],
                            volume_24h=token_data['volume_24h'],
                            liquidity_usd=token_data['liquidity_usd'],
                            ownership_percentage=ownership_pct,
                            total_supply=token_data['total_supply'],
                            buy_count_24h=token_data['txns_24h_buys'],
                            sell_count_24h=token_data['txns_24h_sells'],
                            execution_speed=metrics['execution_speed'],
                            gas_cost=metrics['gas_cost'],
                            exit_reason=metrics['exit_reason'],
                            price_usd_entry=token_data['current_price_usd'] * (trade_data['entry_price'] / trade_data['exit_price']),
                            price_usd_exit=token_data['current_price_usd']
                        )
                        
                        db.session.add(position)
                        
                        # Update user balance
                        user.balance += allocation['profit_amount']
                        total_profit_distributed += allocation['profit_amount']
                        
                        # Create profit record
                        if abs(allocation['profit_amount']) > 0.001:
                            profit_record = Profit(
                                user_id=user.id,
                                amount=allocation['profit_amount'],
                                percentage=trade_data['roi_percentage'],
                                date=trade_timestamp.date()
                            )
                            db.session.add(profit_record)
                        
                        # Create transaction record
                        transaction = Transaction(
                            user_id=user.id,
                            transaction_type='trade_profit' if allocation['profit_amount'] >= 0 else 'trade_loss',
                            amount=abs(allocation['profit_amount']),
                            token_name=token_data['symbol'],
                            timestamp=trade_timestamp,
                            status='completed',
                            notes=f"Trade ROI: {trade_data['roi_percentage']:.2f}% - {token_data['symbol']}",
                            tx_hash=f"{trade_data['tx_link'].split('/')[-1]}_u{user.id}" if trade_data['tx_link'] else f"trade_{int(trade_timestamp.timestamp())}_u{user.id}",
                            processed_at=trade_timestamp
                        )
                        db.session.add(transaction)
                        
                        processed_count += 1
                        
                        logger.info(f"Processed position for user {user.id}: {allocation['profit_amount']:.4f} SOL profit")
                        
                    except Exception as user_error:
                        logger.error(f"Error processing user {user.id}: {str(user_error)}")
                        continue
                
                db.session.commit()
                
                logger.info(f"Successfully processed {processed_count} positions for {token_data['symbol']}")
                
                return {
                    'success': True,
                    'message': f"Processed {processed_count} positions for {token_data['symbol']}",
                    'affected_count': processed_count,
                    'token_data': token_data,
                    'total_profit': total_profit_distributed,
                    'roi_percentage': trade_data['roi_percentage']
                }
                
        except Exception as e:
            logger.error(f"Error processing trade: {str(e)}")
            db.session.rollback()
            return {
                'success': False,
                'error': f"Error processing trade: {str(e)}"
            }