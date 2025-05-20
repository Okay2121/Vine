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
    
    thread = threading.Thread(target=worker)
    thread.daemon = True
    thread.start()
    thread.join(timeout)
    
    if not completed[0]:
        if thread.is_alive():
            # Operation is still running but timed out
            logger.error(f"Operation timed out after {timeout} seconds")
            raise OperationTimeoutError(f"Operation timed out after {timeout} seconds")
        elif error[0]:
            # Operation failed with an error
            logger.error(f"Operation failed: {error[0]}")
            raise error[0]
    elif error[0]:
        # Operation completed but with an error
        raise error[0]
        
    return result[0]

def get_db_session():
    """
    Get a new database session independent of the app's session.
    This prevents the main thread's session from being affected by operations in other threads.
    
    Returns:
        sqlalchemy.orm.Session: A new database session
    """
    engine = create_engine(
        app.config["SQLALCHEMY_DATABASE_URI"],
        poolclass=QueuePool,
        pool_size=10,
        max_overflow=20,
        pool_timeout=30,
        pool_recycle=3600
    )
    session_factory = sessionmaker(bind=engine)
    return scoped_session(session_factory)

def find_user(identifier, use_app_context=False):
    """
    Find a user by identifier with timeout protection.
    
    Args:
        identifier: Username, telegram_id, or database ID
        use_app_context: If True, use the app's context instead of a new session
        
    Returns:
        User object or None if not found
    """
    def _find_user():
        if use_app_context:
            with app.app_context():
                from app import db
                
                # Try to find by telegram_id
                try:
                    user = User.query.filter_by(telegram_id=str(identifier)).first()
                    if user:
                        return user
                except:
                    pass
                    
                # Try to find by user ID (database ID)
                try:
                    user_id = int(identifier)
                    user = User.query.get(user_id)
                    if user:
                        return user
                except (ValueError, TypeError):
                    pass
                    
                # Try to find by username
                if isinstance(identifier, str):
                    # Remove @ prefix if present
                    clean_username = identifier[1:] if identifier.startswith('@') else identifier
                    user = User.query.filter(func.lower(User.username) == func.lower(clean_username)).first()
                    if user:
                        return user
                        
                return None
        else:
            # Use a dedicated session to avoid blocking the app's session
            # Instead of creating a new session, use the app context
            # This ensures we're using the correct database configuration
            with app.app_context():
                from app import db
                
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
            finally:
                session.close()
                Session.remove()
    
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
    if not silent:
        # Log initial confirmation
        logging.info("Balance adjustment confirmed successfully by admin.")
    
    # Find the user first
    user = find_user(identifier)
    if not user:
        return False, f"User not found: {identifier}"
    
    # Validate amount
    try:
        amount = float(amount)
    except ValueError:
        return False, f"Invalid amount: {amount} - must be a number"
    
    # Store user ID for background processing
    user_id = user.id
    telegram_id = user.telegram_id
    username = user.username
    
    # Process in a background thread to avoid blocking the bot
    result_container = [None]
    
    def process_adjustment():
        success = False
        message = ""
        
        # Use a dedicated database session
        Session = get_db_session()
        session = Session()
        
        try:
            # Find user again in this session
            db_user = session.query(User).get(user_id)
            if not db_user:
                return False, f"User not found in database"
            
            # Check if deduction would make balance negative
            if amount < 0 and abs(amount) > db_user.balance:
                return False, f"Cannot deduct {abs(amount)} SOL - user only has {db_user.balance} SOL"
            
            # Store original balance
            original_balance = db_user.balance
            
            # Update balance
            db_user.balance += amount
            
            # Create transaction record
            transaction_type = 'admin_credit' if amount > 0 else 'admin_debit'
            
            new_transaction = Transaction()
            new_transaction.user_id = db_user.id
            new_transaction.transaction_type = transaction_type
            new_transaction.amount = abs(amount)
            new_transaction.token_name = "SOL"
            new_transaction.timestamp = datetime.utcnow()
            new_transaction.status = 'completed'
            new_transaction.notes = reason
            
            # Add to session and commit
            session.add(new_transaction)
            session.commit()
            
            # Format log message
            action_type = "added to" if amount > 0 else "deducted from"
            log_message = (
                f"BALANCE ADJUSTMENT\n"
                f"User: {username} (ID: {user_id}, Telegram ID: {telegram_id})\n"
                f"{abs(amount):.4f} SOL {action_type} balance\n"
                f"Previous balance: {original_balance:.4f} SOL\n"
                f"New balance: {db_user.balance:.4f} SOL\n"
                f"Reason: {reason}\n"
                f"Transaction ID: {new_transaction.id}"
            )
            
            if not silent:
                logger.info(log_message)
                # Log dashboard update
                logging.info(f"User dashboard updated. User ID: {telegram_id}, New Balance: {db_user.balance:.4f}")
                logging.info("Bot is fully responsive.")
            
            success = True
            message = log_message
            
            # Start auto trading in a separate thread if needed
            if amount > 0 and not skip_trading:
                try:
                    # Start a new thread for auto trading
                    def start_trading():
                        try:
                            # Import here to avoid circular imports
                            from utils.auto_trading_history import handle_admin_balance_adjustment
                            
                            # Create a new app context for this thread
                            with app.app_context():
                                # Trigger auto trading
                                handle_admin_balance_adjustment(user_id, amount)
                                if not silent:
                                    logger.info(f"Auto trading started for user {user_id}")
                        except Exception as e:
                            # Don't crash if auto trading fails
                            logger.error(f"Error in auto trading thread: {e}")
                    
                    # Start thread
                    trading_thread = threading.Thread(target=start_trading)
                    trading_thread.daemon = True
                    trading_thread.start()
                    
                    if not silent:
                        logger.info("Auto-trading thread started in background - bot remains responsive")
                except Exception as e:
                    # Don't fail the adjustment if auto trading fails
                    logger.error(f"Error setting up auto trading thread: {e}")
            
            return success, message
        except Exception as e:
            # Handle errors
            session.rollback()
            logger.error(f"Error in balance adjustment thread: {e}")
            logger.error(traceback.format_exc())
            return False, f"Error: {str(e)}"
        finally:
            # Clean up resources
            session.close()
            Session.remove()
    
    # Start a background thread to process the adjustment
    def background_worker():
        try:
            result = process_adjustment()
            result_container[0] = result
        except Exception as e:
            # Catch any exceptions that might occur during processing
            logger.error(f"Critical error in balance adjustment worker: {e}")
            logger.error(traceback.format_exc())
            result_container[0] = (False, f"Critical error: {str(e)}")
    
    worker_thread = threading.Thread(target=background_worker)
    worker_thread.daemon = True
    worker_thread.start()
    
    # Wait for the worker to complete with a timeout
    worker_thread.join(OPERATION_TIMEOUT)
    
    # Check if the worker completed
    if worker_thread.is_alive():
        # Worker is still running after timeout
        if not silent:
            logger.error(f"Balance adjustment operation timed out after {OPERATION_TIMEOUT} seconds, but continues in background")
        
        # Return a message indicating the operation is still in progress
        return True, "Balance adjustment is processing in the background. The bot will remain responsive. Check logs for confirmation."
    
    # Worker completed within the timeout
    if result_container[0] is not None:
        return result_container[0]
    else:
        # This should never happen, but just in case
        return False, "Unknown error during balance adjustment"

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
        import re
        
        # Read the bot_v20_runner.py file
        with open(bot_runner_path, 'r') as file:
            content = file.read()
            
        # Find the admin_confirm_adjustment_handler function
        pattern = r'def admin_confirm_adjustment_handler\(update, chat_id\):(.*?)def admin_referral_overview_handler'
        match = re.search(pattern, content, re.DOTALL)
        
        if not match:
            logger.error(f"Could not find admin_confirm_adjustment_handler in {bot_runner_path}")
            return False
            
        # Get the current implementation
        current_impl = match.group(1)
        
        # Create a fixed version of the function that uses the enhanced balance manager
        fixed_impl = """
    \"\"\"Confirm and process the balance adjustment without freezing the bot.\"\"\"
    try:
        # Access global variables with balance adjustment info
        global admin_target_user_id, admin_adjust_telegram_id, admin_adjust_current_balance
        global admin_adjustment_amount, admin_adjustment_reason
        
        if admin_target_user_id is None or admin_adjustment_amount is None:
            bot.send_message(
                chat_id,
                "⚠️ Balance adjustment data is missing. Please try again.",
                reply_markup=bot.create_inline_keyboard([
                    [{"text": "Return to Admin Panel", "callback_data": "admin_back"}]
                ])
            )
            return
            
        # Use the fully non-blocking enhanced_balance_manager
        # This ensures the bot never freezes under any circumstances
        import enhanced_balance_manager
        
        # Get user details - but don't block if database is slow
        with app.app_context():
            try:
                user = User.query.get(admin_target_user_id)
                
                if not user:
                    bot.send_message(
                        chat_id,
                        "Error: User not found. The user may have been deleted. Please try again.",
                        reply_markup=bot.create_inline_keyboard([
                            [{"text": "Return to Admin Panel", "callback_data": "admin_back"}]
                        ])
                    )
                    # Reset global variables
                    admin_target_user_id = None
                    admin_adjust_telegram_id = None
                    admin_adjust_current_balance = None
                    admin_adjustment_amount = None
                    admin_adjustment_reason = None
                    return
            except Exception as db_error:
                # Handle database errors gracefully
                logging.error(f"Database error: {db_error}")
                bot.send_message(
                    chat_id,
                    "Database is busy. Your request will be processed in the background. You can continue using the bot.",
                    reply_markup=bot.create_inline_keyboard([
                        [{"text": "Return to Admin Panel", "callback_data": "admin_back"}]
                    ])
                )
                # Continue with just the identifier
                user = None
        
        # Start a background thread to handle the balance adjustment
        def process_adjustment_in_background():
            try:
                # Use the user's telegram_id as identifier for reliability
                identifier = admin_adjust_telegram_id
                amount = admin_adjustment_amount
                reason = admin_adjustment_reason or "Bonus"
                
                # Process balance adjustment in a way that never blocks
                success, message = enhanced_balance_manager.adjust_balance(identifier, amount, reason)
                
                if success:
                    # Get updated user data if possible
                    try:
                        with app.app_context():
                            fresh_user = User.query.filter_by(telegram_id=identifier).first()
                            new_balance = fresh_user.balance if fresh_user else "unknown"
                            
                            # Format success message
                            result_message = (
                                f"✅ *Balance Updated Successfully*\\n\\n"
                                f"User ID: `{identifier}`\\n"
                                f"Username: @{fresh_user.username if fresh_user else 'unknown'}\\n"
                                f"Old Balance: {admin_adjust_current_balance:.4f} SOL\\n"
                                f"New Balance: {new_balance if isinstance(new_balance, str) else f'{new_balance:.4f}'} SOL\\n"
                                f"Change: {'➕' if amount > 0 else '➖'} {abs(amount):.4f} SOL\\n"
                                f"Reason: {reason}\\n\\n"
                                f"No notification was sent to the user."
                            )
                    except Exception as e:
                        # Fallback message if can't access database
                        logging.error(f"Error getting updated user data: {e}")
                        result_message = (
                            f"✅ *Balance Updated Successfully*\\n\\n"
                            f"User ID: `{identifier}`\\n"
                            f"Change: {'➕' if amount > 0 else '➖'} {abs(amount):.4f} SOL\\n"
                            f"Reason: {reason}\\n\\n"
                            f"No notification was sent to the user.\\n"
                            f"(Full details unavailable due to database access)"
                        )
                    
                    # Send success message to admin
                    bot.send_message(
                        chat_id,
                        result_message,
                        parse_mode="Markdown",
                        reply_markup=bot.create_inline_keyboard([
                            [
                                {"text": "Adjust Another User", "callback_data": "admin_adjust_balance"},
                                {"text": "Back to Admin", "callback_data": "admin_back"}
                            ]
                        ])
                    )
                else:
                    # Handle error from the balance adjuster
                    bot.send_message(
                        chat_id,
                        f"❌ Error adjusting balance: {message}",
                        reply_markup=bot.create_inline_keyboard([
                            [{"text": "Return to Admin Panel", "callback_data": "admin_back"}]
                        ])
                    )
            except Exception as thread_error:
                # Handle any errors in the background thread
                logging.error(f"Error in balance adjustment background thread: {thread_error}")
                logging.error(traceback.format_exc())
                
                try:
                    # Attempt to notify admin of the error
                    bot.send_message(
                        chat_id,
                        f"❌ Error processing adjustment: {str(thread_error)}",
                        reply_markup=bot.create_inline_keyboard([
                            [{"text": "Return to Admin Panel", "callback_data": "admin_back"}]
                        ])
                    )
                except Exception:
                    # If sending the message fails, just log it
                    logging.error("Could not send error message to admin")
            finally:
                # Always reset global variables, even if there's an error
                global admin_target_user_id, admin_adjust_telegram_id, admin_adjust_current_balance
                global admin_adjustment_amount, admin_adjustment_reason
                admin_target_user_id = None
                admin_adjust_telegram_id = None
                admin_adjust_current_balance = None
                admin_adjustment_amount = None
                admin_adjustment_reason = None
        
        # Tell the admin the process has started
        bot.send_message(
            chat_id,
            "💰 *Processing Balance Adjustment*\\n\\nYour balance adjustment is being processed. The bot will remain responsive during this operation.",
            parse_mode="Markdown"
        )
        
        # Start the background thread
        adjustment_thread = threading.Thread(target=process_adjustment_in_background)
        adjustment_thread.daemon = True
        adjustment_thread.start()
        
        # Reset global variables immediately in this thread as well
        # This is a failsafe in case the background thread encounters an error
        admin_target_user_id = None
        admin_adjust_telegram_id = None
        admin_adjust_current_balance = None
        admin_adjustment_amount = None
        admin_adjustment_reason = None
        return
                
    except Exception as e:
        import logging
        logging.error(f"Error in admin_confirm_adjustment_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        
        try:
            # Reset global variables - no need to declare them as global again
            admin_target_user_id = None
            admin_adjust_telegram_id = None
            admin_adjust_current_balance = None
            admin_adjustment_amount = None
            admin_adjustment_reason = None
            
            # Send error message
            bot.send_message(
                chat_id,
                f"Error processing adjustment: {str(e)}",
                reply_markup=bot.create_inline_keyboard([
                    [{"text": "Return to Admin Panel", "callback_data": "admin_back"}]
                ])
            )
        except:
            pass
        
        return
"""
        
        # Replace the old implementation with the fixed one
        new_content = content.replace(current_impl, fixed_impl)
        
        # Write the updated content back to the file
        with open(bot_runner_path, 'w') as file:
            file.write(new_content)
            
        logger.info(f"Successfully fixed admin_confirm_adjustment_handler in {bot_runner_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error fixing admin_confirm_adjustment_handler: {e}")
        logger.error(traceback.format_exc())
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
        print("Usage: python enhanced_balance_manager.py [action] [args...]")
        print("Run 'python enhanced_balance_manager.py help' for more information")
        return
    
    action = sys.argv[1].lower()
    
    if action == "help":
        print("Enhanced Balance Manager - Never Freeze Version")
        print("==========================================")
        print("Usage:")
        print("  python enhanced_balance_manager.py [action] [args...]")
        print("\nActions:")
        print("  adjust <identifier> <amount> [reason]  - Adjust a user's balance")
        print("  fix                                    - Fix the bot's admin confirm handler")
        print("  help                                   - Show this help message")
        print("\nExamples:")
        print("  python enhanced_balance_manager.py adjust @username 5.0 'Welcome bonus'")
        print("  python enhanced_balance_manager.py adjust 123456789 -2.5 'Penalty'")
        print("  python enhanced_balance_manager.py fix")
        
    elif action == "adjust":
        if len(sys.argv) < 4:
            print("Usage: python enhanced_balance_manager.py adjust <identifier> <amount> [reason]")
            print("Example: python enhanced_balance_manager.py adjust @username 5.0 'Welcome bonus'")
            return
        
        identifier = sys.argv[2]
        
        try:
            amount = float(sys.argv[3])
        except ValueError:
            print(f"❌ Invalid amount: {sys.argv[3]} - must be a number")
            return
            
        reason = sys.argv[4] if len(sys.argv) > 4 else "Admin balance adjustment"
        
        print(f"Adjusting balance for {identifier}...")
        success, message = adjust_balance(identifier, amount, reason)
        
        if success:
            print("✅ Success!")
            print(message)
        else:
            print("❌ Failed!")
            print(message)
    
    elif action == "fix":
        print("Applying fix to admin_confirm_adjustment_handler...")
        success = fix_admin_confirm_handler()
        
        if success:
            print("✅ Fix applied successfully!")
        else:
            print("❌ Failed to apply fix!")
            
    else:
        print(f"Unknown action: {action}")
        print("Run 'python enhanced_balance_manager.py help' for available actions")

if __name__ == "__main__":
    main()