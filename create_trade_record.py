#!/usr/bin/env python
"""
Script to create a specific trade record in the trading history
"""
import logging
import sys
from datetime import datetime, timedelta
from app import app, db
from models import User, Transaction, Profit

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Constants for the operation
USERNAME = "@briensmart"
TRADE_AMOUNT = 5.0  # SOL - use half of the deposited amount
TOKEN_NAME = "BONK"
TOKEN_SYMBOL = "BONK"
PROFIT_PERCENT = 12.5  # A reasonable profit percentage
COMMENT = "Test Deposit"

def find_user_by_username(username):
    """Find a user by their Telegram username"""
    # Remove @ if present
    if username.startswith('@'):
        username = username[1:]
    
    # Try to find the user
    user = User.query.filter(User.username.ilike(username)).first()
    return user

def create_trade_record():
    """Create a trade record for the user with buy, sell transactions and profit"""
    with app.app_context():
        # Find the user
        user = find_user_by_username(USERNAME)
        
        if not user:
            logger.error(f"User {USERNAME} not found")
            return False
        
        try:
            # Calculate values for the trade
            entry_time = datetime.utcnow() - timedelta(hours=1)  # 1 hour ago
            exit_time = datetime.utcnow()  # now
            entry_price = 0.00000325  # Example price
            exit_price = entry_price * (1 + (PROFIT_PERCENT / 100))
            profit_amount = TRADE_AMOUNT * (PROFIT_PERCENT / 100)
            
            # Create the buy transaction
            buy_transaction = Transaction(
                user_id=user.id,
                transaction_type="buy",
                amount=TRADE_AMOUNT,
                token_name=f"{TOKEN_NAME} ({TOKEN_SYMBOL})",
                timestamp=entry_time,
                status="completed",
                notes=f"Auto trade entry at {entry_price:.8f} USD - {COMMENT}"
            )
            
            # Create the sell transaction
            sell_transaction = Transaction(
                user_id=user.id,
                transaction_type="sell",
                amount=TRADE_AMOUNT + profit_amount,
                token_name=f"{TOKEN_NAME} ({TOKEN_SYMBOL})",
                timestamp=exit_time,
                status="completed",
                notes=f"Auto trade exit at {exit_price:.8f} USD - {COMMENT}"
            )
            
            # Create the profit record
            profit_record = Profit(
                user_id=user.id,
                amount=profit_amount,
                percentage=PROFIT_PERCENT,
                date=exit_time.date()
            )
            
            # Add records to database
            db.session.add(buy_transaction)
            db.session.add(sell_transaction)
            db.session.add(profit_record)
            
            # Update user balance with the profit
            user.balance += profit_amount
            
            # Commit the changes
            db.session.commit()
            
            logger.info(f"Trade record created successfully")
            logger.info(f"Buy Transaction ID: {buy_transaction.id}")
            logger.info(f"Sell Transaction ID: {sell_transaction.id}")
            logger.info(f"Profit Record ID: {profit_record.id}")
            logger.info(f"Profit Amount: {profit_amount:.4f} SOL ({PROFIT_PERCENT}%)")
            logger.info(f"New Balance: {user.balance:.4f} SOL")
            
            return True
        
        except Exception as e:
            # Handle errors
            db.session.rollback()
            logger.error(f"Error creating trade record: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

if __name__ == "__main__":
    # Create the trade record
    success = create_trade_record()
    sys.exit(0 if success else 1)