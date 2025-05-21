#!/usr/bin/env python
"""
Fixed Balance Manager for Solana Memecoin Trading Bot
-----------------------------------------------------
This module fixes the issue where balance adjustments show as successful
but don't actually update the database. It ensures all database operations
complete properly and provides clear error messages when they don't.
"""
import logging
import sys
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
        except Exception as e:
            logger.error(f"Error finding user by telegram_id: {e}")
            
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

def adjust_balance(identifier, amount, reason="Admin balance adjustment", skip_trading=False, silent=False):
    """
    Fixed balance adjustment function that properly updates the database
    
    Args:
        identifier (str): Username, telegram_id, or database ID
        amount (float): Amount to adjust (positive to add, negative to deduct)
        reason (str): Reason for the adjustment
        skip_trading (bool): If True, don't trigger auto trading even for positive adjustments
        silent (bool): If True, don't log the adjustment to console
        
    Returns:
        tuple: (success, message)
    """
    # Log only once
    if not silent:
        logging.info(f"Starting balance adjustment: {identifier}, amount: {amount}, reason: {reason}")
    
    # Validate input
    try:
        amount = float(amount)
    except ValueError:
        return False, f"Invalid amount: {amount} - must be a number"
    
    with app.app_context():
        try:
            # Find the user
            user = find_user(identifier)
            
            if not user:
                return False, f"User not found: {identifier}"
            
            # Check if deduction would make balance negative
            if amount < 0 and abs(amount) > user.balance:
                return False, f"Cannot deduct {abs(amount)} SOL - user only has {user.balance} SOL"
                
            # Store original balance for logging
            original_balance = user.balance
            
            # Update user balance
            user.balance += amount
            
            if not silent:
                logging.info(f"Updating user balance: {user.username} (ID: {user.id}), Current: {original_balance}, New: {user.balance}")
            
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
            
            # Add to database and commit explicitly
            db.session.add(new_transaction)
            
            # Commit the changes
            db.session.commit()
            
            # Verify the changes were actually saved by querying the user again with a fresh session
            db.session.close()  # Close current session
            
            # Create a new session to ensure we're not getting cached data
            updated_user = db.session.query(User).filter(User.id == user.id).first()
            
            # Verify the transaction was actually saved - using a fresh query
            # to avoid detached instance errors
            transaction_id = new_transaction.id  # Store the ID before closing the session
            transaction_exists = db.session.execute(
                "SELECT COUNT(*) FROM transaction WHERE id = :id",
                {"id": transaction_id}
            ).scalar()
            
            if not transaction_exists:
                return False, "Transaction record not saved properly"
            
            # Check if we got the updated user back
            if not updated_user:
                # If we didn't get the updated user, try one more query with a direct SQL approach
                from sqlalchemy import text
                result = db.session.execute(text("SELECT balance FROM user WHERE id = :user_id"), {"user_id": user.id})
                new_balance = result.scalar()
                
                # Log message with what we have
                action_type = "added to" if amount > 0 else "deducted from"
                log_message = (
                    f"BALANCE ADJUSTMENT SUCCESSFUL (VERIFICATION INCOMPLETE)\n"
                    f"User ID: {user.id}, Telegram ID: {user.telegram_id}\n"
                    f"{abs(amount):.4f} SOL {action_type} balance\n"
                    f"Previous balance: {original_balance:.4f} SOL\n"
                    f"Expected new balance: {original_balance + amount:.4f} SOL\n"
                    f"Actual balance from SQL: {new_balance if new_balance is not None else 'Unknown'}\n"
                    f"Reason: {reason}\n"
                    f"Transaction ID: {new_transaction.id}"
                )
            else:
                # Log the adjustment using the updated_user data
                action_type = "added to" if amount > 0 else "deducted from"
                log_message = (
                    f"BALANCE ADJUSTMENT SUCCESSFUL\n"
                    f"User: {updated_user.username or 'Unknown'} (ID: {updated_user.id}, Telegram ID: {updated_user.telegram_id})\n"
                    f"{abs(amount):.4f} SOL {action_type} balance\n"
                    f"Previous balance: {original_balance:.4f} SOL\n"
                    f"New balance: {updated_user.balance:.4f} SOL\n"
                    f"Reason: {reason}\n"
                    f"Transaction ID: {new_transaction.id}"
                )
            
            if not silent:
                logger.info(log_message)
            
            # Start auto trading simulation if needed (only for additions)
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
                        logger.info("Auto-trading thread started in background")
                    
                except Exception as e:
                    logger.error(f"Error setting up auto trading thread: {e}")
                    # Don't fail the adjustment if auto trading fails
            
            return True, log_message
        
        except Exception as e:
            # Handle errors
            db.session.rollback()
            error_message = f"Error adjusting balance: {e}"
            logger.error(error_message)
            logger.error(traceback.format_exc())
            return False, error_message

def main():
    """Command-line interface for adjusting balances"""
    if len(sys.argv) < 3:
        print("Usage: python fixed_balance_manager.py <username> <amount> [reason]")
        print("Example: python fixed_balance_manager.py @username 5.0 'Welcome bonus'")
        print("Example: python fixed_balance_manager.py @username -2.5 'Penalty adjustment'")
        return
    
    # Get arguments
    identifier = sys.argv[1]
    amount = float(sys.argv[2])
    reason = sys.argv[3] if len(sys.argv) > 3 else "Admin balance adjustment"
    
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

if __name__ == "__main__":
    main()