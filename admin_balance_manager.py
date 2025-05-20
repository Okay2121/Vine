#!/usr/bin/env python
"""
Admin Balance Manager - Clean implementation for balance adjustments
Allows adding or deducting user balances silently without affecting auto deposit detection
"""
import logging
import sys
from sqlalchemy import func
from datetime import datetime
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
    Find a user by username (case-insensitive) or telegram_id
    
    Args:
        identifier (str): Username (with or without @) or telegram_id
        
    Returns:
        User object or None if not found
    """
    with app.app_context():
        user = None
        
        # Check if identifier is a telegram_id
        try:
            user = User.query.filter_by(telegram_id=identifier).first()
        except:
            pass
            
        # If not found and starts with @, try username without @
        if not user and isinstance(identifier, str) and identifier.startswith('@'):
            username = identifier[1:]  # Remove @ prefix
            user = User.query.filter(func.lower(User.username) == func.lower(username)).first()
            
        # If still not found, try as username directly
        if not user and isinstance(identifier, str):
            user = User.query.filter(func.lower(User.username) == func.lower(identifier)).first()
            
        return user

def adjust_balance(identifier, amount, reason="Admin balance adjustment"):
    """
    Adjust a user's balance by adding or subtracting the specified amount
    
    Args:
        identifier (str): Username or telegram_id of the user
        amount (float): Amount to adjust (positive to add, negative to deduct)
        reason (str): Reason for the adjustment
        
    Returns:
        tuple: (success, message)
    """
    import logging
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
            db.session.commit()
            
            # Log the adjustment (admin-only)
            action_type = "added to" if amount > 0 else "deducted from"
            log_message = (
                f"ADMIN BALANCE ADJUSTMENT\n"
                f"User: {user.username} (ID: {user.id}, Telegram ID: {user.telegram_id})\n"
                f"{abs(amount):.4f} SOL {action_type} balance\n"
                f"Previous balance: {original_balance:.4f} SOL\n"
                f"New balance: {user.balance:.4f} SOL\n"
                f"Reason: {reason}\n"
                f"Transaction ID: {new_transaction.id}"
            )
            
            logger.info(log_message)
            
            # Start auto trading simulation if needed (only for additions) in a non-blocking way
            if amount > 0:
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
                    logger.info("Auto-trading thread started in background - bot remains responsive")
                    
                except Exception as e:
                    logger.error(f"Error setting up auto trading thread: {e}")
                    # Don't fail the adjustment if auto trading fails
            
            return True, log_message
        
        except Exception as e:
            # Handle errors
            db.session.rollback()
            logger.error(f"Error adjusting balance: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False, f"Error: {str(e)}"

def main():
    """Command-line interface for adjusting balances"""
    if len(sys.argv) < 3:
        print("Usage: python admin_balance_manager.py <username> <amount> [reason]")
        print("Example: python admin_balance_manager.py @briensmart 5.0 'Welcome bonus'")
        print("Example: python admin_balance_manager.py @briensmart -2.5 'Penalty adjustment'")
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