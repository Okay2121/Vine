#!/usr/bin/env python
"""
Script to implement a proper admin balance adjustment function
that can find users case-insensitively
"""
import logging
import sys
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

# Parameters for the adjustment
USERNAME = "@briensmart"  # The username to adjust (case-insensitive)
ADJUSTMENT_AMOUNT = 0.5  # Amount to add (in SOL)
ADJUSTMENT_REASON = "Testing balance adjustment"

def find_user_by_username_case_insensitive(username):
    """Find a user by their Telegram username (case-insensitive)"""
    with app.app_context():
        # Remove @ if present
        if username.startswith('@'):
            username = username[1:]
        
        # Try case-insensitive search
        user = User.query.filter(func.lower(User.username) == func.lower(username)).first()
        return user

def apply_balance_adjustment():
    """Apply balance adjustment to the specified user"""
    with app.app_context():
        # Find the user
        user = find_user_by_username_case_insensitive(USERNAME)
        
        if not user:
            logger.error(f"User {USERNAME} not found")
            return False
        
        # Log user info
        logger.info(f"Found user: @{user.username} (ID: {user.id}, Telegram ID: {user.telegram_id})")
        logger.info(f"Current balance: {user.balance:.4f} SOL")
        
        # Save old balance for reporting
        old_balance = user.balance
        
        try:
            # Update user balance
            user.balance += ADJUSTMENT_AMOUNT
            
            # Create transaction record
            transaction_type = 'admin_credit' if ADJUSTMENT_AMOUNT > 0 else 'admin_debit'
            
            # Create the transaction record
            new_transaction = Transaction(
                user_id=user.id,
                transaction_type=transaction_type,
                amount=abs(ADJUSTMENT_AMOUNT),
                token_name="SOL",
                timestamp=datetime.utcnow(),
                status='completed',
                notes=ADJUSTMENT_REASON
            )
            
            # Add and commit transaction
            db.session.add(new_transaction)
            db.session.commit()
            
            # Log success
            logger.info(f"Balance adjustment successful!")
            logger.info(f"Old balance: {old_balance:.4f} SOL")
            logger.info(f"New balance: {user.balance:.4f} SOL")
            logger.info(f"Change: {'➕' if ADJUSTMENT_AMOUNT > 0 else '➖'} {abs(ADJUSTMENT_AMOUNT):.4f} SOL")
            logger.info(f"Transaction ID: {new_transaction.id}")
            
            # Provide SQL to use in bot_v20_runner.py
            logger.info("\nSQL for case-insensitive search:")
            logger.info("=================================")
            logger.info("from sqlalchemy import func")
            logger.info("# If not found by telegram_id, try by username (case-insensitive)")
            logger.info("if not user and text.startswith('@'):")
            logger.info("    username = text[1:]  # Remove @ prefix")
            logger.info("    user = User.query.filter(func.lower(User.username) == func.lower(username)).first()")
            logger.info("elif not user:")
            logger.info("    # Try with username anyway (in case they forgot the @)")
            logger.info("    user = User.query.filter(func.lower(User.username) == func.lower(text)).first()")
            
            return True
            
        except Exception as e:
            # Handle errors
            db.session.rollback()
            logger.error(f"Error during balance adjustment: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

if __name__ == "__main__":
    # Apply the balance adjustment
    success = apply_balance_adjustment()
    sys.exit(0 if success else 1)