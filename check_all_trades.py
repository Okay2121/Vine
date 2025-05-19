#!/usr/bin/env python
"""
Script to check all transactions and trade history for a user
"""
import logging
from app import app, db
from models import User, Transaction, Profit
from datetime import datetime

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

def check_user_details():
    """Check the user's current balance and full transaction history"""
    with app.app_context():
        # Find the user
        user = find_user_by_username(USERNAME)
        
        if not user:
            logger.error(f"User {USERNAME} not found")
            return False
        
        # Display user info
        logger.info(f"USER DETAILS")
        logger.info(f"=============")
        logger.info(f"Username: {user.username} (ID: {user.id}, Telegram ID: {user.telegram_id})")
        logger.info(f"Current Balance: {user.balance:.4f} SOL")
        logger.info(f"Initial Deposit: {user.initial_deposit:.4f} SOL")
        logger.info(f"Joined: {user.joined_at}")
        logger.info(f"Last Activity: {user.last_activity}")
        logger.info(f"Status: {user.status}")
        logger.info("")
        
        # Get and display all transactions
        all_transactions = Transaction.query.filter_by(user_id=user.id).order_by(Transaction.timestamp.desc()).all()
        
        logger.info(f"TRANSACTION HISTORY ({len(all_transactions)} records)")
        logger.info(f"===================")
        
        if all_transactions:
            for tx in all_transactions:
                tx_type = tx.transaction_type.upper()
                date_str = tx.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                
                if tx.transaction_type in ['buy', 'sell']:
                    logger.info(f"[{date_str}] {tx_type}: {tx.amount:.4f} SOL - {tx.token_name}")
                else:
                    logger.info(f"[{date_str}] {tx_type}: {tx.amount:.4f} SOL")
                
                logger.info(f"   Status: {tx.status}")
                
                if tx.notes:
                    logger.info(f"   Notes: {tx.notes}")
                
                logger.info("")
        else:
            logger.info("No transactions found")
            
        # Get and display all profit records
        all_profits = Profit.query.filter_by(user_id=user.id).order_by(Profit.date.desc()).all()
        
        logger.info(f"PROFIT HISTORY ({len(all_profits)} records)")
        logger.info(f"===============")
        
        if all_profits:
            total_profit = 0
            
            for profit in all_profits:
                date_str = profit.date.strftime("%Y-%m-%d")
                prefix = "+" if profit.amount > 0 else ""
                profit_str = f"{prefix}{profit.amount:.4f} SOL ({profit.percentage:.2f}%)"
                logger.info(f"[{date_str}] {profit_str}")
                total_profit += profit.amount
            
            logger.info("")
            logger.info(f"Total Profit: {total_profit:.4f} SOL")
        else:
            logger.info("No profit records found")
            
        # Calculate ROI
        if user.initial_deposit > 0:
            total_profit = user.balance - user.initial_deposit
            roi_percent = (total_profit / user.initial_deposit) * 100
            logger.info(f"ROI: {roi_percent:.2f}% on {user.initial_deposit:.4f} SOL initial deposit")
        
        return True

if __name__ == "__main__":
    # Run the verification
    check_user_details()