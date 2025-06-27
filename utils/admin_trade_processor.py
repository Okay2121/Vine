"""
Admin Trade Processor with Auto Trading Integration
Processes admin trade broadcasts and distributes to eligible users based on their auto trading settings
"""
import logging
from datetime import datetime
from typing import List, Tuple, Dict, Any
from app import db
from models import User, AutoTradingSettings, TradingPosition, Transaction, Profit
from utils.auto_trading_manager import AutoTradingManager

# Configure logging
logger = logging.getLogger(__name__)

class AdminTradeProcessor:
    """Processes admin trades and distributes to auto trading users"""
    
    @staticmethod
    def process_admin_trade_broadcast(token_name: str, trade_type: str, price: float, 
                                    tx_link: str, amount: float = None) -> Tuple[bool, str, int]:
        """
        Process admin trade broadcast and distribute to eligible users
        
        Args:
            token_name (str): Token symbol (e.g., "ZING")
            trade_type (str): "buy" or "sell"
            price (float): Trade price
            tx_link (str): Transaction link
            amount (float): Token amount (optional)
            
        Returns:
            tuple: (success, message, affected_users_count)
        """
        try:
            # Get all users with auto trading enabled and admin signals enabled
            eligible_users = AdminTradeProcessor.get_eligible_users_for_admin_trades()
            
            if not eligible_users:
                return True, "No eligible users for auto trading", 0
            
            processed_count = 0
            
            for user in eligible_users:
                try:
                    settings = AutoTradingManager.get_or_create_settings(user.id)
                    
                    if trade_type.lower() == "buy":
                        success = AdminTradeProcessor.process_buy_for_user(
                            user, settings, token_name, price, tx_link, amount
                        )
                    elif trade_type.lower() == "sell":
                        success = AdminTradeProcessor.process_sell_for_user(
                            user, settings, token_name, price, tx_link, amount
                        )
                    else:
                        logger.warning(f"Unknown trade type: {trade_type}")
                        continue
                    
                    if success:
                        processed_count += 1
                        
                        # Update auto trading stats
                        settings.total_auto_trades += 1
                        settings.last_trade_at = datetime.utcnow()
                        
                        # Increment successful trades for buy orders (sell success determined later)
                        if trade_type.lower() == "buy":
                            settings.successful_auto_trades += 1
                            
                        db.session.commit()
                        
                except Exception as e:
                    logger.error(f"Error processing admin trade for user {user.id}: {e}")
                    continue
            
            logger.info(f"Processed admin {trade_type} trade for {processed_count} users")
            return True, f"Successfully processed {trade_type} trade for {processed_count} users", processed_count
            
        except Exception as e:
            logger.error(f"Error processing admin trade broadcast: {e}")
            return False, f"Error processing trade: {str(e)}", 0
    
    @staticmethod
    def get_eligible_users_for_admin_trades() -> List[User]:
        """Get users eligible to receive admin trade signals"""
        try:
            # Query users with auto trading enabled and sufficient balance
            eligible_users = db.session.query(User).join(AutoTradingSettings).filter(
                AutoTradingSettings.is_enabled == True,
                AutoTradingSettings.admin_signals_enabled == True,
                User.balance >= 0.1  # Minimum balance requirement
            ).all()
            
            # Additional filtering for effective trading balance
            filtered_users = []
            for user in eligible_users:
                settings = user.auto_trading_settings[0] if user.auto_trading_settings else None
                if settings and settings.effective_trading_balance >= 0.05:
                    filtered_users.append(user)
            
            logger.info(f"Found {len(filtered_users)} eligible users for admin trades")
            return filtered_users
            
        except Exception as e:
            logger.error(f"Error getting eligible users: {e}")
            return []
    
    @staticmethod
    def process_buy_for_user(user: User, settings: AutoTradingSettings, 
                           token_name: str, price: float, tx_link: str, amount: float = None) -> bool:
        """Process a buy trade for a specific user"""
        try:
            # Check daily trade limits
            today = datetime.utcnow().date()
            daily_trades = TradingPosition.query.filter(
                TradingPosition.user_id == user.id,
                TradingPosition.timestamp >= today
            ).count()
            
            if daily_trades >= settings.max_daily_trades:
                logger.info(f"User {user.id} reached daily trade limit ({settings.max_daily_trades})")
                return False
            
            # Check maximum simultaneous positions
            open_positions = TradingPosition.query.filter(
                TradingPosition.user_id == user.id,
                TradingPosition.status == 'open'
            ).count()
            
            if open_positions >= settings.max_simultaneous_positions:
                logger.info(f"User {user.id} reached max simultaneous positions ({settings.max_simultaneous_positions})")
                return False
            
            # Calculate position size
            position_value = settings.max_position_size
            token_amount = position_value / price if price > 0 else 0
            
            if token_amount <= 0:
                logger.warning(f"Invalid token amount calculated for user {user.id}")
                return False
            
            # Create trading position
            position = TradingPosition()
            position.user_id = user.id
            position.token_name = token_name
            position.amount = token_amount
            position.entry_price = price
            position.current_price = price
            position.timestamp = datetime.utcnow()
            position.status = 'open'
            position.trade_type = 'admin_signal'
            position.notes = f"Admin broadcast buy signal - {tx_link}"
            
            db.session.add(position)
            
            # Create buy transaction record
            transaction = Transaction()
            transaction.user_id = user.id
            transaction.transaction_type = 'trade_entry'
            transaction.amount = -position_value  # Negative for buy
            transaction.token_name = token_name
            transaction.timestamp = datetime.utcnow()
            transaction.status = 'completed'
            transaction.notes = f"Auto-follow admin buy signal: {token_name} at {price:.6f}"
            
            db.session.add(transaction)
            
            # Update user balance (deduct position value)
            user.balance -= position_value
            
            logger.info(f"Created buy position for user {user.id}: {token_amount:.2f} {token_name} at {price:.6f}")
            return True
            
        except Exception as e:
            logger.error(f"Error processing buy for user {user.id}: {e}")
            return False
    
    @staticmethod
    def process_sell_for_user(user: User, settings: AutoTradingSettings,
                            token_name: str, price: float, tx_link: str, amount: float = None) -> bool:
        """Process a sell trade for a specific user"""
        try:
            # Find open positions for this token
            open_positions = TradingPosition.query.filter(
                TradingPosition.user_id == user.id,
                TradingPosition.token_name == token_name,
                TradingPosition.status == 'open'
            ).order_by(TradingPosition.timestamp.asc()).all()
            
            if not open_positions:
                logger.info(f"No open positions found for user {user.id} in {token_name}")
                # Still count as processed since user followed the signal
                return True
            
            total_profit = 0
            positions_closed = 0
            
            for position in open_positions:
                # Calculate profit/loss
                position_value = position.amount * position.entry_price
                sell_value = position.amount * price
                profit_amount = sell_value - position_value
                roi_percentage = (profit_amount / position_value) * 100 if position_value > 0 else 0
                
                # Update position
                position.current_price = price
                position.status = 'closed'
                position.roi_percentage = roi_percentage
                position.notes += f" | Closed via admin sell signal at {price:.6f}"
                
                # Create sell transaction
                transaction = Transaction()
                transaction.user_id = user.id
                transaction.transaction_type = 'trade_profit' if profit_amount >= 0 else 'trade_loss'
                transaction.amount = sell_value  # Positive for sell proceeds
                transaction.token_name = token_name
                transaction.timestamp = datetime.utcnow()
                transaction.status = 'completed'
                transaction.notes = f"Auto-follow admin sell signal: {token_name} at {price:.6f} (ROI: {roi_percentage:.1f}%)"
                
                db.session.add(transaction)
                
                # Update user balance (add sell proceeds)
                user.balance += sell_value
                total_profit += profit_amount
                positions_closed += 1
                
                # Create profit record for tracking
                if profit_amount != 0:  # Only create if there's actual profit/loss
                    profit_record = Profit()
                    profit_record.user_id = user.id
                    profit_record.amount = profit_amount
                    profit_record.percentage = roi_percentage
                    profit_record.date = datetime.utcnow().date()
                    
                    db.session.add(profit_record)
                
                # Update success rate if profitable
                if profit_amount > 0:
                    settings.successful_auto_trades += 1
            
            logger.info(f"Closed {positions_closed} positions for user {user.id}: total profit {total_profit:.6f} SOL")
            return True
            
        except Exception as e:
            logger.error(f"Error processing sell for user {user.id}: {e}")
            return False
    
    @staticmethod
    def get_auto_trading_summary() -> Dict[str, Any]:
        """Get summary of auto trading activity"""
        try:
            # Count total auto trading users
            total_auto_users = AutoTradingSettings.query.filter(
                AutoTradingSettings.is_enabled == True
            ).count()
            
            # Count users with admin signals enabled
            admin_signal_users = AutoTradingSettings.query.filter(
                AutoTradingSettings.is_enabled == True,
                AutoTradingSettings.admin_signals_enabled == True
            ).count()
            
            # Get eligible users (with sufficient balance)
            eligible_users = len(AdminTradeProcessor.get_eligible_users_for_admin_trades())
            
            # Calculate average success rate
            settings_with_trades = AutoTradingSettings.query.filter(
                AutoTradingSettings.total_auto_trades > 0
            ).all()
            
            if settings_with_trades:
                avg_success_rate = sum(s.success_rate for s in settings_with_trades) / len(settings_with_trades)
            else:
                avg_success_rate = 0
            
            # Count recent trades (last 24 hours)
            from datetime import timedelta
            yesterday = datetime.utcnow() - timedelta(days=1)
            
            recent_auto_trades = TradingPosition.query.filter(
                TradingPosition.trade_type == 'admin_signal',
                TradingPosition.timestamp >= yesterday
            ).count()
            
            return {
                'total_auto_users': total_auto_users,
                'admin_signal_users': admin_signal_users,
                'eligible_users': eligible_users,
                'avg_success_rate': avg_success_rate,
                'recent_trades_24h': recent_auto_trades
            }
            
        except Exception as e:
            logger.error(f"Error getting auto trading summary: {e}")
            return {
                'total_auto_users': 0,
                'admin_signal_users': 0,
                'eligible_users': 0,
                'avg_success_rate': 0,
                'recent_trades_24h': 0
            }
    
    @staticmethod
    def check_and_apply_stop_loss(user_id: int) -> int:
        """Check and apply stop loss for user's open positions"""
        try:
            settings = AutoTradingManager.get_or_create_settings(user_id)
            
            open_positions = TradingPosition.query.filter(
                TradingPosition.user_id == user_id,
                TradingPosition.status == 'open'
            ).all()
            
            stopped_out = 0
            
            for position in open_positions:
                # Calculate current loss percentage
                loss_percentage = ((position.entry_price - position.current_price) / position.entry_price) * 100
                
                if loss_percentage >= settings.stop_loss_percentage:
                    # Execute stop loss
                    position.status = 'closed'
                    position.notes += f" | Stop loss triggered at -{loss_percentage:.1f}%"
                    
                    # Create stop loss transaction
                    sell_value = position.amount * position.current_price
                    loss_amount = sell_value - (position.amount * position.entry_price)
                    
                    transaction = Transaction()
                    transaction.user_id = user_id
                    transaction.transaction_type = 'trade_loss'
                    transaction.amount = loss_amount
                    transaction.token_name = position.token_name
                    transaction.timestamp = datetime.utcnow()
                    transaction.status = 'completed'
                    transaction.notes = f"Auto stop loss: {position.token_name} at -{loss_percentage:.1f}%"
                    
                    db.session.add(transaction)
                    
                    # Update user balance
                    user = User.query.get(user_id)
                    if user:
                        user.balance += sell_value
                    
                    stopped_out += 1
            
            if stopped_out > 0:
                db.session.commit()
                logger.info(f"Applied stop loss to {stopped_out} positions for user {user_id}")
            
            return stopped_out
            
        except Exception as e:
            logger.error(f"Error checking stop loss for user {user_id}: {e}")
            return 0