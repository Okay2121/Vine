"""
Non-Blocking Balance Manager for Solana Memecoin Trading Bot
-------------------------------------------------------------
This module prevents freezing when performing balance adjustments.
It works by running the actual balance operations in a background thread.
"""

import logging
import threading
import time
from datetime import datetime
import traceback

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def adjust_balance(identifier, amount, reason="Admin balance adjustment", skip_trading=False, silent=False):
    """
    Adjust a user's balance without blocking the bot
    
    Args:
        identifier (str): Username, telegram_id, or database ID
        amount (float): Amount to adjust (positive to add, negative to deduct)
        reason (str): Reason for the adjustment
        skip_trading (bool): If True, don't trigger auto trading even for positive adjustments
        silent (bool): If True, don't log the adjustment to console
        
    Returns:
        tuple: (success, message)
    """
    if not silent:
        logger.info(f"Starting non-blocking balance adjustment: {identifier}, amount: {amount}, reason: {reason}")
    
    # Run the actual adjustment in a background thread
    thread = threading.Thread(
        target=_process_balance_adjustment,
        args=(identifier, amount, reason, skip_trading, silent),
        daemon=True
    )
    thread.start()
    
    # Return immediately to prevent bot freezing
    return True, "Balance adjustment is being processed in the background."

def _process_balance_adjustment(identifier, amount, reason, skip_trading, silent):
    """Background worker for balance adjustments"""
    from app import app, db
    from models import User, Transaction
    
    try:
        with app.app_context():
            # Find the user
            user = None
            
            # Try as database ID
            try:
                user_id = int(identifier)
                user = User.query.filter_by(id=user_id).first()
            except (ValueError, TypeError):
                pass
                
            if not user:
                # Try as telegram ID
                user = User.query.filter_by(telegram_id=str(identifier)).first()
            
            if not user:
                # Try as username (case insensitive)
                username = identifier
                if username.startswith('@'):
                    username = username[1:]
                user = User.query.filter(User.username.ilike(username)).first()
            
            if not user:
                if not silent:
                    logger.error(f"User not found: {identifier}")
                return False, f"User not found: {identifier}"
            
            # Update the balance
            try:
                current_balance = user.balance or 0
                new_balance = current_balance + amount
                user.balance = new_balance
                
                # Create transaction record
                transaction_type = 'deposit' if amount > 0 else 'withdrawal'
                transaction = Transaction(
                    user_id=user.id,
                    amount=abs(amount),
                    type=transaction_type,
                    status='completed',
                    description=reason,
                    created_at=datetime.utcnow()
                )
                
                db.session.add(transaction)
                db.session.commit()
                
                # Log the adjustment
                if not silent:
                    logger.info(f"Balance adjusted for {user.username} (ID: {user.id}): {current_balance} → {new_balance} ({reason})")
                
                # Start trading if a positive adjustment and not skipped
                if amount > 0 and not skip_trading:
                    # Importing here to avoid circular imports
                    from utils.trading import process_new_deposit
                    
                    # Start trading in background to avoid blocking
                    trading_thread = threading.Thread(
                        target=_start_trading_in_background,
                        args=(user.id, amount),
                        daemon=True
                    )
                    trading_thread.start()
                
                return True, f"Balance adjusted to {new_balance}"
                
            except Exception as e:
                db.session.rollback()
                logger.error(f"Error adjusting balance: {e}")
                logger.error(traceback.format_exc())
                return False, f"Error adjusting balance: {str(e)}"
    
    except Exception as e:
        logger.error(f"Error in balance adjustment: {e}")
        logger.error(traceback.format_exc())
        return False, f"Error in balance adjustment: {str(e)}"

def _start_trading_in_background(user_id, amount):
    """Start trading for a user with the given amount"""
    from app import app
    
    try:
        with app.app_context():
            logger.info(f"Starting trading for user {user_id} with amount {amount}")
            
            # Import here to avoid circular imports
            from utils.trading import process_new_deposit
            
            # Process the deposit as if it were a new deposit
            process_new_deposit(user_id, amount)
            
    except Exception as e:
        logger.error(f"Error starting trading for user {user_id}: {e}")
        logger.error(traceback.format_exc())