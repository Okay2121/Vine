#!/usr/bin/env python
"""
Script to verify a user's balance and transaction history
"""
import logging
from app import app, db
from models import User, Transaction

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

def check_user_balance_and_history():
    """Check the user's current balance and transaction history"""
    with app.app_context():
        # Find the user
        user = find_user_by_username(USERNAME)
        
        if not user:
            logger.error(f"User {USERNAME} not found")
            return False
        
        # Display user info
        logger.info(f"User: {user.username} (ID: {user.id}, Telegram ID: {user.telegram_id})")
        logger.info(f"Current Balance: {user.balance:.4f} SOL")
        
        # Get and display transactions
        transactions = Transaction.query.filter_by(user_id=user.id).order_by(Transaction.timestamp.desc()).all()
        
        if transactions:
            logger.info(f"Transaction History for {user.username}:")
            for tx in transactions:
                tx_type = tx.transaction_type.upper()
                amount_str = f"+{tx.amount:.4f}" if tx.transaction_type == "admin_credit" else f"{tx.amount:.4f}"
                logger.info(f"[{tx.timestamp}] {tx_type}: {amount_str} SOL - {tx.token_name} - Status: {tx.status} - Notes: {tx.notes}")
        else:
            logger.info(f"No transactions found for {user.username}")
            
        return True

if __name__ == "__main__":
    # Run the verification
    check_user_balance_and_history()