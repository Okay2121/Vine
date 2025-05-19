#!/usr/bin/env python
"""
Script to check auto-trading status and simulate a trade if needed
"""
import logging
from datetime import datetime
from app import app, db
from models import User, Transaction, Profit

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Constant for the operation
USERNAME = "@briensmart"

def find_user_by_username(username):
    """Find a user by their Telegram username"""
    # Remove @ if present
    if username.startswith('@'):
        username = username[1:]
    
    # Try to find the user
    user = User.query.filter(User.username.ilike(username)).first()
    return user

def check_auto_trading_status():
    """Check if auto-trading is active for the user"""
    with app.app_context():
        # Find the user
        user = find_user_by_username(USERNAME)
        
        if not user:
            logger.error(f"User {USERNAME} not found")
            return False
        
        # Display user info
        logger.info(f"User: {user.username} (ID: {user.id})")
        logger.info(f"Current Balance: {user.balance:.4f} SOL")
        
        # Try to import the auto trading module
        try:
            from utils.auto_trading_history import is_auto_trading_active_for_user, simulate_trade_now
            
            # Check if auto trading is active
            is_active = is_auto_trading_active_for_user(user.id)
            logger.info(f"Auto-trading active: {is_active}")
            
            # Count buy/sell transactions to see if any trades were generated
            buy_count = Transaction.query.filter_by(user_id=user.id, transaction_type="buy").count()
            sell_count = Transaction.query.filter_by(user_id=user.id, transaction_type="sell").count()
            profit_count = Profit.query.filter_by(user_id=user.id).count()
            
            logger.info(f"Buy transactions: {buy_count}")
            logger.info(f"Sell transactions: {sell_count}")
            logger.info(f"Profit records: {profit_count}")
            
            # If no trades have been generated yet, manually trigger one for testing
            if buy_count == 0 and is_active:
                logger.info("No trades found. Manually simulating a trade...")
                simulate_trade_now(user.id)
                logger.info("Trade simulation completed.")
                
                # Recount transactions
                buy_count = Transaction.query.filter_by(user_id=user.id, transaction_type="buy").count()
                sell_count = Transaction.query.filter_by(user_id=user.id, transaction_type="sell").count()
                profit_count = Profit.query.filter_by(user_id=user.id).count()
                
                logger.info(f"After simulation - Buy transactions: {buy_count}")
                logger.info(f"After simulation - Sell transactions: {sell_count}")
                logger.info(f"After simulation - Profit records: {profit_count}")
            
            return True
        except ImportError as e:
            logger.error(f"Could not import auto trading module: {e}")
            return False
        except Exception as e:
            logger.error(f"Error checking auto trading status: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

if __name__ == "__main__":
    # Run the verification
    check_auto_trading_status()