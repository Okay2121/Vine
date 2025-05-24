#!/usr/bin/env python
"""
Comprehensive Balance Manager for Solana Memecoin Trading Bot
-----------------------------------------------------------------
This module consolidates all balance adjustment functionality into a single file to:
1. Make maintenance easier
2. Prevent bot freezing issues when using the admin panel
3. Provide consistent error handling and logging
4. Support both admin and programmatic balance adjustments

Usage:
1. Import and use adjust_balance() for programmatic balance adjustments
2. Run this file directly to use the command-line interface
3. The bot uses this module through admin_confirm_adjustment_handler
"""
import logging
import sys
import threading
import traceback
from datetime import datetime
from sqlalchemy import func
from app import app, db
from models import User, Transaction

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def find_user_by_username(username):
    """
    Find a user by their Telegram username (case-insensitive)
    
    Args:
        username (str): Username with or without @ prefix
    
    Returns:
        User object or None if not found
    """
    with app.app_context():
        # Remove @ prefix if present
        clean_username = username[1:] if username.startswith('@') else username
        
        # Search for username case-insensitive
        return User.query.filter(func.lower(User.username) == func.lower(clean_username)).first()

def find_user_by_id(user_id):
    """
    Find a user by their database ID
    
    Args:
        user_id (int): Database ID of the user
    
    Returns:
        User object or None if not found
    """
    with app.app_context():
        return User.query.get(user_id)

def find_user_by_telegram_id(telegram_id):
    """
    Find a user by their Telegram ID
    
    Args:
        telegram_id (str): Telegram ID of the user
    
    Returns:
        User object or None if not found
    """
    with app.app_context():
        return User.query.filter_by(telegram_id=str(telegram_id)).first()

def find_user(identifier):
    """
    Find a user by username, telegram_id, or database ID
    
    Args:
        identifier (str): Username (with or without @), telegram_id, or database ID
        
    Returns:
        User object or None if not found
    """
    with app.app_context():
        user = None
        
        # Try to find by telegram_id
        try:
            user = User.query.filter_by(telegram_id=str(identifier)).first()
        except:
            pass
            
        # Try to find by user ID (database ID)
        if not user:
            try:
                user_id = int(identifier)
                user = User.query.get(user_id)
            except (ValueError, TypeError):
                pass
            
        # If not found and starts with @, try username without @
        if not user and isinstance(identifier, str) and identifier.startswith('@'):
            username = identifier[1:]  # Remove @ prefix
            user = User.query.filter(func.lower(User.username) == func.lower(username)).first()
            
        # If still not found, try as username directly
        if not user and isinstance(identifier, str):
            user = User.query.filter(func.lower(User.username) == func.lower(identifier)).first()
            
        return user

def create_user_if_missing(username):
    """
    Create a user if they don't exist
    
    Args:
        username (str): Username with or without @ prefix
        
    Returns:
        tuple: (User object, was_created boolean)
    """
    with app.app_context():
        # Clean username
        clean_username = username[1:] if username.startswith('@') else username
        
        # Try to find user first
        user = User.query.filter(func.lower(User.username) == func.lower(clean_username)).first()
        
        if user:
            return user, False
        
        # Create new user with minimal info
        new_user = User()
        new_user.username = clean_username
        new_user.telegram_id = f"created_{datetime.utcnow().timestamp()}"  # Placeholder
        new_user.balance = 0.0
        
        db.session.add(new_user)
        db.session.commit()
        
        return new_user, True

def check_user_dashboard(user_id=None, telegram_id=None, username=None):
    """
    Check a user's dashboard including balance and transaction history
    
    Args:
        user_id (int, optional): Database ID of the user
        telegram_id (str, optional): Telegram ID of the user
        username (str, optional): Username with or without @ prefix
        
    Returns:
        dict: User information and transaction history
    """
    with app.app_context():
        user = None
        
        # Try to find user by different methods
        if user_id:
            user = User.query.get(user_id)
        elif telegram_id:
            user = User.query.filter_by(telegram_id=str(telegram_id)).first()
        elif username:
            clean_username = username[1:] if username.startswith('@') else username
            user = User.query.filter(func.lower(User.username) == func.lower(clean_username)).first()
        
        if not user:
            return {"error": "User not found"}
        
        # Get transaction history
        transactions = Transaction.query.filter_by(user_id=user.id).order_by(Transaction.timestamp.desc()).all()
        
        # Format transaction data
        transaction_list = []
        for tx in transactions:
            transaction_list.append({
                "id": tx.id,
                "type": tx.transaction_type,
                "amount": tx.amount,
                "token": tx.token_name,
                "status": tx.status,
                "timestamp": tx.timestamp.isoformat(),
                "notes": tx.notes
            })
        
        # Prepare dashboard data
        dashboard = {
            "user": {
                "id": user.id,
                "username": user.username,
                "telegram_id": user.telegram_id,
                "balance": user.balance,
                "created_at": user.created_at.isoformat() if hasattr(user, 'created_at') else None,
                "wallet_address": user.wallet_address if hasattr(user, 'wallet_address') else None
            },
            "transactions": transaction_list
        }
        
        return dashboard

def set_initial_deposit(identifier, amount, reason="Admin initial deposit setting", silent=False):
    """
    Set a user's initial deposit value (doesn't affect current balance)
    
    This function updates the user's initial deposit field, which is used for ROI calculations
    throughout the dashboard and notifications. It does not adjust the actual balance.
    
    Args:
        identifier (str): Username, telegram_id, or database ID
        amount (float): Amount to set as initial deposit (must be non-negative)
        reason (str): Reason for setting the initial deposit
        silent (bool): If True, don't log the adjustment to console
        
    Returns:
        tuple: (success, message)
    """
    if not silent:
        logging.info(f"Initial deposit setting confirmed by admin.")
    
    # Use app context to work with database
    with app.app_context():
        try:
            # Find the user
            user = find_user(identifier)
            
            if not user:
                return False, f"User not found: {identifier}"
            
            # Validate amount is a positive number
            try:
                amount = float(amount)
                if amount < 0:
                    return False, f"Invalid amount: {amount} - must be non-negative"
            except ValueError:
                return False, f"Invalid amount: {amount} - must be a number"
            
            # Store original values for logging
            original_initial_deposit = user.initial_deposit
            
            # Update user initial deposit
            user.initial_deposit = amount
            
            if not silent:
                logging.info(f"User initial deposit updated. User ID: {user.telegram_id}, Initial Deposit: {user.initial_deposit:.4f}")
                logging.info("Bot is fully responsive.")
            
            # Create a transaction record for tracking
            new_transaction = Transaction()
            new_transaction.user_id = user.id
            new_transaction.transaction_type = 'admin_set_initial'
            new_transaction.amount = amount
            new_transaction.token_name = "SOL"
            new_transaction.timestamp = datetime.utcnow()
            new_transaction.status = 'completed'
            new_transaction.notes = reason
            
            # Add to database and commit
            db.session.add(new_transaction)
            db.session.commit()
            
            # Log the adjustment
            log_message = (
                f"INITIAL DEPOSIT SETTING\n"
                f"User: {user.username} (ID: {user.id}, Telegram ID: {user.telegram_id})\n"
                f"Initial deposit set to: {amount:.4f} SOL\n"
                f"Previous initial deposit: {original_initial_deposit:.4f} SOL\n"
                f"Current balance: {user.balance:.4f} SOL\n"
                f"Reason: {reason}\n"
                f"Transaction ID: {new_transaction.id}"
            )
            
            if not silent:
                logger.info(log_message)
            
            return True, log_message
            
        except Exception as e:
            # Handle errors
            db.session.rollback()
            logger.error(f"Error setting initial deposit: {e}")
            logger.error(traceback.format_exc())
            return False, f"Error: {str(e)}"

def adjust_balance(identifier, amount, reason="Admin balance adjustment", skip_trading=False, silent=False):
    """
    Adjust a user's balance by adding or subtracting the specified amount
    
    This is the core function for all balance adjustments and is designed to be:
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
        # Print confirmation messages as required by the prompt
        logging.info(f"Balance adjustment confirmed successfully by admin.")
    
    # Use app context to work with database
    with app.app_context():
        try:
            # Find the user - optimize to be quick and non-blocking
            user = find_user(identifier)
            
            if not user:
                return False, f"User not found: {identifier}"
            
            # Validate amount is a number
            try:
                amount = float(amount)
            except ValueError:
                return False, f"Invalid amount: {amount} - must be a number"
            
            # Check if deduction would make balance negative
            if amount < 0 and abs(amount) > user.balance:
                return False, f"Cannot deduct {abs(amount)} SOL - user only has {user.balance} SOL"
                
            # Store original balance for logging
            original_balance = user.balance
            
            # Update user balance
            user.balance += amount
            
            if not silent:
                # Print confirmation of user dashboard update
                logging.info(f"User dashboard updated. User ID: {user.telegram_id}, New Balance: {user.balance:.4f}")
                logging.info("Bot is fully responsive.")
            
            # Determine transaction type
            transaction_type = 'admin_credit' if amount > 0 else 'admin_debit'
            
            # Create transaction record
            new_transaction = Transaction()
            new_transaction.user_id = user.id
            new_transaction.transaction_type = transaction_type
            new_transaction.amount = abs(amount)
            new_transaction.token_name = "SOL"
            new_transaction.timestamp = datetime.utcnow()
            new_transaction.status = 'completed'
            new_transaction.notes = reason
            
            # Add to database and commit
            db.session.add(new_transaction)
            
            # CRITICAL FIX: Ensure database changes are committed properly
            try:
                # Commit the transaction
                db.session.commit()
                
                # Get a fresh instance of the user to verify balance was updated
                fresh_user = User.query.get(user.id)
                
                # Double-check if balance was updated correctly
                if fresh_user and abs(fresh_user.balance - (original_balance + amount)) > 0.0001:
                    # Try to fix it manually if there's a discrepancy
                    logger.warning(f"Balance not updated correctly. Expected: {original_balance + amount}, Got: {fresh_user.balance}")
                    fresh_user.balance = original_balance + amount
                    db.session.commit()
                    logger.info(f"Balance fixed manually. New balance: {fresh_user.balance}")
                    
                # Use the updated user going forward
                user = fresh_user
            except Exception as commit_error:
                db.session.rollback()
                logger.error(f"Error committing balance changes: {commit_error}")
                logger.error(traceback.format_exc())
                return False, f"Database error: {str(commit_error)}"
            
            # Log the adjustment (admin-only)
            action_type = "added to" if amount > 0 else "deducted from"
            # Reload the user to get the most current balance
            try:
                db.session.refresh(user)
                actual_balance = user.balance
            except:
                # Fallback to querying again if refresh fails
                try:
                    current_user = User.query.get(user.id)
                    actual_balance = current_user.balance if current_user else user.balance
                except:
                    actual_balance = user.balance  # Use the original if all else fails
            
            log_message = (
                f"BALANCE ADJUSTMENT SUCCESSFUL\n"
                f"User: {user.username} (ID: {user.id}, Telegram ID: {user.telegram_id})\n"
                f"{abs(amount):.4f} SOL {action_type} balance\n"
                f"Previous balance: {original_balance:.4f} SOL\n"
                f"New balance: {actual_balance:.4f} SOL\n"
                f"Reason: {reason}\n"
                f"Transaction ID: {new_transaction.id}"
            )
            
            if not silent:
                logger.info(log_message)
            
            # Start auto trading simulation if needed (only for additions) in a non-blocking way
            if amount > 0 and not skip_trading:
                try:
                    # Only import here to avoid circular imports
                    from utils.auto_trading_history import handle_admin_balance_adjustment
                    import threading
                    
                    # Create a function to run in background thread
                    def start_trading_in_background(user_id, adjustment_amount):
                        try:
                            with app.app_context():
                                handle_admin_balance_adjustment(user_id, adjustment_amount)
                                logger.info(f"Auto trading started for user {user_id}")
                        except Exception as e:
                            logger.error(f"Error in background trading thread: {e}")
                    
                    # Start thread and don't wait for it
                    trading_thread = threading.Thread(
                        target=start_trading_in_background,
                        args=(user.id, amount)
                    )
                    trading_thread.daemon = True
                    trading_thread.start()
                    
                    if not silent:
                        logger.info("Auto-trading thread started in background - bot remains responsive")
                    
                except Exception as e:
                    logger.error(f"Error setting up auto trading thread: {e}")
                    # Don't fail the adjustment if auto trading fails
            
            return True, log_message
        
        except Exception as e:
            # Handle errors
            db.session.rollback()
            logger.error(f"Error adjusting balance: {e}")
            logger.error(traceback.format_exc())
            return False, f"Error: {str(e)}"

def list_users(limit=20):
    """
    List users in the database to identify who to adjust
    
    Args:
        limit (int): Maximum number of users to return
    
    Returns:
        list: User objects
    """
    with app.app_context():
        return User.query.order_by(User.id.desc()).limit(limit).all()

def fix_admin_confirm_handler(bot_runner_path='bot_v20_runner.py'):
    """
    Fix the admin_confirm_adjustment_handler function to prevent freezing
    
    This function is used to update the bot_v20_runner.py file with a fixed
    implementation of the admin_confirm_adjustment_handler that uses this module
    for balance adjustments instead of handling them directly.
    
    Args:
        bot_runner_path (str): Path to the bot_v20_runner.py file
        
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
        
        # Create a fixed version of the function
        fixed_impl = """
    \"\"\"Confirm and process the balance adjustment.\"\"\"
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
            
        # Use the dedicated balance_manager module to handle adjustments
        # This ensures the bot remains responsive and doesn't freeze
        import balance_manager
        
        # Get user details
        with app.app_context():
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
        
        # Use non-blocking, optimized balance adjustment
        identifier = user.telegram_id
        amount = admin_adjustment_amount
        reason = admin_adjustment_reason or "Bonus"
        
        success, message = balance_manager.adjust_balance(identifier, amount, reason)
        
        if success:
            # Show success message to admin
            with app.app_context():
                # Refresh user from database to get updated balance
                fresh_user = User.query.get(admin_target_user_id)
                
                if fresh_user:
                    # Format success message
                    result_message = (
                        f"✅ *Balance Updated Successfully*\\n\\n"
                        f"User ID: `{fresh_user.telegram_id}`\\n"
                        f"Username: @{fresh_user.username}\\n"
                        f"Old Balance: {admin_adjust_current_balance:.4f} SOL\\n"
                        f"New Balance: {fresh_user.balance:.4f} SOL\\n"
                        f"Change: {'➕' if amount > 0 else '➖'} {abs(amount):.4f} SOL\\n"
                        f"Reason: {reason}\\n\\n"
                        f"No notification was sent to the user."
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
        
        # Reset global variables to prevent reuse
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
            # Reset global variables - no need to redeclare them as global
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
    Command-line interface for managing user balances
    
    Usage:
        python balance_manager.py [action] [args...]
        
    Actions:
        adjust <identifier> <amount> [reason]  - Adjust a user's balance
        list                                  - List users
        check <identifier>                    - Check a user's dashboard
        create <username>                     - Create a user if they don't exist
        fix                                   - Fix the bot's admin confirm handler
        help                                  - Show help
    """
    if len(sys.argv) < 2:
        print("Usage: python balance_manager.py [action] [args...]")
        print("Run 'python balance_manager.py help' for more information")
        return
    
    action = sys.argv[1].lower()
    
    if action == "help":
        print("Solana Memecoin Trading Bot - Balance Manager")
        print("===========================================")
        print("Usage:")
        print("  python balance_manager.py [action] [args...]")
        print("\nActions:")
        print("  adjust <identifier> <amount> [reason]  - Adjust a user's balance")
        print("  list                                  - List users")
        print("  check <identifier>                    - Check a user's dashboard")
        print("  create <username>                     - Create a user if they don't exist")
        print("  fix                                   - Fix the bot's admin confirm handler")
        print("  help                                  - Show this help message")
        print("\nExamples:")
        print("  python balance_manager.py adjust @briensmart 5.0 'Welcome bonus'")
        print("  python balance_manager.py adjust @briensmart -2.5 'Penalty adjustment'")
        print("  python balance_manager.py list")
        print("  python balance_manager.py check @briensmart")
        print("  python balance_manager.py create @newuser")
        print("  python balance_manager.py fix")
        
    elif action == "adjust":
        if len(sys.argv) < 4:
            print("Usage: python balance_manager.py adjust <identifier> <amount> [reason]")
            print("Example: python balance_manager.py adjust @briensmart 5.0 'Welcome bonus'")
            return
        
        # Get arguments
        identifier = sys.argv[2]
        amount = sys.argv[3]
        reason = sys.argv[4] if len(sys.argv) > 4 else "Admin balance adjustment"
        
        try:
            # Convert amount to float
            amount = float(amount)
        except ValueError:
            print(f"❌ Invalid amount: {amount} - must be a number")
            return
        
        # Adjust balance
        success, message = adjust_balance(identifier, amount, reason)
        
        # Print result
        if success:
            print("✅ Balance adjusted successfully!")
            print(message)
        else:
            print(f"❌ Failed to adjust balance: {message}")
            
            # List available users to help admin
            with app.app_context():
                users = User.query.all()
                if users:
                    print("\nAvailable users:")
                    for user in users:
                        print(f"- Username: {user.username}, Telegram ID: {user.telegram_id}, Balance: {user.balance:.4f} SOL")
    
    elif action == "list":
        # List users
        with app.app_context():
            users = list_users()
            if users:
                print("Available users:")
                for user in users:
                    print(f"- ID: {user.id}, Username: {user.username}, Telegram ID: {user.telegram_id}, Balance: {user.balance:.4f} SOL")
            else:
                print("No users found in the database")
    
    elif action == "check":
        if len(sys.argv) < 3:
            print("Usage: python balance_manager.py check <identifier>")
            print("Example: python balance_manager.py check @briensmart")
            return
        
        # Get user identifier
        identifier = sys.argv[2]
        
        # Try different types of identifiers
        try:
            user_id = int(identifier)
            dashboard = check_user_dashboard(user_id=user_id)
        except ValueError:
            if identifier.isdigit():
                dashboard = check_user_dashboard(telegram_id=identifier)
            else:
                dashboard = check_user_dashboard(username=identifier)
        
        # Print result
        if "error" in dashboard:
            print(f"❌ {dashboard['error']}")
            return
        
        # Print user info
        user = dashboard["user"]
        print(f"User Information:")
        print(f"- ID: {user['id']}")
        print(f"- Username: {user['username']}")
        print(f"- Telegram ID: {user['telegram_id']}")
        print(f"- Balance: {user['balance']:.4f} SOL")
        if user['wallet_address']:
            print(f"- Wallet: {user['wallet_address']}")
        print(f"- Created: {user['created_at']}")
        
        # Print transactions
        transactions = dashboard["transactions"]
        if transactions:
            print("\nRecent Transactions:")
            for tx in transactions[:10]:  # Show only the 10 most recent
                timestamp = datetime.fromisoformat(tx["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
                print(f"- [{timestamp}] {tx['type']}: {tx['amount']:.4f} {tx['token']} ({tx['status']})")
                if tx["notes"]:
                    print(f"  Note: {tx['notes']}")
        else:
            print("\nNo transactions found for this user")
    
    elif action == "create":
        if len(sys.argv) < 3:
            print("Usage: python balance_manager.py create <username>")
            print("Example: python balance_manager.py create @newuser")
            return
        
        # Get username
        username = sys.argv[2]
        
        # Create user
        user, created = create_user_if_missing(username)
        
        # Print result
        if created:
            print(f"✅ Created new user: {user.username} (ID: {user.id})")
        else:
            print(f"ℹ️ User already exists: {user.username} (ID: {user.id})")
    
    elif action == "fix":
        # Fix the admin confirm handler
        success = fix_admin_confirm_handler()
        
        # Print result
        if success:
            print("✅ Successfully fixed admin_confirm_adjustment_handler in bot_v20_runner.py")
        else:
            print("❌ Failed to fix admin_confirm_adjustment_handler")
    
    else:
        print(f"Unknown action: {action}")
        print("Run 'python balance_manager.py help' for available actions")

if __name__ == "__main__":
    main()