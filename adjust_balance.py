#!/usr/bin/env python
"""
Script to adjust a user's balance and create a trade record
"""
import logging
import sys
from datetime import datetime
from app import app, db
from models import User, Transaction

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Constants for the operation
USERNAME = "@briensmart"
ADJUSTMENT_AMOUNT = 10.0  # SOL
ADJUSTMENT_REASON = "Test Deposit"
TRANSACTION_TYPE = "admin_credit"

def find_user_by_username(username):
    """Find a user by their Telegram username"""
    # Remove @ if present
    if username.startswith('@'):
        username = username[1:]
    
    # Try to find the user
    user = User.query.filter(User.username.ilike(username)).first()
    return user

def create_user_if_missing(username):
    """Create a user if they don't exist"""
    # Check if user exists
    user = find_user_by_username(username)
    
    if user:
        logger.info(f"User {username} already exists with ID {user.id}")
        return user
    
    # Create new user - we need to generate a fake telegram_id since it's required
    import random
    telegram_id = str(random.randint(10000000, 99999999))
    
    # Create user
    if username.startswith('@'):
        clean_username = username[1:]
    else:
        clean_username = username
    
    new_user = User(
        telegram_id=telegram_id,
        username=clean_username,
        first_name=clean_username,
        balance=0.0
    )
    
    # Save user
    db.session.add(new_user)
    db.session.commit()
    
    logger.info(f"Created new user {clean_username} with ID {new_user.id}")
    return new_user

def adjust_balance_and_create_record():
    """Main function to adjust balance and create transaction record"""
    with app.app_context():
        # Find or create user
        user = create_user_if_missing(USERNAME)
        
        if not user:
            logger.error(f"Failed to find or create user {USERNAME}")
            return False
        
        try:
            # Store old balance for reporting
            old_balance = user.balance
            
            # Update user balance
            user.balance += ADJUSTMENT_AMOUNT
            
            # Create transaction record
            new_transaction = Transaction()
            new_transaction.user_id = user.id
            new_transaction.transaction_type = TRANSACTION_TYPE
            new_transaction.amount = ADJUSTMENT_AMOUNT
            new_transaction.token_name = "SOL"
            new_transaction.timestamp = datetime.utcnow()
            new_transaction.status = 'completed'
            new_transaction.notes = ADJUSTMENT_REASON
            
            # Add and commit transaction
            db.session.add(new_transaction)
            db.session.commit()
            
            logger.info(f"Balance adjustment successful")
            logger.info(f"User: {user.username} (ID: {user.id})")
            logger.info(f"Old balance: {old_balance:.4f} SOL")
            logger.info(f"New balance: {user.balance:.4f} SOL")
            logger.info(f"Adjustment: +{ADJUSTMENT_AMOUNT:.4f} SOL")
            logger.info(f"Transaction ID: {new_transaction.id}")
            
            # Trigger auto trading based on the balance adjustment
            try:
                from utils.auto_trading_history import handle_admin_balance_adjustment
                handle_admin_balance_adjustment(user.id, ADJUSTMENT_AMOUNT)
                logger.info(f"Auto trading history started for user {user.id} after balance adjustment")
            except Exception as trading_error:
                logger.error(f"Failed to start auto trading history for user {user.id}: {trading_error}")
                # Don't fail the balance adjustment process if auto trading fails
            
            return True
            
        except Exception as e:
            # Handle errors
            db.session.rollback()
            logger.error(f"Error during balance adjustment: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

if __name__ == "__main__":
    # Run the balance adjustment
    success = adjust_balance_and_create_record()
    sys.exit(0 if success else 1)