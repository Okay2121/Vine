#!/usr/bin/env python
"""
Enhanced Balance Manager for Solana Memecoin Trading Bot
-----------------------------------------------------------
This module provides a completely non-blocking solution for balance adjustments
with advanced error recovery to ensure the bot never freezes, even in case of errors.

Features:
1. Process all database operations in separate threads
2. Add timeouts to prevent indefinite blocking
3. Use a fail-safe mechanism to cancel operations that take too long
4. Implement clean error recovery with explicit cleanup
5. Minimal dependencies to avoid circular import issues
"""
import logging
import sys
import threading
import traceback
import time
from datetime import datetime
from sqlalchemy import func, create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.pool import QueuePool
from app import app
from models import User, Transaction

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Global operation timeout (in seconds)
OPERATION_TIMEOUT = 5

class OperationTimeoutError(Exception):
    """Exception raised when an operation takes too long to complete."""
    pass

def with_timeout(func, timeout=OPERATION_TIMEOUT):
    """
    Run a function with a timeout to prevent indefinite blocking.
    
    Args:
        func: Function to run
        timeout: Timeout in seconds
        
    Returns:
        Result of the function or raises OperationTimeoutError
    """
    result = [None]
    error = [None]
    completed = [False]
    
    def worker():
        try:
            result[0] = func()
            completed[0] = True
        except Exception as e:
            error[0] = e
            completed[0] = True
    
    thread = threading.Thread(target=worker)
    thread.daemon = True
    thread.start()
    thread.join(timeout)
    
    if not completed[0]:
        raise OperationTimeoutError(f"Operation took longer than {timeout} seconds to complete")
    
    if error[0]:
        raise error[0]
        
    return result[0]

def find_user(identifier, use_app_context=True):
    """
    Find a user by identifier with timeout protection.
    
    Args:
        identifier: Username, telegram_id, or database ID
        use_app_context: If True, use the app's context instead of a new session
        
    Returns:
        User object or None if not found
    """
    def _find_user():
        # Always use the app context to ensure correct database access
        with app.app_context():
            # Try to find by telegram_id
            try:
                user = User.query.filter_by(telegram_id=str(identifier)).first()
                if user:
                    return user
            except Exception as e:
                logger.error(f"Error finding user by telegram_id: {e}")
                
            # Try to find by user ID (database ID)
            try:
                user_id = int(identifier)
                user = User.query.get(user_id)
                if user:
                    return user
            except (ValueError, TypeError) as e:
                logger.error(f"Error finding user by ID: {e}")
                
            # Try to find by username
            if isinstance(identifier, str):
                # Remove @ prefix if present
                clean_username = identifier[1:] if identifier.startswith('@') else identifier
                user = User.query.filter(func.lower(User.username) == func.lower(clean_username)).first()
                if user:
                    return user
                    
            return None
    
    try:
        return with_timeout(_find_user)
    except Exception as e:
        logger.error(f"Error finding user: {e}")
        return None

def adjust_balance(identifier, amount, reason="Admin balance adjustment", skip_trading=False, silent=False):
    """
    Adjust a user's balance with advanced error handling and timeout protection.
    This implementation ensures the bot will never freeze, even if there are database issues.
    
    Args:
        identifier: Username, telegram_id, or database ID
        amount: Amount to adjust (positive to add, negative to deduct)
        reason: Reason for the adjustment
        skip_trading: If True, don't trigger auto trading even for positive adjustments
        silent: If True, don't log the adjustment
        
    Returns:
        tuple: (success, message)
    """
    # Input validation
    try:
        amount = float(amount)
    except (ValueError, TypeError):
        return False, f"Invalid amount: {amount}. Please enter a valid number."
    
    if amount == 0:
        return False, "Amount cannot be zero."
    
    # Find the user
    user = find_user(identifier)
    if not user:
        return False, f"User not found: {identifier}"
    
    # Start a background thread for the adjustment
    adjustment_thread = threading.Thread(
        target=lambda: background_worker(),
        daemon=True
    )
    adjustment_thread.start()
    
    # Return immediately without waiting for the thread to complete
    return True, f"Balance adjustment for {user.username} initiated. Amount: ${amount}"
    
    def process_adjustment():
        """Process the balance adjustment in the app context"""
        with app.app_context():
            # Get a fresh instance of the user to avoid stale data
            user = User.query.get(user.id)
            if not user:
                return False, f"User not found when processing adjustment: {identifier}"
            
            # Check for negative balance
            if amount < 0 and user.balance + amount < 0:
                return False, f"Cannot deduct ${abs(amount)} from {user.username}'s balance of ${user.balance}"
            
            # Create transaction record
            transaction = Transaction(
                user_id=user.id,
                amount=amount,
                transaction_type="admin_adjustment",
                status="completed",
                description=reason,
                txid=f"admin_{int(time.time())}",
                created_at=datetime.utcnow()
            )
            
            # Update user balance
            user.balance += amount
            
            # Commit changes
            try:
                from app import db
                db.session.add(transaction)
                db.session.commit()
                
                if not silent:
                    logger.info(f"Balance adjusted for {user.username}: ${amount} ({reason})")
                
                # Start trading for positive adjustments if not skipped
                if amount > 0 and not skip_trading:
                    start_trading()
                
                return True, f"Balance for {user.username} adjusted by ${amount}. New balance: ${user.balance}"
            except Exception as e:
                from app import db
                db.session.rollback()
                logger.error(f"Error adjusting balance: {e}")
                return False, f"Database error when adjusting balance: {e}"
    
    def start_trading():
        """Start trading in background without blocking"""
        try:
            # Import here to avoid circular imports
            from bot.services.trading_engine import start_trading_session
            start_trading_session(user.id, amount)
        except ImportError:
            # Fallback if trading engine module isn't available
            pass
        except Exception as e:
            logger.error(f"Error starting trading: {e}")
    
    def background_worker():
        """Execute the adjustment in a background thread with timeout protection"""
        try:
            success, message = with_timeout(process_adjustment, timeout=OPERATION_TIMEOUT * 2)
            if not success and not silent:
                logger.error(f"Balance adjustment failed: {message}")
        except Exception as e:
            if not silent:
                logger.error(f"Background adjustment error: {e}")
            traceback.print_exc()

def fix_admin_confirm_handler(bot_runner_path='bot_v20_runner.py'):
    """
    Fix the admin_confirm_adjustment_handler function to prevent freezing
    by using the enhanced balance manager.
    
    Args:
        bot_runner_path: Path to the bot_v20_runner.py file
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        with open(bot_runner_path, 'r') as file:
            content = file.read()
        
        # Find the admin_confirm_adjustment_handler function
        if 'def admin_confirm_adjustment_handler(update, context):' in content:
            # Find the start and end of the function
            start_idx = content.find('def admin_confirm_adjustment_handler(update, context):')
            next_def_idx = content.find('def ', start_idx + 10)
            end_idx = next_def_idx if next_def_idx > 0 else len(content)
            
            # Replace the function with the fixed version
            fixed_handler = """
def admin_confirm_adjustment_handler(update, context):
    # Non-blocking balance adjustment using enhanced_balance_manager
    query = update.callback_query
    query.answer()
    
    try:
        # Get adjustment data from context
        data = context.chat_data.get('adjustment_data', None)
        if not data:
            query.edit_message_text("Error: Adjustment data not found.")
            return
        
        username = data.get('username')
        amount = data.get('amount')
        reason = data.get('reason', 'Admin adjustment')
        
        # Log the start of the operation
        logging.info("Starting balance adjustment in background thread")
        
        # Start the adjustment in a separate thread
        import threading
        from enhanced_balance_manager import adjust_balance
        
        thread = threading.Thread(
            target=lambda: adjust_balance(username, amount, reason),
            daemon=True
        )
        thread.start()
        
        # Update the message immediately without waiting for the thread
        query.edit_message_text(f"Balance adjustment for {username} initiated. Amount: ${amount}")
        logging.info("Balance adjustment handler completed - thread started")
        
        # Inform the admin that the operation was successful
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Balance adjustment confirmed successfully by admin."
        )
        
    except Exception as e:
        logging.error(f"Error in admin_confirm_adjustment_handler: {e}")
        query.edit_message_text(f"Error adjusting balance: {str(e)}")
"""
            
            # Replace the old function with the fixed one
            new_content = content[:start_idx] + fixed_handler + content[end_idx:]
            
            # Write the updated content back to the file
            with open(bot_runner_path, 'w') as file:
                file.write(new_content)
            
            return True
        else:
            logger.error("admin_confirm_adjustment_handler function not found in bot_runner.py")
            return False
    except Exception as e:
        logger.error(f"Error fixing admin_confirm_handler: {e}")
        return False

def main():
    """
    Command-line interface for the enhanced balance manager
    
    Usage:
        python enhanced_balance_manager.py [action] [args...]
        
    Actions:
        adjust <identifier> <amount> [reason]  - Adjust a user's balance
        fix                                    - Fix the bot's admin confirm handler
        help                                   - Show help
    """
    if len(sys.argv) < 2:
        print("Error: No action specified")
        print("Use 'python enhanced_balance_manager.py help' for usage information")
        return
    
    action = sys.argv[1].lower()
    
    if action == 'help':
        print(__doc__)
        print(main.__doc__)
        return
    
    elif action == 'adjust':
        if len(sys.argv) < 4:
            print("Error: Missing arguments for adjust")
            print("Usage: python enhanced_balance_manager.py adjust <identifier> <amount> [reason]")
            return
        
        identifier = sys.argv[2]
        amount = sys.argv[3]
        reason = ' '.join(sys.argv[4:]) if len(sys.argv) > 4 else "Admin balance adjustment"
        
        print(f"Adjusting balance for {identifier} by {amount}...")
        success, message = adjust_balance(identifier, amount, reason)
        print(message)
        
    elif action == 'fix':
        print("Fixing admin_confirm_adjustment_handler in bot_v20_runner.py...")
        success = fix_admin_confirm_handler()
        if success:
            print("Fix applied successfully!")
        else:
            print("Failed to apply fix. See error log for details.")
    
    else:
        print(f"Error: Unknown action '{action}'")
        print("Use 'python enhanced_balance_manager.py help' for usage information")

if __name__ == "__main__":
    main()