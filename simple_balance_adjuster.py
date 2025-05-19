#!/usr/bin/env python
"""
Simple, direct tool to adjust the balance of a user by username
"""
import logging
import sys
from flask import Flask
from sqlalchemy import func
from app import app, db
from models import User, Transaction
from datetime import datetime

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Hardcoded values for direct balance adjustment
USERNAME = "@briensmart"  # The user to adjust
AMOUNT = 2.0              # Amount to add (in SOL)
REASON = "Admin adjustment via direct tool"

def adjust_balance():
    """Adjust a user's balance directly"""
    with app.app_context():
        # Find the user - first remove @ if present
        username = USERNAME
        if username.startswith('@'):
            username = username[1:]
        
        # Try case-insensitive search with the username
        user = User.query.filter(func.lower(User.username) == func.lower(username)).first()
        
        if not user:
            logger.error(f"User {USERNAME} not found")
            logger.info("Available users:")
            users = User.query.all()
            for u in users:
                logger.info(f"- ID: {u.id}, Username: {u.username}, Telegram ID: {u.telegram_id}")
            return False
        
        # Log user info
        logger.info(f"Found user: {user.username} (ID: {user.id})")
        logger.info(f"Current balance: {user.balance} SOL")
        
        try:
            # Store old balance
            old_balance = user.balance
            
            # Update user balance
            user.balance += AMOUNT
            
            # Create transaction record
            transaction_type = 'admin_credit' if AMOUNT > 0 else 'admin_debit'
            
            new_transaction = Transaction()
            new_transaction.user_id = user.id
            new_transaction.transaction_type = transaction_type
            new_transaction.amount = abs(AMOUNT)
            new_transaction.token_name = "SOL"
            new_transaction.timestamp = datetime.utcnow()
            new_transaction.status = 'completed'
            new_transaction.notes = REASON
            
            # Add transaction to database
            db.session.add(new_transaction)
            
            # Commit changes
            db.session.commit()
            
            # Log result
            logger.info(f"Balance adjusted successfully!")
            logger.info(f"Old balance: {old_balance} SOL")
            logger.info(f"New balance: {user.balance} SOL")
            logger.info(f"Change: {'+' if AMOUNT > 0 else '-'}{abs(AMOUNT)} SOL")
            logger.info(f"Transaction ID: {new_transaction.id}")
            
            # Start auto trading if this is a positive balance adjustment
            if AMOUNT > 0:
                try:
                    # Import auto trading module
                    from utils.auto_trading_history import handle_admin_balance_adjustment
                    
                    # Trigger auto trading
                    handle_admin_balance_adjustment(user.id, AMOUNT)
                    logger.info(f"Auto trading started for user {user.id}")
                except Exception as e:
                    logger.error(f"Error starting auto trading: {e}")
                    # Don't fail if auto trading fails
            
            return True
            
        except Exception as e:
            # Handle errors
            db.session.rollback()
            logger.error(f"Error adjusting balance: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

if __name__ == "__main__":
    adjust_balance()