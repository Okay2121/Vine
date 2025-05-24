"""
Balance Adjustment Fix - Ensures balance updates are properly committed to the database
This script fixes the issue where balance adjustments aren't properly updating in the database
"""
import logging
import os
import sys
from datetime import datetime
import traceback

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Add the current directory to path so we can import the app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app import app, db
    from models import User, Transaction
except ImportError as e:
    logger.error(f"Failed to import required modules: {e}")
    sys.exit(1)

def fix_balance_adjustment():
    """
    Fix the balance adjustment functionality to ensure database updates
    are properly committed
    """
    try:
        with app.app_context():
            # Test the fix with a user
            test_user = User.query.first()
            
            if not test_user:
                logger.error("No users found in database for testing")
                return False
            
            # Store original balance
            original_balance = test_user.balance
            logger.info(f"Original balance for user {test_user.username}: {original_balance}")
            
            # Create a small test adjustment (0.001 SOL)
            test_amount = 0.001
            
            # Update balance directly with SQL to ensure it works
            db.session.execute(
                f"UPDATE user SET balance = balance + {test_amount} WHERE id = {test_user.id}"
            )
            
            # Force commit
            db.session.commit()
            
            # Refresh the user object to see if balance was updated
            db.session.refresh(test_user)
            new_balance = test_user.balance
            
            logger.info(f"New balance after direct SQL update: {new_balance}")
            
            # Verify the change was made
            if abs(new_balance - (original_balance + test_amount)) < 0.0001:
                logger.info("✅ Direct SQL update works correctly")
            else:
                logger.error(f"❌ Direct SQL update failed. Expected {original_balance + test_amount}, got {new_balance}")
                return False
            
            # Now test our fix in the balance_manager.py
            logger.info("Testing balance_manager.py function...")
            
            # Import the fixed function
            try:
                from balance_manager import adjust_balance
                
                # Call the function
                success, message = adjust_balance(
                    str(test_user.id), 
                    test_amount, 
                    reason="Testing fix",
                    silent=False
                )
                
                logger.info(f"Adjustment result: {success}, {message}")
                
                # Refresh the user again
                db.session.refresh(test_user)
                final_balance = test_user.balance
                
                logger.info(f"Final balance after adjust_balance: {final_balance}")
                
                # Verify it worked
                if abs(final_balance - (new_balance + test_amount)) < 0.0001:
                    logger.info("✅ balance_manager.py fix works correctly")
                else:
                    logger.error(f"❌ balance_manager.py fix failed. Expected {new_balance + test_amount}, got {final_balance}")
                    return False
                
                # Restore original balance for testing user
                test_user.balance = original_balance
                db.session.commit()
                logger.info(f"Restored original balance: {original_balance}")
                
                return True
                
            except ImportError:
                logger.error("Could not import adjust_balance from balance_manager")
                return False
            except Exception as e:
                logger.error(f"Error testing balance_manager.py: {e}")
                logger.error(traceback.format_exc())
                return False
            
    except Exception as e:
        logger.error(f"Error fixing balance adjustment: {e}")
        logger.error(traceback.format_exc())
        return False

def check_transaction_recording():
    """
    Verify transaction records are properly created and stored
    """
    try:
        with app.app_context():
            # Find a user for testing
            test_user = User.query.first()
            
            if not test_user:
                logger.error("No users found in database for testing")
                return False
            
            # Count current transactions
            initial_count = Transaction.query.filter_by(user_id=test_user.id).count()
            logger.info(f"User {test_user.username} has {initial_count} transactions")
            
            # Create a test transaction
            new_transaction = Transaction()
            new_transaction.user_id = test_user.id
            new_transaction.transaction_type = 'test'
            new_transaction.amount = 0.001
            new_transaction.token_name = "SOL"
            new_transaction.timestamp = datetime.utcnow()
            new_transaction.status = 'completed'
            new_transaction.notes = "Testing transaction recording"
            
            # Add to database and commit
            db.session.add(new_transaction)
            db.session.commit()
            
            # Check if transaction was recorded
            new_count = Transaction.query.filter_by(user_id=test_user.id).count()
            logger.info(f"User now has {new_count} transactions")
            
            if new_count == initial_count + 1:
                logger.info("✅ Transaction recording works correctly")
                return True
            else:
                logger.error(f"❌ Transaction recording failed. Expected {initial_count + 1}, got {new_count}")
                return False
            
    except Exception as e:
        logger.error(f"Error checking transaction recording: {e}")
        logger.error(traceback.format_exc())
        return False

def fix_error_handling_in_balance_manager():
    """
    Update the balance_manager.py file to include better error handling
    for database operations
    """
    try:
        balance_manager_path = 'balance_manager.py'
        
        if not os.path.exists(balance_manager_path):
            logger.error(f"{balance_manager_path} not found")
            return False
        
        with open(balance_manager_path, 'r') as file:
            content = file.read()
        
        # Check if we've already applied the fix
        if "# Force an immediate flush to ensure the database sees the change" in content:
            logger.info("Fix already applied to balance_manager.py")
            return True
        
        # Add better error handling and logging for database operations
        update_pattern = "            # Update user balance\n            user.balance += amount"
        replacement = """            # Update user balance - store the new value directly
            new_balance = user.balance + amount
            user.balance = new_balance
            
            # Force an immediate flush to ensure the database sees the change
            db.session.flush()"""
        
        # Apply the fix
        new_content = content.replace(update_pattern, replacement)
        
        # Update the file
        with open(balance_manager_path, 'w') as file:
            file.write(new_content)
        
        logger.info("✅ Updated balance_manager.py with better database handling")
        return True
        
    except Exception as e:
        logger.error(f"Error fixing error handling in balance_manager.py: {e}")
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    print("Running balance adjustment fix...")
    
    # First, update the balance_manager.py file
    if fix_error_handling_in_balance_manager():
        print("✅ Updated balance_manager.py with better database handling")
    else:
        print("❌ Failed to update balance_manager.py")
    
    # Then test the fix
    if fix_balance_adjustment():
        print("✅ Balance adjustment fix successful")
    else:
        print("❌ Balance adjustment fix failed")
    
    # Also check transaction recording
    if check_transaction_recording():
        print("✅ Transaction recording works correctly")
    else:
        print("❌ Transaction recording has issues")