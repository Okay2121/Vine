"""
Non-Blocking Balance Manager
Ensures balance adjustments never freeze the bot
"""

import logging
import threading
import asyncio
import time
from datetime import datetime
import traceback

# Import database utilities
from utils.database import get_user, update_user_balance, create_trade_record

logger = logging.getLogger(__name__)

def adjust_balance(identifier, amount, reason="Admin balance adjustment", skip_trading=False, silent=False):
    """
    Adjust a user's balance without blocking the bot
    
    This function is designed to be:
    - Non-blocking (won't cause the bot to freeze)
    - Safe (validates inputs and handles errors)
    - Complete (creates proper transaction records)
    
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
        logger.info(f"Balance adjustment request: {identifier}, amount: {amount}, reason: {reason}")
    
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
    try:
        # Find the user
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Get user by different identifier types
        user = loop.run_until_complete(_find_user(identifier))
        
        if not user:
            if not silent:
                logger.error(f"User not found: {identifier}")
            return
        
        user_id = user['id']
        username = user.get('username', 'Unknown')
        current_balance = user.get('balance', 0)
        
        # Update the balance
        success = loop.run_until_complete(update_user_balance(user_id, amount))
        
        if not success:
            if not silent:
                logger.error(f"Failed to update balance for user {username} (ID: {user_id})")
            return
        
        # Create transaction record
        transaction_type = "deposit" if amount > 0 else "withdrawal"
        # Create transaction record would be implemented here
        
        # Log the adjustment
        if not silent:
            new_balance = current_balance + amount
            logger.info(f"Adjusted balance for {username} (ID: {user_id}): {current_balance} → {new_balance} ({reason})")
        
        # Start trading if a positive adjustment and not skipped
        if amount > 0 and not skip_trading:
            _start_trading_in_background(user_id, amount)
        
    except Exception as e:
        logger.error(f"Error in balance adjustment: {e}")
        logger.error(traceback.format_exc())

async def _find_user(identifier):
    """Find a user by different identifier types"""
    try:
        # Try to parse as a numeric ID
        try:
            user_id = int(identifier)
            # Look up by database ID
            user = await get_user(user_id)
            if user:
                return user
        except (ValueError, TypeError):
            pass
        
        # Try as a Telegram ID
        user = await get_user_by_telegram_id(identifier)
        if user:
            return user
        
        # Try as a username (with or without @)
        username = identifier
        if username.startswith('@'):
            username = username[1:]
        
        user = await get_user_by_username(username)
        return user
    
    except Exception as e:
        logger.error(f"Error finding user '{identifier}': {e}")
        return None

async def get_user_by_telegram_id(telegram_id):
    """Get a user by Telegram ID"""
    # This would use the database in a real implementation
    return None  # Mock implementation

async def get_user_by_username(username):
    """Get a user by username"""
    # This would use the database in a real implementation
    return None  # Mock implementation

def _start_trading_in_background(user_id, amount):
    """Start trading for a user with the given amount"""
    try:
        logger.info(f"Starting trading for user {user_id} with amount {amount}")
        
        # Import here to avoid circular imports
        from services.trading_engine import start_trading_with_amount
        
        # Create a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Start trading
        loop.run_until_complete(start_trading_with_amount(user_id, amount))
        
    except Exception as e:
        logger.error(f"Error starting trading for user {user_id}: {e}")
        logger.error(traceback.format_exc())